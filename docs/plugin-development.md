# Plugin Development Guide

## Overview

SmartSwitch supports a flexible plugin system that allows you to extend handler functionality. Plugins can add logging, monitoring, type checking, async support, or any other cross-cutting concern.

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

## Plugin Naming

Your plugin should define a class attribute `plugin_name` that specifies the default name used to access the plugin:

```python
class MyPlugin:
    # Default name for sw.myplugin.method() access
    plugin_name = "myplugin"

    def wrap(self, func, switcher):
        # Your implementation
        return func
```

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

Creating a SmartSwitch plugin:

1. ✅ Create a class with `wrap(func, switcher)` method
2. ✅ Add `plugin_name` class attribute for default access name
3. ✅ Use `@wraps` to preserve function metadata
4. ✅ Provide public methods for user interaction
5. ✅ Test with multiple handlers and in combination with other plugins
6. ✅ Document behavior and examples clearly

Your plugin will integrate seamlessly with SmartSwitch's `.plug()` system and be accessible via `switcher.plugin_name.method()`.

---

**Need help?** Check existing plugins like `LoggingPlugin` in `src/smartswitch/plugins/logging.py` for reference implementation.
