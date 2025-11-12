"""
Tests for LoggingPlugin.

Comprehensive tests for the new plugin-based logging system.
"""

import time
import tempfile
import json
from pathlib import Path
from smartswitch import Switcher


class TestLoggingPluginBasics:
    """Basic LoggingPlugin functionality tests."""

    def test_plugin_registration(self):
        """Test that plugin can be registered."""
        sw = Switcher(name="test").plug("logging", mode="silent")
        assert len(sw._plugins) == 1

    def test_plugin_chaining(self):
        """Test that plug() returns self for chaining."""
        sw = Switcher(name="api").plug("logging", mode="silent", time=True)
        assert isinstance(sw, Switcher)
        assert sw.name == "api"

    def test_basic_tracking(self):
        """Test basic call tracking."""
        sw = Switcher(name="test").plug("logging", mode="silent", time=True)

        @sw
        def my_handler(x):
            return x * 2

        result = sw("my_handler")(5)
        assert result == 10

        history = sw.logger.history()
        assert len(history) == 1
        assert history[0]["handler"] == "my_handler"
        assert history[0]["switcher"] == "test"
        assert history[0]["result"] == 10
        assert "elapsed" in history[0]
        assert history[0]["elapsed"] >= 0

    def test_multiple_handlers(self):
        """Test tracking multiple different handlers."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def add(a, b):
            return a + b

        @sw
        def multiply(a, b):
            return a * b

        @sw
        def subtract(a, b):
            return a - b

        sw("add")(2, 3)
        sw("multiply")(4, 5)
        sw("subtract")(10, 3)

        history = sw.logger.history()
        assert len(history) == 3
        assert history[0]["handler"] == "add"
        assert history[1]["handler"] == "multiply"
        assert history[2]["handler"] == "subtract"

    def test_multiple_calls_same_handler(self):
        """Test tracking multiple calls to the same handler."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def increment(x):
            return x + 1

        for i in range(5):
            sw("increment")(i)

        history = sw.logger.history()
        assert len(history) == 5
        assert all(e["handler"] == "increment" for e in history)


class TestLoggingPluginModes:
    """Test different logging modes."""

    def test_mode_silent(self):
        """Test silent mode (history only, no external logging)."""
        sw = Switcher().plug("logging", mode="silent", time=True)

        @sw
        def handler(x):
            return x

        sw("handler")(42)

        history = sw.logger.history()
        assert len(history) == 1
        assert "elapsed" in history[0]

    def test_mode_log(self):
        """Test log mode (Python logging, no history)."""
        import logging

        # Create custom logger to capture logs
        logger = logging.getLogger("test_smartswitch")
        logger.setLevel(logging.INFO)

        # Use in-memory handler
        from io import StringIO
        import logging

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)

        sw = Switcher().plug("logging", mode="log", time=True, logger=logger)

        @sw
        def my_handler(x):
            return x * 2

        sw("my_handler")(5)

        # Log mode doesn't track history
        history = sw.logger.history()
        assert len(history) == 0

        # But it does log
        log_output = stream.getvalue()
        assert "Calling my_handler" in log_output or "returned" in log_output

    def test_mode_both(self):
        """Test both mode (history AND Python logging)."""
        import logging

        logger = logging.getLogger("test_smartswitch_both")
        logger.setLevel(logging.INFO)

        sw = Switcher().plug("logging", mode="both", time=True, logger=logger)

        @sw
        def handler(x):
            return x

        sw("handler")(42)

        # Both mode tracks history
        history = sw.logger.history()
        assert len(history) == 1

    def test_set_log_mode(self):
        """Test changing log mode dynamically."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def handler():
            return 1

        sw("handler")()
        assert len(sw.logger.history()) == 1

        # Change to log mode (no history)
        sw.logger.set_mode("log")
        sw("handler")()
        assert len(sw.logger.history()) == 1  # No new entry

        # Change back to silent
        sw.logger.set_mode("silent")
        sw("handler")()
        assert len(sw.logger.history()) == 2


class TestLoggingPluginHistory:
    """Test history tracking and queries."""

    def test_args_and_kwargs_tracking(self):
        """Test that args and kwargs are tracked."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def handler(a, b, c=10):
            return a + b + c

        sw("handler")(1, 2, c=3)

        history = sw.logger.history()
        assert history[0]["args"] == (1, 2)
        assert history[0]["kwargs"] == {"c": 3}

    def test_result_tracking(self):
        """Test that results are tracked."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def handler(x):
            return x * 2

        sw("handler")(5)
        sw("handler")(10)

        history = sw.logger.history()
        assert history[0]["result"] == 10
        assert history[1]["result"] == 20

    def test_timestamp_tracking(self):
        """Test that timestamps are tracked."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def handler():
            return 1

        before = time.time()
        sw("handler")()
        after = time.time()

        history = sw.logger.history()
        assert before <= history[0]["timestamp"] <= after

    def test_elapsed_time_tracking(self):
        """Test that elapsed time is tracked when enabled."""
        sw = Switcher().plug("logging", mode="silent", time=True)

        @sw
        def slow_handler():
            time.sleep(0.01)
            return 1

        sw("slow_handler")()

        history = sw.logger.history()
        assert "elapsed" in history[0]
        assert history[0]["elapsed"] >= 0.01

    def test_elapsed_time_disabled(self):
        """Test that elapsed time is not tracked when disabled."""
        sw = Switcher().plug("logging", mode="silent", time=False)

        @sw
        def handler():
            return 1

        sw("handler")()

        history = sw.logger.history()
        assert "elapsed" not in history[0]


class TestLoggingPluginExceptions:
    """Test exception tracking."""

    def test_exception_tracking(self):
        """Test that exceptions are tracked."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def failing_handler():
            raise ValueError("test error")

        try:
            sw("failing_handler")()
        except ValueError:
            pass

        history = sw.logger.history()
        assert len(history) == 1
        assert "exception" in history[0]
        assert history[0]["exception"]["type"] == "ValueError"
        assert history[0]["exception"]["message"] == "test error"

    def test_exception_with_timing(self):
        """Test that timing works even when exception is raised."""
        sw = Switcher().plug("logging", mode="silent", time=True)

        @sw
        def failing_handler():
            time.sleep(0.01)
            raise RuntimeError("error")

        try:
            sw("failing_handler")()
        except RuntimeError:
            pass

        history = sw.logger.history()
        assert "elapsed" in history[0]
        assert history[0]["elapsed"] >= 0.01
        assert "exception" in history[0]

    def test_exception_reraise(self):
        """Test that exceptions are re-raised."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def failing_handler():
            raise ValueError("test")

        try:
            sw("failing_handler")()
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert str(e) == "test"


class TestLoggingPluginQueryFilters:
    """Test history query filters."""

    def test_filter_by_handler(self):
        """Test filtering by handler name."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def fast():
            return "fast"

        @sw
        def slow():
            return "slow"

        sw("fast")()
        sw("slow")()
        sw("fast")()
        sw("slow")()

        fast_history = sw.logger.history(handler="fast")
        assert len(fast_history) == 2
        assert all(e["handler"] == "fast" for e in fast_history)

        slow_history = sw.logger.history(handler="slow")
        assert len(slow_history) == 2
        assert all(e["handler"] == "slow" for e in slow_history)

    def test_filter_last_n(self):
        """Test getting last N entries."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def handler(x):
            return x

        for i in range(10):
            sw("handler")(i)

        history = sw.logger.history(last=3)
        assert len(history) == 3
        assert history[0]["args"] == (7,)
        assert history[1]["args"] == (8,)
        assert history[2]["args"] == (9,)

    def test_filter_first_n(self):
        """Test getting first N entries."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def handler(x):
            return x

        for i in range(10):
            sw("handler")(i)

        history = sw.logger.history(first=3)
        assert len(history) == 3
        assert history[0]["args"] == (0,)
        assert history[1]["args"] == (1,)
        assert history[2]["args"] == (2,)

    def test_filter_errors_only(self):
        """Test filtering only errors."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def handler(x):
            if x < 0:
                raise ValueError("negative")
            return x

        sw("handler")(1)
        try:
            sw("handler")(-1)
        except ValueError:
            pass
        sw("handler")(2)
        try:
            sw("handler")(-2)
        except ValueError:
            pass

        errors = sw.logger.history(errors=True)
        assert len(errors) == 2
        assert all("exception" in e for e in errors)

    def test_filter_success_only(self):
        """Test filtering only successful calls."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def handler(x):
            if x < 0:
                raise ValueError("negative")
            return x

        sw("handler")(1)
        try:
            sw("handler")(-1)
        except ValueError:
            pass
        sw("handler")(2)

        successes = sw.logger.history(errors=False)
        assert len(successes) == 2
        assert all("exception" not in e for e in successes)

    def test_filter_slowest(self):
        """Test getting slowest N calls."""
        sw = Switcher().plug("logging", mode="silent", time=True)

        @sw
        def handler(sleep_time):
            time.sleep(sleep_time)
            return sleep_time

        sw("handler")(0.01)
        sw("handler")(0.03)
        sw("handler")(0.02)

        slowest = sw.logger.history(slowest=2)
        assert len(slowest) == 2
        # Slowest first (descending order)
        assert slowest[0]["elapsed"] > slowest[1]["elapsed"]
        # Should be the 0.03 and 0.02 calls
        assert slowest[0]["elapsed"] >= 0.03

    def test_filter_fastest(self):
        """Test getting fastest N calls."""
        sw = Switcher().plug("logging", mode="silent", time=True)

        @sw
        def handler(sleep_time):
            time.sleep(sleep_time)
            return sleep_time

        sw("handler")(0.03)
        sw("handler")(0.01)
        sw("handler")(0.02)

        fastest = sw.logger.history(fastest=2)
        assert len(fastest) == 2
        # Fastest first (ascending order)
        assert fastest[0]["elapsed"] < fastest[1]["elapsed"]
        # All should have elapsed time recorded
        assert all(e["elapsed"] > 0 for e in fastest)

    def test_filter_slower_than(self):
        """Test filtering calls slower than threshold."""
        sw = Switcher().plug("logging", mode="silent", time=True)

        @sw
        def handler(sleep_time):
            time.sleep(sleep_time)
            return sleep_time

        sw("handler")(0.01)
        sw("handler")(0.05)
        sw("handler")(0.02)
        sw("handler")(0.04)

        # Get all entries and check they are in order by duration
        all_history = sw.logger.history()
        assert len(all_history) == 4
        # Find the shortest duration (should be first call with 0.01)
        shortest = min(e["elapsed"] for e in all_history)
        # Get entries slower than the shortest
        slow_calls = sw.logger.history(slower_than=shortest)
        assert len(slow_calls) == 3  # The 0.05, 0.02, and 0.04 calls
        assert all(e["elapsed"] > shortest for e in slow_calls)


class TestLoggingPluginHistoryManagement:
    """Test history management features."""

    def test_clear_history(self):
        """Test clearing history."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def handler():
            return 42

        sw("handler")()
        sw("handler")()
        assert len(sw.logger.history()) == 2

        sw.logger.clear()
        assert len(sw.logger.history()) == 0

    def test_max_history_limit(self):
        """Test that history is limited to max_history."""
        sw = Switcher().plug("logging", mode="silent", max_history=5)

        @sw
        def handler(x):
            return x

        for i in range(10):
            sw("handler")(i)

        history = sw.logger.history()
        assert len(history) == 5
        # Should keep the last 5
        assert history[0]["args"] == (5,)
        assert history[4]["args"] == (9,)

    def test_export_history(self):
        """Test exporting history to JSON file."""
        sw = Switcher().plug("logging", mode="silent", time=True)

        @sw
        def handler(x):
            return x * 2

        sw("handler")(5)
        sw("handler")(10)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "history.json"
            sw.logger.export(str(filepath))

            assert filepath.exists()

            with open(filepath) as f:
                data = json.load(f)

            assert len(data) == 2
            assert data[0]["handler"] == "handler"
            assert "elapsed" in data[0]


class TestLoggingPluginFileLogging:
    """Test real-time file logging."""

    def test_configure_log_file(self):
        """Test configuring log file for real-time logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "calls.jsonl"

            sw = Switcher().plug("logging", mode="silent")
            sw.logger.set_file(str(logfile))

            @sw
            def handler(x):
                return x * 2

            sw("handler")(5)
            sw("handler")(10)

            assert logfile.exists()

            # Read JSONL file
            lines = logfile.read_text().strip().split("\n")
            assert len(lines) == 2

            entry1 = json.loads(lines[0])
            assert entry1["handler"] == "handler"

    def test_disable_log_file(self):
        """Test disabling file logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "calls.jsonl"

            sw = Switcher().plug("logging", mode="silent")
            sw.logger.set_file(str(logfile))

            @sw
            def handler():
                return 1

            sw("handler")()
            assert logfile.exists()

            # Disable file logging
            sw.logger.set_file(None)
            sw("handler")()

            # Should only have 1 entry
            lines = logfile.read_text().strip().split("\n")
            assert len(lines) == 1


class TestLoggingPluginEdgeCases:
    """Test edge cases and special scenarios."""

    def test_no_plugins(self):
        """Test Switcher without plugins works normally."""
        sw = Switcher()

        @sw
        def handler(x):
            return x * 2

        result = sw("handler")(5)
        assert result == 10

    def test_handler_with_no_args(self):
        """Test handler with no arguments."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def handler():
            return 42

        sw("handler")()

        history = sw.logger.history()
        assert history[0]["args"] == ()
        assert history[0]["kwargs"] == {}

    def test_handler_with_only_kwargs(self):
        """Test handler with only keyword arguments."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def handler(a=1, b=2):
            return a + b

        sw("handler")(a=10, b=20)

        history = sw.logger.history()
        assert history[0]["args"] == ()
        assert history[0]["kwargs"] == {"a": 10, "b": 20}

    def test_wrapped_attribute(self):
        """Test that __wrapped__ attribute is preserved."""
        sw = Switcher().plug("logging", mode="silent")

        @sw
        def original_handler():
            """Original docstring."""
            return 42

        wrapped = sw._handlers["original_handler"]
        assert hasattr(wrapped, "__wrapped__")
        assert wrapped.__wrapped__.__doc__ == "Original docstring."

    def test_multiple_plugins_same_handler(self):
        """Test that plugins can be composed (future-proofing)."""
        # For now we only have LoggingPlugin, but test the mechanism
        sw = Switcher()
        sw.plug("logging", mode="silent")

        @sw
        def handler(x):
            return x

        result = sw("handler")(42)
        assert result == 42

        history = sw.logger.history()
        assert len(history) == 1


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
