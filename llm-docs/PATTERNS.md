# SmartSwitch - Real-World Patterns

## API Method Registry

### Organized Method Collections
```python
class UserAPI:
    operations = Switcher(name="user_ops")

    @operations
    def create(self, username, email):
        return {"id": 123, "username": username, "email": email}

    @operations
    def delete(self, user_id):
        return {"deleted": user_id}

    @operations
    def update(self, user_id, **fields):
        return {"updated": user_id, "fields": fields}

api = UserAPI()
api.operations('create')("alice", "alice@example.com")
api.operations('delete')(123)
api.operations('update')(123, email="new@example.com")
```

## Hierarchical API Structure

### Multi-Domain Organization
```python
class ProductionAPI:
    # Root switcher
    api = Switcher(name="api")

    # Domain switchers with prefixes
    users = api.add(Switcher(name="users", prefix="user_"))
    products = api.add(Switcher(name="products", prefix="product_"))
    orders = api.add(Switcher(name="orders", prefix="order_"))

    # User handlers
    @users
    def user_list(self, filters=None):
        return db.users.find(filters or {})

    @users
    def user_create(self, data):
        return db.users.insert(data)

    @users
    def user_update(self, user_id, data):
        return db.users.update(user_id, data)

    # Product handlers
    @products
    def product_list(self, category=None):
        return db.products.find(category)

    @products
    def product_search(self, query):
        return db.products.search(query)

    # Order handlers
    @orders
    def order_create(self, user_id, items):
        return db.orders.create(user_id, items)

    @orders
    def order_get(self, order_id):
        return db.orders.get(order_id)

# Usage
api = ProductionAPI()

# Direct access
api.users('list')(filters={'active': True})

# Hierarchical access (dot notation)
api.api('users.list')(filters={'active': True})
api.api('products.search')(query="laptop")
api.api('orders.get')(order_id=123)

# Introspection
api.api.entries()              # ['users', 'products', 'orders']
api.users.entries()            # ['list', 'create', 'update']
for child in api.api.children:
    print(f"{child.name}: {child.entries()}")
```

## Command Pattern

### Command Handler Registry
```python
class CommandProcessor:
    commands = Switcher(prefix='cmd_')

    @commands
    def cmd_start(self, context):
        context['status'] = 'running'
        return "Started"

    @commands
    def cmd_stop(self, context):
        context['status'] = 'stopped'
        return "Stopped"

    @commands
    def cmd_restart(self, context):
        self.cmd_stop(context)
        self.cmd_start(context)
        return "Restarted"

processor = CommandProcessor()
context = {}

# Execute commands by name
processor.commands('start')(context)
processor.commands('restart')(context)
```

## Plugin Pattern - Middleware

### Request/Response Logging
```python
from smartswitch import Switcher, BasePlugin

class LoggingPlugin(BasePlugin):
    def wrap_handler(self, func, name, switcher):
        def wrapper(*args, **kwargs):
            print(f"[{switcher.name}] Calling {name}")
            print(f"  Args: {args}, Kwargs: {kwargs}")
            result = func(*args, **kwargs)
            print(f"  Result: {result}")
            return result
        return wrapper

api = Switcher(name="api", plugins=[LoggingPlugin()])

@api
def process_payment(amount, currency):
    return {"status": "success", "amount": amount, "currency": currency}

# Logs automatically
api('process_payment')(100, "USD")
# Output:
# [api] Calling process_payment
#   Args: (100, 'USD'), Kwargs: {}
#   Result: {'status': 'success', 'amount': 100, 'currency': 'USD'}
```

## Plugin Pattern - Validation

### Pydantic Integration
```python
from smartswitch import Switcher
from smartswitch.plugins import PydanticPlugin

sw = Switcher(plugins=[PydanticPlugin()])

@sw
def create_user(name: str, age: int, email: str):
    return {"name": name, "age": age, "email": email}

# Valid call
sw('create_user')("Alice", 30, "alice@example.com")

# Invalid call - raises ValidationError
try:
    sw('create_user')("Alice", "thirty", "alice@example.com")  # age must be int
except Exception as e:
    print(f"Validation failed: {e}")
```

## Plugin Pattern - Custom Lifecycle

### Initialization Hook
```python
from smartswitch import BasePlugin

class InitializerPlugin(BasePlugin):
    def on_decorate(self, func, name, switcher, metadata):
        """Called when handler is decorated (before wrapping)."""
        print(f"Registered {name} in {switcher.name}")
        # Can store metadata for later use
        metadata['registered_at'] = time.time()

    def wrap_handler(self, func, name, switcher):
        """Called to wrap the handler."""
        def wrapper(*args, **kwargs):
            # Access metadata stored during on_decorate
            registered_at = func._plugin_meta.get('registered_at')
            print(f"Handler registered at {registered_at}")
            return func(*args, **kwargs)
        return wrapper

sw = Switcher(plugins=[InitializerPlugin()])

@sw
def process(data):
    return f"Processed: {data}"
```

## Prefix-Based Organization

### Event Handler Organization
```python
class EventSystem:
    handlers = Switcher(prefix='on_')

    @handlers
    def on_user_login(self, user_id):
        print(f"User {user_id} logged in")

    @handlers
    def on_user_logout(self, user_id):
        print(f"User {user_id} logged out")

    @handlers
    def on_payment_received(self, amount):
        print(f"Payment received: ${amount}")

    def trigger(self, event_name, *args, **kwargs):
        """Trigger event by name."""
        return self.handlers(event_name)(*args, **kwargs)

events = EventSystem()
events.trigger('user_login', user_id=123)
events.trigger('payment_received', amount=100)
```

## Dynamic Handler Discovery

### List and Call Handlers
```python
api = Switcher(name="api")

@api
def get_users():
    return ["alice", "bob"]

@api
def get_products():
    return ["laptop", "phone"]

@api
def get_orders():
    return [1, 2, 3]

# Discover all handlers
handlers = api.entries()  # ['get_users', 'get_products', 'get_orders']

# Call all handlers dynamically
results = {}
for handler_name in handlers:
    results[handler_name] = api(handler_name)()

print(results)
# {
#   'get_users': ['alice', 'bob'],
#   'get_products': ['laptop', 'phone'],
#   'get_orders': [1, 2, 3]
# }
```

## Method Binding in Classes

### Service Class Pattern
```python
class DatabaseService:
    operations = Switcher()

    def __init__(self, connection_string):
        self.conn = connect(connection_string)

    @operations
    def save(self, table, data):
        return self.conn.execute(f"INSERT INTO {table} ...", data)

    @operations
    def load(self, table, id):
        return self.conn.execute(f"SELECT * FROM {table} WHERE id = ?", id)

    @operations
    def delete(self, table, id):
        return self.conn.execute(f"DELETE FROM {table} WHERE id = ?", id)

# Instance method binding
db = DatabaseService("postgresql://...")
db.operations('save')("users", {"name": "Alice"})  # 'self' bound automatically
db.operations('load')("users", 123)
```

## Plugin Chaining

### Multiple Plugins Together
```python
from smartswitch import Switcher, BasePlugin

class TimingPlugin(BasePlugin):
    def wrap_handler(self, func, name, switcher):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            print(f"{name} took {elapsed:.4f}s")
            return result
        return wrapper

class LoggingPlugin(BasePlugin):
    def wrap_handler(self, func, name, switcher):
        def wrapper(*args, **kwargs):
            print(f"Calling {name}")
            result = func(*args, **kwargs)
            print(f"Done: {name}")
            return result
        return wrapper

# Chain plugins - applied in order
sw = Switcher(plugins=[LoggingPlugin(), TimingPlugin()])

@sw
def process(data):
    time.sleep(0.1)
    return f"Processed: {data}"

sw('process')("test")
# Output:
# Calling process
# process took 0.1002s
# Done: process
```

## Best Practices

1. **Use prefixes for related handlers**: Groups handlers logically
2. **Organize with hierarchy**: Separate concerns with child Switchers
3. **Plugin for cross-cutting concerns**: Logging, validation, timing
4. **Keep handler names descriptive**: Clear intent from name alone
5. **Method binding for services**: Use Switcher as class attribute
6. **Discovery via entries()**: Dynamic handler listing and calling

## Performance Tips

- Handler lookup is O(1) dictionary access (~2μs overhead)
- Plugin wrapping happens once at decoration time
- Child Switchers add ~1μs per level for dot notation access
- For ultra-hot paths, store handler reference directly
