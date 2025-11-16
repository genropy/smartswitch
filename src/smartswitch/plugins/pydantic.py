"""
Pydantic validation plugin for Switcher.

This plugin automatically validates function arguments using type hints via Pydantic v2.
Requires: pip install smartswitch[pydantic]

MVP Support:
- Basic types: str, int, float, bool
- Optional and default values
- Complex types: List, Dict, Set, Tuple
- Existing Pydantic BaseModel instances
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Callable, Optional, get_type_hints

try:
    from pydantic import BaseModel, ValidationError, create_model
except ImportError:
    raise ImportError(
        "Pydantic plugin requires pydantic. " "Install with: pip install smartswitch[pydantic]"
    )

if TYPE_CHECKING:
    from ..core import MethodEntry, Switcher

from ..core import BasePlugin


class PydanticPlugin(BasePlugin):
    """
    Plugin that adds Pydantic validation to handlers based on type hints.

    Usage:
        sw = Switcher().plug("pydantic")

        @sw
        def add(x: int, y: str) -> int:  # Will validate types at runtime
            return x + int(y)

    The plugin extracts type hints from decorated functions and validates
    arguments before calling the function. Raises ValidationError on failure.
    """

    def __init__(self, name: Optional[str] = None, **config: Any):
        """
        Initialize the Pydantic validation plugin.

        Args:
            name: Plugin name (default: 'pydantic')
            **config: Configuration options for the plugin.
                     Common: enabled=True/False to enable/disable globally
        """
        super().__init__(name=name or "pydantic", **config)

    def on_decore(
        self,
        switch: "Switcher",
        func: Callable,
        entry: "MethodEntry",
    ) -> None:
        """
        Prepare validation model during decoration.

        Extracts type hints and creates Pydantic model, storing it in
        entry.metadata['pydantic'] for use at runtime.

        Args:
            switch: The Switcher instance
            func: The handler function being decorated
            entry: The method entry with metadata
        """
        # Get type hints (resolved with string annotations)
        try:
            hints = get_type_hints(func)
        except Exception:
            # If type hints can't be resolved, skip validation
            entry.metadata["pydantic"] = {"enabled": False}
            return

        # Remove return type hint
        hints.pop("return", None)

        # If no type hints to validate, skip
        if not hints:
            entry.metadata["pydantic"] = {"enabled": False}
            return

        # Get function signature
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
        validation_model = create_model(f"{func.__name__}_Model", **fields)  # type: ignore[call-overload]

        # Pre-extract ALL information needed for CLI/API/Help (one-time extraction)
        # This avoids repeated inspect.signature() calls throughout the application
        param_names = []
        param_info = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_names.append(param_name)

            # Extract type info
            hint = hints.get(param_name)
            if hint is not None:
                # Try to get a clean type name
                try:
                    from typing import get_origin

                    origin = get_origin(hint)
                    if origin is not None:
                        param_type = str(hint)
                    else:
                        param_type = hint.__name__ if hasattr(hint, "__name__") else str(hint)
                except Exception:
                    param_type = str(hint)
            else:
                param_type = "Any"

            # Check if required
            required = param.default is inspect.Parameter.empty
            default = None if required else param.default

            param_info.append(
                {
                    "name": param_name,
                    "type": param_type,
                    "required": required,
                    "default": default,
                }
            )

        # Store EVERYTHING in metadata for runtime use (one-time extraction)
        entry.metadata["pydantic"] = {
            "enabled": True,
            "model": validation_model,  # For fast validation
            "param_names": param_names,  # For CLI arg mapping
            "param_info": param_info,  # For help/API documentation
            "hints": hints,  # Original type hints
            "signature": sig,  # Complete signature object
        }

    def wrap_handler(
        self,
        switch: "Switcher",
        entry: "MethodEntry",
        call_next: Callable,
    ) -> Callable:
        """
        Wrap a handler function with Pydantic validation.

        Uses pre-created validation model from entry.metadata['pydantic']
        if available, otherwise skips validation.

        Args:
            switch: The Switcher instance
            entry: The method entry with metadata
            call_next: The next layer in the wrapper chain

        Returns:
            Wrapped function that validates arguments before execution
        """
        # Check if validation model was created in on_decore
        pydantic_meta = entry.metadata.get("pydantic", {})
        if not pydantic_meta.get("enabled", False):
            # No validation model - pass through
            return call_next

        validation_model = pydantic_meta["model"]
        hints = pydantic_meta["hints"]
        sig = pydantic_meta["signature"]

        def wrapper(*args, **kwargs):
            """Validate arguments before calling function."""
            # Build dict of all arguments
            try:
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
            except TypeError:
                # Signature binding failed - let it propagate
                raise

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

                # Call next layer with validated arguments
                return call_next(**final_args)
            except ValidationError as e:
                # Re-raise with more context
                raise ValidationError.from_exception_data(
                    title=f"Validation error in {entry.name}",
                    line_errors=e.errors(),
                ) from e

        return wrapper


# Register plugin globally
from ..core import Switcher  # noqa: E402

Switcher.register_plugin("pydantic", PydanticPlugin)
