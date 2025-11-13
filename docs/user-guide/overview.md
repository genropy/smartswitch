# What is SmartSwitch?

**SmartSwitch** is a Python library for intelligent rule-based function dispatch. It helps you write cleaner, more maintainable code by separating business logic from control flow.

## The Problem

Traditional approaches to conditional logic often result in:
- **Long if-elif chains** that are hard to read and maintain
- **Duplicate code** across similar conditions
- **Tight coupling** between dispatch logic and business logic
- **Poor testability** due to monolithic functions

```python
# Traditional approach - hard to maintain
def handle_request(action, user_type, data):
    if action == "delete" and user_type == "admin":
        # Delete logic here
        pass
    elif action == "delete" and user_type == "user":
        # Different delete logic
        pass
    elif action == "update":
        if user_type == "admin":
            # Admin update
            pass
        else:
            # User update
            pass
    # ... more conditions ...
```

## The Solution

SmartSwitch provides three powerful dispatch mechanisms:

### 1. Named Registry
Call functions by name or custom alias - perfect for command patterns, plugin systems, and API routing.

```python
from smartswitch import Switcher

api = Switcher()

@api
def get_users():
    return ["Alice", "Bob"]

@api
def get_posts():
    return ["Post 1", "Post 2"]

# Direct invocation by name
result = api("get_users")()
```

### 2. Value-Based Dispatch
Route calls based on runtime argument values - ideal for business rules and state machines.

```python
processor = Switcher()

@processor(valrule=lambda user_type: user_type == "admin")
def admin_action(user_type, data):
    return "Admin handling"

@processor(valrule=lambda user_type: user_type == "user")
def user_action(user_type, data):
    return "User handling"

# Automatically selects right handler
result = processor()(user_type="admin", data="test")
```

### 3. Type-Based Dispatch
Route calls based on argument types - eliminates isinstance chains.

```python
formatter = Switcher()

@formatter(typerule={'data': str})
def format_string(data):
    return data.upper()

@formatter(typerule={'data': int})
def format_number(data):
    return f"Number: {data}"

# Dispatches based on type
result = formatter()(data="hello")  # → "HELLO"
result = formatter()(data=42)       # → "Number: 42"
```

## When to Use SmartSwitch

SmartSwitch excels at:

- **API routing** - Map endpoints to handlers
- **Command processing** - Parse and execute user commands
- **Event handling** - Dispatch events to appropriate handlers
- **Business rules** - Complex conditional logic based on multiple factors
- **Plugin systems** - Register and invoke plugins by name
- **State machines** - Route based on current state and input

## When NOT to Use SmartSwitch

SmartSwitch might be overkill for:

- **Simple conditionals** - Basic if/else with 2-3 branches
- **Ultra-performance-critical code** - Sub-microsecond dispatch overhead exists
- **Single-dispatch scenarios** - Python's `singledispatch` might be simpler

## Service-Ready Architecture

SmartSwitch is part of the **Genro-Libs toolkit** and integrates seamlessly with **SmartPublisher** for exposing handlers as microservices.

### The Pattern: Organize → Expose

```python
from smartswitch import Switcher
from smartpublisher import publish

# 1. ORGANIZE: Define business logic with SmartSwitch
api = Switcher()

@api
def get_users():
    """Retrieve all users."""
    return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

@api
def create_user(name: str, email: str):
    """Create a new user."""
    # Business logic here
    return {"id": 3, "name": name, "email": email}

@api
def delete_user(user_id: int):
    """Delete a user by ID."""
    # Business logic here
    return {"deleted": user_id}

# 2. EXPOSE: Publish as REST/gRPC service with SmartPublisher
publish(api, protocol="rest", port=8000)
```

**Benefits**:
- ✅ **Separation of concerns** - Business logic separate from transport layer
- ✅ **Protocol-agnostic** - Same handlers work for REST, gRPC, CLI, or local calls
- ✅ **Testable** - Test business logic without HTTP/network overhead
- ✅ **Service-ready** - Handlers are immediately publishable as microservices

This architecture lets you:
1. Write clean handler logic once
2. Test it locally without servers
3. Expose it as any protocol (REST/gRPC/WebSocket/CLI)
4. Switch protocols without changing business logic

Learn more about SmartPublisher at [genropy/smartpublisher](https://github.com/genropy/smartpublisher).

## Key Features

✅ **Zero dependencies** - Pure Python 3.10+ standard library
✅ **Type safe** - Full type hints support
✅ **High performance** - Optimized with caching and pre-compiled checks
✅ **Extensible** - Plugin system for custom behavior
✅ **Well tested** - 90%+ code coverage

## Next Steps

Ready to try SmartSwitch? Continue to:

- **[Installation](installation.md)** - Install SmartSwitch
- **[Quick Start](quickstart.md)** - Get up and running in 5 minutes
- **[Basic Usage](basic.md)** - Learn the fundamentals
