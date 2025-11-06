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

# Type rule
@sw(typerule={'x': int})
def handle_int(x):
    return f"int: {x}"

# Value rule
@sw(valrule=lambda x: x > 0)
def handle_positive(x):
    return "positive"

# Combined rules
@sw(typerule={'x': int}, valrule=lambda x: x > 0)
def handle_positive_int(x):
    return "positive int"

# Custom alias
@sw('custom_name')
def my_handler(x):
    return x
```

### Using Handlers

```python
# Automatic dispatch
result = sw()(x=42)

# Named handler access
handler = sw('handle_int')
result = handler(x=42)

# One-liner
result = sw('handle_int')(x=42)
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

SmartSwitch supports full type checking:

```python
from typing import Union

@sw(typerule={'value': int | float})
def handle_number(value: Union[int, float]) -> str:
    return f"Number: {value}"
```

## See Also

- [Type Rules Guide](../guide/typerules.md)
- [Value Rules Guide](../guide/valrules.md)
- [Named Handlers Guide](../guide/named-handlers.md)
- [Examples](../examples/index.md)
