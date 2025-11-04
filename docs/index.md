<div align="center">
  <img src="assets/logo.png" alt="SmartSwitch Logo" width="200"/>
</div>

# SmartSwitch

**Intelligent rule-based function dispatch for Python**

SmartSwitch is a powerful library that enables elegant function dispatching based on type rules and value conditions. Write cleaner, more maintainable code by separating business logic from control flow.

## Key Features

- **Type-based dispatch**: Route calls based on argument types
- **Value-based dispatch**: Add conditions on argument values
- **Named handlers**: Register and retrieve handlers by name
- **Zero dependencies**: Pure Python 3.10+ standard library
- **High performance**: Optimized with caching and pre-compiled checks
- **Type safe**: Full type hints support

## Quick Example

```python
from smartswitch import Switcher

sw = Switcher()

# Value-based dispatch (more specific - register first!)
@sw(valrule=lambda data: isinstance(data, int) and data < 0)
def process_negative(data):
    return "Negative number"

# Type-based dispatch
@sw(typerule={'data': str})
def process_string(data):
    return f"String: {data}"

@sw(typerule={'data': int})
def process_number(data):
    return f"Number: {data}"

# Default handler
@sw
def process_other(data):
    return f"Other: {data}"

# Use automatic dispatch
print(sw()(data="hello"))  # String: hello
print(sw()(data=42))       # Number: 42
print(sw()(data=-5))       # Negative number

# Or call by name
handler = sw('process_string')
print(handler(data="world"))  # String: world
```

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

- [Installation](user-guide/installation.md)
- [Quick Start](user-guide/quickstart.md)
- [Basic Usage](user-guide/basic.md)
- [Examples](examples/index.md)

## License

MIT License - see LICENSE file for details.
