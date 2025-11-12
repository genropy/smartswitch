# Logging and History Tracking

**New in v0.4.0**: SmartSwitch includes comprehensive logging and history tracking capabilities for monitoring handler executions, analyzing performance, and debugging.

---

## Quick Start

<!-- test: test_logging.py::test_enable_log_silent_mode -->
```python
from smartswitch import Switcher

sw = Switcher(name="test")

@sw
def my_handler(x: int) -> int:
    return x * 2

# Enable silent logging (history only, no console output)
sw.enable_log(mode="silent")

# Call handler
result = sw("my_handler")(5)  # Returns 10

# Check history
history = sw.get_log_history()
print(history[0])
# {'handler': 'my_handler', 'switcher': 'test',
#  'args': (5,), 'kwargs': {}, 'result': 10, 'elapsed': 0.0001, ...}
```

---

## Logging Modes

SmartSwitch supports three logging modes:

### Silent Mode (Default)

**History tracking only** - zero overhead, no console output:

<!-- test: test_logging.py::test_enable_log_silent_mode -->
```python
sw.enable_log(mode="silent")
```

Use this for:
- Performance analysis
- Debugging in production
- Recording call history without noise

### Log Mode

**Console logging only** - immediate feedback, no history:

```python
sw.enable_log(mode="log")
```

Logs to stdout/stderr using Python's `logging` module.

### Both Mode

**History tracking + console logging**:

```python
sw.enable_log(mode="both")
```

---

## Handler-Specific Logging

Enable logging for specific handlers only:

<!-- test: test_logging.py::test_enable_log_for_specific_handlers -->
```python
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
sw("handler1")(5)  # Logged
sw("handler2")(5)  # Not logged

# History contains only handler1 calls
history = sw.get_log_history()
assert len(history) == 1
assert history[0]["handler"] == "handler1"
```

### Disabling Specific Handlers

<!-- test: test_logging.py::test_disable_log_specific_handler -->
```python
# Enable logging for all handlers
sw.enable_log(mode="silent")

# Disable for specific handler
sw.disable_log("handler2")

sw("handler1")(5)  # Logged
sw("handler2")(5)  # Not logged
```

### Disabling Globally

<!-- test: test_logging.py::test_disable_log_globally -->
```python
sw.enable_log(mode="silent")
sw("my_handler")(5)  # Logged

sw.disable_log()  # Disable all logging

sw("my_handler")(10)  # Not logged
```

---

## Querying History

### Basic Queries

Get all history:

```python
history = sw.get_log_history()
```

Get last N entries:

<!-- test: test_logging.py::test_get_log_history_last -->
```python
# Get last 2 entries
history = sw.get_log_history(last=2)
```

Get first N entries:

<!-- test: test_logging.py::test_get_log_history_first -->
```python
# Get first 2 entries
history = sw.get_log_history(first=2)
```

Filter by handler name:

<!-- test: test_logging.py::test_get_log_history_by_handler -->
```python
history = sw.get_log_history(handler="handler1")
```

---

## Performance Analysis

### Slowest Executions

<!-- test: test_logging.py::test_get_log_history_slowest -->
```python
@sw
def slow_handler(duration: float) -> None:
    time.sleep(duration)

sw.enable_log(mode="silent", time=True)

handler = sw("slow_handler")
handler(0.01)
handler(0.03)
handler(0.02)

# Get 2 slowest executions
history = sw.get_log_history(slowest=2)
# Returns entries in descending order by elapsed time
```

### Fastest Executions

<!-- test: test_logging.py::test_get_log_history_fastest -->
```python
# Get 2 fastest executions
history = sw.get_log_history(fastest=2)
# Returns entries in ascending order by elapsed time
```

### Time Threshold

<!-- test: test_logging.py::test_get_log_history_slower_than -->
```python
# Get all entries slower than 15ms
history = sw.get_log_history(slower_than=0.015)
```

---

## Error Tracking

### Filter by Success/Failure

<!-- test: test_logging.py::test_get_log_history_errors_only -->
```python
@sw
def maybe_fail(should_fail: bool) -> str:
    if should_fail:
        raise ValueError("failed")
    return "success"

sw.enable_log(mode="silent")

handler = sw("maybe_fail")
handler(False)  # Success

with pytest.raises(ValueError):
    handler(True)  # Error

# Get errors only
errors = sw.get_log_history(errors=True)
assert all("exception" in e for e in errors)

# Get successes only
successes = sw.get_log_history(errors=False)
assert all("exception" not in e for e in successes)
```

### Exception Details

<!-- test: test_logging.py::test_log_history_with_exception -->
```python
@sw
def failing_handler(x: int) -> int:
    raise ValueError("test error")

sw.enable_log(mode="silent")

with pytest.raises(ValueError):
    sw("failing_handler")(5)

# History contains exception details
history = sw.get_log_history()
assert "exception" in history[0]
assert history[0]["exception"]["type"] == "ValueError"
assert history[0]["exception"]["message"] == "test error"
```

---

## Statistics

Get aggregate statistics for all handlers:

<!-- test: test_logging.py::test_get_log_stats -->
```python
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

sw("handler1")(5)
sw("handler1")(10)
sw("handler2")(False)

with pytest.raises(ValueError):
    sw("handler2")(True)

stats = sw.get_log_stats()

# handler1 stats
assert stats["handler1"]["calls"] == 2
assert stats["handler1"]["errors"] == 0
assert stats["handler1"]["avg_time"] > 0
assert stats["handler1"]["min_time"] > 0
assert stats["handler1"]["max_time"] > 0

# handler2 stats
assert stats["handler2"]["calls"] == 2
assert stats["handler2"]["errors"] == 1
```

Returns:
```python
{
    "handler1": {
        "calls": 2,
        "errors": 0,
        "avg_time": 0.010234,
        "min_time": 0.010123,
        "max_time": 0.010345,
        "total_time": 0.020468
    },
    "handler2": {
        "calls": 2,
        "errors": 1,
        "avg_time": 0.000012,
        "min_time": 0.000010,
        "max_time": 0.000014,
        "total_time": 0.000024
    }
}
```

---

## History Management

### Clear History

<!-- test: test_logging.py::test_clear_log_history -->
```python
sw.enable_log(mode="silent")
sw("my_handler")(5)

assert len(sw.get_log_history()) == 1

sw.clear_log_history()
assert len(sw.get_log_history()) == 0
```

### Max History Size

<!-- test: test_logging.py::test_max_history_limit -->
```python
# Set max history to 3 entries
sw.enable_log(mode="silent", max_history=3)

handler = sw("my_handler")

# Call 5 times
for i in range(5):
    handler(i)

# Only last 3 entries kept
history = sw.get_log_history()
assert len(history) == 3
assert history[0]["args"] == (2,)
assert history[1]["args"] == (3,)
assert history[2]["args"] == (4,)
```

Default: 1000 entries

---

## Export History

### Export to JSON

<!-- test: test_logging.py::test_export_log_history -->
```python
sw.enable_log(mode="silent")
sw("my_handler")(5)
sw("my_handler")(10)

# Export to JSON file
sw.export_log_history("history.json")

# Read back
import json
with open("history.json") as f:
    data = json.load(f)

assert len(data) == 2
assert data[0]["handler"] == "my_handler"
```

### Log to File (JSONL)

<!-- test: test_logging.py::test_log_file_jsonl -->
```python
# Enable logging with file output
sw.enable_log(mode="silent", log_file="calls.jsonl")

sw("my_handler")(5)
sw("my_handler")(10)

# Read JSONL file
with open("calls.jsonl") as f:
    lines = f.readlines()

# Each line is a JSON object
entry1 = json.loads(lines[0])
entry2 = json.loads(lines[1])

assert entry1["handler"] == "my_handler"
assert entry2["handler"] == "my_handler"
```

JSONL format: One JSON object per line, ideal for streaming and log aggregation tools.

---

## Configuration Options

```python
sw.enable_log(
    *handler_names,           # Optional: specific handlers to log
    mode="silent",            # "silent", "log", or "both"
    before=True,              # Log before handler execution
    after=True,               # Log after handler execution
    time=True,                # Track execution time
    log_file=None,            # Optional: path to JSONL log file
    log_format="json",        # Format: "json" (only option currently)
    max_history=1000,         # Max entries in memory
)
```

---

## Class-Based Usage

<!-- test: test_logging.py::test_logging_with_instance_methods -->
```python
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
assert history[0]["handler"] == "get_value"
assert history[0]["result"] == 42
```

---

## Introspection Preservation

Logging preserves the `__wrapped__` attribute for introspection:

<!-- test: test_logging.py::test_logging_preserves_wrapped -->
```python
@sw
def my_handler(x: int, y: int = 10) -> int:
    """Add two numbers."""
    return x + y

sw.enable_log(mode="silent")
handler = sw("my_handler")

# __wrapped__ still accessible
assert hasattr(handler, "__wrapped__")
assert handler.__wrapped__.__doc__ == "Add two numbers."
```

---

## Performance Impact

**Silent mode**: Near-zero overhead when disabled, minimal overhead when enabled (~2-5 microseconds per call for history recording).

**Log mode**: Depends on logging backend configuration.

**Best practices**:
- Use `mode="silent"` in production for zero-noise monitoring
- Limit `max_history` to prevent memory growth
- Use `log_file` for persistent logs without memory overhead

---

## See Also

- [Best Practices](best-practices.md) - Production patterns
- [API Reference](../api/switcher.md) - Complete API documentation
