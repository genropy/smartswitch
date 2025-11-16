"""
Switcher - core implementation

This module implements the first working iteration of Switcher,
according to the high-level design we discussed.

Key features implemented here:
- Per-class Switcher instances.
- Optional prefix-based name normalization.
- Explicit alias for registration via @switch("alias").
- Name collision detection at switch level.
- Parent/child switch hierarchy (with children registered by name).
- Local registry for methods (by logical name).
- Plugins (BasePlugin) with on_decore + wrap_handler hooks.
- Runtime enable/disable of plugins per instance/method/plugin/thread.
- Per-instance, per-method, per-plugin, per-thread runtime data.
- Named dispatch via switch("name")(...).
- Dotted path dispatch via switch("child.sub.method")(...).
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Type

from smartasync import smartasync
from smartseeds import SmartOptions, extract_kwargs

# ============================================================
# THREAD-LOCAL CONTEXT
# ============================================================

_activation_ctx: contextvars.ContextVar[Dict[Any, bool] | None] = contextvars.ContextVar(
    "smartswitch_activation", default=None
)
_runtime_ctx: contextvars.ContextVar[Dict[Any, Dict[str, Any]] | None] = contextvars.ContextVar(
    "smartswitch_runtime", default=None
)


def _get_activation_map() -> Dict[Any, bool]:
    """Return the thread-local activation map."""
    m = _activation_ctx.get()
    if m is None:
        m = {}
        _activation_ctx.set(m)
    return m


def _get_runtime_map() -> Dict[Any, Dict[str, Any]]:
    """Return the thread-local runtime data map."""
    m = _runtime_ctx.get()
    if m is None:
        m = {}
        _runtime_ctx.set(m)
    return m


# ============================================================
# DATA STRUCTURES
# ============================================================


@dataclass
class MethodEntry:
    """Metadata and runtime info for a decorated method."""

    name: str  # logical registered name
    func: Callable  # original function
    switch: "Switcher"  # owning switch
    plugins: List[str]  # ordered plugin names
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _PluginSpec:
    """Factory metadata required to re-create a plugin."""

    factory: Type["BasePlugin"]
    kwargs: Dict[str, Any]
    plugin_name: str

    def clone(self) -> "_PluginSpec":
        return _PluginSpec(self.factory, dict(self.kwargs), self.plugin_name)

    def instantiate(self) -> "BasePlugin":
        params = dict(self.kwargs)
        if "name" not in params and self.plugin_name:
            params["name"] = self.plugin_name
        return self.factory(**params)


# ============================================================
# CONFIGURATION PROXIES
# ============================================================


class MethodConfigProxy:
    """
    Proxy for per-method configuration access.

    Allows setting/getting configuration for specific methods:
        sw.logging.configure['calculate'].flags = 'time'
        sw.logging.configure['calculate'].level = 'DEBUG'
    """

    def __init__(self, plugin: "BasePlugin", method_names: str):
        """
        Args:
            plugin: The plugin instance
            method_names: Single method or comma-separated ('calculate,clear')
        """
        object.__setattr__(self, "_plugin", plugin)
        object.__setattr__(self, "_method_names", method_names)

    @property
    def flags(self) -> str:
        """Get merged flags for this method (only active boolean flags)."""
        first = self._method_names.split(",")[0].strip()
        cfg = self._plugin.get_config(first)
        enabled = [k for k, v in cfg.items() if isinstance(v, bool) and v]
        return ",".join(enabled)

    @flags.setter
    def flags(self, value: str):
        """Set flags for this/these method(s)."""
        methods = [m.strip() for m in self._method_names.split(",")]
        self._plugin._update_config(*methods, flags=value)

    @property
    def config(self) -> dict:
        """Get full merged configuration for method."""
        first = self._method_names.split(",")[0].strip()
        return self._plugin.get_config(first)

    def __getattr__(self, name: str):
        """Get any merged config parameter for this method."""
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        first = self._method_names.split(",")[0].strip()
        cfg = self._plugin.get_config(first)
        return cfg.get(name)

    def __setattr__(self, name: str, value: Any):
        """Set any config parameter for this/these method(s)."""
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            methods = [m.strip() for m in self._method_names.split(",")]
            self._plugin._update_config(*methods, **{name: value})


class ConfigureProxy:
    """
    Proxy for plugin configuration access (global and per-method).

    Allows both global and per-method configuration:
        sw.logging.configure.flags = 'print,enabled'
        sw.logging.configure['calculate'].flags = 'time'
    """

    def __init__(self, plugin: "BasePlugin"):
        object.__setattr__(self, "_plugin", plugin)

    @property
    def flags(self) -> str:
        """Get global flags (only active boolean flags)."""
        cfg = self._plugin._global_config
        enabled = [k for k, v in cfg.items() if isinstance(v, bool) and v]
        return ",".join(enabled)

    @flags.setter
    def flags(self, value: str):
        """Set global flags."""
        self._plugin._update_config(flags=value)

    @property
    def config(self) -> dict:
        """Get full global configuration."""
        return dict(self._plugin._global_config)

    def __getattr__(self, name: str):
        """Get any global config parameter."""
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        return self._plugin._global_config.get(name)

    def __setattr__(self, name: str, value: Any):
        """Set any global config parameter."""
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._plugin._update_config(**{name: value})

    def __getitem__(self, method_names: str) -> MethodConfigProxy:
        """
        Access per-method configuration.

        Args:
            method_names: Single method or comma-separated ('calculate,clear')
        """
        return MethodConfigProxy(self._plugin, method_names)


# ============================================================
# PLUGIN BASE
# ============================================================


class BasePlugin:
    """
    Base class for Switcher plugins with Pydantic configuration support.

    Plugins have two main hooks:

    - on_decore(switch, func, entry):
        Called once at decoration time. It can mutate entry.metadata.
    - wrap_handler(switch, entry, call_next):
        Called at wrapper-chain construction time.
        Returns a wrapper callable that must call call_next.

    Configuration:
        Subclasses can optionally define config_model (Pydantic BaseModel).
        If defined, automatic flags parsing is enabled for boolean fields.

    Examples:
        # Using flags
        plugin = LoggingPlugin(name='logger', flags='print,enabled')

        # Using kwargs
        plugin = LoggingPlugin(name='logger', print=True, enabled=True)

        # Runtime configuration
        plugin.configure.flags = 'log,time'
        plugin.configure['method'].flags = 'enabled:off'
    """

    config_model: Optional[Type[Any]] = None  # Subclasses can define Pydantic model

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        flags: Optional[str] = None,
        method_config: Optional[Dict[str, Any]] = None,
        **config: Any,
    ):
        """
        Initialize plugin with configuration.

        Args:
            name: Plugin instance name (default: class name)
            description: Plugin description
            flags: Flags string for boolean parameters ('flag1,flag2,flag3:off')
            method_config: Dict of per-method configurations
            **config: Additional config parameters
        """
        self.name = name or self.__class__.__name__
        self.description = description

        # Parse flags if provided
        if flags:
            parsed_flags = self._parse_flags(flags)
            config.update(parsed_flags)

        # Validate with Pydantic if config_model defined
        if self.config_model is not None:
            try:
                from pydantic import BaseModel

                if isinstance(self.config_model, type) and issubclass(self.config_model, BaseModel):
                    # Validate and extract config
                    validated = self.config_model(**config)
                    self._global_config = validated.model_dump(exclude={"methods"})
                else:
                    self._global_config = dict(config)
            except ImportError:
                # Pydantic not available, use dict
                self._global_config = dict(config)
        else:
            self._global_config = dict(config)

        self._handler_configs: Dict[str, Dict[str, Any]] = {}

        # Keep backward compatibility
        self.config = self._global_config

        # Process method_config if provided
        if method_config:
            self._parse_method_configs(method_config)

    def _parse_flags(self, flags: str) -> Dict[str, bool]:
        """
        Parse flags string into config dict.

        Automatically maps flags to boolean fields in config_model (if defined).

        Syntax:
            'flag1,flag2' → flag1=True, flag2=True
            'flag1:off,flag2' → flag1=False, flag2=True
        """
        result = {}

        # Get boolean fields from config_model if available
        bool_fields = set()
        if self.config_model is not None:
            try:
                from pydantic import BaseModel

                if isinstance(self.config_model, type) and issubclass(self.config_model, BaseModel):
                    bool_fields = {
                        name
                        for name, field_info in self.config_model.model_fields.items()
                        if field_info.annotation in (bool, Optional[bool])
                    }
            except (ImportError, AttributeError):
                pass

        # Parse flags
        for flag in flags.split(","):
            flag = flag.strip()
            if not flag:
                continue

            if ":off" in flag:
                field_name = flag.replace(":off", "").strip()
                # If config_model exists, only set if it's a valid field
                if not bool_fields or field_name in bool_fields:
                    result[field_name] = False
            else:
                # If config_model exists, only set if it's a valid field
                if not bool_fields or flag in bool_fields:
                    result[flag] = True

        return result

    def _parse_method_configs(self, method_config: Dict[str, Any]):
        """Parse method_config dict with support for strings, dicts, and Pydantic models."""
        for method_names, method_cfg in method_config.items():
            # Determine config type
            if isinstance(method_cfg, str):
                # Flags string → parse and merge with global
                parsed = self._parse_flags(method_cfg)
                merged = {**self._global_config, **parsed}
            elif isinstance(method_cfg, dict):
                # Dict → merge with global
                merged = {**self._global_config, **method_cfg}
            else:
                # Assume it's a Pydantic model or similar
                try:
                    merged = method_cfg.model_dump(exclude={"methods"})
                except AttributeError:
                    merged = dict(method_cfg) if hasattr(method_cfg, "__iter__") else {}

            # Support comma-separated method names
            for method_name in method_names.split(","):
                method_name = method_name.strip()
                if method_name:
                    self._handler_configs[method_name] = merged

    # ------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------
    def _update_config(
        self, *method_names: str, flags: Optional[str] = None, **config: Any
    ) -> None:
        """
        Internal method to update global or per-method configuration.

        Args:
            *method_names: If provided, update per-method config; otherwise update global
            flags: Flags string for boolean parameters
            **config: Config parameters to update
        """
        # Parse flags if provided
        if flags:
            parsed = self._parse_flags(flags)
            config.update(parsed)

        if not method_names:
            self._global_config.update(config)
            return

        for name in method_names:
            bucket = self._handler_configs.setdefault(name, {})
            bucket.update(config)

    @property
    def configure(self) -> ConfigureProxy:
        """
        Access configuration proxy for runtime config changes.

        Examples:
            plugin.configure.flags = 'enabled,time'
            plugin.configure.level = 'DEBUG'
            plugin.configure['method'].flags = 'enabled:off'
        """
        return ConfigureProxy(self)

    def get_config(self, method_name: Optional[str] = None) -> Dict[str, Any]:
        """Return merged configuration for the given method name."""
        merged = dict(self._global_config)
        if method_name and method_name in self._handler_configs:
            merged.update(self._handler_configs[method_name])
        return merged

    def is_enabled_for(self, method_name: Optional[str] = None) -> bool:
        """Determine whether the plugin is enabled for the given method."""
        cfg = self.get_config(method_name)
        enabled = cfg.get("enabled", True)
        return bool(enabled)

    def to_spec(self) -> _PluginSpec:
        """Return the specification needed to re-instantiate this plugin."""
        kwargs: Dict[str, Any] = dict(self.config)
        return _PluginSpec(self.__class__, kwargs, self.name)

    def on_decore(
        self,
        switch: "Switcher",
        func: Callable,
        entry: MethodEntry,
    ) -> None:
        """Decoration-time hook (default: no-op)."""
        return None

    def wrap_handler(
        self,
        switch: "Switcher",
        entry: MethodEntry,
        call_next: Callable,
    ) -> Callable:
        """Return a wrapper around call_next (default: identity wrapper)."""

        def wrapper(*args, **kwargs):
            return call_next(*args, **kwargs)

        return wrapper


# ============================================================
# SWITCH CALL PROXY
# ============================================================


class _SwitchCall:
    """
    A proxy object returned by Switcher when called with a string.

    It can act both as:
    - a decorator factory (when later called with a single callable)
    - a named/dotted-path dispatch handle (when later called with normal args)
    """

    def __init__(self, switch: "Switcher", selector: str):
        self._switch = switch
        self._selector = selector

    def __call__(self, *args, **kwargs):
        # Decorator usage: @switch("alias")
        if len(args) == 1 and callable(args[0]) and not kwargs:
            func = args[0]
            return self._switch._decorate(func, alias=self._selector)
        # Runtime dispatch usage: switch("name")(*args)
        return self._switch._dispatch_by_name(self._selector, *args, **kwargs)


# ============================================================
# SMART SWITCH
# ============================================================


class Switcher:
    """
    Switcher is a decorator + handler registry + plugin container.

    Usage patterns:

        # Create switcher with optional get() defaults
        switch = Switcher(
            "main",
            prefix="do_",
            get_default_handler=fallback_fn,
            get_use_smartasync=True
        )

        class My:
            main = switch

            @main
            def do_run(self, x):
                ...  # registered name: "run" because of prefix

            @main("special")
            def do_special(self, x):
                ...  # registered name: "special" (alias wins)

        # Handler retrieval and dispatch:
        handler = main.get('run')              # Get with defaults
        handler = main['run']                  # Dict-like access
        handler = main.get('run', use_smartasync=False)  # Override defaults

        result = main['run'](instance, 10)
    """

    _global_plugin_registry: Dict[str, Type[BasePlugin]] = {}

    @classmethod
    def register_plugin(cls, name: str, plugin_class: Type[BasePlugin]) -> None:
        """Register a plugin globally so it can be referenced by string name."""
        if not isinstance(plugin_class, type) or not issubclass(plugin_class, BasePlugin):
            raise TypeError("plugin_class must be a BasePlugin subclass")
        cls._global_plugin_registry[name] = plugin_class

    @classmethod
    def registered_plugins(cls) -> Dict[str, Type[BasePlugin]]:
        """Return the map of registered plugin names to their classes."""
        return dict(cls._global_plugin_registry)

    @extract_kwargs(get=True)
    def __init__(
        self,
        name: Optional[str] = None,
        *,
        prefix: Optional[str] = None,
        parent: Optional["Switcher"] = None,
        inherit_plugins: Optional[bool] = None,
        get_kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.prefix: str
        if prefix is None:
            self.prefix = parent.prefix if parent is not None else ""
        else:
            self.prefix = prefix
        self.parent: Optional["Switcher"] = None

        # Store get() method defaults
        self.get_kwargs = get_kwargs or {}

        self._local_plugins: List[BasePlugin] = []
        self._local_plugin_specs: List[_PluginSpec] = []
        self._plugins_by_name: Dict[str, BasePlugin] = {}  # For attribute access
        self._inherited_plugins: List[BasePlugin] = []
        self._inherited_plugin_specs: List[_PluginSpec] = []
        self._inherit_plugins: bool = True if inherit_plugins is None else bool(inherit_plugins)
        self._using_parent_plugins: bool = False
        self._children: Dict[str, "Switcher"] = {}
        self._methods: Dict[str, MethodEntry] = {}

        if parent is not None:
            parent.add_child(self)

    # --------------------------------------------------------
    # Handler Retrieval
    # --------------------------------------------------------
    def get(self, name: str, **options: Any) -> Callable:
        """
        Get handler by name with optional configuration.

        Supports dotted paths like "child.method" to access child switchers.

        Args:
            name: Handler name to retrieve (supports dotted paths)
            **options: Runtime options that override defaults:
                - default_handler: Fallback callable when method not found
                - use_smartasync: If True, wrap handler with smartasync

        Returns:
            The handler function (optionally wrapped with smartasync)

        Raises:
            NotImplementedError: If handler not found and no default_handler provided
        """
        opts = SmartOptions(incoming=options, defaults=self.get_kwargs)

        # Resolve dotted path if present (e.g., "child.method")
        node, method_name = self._resolve_path(name)

        # Look up the method entry
        entry = node._methods.get(method_name)

        if entry is None:
            # Handler not found - use default if provided
            default = getattr(opts, "default_handler", None)
            if default is not None:
                handler = default
            else:
                raise NotImplementedError(f"Method '{name}' not found")
        else:
            # Get the wrapped handler (with all plugins applied)
            handler = entry._wrapped  # type: ignore[attr-defined]

        # Wrap with smartasync if requested
        if getattr(opts, "use_smartasync", False):
            handler = smartasync(handler)

        return handler

    def __getitem__(self, name: str) -> Callable:
        """
        Dict-like access to handlers using defaults.

        Example:
            handler = sw['my_method']

        Args:
            name: Handler name to retrieve

        Returns:
            The handler function (using default get_kwargs configuration)
        """
        return self.get(name)

    # --------------------------------------------------------
    # Children
    # --------------------------------------------------------
    def add_child(self, child: Any, name: Optional[str] = None) -> None:
        """
        Attach a child switch or scan an arbitrary object for switchers.

        Args:
            child: Either a Switcher instance or any object exposing Switchers.
            name: Optional explicit child name (only used when child is a Switcher).
        """
        if isinstance(child, Switcher):
            self._attach_child_switcher(child, explicit_name=name)
            return

        discovered = list(self._iter_unbound_switchers(child))
        if not discovered:
            raise TypeError(
                f"Object {child!r} does not expose any Switcher instances without a parent"
            )
        for attr_name, switch in discovered:
            derived_name = switch.name or attr_name
            self._attach_child_switcher(switch, explicit_name=derived_name)

    def get_child(self, name: str) -> "Switcher":
        try:
            return self._children[name]
        except KeyError:
            raise KeyError(f"No child switch named {name!r} in {self!r}")

    def _attach_child_switcher(
        self, child: "Switcher", explicit_name: Optional[str] = None
    ) -> None:
        """Attach an actual Switcher instance as a child."""
        if child is self:
            raise ValueError("Cannot attach a switch to itself")
        if child.parent is not None and child.parent is not self:
            raise ValueError("Child already has a different parent")
        key = explicit_name or (child.name or "child")
        if key in self._children and self._children[key] is not child:
            raise ValueError(f"Child name collision: {key}")
        self._children[key] = child
        child.parent = self
        child._sync_parent_plugins()
        if child._inherit_plugins and child.parent is not None:
            child._using_parent_plugins = True
            child._local_plugins.clear()
            child._local_plugin_specs.clear()

    @staticmethod
    def _iter_unbound_switchers(source: Any) -> Iterator[Tuple[str, "Switcher"]]:
        """
        Yield (attribute_name, switcher) pairs for Switchers without a parent.
        """
        if source is None:
            return iter(())

        seen: Set[int] = set()

        def visit(mapping: Dict[str, Any]) -> Iterator[Tuple[str, "Switcher"]]:
            for attr_name, value in mapping.items():
                if attr_name.startswith("__") and attr_name.endswith("__"):
                    continue
                if isinstance(value, Switcher) and value.parent is None:
                    ident = id(value)
                    if ident in seen:
                        continue
                    seen.add(ident)
                    yield attr_name, value

        def generator() -> Iterator[Tuple[str, "Switcher"]]:
            instance_dict = getattr(source, "__dict__", None)
            if instance_dict:
                yield from visit(instance_dict)
            yield from visit(vars(type(source)))

        return generator()

    # --------------------------------------------------------
    # Plugin management
    # --------------------------------------------------------
    def plug(self, plugin: Any, **config: Any) -> "Switcher":
        """Attach a plugin instance, class, or registered name to this switch."""
        if isinstance(plugin, str):
            try:
                plugin_class = self._global_plugin_registry[plugin]
            except KeyError:
                available = ", ".join(sorted(self._global_plugin_registry.keys()))
                raise ValueError(
                    f"Unknown plugin name {plugin!r}. Registered plugins: {available or 'none'}"
                )
            init_kwargs = dict(config)
            init_kwargs.setdefault("name", plugin)
            p = plugin_class(**init_kwargs)
            spec = _PluginSpec(plugin_class, init_kwargs, p.name)
        elif isinstance(plugin, type) and issubclass(plugin, BasePlugin):
            init_kwargs = dict(config)
            p = plugin(**init_kwargs)
            spec = _PluginSpec(plugin, init_kwargs, p.name)
        elif isinstance(plugin, BasePlugin):
            p = plugin
            p.config.update(config)
            spec = p.to_spec()
        else:
            raise TypeError("plugin must be BasePlugin subclass or instance")
        if self._using_parent_plugins:
            self._using_parent_plugins = False
            self._inherit_plugins = False
            self._local_plugins.clear()
            self._local_plugin_specs.clear()
            self._plugins_by_name.clear()
        self._local_plugins.append(p)
        self._local_plugin_specs.append(spec)
        # Store plugin by name for attribute access (sw.logging, etc.)
        self._plugins_by_name[p.name] = p
        return self

    def iter_plugins(self) -> List[BasePlugin]:
        """Return ordered list of active plugins for this switch."""
        if self._using_parent_plugins:
            return list(self._inherited_plugins)
        return list(self._local_plugins)

    def iter_plugin_specs(self) -> List[_PluginSpec]:
        """Return ordered list of plugin specifications."""
        source = (
            self._inherited_plugin_specs if self._using_parent_plugins else self._local_plugin_specs
        )
        return [spec.clone() for spec in source]

    def plugin(self, name: str) -> Optional[BasePlugin]:
        """
        Get a plugin by name.

        Args:
            name: The plugin name to search for

        Returns:
            The plugin instance if found, None otherwise

        Example:
            sw = Switcher().plug("logging", mode="silent")
            logger = sw.plugin("logging")
            history = logger.history()
        """
        for p in self.iter_plugins():
            if p.name == name:
                return p
        return None

    def __getattr__(self, name: str) -> BasePlugin:
        """
        Dynamic plugin access by attribute name.

        Allows accessing any attached plugin as an attribute.
        All plugins are treated uniformly - no special cases.

        Args:
            name: Plugin name to search for

        Returns:
            The plugin instance if found

        Raises:
            AttributeError: If no plugin with that name exists

        Example:
            sw = Switcher().plug("logging", mode="silent")
            history = sw.logging.history()
        """
        plugin = self.plugin(name)
        if plugin is not None:
            return plugin

        # Not found - raise AttributeError
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}' "
            f"and no plugin named '{name}' is attached"
        )

    def use_parent_plugins(self) -> None:
        """Drop local plugins and reuse the parent's plugin stack."""
        if self.parent is None:
            raise ValueError("This switch has no parent to inherit plugins from")
        self._inherit_plugins = True
        self._sync_parent_plugins()
        self._using_parent_plugins = True
        self._local_plugins.clear()
        self._local_plugin_specs.clear()

    def copy_plugins_from_parent(self) -> None:
        """Copy the parent's plugin stack into local plugins."""
        if self.parent is None:
            raise ValueError("This switch has no parent to copy plugins from")
        self._sync_parent_plugins()
        self._inherit_plugins = False
        self._using_parent_plugins = False
        self._local_plugin_specs = [spec.clone() for spec in self._inherited_plugin_specs]
        self._local_plugins = [spec.instantiate() for spec in self._local_plugin_specs]

    # --------------------------------------------------------
    # Plugin inheritance sync
    # --------------------------------------------------------
    def _sync_parent_plugins(self) -> None:
        if self.parent is None:
            self._inherited_plugin_specs = []
            self._inherited_plugins = []
            return
        parent_specs = self.parent.iter_plugin_specs()
        self._inherited_plugin_specs = [spec.clone() for spec in parent_specs]
        self._inherited_plugins = [spec.instantiate() for spec in self._inherited_plugin_specs]

    # --------------------------------------------------------
    # Name normalization & collision detection
    # --------------------------------------------------------
    def _normalize_name(self, func_name: str, alias: Optional[str]) -> str:
        if alias:
            name = alias
        elif self.prefix and func_name.startswith(self.prefix):
            name = func_name[len(self.prefix) :]
        else:
            name = func_name
        if name in self._methods:
            raise ValueError(
                f"Method name collision in switch {self.name!r}: {name!r} already registered"
            )
        return name

    # --------------------------------------------------------
    # Decoration
    # --------------------------------------------------------
    def _decorate(
        self,
        func: Callable,
        *,
        alias: Optional[str] = None,
    ) -> Callable:
        logical_name = self._normalize_name(func.__name__, alias=alias)

        entry = MethodEntry(
            name=logical_name,
            func=func,
            switch=self,
            plugins=[p.name for p in self.iter_plugins()],
            metadata={},
        )

        # Run decoration-time plugin hooks (they may mutate entry.func)
        for plugin in self.iter_plugins():
            plugin.on_decore(self, func, entry)

        base_callable = entry.func

        # Build wrapper chain
        wrapped = base_callable
        for plugin in reversed(self.iter_plugins()):
            next_layer = wrapped

            def make_layer(plg: BasePlugin, call_next: Callable) -> Callable:
                plugin_name = plg.name
                entry_name = entry.name
                wrapped_call = plg.wrap_handler(self, entry, call_next)

                def layer(*args, **kwargs):
                    if hasattr(plg, "is_enabled_for") and not plg.is_enabled_for(entry_name):
                        return call_next(*args, **kwargs)
                    instance = args[0] if args else None
                    if not self.is_plugin_enabled(instance, entry_name, plugin_name):
                        return call_next(*args, **kwargs)
                    return wrapped_call(*args, **kwargs)

                return layer

            wrapped = make_layer(plugin, next_layer)

        # Store metadata on wrapped function for debugging
        setattr(wrapped, "__smartswitch_entry__", entry)
        # Also keep a reference to the final wrapped callable
        entry._wrapped = wrapped  # type: ignore[attr-defined]

        # Save in registry
        self._methods[logical_name] = entry

        return wrapped

    # --------------------------------------------------------
    # __call__ - decorator only
    # --------------------------------------------------------
    def __call__(self, *args, **kwargs):
        """
        Decorator usage only:

        1) As a plain decorator: @switch
           -> switch(func)

        2) As a decorator factory with alias:
           @switch("alias")
           -> returns decorator that registers func with given alias

        For handler retrieval, use:
        - sw.get('name', **options) - with runtime options
        - sw['name'] - using default options
        """
        # CASE 1: Direct decorator - @switch
        if len(args) == 1 and callable(args[0]) and not kwargs:
            func = args[0]
            return self._decorate(func)

        # CASE 2: Decorator factory with alias - @switch("alias")
        if len(args) == 1 and isinstance(args[0], str) and not kwargs:
            alias = args[0]

            def decorator(func: Callable) -> Callable:
                return self._decorate(func, alias=alias)

            return decorator

        raise TypeError(
            "Switcher() supports only decorator usage:\n"
            "  - Direct: @switch\n"
            "  - With alias: @switch('alias')\n"
            "For handler retrieval, use sw.get('name') or sw['name']"
        )

    # --------------------------------------------------------
    # Plugin activation / runtime data
    # --------------------------------------------------------
    @staticmethod
    def _activation_key(instance: Any, method_name: str, plugin_name: str) -> Tuple[int, str, str]:
        instance_id = id(instance) if instance is not None else 0
        return (instance_id, method_name, plugin_name)

    def set_plugin_enabled(
        self,
        instance: Any,
        method_name: str,
        plugin_name: str,
        enabled: bool = True,
    ) -> None:
        m = _get_activation_map()
        m[self._activation_key(instance, method_name, plugin_name)] = enabled

    def is_plugin_enabled(
        self,
        instance: Any,
        method_name: str,
        plugin_name: str,
    ) -> bool:
        m = _get_activation_map()
        key = self._activation_key(instance, method_name, plugin_name)
        value = m.get(key, None)
        if value is None:
            return True
        return bool(value)

    @staticmethod
    def _runtime_key(instance: Any, method_name: str, plugin_name: str) -> Tuple[int, str, str]:
        instance_id = id(instance) if instance is not None else 0
        return (instance_id, method_name, plugin_name)

    def set_runtime_data(
        self,
        instance: Any,
        method_name: str,
        plugin_name: str,
        key: str,
        value: Any,
    ) -> None:
        m = _get_runtime_map()
        slot = m.setdefault(self._runtime_key(instance, method_name, plugin_name), {})
        slot[key] = value

    def get_runtime_data(
        self,
        instance: Any,
        method_name: str,
        plugin_name: str,
        key: str,
        default: Any = None,
    ) -> Any:
        m = _get_runtime_map()
        slot = m.get(self._runtime_key(instance, method_name, plugin_name), {})
        return slot.get(key, default)

    # --------------------------------------------------------
    # Dispatch helpers
    # --------------------------------------------------------
    def _resolve_path(self, selector: str) -> Tuple["Switcher", str]:
        """
        Resolve a dotted path "a.b.c.method" into (switch, method_name).

        If there are no dots, returns (self, selector).
        """
        if "." not in selector:
            return self, selector
        parts = selector.split(".")
        node: Switcher = self
        for seg in parts[:-1]:
            node = node.get_child(seg)
        return node, parts[-1]

    def _dispatch_by_name(self, selector: str, *args, **kwargs):
        node, method_name = self._resolve_path(selector)
        try:
            entry = node._methods[method_name]
        except KeyError:
            raise KeyError(f"Unknown method {method_name!r} for selector {selector!r}")
        # Use the wrapped function we built at decoration time
        wrapped = getattr(entry.func, "__wrapped__", None)
        # We did not attach __wrapped__, so use the final wrapper chain we created:
        # we stored only the original func; we must reconstruct a bound wrapper.
        # Instead, we can re-build the wrapper chain when decorating and store
        # the final wrapper inside metadata; let's do that from now on.
        wrapped = getattr(entry, "_wrapped", None)
        if wrapped is None:
            # As a fallback (should not happen if _decorate sets _wrapped):
            wrapped = entry.func
        return wrapped(*args, **kwargs)

    # --------------------------------------------------------
    # Introspection
    # --------------------------------------------------------
    def describe(self) -> Dict[str, Any]:
        """Return a dictionary describing this switch and its children."""
        return {
            "name": self.name,
            "prefix": self.prefix,
            "plugins": [p.name for p in self.iter_plugins()],
            "methods": {
                name: {
                    "plugins": entry.plugins,
                    "metadata_keys": list(entry.metadata.keys()),
                }
                for name, entry in self._methods.items()
            },
            "children": {name: child.describe() for name, child in self._children.items()},
        }
