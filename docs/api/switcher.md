# API Reference

Complete API documentation for SmartSwitch.

## Switcher Class

::: smartswitch.Switcher
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - __call__
        - __get__

## BoundSwitcher (Internal)

`BoundSwitcher` is an internal class created by the descriptor protocol when accessing a `Switcher` from an instance. You don't create it directly - it's returned automatically when you access a switcher from an object.

**Automatic Binding:**
```python
class MyClass:
    dispatch = Switcher()

obj = MyClass()
bound = obj.dispatch  # Returns BoundSwitcher automatically
```

## Usage Examples

### Creating a Switcher

```python
from smartswitch import Switcher

# Basic switcher
sw = Switcher()

# Named switcher with description
sw = Switcher(
    name="my_dispatcher",
    description="Handles user requests"
)

# With prefix-based auto-naming
sw = Switcher(prefix="handle_")
```

### Registering Handlers

```python
# Default handler
@sw
def default_handler(x):
    return f"default: {x}"

# Named handler
@sw
def handle_data(x):
    return f"data: {x}"

# Custom alias
@sw('custom_name')
def my_handler(x):
    return x
```

### Using Handlers

```python
# Named handler access
handler = sw('handle_data')
result = handler(x=42)

# One-liner
result = sw('handle_data')(x=42)

# Using custom alias
result = sw('custom_name')(x=100)
```

### Descriptor Protocol

```python
class MyClass:
    dispatch = sw

    def __init__(self, value):
        self.value = value

@sw
def method(self, x):
    return f"{self.value} + {x}"

obj = MyClass(10)
result = obj.dispatch('method')(x=5)  # "10 + 5"
```

## Type Annotations

SmartSwitch supports full type checking with type hints:

```python
from typing import Union

@sw
def handle_number(value: Union[int, float]) -> str:
    return f"Number: {value}"
```

## See Also

- [Named Handlers Guide](../guide/named-handlers.md)
- [Plugin System](../plugins/index.md)
- [Best Practices](../guide/best-practices.md)
- [Examples](../examples/index.md)
