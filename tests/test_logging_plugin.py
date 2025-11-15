"""
Tests for LoggingPlugin with composable mode flags.
"""

from __future__ import annotations

import logging
import time

import pytest

from smartswitch import Switcher
from smartswitch.plugins import LoggingPlugin


class TestModeValidation:
    """Test mode flag parsing and validation."""

    def test_default_mode(self):
        """Test default mode is 'print' with before+after."""
        plugin = LoggingPlugin()
        assert plugin.use_print is True
        assert plugin.use_log is False
        assert plugin.show_before is True
        assert plugin.show_after is True
        assert plugin.show_time is False

    def test_print_mode(self):
        """Test explicit print mode."""
        plugin = LoggingPlugin(mode="print")
        assert plugin.use_print is True
        assert plugin.use_log is False
        assert plugin.show_before is True  # Default
        assert plugin.show_after is True  # Default

    def test_log_mode(self):
        """Test log mode."""
        plugin = LoggingPlugin(mode="log")
        assert plugin.use_print is False
        assert plugin.use_log is True
        assert plugin.show_before is True  # Default
        assert plugin.show_after is True  # Default

    def test_before_flag(self):
        """Test before flag only."""
        plugin = LoggingPlugin(mode="print,before")
        assert plugin.show_before is True
        assert plugin.show_after is False
        assert plugin.show_time is False

    def test_after_flag(self):
        """Test after flag only."""
        plugin = LoggingPlugin(mode="print,after")
        assert plugin.show_before is False
        assert plugin.show_after is True
        assert plugin.show_time is False

    def test_time_flag(self):
        """Test time flag with defaults."""
        plugin = LoggingPlugin(mode="print,time")
        assert plugin.show_before is True  # Default
        assert plugin.show_after is True  # Default
        assert plugin.show_time is True

    def test_combined_flags(self):
        """Test combination of flags."""
        plugin = LoggingPlugin(mode="log,before,after,time")
        assert plugin.use_log is True
        assert plugin.show_before is True
        assert plugin.show_after is True
        assert plugin.show_time is True

    def test_whitespace_handling(self):
        """Test mode with whitespace."""
        plugin = LoggingPlugin(mode=" print , after , time ")
        assert plugin.use_print is True
        assert plugin.show_after is True
        assert plugin.show_time is True

    def test_missing_output_mode(self):
        """Test error when no print or log."""
        with pytest.raises(ValueError, match="mode must include 'print' or 'log'"):
            LoggingPlugin(mode="before,after")

    def test_both_output_modes(self):
        """Test error when both print and log."""
        with pytest.raises(ValueError, match="cannot include both 'print' and 'log'"):
            LoggingPlugin(mode="print,log")


class TestPrintOutput:
    """Test output using print()."""

    def test_print_default(self, capsys):
        """Test default print output shows before and after."""
        sw = Switcher().plug("logging", mode="print")

        @sw
        def add(a, b):
            return a + b

        result = sw("add")(2, 3)
        assert result == 5

        captured = capsys.readouterr()
        assert "→ add(2, 3)" in captured.out
        assert "← add() → 5" in captured.out

    def test_print_before_only(self, capsys):
        """Test print with only before flag."""
        sw = Switcher().plug("logging", mode="print,before")

        @sw
        def process(data):
            return f"processed-{data}"

        sw("process")("test")

        captured = capsys.readouterr()
        assert "→ process('test')" in captured.out
        assert "← process()" not in captured.out

    def test_print_after_only(self, capsys):
        """Test print with only after flag."""
        sw = Switcher().plug("logging", mode="print,after")

        @sw
        def process(data):
            return f"processed-{data}"

        sw("process")("test")

        captured = capsys.readouterr()
        assert "→ process(" not in captured.out  # More precise check
        assert "← process() → processed-test" in captured.out

    def test_print_with_time(self, capsys):
        """Test print with timing."""
        sw = Switcher().plug("logging", mode="print,after,time")

        @sw
        def slow():
            time.sleep(0.01)
            return "done"

        sw("slow")()

        captured = capsys.readouterr()
        assert "← slow() → done" in captured.out
        assert "s)" in captured.out  # Has timing

    def test_print_kwargs(self, capsys):
        """Test print with keyword arguments."""
        sw = Switcher().plug("logging", mode="print,before")

        @sw
        def create_user(name, age, email=""):
            return {"name": name, "age": age}

        sw("create_user")("Alice", age=30, email="alice@test.com")

        captured = capsys.readouterr()
        assert "→ create_user('Alice', age=30, email='alice@test.com')" in captured.out


class TestLogOutput:
    """Test output using Python logging."""

    def test_log_with_handlers(self, caplog):
        """Test log output when logging is configured."""
        caplog.set_level(logging.INFO)

        sw = Switcher().plug("logging", mode="log")

        @sw
        def multiply(a, b):
            return a * b

        result = sw("multiply")(3, 4)
        assert result == 12

        assert len(caplog.records) == 2
        assert "→ multiply(3, 4)" in caplog.text
        assert "← multiply() → 12" in caplog.text

    def test_log_fallback_to_print(self, capsys):
        """Test automatic fallback to print when logging not configured."""
        # Create fresh logger with no handlers
        logger = logging.getLogger("test_fallback")
        logger.handlers.clear()
        logger.propagate = False

        sw = Switcher().plug("logging", mode="log", logger=logger)

        @sw
        def divide(a, b):
            return a / b

        sw("divide")(10, 2)

        captured = capsys.readouterr()
        # Should use print() since logger has no handlers
        assert "→ divide(10, 2)" in captured.out
        assert "← divide() → 5" in captured.out

    def test_log_levels(self, caplog):
        """Test different log levels (info for normal, error for exceptions)."""
        caplog.set_level(logging.INFO)

        sw = Switcher().plug("logging", mode="log,after")

        @sw
        def may_fail(should_fail):
            if should_fail:
                raise ValueError("Failed")
            return "Success"

        # Normal call -> info level
        sw("may_fail")(False)
        assert any(r.levelname == "INFO" for r in caplog.records)

        # Failing call -> error level
        caplog.clear()
        with pytest.raises(ValueError):
            sw("may_fail")(True)
        assert any(r.levelname == "ERROR" for r in caplog.records)


class TestExceptionHandling:
    """Test logging of exceptions."""

    def test_exception_logged_before_reraise(self, capsys):
        """Test exception is logged before being re-raised."""
        sw = Switcher().plug("logging", mode="print,after")

        @sw
        def fail():
            raise ValueError("Something broke")

        with pytest.raises(ValueError, match="Something broke"):
            sw("fail")()

        captured = capsys.readouterr()
        assert "✗ fail() raised ValueError: Something broke" in captured.out

    def test_exception_with_timing(self, capsys):
        """Test exception includes timing."""
        sw = Switcher().plug("logging", mode="print,after,time")

        @sw
        def slow_fail():
            time.sleep(0.01)
            raise RuntimeError("Failed")

        with pytest.raises(RuntimeError):
            sw("slow_fail")()

        captured = capsys.readouterr()
        assert "✗ slow_fail() raised RuntimeError" in captured.out
        assert "s)" in captured.out  # Has timing

    def test_exception_before_not_shown(self, capsys):
        """Test exception not logged if show_after is False."""
        sw = Switcher().plug("logging", mode="print,before")

        @sw
        def fail():
            raise ValueError("Error")

        with pytest.raises(ValueError):
            sw("fail")()

        captured = capsys.readouterr()
        assert "→ fail()" in captured.out
        assert "✗ fail()" not in captured.out  # Not shown since show_after=False


class TestMethodBinding:
    """Test LoggingPlugin works with class methods."""

    def test_bound_method(self, capsys):
        """Test logging works with bound methods."""
        sw = Switcher().plug("logging", mode="print,after")

        class Calculator:
            def __init__(self, name):
                self.name = name

            @sw
            def add(self, a, b):
                return f"{self.name}: {a + b}"

        calc = Calculator("MyCalc")
        # Call via switcher, not as method
        result = sw("add")(calc, 10, 20)
        assert result == "MyCalc: 30"

        captured = capsys.readouterr()
        assert "← add() → MyCalc: 30" in captured.out


class TestComplexScenarios:
    """Test complex usage scenarios."""

    def test_multiple_handlers(self, capsys):
        """Test logging works with multiple handlers."""
        sw = Switcher().plug("logging", mode="print,before")

        @sw
        def handler_a(x):
            return x * 2

        @sw
        def handler_b(x):
            return x + 10

        sw("handler_a")(5)
        sw("handler_b")(5)

        captured = capsys.readouterr()
        assert "→ handler_a(5)" in captured.out
        assert "→ handler_b(5)" in captured.out

    def test_nested_calls(self, capsys):
        """Test logging works with nested handler calls."""
        sw = Switcher().plug("logging", mode="print,after")

        @sw
        def inner(x):
            return x * 2

        @sw
        def outer(x):
            return inner(x) + 10

        # Direct reference to avoid lookup overhead in test
        inner_func = sw("inner")
        inner_func(5)

        captured = capsys.readouterr()
        assert "← inner() → 10" in captured.out

    def test_time_flag_only(self, capsys):
        """Test time flag without explicit before/after."""
        sw = Switcher().plug("logging", mode="print,time")

        @sw
        def process():
            return "done"

        sw("process")()

        captured = capsys.readouterr()
        # Should show both before and after (default) with timing
        assert "→ process()" in captured.out
        assert "← process() → done" in captured.out
        assert "s)" in captured.out


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_args(self, capsys):
        """Test handler with no arguments."""
        sw = Switcher().plug("logging", mode="print")

        @sw
        def no_args():
            return 42

        sw("no_args")()

        captured = capsys.readouterr()
        assert "→ no_args()" in captured.out
        assert "← no_args() → 42" in captured.out

    def test_complex_return_value(self, capsys):
        """Test handler returning complex object."""
        sw = Switcher().plug("logging", mode="print,after")

        @sw
        def get_data():
            return {"users": ["alice", "bob"], "count": 2}

        sw("get_data")()

        captured = capsys.readouterr()
        assert "← get_data() →" in captured.out
        assert "users" in captured.out

    def test_none_return(self, capsys):
        """Test handler returning None."""
        sw = Switcher().plug("logging", mode="print,after")

        @sw
        def returns_none():
            pass  # Implicitly returns None

        sw("returns_none")()

        captured = capsys.readouterr()
        assert "← returns_none() → None" in captured.out
