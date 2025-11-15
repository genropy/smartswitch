# Plugin System

**New in v0.5.0**: SmartSwitch includes a powerful plugin system that allows you to extend handler behavior with reusable components.

## Overview

Plugins wrap handlers to add cross-cutting concerns like:
- **Validation** (Pydantic type checking)
- **Logging** (Call history and performance monitoring)
- **Authentication** (Permission checks)
- **Caching** (Result memoization)
- **Async/Sync bridging** (SmartAsync integration)
- **Custom middleware** (Your own functionality)

## Quick Start

```python
from smartswitch import Switcher

# Enable built-in logging plugin (v0.10.0+ uses flags)
sw = Switcher().plug("logging", flags="print,enabled,after")

@sw
def my_handler(x: int) -> int:
    return x * 2

# Call handler - automatically logged
result = sw("my_handler")(5)
# Output: ← my_handler() → 10

# Runtime configuration
sw.logging.configure.flags = "print,enabled,before,after,time"
```

## Built-in Plugins

SmartSwitch comes with two pre-registered plugins:

- **`"logging"`** - Call history tracking, performance analysis, error monitoring
- **`"pydantic"`** - Automatic type validation using Pydantic models

```python
# Use built-in plugins by name
sw = Switcher().plug("logging").plug("pydantic")

@sw
def typed_handler(x: int, y: str) -> str:
    return f"{x}:{y}"

# Both logging and validation applied
result = sw("typed_handler")(42, "test")
```

## Plugin Topics

```{toctree}
:maxdepth: 1

development
middleware
logging
```

### [Plugin Development](development.md)

Learn how to create custom plugins:
- Plugin protocol and lifecycle (v0.6.0+)
- `on_decorate()` hook for setup phase
- Metadata sharing between plugins via `func._plugin_meta`
- BasePlugin class for common functionality
- Global plugin registry

### [Middleware Pattern](middleware.md)

Understand the middleware architecture:
- How plugins compose via wrapper chains
- Execution order and control flow
- Best practices for middleware design
- LoggingPlugin as canonical example

### [Logging Plugin](logging.md)

Deep dive into the built-in logging plugin (v0.4.0+):
- Silent, log, and both modes
- Call history tracking
- Performance analysis and statistics
- Error monitoring
- Query API for filtering and analysis

## Plugin Order Matters

The order you call `.plug()` determines:
1. **Metadata dependencies** - Later plugins can read earlier plugins' metadata
2. **Wrapper execution order** - Outermost to innermost during calls

```python
# ✅ CORRECT - pydantic before logging
sw = Switcher().plug("pydantic").plug("logging")
# Execution: logging → pydantic → handler

# ✅ ALSO VALID - logging before pydantic
sw = Switcher().plug("logging").plug("pydantic")
# Execution: pydantic → logging → handler
# (validation happens first, then logging)
```

Choose plugin order based on your needs:
- **Validation first** - Reject invalid calls before logging
- **Logging first** - Log all calls including validation errors

## Creating Custom Plugins

To create your own plugin, implement the plugin protocol:

```python
from smartswitch import BasePlugin

class MyPlugin(BasePlugin):
    def on_decorate(self, switch, func, entry):
        """Optional: Setup phase during decoration."""
        # Prepare resources, store metadata
        entry.metadata.setdefault("my_plugin", {})
        entry.metadata["my_plugin"]["prepared"] = True

    def wrap_handler(self, switch, entry, call_next):
        """Required: Create wrapper function."""
        def wrapper(*args, **kwargs):
            # Pre-processing
            result = call_next(*args, **kwargs)
            # Post-processing
            return result
        return wrapper

# Register and use
from smartswitch import Switcher
Switcher.register_plugin("my_plugin", MyPlugin)

sw = Switcher().plug("my_plugin")
```

See [Plugin Development](development.md) for complete documentation.

## Next Steps

- **New to plugins?** Start with [Middleware Pattern](middleware.md) to understand the architecture
- **Want to create plugins?** Read [Plugin Development](development.md) for the complete guide
- **Using logging?** Check [Logging Plugin](logging.md) for all features and examples
