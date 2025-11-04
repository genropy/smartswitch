# Basic Usage

This guide covers the fundamental concepts and patterns for using SmartSwitch effectively.

## Creating a Switcher

```python
from smartswitch import Switcher

sw = Switcher()
```

You can also give your switcher a name for debugging:

```python
sw = Switcher(name="my_dispatcher")
```

## Handler Registration

### Type-Based Handlers

Register handlers that match based on argument types using the `typerule` parameter:

```python
sw = Switcher()

@sw(typerule={'text': str})
def process(text):
    return text.upper()

@sw(typerule={'number': int})
def process(number):
    return number * 2

@sw(typerule={'items': list})
def process(items):
    return len(items)

# Automatic dispatch
print(sw()(text="hello"))     # HELLO
print(sw()(number=5))         # 10
print(sw()(items=[1,2,3]))    # 3
```

The `typerule` parameter takes a dictionary mapping parameter names to their expected types.

### Value-Based Handlers

Add conditions on argument values using the `valrule` parameter:

```python
sw = Switcher()

@sw(valrule=lambda x: x < 10)
def handle_small(x):
    return "small"

@sw(valrule=lambda x: x >= 10 and x < 100)
def handle_medium(x):
    return "medium"

@sw(valrule=lambda x: x >= 100)
def handle_large(x):
    return "large"

print(sw()(x=5))    # small
print(sw()(x=50))   # medium
print(sw()(x=500))  # large
```

The `valrule` parameter takes a lambda (or any callable) that receives the arguments as keyword parameters and returns a boolean.

### Multiple Arguments

Handlers can accept multiple arguments. Type rules specify types for each parameter:

```python
sw = Switcher()

@sw(typerule={'text': str, 'count': int})
def format_message(text, count):
    return f"{text} (x{count})"

@sw(typerule={'a': int, 'b': int})
def add_numbers(a, b):
    return a + b

print(sw()(text="hi", count=3))  # hi (x3)
print(sw()(a=5, b=10))           # 15
```

Value rules receive all arguments:

```python
sw = Switcher()

@sw(valrule=lambda a, b: a > b)
def compare_greater(a, b):
    return f"{a} is greater than {b}"

@sw(valrule=lambda a, b: a < b)
def compare_less(a, b):
    return f"{a} is less than {b}"

@sw(valrule=lambda a, b: a == b)
def compare_equal(a, b):
    return f"{a} equals {b}"

print(sw()(a=10, b=5))   # 10 is greater than 5
print(sw()(a=3, b=7))    # 3 is less than 7
print(sw()(a=5, b=5))    # 5 equals 5
```

## Calling Handlers

### Automatic Dispatch

Use `sw()` to get a dispatcher that automatically selects the right handler:

```python
sw = Switcher()

@sw(typerule={'x': int})
def handle(x):
    return "integer"

@sw(typerule={'x': str})
def handle(x):
    return "string"

# Call with sw()
result = sw()(x=42)      # "integer"
result = sw()(x="hi")    # "string"
```

### By Name

Use `sw('name')` to retrieve a specific handler by its function name:

```python
sw = Switcher()

@sw(typerule={'x': int})
def process(x):
    return x * 2

# Get handler by name
handler = sw('process')

# Call it
result = handler(x=5)  # 10

# Or in one line
result = sw('process')(x=5)  # 10
```

## Rule Priority

When multiple rules could match, SmartSwitch evaluates them in registration order and uses the first match:

```python
sw = Switcher()

# Registered first - more specific
@sw(typerule={'x': int}, valrule=lambda x: x < 0)
def handle(x):
    return "negative int"

# Registered second - less specific
@sw(typerule={'x': int})
def handle(x):
    return "any int"

# Default - least specific
@sw
def handle(x):
    return "anything"

print(sw()(x=-5))    # "negative int" (first match)
print(sw()(x=5))     # "any int" (second match)
print(sw()(x="hi"))  # "anything" (default)
```

**Best practice**: Register more specific rules before more general ones.

## Working with Complex Types

### Union Types

Specify multiple allowed types using `|` or `Union`:

```python
from typing import Union

sw = Switcher()

@sw(typerule={'value': int | float})
def process_number(value):
    return f"Number: {value * 2}"

@sw(typerule={'value': str})
def process_text(value):
    return f"Text: {value.upper()}"

print(sw()(value=5))       # Number: 10
print(sw()(value=2.5))     # Number: 5.0
print(sw()(value="hi"))    # Text: HI
```

### Custom Classes

You can dispatch based on custom class types:

```python
class Person:
    def __init__(self, name):
        self.name = name

class Company:
    def __init__(self, name):
        self.name = name

sw = Switcher()

@sw(typerule={'entity': Person})
def greet(entity):
    return f"Hello, {entity.name}!"

@sw(typerule={'entity': Company})
def greet(entity):
    return f"Welcome, {entity.name} Corp!"

person = Person("Alice")
company = Company("Acme")

print(sw()(entity=person))    # Hello, Alice!
print(sw()(entity=company))   # Welcome, Acme Corp!
```

## Combining Type and Value Rules

You can combine both types of rules in a single decorator:

```python
sw = Switcher()

# Only positive integers
@sw(typerule={'x': int}, valrule=lambda x: x > 0)
def handle_positive_int(x):
    return f"Positive int: {x}"

# Only negative integers
@sw(typerule={'x': int}, valrule=lambda x: x < 0)
def handle_negative_int(x):
    return f"Negative int: {x}"

# Any string longer than 5 chars
@sw(typerule={'x': str}, valrule=lambda x: len(x) > 5)
def handle_long_string(x):
    return f"Long string: {x}"

# Default
@sw
def handle_other(x):
    return f"Other: {x}"

print(sw()(x=10))         # Positive int: 10
print(sw()(x=-5))         # Negative int: -5
print(sw()(x="hello!"))   # Long string: hello!
print(sw()(x="hi"))       # Other: hi
```

## Error Handling

### No Match Found

When no handler matches and there's no default, SmartSwitch raises a `ValueError`:

```python
sw = Switcher()

@sw(typerule={'x': int})
def handle(x):
    return x

try:
    sw()(x="not an int")
except ValueError as e:
    print(f"Error: {e}")  # No rule matched
```

Always provide a default handler to avoid this:

```python
sw = Switcher()

@sw(typerule={'x': int})
def handle(x):
    return f"int: {x}"

@sw  # Default catches everything
def handle(x):
    return f"other: {x}"

# No error
print(sw()(x="text"))  # other: text
```

### Handler Not Found by Name

If you request a handler name that doesn't exist, you'll get a `KeyError`:

```python
sw = Switcher()

@sw
def existing_handler(x):
    return x

try:
    handler = sw('nonexistent')
except KeyError as e:
    print(f"Handler not found: {e}")
```

## Best Practices

### 1. Use Descriptive Handler Names

Handler function names are used for lookup, so make them descriptive:

```python
# Good
@sw(typerule={'user_input': str})
def parse_user_input(user_input):
    return user_input.strip().lower()

# Less clear
@sw(typerule={'x': str})
def f(x):
    return x.strip().lower()
```

### 2. Document Rules with Docstrings

Add docstrings to explain what conditions trigger each handler:

```python
@sw(typerule={'value': int}, valrule=lambda value: 0 <= value <= 100)
def validate_percentage(value):
    """
    Validates that value is a valid percentage (0-100).

    Args:
        value: Integer to validate

    Returns:
        The validated percentage value
    """
    return value
```

### 3. Keep Value Rules Pure

Value rules should be pure functions with no side effects:

```python
# Good - pure function
@sw(valrule=lambda x: x > 0)
def handle_positive(x):
    return x

# Bad - side effects in rule
counter = []
@sw(valrule=lambda x: (counter.append(x), True)[1])  # Don't do this!
def handle_with_side_effects(x):
    return x
```

### 4. Order Matters

Register more specific rules before more general ones:

```python
sw = Switcher()

# Specific first
@sw(typerule={'x': int}, valrule=lambda x: x < 0)
def handle_negative(x):
    return "negative"

# General second
@sw(typerule={'x': int})
def handle_any_int(x):
    return "any int"

# Default last
@sw
def handle_anything(x):
    return "anything"
```

### 5. Use Type Hints

Add type hints to your handlers for better IDE support:

```python
@sw(typerule={'text': str, 'count': int})
def repeat_text(text: str, count: int) -> str:
    return text * count
```

### 6. Group Related Handlers

Keep related handlers together in your code:

```python
# String processors
@sw(typerule={'data': str})
def process_filename(data):
    return Path(data)

@sw(typerule={'data': str}, valrule=lambda data: data.startswith('http'))
def process_url(data):
    return URL(data)

# Number processors
@sw(typerule={'data': int})
def process_integer(data):
    return data

@sw(typerule={'data': float})
def process_float(data):
    return round(data, 2)
```

## Advanced Patterns

### Positional Arguments

While named parameters (`x=5`) work best with SmartSwitch, you can also use positional arguments. SmartSwitch will map them to parameter names:

```python
sw = Switcher()

@sw(typerule={'a': int, 'b': int})
def add(a, b):
    return a + b

# Both work
result = sw()(a=5, b=10)  # Named
result = sw()(5, 10)      # Positional
```

### Mixed Arguments

You can mix positional and keyword arguments:

```python
@sw(typerule={'x': int, 'y': int})
def calculate(x, y):
    return x + y

result = sw()(5, y=10)  # Mixed - works!
```

## Next Steps

- Explore [Examples](../examples/index.md) for real-world use cases
- Learn about the [Descriptor Protocol](advanced/descriptors.md) for class-based usage (coming soon)
- See [Performance Tips](advanced/performance.md) for optimization strategies (coming soon)
