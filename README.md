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

## Key Features

### Core Dispatch Mechanisms

- 🔢 **[Type-based dispatch](https://smartswitch.readthedocs.io/guide/typerules/)**: Route by argument types (`int`, `str`, custom classes, unions)
- 🎯 **[Value-based dispatch](https://smartswitch.readthedocs.io/guide/valrules/)**: Match on runtime values with lambda rules
- 🔗 **[Combined rules](https://smartswitch.readthedocs.io/guide/best-practices/)**: Use type AND value rules together for precise routing

### Handler Management

- 📦 **[Named handler access](https://smartswitch.readthedocs.io/guide/named-handlers/)**: Retrieve and call handlers by name
- 🏷️ **[Custom aliases](https://smartswitch.readthedocs.io/guide/named-handlers/#custom-aliases)**: Register handlers with user-friendly names
- 🔤 **[Prefix-based auto-naming](https://smartswitch.readthedocs.io/guide/named-handlers/#prefix-based-auto-naming)**: Convention-driven handler registration (NEW in v0.1.0)

### Developer Experience

- 🧩 **Modular & testable**: Each handler is an independent function
- ✨ **Clean API**: Pythonic decorators with zero boilerplate
- 🚀 **Efficient**: Optimized with caching (~1-2μs overhead)
- 🛡️ **Type-safe**: Full type annotation support

### API Discovery and Introspection

- 🔍 **[Handler introspection](https://smartswitch.readthedocs.io/guide/api-discovery/)**: List all registered handlers with `entries()` method (v0.3.0)
- 🌳 **[Hierarchical structures](https://smartswitch.readthedocs.io/guide/api-discovery/#organizing-multiple-switchers)**: Organize multiple Switchers with `add()` method (v0.3.1)
- 🔗 **[Dot notation access](https://smartswitch.readthedocs.io/guide/api-discovery/#hierarchical-access)**: Navigate hierarchies with dot notation like `mainswitch('users.list')` (NEW in v0.3.1)

### Logging and Observability

- 📊 **[Call history tracking](https://smartswitch.readthedocs.io/guide/logging/)**: Record handler executions with args, results, timing (NEW in v0.4.0)
- 🔍 **[Performance analysis](https://smartswitch.readthedocs.io/guide/logging/#performance-analysis)**: Find slowest calls, analyze execution patterns
- 🐛 **[Error tracking](https://smartswitch.readthedocs.io/guide/logging/#error-tracking)**: Filter and analyze failed executions
- 🤫 **[Silent mode](https://smartswitch.readthedocs.io/guide/logging/#silent-mode-default)**: Zero-overhead history tracking for production

### Plugin System (NEW in v0.5.0)

- 🔌 **[Extensible architecture](docs/plugin-development.md)**: Add custom functionality via plugins
- 🎨 **[Clean API](docs/plugin-development.md#plugin-naming)**: Access plugins via `sw.plugin_name.method()` pattern
- 🧩 **[Composable](docs/plugin-development.md#chaining-multiple-plugins)**: Chain multiple plugins together seamlessly
- 📦 **[Standard plugins](docs/plugin-development.md#standard-vs-external-plugins)**: Built-in logging, type rules, value rules
- 🌐 **[External plugins](docs/plugin-development.md#creating-an-external-plugin-package)**: Third-party packages can extend functionality

**Using plugins:**
```python
from smartswitch import Switcher

# Standard plugin (built-in)
sw = Switcher().plug('logging', mode='silent', time=True)

@sw
def my_handler(x):
    return x * 2

sw('my_handler')(5)

# Access plugin via attribute
sw.logger.history()           # Get call history
sw.logger.history(slowest=5)  # 5 slowest calls
sw.logger.clear()             # Clear history
```

**External plugins:**
```python
from smartswitch import Switcher
from smartasync import SmartAsyncPlugin

# Add external plugin
sw = Switcher().plug(SmartAsyncPlugin())

@sw
async def fetch_data(url: str):
    # async implementation
    pass

# Plugin methods accessible
sw.async_support.is_async('fetch_data')  # True
```

**Chaining plugins:**
```python
sw = (Switcher()
      .plug('logging', mode='silent')
      .plug(SmartAsyncPlugin())
      .plug(YourCustomPlugin()))
```

See the [Plugin Development Guide](docs/plugin-development.md) for creating your own plugins.

**Organizing multiple Switchers in a class:**
```python
from smartswitch import Switcher

class MyAPI:
    # Main switcher
    mainswitch = Switcher(name="main")

    # Add child switchers
    users = mainswitch.add(Switcher(name="users", prefix="user_"))
    products = mainswitch.add(Switcher(name="products", prefix="product_"))

    @users
    def user_list(self):
        return ["alice", "bob"]

    @products
    def product_list(self):
        return ["laptop", "phone"]

# Use directly
api = MyAPI()
api.users('list')()  # Direct access

# Or via mainswitch with dot notation
api.mainswitch('users.list')()  # Hierarchical access
api.mainswitch('products.list')()
```

**Discovering child Switchers:**
```python
# Iterate all children
for child in api.mainswitch.children:
    print(f"{child.name}: {child.entries()}")
# Output:
# users: ['list']
# products: ['list']
```

See the [API Discovery Guide](https://smartswitch.readthedocs.io/guide/api-discovery/) for details, or [smpub](https://github.com/genropy/smpub) for production usage.

## Documentation

📚 **Full documentation**: [smartswitch.readthedocs.io](https://smartswitch.readthedocs.io/)

**Guides:**
- [Type Rules](https://smartswitch.readthedocs.io/guide/typerules/) - Dispatch based on types
- [Value Rules](https://smartswitch.readthedocs.io/guide/valrules/) - Dispatch based on runtime values
- [Named Handlers](https://smartswitch.readthedocs.io/guide/named-handlers/) - Direct handler access
- [API Discovery](https://smartswitch.readthedocs.io/guide/api-discovery/) - Introspection and hierarchies
- [Logging](https://smartswitch.readthedocs.io/guide/logging/) - History tracking and performance analysis (NEW in v0.4.0)
- [Plugin Development](docs/plugin-development.md) - Create your own plugins (NEW in v0.5.0)
- [Best Practices](https://smartswitch.readthedocs.io/guide/best-practices/) - Production patterns
- [API Reference](https://smartswitch.readthedocs.io/api/switcher/) - Complete API docs

**All examples in documentation are tested** - They come directly from our test suite with 95% coverage.

## Performance

SmartSwitch adds ~1-2 microseconds per dispatch. For real-world functions (API calls, DB queries, business logic), this overhead is negligible:

```
Function time: 50ms (API call)
Dispatch overhead: 0.002ms
Impact: 0.004% ✅
```

See [Performance Best Practices](https://smartswitch.readthedocs.io/guide/best-practices/#performance-best-practices) for more details.

## Thread Safety

SmartSwitch is designed for typical Python usage patterns:

- **✅ Handler dispatch** (calling `sw()(args)`) is **fully thread-safe** - uses read-only operations
- **⚠️ Decorator registration** should be done at **module import time** (single-threaded)

**Recommended usage**:
```python
# Module level - executed once at import (safe)
switch = Switcher()

@switch(typerule={'x': int})
def handle_int(x):
    return x * 2

# Runtime - called many times (thread-safe)
result = switch()(x=42)
```

For advanced scenarios requiring runtime registration in multi-threaded applications, external synchronization is needed.

## License

MIT

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

---

<div align="center">
<sub>✨ Part of the genro-libs family of developer tools ✨</sub>
</div>
