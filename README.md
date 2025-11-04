# smartswitch 🧠

**Intelligent rule-based function dispatch for Python.**

`smartswitch` lets you register functions that are called automatically based on argument types and runtime values — no more chains of `if` or `match`.

## Features

- 🎯 **Type + Value dispatch**: Combine type checking with runtime conditions
- 📦 **Registry pattern**: Lookup handlers by name
- 🧩 **Modular**: Each handler is a separate, testable function
- ✨ **Clean API**: Pythonic decorators
- 🚀 **Efficient**: Optimized implementation for real-world use

## Installation

```bash
pip install smartswitch
```

## Quick Start

```python
from smartswitch import Switcher

switch = Switcher()

# Type-based dispatch
@switch(typerule={'a': int | float, 'b': str})
def handle(a, b):
    return f"{a}:{b}"

# Value-based dispatch
@switch(valrule=lambda a, b: a > 100)
def handle(a, b):
    return f"BIG {a}"

# Default handler
@switch
def handle(a, b):
    return f"default {a}, {b}"

# Use it
print(switch()(3, 'hi'))    # → 3:hi
print(switch()(200, 0))     # → BIG 200
print(switch()('x', 'y'))   # → default x, y
```

## Use Cases

### API Routing

```python
api = Switcher()

@api(valrule=lambda method, path: method == 'GET' and path == '/users')
def handle_request(method, path, data=None):
    return get_users()

@api(valrule=lambda method, path: method == 'POST' and path == '/users')
def handle_request(method, path, data=None):
    return create_user(data)

# Dispatch
response = api()('GET', '/users')
```

### Payment Processing

```python
payments = Switcher()

@payments(typerule={'amount': int | float}, 
          valrule=lambda method, amount: method == 'crypto' and amount > 1000)
def process_payment(method, amount, details):
    return process_crypto_large(amount, details)

@payments(valrule=lambda method: method == 'credit_card')
def process_payment(method, amount, details):
    return process_credit_card(amount, details)

@payments
def process_payment(method, amount, details):
    return process_generic(method, amount, details)
```

### Command Pattern

```python
commands = Switcher()

@commands
def save_document(doc):
    # Save logic
    return {'undo': 'load_document', 'args': (doc.id,)}

@commands
def load_document(doc_id):
    # Load logic
    pass

# Execute by name
result = commands('save_document')(my_doc)
# Later: undo
commands(result['undo'])(*result['args'])
```

## How It Works

SmartSwitch evaluates registered functions in order and calls the first one that matches:

1. **Type rules** (`typerule`): Check argument types
2. **Value rules** (`valrule`): Check runtime values
3. **Default handler**: Catch-all with no rules

### Three Ways to Use

```python
switch = Switcher()

# 1. Register handlers with decorators
@switch(typerule={'x': int})
def my_handler(x): ...

# 2. Call by name
handler = switch('my_handler')
handler(42)

# 3. Automatic dispatch
switch()(42)  # Chooses handler based on rules
```

## When to Use

✅ **Good for:**
- API handlers, business logic, event processors
- When you need type + value checks together
- When functions do I/O or significant work (>1ms)
- When modularity and testability matter

⚠️ **Consider alternatives for:**
- Very fast functions (<10μs) called millions of times
- Simple 2-3 case switches → use `if/elif`
- Pure type dispatch → use `functools.singledispatch`

## Performance

SmartSwitch adds ~1-2 microseconds per dispatch. For functions that do real work (DB queries, API calls, business logic), this overhead is negligible:

```
Function time: 50ms (API call)
Dispatch overhead: 0.002ms
Impact: 0.004% ✅
```

## License

MIT

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
