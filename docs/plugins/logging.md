# LoggingPlugin

**New in v0.10.0**: Pydantic-based configuration system with runtime flexibility and elegant flag syntax.

The LoggingPlugin provides real-time visibility into handler calls with flexible, runtime-configurable output options. Perfect for debugging, tutorials, and monitoring.

---

## Quick Start

```python
from smartswitch import Switcher

# Create switcher with logging (enabled + print output)
sw = Switcher().plug('logging', flags='print,enabled')

@sw
def add(a, b):
    return a + b

# Logs input automatically (before=True by default)
result = sw('add')(2, 3)
# Output:
# → add(2, 3)
```

---

## Configuration System

LoggingPlugin uses a **Pydantic-based configuration** with two ways to configure:

### 1. Flags String (Concise)

Set boolean parameters with a comma-separated string:

```python
# Syntax: 'flag1,flag2,flag3:off'
sw.plug('logging', flags='print,enabled,after,time')
```

### 2. Individual Parameters (Explicit)

Set parameters individually for IDE autocomplete:

```python
sw.plug('logging', print=True, enabled=True, after=True, time=True)
```

Both are equivalent and can be mixed!

---

## Available Flags

### State Flag

- **`enabled`** (default: `False`): Enable/disable plugin
  - Plugin is **disabled by default** (opt-in behavior)
  - Must be set to `True` to see any output

### Output Destination

Choose **one** of these (mutually exclusive in practice):

- **`print`** (default: `False`): Output to stdout via `print()`
- **`log`** (default: `True`): Output via Python's logging system

### Content Flags

- **`before`** (default: `True`): Show input parameters
- **`after`** (default: `False`): Show return value
- **`time`** (default: `False`): Include execution time

---

## Default Behavior

When you create a plugin without parameters:

```python
sw = Switcher().plug('logging')  # Plugin registered but disabled
```

**Defaults**:
```python
{
    'enabled': False,  # Disabled by default
    'print': False,
    'log': True,
    'before': True,    # Shows input when enabled
    'after': False,
    'time': False
}
```

To actually see output, you need at least:
```python
sw.plug('logging', flags='print,enabled')  # Minimal activation
```

---

## Common Patterns

### Tutorial/Demo Mode

Show input and output for educational purposes:

```python
sw = Switcher().plug('logging', flags='print,enabled,after')

@sw
def calculate(x, y):
    return x + y

sw('calculate')(5, 10)
# Output:
# → calculate(5, 10)
# ← calculate() → 15
```

### Debugging Inputs Only

When debugging parameter issues:

```python
sw = Switcher().plug('logging', flags='print,enabled')  # before=True by default

@sw
def process(data):
    return result

sw('process')(complex_data)
# Output: → process({...complex data...})
# (no output clutter from results)
```

### Performance Analysis

Show output with timing:

```python
sw = Switcher().plug('logging', flags='print,enabled,after,time')

@sw
def expensive_operation():
    return result

sw('expensive_operation')()
# Output: ← expensive_operation() → ... (0.1234s)
```

### Production Monitoring

Use Python logging with structured output:

```python
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

sw = Switcher().plug('logging', flags='log,enabled,after,time')

@sw
def api_handler(request):
    return process_request(request)

# Logs via logging module:
# 2024-01-15 10:30:45 - ← api_handler() → {...} (0.0123s)
```

---

## Runtime Configuration

**New in v0.10.0**: Change configuration dynamically at runtime!

### Access Plugin

Access plugin directly via attribute:

```python
sw = Switcher().plug('logging', flags='print,enabled')

# Access plugin
logger = sw.logging  # Direct attribute access
```

### Global Configuration

Modify global settings at runtime:

```python
# Change flags
sw.logging.configure.flags = 'log,enabled,after,time'

# Change individual parameters
sw.logging.configure.enabled = True
sw.logging.configure.print = True
sw.logging.configure.time = True

# Get current config
print(sw.logging.configure.config)
# → {'enabled': True, 'print': True, 'log': True, ...}

# Get active flags
print(sw.logging.configure.flags)
# → 'enabled,print,log,after,time'
```

### Per-Method Configuration

Configure specific methods differently:

```python
sw = Switcher().plug('logging', flags='print,enabled')

@sw
def public_api(x):
    return x * 2

@sw
def internal_helper(x):
    return x + 1

# Disable logging for internal_helper
sw.logging.configure['internal_helper'].flags = 'enabled:off'

# Add timing for public_api
sw.logging.configure['public_api'].flags = 'time,after'

# Configuration for multiple methods at once
sw.logging.configure['method1,method2,method3'].flags = 'enabled:off'
```

### Dynamic Changes

Configuration changes apply immediately:

```python
sw = Switcher().plug('logging', flags='print,enabled')

@sw
def dynamic_func(x):
    return x * 2

# First call (before=True by default)
dynamic_func(5)  # → dynamic_func(5)

# Change config
sw.logging.configure.flags = 'print,enabled,before:off,after,time'

# Second call (new config applies immediately)
dynamic_func(7)  # ← dynamic_func() → 14 (0.0000s)
```

---

## Output Formats

### Before (Input Parameters)

```python
sw = Switcher().plug('logging', flags='print,enabled')  # before=True by default

@sw
def create_user(name, age, email=''):
    return {"name": name, "age": age}

sw('create_user')("Alice", age=30, email="alice@test.com")
# Output: → create_user('Alice', age=30, email='alice@test.com')
```

### After (Return Value)

```python
sw = Switcher().plug('logging', flags='print,enabled,after')

@sw
def process(data):
    return f"Processed: {data}"

sw('process')("test")
# Output: ← process() → Processed: test
```

### With Timing

```python
sw = Switcher().plug('logging', flags='print,enabled,after,time')

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
sw = Switcher().plug('logging', flags='print,enabled,after')

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

When using `log=True`, the plugin automatically falls back to `print()` if logging is not configured:

```python
# No logging configured - automatically uses print()
sw = Switcher().plug('logging', flags='log,enabled')

@sw
def handler():
    return "result"

sw('handler')()
# Output (via print, not logging): → handler()
```

This makes the plugin **tutorial-friendly** - works out of the box without requiring logging setup.

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
sw = Switcher().plug('logging',
                     flags='log,enabled,after,time',
                     logger=logger)

@sw
def my_handler():
    return "result"

# Logs to handlers.log via custom logger
```

---

## Pydantic Integration

**Optional**: If Pydantic is installed, configuration is validated:

```python
# With Pydantic installed - validated
sw.plug('logging', flags='print,enabled', invalid_param=True)
# → ValidationError: Extra inputs are not permitted

# Without Pydantic - permissive (no validation)
sw.plug('logging', flags='print,enabled', invalid_param=True)
# → Works, invalid_param ignored
```

Install with Pydantic support:
```bash
pip install smartswitch[plugins]  # Includes Pydantic
```

---

## Combining with Other Plugins

LoggingPlugin works seamlessly with other plugins:

```python
from smartswitch import Switcher

# Stack multiple plugins
sw = (Switcher()
      .plug('logging', flags='print,enabled,after,time')
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

- **`flags`** (str, optional): Comma-separated boolean flags
  - Syntax: `'flag1,flag2,flag3:off'`
  - Available: `'enabled'`, `'print'`, `'log'`, `'before'`, `'after'`, `'time'`
  - Examples: `'print,enabled'`, `'log,enabled,after,time'`

- **Individual boolean parameters** (bool, optional):
  - `enabled` (default: `False`): Enable plugin
  - `print` (default: `False`): Use print() output
  - `log` (default: `True`): Use Python logging
  - `before` (default: `True`): Show input parameters
  - `after` (default: `False`): Show return value
  - `time` (default: `False`): Show execution time

- **`logger`** (logging.Logger, optional): Custom logger instance
  - Only used when `log=True`
  - If None, uses `logging.getLogger('smartswitch')`

- **`method_config`** (dict, optional): Per-method configuration overrides
  - Keys: method name or comma-separated names ('alfa,beta,gamma')
  - Values: flags string or dict

**Examples**:

```python
# Basic activation
sw.plug('logging', flags='print,enabled')

# With flags and kwargs mixed
sw.plug('logging', flags='print,enabled', time=True)

# Per-method config
sw.plug('logging',
        flags='print,enabled',
        method_config={
            'calculate': 'after,time',
            'internal': 'enabled:off'
        })

# Custom logger
sw.plug('logging', flags='log,enabled,after', logger=my_logger)
```

### Runtime Configuration API

Access via `sw.<plugin_name>.configure`:

```python
# Global config
sw.logging.configure.flags = 'print,enabled,after'
sw.logging.configure.enabled = True
sw.logging.configure.time = True

# Per-method config
sw.logging.configure['method_name'].flags = 'time,after'
sw.logging.configure['method_name'].enabled = False

# Get config
config = sw.logging.configure.config  # dict
flags = sw.logging.configure.flags    # str

# Get per-method config (merged with global)
config = sw.logging.configure['method_name'].config
```

---

## See Also

- [Plugin Development Guide](development.md) - Create custom plugins with Pydantic
- [Plugin System Overview](index.md) - Understanding the plugin architecture
- [Middleware Pattern](middleware.md) - How plugins work internally
