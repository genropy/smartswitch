<div align="center">
  <img src="_static/logo.png" alt="SmartSwitch Logo" width="200"/>
</div>

# SmartSwitch

**Intelligent function registry and dispatch for Python**

SmartSwitch is a powerful library that enables elegant function dispatching through named registries and plugin-based composition. Write cleaner, more maintainable code by separating business logic from control flow.

## Key Features

- **Named handler registry**: Call functions by name or custom alias
- **Plugin system**: Extend functionality with middleware-style plugins
- **Zero dependencies**: Pure Python 3.10+ standard library
- **High performance**: Optimized with caching and pre-compiled checks
- **Type safe**: Full type hints support

## Learning by Example

The best way to understand SmartSwitch is to see how it solves real problems. Let's go step by step.

### 1. The Registry Pattern

**The Problem**: You have multiple operations and want to invoke them by name.

**Without SmartSwitch**:
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

**With SmartSwitch**:
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

**Why it's better**:
- No manual dictionary maintenance
- Functions self-register with decorator
- Clear, declarative code

### 2. Custom Aliases

**The Problem**: Function names don't match user-facing command names.

**Without SmartSwitch**:
```python
# Awkward mapping
command_map = {
    'reset': destroy_all_data,
    'clear': remove_cache,
    'wipe': erase_history
}

handler = command_map[user_command]
handler()
```

**With SmartSwitch**:
```python
ops = Switcher()

@ops('reset')
def destroy_all_data():
    return "All data destroyed"

@ops('clear')
def remove_cache():
    return "Cache cleared"

@ops('wipe')
def erase_history():
    return "History erased"

# Use friendly names
result = ops('reset')()
```

**Why it's better**:
- Aliases defined right where function is defined
- No separate mapping to maintain
- Function name can be descriptive, alias can be short

## Why SmartSwitch?

Traditional approaches to conditional logic often lead to:
- Long if-elif chains
- Duplicate code
- Hard to maintain functions
- Poor testability

SmartSwitch solves these problems by:
- Separating logic from dispatch
- Making rules explicit and testable
- Enabling modular handler composition
- Providing clear, readable code

## Get Started

Install with pip:

```bash
pip install smartswitch
```

Then check out the [Quick Start Guide](user-guide/quickstart.md) to begin using SmartSwitch in your projects.

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
appendix/vs-match
```

## License

MIT License - see LICENSE file for details.
