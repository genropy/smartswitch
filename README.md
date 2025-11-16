<div align="center">

<img src="docs/assets/logo.png" alt="SmartSwitch Logo" width="200"/>

# SmartSwitch

**Named function registry and plugin system for Python**

</div>

[![PyPI version](https://img.shields.io/pypi/v/smartswitch.svg)](https://pypi.org/project/smartswitch/)
[![Tests](https://github.com/genropy/smartswitch/actions/workflows/test.yml/badge.svg)](https://github.com/genropy/smartswitch/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/genropy/smartswitch/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/smartswitch)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://readthedocs.org/projects/smartswitch/badge/?version=latest)](https://smartswitch.readthedocs.io/)

---

**SmartSwitch** is a lightweight Python library for managing function registries with named handlers and extensible plugin architecture. Perfect for API routers, command dispatchers, event handlers, and any scenario where you need clean, maintainable function organization.

## What is SmartSwitch?

SmartSwitch provides two core capabilities:

1. **Named Handler Registry**: Register functions by name or custom alias, then call them dynamically
2. **Plugin System**: Extend functionality with middleware-style plugins for logging, validation, caching, metrics, etc.

**When to use SmartSwitch**:
- Building API routers or command dispatchers
- Creating plugin-based architectures
- Organizing related functions into callable registries
- Need middleware-style function wrapping
- Want clean, testable code instead of if-elif chains

## Installation

```bash
pip install smartswitch
```

## Quick Start

### Basic Handler Registry

```python
from smartswitch import Switcher

# Create a registry
ops = Switcher()

# Register handlers
@ops
def save_data(data):
    return f"Saved: {data}"

@ops
def load_data(data):
    return f"Loaded: {data}"

# Call by name
result = ops['save_data']("my_file.txt")
print(result)  # → "Saved: my_file.txt"
```

### Custom Aliases

```python
ops = Switcher()

# Register with custom names
@ops('reset')
def destroy_all_data():
    return "Everything destroyed"

@ops('clear')
def remove_cache():
    return "Cache cleared"

# Call with friendly alias
result = ops['reset']()
print(result)  # → "Everything destroyed"
```

### Prefix-Based Auto-Naming

Use naming conventions to automatically derive handler names:

```python
# Set a prefix for automatic name derivation
protocols = Switcher(prefix='protocol_')

@protocols  # Auto-registers as 's3_aws' (removes prefix)
def protocol_s3_aws():
    return {"type": "s3", "region": "us-east-1"}

@protocols  # Auto-registers as 'gcs'
def protocol_gcs():
    return {"type": "gcs", "bucket": "data"}

# Call by derived names
result = protocols['s3_aws']()
print(result)  # → {"type": "s3", "region": "us-east-1"}
```

### Hierarchical Organization

Organize multiple Switchers into parent-child relationships:

```python
from smartswitch import Switcher

class MyAPI:
    # Main switcher
    main = Switcher(name="main")

    # Child switchers with hierarchy
    users = Switcher(name="users", parent=main, prefix="user_")
    products = Switcher(name="products", parent=main, prefix="product_")

    @users
    def user_list(self):
        return ["alice", "bob"]

    @products
    def product_list(self):
        return ["laptop", "phone"]

# Direct access
api = MyAPI()
api.users['list']()  # → ["alice", "bob"]

# Hierarchical access via parent
api.main['users.list']()  # → ["alice", "bob"]
api.main['products.list']()  # → ["laptop", "phone"]

# Discover children
for child in api.main.children:
    print(f"{child.name}: {child.entries()}")
```

## Plugin System

Extend SmartSwitch functionality with plugins:

```python
from smartswitch import Switcher

# Create switcher with logging plugin
sw = Switcher().plug('logging', flags='print,enabled,after,time')

@sw
def my_handler(x):
    return x * 2

# Use handler - logs output automatically
result = sw['my_handler'](5)  # → 10
# Output: ← my_handler() → 10 (0.0001s)

# Use before+after for debugging
sw_debug = Switcher().plug('logging', flags='print,enabled,after')

@sw_debug
def process(data):
    return f"Processed: {data}"

sw_debug['process']("test")
# Output:
# → process('test')
# ← process() → Processed: test
```

### Creating Custom Plugins

```python
from smartswitch import Switcher, BasePlugin

class ValidationPlugin(BasePlugin):
    """Validate arguments before handler execution."""

    def wrap_handler(self, switch, entry, call_next):
        def wrapper(*args, **kwargs):
            # Custom validation logic
            if not args:
                raise ValueError("No arguments provided")
            return call_next(*args, **kwargs)
        return wrapper

# Register plugin globally
Switcher.register_plugin('validation', ValidationPlugin)

# Use registered plugin by name
sw = Switcher().plug('validation')

@sw
def process(data):
    return f"Processed: {data}"

# Plugin validates before execution
result = sw['process']("test")  # → "Processed: test"
```

### Chaining Multiple Plugins

```python
from smartswitch import Switcher

# Register custom plugins first
from my_plugins import CachePlugin, MetricsPlugin
Switcher.register_plugin('cache', CachePlugin)
Switcher.register_plugin('metrics', MetricsPlugin)

# Use registered plugins by name
sw = (Switcher()
      .plug('logging', flags='print,enabled,after,time')
      .plug('cache', ttl=300)
      .plug('metrics', namespace='api'))

@sw
def expensive_operation(x):
    # Plugins execute in order: logging → cache → metrics
    return x * 2
```

## Real-World Examples

### API Router

```python
from smartswitch import Switcher

api = Switcher(name="api")

@api('list_users')
def get_users(page=1):
    # Fetch from database
    return {"users": [...], "page": page}

@api('create_user')
def create_user(data):
    # Create user
    return {"id": 123, "created": True}

@api('not_found')
def handle_404():
    return {"error": "Not Found", "status": 404}

# Route requests
def handle_request(endpoint, **kwargs):
    if endpoint in api.entries():
        return api[endpoint](**kwargs)
    return api['not_found']()
```

### Command Dispatcher

```python
cli = Switcher(prefix='cmd_')

@cli
def cmd_backup(target):
    return f"Backing up {target}"

@cli
def cmd_restore(source):
    return f"Restoring from {source}"

@cli('help')
def cmd_show_help():
    return "Available commands: " + ", ".join(cli.entries())

# Dispatch commands
command = input("Enter command: ")
result = cli[command.split()[0]](*command.split()[1:])
```

### Event Handler

```python
events = Switcher()

@events('user.created')
def on_user_created(user_id):
    print(f"Welcome email sent to user {user_id}")

@events('user.deleted')
def on_user_deleted(user_id):
    print(f"Cleanup completed for user {user_id}")

# Emit events
def emit(event_name, *args):
    if event_name in events.entries():
        events[event_name](*args)
```

## Key Features

### Core Functionality

- **Named handler registry**: Register and call functions by name
- **Custom aliases**: Use friendly names different from function names
- **Dict-like access**: Clean `sw['name']()` syntax for handler retrieval
- **Flexible retrieval**: `get()` method with runtime options (default handlers, async wrapping)
- **Prefix-based naming**: Convention-driven automatic name derivation
- **Hierarchical organization**: Parent-child Switcher relationships with dotted-path access
- **Bidirectional async**: Handlers work in both sync and async contexts (CLI + FastAPI)
- **Minimal dependencies**: smartasync, smartseeds (both from Genro-Libs ecosystem)
- **Type-safe**: Full type hints support

### Plugin System

- **Extensible architecture**: Add custom functionality via plugins
- **Clean API**: Access plugins via `sw.plugin_name.method()` pattern
- **Composable**: Chain multiple plugins seamlessly
- **Standard plugins**: Built-in logging plugin included
- **External plugins**: Third-party packages can extend functionality

### Developer Experience

- **Modular & testable**: Each handler is an independent, testable function
- **Clean code**: Replace if-elif chains with declarative registries
- **High performance**: Optimized with caching (~1-2μs overhead per call)
- **Well documented**: Comprehensive guides and tested examples

## Performance

SmartSwitch adds minimal overhead (~1-2 microseconds per dispatch). For real-world functions doing actual work (API calls, database queries, business logic), this is negligible:

```
Function execution time: 50ms (API call)
SmartSwitch overhead: 0.002ms
Relative impact: 0.004% ✅
```

**Good for:**
- API handlers and request routers
- Command dispatchers
- Event handling systems
- Business logic organization
- Any function doing real work (>1ms execution time)

**Consider alternatives for:**
- Ultra-fast functions (<10μs) called millions of times per second
- Simple 2-3 case switches (plain if-elif is fine)

See [Performance Best Practices](https://smartswitch.readthedocs.io/guide/best-practices/#performance-best-practices) for details.

## Thread Safety

SmartSwitch is designed for typical Python usage patterns:

- **Handler dispatch** (calling `sw['name'](args)`) is **fully thread-safe** - uses read-only operations
- **Decorator registration** should be done at **module import time** (single-threaded)

**Recommended usage**:
```python
# Module level - executed once at import (safe)
switch = Switcher()

@switch
def my_handler(x):
    return x * 2

# Runtime - called many times (thread-safe)
result = switch['my_handler'](42)
```

For advanced scenarios requiring runtime registration in multi-threaded applications, external synchronization is needed.

## Documentation

📚 **Full documentation**: [smartswitch.readthedocs.io](https://smartswitch.readthedocs.io/)

**User Guides:**
- [Installation](https://smartswitch.readthedocs.io/user-guide/installation/)
- [Quick Start](https://smartswitch.readthedocs.io/user-guide/quickstart/)
- [Basic Usage](https://smartswitch.readthedocs.io/user-guide/basic/)

**Feature Guides:**
- [Named Handlers](https://smartswitch.readthedocs.io/guide/named-handlers/) - Function registry patterns
- [API Discovery](https://smartswitch.readthedocs.io/guide/api-discovery/) - Introspection and hierarchies
- [Best Practices](https://smartswitch.readthedocs.io/guide/best-practices/) - Production patterns

**Plugin System:**
- [Plugin Overview](https://smartswitch.readthedocs.io/plugins/index/) - Understanding plugins
- [Plugin Development](https://smartswitch.readthedocs.io/plugins/development/) - Create custom plugins
- [Logging Plugin](https://smartswitch.readthedocs.io/plugins/logging/) - Call history tracking

**Reference:**
- [API Reference](https://smartswitch.readthedocs.io/api/switcher/) - Complete API docs
- [Architecture](https://smartswitch.readthedocs.io/appendix/architecture/) - Internal design

**All examples in documentation are tested** - They come directly from our test suite with 92% coverage.

## License

MIT

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

---

<div align="center">
<sub>Part of the Genro-Libs family of developer tools</sub>
</div>
