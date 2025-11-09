"""
Tests for logging functionality.
"""

import json
import tempfile
import time
from pathlib import Path

import pytest
from smartswitch import Switcher


def test_enable_log_silent_mode():
    """Test enable_log with silent mode (history only, no logging)."""
    sw = Switcher(name="test")

    @sw
    def my_handler(x: int) -> int:
        return x * 2

    # Enable silent logging
    sw.enable_log(mode="silent")

    # Call handler
    handler = sw("my_handler")
    result = handler(5)

    assert result == 10

    # Check history
    history = sw.get_log_history()
    assert len(history) == 1
    assert history[0]["handler"] == "my_handler"
    assert history[0]["args"] == (5,)
    assert history[0]["result"] == 10
    assert "elapsed" in history[0]


def test_enable_log_for_specific_handlers():
    """Test enabling logging for specific handlers only."""
    sw = Switcher(name="test")

    @sw
    def handler1(x: int) -> int:
        return x * 2

    @sw
    def handler2(x: int) -> int:
        return x * 3

    # Enable logging only for handler1
    sw.enable_log("handler1", mode="silent")

    # Call both handlers
    sw("handler1")(5)
    sw("handler2")(5)

    # Check history - only handler1 should be logged
    history = sw.get_log_history()
    assert len(history) == 1
    assert history[0]["handler"] == "handler1"


def test_disable_log_specific_handler():
    """Test disabling logging for specific handler."""
    sw = Switcher(name="test")

    @sw
    def handler1(x: int) -> int:
        return x * 2

    @sw
    def handler2(x: int) -> int:
        return x * 3

    # Enable logging for all
    sw.enable_log(mode="silent")

    # Disable for handler2
    sw.disable_log("handler2")

    # Call both
    sw("handler1")(5)
    sw("handler2")(5)

    # Only handler1 should be logged
    history = sw.get_log_history()
    assert len(history) == 1
    assert history[0]["handler"] == "handler1"


def test_disable_log_globally():
    """Test disabling logging globally."""
    sw = Switcher(name="test")

    @sw
    def my_handler(x: int) -> int:
        return x * 2

    # Enable logging
    sw.enable_log(mode="silent")

    # Call handler
    sw("my_handler")(5)
    assert len(sw.get_log_history()) == 1

    # Disable globally
    sw.disable_log()

    # Call again
    sw("my_handler")(10)

    # History should still have only 1 entry (from before disable)
    assert len(sw.get_log_history()) == 1


def test_log_history_with_exception():
    """Test that exceptions are logged in history."""
    sw = Switcher(name="test")

    @sw
    def failing_handler(x: int) -> int:
        raise ValueError("test error")

    sw.enable_log(mode="silent")

    handler = sw("failing_handler")

    with pytest.raises(ValueError, match="test error"):
        handler(5)

    # Check history has exception
    history = sw.get_log_history()
    assert len(history) == 1
    assert "exception" in history[0]
    assert history[0]["exception"]["type"] == "ValueError"
    assert history[0]["exception"]["message"] == "test error"


def test_get_log_history_last():
    """Test get_log_history with last parameter."""
    sw = Switcher(name="test")

    @sw
    def my_handler(x: int) -> int:
        return x * 2

    sw.enable_log(mode="silent")

    handler = sw("my_handler")

    # Call 5 times
    for i in range(5):
        handler(i)

    # Get last 2
    history = sw.get_log_history(last=2)
    assert len(history) == 2
    assert history[0]["args"] == (3,)
    assert history[1]["args"] == (4,)


def test_get_log_history_first():
    """Test get_log_history with first parameter."""
    sw = Switcher(name="test")

    @sw
    def my_handler(x: int) -> int:
        return x * 2

    sw.enable_log(mode="silent")

    handler = sw("my_handler")

    # Call 5 times
    for i in range(5):
        handler(i)

    # Get first 2
    history = sw.get_log_history(first=2)
    assert len(history) == 2
    assert history[0]["args"] == (0,)
    assert history[1]["args"] == (1,)


def test_get_log_history_by_handler():
    """Test filtering history by handler name."""
    sw = Switcher(name="test")

    @sw
    def handler1(x: int) -> int:
        return x * 2

    @sw
    def handler2(x: int) -> int:
        return x * 3

    sw.enable_log(mode="silent")

    sw("handler1")(5)
    sw("handler2")(5)
    sw("handler1")(10)

    # Filter by handler1
    history = sw.get_log_history(handler="handler1")
    assert len(history) == 2
    assert all(e["handler"] == "handler1" for e in history)


def test_get_log_history_slowest():
    """Test getting slowest executions."""
    sw = Switcher(name="test")

    @sw
    def slow_handler(duration: float) -> None:
        time.sleep(duration)

    sw.enable_log(mode="silent", time=True)

    handler = sw("slow_handler")

    # Call with different durations
    handler(0.01)
    handler(0.03)
    handler(0.02)

    # Get slowest 2
    history = sw.get_log_history(slowest=2)
    assert len(history) == 2
    # Should be in descending order
    assert history[0]["elapsed"] > history[1]["elapsed"]
    # Slowest should be ~0.03s
    assert history[0]["elapsed"] > 0.025


def test_get_log_history_fastest():
    """Test getting fastest executions."""
    sw = Switcher(name="test")

    @sw
    def slow_handler(duration: float) -> None:
        time.sleep(duration)

    sw.enable_log(mode="silent", time=True)

    handler = sw("slow_handler")

    # Call with different durations
    handler(0.01)
    handler(0.03)
    handler(0.02)

    # Get fastest 2
    history = sw.get_log_history(fastest=2)
    assert len(history) == 2
    # Should be in ascending order (fastest first)
    assert history[0]["elapsed"] < history[1]["elapsed"]
    # All should have elapsed time recorded
    assert all(e["elapsed"] > 0 for e in history)


def test_get_log_history_errors_only():
    """Test filtering history to errors only."""
    sw = Switcher(name="test")

    @sw
    def maybe_fail(should_fail: bool) -> str:
        if should_fail:
            raise ValueError("failed")
        return "success"

    sw.enable_log(mode="silent")

    handler = sw("maybe_fail")

    # Mix of success and failure
    handler(False)
    with pytest.raises(ValueError):
        handler(True)
    handler(False)
    with pytest.raises(ValueError):
        handler(True)

    # Get errors only
    history = sw.get_log_history(errors=True)
    assert len(history) == 2
    assert all("exception" in e for e in history)

    # Get successes only
    history = sw.get_log_history(errors=False)
    assert len(history) == 2
    assert all("exception" not in e for e in history)


def test_get_log_history_slower_than():
    """Test filtering by elapsed time threshold."""
    sw = Switcher(name="test")

    @sw
    def slow_handler(duration: float) -> None:
        time.sleep(duration)

    sw.enable_log(mode="silent", time=True)

    handler = sw("slow_handler")

    # Call with different durations
    handler(0.01)
    handler(0.03)
    handler(0.02)

    # Get all entries and check they are in order by duration
    all_history = sw.get_log_history()
    assert len(all_history) == 3
    # Find the shortest duration (should be first call with 0.01)
    shortest = min(e["elapsed"] for e in all_history)
    # Get entries slower than the shortest
    history = sw.get_log_history(slower_than=shortest)
    assert len(history) == 2  # The 0.03 and 0.02 calls
    assert all(e["elapsed"] > shortest for e in history)


def test_get_log_stats():
    """Test log statistics."""
    sw = Switcher(name="test")

    @sw
    def handler1(x: int) -> int:
        time.sleep(0.01)
        return x * 2

    @sw
    def handler2(should_fail: bool) -> str:
        if should_fail:
            raise ValueError("error")
        return "ok"

    sw.enable_log(mode="silent", time=True)

    # Call handlers
    sw("handler1")(5)
    sw("handler1")(10)
    sw("handler2")(False)
    with pytest.raises(ValueError):
        sw("handler2")(True)

    stats = sw.get_log_stats()

    # Check handler1 stats
    assert stats["handler1"]["calls"] == 2
    assert stats["handler1"]["errors"] == 0
    assert stats["handler1"]["avg_time"] > 0
    assert stats["handler1"]["min_time"] > 0
    assert stats["handler1"]["max_time"] > 0

    # Check handler2 stats
    assert stats["handler2"]["calls"] == 2
    assert stats["handler2"]["errors"] == 1


def test_clear_log_history():
    """Test clearing log history."""
    sw = Switcher(name="test")

    @sw
    def my_handler(x: int) -> int:
        return x * 2

    sw.enable_log(mode="silent")

    sw("my_handler")(5)
    assert len(sw.get_log_history()) == 1

    sw.clear_log_history()
    assert len(sw.get_log_history()) == 0


def test_export_log_history():
    """Test exporting log history to JSON file."""
    sw = Switcher(name="test")

    @sw
    def my_handler(x: int) -> int:
        return x * 2

    sw.enable_log(mode="silent")

    sw("my_handler")(5)
    sw("my_handler")(10)

    # Export to temp file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        filepath = f.name

    try:
        sw.export_log_history(filepath)

        # Read back
        with open(filepath) as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["handler"] == "my_handler"
        assert data[1]["handler"] == "my_handler"
    finally:
        Path(filepath).unlink()


def test_log_file_jsonl():
    """Test logging to JSONL file."""
    sw = Switcher(name="test")

    @sw
    def my_handler(x: int) -> int:
        return x * 2

    # Create temp file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
        filepath = f.name

    try:
        sw.enable_log(mode="silent", log_file=filepath)

        sw("my_handler")(5)
        sw("my_handler")(10)

        # Read JSONL file
        with open(filepath) as f:
            lines = f.readlines()

        assert len(lines) == 2

        # Parse each line as JSON
        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])

        assert entry1["handler"] == "my_handler"
        assert entry2["handler"] == "my_handler"
    finally:
        Path(filepath).unlink()


def test_max_history_limit():
    """Test that history is limited to max_history entries."""
    sw = Switcher(name="test")

    @sw
    def my_handler(x: int) -> int:
        return x * 2

    # Set small max_history
    sw.enable_log(mode="silent", max_history=3)

    handler = sw("my_handler")

    # Call 5 times
    for i in range(5):
        handler(i)

    # Should only have last 3
    history = sw.get_log_history()
    assert len(history) == 3
    assert history[0]["args"] == (2,)
    assert history[1]["args"] == (3,)
    assert history[2]["args"] == (4,)


def test_logging_with_instance_methods():
    """Test logging with instance methods."""

    class MyAPI:
        sw = Switcher(name="api")

        def __init__(self):
            self.value = 42

        @sw
        def get_value(self) -> int:
            return self.value

    api = MyAPI()
    api.sw.enable_log(mode="silent")

    # Call method
    result = api.sw("get_value")()
    assert result == 42

    # Check history
    history = api.sw.get_log_history()
    assert len(history) == 1
    assert history[0]["handler"] == "get_value"
    assert history[0]["result"] == 42


def test_logging_preserves_wrapped():
    """Test that __wrapped__ attribute is preserved with logging."""
    sw = Switcher(name="test")

    @sw
    def my_handler(x: int, y: int = 10) -> int:
        """Add two numbers."""
        return x + y

    sw.enable_log(mode="silent")

    handler = sw("my_handler")

    # Should still have __wrapped__
    assert hasattr(handler, "__wrapped__")
    assert handler.__wrapped__.__doc__ == "Add two numbers."


def test_invalid_log_mode():
    """Test that invalid log mode raises ValueError."""
    sw = Switcher(name="test")

    with pytest.raises(ValueError, match="Invalid mode"):
        sw.enable_log(mode="invalid")
