"""
SmartSwitch TypeRule Plugin.

Provides type-based automatic dispatch for SmartSwitch handlers.
"""

import inspect
from typing import TYPE_CHECKING, Any, Callable, Union, get_args, get_origin

if TYPE_CHECKING:
    from ..core import Switcher


class TypeRulePlugin:
    """
    SmartSwitch plugin for type-based dispatch.

    Enables automatic handler selection based on argument types.
    When decorating with `@switcher(typerule={'param': type})`,
    the handler is registered for automatic dispatch.

    The plugin compiles type checkers at registration time for optimal
    runtime performance, supporting:
    - Simple types: `int`, `str`, `dict`, etc.
    - Union types: `int | str`, `Optional[int]`
    - Generic types: `list[int]`, `dict[str, Any]`
    - Custom classes and protocols

    Examples:
        Basic type dispatch:

        >>> converter = Switcher().plug('typerule')
        >>>
        >>> @converter(typerule={'data': dict})
        ... def dict_to_json(data):
        ...     return json.dumps(data)
        >>>
        >>> @converter(typerule={'data': list})
        ... def list_to_json(data):
        ...     return json.dumps(data)
        >>>
        >>> converter()(data={'key': 'value'})  # Calls dict_to_json
        '{"key": "value"}'

        Multiple parameter types:

        >>> processor = Switcher().plug('typerule')
        >>>
        >>> @processor(typerule={'x': int, 'y': int})
        ... def process_ints(x, y):
        ...     return x + y
        >>>
        >>> @processor(typerule={'x': str, 'y': str})
        ... def process_strs(x, y):
        ...     return x + " " + y
        >>>
        >>> processor()(x=1, y=2)  # -> 3
        >>> processor()(x="hello", y="world")  # -> "hello world"

        Union types:

        >>> from typing import Union
        >>> handler = Switcher().plug('typerule')
        >>>
        >>> @handler(typerule={'value': int | str})
        ... def process_scalar(value):
        ...     return str(value).upper()
        >>>
        >>> handler()(value=42)  # -> "42"
        >>> handler()(value="test")  # -> "TEST"

        Custom classes:

        >>> class User:
        ...     pass
        >>> class Admin:
        ...     pass
        >>>
        >>> auth = Switcher().plug('typerule')
        >>>
        >>> @auth(typerule={'user': User})
        ... def auth_user(user):
        ...     return "user"
        >>>
        >>> @auth(typerule={'user': Admin})
        ... def auth_admin(user):
        ...     return "admin"

    Attributes:
        _type_rules: List of registered type rules
        _switcher: Reference to parent Switcher
    """

    def __init__(self):
        """Initialize the type rule plugin."""
        self._type_rules: list[dict] = []
        self._switcher: "Switcher | None" = None

    def wrap(self, func: Callable, switcher: "Switcher") -> Callable:
        """
        Register function with type rule if present.

        Args:
            func: The handler function to wrap
            switcher: The Switcher instance

        Returns:
            The original function (type rules don't wrap, they register)
        """
        # Store switcher reference
        if self._switcher is None:
            self._switcher = switcher
            # Inject dispatch logic into switcher
            self._inject_dispatch(switcher)

        # Check if function has type rule metadata
        if hasattr(func, "_smartswitch_typerule"):
            typerule = func._smartswitch_typerule
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())

            # Compile type checkers
            type_checks = self._compile_type_checks(typerule, param_names)

            # Register the rule
            self._type_rules.append(
                {
                    "func": func,
                    "typerule": typerule,
                    "signature": sig,
                    "param_names": param_names,
                    "type_checks": type_checks,
                }
            )

        return func

    def _inject_dispatch(self, switcher: "Switcher"):
        """Inject type dispatch logic into the Switcher."""
        # Save original __call__ behavior
        original_call = switcher.__call__

        def enhanced_call(arg=None, /, *, typerule=None, valrule=None):
            # If typerule specified, attach metadata to function for later registration
            if typerule is not None:

                def decorator(func):
                    func._smartswitch_typerule = typerule
                    return original_call(func)

                return decorator

            # Dispatch mode: switch()(*args, **kwargs)
            if arg is None and typerule is None and valrule is None:

                def invoker(*args, **kwargs):
                    # Try type rules
                    for rule in self._type_rules:
                        if self._matches_typerule(rule, args, kwargs):
                            return rule["func"](*args, **kwargs)
                    # Fall back to original dispatch
                    raise ValueError(f"No type rule matched for {args}, {kwargs}")

                return invoker

            # Otherwise use original behavior
            return original_call(arg, typerule=typerule, valrule=valrule)

        switcher.__call__ = enhanced_call

    def _compile_type_checks(self, typerule: dict, param_names: list) -> list:
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

    def _make_type_checker(self, hint: type) -> Callable[[Any], bool]:
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
            checkers = [self._make_type_checker(t) for t in args]
            return lambda val: any(check(val) for check in checkers)

        # Generic types (e.g., list[int], dict[str, Any])
        if origin is not None:
            # For now, only check the origin type (list, dict, etc.)
            # Full generic checking would require recursion
            return lambda val: isinstance(val, origin)

        # Simple type
        return lambda val: isinstance(val, hint)

    def _matches_typerule(self, rule: dict, args: tuple, kwargs: dict) -> bool:
        """
        Check if arguments match a type rule.

        Args:
            rule: Type rule dict with compiled checkers
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            True if all type checks pass
        """
        param_names = rule["param_names"]
        type_checks = rule["type_checks"]

        # Build kwargs dict from args + kwargs
        args_dict = {}

        # Map positional args to param names
        for i, arg in enumerate(args):
            if i < len(param_names):
                args_dict[param_names[i]] = arg

        # Add keyword args
        args_dict.update(kwargs)

        # Check all type constraints
        for param_name, checker in type_checks:
            if param_name not in args_dict:
                # Missing required parameter
                return False

            value = args_dict[param_name]
            if not checker(value):
                return False

        return True
