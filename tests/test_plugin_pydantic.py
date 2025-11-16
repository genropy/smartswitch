"""
Tests for PydanticPlugin.

Tests the MVP implementation of Pydantic validation integration.

Requirements: pip install smartswitch[pydantic]
"""

import pytest

# Skip all tests if pydantic is not installed
pydantic = pytest.importorskip("pydantic", reason="pydantic not installed")

from typing import Optional  # noqa: E402

from pydantic import BaseModel, ValidationError  # noqa: E402

from smartswitch import Switcher  # noqa: E402


class TestPydanticPluginBasics:
    """Basic PydanticPlugin functionality tests."""

    def test_plugin_registration(self):
        """Test that pydantic plugin can be registered."""
        sw = Switcher(name="test").plug("pydantic")
        assert len(list(sw.iter_plugins())) == 1

    def test_plugin_chaining(self):
        """Test that plug() returns self for chaining."""
        sw = Switcher(name="api").plug("pydantic")
        assert isinstance(sw, Switcher)
        assert sw.name == "api"

    def test_basic_type_validation(self):
        """Test basic type validation with simple types."""
        sw = Switcher().plug("pydantic")

        @sw
        def add_numbers(x: int, y: int) -> int:
            return x + y

        # Valid call
        result = sw["add_numbers"](5, 10)
        assert result == 15

        # Invalid call - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            sw["add_numbers"]("not a number", 10)

        errors = exc_info.value.errors()
        assert len(errors) >= 1
        assert errors[0]["type"] == "int_parsing"


class TestPydanticBasicTypes:
    """Test validation of basic Python types."""

    def test_string_validation(self):
        """Test string type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def greet(name: str) -> str:
            return f"Hello, {name}"

        assert sw["greet"]("Alice") == "Hello, Alice"

        with pytest.raises(ValidationError):
            sw["greet"](123)

    def test_integer_validation(self):
        """Test integer type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def double(x: int) -> int:
            return x * 2

        assert sw["double"](5) == 10

        # Pydantic coerces strings to int if possible
        assert sw["double"]("5") == 10

        with pytest.raises(ValidationError):
            sw["double"]("not a number")

    def test_float_validation(self):
        """Test float type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def square(x: float) -> float:
            return x * x

        assert sw["square"](3.0) == 9.0
        assert sw["square"](3) == 9.0  # int coerced to float

        with pytest.raises(ValidationError):
            sw["square"]("not a number")

    def test_bool_validation(self):
        """Test boolean type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def negate(flag: bool) -> bool:
            return not flag

        assert sw["negate"](True) is False
        assert sw["negate"](False) is True


class TestPydanticOptionalAndDefaults:
    """Test Optional types and default values."""

    def test_optional_parameter(self):
        """Test Optional type annotation."""
        sw = Switcher().plug("pydantic")

        @sw
        def greet(name: str, title: Optional[str] = None) -> str:
            if title:
                return f"Hello, {title} {name}"
            return f"Hello, {name}"

        # With title
        assert sw["greet"]("Smith", title="Dr.") == "Hello, Dr. Smith"

        # Without title
        assert sw["greet"]("Alice") == "Hello, Alice"

    def test_default_values(self):
        """Test parameters with default values."""
        sw = Switcher().plug("pydantic")

        @sw
        def power(x: int, exponent: int = 2) -> int:
            return x**exponent

        # Use default
        assert sw["power"](5) == 25

        # Override default
        assert sw["power"](2, exponent=3) == 8


class TestPydanticComplexTypes:
    """Test validation of complex types (List, Dict, etc)."""

    def test_list_validation(self):
        """Test List type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def sum_numbers(numbers: list[int]) -> int:
            return sum(numbers)

        assert sw["sum_numbers"]([1, 2, 3]) == 6

        # Pydantic coerces strings to ints in list
        assert sw["sum_numbers"](["1", "2", "3"]) == 6

        with pytest.raises(ValidationError):
            sw["sum_numbers"](["a", "b", "c"])

    def test_dict_validation(self):
        """Test Dict type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def get_value(data: dict[str, int], key: str) -> int:
            return data.get(key, 0)

        assert sw["get_value"]({"a": 1, "b": 2}, "a") == 1
        assert sw["get_value"]({"a": 1}, "missing") == 0

        with pytest.raises(ValidationError):
            sw["get_value"]({"a": "not an int"}, "a")

    def test_tuple_validation(self):
        """Test Tuple type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def add_coords(point: tuple[int, int]) -> int:
            return point[0] + point[1]

        assert sw["add_coords"]((3, 4)) == 7


class TestPydanticBaseModel:
    """Test validation with existing Pydantic models."""

    def test_pydantic_model_validation(self):
        """Test using existing Pydantic BaseModel."""

        class User(BaseModel):
            name: str
            age: int
            email: Optional[str] = None

        sw = Switcher().plug("pydantic")

        @sw
        def greet_user(user: User) -> str:
            return f"Hello, {user.name} (age {user.age})"

        # Valid user
        user = User(name="Alice", age=30)
        assert sw["greet_user"](user) == "Hello, Alice (age 30)"

        # Can also pass dict (Pydantic will validate and construct)
        result = sw["greet_user"]({"name": "Bob", "age": 25})
        assert result == "Hello, Bob (age 25)"

        # Invalid data
        with pytest.raises(ValidationError):
            sw["greet_user"]({"name": "Charlie", "age": "not a number"})


class TestPydanticEdgeCases:
    """Test edge cases and error handling."""

    def test_no_type_hints(self):
        """Test function with no type hints (should not validate)."""
        sw = Switcher().plug("pydantic")

        @sw
        def no_hints(x, y):
            return x + y

        # Should work without validation
        assert sw["no_hints"](5, 10) == 15
        assert sw["no_hints"]("hello", " world") == "hello world"

    def test_partial_type_hints(self):
        """Test function with partial type hints."""
        sw = Switcher().plug("pydantic")

        @sw
        def partial(x: int, y) -> int:
            return x + int(y)

        # Should validate x but not y
        assert sw["partial"](5, "10") == 15

        with pytest.raises(ValidationError):
            sw["partial"]("not a number", 10)

    def test_validation_error_message(self):
        """Test that validation errors have useful messages."""
        sw = Switcher().plug("pydantic")

        @sw
        def strict_int(x: int) -> int:
            return x * 2

        with pytest.raises(ValidationError) as exc_info:
            sw["strict_int"]("not a number")

        error = exc_info.value
        assert "strict_int" in str(error)  # Function name in error


class TestPydanticPluginStacking:
    """Test Pydantic plugin with other plugins."""

    def test_pydantic_with_logging(self, capsys):
        """Test combining Pydantic validation with logging."""
        sw = Switcher().plug("logging", flags="print,enabled,before:off,after").plug("pydantic")

        @sw
        def add(x: int, y: int) -> int:
            return x + y

        result = sw["add"](3, 4)
        assert result == 7

        # Check logging produced output
        captured = capsys.readouterr()
        assert "← add() → 7" in captured.out

    def test_validation_error_logged(self, capsys):
        """Test that validation errors are logged by LoggingPlugin."""
        sw = Switcher().plug("logging", flags="print,enabled,before:off,after").plug("pydantic")

        @sw
        def strict_func(x: int) -> int:
            return x * 2

        # Trigger validation error - should be logged by LoggingPlugin
        with pytest.raises(ValidationError):
            sw["strict_func"]("invalid")

        # LoggingPlugin catches and logs the exception before re-raising
        captured = capsys.readouterr()
        assert "✗ strict_func() raised ValidationError" in captured.out


class TestPydanticPluginConfigure:
    """Test BasePlugin configure() functionality with Pydantic."""

    def test_disable_globally(self):
        """Test disabling validation globally via configure()."""
        sw = Switcher().plug("pydantic")

        @sw
        def strict_func(x: int) -> int:
            return x * 2

        # Initially validation is active - should raise
        with pytest.raises(ValidationError):
            sw["strict_func"]("not a number")

        # Disable validation globally
        sw.pydantic.configure.enabled = False

        # Now validation is bypassed - string passes through
        # String * 2 in Python = concatenation, not TypeError
        result = sw["strict_func"]("hello")
        assert result == "hellohello"

    def test_disable_specific_handler(self):
        """Test disabling validation for specific handler."""
        sw = Switcher().plug("pydantic")

        @sw
        def handler1(x: int) -> int:
            return x * 2

        @sw
        def handler2(x: int) -> int:
            return x * 3

        # Both validate initially
        assert sw["handler1"](5) == 10
        assert sw["handler2"](5) == 15

        # Disable validation only for handler1
        sw.pydantic.configure["handler1"].enabled = False

        # handler1 no longer validates (passes string through)
        result = sw["handler1"]("abc")
        assert result == "abcabc"  # String * 2

        # handler2 still validates
        with pytest.raises(ValidationError):
            sw["handler2"]("not a number")

    def test_re_enable_handler(self):
        """Test re-enabling validation after disabling."""
        sw = Switcher().plug("pydantic")

        @sw
        def my_func(x: int) -> int:
            return x * 2

        # Initially validates
        with pytest.raises(ValidationError):
            sw["my_func"]("invalid")

        # Disable - validation bypassed
        sw.pydantic.configure["my_func"].enabled = False
        result = sw["my_func"]("test")
        assert result == "testtest"  # No validation

        # Re-enable
        sw.pydantic.configure["my_func"].enabled = True
        with pytest.raises(ValidationError):  # Validation is back
            sw["my_func"]("invalid")

    def test_configure_multiple_handlers(self):
        """Test configuring multiple handlers at once."""
        sw = Switcher().plug("pydantic")

        @sw
        def func1(x: int) -> int:
            return x * 2

        @sw
        def func2(x: int) -> int:
            return x * 3

        @sw
        def func3(x: int) -> int:
            return x * 4

        # Disable validation for func1 and func2 only
        sw.pydantic.configure["func1"].enabled = False
        sw.pydantic.configure["func2"].enabled = False

        # func1 and func2 don't validate - strings pass through
        assert sw["func1"]("x") == "xx"
        assert sw["func2"]("y") == "yyy"

        # func3 still validates
        with pytest.raises(ValidationError):
            sw["func3"]("invalid")

    def test_get_config(self):
        """Test get_config() returns correct merged configuration."""
        sw = Switcher().plug("pydantic", global_param="global_value")

        @sw
        def handler1(x: int) -> int:
            return x

        # Global config
        config = sw.pydantic.get_config("handler1")
        assert config["global_param"] == "global_value"
        assert config.get("enabled", True) is True

        # Override for specific handler
        proxy = sw.pydantic.configure["handler1"]
        proxy.handler_param = "handler_value"
        proxy.enabled = False
        config = sw.pydantic.get_config("handler1")
        assert config["global_param"] == "global_value"  # Still has global
        assert config["handler_param"] == "handler_value"  # Has override
        assert config["enabled"] is False  # Override wins

    def test_is_enabled(self):
        """Test is_enabled() method."""
        sw = Switcher().plug("pydantic")

        @sw
        def my_handler(x: int) -> int:
            return x

        # Initially enabled
        assert sw.pydantic.is_enabled_for("my_handler") is True

        # Disable
        sw.pydantic.configure["my_handler"].enabled = False
        assert sw.pydantic.is_enabled_for("my_handler") is False

        # Re-enable
        sw.pydantic.configure["my_handler"].enabled = True
        assert sw.pydantic.is_enabled_for("my_handler") is True

    def test_plugin_name_property(self):
        """Test that plugin_name property generates correct name."""
        sw = Switcher().plug("pydantic")

        # PydanticPlugin should register as 'pydantic'
        assert hasattr(sw, "pydantic")
        assert sw.pydantic.name == "pydantic"

        # Verify it's accessible via __getattr__
        assert sw.pydantic is sw.plugin("pydantic")


class TestPydanticPluginEdgeCases:
    """Test edge cases and error handling in PydanticPlugin."""

    def test_unresolvable_type_hints_disables_validation(self):
        """Test that get_type_hints exception disables validation (lines 78-81)."""
        # Import to avoid NameError at runtime

        sw = Switcher().plug("pydantic")

        # Create function with problematic annotation that will cause get_type_hints to fail
        # Using a forward reference that can't be resolved
        @sw
        def handler_with_bad_hint(x: "NonExistentTypeInThisScope") -> int:  # noqa: F821
            return x

        # The function should still be callable (validation disabled due to error)
        result = sw["handler_with_bad_hint"](42)
        assert result == 42

    def test_signature_binding_error_propagates(self):
        """Test that TypeError during signature binding propagates (lines 154-156)."""
        sw = Switcher().plug("pydantic")

        @sw
        def handler(x: int, y: int) -> int:
            return x + y

        # Call with wrong number of arguments - should raise TypeError
        with pytest.raises(TypeError):
            sw["handler"](42)  # Missing required argument 'y'
