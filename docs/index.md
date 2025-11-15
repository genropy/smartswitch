<div align="center">
  <img src="_static/logo.png" alt="SmartSwitch Logo" width="200"/>
</div>

# SmartSwitch

**Named function registry and plugin system for Python**

## What is SmartSwitch?

SmartSwitch is a lightweight library that helps you organize and manage functions using two core capabilities:

1. **Named Handler Registry**: Register functions by name or custom alias, then call them dynamically
2. **Plugin System**: Extend functionality with middleware-style plugins for logging, validation, and more

**In one sentence**: SmartSwitch turns your functions into a callable registry with extensible middleware.

## When is SmartSwitch Useful?

SmartSwitch shines in these scenarios:

- **API Routers**: Map endpoint names to handler functions
- **Command Dispatchers**: Build CLI tools with named command handlers
- **Event Handlers**: Create event-driven systems with clean handler registration
- **Plugin Architectures**: Need middleware-style wrapping around functions
- **Code Organization**: Replace messy if-elif chains with declarative function registries

## Key Features

### Core Functionality

- **Named handler registry**: Call functions by name using decorator-based registration
- **Custom aliases**: Use friendly names different from function names
- **Prefix-based naming**: Convention-driven automatic name derivation
- **Hierarchical organization**: Parent-child Switcher relationships with dotted-path access
- **Zero dependencies**: Pure Python 3.10+ standard library
- **Type safe**: Full type hints support

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
- **Well documented**: Comprehensive guides with tested examples

## Quick Example

### Basic Usage

Replace this messy code:

```python
# Manual dictionary - error-prone
operations = {
    'save': save_data,
    'load': load_data,
    'delete': delete_data
}

# Need to check existence
op = operations.get(action)
if op:
    result = op(data)
```

With clean, self-registering handlers:

```python
from smartswitch import Switcher

ops = Switcher()

@ops
def save_data(data):
    return f"Saved {data}"

@ops
def load_data(data):
    return f"Loaded {data}"

@ops
def delete_data(data):
    return f"Deleted {data}"

# Clean, direct call
result = ops('save_data')(data)
```

### With Plugins

Add logging to track all handler calls:

```python
from smartswitch import Switcher

# Create switcher with logging plugin
sw = Switcher().plug('logging', mode='print,after,time')

@sw
def my_handler(x):
    return x * 2

# Use handler
result = sw('my_handler')(5)  # → 10

# Access plugin to analyze history
print(history)  # → [{'handler': 'my_handler', 'args': (5,), 'result': 10, ...}]

# Find slow operations
slowest = sw.logging.history(slowest=5)
```

## Learning Path

### For Beginners

Start here to understand the basics:

1. **[Installation](user-guide/installation.md)** - Get SmartSwitch installed
2. **[Quick Start](user-guide/quickstart.md)** - Learn the two core patterns in minutes
3. **[Basic Usage](user-guide/basic.md)** - Understand decorator patterns and calling conventions

### For Production Use

Deep dive into specific features:

- **[Named Handlers](guide/named-handlers.md)** - Registry patterns, aliases, prefix-based naming
- **[API Discovery](guide/api-discovery.md)** - Introspection and hierarchical organization
- **[Best Practices](guide/best-practices.md)** - Production patterns and performance tips

### For Extension Developers

Build custom functionality:

- **[Plugin System Overview](plugins/index.md)** - Understanding the plugin architecture
- **[Plugin Development](plugins/development.md)** - Create your own plugins
- **[Middleware Pattern](plugins/middleware.md)** - Advanced plugin patterns

## Why SmartSwitch?

Traditional approaches to conditional logic often lead to:

- Long if-elif chains that grow over time
- Duplicate code across similar handlers
- Hard-to-maintain monolithic functions
- Poor testability and code organization

SmartSwitch solves these problems by:

- **Separating registration from invocation**: Functions self-register, you call by name
- **Making handlers independent**: Each function is standalone and testable
- **Enabling composition**: Plugins add cross-cutting concerns without modifying handlers
- **Providing clear structure**: Hierarchical organization for complex systems

## Real-World Example

Here's a complete API router implementation:

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
    handler = api._methods.get(endpoint)
    if handler:
        return api(endpoint)(**kwargs)
    return api('not_found')()

# Use it
response = handle_request('list_users', page=2)
print(response)  # → {"users": [...], "page": 2}
```

## Get Started

Install with pip:

```bash
pip install smartswitch
```

Then check out the [Quick Start Guide](user-guide/quickstart.md) to begin using SmartSwitch in your projects.

## Performance

SmartSwitch adds minimal overhead (~1-2 microseconds per dispatch). For real-world functions doing actual work (API calls, database queries, business logic), this overhead is negligible:

```
Function execution time: 50ms (API call)
SmartSwitch overhead: 0.002ms
Relative impact: 0.004% ✅
```

See [Performance Best Practices](guide/best-practices.md#performance-best-practices) for details.

## Documentation

```{toctree}
:maxdepth: 2
:caption: Getting Started

user-guide/overview
user-guide/installation
user-guide/quickstart
user-guide/basic
```

```{toctree}
:maxdepth: 2
:caption: User Guide

guide/named-handlers
guide/api-discovery
guide/best-practices
```

```{toctree}
:maxdepth: 2
:caption: Plugin System

plugins/index
plugins/development
plugins/middleware
plugins/logging
```

```{toctree}
:maxdepth: 2
:caption: Examples

examples/index
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/switcher
```

```{toctree}
:maxdepth: 2
:caption: Advanced

appendix/architecture
```

## License

MIT License - see LICENSE file for details.
