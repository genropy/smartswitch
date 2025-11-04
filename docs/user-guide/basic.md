# Basic Usage

This guide covers the fundamental concepts and patterns for using SmartSwitch effectively.

## Creating a Switcher

```python
from smartswitch import Switcher

sw = Switcher()
```

## Handler Registration

### Type-Based Handlers

Register handlers that match based on argument types:

```python
@sw.typerule(str)
def process(text):
    return text.upper()

@sw.typerule(int)
def process(number):
    return number * 2

@sw.typerule(list)
def process(items):
    return len(items)
```

### Value-Based Handlers

Add conditions on argument values:

```python
@sw.valrule(lambda x: x < 10)
def handle_small(x):
    return "small"

@sw.valrule(lambda x: x >= 10 and x < 100)
def handle_medium(x):
    return "medium"

@sw.valrule(lambda x: x >= 100)
def handle_large(x):
    return "large"
```

### Multiple Arguments

Handlers can accept multiple arguments:

```python
@sw.typerule(str, int)
def format_message(text, count):
    return f"{text} (x{count})"

@sw.typerule(int, int)
def add_numbers(a, b):
    return a + b
```

Value rules receive all arguments as a tuple:

```python
@sw.valrule(lambda args: args[0] > args[1])
def compare(a, b):
    return f"{a} is greater than {b}"
```

## Calling Handlers

### By Name

Call registered handlers by name:

```python
result = sw('process', "hello")
```

### Direct Call

If you have a reference to the handler:

```python
handler = sw.get('process', str)
result = handler("hello")
```

## Rule Priority

When multiple rules match, SmartSwitch uses this priority:

1. Value rules (most specific)
2. Type rules
3. Default handlers (least specific)

Example:

```python
@sw.typerule(int)
def handle(x):
    return "any int"

@sw.valrule(lambda x: x < 0)
def handle(x):
    return "negative int"

# Value rule wins
print(sw('handle', -5))   # "negative int"
print(sw('handle', 5))    # "any int"
```

## Working with Complex Types

### Union Types

```python
from typing import Union

@sw.typerule(Union[str, int])
def process(data):
    return f"String or int: {data}"
```

### Generic Types

```python
from typing import List

@sw.typerule(List[int])
def sum_numbers(numbers):
    return sum(numbers)
```

### Custom Classes

```python
class Person:
    def __init__(self, name):
        self.name = name

@sw.typerule(Person)
def greet(person):
    return f"Hello, {person.name}!"
```

## Error Handling

### No Match Found

When no handler matches, SmartSwitch raises `KeyError`:

```python
try:
    sw('unknown_handler', "data")
except KeyError as e:
    print(f"No handler found: {e}")
```

### Type Checking

SmartSwitch validates types at call time:

```python
@sw.typerule(int)
def process(x):
    return x * 2

# This will not match the int handler
sw('process', "not an int")  # May raise KeyError or match different handler
```

## Best Practices

### 1. Clear Handler Names

Use descriptive names that indicate what the handler does:

```python
@sw.typerule(str)
def parse_user_input(text):
    return text.strip().lower()
```

### 2. Document Rules

Add docstrings to explain matching conditions:

```python
@sw.valrule(lambda x: 0 <= x <= 100)
def validate_percentage(value):
    """Validates that value is a valid percentage (0-100)."""
    return value
```

### 3. Avoid Side Effects in Rules

Value rules should be pure functions:

```python
# Good
@sw.valrule(lambda x: x > 0)
def handle(x):
    return x

# Bad - don't modify state in rules
@sw.valrule(lambda x: some_global_list.append(x) or True)
def handle(x):
    return x
```

### 4. Group Related Handlers

Keep related handlers together in your code:

```python
# File processors
@sw.typerule(str)
def process_filename(name): ...

@sw.typerule(Path)
def process_path(path): ...

# Number processors
@sw.typerule(int)
def process_integer(n): ...

@sw.typerule(float)
def process_float(n): ...
```

## Next Steps

- Explore [Examples](../examples/index.md) for real-world use cases
- Learn about advanced patterns (coming soon)
