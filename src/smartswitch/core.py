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
# PLUGIN BASE
# ============================================================


class BasePlugin:
    """
    Base class for Switcher plugins.

    Plugins have two main hooks:

    - on_decore(switch, func, entry):
        Called once at decoration time. It can mutate entry.metadata.
    - wrap_handler(switch, entry, call_next):
        Called at wrapper-chain construction time.
        Returns a wrapper callable that must call call_next.
    """

    def __init__(self, name: Optional[str] = None, **config: Any):
        self.name = name or self.__class__.__name__
        self._global_config: Dict[str, Any] = dict(config)
        self._handler_configs: Dict[str, Dict[str, Any]] = {}
        # Keep backward compatibility for plugins that accessed self.config directly
        self.config = self._global_config

    # ------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------
    def configure(self, *method_names: str, **config: Any) -> None:
        """Update global or per-method configuration.

        Without method names, updates global config; otherwise stores per-method overrides.
        """
        if not method_names:
            self._global_config.update(config)
            return
        for name in method_names:
            bucket = self._handler_configs.setdefault(name, {})
            bucket.update(config)

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
    Switcher is a decorator + dispatcher + plugin container.

    Usage patterns:

        switch = Switcher("main", prefix="do_")

        class My:
            main = switch

            @main
            def do_run(self, x):
                ...  # registered name: "run" because of prefix

            @main("special")
            def do_special(self, x):
                ...  # registered name: "special" (alias wins)

        # Named dispatch:
        main("run")(instance, 10)
        main("special")(instance, 20)

        result = main("run")(instance, 10)
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

    def __init__(
        self,
        name: Optional[str] = None,
        *,
        prefix: Optional[str] = None,
        parent: Optional["Switcher"] = None,
        inherit_plugins: Optional[bool] = None,
    ):
        self.name = name
        self.prefix: str
        if prefix is None:
            self.prefix = parent.prefix if parent is not None else ""
        else:
            self.prefix = prefix
        self.parent: Optional["Switcher"] = None

        self._local_plugins: List[BasePlugin] = []
        self._local_plugin_specs: List[_PluginSpec] = []
        self._inherited_plugins: List[BasePlugin] = []
        self._inherited_plugin_specs: List[_PluginSpec] = []
        self._inherit_plugins: bool = True if inherit_plugins is None else bool(inherit_plugins)
        self._using_parent_plugins: bool = False
        self._children: Dict[str, "Switcher"] = {}
        self._methods: Dict[str, MethodEntry] = {}

        if parent is not None:
            parent.add_child(self)

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
        self._local_plugins.append(p)
        self._local_plugin_specs.append(spec)
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
    # __call__ - decorator or dispatch
    # --------------------------------------------------------
    def __call__(self, *args, **kwargs):
        """
        Overloaded behavior:

        1) As a plain decorator: @switch
           -> switch(func)

        2) As a decorator factory with alias:
           @switch("alias")

        3) As a named/dotted-path dispatch handle:
           switch("name")(*args)
           switch("a.b.name")(*args)
        """
        # CASE 1: @switch
        if len(args) == 1 and callable(args[0]) and not kwargs:
            func = args[0]
            return self._decorate(func)

        # CASE 2/3: first arg is string -> alias OR named dispatch
        if len(args) >= 1 and isinstance(args[0], str):
            selector = args[0]
            if len(args) == 1 and not kwargs:
                # Named/dotted path dispatch handle: switch("name")
                return _SwitchCall(self, selector)

            raise TypeError(
                "Switcher selector usage only supports a single string argument. "
                "Call the returned handle to execute handlers."
            )

        raise TypeError(
            "Switcher no longer supports implicit dispatch. "
            "Call switch('name') to get a callable handler."
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
