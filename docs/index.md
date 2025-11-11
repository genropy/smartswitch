<div align="center">
  <img src="_static/logo.png" alt="SmartSwitch Logo" width="200"/>
</div>

# SmartSwitch

**Intelligent rule-based function dispatch for Python**

SmartSwitch is a powerful library that enables elegant function dispatching based on type rules and value conditions. Write cleaner, more maintainable code by separating business logic from control flow.

## Key Features

- **Named handler registry**: Call functions by name or custom alias
- **Value-based dispatch**: Route calls based on argument values
- **Type-based dispatch**: Route calls based on argument types
- **Zero dependencies**: Pure Python 3.10+ standard library
- **High performance**: Optimized with caching and pre-compiled checks
- **Type safe**: Full type hints support

## Learning by Example

The best way to understand SmartSwitch is to see how it solves real problems. Let's go step by step.

### 1. The Registry Pattern

**The Problem**: You have multiple operations and want to invoke them by name.

**Without SmartSwitch**:
```python
# Manual dictionary - error-prone
operations = {
    'save': save_data,
    'load': load_data,
    'delete': delete_data
}

# Need to check existence
op = operations.get(action)
if op:
    result = op(data)
```

**With SmartSwitch**:
```python
from smartswitch import Switcher

ops = Switcher()

@ops
def save_data(data):
    return f"Saved {data}"

@ops
def load_data(data):
    return f"Loaded {data}"

@ops
def delete_data(data):
    return f"Deleted {data}"

# Clean, direct call
result = ops('save_data')(data)
```

**Why it's better**:
- No manual dictionary maintenance
- Functions self-register with decorator
- Clear, declarative code

### 2. Custom Aliases

**The Problem**: Function names don't match user-facing command names.

**Without SmartSwitch**:
```python
# Awkward mapping
command_map = {
    'reset': destroy_all_data,
    'clear': remove_cache,
    'wipe': erase_history
}

handler = command_map[user_command]
handler()
```

**With SmartSwitch**:
```python
ops = Switcher()

@ops('reset')
def destroy_all_data():
    return "All data destroyed"

@ops('clear')
def remove_cache():
    return "Cache cleared"

@ops('wipe')
def erase_history():
    return "History erased"

# Use friendly names
result = ops('reset')()
```

**Why it's better**:
- Aliases defined right where function is defined
- No separate mapping to maintain
- Function name can be descriptive, alias can be short

### 3. Value-Based Logic

**The Problem**: Complex business logic with many conditions.

**Without SmartSwitch**:
```python
def handle_user(user_type, reason):
    # Long, nested if-elif chains
    if user_type == 'to_delete' and reason == 'no_payment':
        # Remove user immediately
        remove_user()
    elif reason == 'no_payment':
        # Just send reminder
        send_payment_reminder()
    elif user_type == 'to_delete':
        # Archive for other reasons
        archive_user()
    else:
        # Normal processing
        process_user()
```

**With SmartSwitch**:
```python
users = Switcher()

@users(valrule=lambda user_type, reason:
       user_type == 'to_delete' and reason == 'no_payment')
def remove_user(user_type, reason):
    return "User removed"

@users(valrule=lambda reason: reason == 'no_payment')
def send_payment_reminder(user_type, reason):
    return "Reminder sent"

@users(valrule=lambda user_type: user_type == 'to_delete')
def archive_user(user_type, reason):
    return "User archived"

@users
def process_user(user_type, reason):
    return "User processed"

# Automatic dispatch - right handler chosen
result = users()(user_type='to_delete', reason='no_payment')
```

**Why it's better**:
- Each handler is separate, testable function
- Rules are declarative and explicit
- Easy to add new cases without touching existing code
- No deep nesting

**Compact lambda syntax**: For complex multi-parameter conditions, you can use dict-style lambda:

```python
@users(valrule=lambda kw: kw['user_type'] == 'to_delete' and kw['reason'] == 'no_payment')
def remove_user(user_type, reason):
    return "User removed"
```

This allows checking multiple parameters in a single compact expression.

### 4. Type-Based Routing

**The Problem**: Different handling for different data types.

**Without SmartSwitch**:
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

**With SmartSwitch**:
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
result = processor()(data="hello")  # → "HELLO"
result = processor()(data=42)       # → 84
result = processor()(data=[1,2,3])  # → 3
```

**Why it's better**:
- Type checking is declarative
- Each type handler is independent
- Easy to extend with new types
- More maintainable than isinstance chains

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

```{toctree}
:maxdepth: 2
:caption: Getting Started

user-guide/installation
user-guide/quickstart
user-guide/basic
```

```{toctree}
:maxdepth: 2
:caption: User Guide

guide/named-handlers
guide/api-discovery
guide/valrules
guide/typerules
guide/logging
guide/best-practices
```

```{toctree}
:maxdepth: 2
:caption: Plugin System

plugin-development
guide/middleware-pattern
```

```{toctree}
:maxdepth: 2
:caption: Examples

examples/index
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/switcher
```

```{toctree}
:maxdepth: 2
:caption: Advanced

appendix/architecture
appendix/vs-match
```

## License

MIT License - see LICENSE file for details.
