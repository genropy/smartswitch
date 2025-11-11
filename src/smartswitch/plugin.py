"""
SmartSwitch Plugin Protocol.

Defines the protocol that all SmartSwitch plugins must implement.
Plugins can extend Switcher functionality by wrapping handlers during registration.
"""

from typing import Callable, Protocol, TYPE_CHECKING

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
