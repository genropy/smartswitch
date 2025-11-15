# Quick Start

This guide will get you up and running with SmartSwitch in minutes.

## Installation

```bash
pip install smartswitch
```

## The Two Core Patterns

SmartSwitch provides two main capabilities. Let's explore them in order.

### Pattern 1: Named Handler Registry

**Your situation**: You have operations and want to call them by name.

#### Basic Registration

Register functions using decorators:

```python
from smartswitch import Switcher

ops = Switcher()

@ops
def save_data(data):
    return f"Saved: {data}"

@ops
def load_data(data):
    return f"Loaded: {data}"

# Call by name
result = ops('save_data')("my_file.txt")
print(result)  # → "Saved: my_file.txt"
```

**Why it's better than manual dictionaries:**
- Functions self-register with decorator
- No manual dictionary maintenance
- Clear, declarative code
- Collision detection built-in

#### Custom Aliases

**Your situation**: Function names are long, but you want short command names.

```python
ops = Switcher()

@ops('reset')
def destroy_all_data():
    return "Everything destroyed"

@ops('clear')
def remove_cache():
    return "Cache cleared"

# Call with friendly alias
result = ops('reset')()
print(result)  # → "Everything destroyed"
```

**Key insight**: Alias is defined right where the function is defined - no separate mapping needed.

#### Prefix-Based Auto-Naming

**Your situation**: You follow naming conventions and want automatic name derivation.

```python
# Set prefix for automatic name stripping
protocols = Switcher(prefix='protocol_')

@protocols  # Auto-registers as 's3_aws'
def protocol_s3_aws():
    return {"type": "s3", "region": "us-east-1"}

@protocols  # Auto-registers as 'gcs'
def protocol_gcs():
    return {"type": "gcs", "bucket": "data"}

# Call by derived name (prefix removed)
result = protocols('s3_aws')()
print(result)  # → {"type": "s3", "region": "us-east-1"}
```

**Why use prefixes:**
- Maintain Python naming conventions (`protocol_*` functions in IDE)
- Get clean handler names automatically (`s3_aws`, not `protocol_s3_aws`)
- Consistent with method name patterns

#### Hierarchical Organization

**Your situation**: You have multiple related registries and want to organize them.

```python
from smartswitch import Switcher

class MyAPI:
    # Main switcher
    main = Switcher(name="main")

    # Child switchers
    users = Switcher(name="users", parent=main, prefix="user_")
    products = Switcher(name="products", parent=main, prefix="product_")

    @users
    def user_list(self):
        return ["alice", "bob"]

    @users
    def user_create(self, name):
        return f"Created user: {name}"

    @products
    def product_list(self):
        return ["laptop", "phone"]

# Direct access to child switchers
api = MyAPI()
api.users('list')()  # → ["alice", "bob"]

# Hierarchical access via parent
api.main('users.list')()  # → ["alice", "bob"]
api.main('users.create')("charlie")  # → "Created user: charlie"

# Discover structure
for child in api.main._children.values():
    print(f"{child.name}: {list(child._methods.keys())}")
# Output:
# users: ['list', 'create']
# products: ['list']
```

**Benefits:**
- Clear namespace organization
- Both direct and hierarchical access
- Easy to discover available handlers
- Parent can route to children with dotted paths

### Pattern 2: Plugin System

**Your situation**: You need cross-cutting functionality (logging, caching, validation) without modifying handlers.

#### Basic Plugin Usage

```python
from smartswitch import Switcher

# Add logging plugin
sw = Switcher().plug('logging', mode='print,after,time')

@sw
def calculate(x, y):
    return x + y

# Use normally - logs automatically
result = sw('calculate')(10, 5)  # → 15
# Output:
# → calculate(10, 5)
# ← calculate() → 15 (0.0001s)
```

**Why plugins:**
- Add functionality without modifying handler code
- Composable - chain multiple plugins
- Each plugin focused on one concern
- Enable/disable at runtime

#### Creating Custom Plugins

```python
from smartswitch import BasePlugin

class ValidationPlugin(BasePlugin):
    """Validate arguments before handler execution."""

    def wrap_handler(self, switch, entry, call_next):
        def wrapper(*args, **kwargs):
            # Custom validation
            if not args and not kwargs:
                raise ValueError("No arguments provided")
            # Call actual handler
            return call_next(*args, **kwargs)
        return wrapper

# Use custom plugin
sw = Switcher().plug(ValidationPlugin())

@sw
def process(data):
    return f"Processed: {data}"

# Plugin validates automatically
result = sw('process')("test")  # → "Processed: test"
sw('process')()  # Raises ValueError: No arguments provided
```

#### Chaining Multiple Plugins

```python
from smartswitch import Switcher

# Chain plugins - they execute in order
sw = (Switcher()
      .plug('logging', mode='print')
      .plug(ValidationPlugin())
      .plug(CachePlugin(ttl=300)))

@sw
def expensive_operation(x):
    # Execution order: logging → validation → cache → handler
    return x * 2

result = sw('expensive_operation')(5)
```

**Execution flow:**
1. Logging plugin records start
2. Validation plugin checks arguments
3. Cache plugin checks for cached result
4. Handler executes (if not cached)
5. Plugins unwind in reverse order

## Real-World Example: API Router

Combining both patterns for a practical application:

```python
from smartswitch import Switcher

# Create API with logging
api = Switcher(name="api").plug('logging', mode='print,after,time')

@api('list_users')
def get_users(page=1):
    # Simulate database query
    return {"users": ["Alice", "Bob", "Charlie"], "page": page}

@api('create_user')
def create_user(name):
    # Simulate user creation
    return {"id": 123, "name": name, "created": True}

@api('delete_user')
def delete_user(user_id):
    return {"id": user_id, "deleted": True}

@api('not_found')
def handle_404():
    return {"error": "Not Found", "status": 404}

# Request handler
def handle_request(endpoint, **kwargs):
    """Route requests to appropriate handlers."""
    handler = api._methods.get(endpoint)
    if handler:
        return api(endpoint)(**kwargs)
    return api('not_found')()

# Use it
response = handle_request('list_users', page=2)
print(response)  # → {"users": [...], "page": 2}

response = handle_request('create_user', name='Dave')
print(response)  # → {"id": 123, "name": "Dave", "created": True}

response = handle_request('unknown_endpoint')
print(response)  # → {"error": "Not Found", "status": 404}

# Analyze performance
print("\nSlowest operations:")
for entry in api.logging.history(slowest=3):
    print(f"{entry['handler']}: {entry['duration']:.4f}s")
```

## Key Concepts Summary

### Named Handler Registry

- **Register by name**: `@sw` uses function name
- **Register with alias**: `@sw('alias')` uses custom name
- **Auto-naming**: `Switcher(prefix='do_')` strips prefix automatically
- **Call by name**: `sw('handler_name')(args)`
- **Hierarchical**: `parent('child.handler')(args)` for organized systems

### Plugin System

- **Add plugins**: `sw.plug('logging')` or `sw.plug(CustomPlugin())`
- **Access plugins**: `sw.logging.method()` or `sw.plugin('logging').method()`
- **Chain plugins**: `sw.plug(A).plug(B).plug(C)`
- **Custom plugins**: Inherit from `BasePlugin`, implement `wrap_handler()`

## Next Steps

Now that you understand the basics:

1. **[Basic Usage Guide](basic.md)** - Deeper dive into patterns and edge cases
2. **[Named Handlers Guide](../guide/named-handlers.md)** - Advanced registry patterns
3. **[Plugin Development](../plugins/development.md)** - Build your own plugins
4. **[Examples](../examples/index.md)** - More real-world examples

## Quick Reference

```python
from smartswitch import Switcher, BasePlugin

# Create switcher
sw = Switcher()
sw = Switcher(name="api", prefix="api_")  # with name and prefix
sw = Switcher(parent=parent_sw)  # with parent

# Add plugins
sw.plug('logging', mode='print,after,time')
sw.plug(CustomPlugin(config="value"))

# Register handlers
@sw
def handler_name(arg): pass

@sw('custom_alias')
def handler_function(arg): pass

# Call handlers
result = sw('handler_name')(arg)
result = sw('custom_alias')(arg)
result = parent_sw('child.handler')(arg)  # hierarchical

# Access plugins
sw.plugin('logging')  # Get plugin instance
sw.logging  # shorthand via attribute

# Introspection
sw._methods  # dict of registered handlers
sw._children  # dict of child switchers
sw.describe()  # full description
```
