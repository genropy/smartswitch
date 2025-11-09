"""
Tests for __wrapped__ attribute to enable introspection.
"""

import inspect
from smartswitch import Switcher


def test_wrapped_attribute_exists():
    """Test that retrieved handlers have __wrapped__ attribute."""
    sw = Switcher()

    @sw
    def my_handler(name: str, value: int) -> str:
        """Process data."""
        return f"{name}={value}"

    # Get handler
    handler = sw('my_handler')

    # Should have __wrapped__ attribute
    assert hasattr(handler, '__wrapped__')
    assert handler.__wrapped__ is my_handler


def test_wrapped_preserves_signature():
    """Test that __wrapped__ allows signature introspection."""
    sw = Switcher()

    @sw
    def process_data(filename: str, mode: str = 'read') -> None:
        """Process a file."""
        pass

    # Get handler
    handler = sw('process_data')

    # Introspect original function via __wrapped__
    original = handler.__wrapped__
    sig = inspect.signature(original)

    # Should see original parameters, not (*args, **kwargs)
    params = list(sig.parameters.keys())
    assert params == ['filename', 'mode']

    # Check types
    assert sig.parameters['filename'].annotation == str
    assert sig.parameters['mode'].annotation == str
    assert sig.parameters['mode'].default == 'read'
    assert sig.return_annotation is None


def test_wrapped_with_custom_alias():
    """Test __wrapped__ works with custom alias."""
    sw = Switcher()

    @sw('custom_name')
    def my_function(x: int, y: int) -> int:
        """Add two numbers."""
        return x + y

    # Get handler by alias
    handler = sw('custom_name')

    # Should have __wrapped__
    assert hasattr(handler, '__wrapped__')
    assert handler.__wrapped__ is my_function

    # Introspect
    sig = inspect.signature(handler.__wrapped__)
    assert list(sig.parameters.keys()) == ['x', 'y']


def test_wrapped_function_still_works():
    """Test that adding __wrapped__ doesn't break function calls."""
    sw = Switcher()

    @sw
    def add(a: int, b: int) -> int:
        return a + b

    # Get handler
    handler = sw('add')

    # Should still work normally
    result = handler(10, 20)
    assert result == 30

    # __wrapped__ should also work
    result = handler.__wrapped__(5, 7)
    assert result == 12


def test_wrapped_with_typerule():
    """Test __wrapped__ with handlers registered via typerule."""
    sw = Switcher()

    @sw(typerule={'x': int})
    def process_int(x):
        return f"int: {x}"

    @sw(typerule={'x': str})
    def process_str(x):
        return f"str: {x}"

    # Get handlers by name
    int_handler = sw('process_int')
    str_handler = sw('process_str')

    # Should have __wrapped__
    assert hasattr(int_handler, '__wrapped__')
    assert hasattr(str_handler, '__wrapped__')

    assert int_handler.__wrapped__ is process_int
    assert str_handler.__wrapped__ is process_str


def test_wrapped_with_prefix():
    """Test __wrapped__ with prefix-based naming."""
    sw = Switcher(prefix="cmd_")

    @sw
    def cmd_start():
        """Start the process."""
        return "started"

    # Get handler (prefix stripped)
    handler = sw('start')

    # Should have __wrapped__
    assert hasattr(handler, '__wrapped__')
    assert handler.__wrapped__.__name__ == 'cmd_start'


def test_wrapped_docstring_access():
    """Test that docstring is accessible via __wrapped__."""
    sw = Switcher()

    @sw
    def documented_function(param: str) -> str:
        """
        This is a well-documented function.

        Args:
            param: The parameter

        Returns:
            Processed string
        """
        return param.upper()

    # Get handler
    handler = sw('documented_function')

    # Access docstring via __wrapped__
    assert handler.__wrapped__.__doc__ is not None
    assert "well-documented function" in handler.__wrapped__.__doc__


def test_wrapped_with_instance_methods():
    """Test __wrapped__ works with instance methods."""

    class MyAPI:
        sw = Switcher()

        @sw
        def process(self, data: str) -> str:
            """Process some data."""
            return data.upper()

    api = MyAPI()

    # Get bound handler
    handler = api.sw('process')

    # The partial should still give access to original function
    # Note: with partial, __wrapped__ points to the original unbound method
    assert hasattr(handler, '__wrapped__')
