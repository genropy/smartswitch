# Quick Start

This guide will get you up and running with SmartSwitch in minutes.

## Basic Concept

SmartSwitch allows you to register multiple implementations of the same function and automatically dispatch to the right one based on:

1. **Type rules** - Match based on argument types
2. **Value rules** - Match based on runtime values

## Your First Switcher

```python
from smartswitch import Switcher

# Create a switcher instance
sw = Switcher()

# Register a handler for strings
@sw.typerule(str)
def greet(name):
    return f"Hello, {name}!"

# Register a handler for integers
@sw.typerule(int)
def greet(age):
    return f"You are {age} years old"

# Call the appropriate handler
print(sw('greet', "Alice"))  # Hello, Alice!
print(sw('greet', 25))        # You are 25 years old
```

## Type Rules

Type rules dispatch based on the type of arguments:

```python
@sw.typerule(str)
def process(data):
    return data.upper()

@sw.typerule(list)
def process(data):
    return len(data)

@sw.typerule(dict)
def process(data):
    return list(data.keys())
```

## Value Rules

Value rules add conditions on values:

```python
@sw.valrule(lambda x: x < 0)
def handle_number(x):
    return "negative"

@sw.valrule(lambda x: x == 0)
def handle_number(x):
    return "zero"

@sw.valrule(lambda x: x > 0)
def handle_number(x):
    return "positive"

print(sw('handle_number', -5))  # negative
print(sw('handle_number', 0))   # zero
print(sw('handle_number', 5))   # positive
```

## Combining Rules

You can combine type and value rules:

```python
# Only match positive integers
@sw.typerule(int)
@sw.valrule(lambda x: x > 0)
def process_positive_int(x):
    return f"Positive: {x}"

# Only match negative integers
@sw.typerule(int)
@sw.valrule(lambda x: x < 0)
def process_negative_int(x):
    return f"Negative: {x}"
```

## Default Handlers

Register a fallback handler without rules:

```python
@sw.default()
def process_anything(data):
    return f"Unknown type: {type(data).__name__}"
```

## Next Steps

Learn more in the [Basic Usage Guide](basic.md) or explore [Examples](../examples/index.md).
