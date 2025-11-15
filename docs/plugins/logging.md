# LoggingPlugin

**New in v0.9.2**: Completely redesigned LoggingPlugin with composable mode flags for real-time output.

The LoggingPlugin provides real-time visibility into handler calls with flexible output options. Perfect for debugging, tutorials, and monitoring.

---

## Quick Start

```python
from smartswitch import Switcher

# Create switcher with logging
sw = Switcher().plug('logging', mode='print')

@sw
def add(a, b):
    return a + b

# Logs input and output automatically
result = sw('add')(2, 3)
# Output:
# → add(2, 3)
# ← add() → 5
```

---

## Mode Flags

The LoggingPlugin uses **composable mode flags** - combine them to control what gets logged.

### Output Destination (Required)

Choose **one** of these:

- **`print`**: Output to stdout via `print()`
- **`log`**: Output via Python's logging system

```python
# Use print (tutorial-friendly, no setup needed)
sw = Switcher().plug('logging', mode='print')

# Use Python logging (production-ready)
import logging
logging.basicConfig(level=logging.INFO)
sw = Switcher().plug('logging', mode='log')
```

### Content Flags (Optional)

Add these to control **what** gets logged:

- **`before`**: Show input parameters
- **`after`**: Show return value
- **`time`**: Include execution time

**Default**: If no content flags specified, shows both `before` and `after`.

```python
# Only show output
sw = Switcher().plug('logging', mode='print,after')

# Only show input
sw = Switcher().plug('logging', mode='print,before')

# Show output with timing
sw = Switcher().plug('logging', mode='print,after,time')

# Show everything with timing
sw = Switcher().plug('logging', mode='print,before,after,time')
```

---

## Output Formats

### Before (Input Parameters)

```python
sw = Switcher().plug('logging', mode='print,before')

@sw
def create_user(name, age, email=''):
    return {"name": name, "age": age}

sw('create_user')("Alice", age=30, email="alice@test.com")
# Output: → create_user('Alice', age=30, email='alice@test.com')
```

### After (Return Value)

```python
sw = Switcher().plug('logging', mode='print,after')

@sw
def process(data):
    return f"Processed: {data}"

sw('process')("test")
# Output: ← process() → Processed: test
```

### With Timing

```python
sw = Switcher().plug('logging', mode='print,after,time')

@sw
def slow_operation():
    time.sleep(0.1)
    return "done"

sw('slow_operation')()
# Output: ← slow_operation() → done (0.1002s)
```

### Exception Handling

Exceptions are logged before being re-raised (only if `after` flag is set):

```python
sw = Switcher().plug('logging', mode='print,after')

@sw
def may_fail():
    raise ValueError("Something broke")

try:
    sw('may_fail')()
except ValueError:
    pass
# Output: ✗ may_fail() raised ValueError: Something broke
```

---

## Auto-Fallback Behavior

When using `mode='log'`, the plugin automatically falls back to `print()` if logging is not configured:

```python
# No logging configured - automatically uses print()
sw = Switcher().plug('logging', mode='log')

@sw
def handler():
    return "result"

sw('handler')()
# Output (via print, not logging): ← handler() → result
```

This makes the plugin **tutorial-friendly** - works out of the box without requiring logging setup.

---

## Common Use Cases

### Tutorial/Demo Mode

Show everything for educational purposes:

```python
sw = Switcher().plug('logging', mode='print,before,after')

@sw
def calculate(x, y):
    return x + y

sw('calculate')(5, 10)
# Output:
# → calculate(5, 10)
# ← calculate() → 15
```

### Performance Analysis

Only show timing information:

```python
sw = Switcher().plug('logging', mode='print,after,time')

@sw
def expensive_operation():
    # ... complex logic ...
    return result

sw('expensive_operation')()
# Output: ← expensive_operation() → ... (0.1234s)
```

### Production Monitoring

Use Python logging with structured output:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

sw = Switcher().plug('logging', mode='log,after,time')

@sw
def api_handler(request):
    return process_request(request)

# Logs via logging module:
# 2024-01-15 10:30:45 - ← api_handler() → {...} (0.0123s)
```

### Debugging Only Inputs

When debugging parameter issues:

```python
sw = Switcher().plug('logging', mode='print,before')

@sw
def process(data):
    # ... implementation ...
    return result

sw('process')(some_complex_data)
# Output: → process({...complex data...})
# (no output clutter from results)
```

---

## Custom Logger

Provide a custom logger instance:

```python
import logging

# Create custom logger
logger = logging.getLogger('myapp.handlers')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('handlers.log')
logger.addHandler(handler)

# Use with LoggingPlugin
sw = Switcher().plug('logging', mode='log,after,time', logger=logger)

@sw
def my_handler():
    return "result"

# Logs to handlers.log via custom logger
```

---

## Combining with Other Plugins

LoggingPlugin works seamlessly with other plugins:

```python
from smartswitch import Switcher

# Stack multiple plugins
sw = (Switcher()
      .plug('logging', mode='print,after,time')
      .plug('pydantic'))  # Validation + logging

@sw
def create_user(name: str, age: int):
    return {"name": name, "age": age}

# If validation fails, exception is logged
# If validation passes, result is logged with timing
```

---

## API Reference

### `.plug('logging', **kwargs)`

Register LoggingPlugin with a Switcher.

**Parameters**:

- **`mode`** (str, default='print'): Composable mode flags
  - Output: `'print'` or `'log'` (required, mutually exclusive)
  - Content: `'before'`, `'after'`, `'time'` (optional, combinable)
  - Examples: `'print'`, `'log,after'`, `'print,before,after,time'`

- **`logger`** (logging.Logger, optional): Custom logger instance
  - Only used when `mode` includes `'log'`
  - If None, uses `logging.getLogger('smartswitch')`

**Raises**:

- **ValueError**: If mode doesn't include 'print' or 'log'
- **ValueError**: If mode includes both 'print' and 'log'

**Examples**:

```python
# Basic print
sw.plug('logging', mode='print')

# Only output with timing
sw.plug('logging', mode='print,after,time')

# Use Python logging
sw.plug('logging', mode='log,before,after')

# Custom logger with timing
sw.plug('logging', mode='log,after,time', logger=my_logger)
```

---

## Migration from v0.8.x

The LoggingPlugin was completely redesigned in v0.9.2. Here's how to migrate:

### Removed Features

| Old API (v0.8.x) | Migration |
|------------------|-----------|
| `mode='print'` | Use a separate data collection plugin |
| `.history()` | No longer available - not an output concern |
| `.clear()` | No longer available |
| `.export()` | No longer available |
| `.stats()` | No longer available |
| `.set_file()` | Use custom logger with FileHandler |
| `max_history=N` | No longer available |

### Mode Migration

| Old Mode | New Mode |
|----------|----------|
| `mode='print'` | Remove logging or use collection plugin |
| `mode='log'` | `mode='log,before,after'` or `mode='print,before,after'` |
| `mode='both'` | `mode='print,before,after'` |
| `mode='print', time=True` | Use collection plugin with timing |

### Example Migration

**Before (v0.8.x)**:
```python
sw = Switcher().plug('logging', mode='print,after,time')

@sw
def handler(x):
    return x * 2

result = sw('handler')(5)
history = sw.logging.history()
print(history[0]['elapsed'])
```

**After (v0.9.2+)**:
```python
# For output: use new LoggingPlugin
sw = Switcher().plug('logging', mode='print,after,time')

@sw
def handler(x):
    return x * 2

result = sw('handler')(5)
# Output: ← handler() → 10 (0.0001s)

# For data collection: wait for CollectPlugin (Issue #21)
# or implement custom plugin for your needs
```

---

## Why the Redesign?

The v0.8.x LoggingPlugin mixed two concerns:
1. **Real-time output** (logging calls as they happen)
2. **Data collection** (storing history for analysis)

This violated the Single Responsibility Principle and made the code complex (387 lines).

**v0.9.2 solution**: Split into two plugins:
- **LoggingPlugin** (v0.9.2): Real-time output only (220 lines)
- **CollectPlugin** (planned, Issue #21): Data collection and analysis

This makes both plugins simpler, more focused, and easier to test.

---

## See Also

- [Plugin Development Guide](development.md) - Create custom plugins
- [Middleware Pattern](middleware.md) - How plugins work
- [API Reference](../appendix/api.md) - Complete API documentation
