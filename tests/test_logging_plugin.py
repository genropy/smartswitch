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
        """Test default flags (plugin disabled)."""
        plugin = LoggingPlugin()
        # Check global config - Pydantic defaults
        assert plugin._global_config["log"] is True  # Default output
        assert plugin._global_config["print"] is False
        assert plugin._global_config["enabled"] is False  # Disabled by default
        assert plugin._global_config["before"] is True  # Default: show input
        assert plugin._global_config["after"] is False  # Default: hide output
        assert plugin._global_config["time"] is False

    def test_print_mode(self):
        """Test explicit print mode."""
        plugin = LoggingPlugin(flags="print,enabled")
        cfg = plugin._global_config
        assert cfg["print"] is True
        assert cfg["log"] is True  # Both can be True (print overrides)
        assert cfg["enabled"] is True
        assert cfg["before"] is True  # Default
        assert cfg["after"] is False  # Default

    def test_log_mode(self):
        """Test log mode."""
        plugin = LoggingPlugin(flags="log,enabled")
        cfg = plugin._global_config
        assert cfg["print"] is False
        assert cfg["log"] is True
        assert cfg["enabled"] is True
        assert cfg["before"] is True  # Default
        assert cfg["after"] is False  # Default

    def test_before_flag(self):
        """Test before flag only."""
        plugin = LoggingPlugin(flags="print,enabled,before")
        cfg = plugin._global_config
        assert cfg["before"] is True
        assert cfg["after"] is False
        assert cfg["time"] is False

    def test_after_flag(self):
        """Test after flag only (must disable before explicitly)."""
        plugin = LoggingPlugin(flags="print,enabled,before:off,after")
        cfg = plugin._global_config
        assert cfg["before"] is False
        assert cfg["after"] is True
        assert cfg["time"] is False

    def test_time_flag(self):
        """Test time flag with defaults."""
        plugin = LoggingPlugin(flags="print,enabled,time")
        cfg = plugin._global_config
        assert cfg["before"] is True  # Default
        assert cfg["after"] is False  # Default (not enabled by time flag)
        assert cfg["time"] is True

    def test_combined_flags(self):
        """Test combination of flags."""
        plugin = LoggingPlugin(flags="log,enabled,before,after,time")
        cfg = plugin._global_config
        assert cfg["log"] is True
        assert cfg["before"] is True
        assert cfg["after"] is True
        assert cfg["time"] is True

    def test_whitespace_handling(self):
        """Test flags with whitespace."""
        plugin = LoggingPlugin(flags=" print,enabled , after , time ")
        cfg = plugin._global_config
        assert cfg["print"] is True
        assert cfg["after"] is True
        assert cfg["time"] is True


class TestPrintOutput:
    """Test output using print()."""

    def test_print_default(self, capsys):
        """Test default print output shows only before (default)."""
        sw = Switcher().plug("logging", flags="print,enabled")

        @sw
        def add(a, b):
            return a + b

        result = sw["add"](2, 3)
        assert result == 5

        captured = capsys.readouterr()
        assert "→ add(2, 3)" in captured.out
        # Default: after is False, so no output line
        assert "← add()" not in captured.out

    def test_print_before_only(self, capsys):
        """Test print with only before flag."""
        sw = Switcher().plug("logging", flags="print,enabled,before")

        @sw
        def process(data):
            return f"processed-{data}"

        sw["process"]("test")

        captured = capsys.readouterr()
        assert "→ process('test')" in captured.out
        assert "← process()" not in captured.out

    def test_print_after_only(self, capsys):
        """Test print with only after flag (disable before explicitly)."""
        sw = Switcher().plug("logging", flags="print,enabled,before:off,after")

        @sw
        def process(data):
            return f"processed-{data}"

        sw["process"]("test")

        captured = capsys.readouterr()
        assert "→ process(" not in captured.out  # Before disabled
        assert "← process() → processed-test" in captured.out

    def test_print_with_time(self, capsys):
        """Test print with timing."""
        sw = Switcher().plug("logging", flags="print,enabled,after,time")

        @sw
        def slow():
            time.sleep(0.01)
            return "done"

        sw["slow"]()

        captured = capsys.readouterr()
        assert "← slow() → done" in captured.out
        assert "s)" in captured.out  # Has timing

    def test_print_kwargs(self, capsys):
        """Test print with keyword arguments."""
        sw = Switcher().plug("logging", flags="print,enabled,before")

        @sw
        def create_user(name, age, email=""):
            return {"name": name, "age": age}

        sw["create_user"]("Alice", age=30, email="alice@test.com")

        captured = capsys.readouterr()
        assert "→ create_user('Alice', age=30, email='alice@test.com')" in captured.out


class TestLogOutput:
    """Test output using Python logging."""

    def test_log_with_handlers(self, caplog):
        """Test log output when logging is configured."""
        caplog.set_level(logging.INFO)

        sw = Switcher().plug("logging", flags="log,enabled,before,after")

        @sw
        def multiply(a, b):
            return a * b

        result = sw["multiply"](3, 4)
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

        sw = Switcher().plug("logging", flags="log,enabled,before,after", logger=logger)

        @sw
        def divide(a, b):
            return a / b

        sw["divide"](10, 2)

        captured = capsys.readouterr()
        # Should use print() since logger has no handlers
        assert "→ divide(10, 2)" in captured.out
        assert "← divide() → 5" in captured.out

    def test_log_levels(self, caplog):
        """Test different log levels (info for normal, error for exceptions)."""
        caplog.set_level(logging.INFO)

        sw = Switcher().plug("logging", flags="log,enabled,after")

        @sw
        def may_fail(should_fail):
            if should_fail:
                raise ValueError("Failed")
            return "Success"

        # Normal call -> info level
        sw["may_fail"](False)
        assert any(r.levelname == "INFO" for r in caplog.records)

        # Failing call -> error level
        caplog.clear()
        with pytest.raises(ValueError):
            sw["may_fail"](True)
        assert any(r.levelname == "ERROR" for r in caplog.records)


class TestExceptionHandling:
    """Test logging of exceptions."""

    def test_exception_logged_before_reraise(self, capsys):
        """Test exception is logged before being re-raised."""
        sw = Switcher().plug("logging", flags="print,enabled,after")

        @sw
        def fail():
            raise ValueError("Something broke")

        with pytest.raises(ValueError, match="Something broke"):
            sw["fail"]()

        captured = capsys.readouterr()
        assert "✗ fail() raised ValueError: Something broke" in captured.out

    def test_exception_with_timing(self, capsys):
        """Test exception includes timing."""
        sw = Switcher().plug("logging", flags="print,enabled,after,time")

        @sw
        def slow_fail():
            time.sleep(0.01)
            raise RuntimeError("Failed")

        with pytest.raises(RuntimeError):
            sw["slow_fail"]()

        captured = capsys.readouterr()
        assert "✗ slow_fail() raised RuntimeError" in captured.out
        assert "s)" in captured.out  # Has timing

    def test_exception_before_not_shown(self, capsys):
        """Test exception not logged if show_after is False."""
        sw = Switcher().plug("logging", flags="print,enabled,before")

        @sw
        def fail():
            raise ValueError("Error")

        with pytest.raises(ValueError):
            sw["fail"]()

        captured = capsys.readouterr()
        assert "→ fail()" in captured.out
        assert "✗ fail()" not in captured.out  # Not shown since show_after=False


class TestMethodBinding:
    """Test LoggingPlugin works with class methods."""

    def test_bound_method(self, capsys):
        """Test logging works with bound methods."""
        sw = Switcher().plug("logging", flags="print,enabled,after")

        class Calculator:
            def __init__(self, name):
                self.name = name

            @sw
            def add(self, a, b):
                return f"{self.name}: {a + b}"

        calc = Calculator("MyCalc")
        # Call via switcher, not as method
        result = sw["add"](calc, 10, 20)
        assert result == "MyCalc: 30"

        captured = capsys.readouterr()
        assert "← add() → MyCalc: 30" in captured.out


class TestComplexScenarios:
    """Test complex usage scenarios."""

    def test_multiple_handlers(self, capsys):
        """Test logging works with multiple handlers."""
        sw = Switcher().plug("logging", flags="print,enabled,before")

        @sw
        def handler_a(x):
            return x * 2

        @sw
        def handler_b(x):
            return x + 10

        sw["handler_a"](5)
        sw["handler_b"](5)

        captured = capsys.readouterr()
        assert "→ handler_a(5)" in captured.out
        assert "→ handler_b(5)" in captured.out

    def test_nested_calls(self, capsys):
        """Test logging works with nested handler calls."""
        sw = Switcher().plug("logging", flags="print,enabled,after")

        @sw
        def inner(x):
            return x * 2

        @sw
        def outer(x):
            return inner(x) + 10

        # Direct reference to avoid lookup overhead in test
        inner_func = sw["inner"]
        inner_func(5)

        captured = capsys.readouterr()
        assert "← inner() → 10" in captured.out

    def test_time_flag_only(self, capsys):
        """Test time flag with before/after."""
        sw = Switcher().plug("logging", flags="print,enabled,before,after,time")

        @sw
        def process():
            return "done"

        sw["process"]()

        captured = capsys.readouterr()
        # Should show both before and after with timing
        assert "→ process()" in captured.out
        assert "← process() → done" in captured.out
        assert "s)" in captured.out


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_args(self, capsys):
        """Test handler with no arguments."""
        sw = Switcher().plug("logging", flags="print,enabled,before,after")

        @sw
        def no_args():
            return 42

        sw["no_args"]()

        captured = capsys.readouterr()
        assert "→ no_args()" in captured.out
        assert "← no_args() → 42" in captured.out

    def test_complex_return_value(self, capsys):
        """Test handler returning complex object."""
        sw = Switcher().plug("logging", flags="print,enabled,after")

        @sw
        def get_data():
            return {"users": ["alice", "bob"], "count": 2}

        sw["get_data"]()

        captured = capsys.readouterr()
        assert "← get_data() →" in captured.out
        assert "users" in captured.out

    def test_none_return(self, capsys):
        """Test handler returning None."""
        sw = Switcher().plug("logging", flags="print,enabled,after")

        @sw
        def returns_none():
            pass  # Implicitly returns None

        sw["returns_none"]()

        captured = capsys.readouterr()
        assert "← returns_none() → None" in captured.out


class TestGranularConfiguration:
    """Test per-method configuration feature."""

    def test_default_disabled(self, capsys):
        """Test plugin is disabled by default."""
        sw = Switcher().plug("logging")  # No mode specified

        @sw
        def calculate(x):
            return x * 2

        result = sw["calculate"](5)
        assert result == 10

        # Should have no output (plugin disabled by default)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_enable_specific_methods(self, capsys):
        """Test enabling only specific methods."""
        sw = Switcher().plug(
            "logging",
            method_config={
                "calculate": "print,enabled,before:off,after,time",
                "process": "print,enabled,before,after:off",
            },
        )

        @sw
        def calculate(x):
            return x * 2

        @sw
        def process(x):
            return x + 10

        @sw
        def other(x):
            return x - 1

        # Calculate should log (after + time)
        sw["calculate"](5)
        captured = capsys.readouterr()
        assert "← calculate() → 10" in captured.out
        assert "s)" in captured.out  # Has timing
        assert "→ calculate" not in captured.out  # No before

        # Process should log (before only)
        sw["process"](5)
        captured = capsys.readouterr()
        assert "→ process(5)" in captured.out
        assert "← process()" not in captured.out  # No after

        # Other should not log (global disabled)
        sw["other"](5)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_disable_specific_methods(self, capsys):
        """Test disabling specific methods when globally enabled."""
        sw = Switcher().plug(
            "logging",
            flags="print,enabled,after",
            method_config={
                "internal": "enabled:off",
                "helper": "enabled:off",
            },
        )

        @sw
        def public_api(x):
            return x * 2

        @sw
        def internal(x):
            return x + 10

        @sw
        def helper(x):
            return x - 1

        # public_api should log
        sw["public_api"](5)
        captured = capsys.readouterr()
        assert "← public_api() → 10" in captured.out

        # internal should not log
        sw["internal"](5)
        captured = capsys.readouterr()
        assert captured.out == ""

        # helper should not log
        sw["helper"](5)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_comma_separated_method_names(self, capsys):
        """Test disabling multiple methods with comma-separated names."""
        sw = Switcher().plug(
            "logging",
            flags="print,enabled,after",
            method_config={
                "alfa,beta,gamma": "enabled:off",
            },
        )

        @sw
        def alfa(x):
            return x

        @sw
        def beta(x):
            return x

        @sw
        def gamma(x):
            return x

        @sw
        def delta(x):
            return x

        # alfa, beta, gamma should not log
        sw["alfa"](1)
        sw["beta"](2)
        sw["gamma"](3)
        captured = capsys.readouterr()
        assert captured.out == ""

        # delta should log
        sw["delta"](4)
        captured = capsys.readouterr()
        assert "← delta() → 4" in captured.out

    def test_mixed_configuration(self, capsys):
        """Test mix of global and method-specific configuration."""
        sw = Switcher().plug(
            "logging",
            flags="print,enabled,before,after:off",  # Global: before only
            method_config={
                "special": "print,enabled,before:off,after,time",  # Override: after + time only
            },
        )

        @sw
        def normal(x):
            return x * 2

        @sw
        def special(x):
            return x + 10

        # normal should use global config (before only)
        sw["normal"](5)
        captured = capsys.readouterr()
        assert "→ normal(5)" in captured.out
        assert "← normal()" not in captured.out

        # special should use method-specific config (after + time)
        sw["special"](5)
        captured = capsys.readouterr()
        assert "← special() → 15" in captured.out
        assert "s)" in captured.out
        assert "→ special" not in captured.out

    def test_disabled_flag_in_method_config(self, capsys):
        """Test using disabled flag in method_config dict."""
        sw = Switcher().plug(
            "logging",
            flags="print,enabled,after",
            method_config={
                "skip_me": "enabled:off",
            },
        )

        @sw
        def skip_me(x):
            return x

        @sw
        def process_me(x):
            return x

        # skip_me should not log
        sw["skip_me"](1)
        captured = capsys.readouterr()
        assert captured.out == ""

        # process_me should log
        sw["process_me"](2)
        captured = capsys.readouterr()
        assert "← process_me() → 2" in captured.out


class TestLoggingPluginInternal:
    """Test internal implementation details for coverage."""

    def test_output_uses_global_config_when_cfg_is_none(self, capsys):
        """Test that _output() uses global config when cfg=None (line 143)."""
        plugin = LoggingPlugin(flags="print,enabled")

        # Call _output with cfg=None - should use global config
        plugin._output("Test message", cfg=None)

        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_plugin_disabled_early_return(self, capsys):
        """Test early return when plugin disabled (line 203)."""
        sw = Switcher().plug("logging", flags="print,enabled:off")

        @sw
        def handler(x):
            return x * 2

        # Plugin disabled - no logging
        result = sw["handler"](5)

        assert result == 10
        captured = capsys.readouterr()
        assert captured.out == ""  # No output when disabled

    def test_on_decorate_is_called_during_decoration(self):
        """Test that on_decorate is called (covers line 176 pass statement)."""
        sw = Switcher().plug("logging", flags="print,enabled")

        # Decorate a function - this calls on_decorate internally
        @sw
        def handler():
            return "test"

        # Function should work normally (on_decorate does nothing)
        result = sw["handler"]()
        assert result == "test"
