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

@sw.typerule(str)
def process(data):
    return f"Processing string: {data}"

@sw.typerule(int)
def process(data):
    return f"Processing number: {data}"

@sw.valrule(lambda x: x < 0)
def process(data):
    return "Processing negative number"

print(sw('process', "hello"))    # Processing string: hello
print(sw('process', 42))          # Processing number: 42
print(sw('process', -5))          # Processing negative number
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
