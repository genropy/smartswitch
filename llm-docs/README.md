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

# Call by name - dict-like access
result = ops['save_data'](data)
result = ops['custom_name'](data)

# Or with options
handler = ops.get('save_data', use_smartasync=True)
result = handler(data)
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
api.users['list']()              # Direct access
api.root['users.list']()         # Via hierarchy
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

handlers['payment'](100)
```

### 4. Plugin System (v0.5.0+, updated v0.10.0)
```python
from smartswitch import Switcher, BasePlugin
from pydantic import BaseModel, Field

# Define configuration with Pydantic
class LogConfig(BaseModel):
    enabled: bool = Field(default=True)
    verbose: bool = Field(default=False)

class LoggingPlugin(BasePlugin):
    config_model = LogConfig

    def wrap_handler(self, switch, entry, call_next):
        handler_name = entry.name

        def wrapper(*args, **kwargs):
            cfg = self.get_config(handler_name)
            if cfg.get('enabled'):
                print(f"→ Calling {handler_name}")
            result = call_next(*args, **kwargs)
            if cfg.get('verbose'):
                print(f"← Result: {result}")
            return result
        return wrapper

# Register plugin
Switcher.register_plugin('mylog', LoggingPlugin)

# Use with flags
sw = Switcher().plug('mylog', flags='enabled,verbose')

@sw
def process(data):
    return f"Processed: {data}"

sw['process']("test")  # Logs with config
# Runtime config: sw.mylog.configure.verbose = False
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
svc.ops['save']("data")  # 'self' bound automatically
```

## Critical Rules

1. **Decorator registration** = module-level (thread-safe)
2. **Handler retrieval** = `sw['name']` or `sw.get('name', **options)` (fully thread-safe)
3. **Named dispatch only** - No automatic rule-based dispatch
4. **Plugin hooks**: `on_decore(switch, func, entry)` and `wrap_handler(switch, entry, call_next)`
5. **Plugin registration**: Use `Switcher.register_plugin(name, PluginClass)` then `.plug(name, flags=...)`
6. **Plugin config** (v0.10.0+): Pydantic-based with runtime changes via `.configure`
7. **SmartAsync wrapping** (v0.10.0+): Bidirectional sync/async support via `get_use_smartasync=True`

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
Current: 0.10.0 (Python 3.10+)

**v0.10.0 highlights**:
- **SmartAsync integration**: Bidirectional sync/async handler wrapping
- **New API**: `get()` method and `__getitem__` dict-like access
- **SmartSeeds integration**: Smart options with `extract_kwargs` decorator
- **Flexible defaults**: `get_default_handler`, `get_use_smartasync` at init
- Pydantic-based plugin configuration system
- Runtime configuration with `.configure` property
- `flags` parameter for boolean settings
- Per-method configuration overrides

## Performance
~2μs dispatch overhead. Negligible for typical business logic (DB, API calls, etc.)

## Quick Troubleshooting

**Name not found**: Check registered names with `sw.entries()`
**Name collision**: Use custom aliases `@sw('unique_name')`
**Method binding issue**: Ensure Switcher is class attribute, not instance
