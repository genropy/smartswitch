# SmartSwitch - LLM Quick Reference

## Core Purpose
Named function registry and plugin system for Python. Register handlers by name, organize them hierarchically, and extend functionality with plugins. ~2μs dispatch overhead.

## Installation
```bash
pip install smartswitch
```

## Essential Patterns

### 1. Named Handler Registry
```python
from smartswitch import Switcher

ops = Switcher()

@ops  # Auto-registers as 'save_data'
def save_data(data):
    return f"Saved: {data}"

@ops('custom_name')  # Register with alias
def process(data):
    return f"Processed: {data}"

# Call by name
result = ops('save_data')(data)
result = ops('custom_name')(data)
```

### 2. Hierarchical Organization
```python
class MyAPI:
    root = Switcher(name="api")
    users = root.add(Switcher(name="users", prefix="user_"))
    products = root.add(Switcher(name="products", prefix="product_"))

    @users
    def user_list(self):
        return ["alice", "bob"]

    @products
    def product_list(self):
        return ["laptop", "phone"]

api = MyAPI()
api.users('list')()              # Direct access
api.root('users.list')()         # Via hierarchy
```

### 3. Prefix-Based Auto-Naming
```python
handlers = Switcher(prefix='handle_')

@handlers  # Auto-registers as 'payment'
def handle_payment(amount):
    return f"Processing ${amount}"

@handlers  # Auto-registers as 'refund'
def handle_refund(amount):
    return f"Refunding ${amount}"

handlers('payment')(100)
```

### 4. Plugin System (v0.5.0+)
```python
from smartswitch import Switcher, BasePlugin

class LoggingPlugin(BasePlugin):
    def wrap_handler(self, func, name, switcher):
        def wrapper(*args, **kwargs):
            print(f"Calling {name}")
            result = func(*args, **kwargs)
            print(f"Result: {result}")
            return result
        return wrapper

sw = Switcher(plugins=[LoggingPlugin()])

@sw
def process(data):
    return f"Processed: {data}"

sw('process')("test")  # Logs before and after
```

## Method Binding (Class Usage)
```python
class Service:
    ops = Switcher()

    @ops
    def save(self, data):
        return f"Saved by {self.name}"

    def __init__(self, name):
        self.name = name

svc = Service("DB")
svc.ops('save')("data")  # 'self' bound automatically
```

## Critical Rules

1. **Decorator registration** = module-level (thread-safe)
2. **Handler dispatch** = runtime (fully thread-safe)
3. **Named dispatch only** - No automatic rule-based dispatch
4. **Plugin hooks**: `on_decorate()` and `wrap_handler()`

## Common Use Cases

✅ **Do**: API routers, method registries, plugin architectures, hierarchical organization
❌ **Don't**: Use for 2-3 simple cases (use if/elif)

## Quick Introspection
```python
sw = Switcher(name="api")
sw.entries()        # List all handler names
sw.children         # Set of child Switchers
sw.parent           # Parent Switcher or None
```

## Advanced Features
See additional files in llm-docs/:
- **API-DETAILS.md**: Complete API reference with all methods and parameters
- **PATTERNS.md**: Real-world usage patterns from production code

For complete documentation including plugin system, see `docs/` directory:
- Core features: `docs/guide/`
- Plugin development: `docs/plugins/`
- Examples: `docs/examples/`

## Version
Current: 0.9.2 (Python 3.10+)

## Performance
~2μs dispatch overhead. Negligible for typical business logic (DB, API calls, etc.)

## Quick Troubleshooting

**Name not found**: Check registered names with `sw.entries()`
**Name collision**: Use custom aliases `@sw('unique_name')`
**Method binding issue**: Ensure Switcher is class attribute, not instance
