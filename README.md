<div align="center">

<img src="docs/assets/logo.png" alt="SmartSwitch Logo" width="200"/>

# SmartSwitch

**Intelligent rule-based function dispatch for Python**

</div>

[![PyPI version](https://img.shields.io/pypi/v/smartswitch.svg)](https://pypi.org/project/smartswitch/)
[![Tests](https://github.com/genropy/smartswitch/actions/workflows/test.yml/badge.svg)](https://github.com/genropy/smartswitch/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/genropy/smartswitch/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/smartswitch)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://readthedocs.org/projects/smartswitch/badge/?version=latest)](https://smartswitch.readthedocs.io/)

---

> 📚 **Part of the [genro-libs](https://github.com/softwellsrl/meta-genro-libs) family**
> *General-purpose Python developer tools*

Replace messy if-elif chains and duplicated logic with clean, maintainable function registries.

## Installation

```bash
pip install smartswitch
```

## The Problem-Solution Approach

SmartSwitch helps you organize code that needs to handle different cases. Let's see how, step by step.

### 1. Function Registry Pattern

**Problem**: You have several operations and want to call them by name.

**Traditional approach** - Dictionary of functions:
```python
# Hard to maintain, easy to make mistakes
operations = {
    'save': save_data,
    'load': load_data,
    'delete': delete_data
}

# Calling
op = operations.get(action)
if op:
    op(data)
```

**With SmartSwitch** - Clean registration:
```python
from smartswitch import Switcher

ops = Switcher()

@ops
def save_data(data):
    # Save logic
    pass

@ops
def load_data(data):
    # Load logic
    pass

@ops
def delete_data(data):
    # Delete logic
    pass

# Call by name
ops('save_data')(data)
```

### 2. Custom Action Names

**Problem**: You want friendly names different from function names.

**Traditional approach** - Manual mapping:
```python
actions = {
    'reset': destroy_all_data,
    'clear': remove_cache,
    'wipe': erase_history
}

action = actions[command]
action()
```

**With SmartSwitch** - Alias registration:
```python
ops = Switcher()

@ops('reset')
def destroy_all_data():
    pass

@ops('clear')
def remove_cache():
    pass

# Call with alias
ops('reset')()
```

**Or use prefix-based auto-naming** for convention-driven naming:
```python
# Set a prefix to auto-derive handler names
protocols = Switcher(prefix='protocol_')

@protocols  # Auto-registers as 's3_aws'
def protocol_s3_aws():
    return {"type": "s3", "region": "us-east-1"}

@protocols  # Auto-registers as 'gcs'
def protocol_gcs():
    return {"type": "gcs", "bucket": "data"}

# Call by auto-derived names
protocols('s3_aws')()
protocols('gcs')()
```

### 3. Value-Based Dispatch

**Problem**: Choose handler based on actual data values.

**Traditional approach** - Long if-elif chains:
```python
def process_user(user_type, reason):
    if user_type == 'to_delete' and reason == 'no_payment':
        # Remove user
        pass
    elif reason == 'no_payment':
        # Send reminder
        pass
    elif user_type == 'to_delete':
        # Archive
        pass
    else:
        # Default
        pass
```

**With SmartSwitch** - Declarative rules:
```python
users = Switcher()

@users(valrule=lambda user_type, reason:
       user_type == 'to_delete' and reason == 'no_payment')
def remove_user(user_type, reason):
    # Remove user
    pass

@users(valrule=lambda reason: reason == 'no_payment')
def send_payment_reminder(user_type, reason):
    # Send reminder
    pass

@users(valrule=lambda user_type: user_type == 'to_delete')
def archive_user(user_type, reason):
    # Archive
    pass

@users
def handle_default(user_type, reason):
    # Default
    pass

# Automatic dispatch
users()(user_type='to_delete', reason='no_payment')
```

**Tip**: For multi-parameter conditions, you can use compact dict-style lambda:

```python
@users(valrule=lambda kw: kw['user_type'] == 'to_delete' and kw['reason'] == 'no_payment')
def remove_user(user_type, reason):
    pass
```

### 4. Type-Based Dispatch

**Problem**: Handle different data types differently.

**Traditional approach** - Multiple isinstance checks:
```python
def process(data):
    if isinstance(data, str):
        return data.upper()
    elif isinstance(data, int):
        return data * 2
    elif isinstance(data, list):
        return len(data)
    else:
        return None
```

**With SmartSwitch** - Type rules:
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
    return len(data)

@processor
def process_other(data):
    return None

# Automatic dispatch based on type
processor()(data="hello")  # → HELLO
processor()(data=42)       # → 84
```

## Real-World Examples

### API Routing
```python
api = Switcher()

@api(valrule=lambda method, path: method == 'GET' and path == '/users')
def get_users(method, path, data=None):
    return list_all_users()

@api(valrule=lambda method, path: method == 'POST' and path == '/users')
def create_user(method, path, data=None):
    return create_new_user(data)

@api
def not_found(method, path, data=None):
    return {"error": "Not Found", "status": 404}

# Dispatch
response = api()('GET', '/users')
```

### Payment Processing
```python
payments = Switcher()

@payments(typerule={'amount': int | float},
          valrule=lambda method, amount: method == 'crypto' and amount > 1000)
def process_large_crypto(method, amount, details):
    return {"processor": "crypto_large", "fee": amount * 0.01}

@payments(valrule=lambda method, **kw: method == 'credit_card')
def process_card(method, amount, details):
    return {"processor": "credit_card", "fee": amount * 0.03}

@payments
def process_generic(method, amount, details):
    return {"error": "Unsupported payment method"}
```

## When to Use

✅ **Good for:**
- API handlers and request routers
- Business logic with multiple branches
- Plugin systems and extensible architectures
- State machines and workflow engines
- When you need type + value checks together

⚠️ **Consider alternatives for:**
- Simple 2-3 case switches → use `if/elif`
- Pure type dispatch → use `functools.singledispatch`
- Very high-performance code (< 10μs functions called millions of times)

## Features

- 🎯 **Value-based dispatch**: Match on runtime values
- 📦 **Named handler registry**: Look up by name or alias
- 🔤 **Prefix-based auto-naming**: Convention-driven handler registration
- 🔢 **Type-based dispatch**: Match on argument types
- 🧩 **Modular**: Each handler is separate and testable
- ✨ **Clean API**: Pythonic decorators
- 🚀 **Efficient**: Optimized with caching (~1-2μs overhead)

## Performance

SmartSwitch adds ~1-2 microseconds per dispatch. For real-world functions (API calls, DB queries, business logic), this overhead is negligible:

```
Function time: 50ms (API call)
Dispatch overhead: 0.002ms
Impact: 0.004% ✅
```

## License

MIT

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
