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
@sw(typerule={'name': str})
def greet_by_name(name):
    return f"Hello, {name}!"

# Register a handler for integers
@sw(typerule={'age': int})
def greet_by_age(age):
    return f"You are {age} years old"

# Use automatic dispatch
print(sw()(name="Alice"))  # Hello, Alice!
print(sw()(age=25))        # You are 25 years old

# Or call by name
handler = sw('greet_by_name')
print(handler(name="Bob"))  # Hello, Bob!
```

## Type Rules

Type rules dispatch based on the type of arguments:

```python
sw = Switcher()

@sw(typerule={'data': str})
def process_string(data):
    return data.upper()

@sw(typerule={'data': list})
def process_list(data):
    return len(data)

@sw(typerule={'data': dict})
def process_dict(data):
    return list(data.keys())

# Automatic dispatch
print(sw()(data="hello"))      # HELLO
print(sw()(data=[1, 2, 3]))    # 3
print(sw()(data={'a': 1}))     # ['a']
```

## Value Rules

Value rules add conditions on runtime values:

```python
sw = Switcher()

@sw(valrule=lambda x: x < 0)
def handle_negative(x):
    return "negative"

@sw(valrule=lambda x: x == 0)
def handle_zero(x):
    return "zero"

@sw(valrule=lambda x: x > 0)
def handle_positive(x):
    return "positive"

# Automatic dispatch
print(sw()(x=-5))  # negative
print(sw()(x=0))   # zero
print(sw()(x=5))   # positive

# By name
print(sw('handle_positive')(x=10))  # positive
```

## Combining Type and Value Rules

You can combine both types of rules:

```python
sw = Switcher()

# Only match positive integers
@sw(typerule={'x': int}, valrule=lambda x: x > 0)
def process_positive_int(x):
    return f"Positive: {x}"

# Only match negative integers
@sw(typerule={'x': int}, valrule=lambda x: x < 0)
def process_negative_int(x):
    return f"Negative: {x}"

# Only match strings
@sw(typerule={'x': str})
def process_string(x):
    return f"String: {x}"

print(sw()(x=5))      # Positive: 5
print(sw()(x=-5))     # Negative: -5
print(sw()(x="hi"))   # String: hi
```

## Default Handlers

Register a fallback handler without rules:

```python
sw = Switcher()

# Specific handlers
@sw(typerule={'data': int})
def process_integer(data):
    return f"Integer: {data}"

# Default handler (catches everything else)
@sw
def process_default(data):
    return f"Unknown type: {type(data).__name__}"

print(sw()(data=42))      # Integer: 42
print(sw()(data="text"))  # Unknown type: str
print(sw()(data=[1,2]))   # Unknown type: list
```

## Multiple Parameters

Handlers can work with multiple parameters:

```python
sw = Switcher()

@sw(typerule={'a': int, 'b': int})
def add_numbers(a, b):
    return a + b

@sw(typerule={'a': str, 'b': str})
def concat_strings(a, b):
    return a + b  # String concatenation

@sw(typerule={'a': int, 'b': str})
def format_mixed(a, b):
    return f"{a}:{b}"

print(sw()(a=5, b=10))       # 15
print(sw()(a="hi", b="!"))   # hi!
print(sw()(a=3, b="test"))   # 3:test
```

## Using Union Types

You can specify multiple allowed types:

```python
from typing import Union

sw = Switcher()

@sw(typerule={'value': int | float})
def process_number(value):
    return value * 2

@sw(typerule={'value': str})
def process_text(value):
    return value.upper()

print(sw()(value=5))      # 10
print(sw()(value=2.5))    # 5.0
print(sw()(value="hi"))   # HI
```

## Two Ways to Call

SmartSwitch offers two calling patterns:

```python
sw = Switcher()

@sw(typerule={'x': int})
def compute(x):
    return x * 2

# 1. Automatic dispatch - rules decide which handler
result = sw()(x=5)

# 2. By name - explicitly get the handler
handler = sw('compute')
result = handler(x=5)
```

## Next Steps

Learn more in the [Basic Usage Guide](basic.md) or explore [Examples](../examples/index.md).
