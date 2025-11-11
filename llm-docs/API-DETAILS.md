# SmartSwitch - Complete API Reference

## Switcher Class

### Constructor
```python
Switcher(
    name: str = "default",
    description: str | None = None,
    prefix: str | None = None,
    parent: Switcher | None = None
)
```

**Parameters:**
- `name`: Identifier for this Switcher (used in logs, hierarchies)
- `description`: Optional human-readable description
- `prefix`: If set, auto-derive handler names by removing prefix from function names
- `parent`: Parent Switcher for hierarchical APIs

**Example:**
```python
sw = Switcher(name="api", prefix="handle_")
```

### Decorator Methods

#### `@sw` - Register Default Handler
```python
@sw
def handler(args):
    pass
```
Registers as both default and named handler (using function name or prefix-stripped name).

#### `@sw('name')` - Register with Custom Name
```python
@sw('custom_name')
def handler(args):
    pass
```
Registers with specified alias. Also works for lookup if name exists.

#### `@sw(typerule=..., valrule=...)` - Register with Rules
```python
@sw(
    typerule={'param': type},
    valrule=lambda param: condition
)
def handler(param):
    pass
```

**typerule format:**
```python
{
    'param_name': type,           # Single type
    'other': int | str,           # Union type
    'third': list[int]            # Generic type
}
```

**valrule formats:**
```python
# Expanded (recommended for simple cases)
valrule=lambda x, y: x > y

# Compact dict
valrule=lambda kw: kw['x'] > kw['y']

# Compact unpack
valrule=lambda **kw: kw.get('x', 0) > kw.get('y', 0)
```

### Call Methods

#### Get Handler by Name
```python
handler = sw('handler_name')
result = handler(args)
```
Supports dot notation for hierarchical access: `sw('child.handler')`

#### Get Dispatcher (Auto-Dispatch)
```python
dispatcher = sw()
result = dispatcher(args)  # Chooses handler by rules
```

### Hierarchy Management

#### `.add(switcher)` / `.add_child(switcher)`
```python
child = parent.add(Switcher(name="child"))
```
Adds child Switcher and sets bidirectional parent-child relationship. Returns child for chaining.

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

### Introspection

#### `.entries()`
```python
names = sw.entries()        # List of all handler names
```

#### `.name` attribute
```python
sw.name = "new_name"
```

#### `.description` attribute
```python
sw.description = "API for user management"
```

### Logging (v0.4.0)

#### `.enable_log(...)`
```python
sw.enable_log(
    *handler_names: str,           # Empty = all handlers
    mode: str = 'silent',          # 'log', 'silent', 'both'
    before: bool = True,           # Log args
    after: bool = True,            # Log result
    time: bool = True,             # Measure time
    log_file: str | None = None,   # Optional JSONL file
    log_format: str = 'json',      # 'json' or 'jsonl'
    max_history: int = 1000        # History size limit
)
```

**Modes:**
- `'silent'`: History only, no console output (production)
- `'log'`: Console logging only
- `'both'`: Console + history

**Examples:**
```python
# Enable for all handlers
sw.enable_log(mode='silent')

# Enable for specific handlers
sw.enable_log('critical', 'important', mode='both', time=True)

# Disable specific handlers
sw.disable_log('debug_handler')

# Disable all
sw.disable_log()
```

#### `.get_log_history(...)`
```python
sw.get_log_history(
    last: int | None = None,           # Last N entries
    first: int | None = None,          # First N entries
    handler: str | None = None,        # Filter by handler
    slowest: int | None = None,        # N slowest calls
    fastest: int | None = None,        # N fastest calls
    errors: bool | None = None,        # True=errors, False=successes
    slower_than: float | None = None   # Threshold in seconds
) -> list[dict]
```

**Returns:** List of log entries with:
```python
{
    'handler': str,
    'switcher': str,
    'timestamp': float,
    'args': tuple,
    'kwargs': dict,
    'result': Any,              # If success
    'exception': {              # If error
        'type': str,
        'message': str
    },
    'elapsed': float            # If time=True
}
```

#### `.get_log_stats()`
```python
stats = sw.get_log_stats()
```

**Returns:** Dict mapping handler names to stats:
```python
{
    'handler_name': {
        'calls': int,
        'errors': int,
        'avg_time': float,
        'min_time': float,
        'max_time': float,
        'total_time': float
    }
}
```

#### `.clear_log_history()`
```python
sw.clear_log_history()
```

#### `.export_log_history(filepath)`
```python
sw.export_log_history('history.json')
```

## BoundSwitcher Class

Automatically created when accessing Switcher as class attribute. Binds `self` to handlers.

```python
class Service:
    ops = Switcher()
    
    @ops
    def process(self, data):
        return f"{self.name}: {data}"

svc = Service()
svc.ops('process')(data)  # 'self' bound automatically
```

**Methods:** Same as Switcher, with automatic `self` binding.

## Type System

### Supported Types
- Built-in types: `int`, `str`, `float`, `bool`, `list`, `dict`, `tuple`, `set`
- Custom classes: `MyClass`
- Union types: `int | str` (Python 3.10+)
- Generic types: `list[int]`, `dict[str, int]`
- Any: `Any` (matches anything)

### Type Checking
```python
from typing import Any

@sw(typerule={
    'count': int,
    'name': str,
    'data': list[int] | dict,
    'any_value': Any
})
def handler(count, name, data, any_value):
    pass
```

## Rule Evaluation Order

1. **Specific rules** (with typerule/valrule) - in registration order
2. **Default handler** (plain `@sw`)

First matching rule wins.

```python
sw = Switcher()

@sw(valrule=lambda x: x > 100)  # Most specific - checked first
def handle_large(x):
    return "large"

@sw(valrule=lambda x: x > 10)   # Less specific - checked second
def handle_medium(x):
    return "medium"

@sw  # Default - checked last
def handle_small(x):
    return "small"

sw()(x=150)  # → handle_large
sw()(x=50)   # → handle_medium
sw()(x=5)    # → handle_small
```

## Method Binding (Descriptor Protocol)

Switcher implements `__get__` for automatic method binding:

```python
class API:
    handlers = Switcher()
    
    @handlers
    def save(self, data):
        return f"{self.name} saved {data}"
    
    def __init__(self, name):
        self.name = name

api = API("DB")
api.handlers('save')("data")  # 'self' bound, no need to pass api
```

## Thread Safety

### Safe Operations (Read-Only)
- Handler dispatch: `sw('name')(args)`
- Rule evaluation: `sw()(args)`
- Introspection: `sw.entries()`, `sw.children`
- History queries: `sw.get_log_history()`

### Unsafe Operations (Require External Locking)
- Decorator registration: `@sw` (should be at module level)
- Hierarchy modification: `sw.add()`, `sw.remove_child()`
- Runtime handler addition (not recommended)

**Best Practice:** Register handlers at module import (single-threaded), dispatch at runtime (thread-safe).

## Performance Characteristics

- **Dispatch overhead**: ~2μs per call
- **Type checking**: Cached after first use
- **Rule evaluation**: O(n) where n = number of rules
- **Default handler**: O(1) (no rule evaluation)
- **Logging overhead**:
  - Silent mode: ~0.5μs
  - Log mode: ~50μs (I/O bound)

## Common Patterns

### API Router
```python
api = Switcher()

@api(valrule=lambda method, path: method == 'GET' and path == '/users')
def list_users(method, path):
    pass
```

### State Machine
```python
fsm = Switcher()

@fsm(valrule=lambda state: state == 'idle')
def start(state):
    return 'running'
```

### Plugin System
```python
plugins = Switcher(prefix='plugin_')

@plugins  # Auto-registers as 'image'
def plugin_image(data):
    pass
```

### Hierarchical API
```python
root = Switcher(name="api")
users = root.add(Switcher(name="users"))
products = root.add(Switcher(name="products"))

@users
def list(): pass

root('users.list')()  # Dot notation access
```

## Error Handling

### ValueError
Raised when no rule matches and no default handler:
```python
try:
    sw()(unmatched_args)
except ValueError as e:
    print(f"No handler found: {e}")
```

### KeyError
Raised when handler name not found:
```python
try:
    sw('nonexistent')
except KeyError as e:
    print(f"Handler not found: {e}")
```

### TypeError
Raised on invalid decorator usage:
```python
try:
    sw(invalid_argument)
except TypeError as e:
    print(f"Invalid usage: {e}")
```

## Debugging Tips

1. **List handlers**: `print(sw.entries())`
2. **Check hierarchy**: `print([c.name for c in sw.children])`
3. **Enable logging**: `sw.enable_log(mode='log')`
4. **Check stats**: `print(sw.get_log_stats())`
5. **Find errors**: `errors = sw.get_log_history(errors=True)`
6. **Introspect handler**: `print(sw('name').__wrapped__)`

## Version History

- **0.4.0**: Added logging, history tracking, performance analysis
- **0.3.1**: Added dot notation for hierarchical access
- **0.3.0**: Added `entries()` method, hierarchical structures
- **0.2.x**: Added prefix-based auto-naming
- **0.1.x**: Initial release with basic dispatch
