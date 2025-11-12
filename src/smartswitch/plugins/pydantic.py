"""
Pydantic validation plugin for SmartSwitch.

This plugin automatically validates function arguments using type hints via Pydantic v2.
Requires: pip install smartswitch[pydantic]

MVP Support:
- Basic types: str, int, float, bool
- Optional and default values
- Complex types: List, Dict, Set, Tuple
- Existing Pydantic BaseModel instances
"""

from functools import wraps
from typing import Any, Callable, get_type_hints

try:
    from pydantic import BaseModel, ValidationError, create_model
except ImportError:
    raise ImportError(
        "Pydantic plugin requires pydantic. " "Install with: pip install smartswitch[pydantic]"
    )

from ..plugin import BasePlugin


class PydanticPlugin(BasePlugin):
    """
    Plugin that adds Pydantic validation to handlers based on type hints.

    Usage:
        sw = Switcher().plug("pydantic")

        @sw.typerule(x=int, y=int)
        def add(x: int, y: str) -> int:  # Will validate types at runtime
            return x + int(y)

    The plugin extracts type hints from decorated functions and validates
    arguments before calling the function. Raises ValidationError on failure.
    """

    def __init__(self, **config):
        """
        Initialize the Pydantic validation plugin.

        Args:
            **config: Configuration options for the plugin.
                     Common: enabled=True/False to enable/disable globally
        """
        super().__init__(**config)

    def on_decorate(self, func: Callable, switcher: Any) -> None:
        """
        Prepare validation model during decoration.

        Extracts type hints and creates Pydantic model, storing it in
        func._plugin_meta['pydantic'] for use by this plugin and others.

        Args:
            func: The handler function being decorated
            switcher: The Switcher instance
        """
        # Get type hints (resolved with string annotations)
        try:
            hints = get_type_hints(func)
        except Exception:
            # If type hints can't be resolved, skip
            return

        # Remove return type hint
        hints.pop("return", None)

        # If no type hints to validate, skip
        if not hints:
            return

        # Create a Pydantic model dynamically from type hints
        import inspect

        sig = inspect.signature(func)
        fields = {}

        for param_name, hint in hints.items():
            param = sig.parameters.get(param_name)
            if param is None:
                # Parameter not in signature (shouldn't happen)
                fields[param_name] = (hint, ...)
            elif param.default is inspect.Parameter.empty:
                # Required parameter
                fields[param_name] = (hint, ...)
            else:
                # Optional parameter with default
                fields[param_name] = (hint, param.default)

        # Create validation model
        validation_model = create_model(f"{func.__name__}_Model", **fields)

        # Store model and metadata for use by this and other plugins
        func._plugin_meta["pydantic"] = {
            "model": validation_model,
            "hints": hints,
            "signature": sig,
        }

    def _wrap_handler(self, func: Callable, switcher: Any) -> Callable:
        """
        Wrap a function with Pydantic validation.

        Uses pre-created validation model from func._plugin_meta['pydantic']
        if available, otherwise skips validation.

        Args:
            func: The function to wrap
            switcher: The Switcher instance (unused in MVP)

        Returns:
            Wrapped function that validates arguments before execution
        """
        # Check if validation model was created in on_decorate
        pydantic_meta = getattr(func, "_plugin_meta", {}).get("pydantic", {})
        if not pydantic_meta:
            # No validation model - return original function
            return func

        validation_model = pydantic_meta["model"]
        hints = pydantic_meta["hints"]
        sig = pydantic_meta["signature"]

        @wraps(func)
        def wrapper(*args, **kwargs):
            """Validate arguments before calling function."""
            # Build dict of all arguments
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            # Split arguments into those with hints and those without
            args_to_validate = {k: v for k, v in bound.arguments.items() if k in hints}
            args_without_hints = {k: v for k, v in bound.arguments.items() if k not in hints}

            # Validate using Pydantic
            try:
                validated = validation_model(**args_to_validate)

                # Merge validated args with unvalidated args
                # For BaseModel instances, keep the validated object, not the dict
                final_args = args_without_hints.copy()
                for key, value in validated:
                    # Check if original input was already a BaseModel instance
                    original_value = args_to_validate.get(key)
                    if isinstance(original_value, BaseModel):
                        # Keep the original BaseModel instance
                        final_args[key] = original_value
                    else:
                        # Use validated value
                        final_args[key] = value

                # Call original function with all arguments
                return func(**final_args)
            except ValidationError as e:
                # Re-raise with more context
                raise ValidationError.from_exception_data(
                    title=f"Validation error in {func.__name__}",
                    line_errors=e.errors(),
                ) from e

        return wrapper
