# Plugin Development Guide

## Overview

SmartSwitch supports a flexible plugin system that allows you to extend handler functionality. Plugins can add logging, monitoring, type checking, caching, validation, or any other cross-cutting concern.

> **📖 Deep Dive**: For a comprehensive understanding of the middleware pattern behind plugins, including detailed execution flow diagrams and the reference LoggingPlugin implementation, see the [Middleware Pattern Guide](middleware.md).

## Quick Links

- **[Middleware Pattern](middleware.md)** - Understand the bidirectional execution flow (onCalling/onCalled)
- **[Plugin Naming Guidelines](#plugin-naming)** - How to name your plugins correctly
- **[Global Registration](#global-plugin-registry)** - Register plugins for string-based loading (RECOMMENDED)
- **[LoggingPlugin as Reference](middleware.md#reference-implementation-loggingplugin)** - Use this as your template

## The Plugin Protocol

All plugins must implement the `SwitcherPlugin` protocol (updated in v0.10.0):

```python
from typing import Callable, Protocol

class SwitcherPlugin(Protocol):
    """Protocol for SmartSwitch plugins (v0.6.0+, updated v0.10.0)."""

    def on_decorate(self, switch: "Switcher", func: Callable, entry: "MethodEntry") -> None:
        """
        Optional hook called during decoration, before wrap_handler().

        Use this for expensive setup (model creation, compilation, etc.)
        and to store metadata in entry.metadata.

        Args:
            switch: The Switcher instance
            func: The handler function being decorated
            entry: MethodEntry object with handler metadata
        """
        ...  # Optional - default no-op in BasePlugin

    def wrap_handler(self, switch: "Switcher", entry: "MethodEntry", call_next: Callable) -> Callable:
        """
        Wrap a handler function using middleware pattern.

        Args:
            switch: The Switcher instance
            entry: MethodEntry object with handler metadata
            call_next: The next layer in the middleware chain

        Returns:
            Wrapped function that calls call_next()
        """
        ...  # Required
```

## Plugin Lifecycle (v0.6.0+)

**New in v0.6.0**: SmartSwitch plugins now have a complete lifecycle with three distinct phases.

### Understanding the Three Phases

SmartSwitch plugins operate in **three distinct phases**:

#### Phase 1: Decoration (Happens ONCE when `@sw` is applied)

When you decorate a function with `@sw`, SmartSwitch calls each plugin twice:

1. **`on_decorate(switch, func, entry)`** - Setup phase (NEW in v0.6.0)
   - Called BEFORE wrap_handler()
   - Receives the **switcher, original function, and MethodEntry**
   - Used for expensive setup (creating models, compiling regexes, etc.)
   - Can store metadata in `entry.metadata` for other plugins

2. **`wrap_handler(switch, entry, call_next)`** - Wrapping phase
   - Called AFTER on_decorate()
   - Can read metadata from `entry.metadata`
   - Returns wrapper function using middleware pattern with `call_next`

**Example:**
```python
@sw
def my_handler(x: int) -> str:
    return str(x)

# Internally SmartSwitch does:
# 1. entry = MethodEntry(..., metadata={})
# 2. For each plugin:
#    - plugin.on_decorate(sw, my_handler, entry)
#    - wrapper = plugin.wrap_handler(sw, entry, call_next)
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
    def on_decorate(self, switch: "Switcher", func: Callable, entry: "MethodEntry") -> None:
        """
        Called ONCE during decoration, BEFORE wrap_handler().

        Use this to:
        - Analyze function signature, type hints, docstring
        - Prepare expensive resources (models, compiled patterns, etc.)
        - Store metadata in entry.metadata
        """
        # Access function metadata
        import inspect
        from typing import get_type_hints

        sig = inspect.signature(func)
        hints = get_type_hints(func)

        # Store in entry metadata under our plugin's namespace
        if not hasattr(entry, '_myplugin_meta'):
            entry._myplugin_meta = {}
        entry._myplugin_meta["signature"] = sig
        entry._myplugin_meta["hints"] = hints
        entry._myplugin_meta["analyzed"] = True

    def wrap_handler(self, switch: "Switcher", entry: "MethodEntry", call_next: Callable) -> Callable:
        """
        Called AFTER on_decorate().

        Can read metadata prepared in on_decorate().
        """
        def wrapper(*args, **kwargs):
            # Use metadata during execution
            if hasattr(entry, '_myplugin_meta') and entry._myplugin_meta.get("analyzed"):
                # Do something with prepared data
                pass
            return call_next(*args, **kwargs)

        return wrapper
```

### Metadata Sharing Between Plugins

**New in v0.6.0**: Plugins can share metadata using `entry` attributes or `entry.metadata` dict.

**Recommended Approach**: Store metadata as entry attributes with plugin-specific prefix:
- Use `entry._pluginname_data` for plugin-specific data
- Or use `entry.metadata['pluginname']` for dict-based storage
- Later plugins can read earlier plugins' metadata

**Why Namespacing Matters:**
- Multiple plugins can store data without conflicts
- Plugins can read data from other plugins
- Metadata persists throughout the handler's lifetime
- Each plugin owns its namespace

```python
class PydanticPlugin(BasePlugin):
    def on_decorate(self, switch, func, entry):
        from typing import get_type_hints
        from pydantic import create_model

        # Create Pydantic model from type hints
        hints = get_type_hints(func)
        validation_model = create_model(f"{func.__name__}_Model", **hints)

        # Store in entry as attribute (recommended)
        if not hasattr(entry, '_pydantic'):
            entry._pydantic = {}
        entry._pydantic["model"] = validation_model
        entry._pydantic["hints"] = hints

class FastAPIPlugin(BasePlugin):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def on_decorate(self, switch, func, entry):
        # Read from Pydantic plugin metadata
        if hasattr(entry, '_pydantic'):
            pydantic_meta = entry._pydantic
            # Use pre-created Pydantic model for FastAPI
            model = pydantic_meta["model"]
            self.app.post(f"/{func.__name__}", response_model=model)(func)

        # Store our own metadata
        if not hasattr(entry, '_fastapi'):
            entry._fastapi = {}
        entry._fastapi["registered"] = True
        entry._fastapi["endpoint"] = f"/{func.__name__}"

# Usage - order matters! Pydantic must come before FastAPI
# Register plugins
Switcher.register_plugin("pydantic", PydanticPlugin)
Switcher.register_plugin("fastapi", lambda app: FastAPIPlugin(app))

sw = Switcher().plug("pydantic").plug("fastapi", app=my_app)
```

**Key Points:**
- Store metadata as `entry._pluginname_data` attributes
- Later plugins can read earlier plugins' metadata by accessing entry attributes
- Plugin order matters for metadata dependencies
- Metadata is for immutable setup data (signatures, compiled patterns, models)

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

    def on_decorate(self, switch, func, entry):
        # Optional setup phase - called before wrap_handler
        # Store metadata in entry.metadata if needed
        pass

    def wrap_handler(self, switch, entry, call_next):
        # Required wrapping logic
        def wrapper(*args, **kwargs):
            # Pre-processing
            result = call_next(*args, **kwargs)
            # Post-processing
            return result
        return wrapper
```

**Benefits of BasePlugin:**
- Automatic `plugin_name` generation (removes "Plugin" suffix, lowercase)
- Per-handler configuration via `configure()`
- Enable/disable functionality built-in
- No-op `on_decorate()` provided (override if needed)

### Global Plugin Registry

**New in v0.6.0**: Plugin **users** should register external plugins globally to use the same string-based loading semantics as built-in plugins.

**Who registers plugins?** **USERS**, not developers!

- **Plugin developers**: Just publish the plugin class
- **Plugin users**: Should register it in their own code to enable string-based loading

```python
# User's application code
from smartswitch import Switcher
from smartcache import SmartCachePlugin  # External plugin

# USER registers the plugin to enable string-based loading
Switcher.register_plugin("cache", SmartCachePlugin)

# Now can use same semantics as built-in plugins
sw = Switcher().plug("cache", ttl=300)

# Without registration, would need:
# sw = Switcher().plug(SmartCachePlugin(ttl=300))  # Different semantics
```

**Built-in plugins** are pre-registered:
- `"logging"` - Call history and monitoring
- `"pydantic"` - Type validation via Pydantic models

**Recommended practice**: Register external plugins once at application startup to maintain consistent plugin loading semantics throughout your codebase.

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
    plugin_name = "logging"   # ✅ Clear: logs things

class MetricsPlugin:
    plugin_name = "metrics"   # ✅ Clear: tracks metrics

class CachePlugin:
    plugin_name = "cache"     # ✅ Clear: caches results

class ValidationPlugin:
    plugin_name = "validation"  # ✅ Clear: validates inputs
```

### Why This Matters

The `plugin_name` becomes the attribute for accessing the plugin:

```python
# Good naming
sw = Switcher().plug('logging')

# Bad naming (redundant)
sw = Switcher().plug('smartswitch-logger')
```

### External Package Naming

When publishing plugin packages to PyPI:

**Package name** (PyPI): Can reference ecosystem for discoverability

- ✅ `smartretry` - OK for PyPI package name
- ✅ `gtext-cache` - OK for PyPI package name

**Plugin name** (in code): Should describe functionality only

- ✅ `plugin_name = "retry"` - Clean attribute access
- ✅ `plugin_name = "cache"` - Clean attribute access

**Example**:

```python
# Package on PyPI: "smartretry"
# pip install smartretry

from smartretry import SmartRetryPlugin

class SmartRetryPlugin(BasePlugin):
    def __init__(self, **kwargs):
        super().__init__(name="retry", **kwargs)  # ✅ Not "smartretry"!

# Usage
Switcher.register_plugin('retry', SmartRetryPlugin)
sw = Switcher().plug('retry')
sw.retry.set_max_attempts(3)  # ✅ Clean attribute name
```

### Naming Guidelines Summary

1. **plugin_name**: Describes functionality (e.g., `"logger"`, `"cache"`, `"metrics"`)
2. **Class name**: Can reference ecosystem (e.g., `SmartRetryPlugin`, `GtextCachePlugin`)
3. **PyPI package**: Can reference ecosystem (e.g., `smartretry`, `gtext-cache`)
4. **Attribute access**: Uses `plugin_name`, should be clean and concise

## Basic Plugin Example

Here's a minimal plugin that tracks call counts:

```python
from smartswitch import Switcher, BasePlugin

class CallCounterPlugin(BasePlugin):
    """Plugin that counts handler calls."""

    def __init__(self, **kwargs):
        super().__init__(name="counter", **kwargs)  # Access via sw.counter
        self._counts = {}

    def wrap_handler(self, switch, entry, call_next):
        """Wrap function to count calls."""
        handler_name = entry.name
        self._counts[handler_name] = 0

        def wrapper(*args, **kwargs):
            self._counts[handler_name] += 1
            return call_next(*args, **kwargs)

        return wrapper

    def get_count(self, handler: str) -> int:
        """Get call count for a handler."""
        return self._counts.get(handler, 0)

    def reset(self):
        """Reset all counts."""
        self._counts.clear()

# Register plugin globally
Switcher.register_plugin("counter", CallCounterPlugin)

# Usage:
sw = Switcher().plug("counter")

@sw
def my_handler(x):
    return x * 2

sw('my_handler')(5)
sw('my_handler')(10)

print(sw.counter.get_count('my_handler'))  # Output: 2
```

## Accessing the Plugin

After registration with `.plug()`, your plugin is accessible via attribute access:

```python
# Register plugin
Switcher.register_plugin("myplugin", MyPlugin)

# Use plugin
sw = Switcher().plug("myplugin")

# Access plugin methods:
sw.myplugin.some_method()
sw.myplugin.another_method()
```

### Custom Plugin Names

You can use a custom name when calling `.plug()`:

```python
# Register with one name
Switcher.register_plugin("original", MyPlugin)

# Can use with different instance name if plugin supports it
sw.plug("original", name='custom_name')
sw.custom_name.some_method()  # Access with custom name
```

## Advanced Plugin Example: Retry Logic

Here's a more complex example showing how to add retry logic with exponential backoff:

```python
import time
from smartswitch import Switcher, BasePlugin
from pydantic import BaseModel, Field

class RetryConfig(BaseModel):
    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    backoff: float = Field(default=1.0, description="Backoff multiplier")
    exceptions: tuple = Field(default=(Exception,), description="Exceptions to retry")

class RetryPlugin(BasePlugin):
    """Plugin that retries failed operations with exponential backoff."""

    config_model = RetryConfig

    def wrap_handler(self, switch, entry, call_next):
        """Wrap handler with retry logic."""
        handler_name = entry.name

        def retry_wrapper(*args, **kwargs):
            cfg = self.get_config(handler_name)
            max_attempts = cfg.get('max_attempts', 3)
            backoff = cfg.get('backoff', 1.0)
            exceptions = cfg.get('exceptions', (Exception,))

            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return call_next(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = backoff * (2 ** attempt)
                        print(f"Retry {handler_name}: attempt {attempt + 1} failed, waiting {wait_time}s")
                        time.sleep(wait_time)
                    else:
                        print(f"Retry {handler_name}: all {max_attempts} attempts failed")

            # All retries exhausted
            raise last_exception

        return retry_wrapper

# Register plugin
Switcher.register_plugin("retry", RetryPlugin)

# Usage:
sw = Switcher().plug("retry", flags='')

@sw
def unstable_api_call(endpoint: str):
    """Handler that might fail and needs retries."""
    # Simulate flaky API
    import random
    if random.random() < 0.7:  # 70% failure rate
        raise ConnectionError("API unavailable")
    return f"Success: {endpoint}"

# Configure per-method retries
sw.retry.configure['unstable_api_call'].max_attempts = 5
sw.retry.configure['unstable_api_call'].backoff = 0.5

# Will retry up to 5 times with exponential backoff
result = sw('unstable_api_call')('/users')
```

## Plugin Initialization Parameters

Plugins can accept configuration parameters:

```python
from smartswitch import Switcher, BasePlugin

class ConfigurablePlugin(BasePlugin):
    def __init__(self, option1: str, option2: int = 10, **kwargs):
        super().__init__(name="config", **kwargs)
        self.option1 = option1
        self.option2 = option2

    def wrap_handler(self, switch, entry, call_next):
        # Use self.option1 and self.option2 in wrapping logic
        def wrapper(*args, **kwargs):
            # Access configuration
            return call_next(*args, **kwargs)
        return wrapper

# Register and use:
Switcher.register_plugin('config', ConfigurablePlugin)
sw = Switcher().plug('config', option1="value", option2=20)
```

## Storing State

Plugins can store state and provide query methods:

```python
from smartswitch import Switcher, BasePlugin
from functools import wraps
import time

class StatefulPlugin(BasePlugin):
    def __init__(self, **kwargs):
        super().__init__(name="stats", **kwargs)
        self._call_times = []

    def wrap_handler(self, switch, entry, call_next):
        @wraps(entry.func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = call_next(*args, **kwargs)
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

# Register and use:
Switcher.register_plugin('stats', StatefulPlugin)
sw = Switcher().plug('stats')

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
      .plug('logging', flags='print,enabled')
      .plug('validation')
      .plug('cache'))

@sw
def expensive_computation(x):
    import time
    time.sleep(0.1)
    return x * 2

# Handler is wrapped by all three plugins:
# 1. LoggingPlugin tracks the call
# 2. ValidationPlugin validates inputs
# 3. CachePlugin caches results

result = sw('expensive_computation')(5)  # First call: slow
result = sw('expensive_computation')(5)  # Second call: cached, fast
```

## Standard vs External Plugins

**Standard plugins** (shipped with SmartSwitch):
- Pre-registered, loaded by string name: `sw.plug('logging', flags='enabled')`
- Registered via `Switcher.register_plugin()`
- Examples: `logging`

**External plugins** (third-party packages):
- Must be registered first, then used by name
- Distributed as separate packages
- Examples: `smartretry`, `smartcache`, custom monitoring tools

**Example with external plugin**:
```python
from smartswitch import Switcher
from smartretry import SmartRetryPlugin

# Register the external plugin
Switcher.register_plugin("retry", SmartRetryPlugin)

# Use by name (recommended)
sw = Switcher().plug("retry", max_attempts=3)
```

### Creating an External Plugin Package

For a package like `smartretry`, the structure would be:

```
smartretry/
├── pyproject.toml
├── src/
│   └── smartretry/
│       ├── __init__.py
│       └── plugin.py
└── tests/
    └── test_plugin.py
```

**src/smartretry/__init__.py**:
```python
"""SmartRetry - Retry logic plugin for SmartSwitch."""

from .plugin import SmartRetryPlugin

__version__ = "0.1.0"
__all__ = ["SmartRetryPlugin"]
```

**src/smartretry/plugin.py**:
```python
"""SmartRetry Plugin implementation."""

import time
from smartswitch import BasePlugin
from pydantic import BaseModel, Field

class RetryConfig(BaseModel):
    max_attempts: int = Field(default=3)
    backoff: float = Field(default=1.0)

class SmartRetryPlugin(BasePlugin):
    """Plugin that retries failed operations."""

    config_model = RetryConfig

    def wrap_handler(self, switch, entry, call_next):
        """Wrap handler with retry logic."""
        handler_name = entry.name

        def retry_wrapper(*args, **kwargs):
            cfg = self.get_config(handler_name)
            max_attempts = cfg.get('max_attempts', 3)
            backoff = cfg.get('backoff', 1.0)

            for attempt in range(max_attempts):
                try:
                    return call_next(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(backoff * (2 ** attempt))

        return retry_wrapper
```

**Usage in user code**:
```python
from smartswitch import Switcher
from smartretry import SmartRetryPlugin

# Register plugin
Switcher.register_plugin("retry", SmartRetryPlugin)

# Use by name
sw = Switcher().plug("retry", max_attempts=5)

@sw
def flaky_api_call(url: str):
    # May fail and needs retries
    pass
```

## Best Practices

### 1. Use `@wraps` to Preserve Metadata

Always use `functools.wraps` to preserve function metadata:

```python
from functools import wraps

def wrap_handler(self, switch, entry, call_next):
    @wraps(entry.func)  # Preserves __name__, __doc__, etc.
    def wrapper(*args, **kwargs):
        return call_next(*args, **kwargs)
    return wrapper
```

### 2. Store Switcher Reference Carefully

If you need the Switcher instance later, store it in `on_decorate()`:

```python
def on_decorate(self, switch, func, entry):
    if self._switcher is None:
        self._switcher = switch
    # ... rest of setup

def wrap_handler(self, switch, entry, call_next):
    # Access self._switcher here
    # ... rest of implementation
```

### 3. Provide Clear Public Methods

Design a clean API for users:

```python
class MyPlugin(BasePlugin):
    def wrap_handler(self, switch, entry, call_next):
        # Internal implementation
        def wrapper(*args, **kwargs):
            return call_next(*args, **kwargs)
        return wrapper

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

A: Plugins are applied in registration order. Each plugin's `wrap_handler()` creates a layer in the middleware chain:

```python
sw.plug('plugin1').plug('plugin2').plug('plugin3')

# Execution flows through the chain:
# plugin1.wrap_handler() → plugin2.wrap_handler() → plugin3.wrap_handler() → original function
```

**Q: Can I make a plugin that doesn't wrap the function?**

A: Yes! Just return the original function via `call_next` unchanged. The plugin can still store information in the setup phase:

```python
def on_decorate(self, switch, func, entry):
    # Register function during setup
    self._registered_functions.add(entry.name)

def wrap_handler(self, switch, entry, call_next):
    # Return handler unchanged
    return call_next
```

**Q: How do I access plugin methods from wrapped functions?**

A: Access `self` directly in the wrapper - it's already available:

```python
def wrap_handler(self, switch, entry, call_next):
    @wraps(entry.func)
    def wrapper(*args, **kwargs):
        # Access self (the plugin instance) here
        self.do_something()
        return call_next(*args, **kwargs)

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
def on_decorate(self, switch, func, entry):
    if hasattr(func, '_is_async'):
        # Store metadata about async function
        entry.metadata['async'] = True

def wrap_handler(self, switch, entry, call_next):
    if entry.metadata.get('async'):
        # Handle async function
        pass
    return call_next
```

## Summary

Creating a SmartSwitch plugin (v0.6.0+):

1. ✅ Inherit from `BasePlugin` for common functionality
2. ✅ Override `on_decorate(switch, func, entry)` for setup phase (optional)
3. ✅ Implement `wrap_handler(switch, entry, call_next)` for wrapping logic (required)
4. ✅ Use `entry.metadata[plugin_namespace]` to store/share metadata
5. ✅ Use middleware pattern with `call_next` for proper execution flow
6. ✅ Provide public methods for user interaction
7. ✅ Test with multiple handlers and in combination with other plugins
8. ✅ Document behavior and examples clearly
9. ✅ Register globally with `Switcher.register_plugin()` (optional)

Your plugin will integrate seamlessly with SmartSwitch's `.plug()` system and be accessible via `switcher.plugin_name.method()`.

---

**Need help?** Check existing plugins like `LoggingPlugin` in `src/smartswitch/plugins/logging.py` for reference implementation.
