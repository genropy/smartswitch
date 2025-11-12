"""
SmartSwitch Plugin Protocol and Base Class.

Defines the protocol that all SmartSwitch plugins must implement,
and provides a base class with common functionality.
"""

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Protocol

if TYPE_CHECKING:
    from .core import Switcher


class SwitcherPlugin(Protocol):
    """
    Protocol for SmartSwitch plugins.

    Plugins can modify or enhance handler behavior by wrapping functions
    during registration. Each plugin receives the function and the parent
    Switcher instance, allowing it to:

    - Add logging or monitoring
    - Implement type-based or value-based dispatch rules
    - Add validation or preprocessing
    - Register handlers in internal data structures
    - Apply any other cross-cutting concerns

    Example:
        >>> class LoggingPlugin:
        ...     def wrap(self, func: Callable, switcher: 'Switcher') -> Callable:
        ...         @wraps(func)
        ...         def wrapper(*args, **kwargs):
        ...             print(f"Calling {func.__name__}")
        ...             return func(*args, **kwargs)
        ...         return wrapper
        ...
        >>> switcher = Switcher(plugins=[LoggingPlugin()])
        >>> @switcher
        ... def my_handler():
        ...     return "result"
        >>> switcher('my_handler')()  # Prints: Calling my_handler
        'result'

    Note:
        Plugins are applied in order during handler registration.
        The wrapped function from one plugin is passed to the next plugin.
    """

    def wrap(self, func: Callable, switcher: "Switcher") -> Callable:
        """
        Wrap a handler function during registration.

        This method is called when a handler is registered via the @switcher
        decorator. The plugin can:

        1. Return the function unmodified (pass-through)
        2. Return a wrapped version with additional behavior
        3. Store information about the function for later use
        4. Modify the Switcher's internal state

        Args:
            func: The handler function being registered
            switcher: The Switcher instance registering the handler

        Returns:
            The function to be registered (original or wrapped)

        Example:
            >>> class TypeCheckPlugin:
            ...     def wrap(self, func, switcher):
            ...         if hasattr(func, '_typerule'):
            ...             # Store type rule, return wrapped function
            ...             return self._add_type_checking(func)
            ...         return func  # Pass through if no type rule
        """
        ...


class BasePlugin:
    """
    Base class for SmartSwitch plugins with common functionality.

    Provides:
    - Global and per-handler configuration management
    - Enable/disable functionality via `enabled` parameter
    - Automatic configuration merging (global + handler-specific)

    Subclasses should override `_wrap_handler()` to implement their
    specific wrapping logic.

    Example:
        >>> class MyPlugin(BasePlugin):
        ...     def _wrap_handler(self, func, switcher, config):
        ...         @wraps(func)
        ...         def wrapper(*args, **kwargs):
        ...             if config.get('debug'):
        ...                 print(f"Calling {func.__name__}")
        ...             return func(*args, **kwargs)
        ...         return wrapper
        ...
        >>> sw = Switcher().plug(MyPlugin(debug=False))
        >>> sw.my_plugin.configure("handler1", debug=True)  # Enable only for handler1
    """

    def __init__(self, **config):
        """
        Initialize plugin with global configuration.

        Args:
            **config: Global configuration parameters. All plugins support
                     'enabled' parameter to disable/enable the plugin.
        """
        self._global_config = config
        self._handler_configs = {}  # {handler_name: config_override}

    @property
    def plugin_name(self) -> str:
        """
        Get the plugin's registration name.

        By default, generates name from class name by:
        1. Removing 'Plugin' suffix if present
        2. Converting to lowercase

        Examples:
            PydanticPlugin -> 'pydantic'
            MyCustomPlugin -> 'mycustom'
            CustomValidator -> 'customvalidator'

        Subclasses can override this property to provide custom names.

        Returns:
            Plugin name for registration in Switcher._plugin_registry
        """
        name = self.__class__.__name__
        if name.endswith("Plugin"):
            name = name[:-6]  # Remove 'Plugin' suffix
        return name.lower()

    def configure(self, *handler_names: str, **config) -> None:
        """
        Configure plugin globally or for specific handlers.

        Without handler names, updates global configuration.
        With handler names, creates/updates handler-specific overrides.

        Args:
            *handler_names: Optional handler names to configure specifically.
                           If empty, configures globally.
            **config: Configuration parameters to set. Use `enabled=True/False`
                     to enable/disable the plugin for specific handlers.

        Examples:
            Global configuration:
                >>> plugin.configure(debug=True)

            Handler-specific configuration:
                >>> plugin.configure("handler1", "handler2", enabled=False)
                >>> plugin.configure("api_endpoint", timeout=30, strict=True)

            Re-enable after disabling:
                >>> plugin.configure("handler1", enabled=True)
        """
        if not handler_names:
            # Global configuration update
            self._global_config.update(config)
        else:
            # Handler-specific configuration
            for name in handler_names:
                if name not in self._handler_configs:
                    self._handler_configs[name] = {}
                self._handler_configs[name].update(config)

    def get_config(self, handler_name: str) -> dict[str, Any]:
        """
        Get effective configuration for a handler.

        Merges global config with handler-specific overrides.

        Args:
            handler_name: Name of the handler

        Returns:
            Merged configuration dictionary (global + handler-specific)
        """
        config = self._global_config.copy()
        if handler_name in self._handler_configs:
            config.update(self._handler_configs[handler_name])
        return config

    def is_enabled(self, handler_name: str) -> bool:
        """
        Check if plugin is enabled for a specific handler.

        Args:
            handler_name: Name of the handler

        Returns:
            True if enabled, False if disabled via `enabled=False`
        """
        config = self.get_config(handler_name)
        return config.get("enabled", True)

    def on_decorate(self, func: Callable, switcher: "Switcher") -> None:
        """
        Hook called when a function is decorated (optional).

        This method is called during decoration, BEFORE wrap() is called.
        It allows plugins to be notified of decoration events and perform
        setup, initialization, or store metadata without necessarily wrapping
        the function.

        Args:
            func: The handler function being decorated
            switcher: The Switcher instance registering the handler

        Note:
            This is an optional hook. BasePlugin provides a no-op implementation.
            Subclasses can override to add custom behavior.

        Example:
            >>> class MetadataPlugin(BasePlugin):
            ...     def __init__(self, **config):
            ...         super().__init__(**config)
            ...         self.decorated_funcs = []
            ...
            ...     def on_decorate(self, func, switcher):
            ...         # Store metadata about decorated function
            ...         self.decorated_funcs.append({
            ...             'name': func.__name__,
            ...             'module': func.__module__,
            ...             'doc': func.__doc__
            ...         })
            ...
            ...     def _wrap_handler(self, func, switcher):
            ...         # No wrapping needed
            ...         return func
        """
        # No-op by default - subclasses can override
        pass

    def wrap(self, func: Callable, switcher: "Switcher") -> Callable:
        """
        Wrap handler with configuration-aware logic.

        This method handles the enable/disable check and passes control
        to the subclass-specific `_wrap_handler()` method.

        Args:
            func: Handler function to wrap
            switcher: Switcher instance

        Returns:
            Wrapped function (or original if disabled)
        """
        handler_name = func.__name__

        # Get wrapped function from subclass
        wrapped_func = self._wrap_handler(func, switcher)

        @wraps(func)
        def config_aware_wrapper(*args, **kwargs):
            """Wrapper that checks enabled status at call time."""
            # Check if plugin is enabled for this handler
            if self.is_enabled(handler_name):
                return wrapped_func(*args, **kwargs)
            else:
                # Plugin disabled - call original function directly
                return func(*args, **kwargs)

        return config_aware_wrapper

    def _wrap_handler(self, func: Callable, switcher: "Switcher") -> Callable:
        """
        Wrap handler with plugin-specific logic.

        Subclasses must override this method to implement their wrapping logic.
        This method should return a wrapped version of the function that
        implements the plugin's functionality.

        The wrapped function can access handler-specific configuration via
        `self.get_config(func.__name__)`.

        Args:
            func: Handler function to wrap
            switcher: Switcher instance

        Returns:
            Wrapped function implementing plugin logic

        Example:
            >>> def _wrap_handler(self, func, switcher):
            ...     config = self.get_config(func.__name__)
            ...     @wraps(func)
            ...     def wrapper(*args, **kwargs):
            ...         if config.get('log_calls'):
            ...             print(f"Calling {func.__name__}")
            ...         return func(*args, **kwargs)
            ...     return wrapper
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement _wrap_handler()")
