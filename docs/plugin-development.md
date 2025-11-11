# Plugin Development Guide

## Overview

SmartSwitch supports a flexible plugin system that allows you to extend handler functionality. Plugins can add logging, monitoring, type checking, async support, or any other cross-cutting concern.

> **📖 Deep Dive**: For a comprehensive understanding of the middleware pattern behind plugins, including detailed execution flow diagrams and the reference LoggingPlugin implementation, see the [Middleware Pattern Guide](middleware-pattern.md).

## Quick Links

- **[Middleware Pattern](middleware-pattern.md)** - Understand the bidirectional execution flow (onCalling/onCalled)
- **[Plugin Naming Guidelines](#plugin-naming)** - How to name your plugins correctly
- **[LoggingPlugin as Reference](middleware-pattern.md#reference-implementation-loggingplugin)** - Use this as your template

## The Plugin Protocol

All plugins must implement the `SwitcherPlugin` protocol:

```python
from typing import Callable, Protocol

class SwitcherPlugin(Protocol):
    """Protocol for SmartSwitch plugins."""

    def wrap(self, func: Callable, switcher: "Switcher") -> Callable:
        """
        Wrap a handler function during registration.

        Args:
            func: The handler function being registered
            switcher: The Switcher instance registering the handler

        Returns:
            The function to be registered (original or wrapped)
        """
        ...
```

## Plugin Lifecycle (v0.6.0+)

**New in v0.6.0**: SmartSwitch plugins now have a complete lifecycle with three distinct phases.

### Understanding the Three Phases

SmartSwitch plugins operate in **three distinct phases**:

#### Phase 1: Decoration (Happens ONCE when `@sw` is applied)

When you decorate a function with `@sw`, SmartSwitch calls each plugin twice:

1. **`on_decorate(func, switcher)`** - Setup phase (NEW in v0.6.0)
   - Called BEFORE wrap()
   - Receives the **original unwrapped function**
   - Used for expensive setup (creating models, compiling regexes, etc.)
   - Can store metadata in `func._plugin_meta` for other plugins

2. **`wrap(func, switcher)`** - Wrapping phase
   - Called AFTER on_decorate()
   - Can read metadata from `func._plugin_meta`
   - Returns wrapped or original function

**Example:**
```python
@sw
def my_handler(x: int) -> str:
    return str(x)

# Internally SmartSwitch does:
# 1. my_handler._plugin_meta = {}
# 2. For each plugin:
#    - plugin.on_decorate(my_handler, sw)
#    - wrapped = plugin.wrap(wrapped, sw)
```

#### Phase 2: Call (Happens EVERY TIME the function is called)

When you call the handler, the wrapper chain executes:

```python
result = sw("my_handler")(42)

# Execution flow:
# Plugin3.wrapper(
#   Plugin2.wrapper(
#     Plugin1.wrapper(
#       original_func(42)
#     )
#   )
# )
```

#### Phase 3: Exit (Happens EVERY TIME, on return or exception)

The return value (or exception) propagates back through the wrapper chain, allowing each plugin to:
- Log the result
- Transform the return value
- Handle exceptions
- Clean up resources

### The `on_decorate()` Hook

**New in v0.6.0**: Optional hook called during decoration, before wrapping.

```python
from smartswitch import BasePlugin

class MyPlugin(BasePlugin):
    def on_decorate(self, func: Callable, switcher: "Switcher") -> None:
        """
        Called ONCE during decoration, BEFORE wrap().

        Use this to:
        - Analyze function signature, type hints, docstring
        - Prepare expensive resources (models, compiled patterns, etc.)
        - Store metadata for other plugins
        """
        # Access function metadata
        import inspect
        from typing import get_type_hints

        sig = inspect.signature(func)
        hints = get_type_hints(func)

        # Store for use by this plugin and others
        func._plugin_meta["my_plugin"] = {
            "signature": sig,
            "hints": hints,
            "analyzed": True
        }

    def _wrap_handler(self, func: Callable, switcher: "Switcher") -> Callable:
        """
        Called AFTER on_decorate().

        Can read metadata prepared in on_decorate().
        """
        # Read pre-prepared metadata
        meta = func._plugin_meta.get("my_plugin", {})

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use metadata during execution
            if meta.get("analyzed"):
                # Do something with prepared data
                pass
            return func(*args, **kwargs)

        return wrapper
```

### Metadata Sharing Between Plugins

**New in v0.6.0**: Plugins can share metadata via `func._plugin_meta`.

**Convention**: Each plugin uses its own key (usually `plugin_name`) as namespace.

```python
class PydanticPlugin(BasePlugin):
    def on_decorate(self, func, switcher):
        # Create Pydantic model from type hints
        hints = get_type_hints(func)
        ValidationModel = create_model(f"{func.__name__}_Model", **hints)

        # Store for other plugins to read
        func._plugin_meta["pydantic"] = {
            "model": ValidationModel,
            "hints": hints
        }

class FastAPIPlugin(BasePlugin):
    def on_decorate(self, func, switcher):
        # Read Pydantic metadata from previous plugin
        pydantic_meta = func._plugin_meta.get("pydantic", {})

        if pydantic_meta:
            # Use pre-created Pydantic model for FastAPI
            model = pydantic_meta["model"]
            self.app.post(f"/{func.__name__}", response_model=model)(func)

# Usage - order matters!
sw = Switcher().plug("pydantic").plug(FastAPIPlugin(app))
```

**Key Points:**
- Metadata is shared via `func._plugin_meta` dictionary
- Each plugin should use its own namespace (key)
- Later plugins can read earlier plugins' metadata
- Plugin order matters for metadata dependencies

### BasePlugin Class

**Recommended**: Inherit from `BasePlugin` for common functionality.

```python
from smartswitch import BasePlugin

class MyPlugin(BasePlugin):
    """BasePlugin provides:
    - plugin_name property (auto-generated from class name)
    - configure() for per-handler configuration
    - get_config() and is_enabled() utilities
    - Default no-op on_decorate() implementation
    """

    def __init__(self, **config):
        super().__init__(**config)
        # Your initialization

    def on_decorate(self, func, switcher):
        # Optional setup phase
        pass

    def _wrap_handler(self, func, switcher):
        # Required wrapping logic
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
```

**Benefits of BasePlugin:**
- Automatic `plugin_name` generation (removes "Plugin" suffix, lowercase)
- Per-handler configuration via `configure()`
- Enable/disable functionality built-in
- No-op `on_decorate()` provided (override if needed)

### Global Plugin Registry

**New in v0.6.0**: Register plugins globally for string-based loading.

```python
from smartswitch import Switcher, BasePlugin

class MyCustomPlugin(BasePlugin):
    def _wrap_handler(self, func, switcher):
        return func

# Register globally
Switcher.register_plugin("custom", MyCustomPlugin)

# Now usable by string name everywhere
sw = Switcher().plug("custom")
```

Built-in plugins are pre-registered:
- `"logging"` - Call history and monitoring
- `"pydantic"` - Type validation via Pydantic models

## Plugin Naming

### Core Principle: Name by Function, Not Framework

**IMPORTANT**: Plugin names should describe **what the plugin does**, not that it's a SmartSwitch plugin.

**❌ BAD** - Names reference SmartSwitch:

```python
class SmartSwitchLoggerPlugin:
    plugin_name = "smartswitch-logger"  # ❌ Redundant!

class SwitcherMetricsPlugin:
    plugin_name = "switcher-metrics"    # ❌ Redundant!
```

**✅ GOOD** - Names describe functionality:

```python
class LoggingPlugin:
    plugin_name = "logger"    # ✅ Clear: logs things

class MetricsPlugin:
    plugin_name = "metrics"   # ✅ Clear: tracks metrics

class CachePlugin:
    plugin_name = "cache"     # ✅ Clear: caches results

class AsyncPlugin:
    plugin_name = "async"     # ✅ Clear: async support
```

### Why This Matters

The `plugin_name` becomes the attribute for accessing the plugin:

```python
# Good naming
sw = Switcher().plug('logging')
sw.logger.history()           # ✅ Reads naturally

# Bad naming (redundant)
sw = Switcher().plug('smartswitch-logger')
sw.smartswitch-logger.history()  # ❌ We know it's SmartSwitch!
```

### External Package Naming

When publishing plugin packages to PyPI:

**Package name** (PyPI): Can reference ecosystem for discoverability

- ✅ `smartasync` - OK for PyPI package name
- ✅ `gtext-cache` - OK for PyPI package name

**Plugin name** (in code): Should describe functionality only

- ✅ `plugin_name = "async"` - Clean attribute access
- ✅ `plugin_name = "cache"` - Clean attribute access

**Example**:

```python
# Package on PyPI: "smartasync"
# pip install smartasync

from smartasync import SmartAsyncPlugin

class SmartAsyncPlugin:
    plugin_name = "async"  # ✅ Not "smartasync"!

# Usage
sw = Switcher().plug(SmartAsyncPlugin())
sw.async.is_async('my_handler')  # ✅ Clean attribute name
```

### Naming Guidelines Summary

1. **plugin_name**: Describes functionality (e.g., `"logger"`, `"cache"`, `"metrics"`)
2. **Class name**: Can reference ecosystem (e.g., `SmartAsyncPlugin`, `GtextCachePlugin`)
3. **PyPI package**: Can reference ecosystem (e.g., `smartasync`, `gtext-cache`)
4. **Attribute access**: Uses `plugin_name`, should be clean and concise

## Basic Plugin Example

Here's a minimal plugin that tracks call counts:

```python
from functools import wraps

class CallCounterPlugin:
    """Plugin that counts handler calls."""

    plugin_name = "counter"  # Access via sw.counter

    def __init__(self):
        self._counts = {}

    def wrap(self, func, switcher):
        """Wrap function to count calls."""
        handler_name = func.__name__
        self._counts[handler_name] = 0

        @wraps(func)
        def wrapper(*args, **kwargs):
            self._counts[handler_name] += 1
            return func(*args, **kwargs)

        return wrapper

    def get_count(self, handler: str) -> int:
        """Get call count for a handler."""
        return self._counts.get(handler, 0)

    def reset(self):
        """Reset all counts."""
        self._counts.clear()

# Usage:
sw = Switcher().plug(CallCounterPlugin())

@sw
def my_handler(x):
    return x * 2

sw('my_handler')(5)
sw('my_handler')(10)

print(sw.counter.get_count('my_handler'))  # Output: 2
```

## Accessing the Plugin

After registration with `.plug()`, your plugin is accessible via `__getattr__`:

```python
sw = Switcher().plug(MyPlugin())

# Access plugin methods:
sw.myplugin.some_method()
sw.myplugin.another_method()
```

### Custom Plugin Names

You can override the default name when registering:

```python
sw.plug(MyPlugin(), name='custom_name')
sw.custom_name.some_method()  # Access with custom name
```

## Advanced Plugin Example: Async Support

Here's a more complex example showing how to add async support to SmartSwitch:

```python
import asyncio
from functools import wraps
import inspect

class AsyncPlugin:
    """Plugin that enables async handler support."""

    plugin_name = "async_support"

    def __init__(self):
        self._async_handlers = set()

    def wrap(self, func, switcher):
        """Wrap async functions for proper execution."""
        # Check if function is async
        if not inspect.iscoroutinefunction(func):
            return func  # Not async, pass through

        # Track this as an async handler
        self._async_handlers.add(func.__name__)

        @wraps(func)
        def async_wrapper(*args, **kwargs):
            """Wrapper that runs async function in event loop."""
            coro = func(*args, **kwargs)

            # Try to get running loop, or create new one
            try:
                loop = asyncio.get_running_loop()
                # Already in async context, return coroutine
                return coro
            except RuntimeError:
                # No loop, create one and run
                return asyncio.run(coro)

        return async_wrapper

    def is_async(self, handler: str) -> bool:
        """Check if a handler is async."""
        return handler in self._async_handlers

# Usage:
sw = Switcher().plug(AsyncPlugin())

@sw
async def fetch_data(url: str):
    """Async handler that fetches data."""
    # In real code: await aiohttp request
    await asyncio.sleep(0.1)
    return f"Data from {url}"

# Call works seamlessly:
result = sw('fetch_data')('https://example.com')
```

## Plugin Initialization Parameters

Plugins can accept configuration parameters:

```python
class ConfigurablePlugin:
    plugin_name = "config"

    def __init__(self, option1: str, option2: int = 10):
        self.option1 = option1
        self.option2 = option2

    def wrap(self, func, switcher):
        # Use self.option1 and self.option2
        return func

# Usage:
sw = Switcher().plug(ConfigurablePlugin(option1="value", option2=20))
```

## Storing State

Plugins can store state and provide query methods:

```python
class StatefulPlugin:
    plugin_name = "stats"

    def __init__(self):
        self._call_times = []

    def wrap(self, func, switcher):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            self._call_times.append(elapsed)
            return result
        return wrapper

    def average_time(self) -> float:
        """Get average call time."""
        return sum(self._call_times) / len(self._call_times) if self._call_times else 0

    def total_calls(self) -> int:
        """Get total number of calls."""
        return len(self._call_times)

# Usage:
sw = Switcher().plug(StatefulPlugin())

@sw
def handler():
    return 42

sw('handler')()
sw('handler')()

print(f"Average time: {sw.stats.average_time():.4f}s")
print(f"Total calls: {sw.stats.total_calls()}")
```

## Chaining Multiple Plugins

Plugins can be chained together:

```python
sw = (Switcher()
      .plug('logging', mode='silent')
      .plug(AsyncPlugin())
      .plug(CallCounterPlugin()))

@sw
async def my_handler(x):
    return x * 2

# Handler is wrapped by all three plugins:
# 1. LoggingPlugin tracks the call
# 2. AsyncPlugin handles async execution
# 3. CallCounterPlugin counts the call

result = sw('my_handler')(5)
print(sw.logger.history())  # From logging plugin
print(sw.counter.get_count('my_handler'))  # From counter plugin
```

## Standard vs External Plugins

**Standard plugins** (shipped with SmartSwitch):
- Can be loaded by string name: `sw.plug('logging')`
- Registered in `Switcher._get_standard_plugin()`
- Examples: `logging`, `typerule`, `valrule`

**External plugins** (third-party packages):
- Must be imported and instantiated: `sw.plug(MyPlugin())`
- Distributed as separate packages
- Examples: `smartasync`, custom monitoring tools

### Creating an External Plugin Package

For a package like `smartasync`, the structure would be:

```
smartasync/
├── pyproject.toml
├── src/
│   └── smartasync/
│       ├── __init__.py
│       └── plugin.py
└── tests/
    └── test_plugin.py
```

**src/smartasync/__init__.py**:
```python
"""SmartAsync - Async support plugin for SmartSwitch."""

from .plugin import SmartAsyncPlugin

__version__ = "0.1.0"
__all__ = ["SmartAsyncPlugin"]
```

**src/smartasync/plugin.py**:
```python
"""SmartAsync Plugin implementation."""

import asyncio
import inspect
from functools import wraps

class SmartAsyncPlugin:
    """Plugin that enables async handler support for SmartSwitch."""

    plugin_name = "async_support"

    def __init__(self, loop=None):
        self._loop = loop
        self._async_handlers = set()

    def wrap(self, func, switcher):
        """Wrap async functions for proper execution."""
        if not inspect.iscoroutinefunction(func):
            return func

        self._async_handlers.add(func.__name__)

        @wraps(func)
        def async_wrapper(*args, **kwargs):
            coro = func(*args, **kwargs)
            loop = self._loop or asyncio.get_event_loop()
            return loop.run_until_complete(coro)

        return async_wrapper

    def is_async(self, handler: str) -> bool:
        return handler in self._async_handlers
```

**Usage in user code**:
```python
from smartswitch import Switcher
from smartasync import SmartAsyncPlugin

sw = Switcher().plug(SmartAsyncPlugin())

@sw
async def fetch_data(url: str):
    # async implementation
    pass
```

## Best Practices

### 1. Use `@wraps` to Preserve Metadata

Always use `functools.wraps` to preserve function metadata:

```python
from functools import wraps

def wrap(self, func, switcher):
    @wraps(func)  # Preserves __name__, __doc__, etc.
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

### 2. Store Switcher Reference Carefully

If you need the Switcher instance later, store it only once:

```python
def wrap(self, func, switcher):
    if self._switcher is None:
        self._switcher = switcher
    # ... rest of implementation
```

### 3. Provide Clear Public Methods

Design a clean API for users:

```python
class MyPlugin:
    def wrap(self, func, switcher):
        # Internal implementation
        pass

    # Public API methods:
    def get_stats(self):
        """Get statistics (user-facing)."""
        pass

    def reset(self):
        """Reset internal state (user-facing)."""
        pass

    def _internal_helper(self):
        """Internal helper (private)."""
        pass
```

### 4. Document Plugin Behavior

Provide clear docstrings:

```python
class MyPlugin:
    """
    Plugin that adds X functionality to SmartSwitch handlers.

    Features:
    - Feature 1
    - Feature 2

    Examples:
        >>> sw = Switcher().plug(MyPlugin())
        >>> @sw
        ... def handler():
        ...     return 42
        >>> sw.myplugin.some_method()
    """
```

### 5. Handle Edge Cases

Consider what happens when:
- Handler has no arguments
- Handler raises exceptions
- Handler is called multiple times
- Multiple plugins are active

### 6. Test Thoroughly

Write comprehensive tests:

```python
def test_plugin_basic():
    sw = Switcher().plug(MyPlugin())

    @sw
    def handler(x):
        return x * 2

    assert sw('handler')(5) == 10
    # Test plugin-specific behavior

def test_plugin_with_logging():
    sw = Switcher().plug('logging').plug(MyPlugin())

    @sw
    def handler():
        return 42

    sw('handler')()
    # Verify both plugins work together
```

## Plugin Protocol Reference

### Required

- `wrap(func, switcher) -> Callable`: Transform/wrap the handler function

### Recommended

- `plugin_name: str`: Class attribute defining default access name

### Optional

- `__init__(...)`: Accept configuration parameters
- Public methods for user interaction (queries, configuration, etc.)

## FAQ

**Q: Can plugins modify the Switcher instance?**

A: Yes, but be careful. The `switcher` parameter gives you access to the Switcher instance. You can read its state, but modifying it directly is discouraged. Use your plugin's state instead.

**Q: What's the execution order when multiple plugins are chained?**

A: Plugins are applied in registration order. The function passes through each plugin's `wrap()` method sequentially:

```python
sw.plug(Plugin1()).plug(Plugin2()).plug(Plugin3())

# Execution: Plugin1.wrap(Plugin2.wrap(Plugin3.wrap(func)))
```

**Q: Can I make a plugin that doesn't wrap the function?**

A: Yes! Just return `func` unchanged. The plugin can still store information or register the function in internal data structures:

```python
def wrap(self, func, switcher):
    # Register function without wrapping
    self._registered_functions.add(func.__name__)
    return func  # Return unchanged
```

**Q: How do I access plugin methods from wrapped functions?**

A: Store the plugin instance during wrap and access it in the wrapper:

```python
def wrap(self, func, switcher):
    plugin_instance = self

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Access plugin_instance here
        plugin_instance.do_something()
        return func(*args, **kwargs)

    return wrapper
```

**Q: Can plugins add new decorator parameters?**

A: Not directly. The decorator syntax is controlled by Switcher. But you can create a custom decorator that adds metadata:

```python
def async_handler(func):
    """Decorator to mark handler as async."""
    func._is_async = True
    return func

# In plugin:
def wrap(self, func, switcher):
    if hasattr(func, '_is_async'):
        # Handle async function
        pass
```

## Summary

Creating a SmartSwitch plugin (v0.6.0+):

1. ✅ Inherit from `BasePlugin` for common functionality
2. ✅ Override `on_decorate(func, switcher)` for setup phase (optional)
3. ✅ Implement `_wrap_handler(func, switcher)` for wrapping logic (required)
4. ✅ Use `func._plugin_meta[plugin_name]` to store/share metadata
5. ✅ Use `@wraps` to preserve function metadata
6. ✅ Provide public methods for user interaction
7. ✅ Test with multiple handlers and in combination with other plugins
8. ✅ Document behavior and examples clearly
9. ✅ Register globally with `Switcher.register_plugin()` (optional)

Your plugin will integrate seamlessly with SmartSwitch's `.plug()` system and be accessible via `switcher.plugin_name.method()`.

---

**Need help?** Check existing plugins like `LoggingPlugin` in `src/smartswitch/plugins/logging.py` for reference implementation.
