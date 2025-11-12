"""
SmartSwitch - Intelligent rule-based function dispatch for Python.

Optimized version with ~3x performance improvement over naive implementation.
"""

import inspect
import json
import logging
import time
from functools import partial, wraps
from typing import Any, Union, get_args, get_origin


class BoundSwitcher:
    """
    A bound version of Switcher that automatically binds 'self' to retrieved handlers.
    Created when accessing a Switcher instance as a class attribute.
    """

    __slots__ = ("_switcher", "_instance")

    def __init__(self, switcher, instance):
        self._switcher = switcher
        self._instance = instance

    def __getattr__(self, name):
        """Delegate attribute access to the underlying Switcher."""
        return getattr(self._switcher, name)

    def __call__(self, name):
        """
        Get a handler by name and bind it to the instance.
        Supports dot notation for hierarchical navigation.

        Args:
            name: Handler function name (supports dot notation like 'child.handler')

        Returns:
            Bound method ready to call without passing self
        """
        # Check for dot notation (hierarchical navigation)
        if "." in name:
            # Delegate to underlying Switcher's dot notation support
            # which returns the handler, then bind it
            handler = self._switcher(name)
            # If it's already a HandlerOrDecorator, extract the actual function
            if hasattr(handler, "__self__"):
                # Already bound
                return handler
            # Bind to instance
            bound = partial(handler, self._instance)
            # Preserve __wrapped__ if available
            if hasattr(handler, "__wrapped__"):
                bound.__wrapped__ = handler.__wrapped__
            return bound

        # Standard lookup
        func = self._switcher._handlers[name]

        # Apply logging wrapper if enabled
        logged_func = self._switcher._wrap_with_logging(name, func)

        bound = partial(logged_func, self._instance)
        # Add __wrapped__ attribute for introspection
        bound.__wrapped__ = func
        return bound


class Switcher:
    """
    Intelligent function dispatch based on type and value rules.

    Supports three modes:
    1. Dispatch by name: switch("handler_name")
    2. Automatic dispatch: switch()(args) - chooses handler by rules
    3. Both: register with name, dispatch automatically

    Optimizations applied:
    - Cached signature inspection (done once per function)
    - Manual kwargs building (no expensive bind_partial)
    - Pre-compiled type checkers
    - __slots__ for reduced memory overhead
    """

    __slots__ = (
        "name",
        "description",
        "prefix",
        "_parent",
        "_children",
        "_handlers",
        "_rules",
        "_default_handler",
        "_param_names_cache",
        "_plugins",
        "_plugin_registry",
        "_log_mode",
        "_log_default",
        "_log_handlers",
        "_log_history",
        "_log_max_history",
        "_log_file",
        "_logger",
    )

    # Global plugin registry - shared across all Switcher instances
    _global_plugin_registry: dict[str, type] = {}

    @classmethod
    def register_plugin(cls, name: str, plugin_class: type) -> None:
        """
        Register a plugin globally by name.

        This allows external plugins to register themselves so they can be
        loaded by name using plug(name) without explicit imports.

        Args:
            name: Plugin name for registration (e.g., "redis", "mongodb")
            plugin_class: Plugin class (not instance) to register

        Example:
            >>> from smartswitch import Switcher, BasePlugin
            >>>
            >>> class RedisPlugin(BasePlugin):
            ...     def _wrap_handler(self, func, switcher):
            ...         # ... implementation ...
            ...         return func
            >>>
            >>> # Register plugin globally
            >>> Switcher.register_plugin("redis", RedisPlugin)
            >>>
            >>> # Now can be used anywhere with just the name
            >>> sw = Switcher().plug("redis")
        """
        cls._global_plugin_registry[name] = plugin_class

    def __init__(
        self,
        name: str = "default",
        description: str | None = None,
        prefix: str | None = None,
        parent: "Switcher | None" = None,
    ):
        """
        Initialize a new Switcher.

        Args:
            name: Optional name for this switch (for debugging)
            description: Optional description for documentation/introspection
            prefix: If set, auto-derive handler names by removing this prefix
                    from decorated function names
            parent: Optional parent Switcher for hierarchical API structure
        """
        self.name = name
        self.description = description
        self.prefix = prefix
        self._parent = None
        self._children = set()
        self._handlers = {}  # name -> function mapping
        self._rules = []  # list of (matcher, function) tuples
        self._default_handler = None  # default catch-all handler
        self._param_names_cache = {}  # function -> param names cache
        self._plugins = []  # List of plugins
        self._plugin_registry = {}  # name -> plugin instance mapping

        # Logging support (will be deprecated in favor of LoggingPlugin)
        self._log_mode = None  # None, 'log', 'silent', 'both'
        self._log_default = {}  # Default config: {'before': bool, 'after': bool, 'time': bool}
        self._log_handlers = {}  # {handler_name: config_dict or False}
        self._log_history = []  # List of log entries
        self._log_max_history = 1000  # Max history size
        self._log_file = None  # Optional log file path
        self._logger = None  # logging.Logger instance

        # Set parent after initialization (triggers property setter)
        if parent is not None:
            self.parent = parent

    def plug(self, plugin, name=None, **kwargs):
        """
        Add a plugin to this Switcher.

        Plugins extend Switcher functionality by wrapping handlers during registration.
        Standard plugins can be specified by name (string), external plugins by instance.

        Args:
            plugin: Either a plugin name (str) for standard plugins,
                   or a plugin instance for external plugins
            name: Custom name for plugin access (optional, uses plugin's default if not provided)
            **kwargs: Configuration parameters (only for string names)

        Returns:
            Self for method chaining

        Examples:
            Standard plugins (by name):

            >>> sw = Switcher()
            >>> sw.plug('logging', mode='silent', time=True)
            <Switcher...>
            >>> sw.logger.get_log_history()  # Access via default name 'logger'

            Custom plugin names:

            >>> sw.plug('logging', name='mylog', mode='silent')
            >>> sw.mylog.get_log_history()  # Access via custom name

            External plugins (by class):

            >>> from smartasync import SmartAsyncPlugin
            >>> sw.plug(SmartAsyncPlugin())
            <Switcher...>

            Chaining:

            >>> sw = (Switcher(name="api")
            ...       .plug('logging', mode='log')
            ...       .plug('typerule')
            ...       .plug(SmartAsyncPlugin()))
        """
        if isinstance(plugin, str):
            # Lookup standard plugin by name
            plugin_name = plugin
            plugin = self._get_standard_plugin(plugin, **kwargs)
        else:
            plugin_name = None

        self._plugins.append(plugin)

        # Register plugin by name for __getattr__ access
        if name:
            # Use custom name
            self._plugin_registry[name] = plugin
        elif hasattr(plugin, "plugin_name"):
            # Use plugin's default name
            self._plugin_registry[plugin.plugin_name] = plugin
        elif plugin_name:
            # Fallback: use the string name used to load it
            self._plugin_registry[plugin_name] = plugin

        return self  # For chaining

    def _get_standard_plugin(self, name: str, **kwargs):
        """
        Lookup and instantiate a plugin by name from global registry.

        Args:
            name: Plugin name (e.g., 'logging', 'pydantic', or any registered plugin)
            **kwargs: Plugin configuration parameters

        Returns:
            Plugin instance

        Raises:
            ValueError: If plugin name is not registered
        """
        if name not in self._global_plugin_registry:
            available = ", ".join(sorted(self._global_plugin_registry.keys()))
            raise ValueError(
                f"Unknown plugin: '{name}'. "
                f"Available plugins: {available}\n"
                f"External plugins can be registered with: "
                f"Switcher.register_plugin(name, PluginClass)"
            )

        plugin_class = self._global_plugin_registry[name]
        return plugin_class(**kwargs)

    def __getattr__(self, name: str):
        """
        Enable plugin access via attribute syntax.

        This allows accessing plugins by name: sw.logger.get_log_history()

        Args:
            name: Attribute name (plugin name)

        Returns:
            Plugin instance if registered

        Raises:
            AttributeError: If attribute or plugin not found

        Examples:
            >>> sw = Switcher().plug('logging', mode='silent')
            >>> sw.logger.get_log_history()  # Access plugin by default name
            []

            >>> sw.plug('logging', name='mylog', mode='silent')
            >>> sw.mylog.get_log_history()  # Access plugin by custom name
            []
        """
        # Check if it's a registered plugin
        if name in self._plugin_registry:
            return self._plugin_registry[name]

        # Otherwise raise standard AttributeError
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __call__(
        self,
        arg: Any = None,
        *,
        typerule: dict[str, type] | None = None,
        valrule: Any = None,
    ) -> Any:
        """
        Multi-purpose call method supporting different invocation patterns.

        Patterns:
        1. @switch                    -> register as default handler
        2. @switch('alias')           -> register with custom name
        3. @switch(typerule=..., valrule=...) -> register with rules
        4. switch("name")            -> get handler by name
        5. switch()                  -> get dispatcher function

        Args:
            arg: Function to decorate, handler name, or None for dispatcher
            typerule: Dict mapping parameter names to expected types
            valrule: Callable that receives **kwargs and returns bool

        Returns:
            Decorated function, handler, or dispatcher depending on usage
        """
        # Case 1: @switch (decorator without parameters - default handler)
        if callable(arg) and typerule is None and valrule is None:
            # Derive handler name (with optional prefix stripping)
            if self.prefix and arg.__name__.startswith(self.prefix):
                handler_name = arg.__name__[len(self.prefix) :]
            else:
                handler_name = arg.__name__

            # Check for duplicates
            if handler_name in self._handlers:
                existing = self._handlers[handler_name]
                raise ValueError(
                    f"Handler '{handler_name}' already taken by function '{existing.__name__}'"
                )

            # Initialize plugin metadata dictionary
            if not hasattr(arg, "_plugin_meta"):
                arg._plugin_meta = {}

            # Apply plugins
            wrapped = arg
            for plugin in self._plugins:
                # Call on_decorate hook first (notification)
                plugin.on_decorate(arg, self)
                # Then wrap the function
                wrapped = plugin.wrap(wrapped, self)

            self._handlers[handler_name] = wrapped
            self._default_handler = wrapped
            return wrapped

        # Case 2: @switch('alias') - register with custom name OR lookup
        if isinstance(arg, str) and typerule is None and valrule is None:
            # Check for dot notation (hierarchical navigation)
            if "." in arg:
                parts = arg.split(".", 1)
                child_name = parts[0]
                remaining = parts[1]

                # Find child by name
                for child in self._children:
                    if child.name == child_name:
                        # Recursively navigate
                        return child(remaining)

                # Child not found
                raise KeyError(f"Child Switcher '{child_name}' not found")

            # No dot notation - standard behavior
            # If handler exists, check if being used as decorator or lookup
            if arg in self._handlers:
                handler = self._handlers[arg]

                # Apply logging wrapper if enabled
                logged_handler = self._wrap_with_logging(arg, handler)

                # Create a wrapper that can be used both ways
                class HandlerOrDecorator:
                    def __call__(self, *args, **kwargs):
                        # If called with a function as first arg and it's callable,
                        # assume decorator usage
                        if len(args) == 1 and callable(args[0]) and not kwargs:
                            # Check if it looks like it's being used as decorator
                            # (single callable argument, no other args)
                            import inspect

                            if inspect.isfunction(args[0]) or inspect.ismethod(args[0]):
                                raise ValueError(f"Alias '{arg}' is already registered")
                        # Normal function call
                        return logged_handler(*args, **kwargs)

                wrapper = HandlerOrDecorator()
                # Add __wrapped__ attribute for introspection tools
                wrapper.__wrapped__ = handler
                return wrapper

            # Not found, return decorator for registration
            def decorator(func):
                self._handlers[arg] = func
                return func

            return decorator

        # Case 3: @switch(typerule=..., valrule=...) - returns decorator
        if typerule is not None or valrule is not None:
            # Detect valrule calling convention
            valrule_takes_dict = False
            valrule_needs_unpack = False  # True for **kw style
            if valrule is not None:
                valrule_sig = inspect.signature(valrule)
                params = valrule_sig.parameters

                # Compact dict syntax comes in two forms:
                # 1. Single positional param named 'kw', 'kwargs', or 'args'
                #    e.g., lambda kw: kw['mode'] == 'test'
                #    Call with: valrule(args_dict)
                # 2. VAR_KEYWORD parameter (**kw)
                #    e.g., lambda **kw: kw.get('mode') == 'test'
                #    Call with: valrule(**args_dict)

                positional_params = [
                    name
                    for name, p in params.items()
                    if p.kind
                    not in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
                ]
                has_var_keyword = any(
                    p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
                )

                if len(positional_params) == 1 and list(positional_params)[0] in (
                    "kw",
                    "kwargs",
                    "args",
                ):
                    valrule_takes_dict = True
                    valrule_needs_unpack = False
                elif has_var_keyword and len(positional_params) == 0:
                    valrule_takes_dict = True
                    valrule_needs_unpack = True

            def decorator(func):
                # OPTIMIZATION: Cache signature once
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                self._param_names_cache[func] = param_names

                # OPTIMIZATION: Pre-compile type checks
                if typerule:
                    type_checks = self._compile_type_checks(typerule, param_names)
                else:
                    type_checks = None

                # OPTIMIZATION: Optimized matcher - no bind_partial
                def matches(*a, **kw):
                    # Build args dict manually (much faster than bind_partial)
                    args_dict = {}
                    for i, name in enumerate(param_names):
                        if i < len(a):
                            args_dict[name] = a[i]
                        elif name in kw:
                            args_dict[name] = kw[name]

                    # Type checks
                    if type_checks:
                        for name, checker in type_checks:
                            if name in args_dict and not checker(args_dict[name]):
                                return False

                    # Value rule - support both calling conventions
                    if valrule:
                        if valrule_takes_dict:
                            # Compact syntax
                            if valrule_needs_unpack:
                                # lambda **kw: kw.get('x') > 10
                                if not valrule(**args_dict):
                                    return False
                            else:
                                # lambda kw: kw['x'] > 10
                                if not valrule(args_dict):
                                    return False
                        else:
                            # Expanded syntax: lambda x, y: x > 10
                            if not valrule(**args_dict):
                                return False

                    return True

                self._rules.append((matches, func))
                # Register by name so it can be retrieved with sw('name')
                self._handlers[func.__name__] = func
                return func

            return decorator

        # Case 4: switch() - invoker
        if arg is None:

            def invoker(*a, **kw):
                # Check specific rules first
                for cond, func in self._rules:
                    if cond(*a, **kw):
                        return func(*a, **kw)
                # Check default last
                if self._default_handler:
                    return self._default_handler(*a, **kw)
                raise ValueError(f"No rule matched for {a}, {kw}")

            return invoker

        raise TypeError("Switcher.__call__ expects callable, str, or None")

    def __get__(self, instance: Any, owner: type | None = None) -> "Switcher | BoundSwitcher":
        """
        Descriptor protocol support for automatic method binding.

        When a Switcher is accessed as a class attribute, this returns
        a BoundSwitcher that automatically binds 'self' to retrieved handlers.

        Args:
            instance: The instance accessing this descriptor
            owner: The class owning this descriptor

        Returns:
            BoundSwitcher if accessed from instance, self if accessed from class
        """
        if instance is None:
            # Accessed from class, return the switcher itself
            return self
        # Accessed from instance, return bound version
        return BoundSwitcher(self, instance)

    def _compile_type_checks(self, typerule, param_names):
        """
        Pre-compile type checkers for faster runtime evaluation.

        Args:
            typerule: Dict mapping parameter names to types
            param_names: List of parameter names from function signature

        Returns:
            List of (param_name, checker_function) tuples
        """
        checks = []
        for name, hint in typerule.items():
            if name not in param_names:
                continue

            # Create optimized checker for this type
            checker = self._make_type_checker(hint)
            checks.append((name, checker))

        return checks

    def _make_type_checker(self, hint):
        """
        Create an optimized type checking function.

        Args:
            hint: Type hint to check against

        Returns:
            Function that takes a value and returns bool
        """
        # Fast path for Any
        if hint is Any:
            return lambda val: True

        origin = get_origin(hint)

        # Union types (e.g., int | str)
        if origin is Union:
            args = get_args(hint)
            # Pre-compile checkers for each union member
            checkers = [self._make_type_checker(t) for t in args]
            return lambda val: any(c(val) for c in checkers)

        # Simple type check
        return lambda val: isinstance(val, hint)

    def entries(self):
        """
        List all registered handler names.

        Returns:
            List of handler names registered in this Switcher
        """
        return list(self._handlers.keys())

    @property
    def parent(self) -> "Switcher | None":
        """
        Get the parent Switcher.

        Returns:
            Parent Switcher instance or None if no parent
        """
        return self._parent

    @parent.setter
    def parent(self, value: "Switcher | None"):
        """
        Set the parent Switcher with automatic bidirectional registration.

        When setting a parent:
        1. Unregisters from old parent (if any)
        2. Sets new parent
        3. Registers with new parent's children

        Args:
            value: Parent Switcher instance or None to unset parent
        """
        # Unregister from old parent
        if self._parent is not None:
            self._parent._children.discard(self)

        # Set new parent
        self._parent = value

        # Register with new parent
        if value is not None:
            value._children.add(self)

    @property
    def children(self) -> set["Switcher"]:
        """
        Get all child Switchers.

        Returns:
            Set of child Switcher instances
        """
        return self._children.copy()

    def add_child(self, switcher: "Switcher") -> "Switcher":
        """
        Add a child Switcher and return it.

        This also sets this Switcher as the child's parent.
        Returns the child so it can be used as a decorator.

        Args:
            switcher: Child Switcher to add

        Returns:
            The child Switcher (for chaining/assignment)

        Raises:
            TypeError: If switcher is not a Switcher instance
        """
        if not isinstance(switcher, Switcher):
            raise TypeError(f"Expected Switcher instance, got {type(switcher)}")

        # Setting parent will automatically add to children via property setter
        switcher.parent = self
        return switcher

    def add(self, switcher: "Switcher") -> "Switcher":
        """
        Alias for add_child(). Add a child Switcher and return it.

        This is a shorter, more convenient alias for add_child().

        Args:
            switcher: Child Switcher to add

        Returns:
            The child Switcher (for chaining/assignment)
        """
        return self.add_child(switcher)

    def remove_child(self, switcher: "Switcher"):
        """
        Remove a child Switcher.

        This also unsets the child's parent.

        Args:
            switcher: Child Switcher to remove
        """
        if switcher in self._children:
            # Setting parent to None will automatically remove from children
            switcher.parent = None

    def enable_log(
        self,
        *handler_names: str,
        mode: str = "silent",
        before: bool = True,
        after: bool = True,
        time: bool = True,
        log_file: str | None = None,
        log_format: str = "json",
        max_history: int = 1000,
    ):
        """
        Enable logging for handlers.

        Args:
            *handler_names: Handler names to enable logging for. If empty, enables for all.
            mode: Logging mode - 'log' (immediate logging), 'silent' (history only),
                  'both' (logging + history). Default: 'silent'
            before: Log before handler execution (args, kwargs)
            after: Log after handler execution (result or exception)
            time: Measure and log execution time
            log_file: Optional path to log file (JSONL format)
            log_format: Log format - 'json' or 'jsonl' (same as 'json')
            max_history: Maximum number of entries in history (default: 1000)
        """
        # Validate mode
        if mode not in ("log", "silent", "both"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'log', 'silent', or 'both'")

        # Set global log mode
        self._log_mode = mode
        self._log_max_history = max_history
        self._log_file = log_file

        # Create logger if needed
        if mode in ("log", "both") and self._logger is None:
            self._logger = logging.getLogger(f"smartswitch.{self.name}")
            if not self._logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(
                    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                )
                self._logger.addHandler(handler)
                self._logger.setLevel(logging.INFO)

        # Set default config
        self._log_default = {"before": before, "after": after, "time": time}

        # If handler names specified, set their config
        if handler_names:
            config = {"before": before, "after": after, "time": time}
            for name in handler_names:
                self._log_handlers[name] = config
        # If no names, clear handler-specific configs (all use default)
        else:
            self._log_handlers.clear()

    def disable_log(self, *handler_names: str):
        """
        Disable logging for specific handlers or globally.

        Args:
            *handler_names: Handler names to disable logging for.
                           If empty, disables logging globally.
        """
        if handler_names:
            # Disable specific handlers
            for name in handler_names:
                self._log_handlers[name] = False
        else:
            # Disable globally
            self._log_mode = None
            self._log_default.clear()
            self._log_handlers.clear()

    def _get_log_config(self, handler_name: str) -> dict | None:
        """
        Get the effective logging configuration for a handler.

        Args:
            handler_name: Name of the handler

        Returns:
            Config dict with 'before', 'after', 'time' keys, or None if logging disabled
        """
        # No logging enabled
        if self._log_mode is None:
            return None

        # Check if handler explicitly disabled
        if handler_name in self._log_handlers and self._log_handlers[handler_name] is False:
            return None

        # Check if handler has specific config
        if handler_name in self._log_handlers:
            return self._log_handlers[handler_name]

        # If _log_handlers has entries that are dicts (not False),
        # it means specific handlers were configured, so other handlers shouldn't be logged
        has_specific_configs = any(isinstance(v, dict) for v in self._log_handlers.values())
        if has_specific_configs:
            return None

        # Use default config
        return self._log_default if self._log_default else None

    def _wrap_with_logging(self, handler_name: str, func):
        """
        Wrap a handler function with logging.

        Args:
            handler_name: Name of the handler
            func: Function to wrap

        Returns:
            Wrapped function that logs calls
        """
        config = self._get_log_config(handler_name)
        if config is None:
            return func

        @wraps(func)
        def logged_wrapper(*args, **kwargs):
            # Prepare log entry
            entry = {
                "handler": handler_name,
                "switcher": self.name,
                "timestamp": time.time(),
                "args": args,
                "kwargs": kwargs,
            }

            # Log before if enabled
            if config.get("before") and self._log_mode in ("log", "both"):
                if self._logger:
                    self._logger.info(f"Calling {handler_name} with args={args}, kwargs={kwargs}")

            # Execute handler and measure time
            start_time = time.time() if config.get("time") else None
            exception = None
            result = None

            try:
                result = func(*args, **kwargs)
                entry["result"] = result
            except Exception as e:
                exception = e
                entry["exception"] = {
                    "type": type(e).__name__,
                    "message": str(e),
                }
                raise
            finally:
                # Add elapsed time if enabled
                if start_time is not None:
                    entry["elapsed"] = time.time() - start_time

                # Add to history if mode is 'silent' or 'both'
                if self._log_mode in ("silent", "both"):
                    self._log_history.append(entry)
                    # Trim history if needed
                    if len(self._log_history) > self._log_max_history:
                        self._log_history.pop(0)

                # Log after if enabled
                if config.get("after") and self._log_mode in ("log", "both"):
                    if self._logger:
                        if exception:
                            elapsed_str = (
                                f" (elapsed: {entry['elapsed']:.4f}s)" if "elapsed" in entry else ""
                            )
                            exc_type = type(exception).__name__
                            self._logger.error(
                                f"{handler_name} raised {exc_type}: {exception}{elapsed_str}"
                            )
                        else:
                            elapsed_str = (
                                f" (elapsed: {entry['elapsed']:.4f}s)" if "elapsed" in entry else ""
                            )
                            self._logger.info(f"{handler_name} returned {result}{elapsed_str}")

                # Write to log file if configured
                if self._log_file:
                    try:
                        with open(self._log_file, "a") as f:
                            # Convert entry to JSON-serializable format
                            serializable_entry = {
                                "handler": entry["handler"],
                                "switcher": entry["switcher"],
                                "timestamp": entry["timestamp"],
                                "args": str(entry["args"]),
                                "kwargs": str(entry["kwargs"]),
                            }
                            if "result" in entry:
                                serializable_entry["result"] = str(entry["result"])
                            if "exception" in entry:
                                serializable_entry["exception"] = entry["exception"]
                            if "elapsed" in entry:
                                serializable_entry["elapsed"] = entry["elapsed"]

                            f.write(json.dumps(serializable_entry) + "\n")
                    except Exception:
                        # Silently ignore file write errors
                        pass

            return result

        # Preserve __wrapped__ attribute
        logged_wrapper.__wrapped__ = func
        return logged_wrapper

    def get_log_history(
        self,
        last: int | None = None,
        first: int | None = None,
        handler: str | None = None,
        slowest: int | None = None,
        fastest: int | None = None,
        errors: bool | None = None,
        slower_than: float | None = None,
    ) -> list[dict]:
        """
        Query the log history with various filters.

        Args:
            last: Return last N entries
            first: Return first N entries
            handler: Filter by handler name
            slowest: Return N slowest executions
            fastest: Return N fastest executions
            errors: If True, return only errors; if False, return only successes
            slower_than: Return entries with elapsed time > threshold (seconds)

        Returns:
            List of log entries matching the criteria
        """
        result = self._log_history.copy()

        # Filter by handler
        if handler is not None:
            result = [e for e in result if e.get("handler") == handler]

        # Filter by errors
        if errors is not None:
            if errors:
                result = [e for e in result if "exception" in e]
            else:
                result = [e for e in result if "exception" not in e]

        # Filter by elapsed time threshold
        if slower_than is not None:
            result = [e for e in result if e.get("elapsed", 0) > slower_than]

        # Sort by elapsed time if needed
        if slowest is not None:
            result = sorted(result, key=lambda e: e.get("elapsed", 0), reverse=True)
            result = result[:slowest]
        elif fastest is not None:
            result = sorted(result, key=lambda e: e.get("elapsed", 0))
            result = result[:fastest]
        elif last is not None:
            result = result[-last:]
        elif first is not None:
            result = result[:first]

        return result

    def get_log_stats(self) -> dict[str, dict]:
        """
        Get statistics for all handlers.

        Returns:
            Dict mapping handler names to stats dicts with keys:
            - calls: number of calls
            - errors: number of errors
            - avg_time: average execution time
            - min_time: minimum execution time
            - max_time: maximum execution time
            - total_time: total execution time
        """
        stats = {}

        for entry in self._log_history:
            handler = entry.get("handler")
            if handler not in stats:
                stats[handler] = {
                    "calls": 0,
                    "errors": 0,
                    "times": [],
                }

            stats[handler]["calls"] += 1

            if "exception" in entry:
                stats[handler]["errors"] += 1

            if "elapsed" in entry:
                stats[handler]["times"].append(entry["elapsed"])

        # Compute time statistics
        result = {}
        for handler, data in stats.items():
            times = data["times"]
            result[handler] = {
                "calls": data["calls"],
                "errors": data["errors"],
            }
            if times:
                result[handler]["avg_time"] = sum(times) / len(times)
                result[handler]["min_time"] = min(times)
                result[handler]["max_time"] = max(times)
                result[handler]["total_time"] = sum(times)
            else:
                result[handler]["avg_time"] = 0.0
                result[handler]["min_time"] = 0.0
                result[handler]["max_time"] = 0.0
                result[handler]["total_time"] = 0.0

        return result

    def clear_log_history(self):
        """Clear all log history."""
        self._log_history.clear()

    def export_log_history(self, filepath: str):
        """
        Export log history to a JSON file.

        Args:
            filepath: Path to output JSON file
        """
        with open(filepath, "w") as f:
            # Convert entries to JSON-serializable format
            serializable_entries = []
            for entry in self._log_history:
                serializable_entry = {
                    "handler": entry["handler"],
                    "switcher": entry["switcher"],
                    "timestamp": entry["timestamp"],
                    "args": str(entry["args"]),
                    "kwargs": str(entry["kwargs"]),
                }
                if "result" in entry:
                    serializable_entry["result"] = str(entry["result"])
                if "exception" in entry:
                    serializable_entry["exception"] = entry["exception"]
                if "elapsed" in entry:
                    serializable_entry["elapsed"] = entry["elapsed"]

                serializable_entries.append(serializable_entry)

            json.dump(serializable_entries, f, indent=2)


# ============================================================================
# Pre-register built-in plugins in global registry
# ============================================================================

# Register logging plugin (always available)
from .plugins import LoggingPlugin  # noqa: E402

Switcher.register_plugin("logging", LoggingPlugin)

# Register pydantic plugin if available (optional dependency)
try:
    from .plugins.pydantic import PydanticPlugin  # noqa: E402

    Switcher.register_plugin("pydantic", PydanticPlugin)
except ImportError:
    # Pydantic not installed - plugin won't be available
    pass
