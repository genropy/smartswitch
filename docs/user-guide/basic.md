# Basic Usage

This guide covers the fundamental concepts and patterns for using SmartSwitch effectively.

## Creating a Switcher

```python
from smartswitch import Switcher

sw = Switcher()
```

You can also give your switcher a name and description for better organization:

```python
sw = Switcher(
    name="api_handlers",
    description="HTTP API request handlers"
)
```

## Registering Handlers

### Simple Registration

The most basic way to register a handler is using the `@sw` decorator:

```python
sw = Switcher()

@sw
def get_users():
    """Fetch all users from database."""
    return ["Alice", "Bob", "Charlie"]

@sw
def get_posts():
    """Fetch all posts from database."""
    return ["Post 1", "Post 2", "Post 3"]

@sw
def create_user(name: str, email: str):
    """Create a new user."""
    return {"name": name, "email": email, "id": 123}
```

Each function is automatically registered by its function name.

### Handlers with Arguments

Handlers can accept any number of arguments with type hints:

```python
@sw
def update_user(user_id: int, name: str, email: str):
    """Update user information."""
    return {
        "user_id": user_id,
        "name": name,
        "email": email,
        "updated": True
    }

@sw
def delete_user(user_id: int):
    """Delete a user by ID."""
    return {"deleted": user_id}
```

## Calling Handlers

### By Name

Call handlers by their function name:

```python
# Retrieve and call in one line
users = sw("get_users")()

# Or retrieve first, then call
handler = sw("get_users")
users = handler()

# With arguments
new_user = sw("create_user")(name="Dave", email="dave@example.com")
user_updated = sw("update_user")(user_id=123, name="David", email="david@example.com")
```

### Error Handling

If a handler doesn't exist, SmartSwitch raises a `KeyError`:

```python
try:
    result = sw("nonexistent_handler")()
except KeyError:
    print("Handler not found")
```

You can check if a handler exists before calling:

```python
if "get_users" in sw._handlers:
    users = sw("get_users")()
```

## Custom Aliases

Register handlers with custom names different from the function name:

```python
@sw("reset")
def destroy_all_data():
    """Dangerous operation - use with caution!"""
    return "All data destroyed"

@sw("clear")
def remove_cache():
    """Clear application cache."""
    return "Cache cleared"

# Call by alias
result = sw("reset")()
result = sw("clear")()
```

This is useful for:
- User-facing command names
- API endpoint mapping
- Backward compatibility

## Prefix Conventions

When you have many related handlers, use a consistent prefix:

```python
storage = Switcher(
    name='storage',
    description='Storage backend dispatcher',
    prefix='backend_'
)

@storage
def backend_s3(bucket: str, key: str):
    """Store file in AWS S3."""
    return f"Stored in S3: {bucket}/{key}"

@storage
def backend_gcs(bucket: str, key: str):
    """Store file in Google Cloud Storage."""
    return f"Stored in GCS: {bucket}/{key}"

@storage
def backend_local(path: str):
    """Store file locally."""
    return f"Stored locally: {path}"

# Access by short names (prefix automatically stripped)
result = storage("s3")(bucket="my-bucket", key="file.txt")
result = storage("gcs")(bucket="my-bucket", key="file.txt")
result = storage("local")(path="/tmp/file.txt")
```

## Using Plugins

SmartSwitch supports a powerful plugin system for extending functionality:

### Logging Plugin

Automatically log function entry, exit, and errors:

```python
from smartswitch import Switcher
from smartswitch.plugins import LoggingPlugin

api = Switcher()
api.plug(LoggingPlugin(logger_name="api"))

@api
def process_payment(amount: float, currency: str):
    """Process a payment transaction."""
    # Plugin logs entry, exit, and any errors
    return {"amount": amount, "currency": currency, "status": "completed"}

result = api("process_payment")(amount=100.0, currency="USD")
# Logs: "Calling process_payment with ..."
# Logs: "process_payment returned ..."
```

### Database Plugin

Inject database cursors and manage transactions:

```python
from smartswitch.plugins import DbOpPlugin

class UserService:
    def __init__(self, db):
        self.db = db
        self.api = Switcher()
        self.api.plug(DbOpPlugin())

    @property
    def create_user(self):
        @self.api
        def _create_user(self, name: str, email: str, cursor=None, autocommit=True):
            cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
            return cursor.lastrowid
        return _create_user

# Plugin automatically injects cursor and manages transaction
service = UserService(db)
user_id = service.create_user(service, name="Alice", email="alice@example.com")
```

### Custom Plugins

Create your own plugins by inheriting from `BasePlugin`:

```python
from smartswitch import BasePlugin

class TimingPlugin(BasePlugin):
    """Measure execution time of handlers."""

    def wrap_handler(self, switch, entry, call_next):
        import time

        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = call_next(*args, **kwargs)
                elapsed = time.time() - start
                print(f"{entry.name} took {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start
                print(f"{entry.name} failed after {elapsed:.3f}s")
                raise

        return wrapper

# Use custom plugin
api = Switcher()
api.plug(TimingPlugin())

@api
def slow_operation():
    import time
    time.sleep(1)
    return "done"

result = api("slow_operation")()
# Prints: "slow_operation took 1.001s"
```

## Descriptor Protocol

Switchers can be used as class attributes and work with the descriptor protocol:

```python
class APIServer:
    handlers = Switcher()

    def __init__(self, base_url):
        self.base_url = base_url

@APIServer.handlers
def get_status(self):
    return {"url": self.base_url, "status": "running"}

server = APIServer("https://api.example.com")
status = server.handlers("get_status")(server)
# → {"url": "https://api.example.com", "status": "running"}
```

## Inspecting Handlers

List all registered handlers:

```python
sw = Switcher()

@sw
def handler1(): pass

@sw
def handler2(): pass

@sw("custom")
def handler3(): pass

# Check registered names
print("handler1" in sw._handlers)  # True
print("handler2" in sw._handlers)  # True
print("custom" in sw._handlers)    # True
print("handler3" in sw._handlers)  # False (registered as "custom")

# List all handler names
print(list(sw._handlers.keys()))
# → ["handler1", "handler2", "custom"]
```

## Best Practices

### 1. Use Descriptive Names

Make handler names self-documenting:

```python
# ✅ Good
@sw
def send_password_reset_email(user_id: int):
    ...

# ❌ Bad
@sw
def handler1(id: int):
    ...
```

### 2. Validate Inputs

Always validate inputs in your handlers:

```python
@sw
def transfer_funds(from_account: int, to_account: int, amount: float):
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if from_account == to_account:
        raise ValueError("Cannot transfer to same account")
    # Process transfer...
```

### 3. Document Handlers

Use docstrings to document what each handler does:

```python
@sw
def calculate_shipping(weight: float, distance: float) -> float:
    """
    Calculate shipping cost based on package weight and distance.

    Args:
        weight: Package weight in kilograms
        distance: Shipping distance in kilometers

    Returns:
        Shipping cost in USD

    Raises:
        ValueError: If weight or distance is negative
    """
    if weight < 0 or distance < 0:
        raise ValueError("Weight and distance must be non-negative")
    return weight * 0.5 + distance * 0.1
```

### 4. Group Related Handlers

Organize handlers by domain or feature:

```python
# User management
user_api = Switcher(name="users", prefix="user_")

@user_api
def user_create(name: str, email: str): ...

@user_api
def user_delete(user_id: int): ...

@user_api
def user_update(user_id: int, **fields): ...

# Payment processing
payment_api = Switcher(name="payments", prefix="payment_")

@payment_api
def payment_process(amount: float): ...

@payment_api
def payment_refund(transaction_id: str): ...
```

## Next Steps

- Learn about [Named Handlers](../guide/named-handlers.md) in depth
- Explore the [Plugin System](../plugins/index.md)
- Read [Best Practices](../guide/best-practices.md) for production usage
- Check out [Real-World Examples](../examples/index.md)
