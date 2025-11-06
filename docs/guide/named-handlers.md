# Named Handlers Guide

> **Test Source**: Examples in this guide are from [test_complete.py](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py)

Named handlers allow you to retrieve and invoke specific handlers by name, without relying on automatic rule-based dispatch. This is useful for explicit invocation, method routing, and plugin systems.

<!-- test: test_complete.py::test_get_handler_by_name -->

## Basic Named Handler Access

Every handler registered with a Switcher is accessible by its function name:

**From test**: [test_get_handler_by_name](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L377-L386)

```python
from smartswitch import Switcher

sw = Switcher()

@sw(typerule={'x': int})
def compute(x):
    return x * 2

# Retrieve handler by name
handler = sw('compute')
assert handler(x=5) == 10
```

**Key Points:**
- Handlers are registered by their function name automatically
- Use `sw('name')` to retrieve a handler
- The returned handler is a normal Python function

<!-- test: test_complete.py::test_get_handler_by_name_one_liner -->

## One-Liner Invocation

For quick invocations, you can retrieve and call in one line:

**From test**: [test_get_handler_by_name_one_liner](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L388-L396)

```python
sw = Switcher()

@sw(typerule={'x': int})
def compute(x):
    return x * 2

# One-liner: retrieve + invoke
assert sw('compute')(x=5) == 10
```

This is especially useful in routing scenarios where the handler name comes from external input.

<!-- test: test_complete.py::test_register_with_alias -->

## Custom Aliases

You can register handlers with custom names different from their function name:

**From test**: [test_register_with_alias](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L422-L431)

```python
sw = Switcher()

@sw('reset')
def destroyall():
    return "destroyed"

# Access by alias, not function name
assert sw('reset')() == "destroyed"
```

**Use Cases:**
- User-facing command names
- API endpoint mapping
- Backward compatibility aliases

## Explicit vs Automatic Dispatch

SmartSwitch supports two dispatch modes:

### 1. Automatic Dispatch (Rule-Based)

```python
sw = Switcher()

@sw(typerule={'x': int})
def handle_int(x):
    return "int"

@sw(typerule={'x': str})
def handle_str(x):
    return "str"

# Automatic: rules determine the handler
print(sw()(x=42))    # → "int"
print(sw()(x="hi"))  # → "str"
```

### 2. Explicit Dispatch (Named)

```python
sw = Switcher()

@sw
def process_payment(amount):
    return f"Processing ${amount}"

@sw
def refund_payment(amount):
    return f"Refunding ${amount}"

# Explicit: you choose the handler
action = 'process_payment'  # From user input, config, etc.
result = sw(action)(amount=100)
print(result)  # → "Processing $100"
```

**When to Use Each:**
- **Automatic**: When dispatch logic is complex or based on types/values
- **Explicit**: When handler selection comes from external sources (user input, config, database)

<!-- test: test_complete.py::test_prefix_basic_stripping -->

## Prefix-Based Auto-Naming

When handlers follow a naming convention, you can use prefix-based auto-naming to simplify handler retrieval:

**From test**: [test_prefix_basic_stripping](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L766-L784)

```python
sw = Switcher(prefix='handle_')

@sw
def handle_foo(x):
    return f"foo: {x}"

@sw
def handle_bar(x):
    return f"bar: {x}"

# Handlers registered with stripped names
assert 'foo' in sw._handlers
assert 'bar' in sw._handlers

# Access by shortened names (prefix stripped)
assert sw('foo')(x=5) == "foo: 5"
assert sw('bar')(x=10) == "bar: 10"
```

**How It Works:**
- The `prefix` parameter is specified when creating the Switcher
- Functions whose names start with the prefix are registered with shortened names
- The prefix is stripped from the handler name
- Functions not matching the prefix keep their full name

### Real-World Example: Protocol Handlers

```python
protocol = Switcher(prefix='protocol_')

@protocol
def protocol_s3_aws(bucket, key):
    return f"S3: s3://{bucket}/{key}"

@protocol
def protocol_gcs(bucket, key):
    return f"GCS: gs://{bucket}/{key}"

@protocol
def protocol_local(path):
    return f"Local: {path}"

# Access by shortened protocol names
print(protocol('s3_aws')(bucket='data', key='file.csv'))
# → "S3: s3://data/file.csv"

print(protocol('gcs')(bucket='data', key='file.csv'))
# → "GCS: gs://data/file.csv"

print(protocol('local')(path='/tmp/file.csv'))
# → "Local: /tmp/file.csv"
```

**Use Cases:**
- Plugin systems (`plugin_*`)
- Command handlers (`cmd_*`)
- Protocol dispatchers (`protocol_*`)
- HTTP handlers (`handle_*`)

<!-- test: test_complete.py::test_prefix_with_description -->

### Prefix with Description

Combine prefix with description for self-documenting code:

**From test**: [test_prefix_with_description](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L837-L857)

```python
sw = Switcher(
    name='protocol',
    description='Storage protocol dispatcher',
    prefix='protocol_'
)

@sw
def protocol_s3_aws(x):
    return "s3_aws"

@sw
def protocol_gcs(x):
    return "gcs"

assert sw.description == 'Storage protocol dispatcher'
assert 's3_aws' in sw._handlers
assert 'gcs' in sw._handlers
assert sw('s3_aws')(x=1) == "s3_aws"
assert sw('gcs')(x=1) == "gcs"
```

<!-- test: test_complete.py::test_prefix_no_match_uses_full_name -->

### When Prefix Doesn't Match

Functions not matching the prefix keep their full name:

**From test**: [test_prefix_no_match_uses_full_name](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L786-L796)

```python
sw = Switcher(prefix='handle_')

@sw
def other_name(x):
    return f"other: {x}"

# Registered with full name (no prefix match)
assert 'other_name' in sw._handlers
assert sw('other_name')(x=5) == "other: 5"
```

**Best Practice:** Be consistent with your naming convention to avoid confusion.

<!-- test: test_complete.py::test_prefix_explicit_name_override -->

### Explicit Names Override Prefix

You can always override the prefix with an explicit alias:

**From test**: [test_prefix_explicit_name_override](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L798-L809)

```python
sw = Switcher(prefix='handle_')

@sw('custom_name')
def handle_foo(x):
    return x

# Registered as 'custom_name', not 'foo'
assert 'custom_name' in sw._handlers
assert 'foo' not in sw._handlers
assert sw('custom_name')(x=5) == 5
```

<!-- test: test_complete.py::test_prefix_with_typerule -->

### Prefix with Type Rules

Prefix stripping works seamlessly with type rules:

**From test**: [test_prefix_with_typerule](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L859-L877)

```python
sw = Switcher(prefix='cmd_')

@sw(typerule={'x': int})
def cmd_add(x):
    return f"add: {x}"

@sw(typerule={'x': str})
def cmd_delete(x):
    return f"delete: {x}"

# Named registration works with rules
assert 'cmd_add' in sw._handlers
assert 'cmd_delete' in sw._handlers

# Can access by name
assert sw('cmd_add')(x=5) == "add: 5"
assert sw('cmd_delete')(x="item") == "delete: item"
```

## Handler Registry

All registered handlers live in the `_handlers` dictionary:

```python
sw = Switcher()

@sw
def foo(x):
    return x

@sw
def bar(x):
    return x * 2

# Check what's registered
print('foo' in sw._handlers)  # → True
print('bar' in sw._handlers)  # → True
print(len(sw._handlers))      # → 2
```

**Use Cases:**
- Introspection
- Dynamic handler discovery
- Plugin listing

## Duplicate Name Detection

SmartSwitch prevents duplicate handler names:

```python
sw = Switcher()

@sw
def my_function():
    return "first"

# This will raise ValueError
@sw
def my_function():
    return "second"
```

**Error Message:** `ValueError: Handler 'my_function' already taken by function 'my_function'`

### Duplicate Alias Detection

```python
sw = Switcher()

@sw('action')
def first():
    return "first"

# This will raise ValueError
@sw('action')
def second():
    return "second"
```

**Error Message:** `ValueError: Alias 'action' is already registered`

**Best Practice:** Use unique names or aliases for all handlers.

## Handler Not Found

When you request a handler that doesn't exist, SmartSwitch returns a **decorator** (for potential future registration):

```python
sw = Switcher()

@sw
def existing(x):
    return x

# 'nonexistent' is not registered
result = sw('nonexistent')
# Returns a decorator (not an error)

# You can use it to register a handler with that name
@result
def new_handler(x):
    return "new"

# Now it's available
print(sw('nonexistent')(x=1))  # → "new"
```

**This allows dynamic registration**, which can be useful for plugin systems or lazy loading.

## Common Patterns

### Command Dispatcher

```python
commands = Switcher(prefix='cmd_')

@commands
def cmd_start(service):
    return f"Starting {service}"

@commands
def cmd_stop(service):
    return f"Stopping {service}"

@commands
def cmd_restart(service):
    return f"Restarting {service}"

# From user input
user_command = 'start'  # e.g., from CLI argument
service_name = 'nginx'

result = commands(user_command)(service=service_name)
print(result)  # → "Starting nginx"
```

### Plugin Registry

```python
plugins = Switcher(
    name='plugins',
    description='Available plugins',
    prefix='plugin_'
)

@plugins
def plugin_logger(event):
    print(f"LOG: {event}")

@plugins
def plugin_metrics(event):
    print(f"METRIC: {event}")

@plugins
def plugin_alerts(event):
    print(f"ALERT: {event}")

# Dynamically invoke all plugins
enabled_plugins = ['logger', 'metrics']

for plugin_name in enabled_plugins:
    plugins(plugin_name)(event="User logged in")
# Output:
# LOG: User logged in
# METRIC: User logged in
```

### Method Routing

```python
class APIHandler:
    routes = Switcher(prefix='handle_')

    @routes
    def handle_get_users(self):
        return "List of users"

    @routes
    def handle_post_users(self):
        return "Create user"

    def dispatch(self, method, path):
        # Build handler name from HTTP method + path
        handler_name = f"{method.lower()}_{path.strip('/').replace('/', '_')}"
        return self.routes(handler_name)()

api = APIHandler()
print(api.dispatch('GET', '/users'))   # → "List of users"
print(api.dispatch('POST', '/users'))  # → "Create user"
```

### Configuration-Based Dispatch

```python
import os

storage = Switcher(prefix='backend_')

@storage
def backend_s3(data):
    return f"S3: {data}"

@storage
def backend_local(data):
    return f"Local: {data}"

@storage
def backend_gcs(data):
    return f"GCS: {data}"

# From environment variable
backend_type = os.getenv('STORAGE_BACKEND', 'local')

# Dispatch based on config
handler = storage(backend_type)
result = handler(data="test.csv")
print(result)
```

## Combining Named and Automatic Dispatch

You can use both modes together:

```python
sw = Switcher()

# Named handlers
@sw
def explicit_action(x):
    return f"Explicit: {x}"

# Rule-based handlers
@sw(typerule={'x': int})
def handle_int(x):
    return f"Int: {x}"

@sw(typerule={'x': str})
def handle_str(x):
    return f"Str: {x}"

# Explicit by name
print(sw('explicit_action')(x=10))  # → "Explicit: 10"

# Automatic by rules
print(sw()(x=10))   # → "Int: 10"
print(sw()(x="hi")) # → "Str: hi"
```

**Use Case:** Some handlers are invoked explicitly (admin commands), while others are dispatched automatically (request routing).

## Descriptor Protocol for Class Usage

When using Switcher as a class attribute, it automatically binds `self` to handlers:

```python
sw = Switcher()

@sw
def method(self, x):
    return f"{self.name}: {x}"

class MyClass:
    dispatch = sw

    def __init__(self, name):
        self.name = name

obj = MyClass("test")

# Get bound switcher from instance
bound = obj.dispatch

# Handlers automatically receive 'self'
result = bound('method')(x=5)
print(result)  # → "test: 5"
```

**How It Works:**
- Accessing `obj.dispatch` returns a `BoundSwitcher`
- `BoundSwitcher` automatically binds `self` to retrieved handlers
- No need to pass `self` manually

**Use Cases:**
- Method dispatch in classes
- State machines with instance state
- Plugin systems in object-oriented code

## Performance Characteristics

Named handler access is extremely fast:
- Dictionary lookup: O(1)
- No rule evaluation
- No type checking

**Overhead:** ~50-100 nanoseconds (dictionary lookup)

This makes named handlers ideal for:
- ✅ High-frequency dispatch (millions of calls)
- ✅ Performance-critical paths
- ✅ Simple routing where rules are overkill

## Best Practices

1. **Use descriptive names**: Handler names should be clear and self-documenting
2. **Prefix conventions**: Use consistent prefixes for related handlers
3. **Documentation**: Document available handler names for users
4. **Error handling**: Handle missing handlers gracefully
5. **Testing**: Test handler registration and retrieval

```python
# Good: clear names with prefix
api = Switcher(prefix='handle_')

@api
def handle_get_users(): ...

@api
def handle_create_user(): ...

# Also good: explicit aliases
api = Switcher()

@api('GET /users')
def list_users(): ...

@api('POST /users')
def create_user(): ...
```

## Next Steps

- Learn about [Type Rules](typerules.md) for type-based dispatch
- Explore [Value Rules](valrules.md) for condition-based dispatch
- See [Best Practices](best-practices.md) for production usage patterns
- Check [Real-World Examples](../examples/index.md) for practical use cases
