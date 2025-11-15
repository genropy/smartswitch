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

## BasePlugin Class (v0.5.0+)

Base class for creating custom plugins that extend Switcher functionality.

### Methods to Override

#### `on_decorate(func, name, switcher, metadata)`

Called when a handler is decorated, **before** wrapping. Use for initialization, validation, or storing metadata.

**Parameters:**
- `func`: The original function being decorated
- `name`: The registered name for this handler
- `switcher`: The Switcher instance
- `metadata`: Dict for storing plugin-specific data (accessible as `func._plugin_meta`)

**Example:**
```python
class MetadataPlugin(BasePlugin):
    def on_decorate(self, func, name, switcher, metadata):
        metadata['registered_at'] = time.time()
        metadata['version'] = '1.0'
```

#### `wrap_handler(func, name, switcher)`

Called to wrap the handler function. Return a wrapper function that calls the original.

**Parameters:**
- `func`: The original function
- `name`: The registered name
- `switcher`: The Switcher instance

**Returns:** Wrapped function

**Example:**
```python
class LoggingPlugin(BasePlugin):
    def wrap_handler(self, func, name, switcher):
        def wrapper(*args, **kwargs):
            print(f"Calling {name}")
            result = func(*args, **kwargs)
            print(f"Done: {name}")
            return result
        return wrapper
```

### Complete Plugin Example

```python
from smartswitch import Switcher, BasePlugin
import time

class TimingPlugin(BasePlugin):
    def on_decorate(self, func, name, switcher, metadata):
        # Store registration time
        metadata['registered_at'] = time.time()

    def wrap_handler(self, func, name, switcher):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            print(f"{name} took {elapsed:.4f}s")
            return result
        return wrapper

sw = Switcher(plugins=[TimingPlugin()])

@sw
def slow_operation():
    time.sleep(0.1)
    return "done"

sw('slow_operation')()  # Prints timing
```

## Built-in Plugins

### PydanticPlugin (v0.5.0+)

Validates handler arguments using type hints and Pydantic models.

**Installation:**
```bash
pip install smartswitch[pydantic]
```

**Usage:**
```python
from smartswitch import Switcher
from smartswitch.plugins import PydanticPlugin

sw = Switcher(plugins=[PydanticPlugin()])

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

### Plugin System
```python
plugins = Switcher(prefix='plugin_')

@plugins
def plugin_markdown(content):
    return markdown.render(content)

@plugins
def plugin_syntax(content):
    return highlight(content)

plugins('markdown')(content)
plugins('syntax')(code)
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

- **0.9.2**: Documentation updates, removed obsolete features
- **0.6.0**: Added plugin lifecycle hooks (`on_decorate()`), metadata sharing (`func._plugin_meta`)
- **0.5.0**: Added plugin system with `BasePlugin`, global registry, `PydanticPlugin`
- **0.4.0**: Refactored core, improved type hints
- **0.3.1**: Added dot notation for hierarchical access
- **0.3.0**: Added `entries()` method, hierarchical structures
- **0.2.x**: Added prefix-based auto-naming
- **0.1.x**: Initial release with basic named dispatch

## Migration Notes

### From 0.8.x to 0.9.x

**Removed features:**
- `typerule` parameter (type-based dispatch)
- `valrule` parameter (value-based dispatch)
- Automatic rule-based dispatch

**Migration:**
- Use named dispatch only: `sw('handler_name')(args)`
- For validation, use `PydanticPlugin`
- For conditional logic, implement inside handlers or use separate functions

**Example:**
```python
# Old (0.8.x) - NO LONGER WORKS
@sw(typerule={'data': str})
def process_string(data):
    return data.upper()

@sw(typerule={'data': int})
def process_number(data):
    return data * 2

# New (0.9.x) - Use named dispatch
@sw('process_string')
def process_string(data: str):
    return data.upper()

@sw('process_number')
def process_number(data: int):
    return data * 2

# Call explicitly by name
sw('process_string')("hello")
sw('process_number')(42)
```
