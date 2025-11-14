# Quick Start

This guide will get you up and running with SmartSwitch in minutes.

## Installation

```bash
pip install smartswitch
```

## The Four Core Patterns

SmartSwitch solves four common problems. Let's see them in order of complexity.

### 1. Call Functions by Name

**Your situation**: You have operations and want to call them by name.

```python
from smartswitch import Switcher

ops = Switcher()

@ops
def save_data(data):
    return f"Saved: {data}"

@ops
def load_data(data):
    return f"Loaded: {data}"

# Call by name
result = ops('save_data')("my_file.txt")
print(result)  # → "Saved: my_file.txt"
```

### 2. Use Custom Aliases

**Your situation**: Function names are long, but you want short command names.

```python
ops = Switcher()

@ops('reset')
def destroy_all_data():
    return "Everything destroyed"

@ops('clear')
def remove_cache():
    return "Cache cleared"

# Call with friendly alias
result = ops('reset')()
print(result)  # → "Everything destroyed"
```

### 3. Dispatch on Values

**Your situation**: Different logic based on actual data values.

```python
sw = Switcher()

@sw(valrule=lambda status: status == 'active')
def handle_active(status, user):
    return f"Processing active user: {user}"

@sw(valrule=lambda status: status == 'suspended')
def handle_suspended(status, user):
    return f"User {user} is suspended"

@sw
def handle_other(status, user):
    return f"Unknown status for {user}"

# Automatic dispatch based on values
result = sw()(status='active', user='Alice')
print(result)  # → "Processing active user: Alice"
```

**Alternative: Compact lambda syntax**

You can also use a compact dict-style lambda for complex conditions:

```python
sw = Switcher()

@sw(valrule=lambda kw: kw['status'] == 'active' and kw['user'].startswith('A'))
def handle_special(status, user):
    return f"Special processing for {user}"

@sw(valrule=lambda kw: kw['status'] == 'active')
def handle_active(status, user):
    return f"Processing active user: {user}"
```

This is useful when you need to check multiple parameters in one condition.

### 4. Dispatch on Types

**Your situation**: Different handling for different data types.

```python
processor = Switcher()

@processor(typerule={'data': str})
def process_string(data):
    return data.upper()

@processor(typerule={'data': int})
def process_number(data):
    return data * 2

@processor(typerule={'data': list})
def process_list(data):
    return f"{len(data)} items"

# Automatic dispatch based on type
print(processor()(data="hello"))    # → "HELLO"
print(processor()(data=42))         # → 84
print(processor()(data=[1,2,3]))    # → "3 items"
```

## Combining Patterns

You can mix patterns as needed:

```python
handler = Switcher()

# Type AND value rules together
@handler(typerule={'amount': int | float},
         valrule=lambda amount: amount > 1000)
def handle_large_amount(amount):
    return f"Large: {amount}"

@handler(typerule={'amount': int | float})
def handle_normal_amount(amount):
    return f"Normal: {amount}"

@handler
def handle_other(amount):
    return f"Invalid: {amount}"

# Automatic dispatch
print(handler()(amount=5000))    # → "Large: 5000"
print(handler()(amount=50))      # → "Normal: 50"
print(handler()(amount="bad"))   # → "Invalid: bad"
```

## Two Ways to Use

SmartSwitch offers two calling patterns:

```python
sw = Switcher()

@sw
def my_handler(x):
    return x * 2

# 1. By name - you choose the handler
result = sw('my_handler')(x=5)  # → 10

# 2. Automatic - rules choose the handler
# (when using typerule/valrule)
result = sw()(x=5)  # → 10 if my_handler matches
```

## Real Example: API Router

```python
api = Switcher()

@api(valrule=lambda method, path: method == 'GET' and path == '/users')
def list_users(method, path):
    return {"users": ["Alice", "Bob"]}

@api(valrule=lambda method, path: method == 'POST' and path == '/users')
def create_user(method, path):
    return {"created": True}

@api
def not_found(method, path):
    return {"error": "Not Found"}

# Use it
response = api()(method='GET', path='/users')
print(response)  # → {"users": ["Alice", "Bob"]}
```

## Next Steps

- Learn more in the [Basic Usage Guide](basic.md)
- See more examples in [Examples](../examples/index.md)
- Check out the detailed guides: [Named Handlers](../guide/named-handlers.md), [Plugin System](../plugins/index.md)

## Quick Reference

```python
from smartswitch import Switcher

sw = Switcher()

# Register by function name
@sw
def my_function(): pass

# Register with alias
@sw('alias_name')
def my_function(): pass

# Register with value rule
@sw(valrule=lambda x: x > 10)
def handle_large(x): pass

# Register with type rule
@sw(typerule={'x': int})
def handle_int(x): pass

# Register with both
@sw(typerule={'x': int}, valrule=lambda x: x > 0)
def handle_positive_int(x): pass

# Call by name
sw('my_function')()

# Automatic dispatch
sw()(x=value)
```
