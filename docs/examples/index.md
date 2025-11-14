# Examples

Real-world examples of using SmartSwitch in various scenarios.

## Command-Line Tool

Build a CLI tool with subcommands:

```python
from smartswitch import Switcher
import sys

cli = Switcher(name="mycli", prefix="cmd_")

@cli
def cmd_init(project_name: str):
    """Initialize a new project."""
    print(f"Initializing project: {project_name}")
    return {"project": project_name, "status": "created"}

@cli
def cmd_build(target: str = "production"):
    """Build the project."""
    print(f"Building for {target}...")
    return {"target": target, "status": "built"}

@cli
def cmd_deploy(environment: str):
    """Deploy to specified environment."""
    print(f"Deploying to {environment}...")
    return {"environment": environment, "status": "deployed"}

@cli
def cmd_help():
    """Show available commands."""
    commands = list(cli._handlers.keys())
    print("Available commands:")
    for cmd in commands:
        print(f"  - {cmd}")
    return commands

# Usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        cli("help")()
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    try:
        handler = cli(command)
        result = handler(*args)
        print(f"✓ Success: {result}")
    except KeyError:
        print(f"✗ Unknown command: {command}")
        cli("help")()
        sys.exit(1)
```

Run it:
```bash
$ python mycli.py init myproject
Initializing project: myproject
✓ Success: {'project': 'myproject', 'status': 'created'}

$ python mycli.py build staging
Building for staging...
✓ Success: {'target': 'staging', 'status': 'built'}
```

## API Request Router

Route HTTP requests using named handlers:

```python
from smartswitch import Switcher
from smartswitch.plugins import LoggingPlugin

api = Switcher(name="api", prefix="handle_")
api.plug(LoggingPlugin(logger_name="api"))

@api
def handle_get_users():
    """GET /users - List all users."""
    return [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ]

@api
def handle_create_user(name: str, email: str):
    """POST /users - Create new user."""
    user_id = 123  # Generate ID
    return {"id": user_id, "name": name, "email": email}

@api
def handle_get_user(user_id: int):
    """GET /users/:id - Get specific user."""
    # Fetch from database
    return {"id": user_id, "name": "Alice", "email": "alice@example.com"}

@api
def handle_update_user(user_id: int, **updates):
    """PATCH /users/:id - Update user."""
    return {"id": user_id, **updates, "updated": True}

@api
def handle_delete_user(user_id: int):
    """DELETE /users/:id - Delete user."""
    return {"id": user_id, "deleted": True}

# Map routes to handlers
ROUTES = {
    ("GET", "/users"): "get_users",
    ("POST", "/users"): "create_user",
    ("GET", "/users/:id"): "get_user",
    ("PATCH", "/users/:id"): "update_user",
    ("DELETE", "/users/:id"): "delete_user",
}

def route_request(method: str, path: str, data: dict = None):
    """Route HTTP request to appropriate handler."""
    handler_name = ROUTES.get((method, path))
    if not handler_name:
        return {"error": "Not found"}, 404

    handler = api(handler_name)
    result = handler(**data) if data else handler()
    return result, 200

# Usage
result, status = route_request("GET", "/users")
print(result)  # [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

result, status = route_request("POST", "/users", {"name": "Charlie", "email": "charlie@example.com"})
print(result)  # {"id": 123, "name": "Charlie", "email": "charlie@example.com"}
```

## Plugin System Integration

Create a modular application using plugins:

```python
from smartswitch import Switcher
from smartswitch.plugins import LoggingPlugin

class Application:
    def __init__(self):
        self.handlers = Switcher(name="app")
        self.handlers.plug(LoggingPlugin(logger_name="app"))
        self._setup_handlers()

    def _setup_handlers(self):
        """Register core handlers."""
        @self.handlers
        def startup():
            print("Application starting...")
            return {"status": "started"}

        @self.handlers
        def shutdown():
            print("Application shutting down...")
            return {"status": "stopped"}

        @self.handlers
        def health_check():
            return {"status": "healthy", "uptime": 100}

    def register_plugin(self, plugin_name: str, handler_func):
        """Allow plugins to register handlers."""
        self.handlers._handlers[plugin_name] = handler_func

    def execute(self, command: str, **kwargs):
        """Execute a command."""
        if command not in self.handlers._handlers:
            return {"error": f"Unknown command: {command}"}
        return self.handlers(command)(**kwargs)

# Create application
app = Application()

# Register plugin handlers dynamically
def email_plugin():
    """Plugin: Send emails."""
    return {"plugin": "email", "status": "email sent"}

def sms_plugin():
    """Plugin: Send SMS."""
    return {"plugin": "sms", "status": "sms sent"}

app.register_plugin("send_email", email_plugin)
app.register_plugin("send_sms", sms_plugin)

# Use application
print(app.execute("startup"))       # Logs + returns {"status": "started"}
print(app.execute("health_check"))  # {"status": "healthy", "uptime": 100}
print(app.execute("send_email"))    # {"plugin": "email", "status": "email sent"}
print(app.execute("shutdown"))      # Logs + returns {"status": "stopped"}
```

## Database Operations

Use DbOpPlugin for automatic cursor injection:

```python
from smartswitch import Switcher
from smartswitch.plugins import DbOpPlugin
import sqlite3

class UserRepository:
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self.api = Switcher()
        self.api.plug(DbOpPlugin())

    @property
    def create_user(self):
        @self.api
        def _create(self, name: str, email: str, cursor=None, autocommit=True):
            """Create new user."""
            cursor.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                (name, email)
            )
            return {"id": cursor.lastrowid, "name": name, "email": email}
        return _create

    @property
    def find_user(self):
        @self.api
        def _find(self, user_id: int, cursor=None):
            """Find user by ID."""
            cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "name": row[1], "email": row[2]}
            return None
        return _find

    @property
    def delete_user(self):
        @self.api
        def _delete(self, user_id: int, cursor=None, autocommit=True):
            """Delete user by ID."""
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return {"deleted": user_id, "rows": cursor.rowcount}
        return _delete

# Setup database
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
conn.commit()

# Use repository
repo = UserRepository(":memory:")
repo.db = conn  # Share connection

# Plugin handles cursor and transaction automatically
user = repo.create_user(repo, name="Alice", email="alice@example.com")
print(user)  # {"id": 1, "name": "Alice", "email": "alice@example.com"}

found = repo.find_user(repo, user_id=1)
print(found)  # {"id": 1, "name": "Alice", "email": "alice@example.com"}

deleted = repo.delete_user(repo, user_id=1)
print(deleted)  # {"deleted": 1, "rows": 1}
```

## Event Handler System

Build an event-driven system:

```python
from smartswitch import Switcher
from smartswitch.plugins import LoggingPlugin
from typing import Any
import json

class EventBus:
    def __init__(self):
        self.handlers = Switcher(name="events", prefix="on_")
        self.handlers.plug(LoggingPlugin(logger_name="events"))

    def on(self, event_name: str):
        """Decorator to register event handlers."""
        def decorator(func):
            # Register with 'on_' prefix
            self.handlers._handlers[f"on_{event_name}"] = func
            return func
        return decorator

    def emit(self, event_name: str, data: Any = None):
        """Emit an event to all registered handlers."""
        handler_name = f"on_{event_name}"
        if handler_name in self.handlers._handlers:
            handler = self.handlers(handler_name)
            return handler(data) if data else handler()
        else:
            print(f"No handler for event: {event_name}")
            return None

# Create event bus
events = EventBus()

# Register event handlers
@events.on("user_registered")
def handle_user_registered(user_data):
    """Handle new user registration."""
    print(f"Welcome email sent to {user_data['email']}")
    return {"email_sent": True}

@events.on("order_placed")
def handle_order_placed(order_data):
    """Handle new order."""
    print(f"Processing order {order_data['order_id']}")
    print(f"Total: ${order_data['total']}")
    return {"order_id": order_data["order_id"], "status": "processing"}

@events.on("payment_received")
def handle_payment_received(payment_data):
    """Handle payment confirmation."""
    print(f"Payment received: ${payment_data['amount']}")
    return {"payment_id": payment_data["transaction_id"], "confirmed": True}

# Emit events
events.emit("user_registered", {
    "user_id": 123,
    "name": "Alice",
    "email": "alice@example.com"
})
# Output: Welcome email sent to alice@example.com

events.emit("order_placed", {
    "order_id": "ORD-456",
    "total": 99.99,
    "items": ["item1", "item2"]
})
# Output: Processing order ORD-456
#         Total: $99.99

events.emit("payment_received", {
    "transaction_id": "TXN-789",
    "amount": 99.99
})
# Output: Payment received: $99.99
```

## State Machine

Implement a state machine for order processing:

```python
from smartswitch import Switcher
from enum import Enum

class OrderState(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class OrderStateMachine:
    def __init__(self, order_id: str):
        self.order_id = order_id
        self.state = OrderState.PENDING
        self.actions = Switcher(name="order_actions", prefix="action_")
        self._setup_actions()

    def _setup_actions(self):
        """Setup state transition actions."""
        @self.actions
        def action_confirm():
            if self.state == OrderState.PENDING:
                self.state = OrderState.CONFIRMED
                return {"order_id": self.order_id, "state": self.state.value}
            raise ValueError(f"Cannot confirm order in state: {self.state.value}")

        @self.actions
        def action_ship():
            if self.state == OrderState.CONFIRMED:
                self.state = OrderState.SHIPPED
                return {"order_id": self.order_id, "state": self.state.value}
            raise ValueError(f"Cannot ship order in state: {self.state.value}")

        @self.actions
        def action_deliver():
            if self.state == OrderState.SHIPPED:
                self.state = OrderState.DELIVERED
                return {"order_id": self.order_id, "state": self.state.value}
            raise ValueError(f"Cannot deliver order in state: {self.state.value}")

        @self.actions
        def action_cancel():
            if self.state in (OrderState.PENDING, OrderState.CONFIRMED):
                self.state = OrderState.CANCELLED
                return {"order_id": self.order_id, "state": self.state.value}
            raise ValueError(f"Cannot cancel order in state: {self.state.value}")

    def transition(self, action: str):
        """Execute state transition."""
        try:
            handler = self.actions(action)
            return handler()
        except KeyError:
            raise ValueError(f"Unknown action: {action}")

# Use state machine
order = OrderStateMachine("ORD-123")

print(order.state)  # OrderState.PENDING

result = order.transition("confirm")
print(result)  # {'order_id': 'ORD-123', 'state': 'confirmed'}

result = order.transition("ship")
print(result)  # {'order_id': 'ORD-123', 'state': 'shipped'}

result = order.transition("deliver")
print(result)  # {'order_id': 'ORD-123', 'state': 'delivered'}

# Invalid transitions raise errors
try:
    order.transition("cancel")  # Can't cancel after delivery
except ValueError as e:
    print(f"Error: {e}")  # Error: Cannot cancel order in state: delivered
```

## Next Steps

- Explore the [Plugin System](../plugins/index.md) for advanced customization
- See [Best Practices](../guide/best-practices.md) for production patterns
- Check the [API Reference](../api/switcher.md) for detailed documentation
