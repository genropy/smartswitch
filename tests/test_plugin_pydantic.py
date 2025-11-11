"""
Tests for PydanticPlugin.

Tests the MVP implementation of Pydantic validation integration.

Requirements: pip install smartswitch[pydantic]
"""

import pytest

# Skip all tests if pydantic is not installed
pydantic = pytest.importorskip("pydantic", reason="pydantic not installed")

from pydantic import BaseModel, ValidationError
from smartswitch import Switcher
from typing import Optional


class TestPydanticPluginBasics:
    """Basic PydanticPlugin functionality tests."""

    def test_plugin_registration(self):
        """Test that pydantic plugin can be registered."""
        sw = Switcher(name="test").plug("pydantic")
        assert len(sw._plugins) == 1

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
        result = sw("add_numbers")(5, 10)
        assert result == 15

        # Invalid call - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            sw("add_numbers")("not a number", 10)

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

        assert sw("greet")("Alice") == "Hello, Alice"

        with pytest.raises(ValidationError):
            sw("greet")(123)

    def test_integer_validation(self):
        """Test integer type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def double(x: int) -> int:
            return x * 2

        assert sw("double")(5) == 10

        # Pydantic coerces strings to int if possible
        assert sw("double")("5") == 10

        with pytest.raises(ValidationError):
            sw("double")("not a number")

    def test_float_validation(self):
        """Test float type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def square(x: float) -> float:
            return x * x

        assert sw("square")(3.0) == 9.0
        assert sw("square")(3) == 9.0  # int coerced to float

        with pytest.raises(ValidationError):
            sw("square")("not a number")

    def test_bool_validation(self):
        """Test boolean type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def negate(flag: bool) -> bool:
            return not flag

        assert sw("negate")(True) is False
        assert sw("negate")(False) is True


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
        assert sw("greet")("Smith", title="Dr.") == "Hello, Dr. Smith"

        # Without title
        assert sw("greet")("Alice") == "Hello, Alice"

    def test_default_values(self):
        """Test parameters with default values."""
        sw = Switcher().plug("pydantic")

        @sw
        def power(x: int, exponent: int = 2) -> int:
            return x**exponent

        # Use default
        assert sw("power")(5) == 25

        # Override default
        assert sw("power")(2, exponent=3) == 8


class TestPydanticComplexTypes:
    """Test validation of complex types (List, Dict, etc)."""

    def test_list_validation(self):
        """Test List type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def sum_numbers(numbers: list[int]) -> int:
            return sum(numbers)

        assert sw("sum_numbers")([1, 2, 3]) == 6

        # Pydantic coerces strings to ints in list
        assert sw("sum_numbers")(["1", "2", "3"]) == 6

        with pytest.raises(ValidationError):
            sw("sum_numbers")(["a", "b", "c"])

    def test_dict_validation(self):
        """Test Dict type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def get_value(data: dict[str, int], key: str) -> int:
            return data.get(key, 0)

        assert sw("get_value")({"a": 1, "b": 2}, "a") == 1
        assert sw("get_value")({"a": 1}, "missing") == 0

        with pytest.raises(ValidationError):
            sw("get_value")({"a": "not an int"}, "a")

    def test_tuple_validation(self):
        """Test Tuple type validation."""
        sw = Switcher().plug("pydantic")

        @sw
        def add_coords(point: tuple[int, int]) -> int:
            return point[0] + point[1]

        assert sw("add_coords")((3, 4)) == 7


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
        assert sw("greet_user")(user) == "Hello, Alice (age 30)"

        # Can also pass dict (Pydantic will validate and construct)
        result = sw("greet_user")({"name": "Bob", "age": 25})
        assert result == "Hello, Bob (age 25)"

        # Invalid data
        with pytest.raises(ValidationError):
            sw("greet_user")({"name": "Charlie", "age": "not a number"})


class TestPydanticEdgeCases:
    """Test edge cases and error handling."""

    def test_no_type_hints(self):
        """Test function with no type hints (should not validate)."""
        sw = Switcher().plug("pydantic")

        @sw
        def no_hints(x, y):
            return x + y

        # Should work without validation
        assert sw("no_hints")(5, 10) == 15
        assert sw("no_hints")("hello", " world") == "hello world"

    def test_partial_type_hints(self):
        """Test function with partial type hints."""
        sw = Switcher().plug("pydantic")

        @sw
        def partial(x: int, y) -> int:
            return x + int(y)

        # Should validate x but not y
        assert sw("partial")(5, "10") == 15

        with pytest.raises(ValidationError):
            sw("partial")("not a number", 10)

    def test_validation_error_message(self):
        """Test that validation errors have useful messages."""
        sw = Switcher().plug("pydantic")

        @sw
        def strict_int(x: int) -> int:
            return x * 2

        with pytest.raises(ValidationError) as exc_info:
            sw("strict_int")("not a number")

        error = exc_info.value
        assert "strict_int" in str(error)  # Function name in error


class TestPydanticPluginStacking:
    """Test Pydantic plugin with other plugins."""

    def test_pydantic_with_logging(self):
        """Test combining Pydantic validation with logging."""
        sw = Switcher().plug("logging", mode="silent").plug("pydantic")

        @sw
        def add(x: int, y: int) -> int:
            return x + y

        result = sw("add")(3, 4)
        assert result == 7

        # Check logging captured the call
        history = sw.logger.history()
        assert len(history) == 1
        assert history[0]["result"] == 7

    def test_validation_error_logged(self):
        """Test that validation errors interrupt execution before logging."""
        sw = Switcher().plug("logging", mode="silent").plug("pydantic")

        @sw
        def strict_func(x: int) -> int:
            return x * 2

        # Trigger validation error - should raise before logging can capture it
        with pytest.raises(ValidationError):
            sw("strict_func")("invalid")

        # Note: ValidationError is raised by pydantic plugin before logging plugin
        # can capture the call, so history should be empty. This is expected behavior
        # because plugin order matters: logging wraps the function, then pydantic wraps
        # that wrapper. When pydantic raises, the call never reaches the logging wrapper.
        history = sw.logger.history()
        assert len(history) == 0  # No call logged because validation failed
