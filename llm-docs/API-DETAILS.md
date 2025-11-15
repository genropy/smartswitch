# SmartSwitch - Complete API Reference

## Switcher Class

### Constructor

```python
Switcher(
    name: str = "default",
    description: str | None = None,
    prefix: str | None = None,
    parent: Switcher | None = None,
    plugins: list[BasePlugin] | None = None
)
```

**Parameters:**
- `name`: Identifier for this Switcher (used in logs, hierarchies)
- `description`: Optional human-readable description
- `prefix`: If set, auto-derive handler names by removing prefix from function names
- `parent`: Parent Switcher for hierarchical APIs
- `plugins`: List of plugin instances to apply to all handlers (v0.5.0+)

**Example:**
```python
from smartswitch import Switcher

sw = Switcher(name="api", prefix="handle_")
```

### Decorator Methods

#### `@sw` - Register Handler by Function Name

```python
@sw
def handler(args):
    pass
```

Registers handler using function name (or prefix-stripped name if prefix is set).

**Example:**
```python
sw = Switcher()

@sw
def save_data(data):
    return f"Saved: {data}"

# Call by name
sw('save_data')(data)
```

#### `@sw('name')` - Register with Custom Name

```python
@sw('custom_name')
def handler(args):
    pass
```

Registers with specified alias. Also works for lookup if name exists.

**Example:**
```python
@sw('process')
def handler(data):
    return f"Processed: {data}"

sw('process')(data)
```

### Call Methods

#### Get Handler by Name

```python
handler = sw('handler_name')
result = handler(args)
```

Returns callable handler. Supports dot notation for hierarchical access: `sw('child.handler')`

**Example:**
```python
sw = Switcher()

@sw
def process(data):
    return f"Processed: {data}"

# Get handler
handler = sw('process')
# Call handler
result = handler("test")  # → "Processed: test"
```

**Hierarchical access:**
```python
root = Switcher(name="api")
users = root.add(Switcher(name="users"))

@users
def list():
    return ["alice", "bob"]

# Access via dot notation
root('users.list')()  # → ["alice", "bob"]
```

### Hierarchy Management

#### `.add(switcher)` / `.add_child(switcher)`

```python
child = parent.add(Switcher(name="child"))
```

Adds child Switcher and sets bidirectional parent-child relationship. Returns child for chaining.

**Example:**
```python
api = Switcher(name="api")
users = api.add(Switcher(name="users"))
products = api.add(Switcher(name="products"))

# Access via parent
api('users')  # → users Switcher
api('products')  # → products Switcher
```

#### `.remove_child(switcher)`

```python
parent.remove_child(child)
```

Removes child and unsets parent relationship.

#### `.parent` property

```python
parent = sw.parent          # Get parent
sw.parent = new_parent      # Set parent (auto-registers with parent)
sw.parent = None            # Unset parent
```

#### `.children` property

```python
children = sw.children      # Returns set of child Switchers
```

**Example:**
```python
api = Switcher(name="api")
users = api.add(Switcher(name="users"))
products = api.add(Switcher(name="products"))

for child in api.children:
    print(child.name)  # → "users", "products"
```

### Introspection

#### `.entries()`

```python
names = sw.entries()        # List of all handler names
```

**Example:**
```python
sw = Switcher()

@sw
def process():
    pass

@sw
def save():
    pass

sw.entries()  # → ['process', 'save']
```

#### `.name` attribute

```python
sw.name = "new_name"
```

#### `.description` attribute

```python
sw.description = "API for user management"
```

## BoundSwitcher Class

Automatically created when accessing Switcher as class attribute. Binds `self` to handlers.

```python
class Service:
    ops = Switcher()

    @ops
    def process(self, data):
        return f"{self.name}: {data}"

    def __init__(self, name):
        self.name = name

svc = Service("MyService")
svc.ops('process')(data)  # 'self' bound automatically
```

**Methods:** Same as Switcher, with automatic `self` binding.

## BasePlugin Class (v0.5.0+, updated v0.10.0)

Base class for creating custom plugins that extend Switcher functionality.

**New in v0.10.0**: Pydantic-based configuration system with `config_model`, `flags` parameter, and runtime configuration via `.configure` property.

### Configuration System (v0.10.0+)

Plugins can define a `config_model` (Pydantic BaseModel) for validated configuration:

```python
from pydantic import BaseModel, Field

class MyPluginConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable plugin")
    verbose: bool = Field(default=False, description="Verbose output")
    timeout: int = Field(default=30, description="Timeout in seconds")

class MyPlugin(BasePlugin):
    config_model = MyPluginConfig

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
```

**Using flags for boolean parameters:**
```python
# Register plugin
Switcher.register_plugin('myplugin', MyPlugin)

# Configure with flags
sw = Switcher().plug('myplugin', flags='enabled,verbose')

# Runtime configuration
sw.myplugin.configure.flags = 'enabled,verbose:off'
sw.myplugin.configure.timeout = 60
```

### Methods to Override

#### `on_decorate(switch, func, entry)`

Called when a handler is decorated, **before** wrapping. Use for initialization, validation, or storing metadata.

**Parameters:**
- `switch`: The Switcher instance
- `func`: The original function being decorated
- `entry`: MethodEntry object with handler metadata (name, func, etc.)

**Example:**
```python
class MetadataPlugin(BasePlugin):
    def on_decorate(self, switch, func, entry):
        # Store registration time in entry metadata
        if not hasattr(entry, '_plugin_meta'):
            entry._plugin_meta = {}
        entry._plugin_meta['registered_at'] = time.time()
```

#### `wrap_handler(switch, entry, call_next)`

Called to wrap the handler function. Return a wrapper function that calls `call_next()`.

**Parameters:**
- `switch`: The Switcher instance
- `entry`: MethodEntry object with handler metadata
- `call_next`: The next layer in the middleware chain (call this to execute handler)

**Returns:** Wrapped function

**Example:**
```python
class LoggingPlugin(BasePlugin):
    def wrap_handler(self, switch, entry, call_next):
        handler_name = entry.name

        def wrapper(*args, **kwargs):
            # Get runtime config (supports dynamic changes)
            cfg = self.get_config(handler_name)

            if cfg.get('enabled'):
                print(f"→ Calling {handler_name}")

            result = call_next(*args, **kwargs)

            if cfg.get('enabled'):
                print(f"← Done: {handler_name}")

            return result
        return wrapper
```

### Complete Plugin Example

```python
from smartswitch import Switcher, BasePlugin
from pydantic import BaseModel, Field
import time

# Define configuration model
class TimingConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable timing")
    verbose: bool = Field(default=False, description="Show detailed timing")

class TimingPlugin(BasePlugin):
    config_model = TimingConfig

    def on_decorate(self, switch, func, entry):
        # Store registration time in entry metadata
        if not hasattr(entry, '_timing_meta'):
            entry._timing_meta = {'registered_at': time.time()}

    def wrap_handler(self, switch, entry, call_next):
        handler_name = entry.name

        def wrapper(*args, **kwargs):
            # Get runtime config
            cfg = self.get_config(handler_name)

            if not cfg.get('enabled'):
                return call_next(*args, **kwargs)

            start = time.time()
            result = call_next(*args, **kwargs)
            elapsed = time.time() - start

            if cfg.get('verbose'):
                print(f"{handler_name} took {elapsed:.6f}s")
            else:
                print(f"{handler_name}: {elapsed:.4f}s")

            return result
        return wrapper

# Register plugin globally
Switcher.register_plugin('timing', TimingPlugin)

# Use registered plugin
sw = Switcher().plug('timing', flags='enabled,verbose')

@sw
def slow_operation():
    time.sleep(0.1)
    return "done"

sw('slow_operation')()  # Prints timing

# Runtime configuration changes
sw.timing.configure.verbose = False
sw('slow_operation')()  # Different format
```

## Built-in Plugins

### LoggingPlugin (v0.4.0+, updated v0.10.0)

Real-time call logging with flexible output options and runtime configuration.

**Usage:**
```python
from smartswitch import Switcher

# Register automatically on import (already registered)
sw = Switcher().plug('logging', flags='print,enabled,after,time')

@sw
def process(data):
    return data * 2

sw('process')(42)
# Output: ← process() → 84 (0.0001s)
```

**Configuration flags:**
- `enabled` (default: False): Enable plugin
- `print` (default: False): Output via print()
- `log` (default: True): Output via Python logging
- `before` (default: True): Show input parameters
- `after` (default: False): Show return value
- `time` (default: False): Show execution time

**Runtime configuration:**
```python
# Change config globally
sw.logging.configure.flags = 'print,enabled,before,after,time'

# Per-method configuration
sw.logging.configure['process'].flags = 'enabled:off'
sw.logging.configure['critical_op'].flags = 'after,time'
```

**See full documentation:** [docs/plugins/logging.md](../docs/plugins/logging.md)

### PydanticPlugin (v0.5.0+)

Validates handler arguments using type hints and Pydantic models.

**Installation:**
```bash
pip install smartswitch[pydantic]
```

**Usage:**
```python
from smartswitch import Switcher

# Register plugin first
from smartswitch.plugins import PydanticPlugin
Switcher.register_plugin('pydantic', PydanticPlugin)

# Use by name
sw = Switcher().plug('pydantic')

@sw
def create_user(name: str, age: int, email: str):
    return {"name": name, "age": age, "email": email}

# Valid
sw('create_user')("Alice", 30, "alice@example.com")

# Invalid - raises ValidationError
sw('create_user')("Alice", "thirty", "invalid-email")
```

**Behavior:**
- Automatically validates arguments against type hints
- Raises `ValidationError` on type mismatch
- Supports all Pydantic types and validators
- Works with `from __future__ import annotations`

## Method Binding (Descriptor Protocol)

Switcher implements `__get__` for automatic method binding in classes:

```python
class API:
    handlers = Switcher()

    @handlers
    def save(self, data):
        return f"{self.name} saved {data}"

    def __init__(self, name):
        self.name = name

api = API("DB")
api.handlers('save')("data")  # 'self' automatically bound
```

**How it works:**
- When accessed as class attribute, Switcher returns a `BoundSwitcher`
- `BoundSwitcher` automatically passes instance (`self`) to handlers
- All Switcher methods work the same on `BoundSwitcher`

## Thread Safety

### Safe Operations (Read-Only)
- Handler dispatch: `sw('name')(args)` ✅
- Introspection: `sw.entries()`, `sw.children` ✅
- Handler lookup: `sw('name')` ✅

### Unsafe Operations (Require External Locking)
- Decorator registration: `@sw` ⚠️ (should be at module level)
- Hierarchy modification: `sw.add()`, `sw.remove_child()` ⚠️

**Best Practice:** Register handlers at module import (single-threaded), dispatch at runtime (fully thread-safe).

## Performance Characteristics

- **Dispatch overhead**: ~2μs per call
- **Handler lookup**: O(1) dictionary access
- **Hierarchical access**: +~1μs per level with dot notation
- **Plugin overhead**: Negligible (wrapping happens once at decoration)
- **Memory**: Minimal (handlers stored as dict references)

**Good for:**
- API handlers (I/O bound)
- Business logic (DB queries, calculations)
- Event handlers
- Command processors

**Not ideal for:**
- Ultra-fast functions called millions of times (<10μs functions)
- Performance-critical inner loops
- Simple 2-3 case dispatches (use if/elif)

## Common Patterns

### API Router
```python
class API:
    router = Switcher(name="api")

    @router
    def get_users(self):
        return ["alice", "bob"]

    @router
    def create_user(self, name):
        return {"id": 123, "name": name}

api = API()
api.router('get_users')()
api.router('create_user')("charlie")
```

### Command Pattern
```python
commands = Switcher(prefix='cmd_')

@commands
def cmd_start():
    return "Started"

@commands
def cmd_stop():
    return "Stopped"

commands('start')()
commands('stop')()
```

### Plugin System with Chaining
```python
from smartswitch import Switcher, BasePlugin

# Register custom plugins
class CachePlugin(BasePlugin):
    def wrap_handler(self, switch, entry, call_next):
        cache = {}
        def wrapper(*args, **kwargs):
            key = (args, tuple(kwargs.items()))
            if key not in cache:
                cache[key] = call_next(*args, **kwargs)
            return cache[key]
        return wrapper

class MetricsPlugin(BasePlugin):
    def wrap_handler(self, switch, entry, call_next):
        def wrapper(*args, **kwargs):
            print(f"Metrics: {entry.name} called")
            return call_next(*args, **kwargs)
        return wrapper

Switcher.register_plugin('cache', CachePlugin)
Switcher.register_plugin('metrics', MetricsPlugin)

# Chain multiple plugins
sw = (Switcher()
      .plug('logging', flags='print,enabled,after')
      .plug('cache')
      .plug('metrics'))

@sw
def expensive_operation(x):
    return x * 2
```

### Hierarchical Organization
```python
api = Switcher(name="api")
v1 = api.add(Switcher(name="v1"))
v2 = api.add(Switcher(name="v2"))

@v1
def users():
    return ["alice"]

@v2
def users():
    return ["alice", "bob", "charlie"]

api('v1.users')()  # → ["alice"]
api('v2.users')()  # → ["alice", "bob", "charlie"]
```

## Error Handling

### ValueError - Handler Not Found by Name

Raised when handler name not found:
```python
try:
    sw('nonexistent')
except ValueError as e:
    print(f"Handler not found: {e}")
```

### TypeError - Invalid Decorator Usage

Raised on invalid decorator arguments:
```python
try:
    @sw(invalid_argument)
    def handler():
        pass
except TypeError as e:
    print(f"Invalid usage: {e}")
```

## Debugging Tips

1. **List all handlers**: `print(sw.entries())`
2. **Check hierarchy**: `print([c.name for c in sw.children])`
3. **Inspect handler**: `print(sw('name').__wrapped__)`
4. **Check parent**: `print(sw.parent.name if sw.parent else 'No parent')`

## Version History

- **0.10.0**: Pydantic-based plugin configuration system with runtime flexibility
  - `flags` parameter for boolean settings
  - Runtime configuration via `.configure` property
  - Per-method configuration overrides
  - LoggingPlugin with full Pydantic configuration
- **0.6.0**: Plugin lifecycle hooks (`on_decorate()`), metadata sharing
- **0.5.0**: Plugin system with `BasePlugin`, global registry, `PydanticPlugin`
- **0.4.0**: Refactored core, improved type hints
- **0.3.1**: Dot notation for hierarchical access
- **0.3.0**: `entries()` method, hierarchical structures
- **0.2.x**: Prefix-based auto-naming
- **0.1.x**: Initial release with basic named dispatch
