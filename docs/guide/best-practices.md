# Best Practices

> **Test Source**: Examples in this guide are from [test_complete.py](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py)

This guide provides production-ready patterns and best practices for using SmartSwitch effectively.

## Design Principles

### 1. Use Descriptive Names

Make handler names self-documenting:

```python
# ✅ Good: Clear intent
@sw
def handle_payment_success(transaction):
    ...

@sw
def handle_payment_failure(transaction):
    ...

# ❌ Bad: Unclear purpose
@sw
def handler1(transaction):
    ...

@sw
def handler2(transaction):
    ...
```

### 2. Use Prefix Conventions

When you have many related handlers, use a consistent prefix and the `prefix` parameter:

```python
# ✅ Good: Consistent prefix with auto-stripping
storage = Switcher(
    name='storage',
    description='Storage backend dispatcher',
    prefix='backend_'
)

@storage
def backend_s3(data):
    ...

@storage
def backend_gcs(data):
    ...

@storage
def backend_local(data):
    ...

# Access by short names
storage('s3')(data)
storage('gcs')(data)

# ❌ Bad: Inconsistent or no prefix
storage = Switcher()

@storage
def s3_handler(data):
    ...

@storage
def handle_gcs(data):
    ...

@storage
def local(data):
    ...
```

## Performance Best Practices

### When to Use SmartSwitch

SmartSwitch is optimized for functions that do **real work** (>1ms):

```python
# ✅ Good: I/O-bound operation
@sw
def fetch_from_api(url):
    response = requests.get(url)  # Milliseconds
    return response.json()

# ✅ Good: Business logic
@sw
def process_large_transaction(amount):
    # Complex validation, database queries, etc.
    ...

# ❌ Bad: Ultra-fast inner loop
for i in range(1_000_000):
    result = sw('handler')(x=i)  # Overhead dominates
```

**Overhead:** ~1-2 microseconds per dispatch

**Use for:**
- ✅ API routing
- ✅ Event handling
- ✅ Data validation
- ✅ Business logic dispatch

**Avoid for:**
- ❌ Nanosecond-level operations
- ❌ Inner loops with millions of iterations

### Use Direct Named Access for Hot Paths

For performance-critical code, retrieve and cache handlers:

```python
# ✅ Good: Direct access (minimal overhead)
handler = sw('process_payment')
result = handler(transaction)

# Also good: Direct call
result = sw('process_payment')(transaction)
```

**Use case:** When you know the handler name at runtime.

### Cache Switchers

Create Switchers once and reuse them:

```python
# ✅ Good: Module-level switcher
api = Switcher(prefix='handle_')

@api
def handle_get_users():
    ...

# ❌ Bad: Creating switcher per request
def handle_request(method, path):
    api = Switcher()  # Unnecessary overhead
    @api
    def handler():
        ...
```

## Error Handling Best Practices

### Validate Inputs in Handlers

Always validate inputs within your handlers:

```python
# ✅ Good: Comprehensive validation in handler
@sw
def process_payment(amount):
    if not isinstance(amount, (int, float)):
        raise TypeError("Amount must be a number")
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if amount > 1_000_000:
        raise ValueError("Amount too large")
    # Process payment
    ...

# ❌ Bad: No validation in handler
@sw
def process_payment(amount):
    # Assumes amount is valid
    charge_card(amount)  # What if amount is negative or wrong type?
```

### Handle Missing Handlers Gracefully

When using named dispatch with user input:

```python
# ✅ Good: Defensive check
def execute_command(command_name, *args):
    if command_name in commands._handlers:
        return commands(command_name)(*args)
    else:
        return {"error": f"Unknown command: {command_name}"}

# ❌ Bad: Unhandled error
def execute_command(command_name, *args):
    return commands(command_name)(*args)  # May fail
```

### Provide Helpful Error Messages

Use custom error messages in default handlers:

```python
# ✅ Good: Helpful error message
@sw
def handle_unsupported(data):
    return {
        "error": "Unsupported data type",
        "type": type(data).__name__,
        "hint": "Supported types: int, str, list"
    }

# ❌ Bad: Generic error
@sw
def handle_unsupported(data):
    return {"error": "Invalid"}
```

## Testing Best Practices

### Test Each Handler Independently

```python
# ✅ Good: Test handlers independently
def test_handle_int():
    result = handle_int(x=42)
    assert result == "int"

def test_handle_string():
    result = handle_string(x="hello")
    assert result == "string"

# Test dispatch
def test_dispatch():
    assert sw()(x=42) == "int"
    assert sw()(x="hello") == "string"
```

### Test Rule Priority

```python
def test_rule_priority():
    """Ensure specific rules match before general ones."""
    # Specific rule should match
    assert sw()(x=150) == "very large"

    # General rule should match when specific doesn't
    assert sw()(x=50) == "large"
```

### Test Default Handler

```python
def test_default_handler():
    """Ensure default handler catches unmatched cases."""
    result = sw()(x=3.14)  # Not int or str
    assert result == "default"
```

### Test Edge Cases

```python
def test_edge_cases():
    """Test boundary conditions."""
    assert sw()(x=0) == "zero"
    assert sw()(x=-1) == "negative"
    assert sw()(x=1) == "positive"
```

## Documentation Best Practices

### Document Your Switcher

Use the `description` parameter:

```python
# ✅ Good: Self-documenting
api = Switcher(
    name='api',
    description='HTTP API request router',
    prefix='handle_'
)
```

### Document Handler Intent

Use docstrings for complex handlers:

```python
# ✅ Good: Clear documentation
@sw
def handle_admin_request(user, action):
    """
    Handle administrative actions.

    Args:
        user: Authenticated admin user
        action: Admin action to perform (create, delete, modify)

    Returns:
        dict: Action result with status and message

    Raises:
        PermissionError: If user lacks required permissions
    """
    ...
```

## Organization Best Practices

### Group Related Handlers

```python
# ✅ Good: Organized by domain
# User management
user_api = Switcher(prefix='handle_')

@user_api
def handle_create_user():
    ...

@user_api
def handle_delete_user():
    ...

# Payment processing
payment_api = Switcher(prefix='handle_')

@payment_api
def handle_charge():
    ...

@payment_api
def handle_refund():
    ...
```

### Use Separate Files for Large Switchers

```python
# handlers/user.py
user_api = Switcher(prefix='handle_')

@user_api
def handle_create():
    ...

# handlers/payment.py
payment_api = Switcher(prefix='handle_')

@payment_api
def handle_charge():
    ...

# main.py
from handlers.user import user_api
from handlers.payment import payment_api
```

## Security Best Practices

### Validate User Input

Never trust user input when selecting handlers:

```python
# ✅ Good: Whitelist approach
ALLOWED_COMMANDS = ['start', 'stop', 'restart']

def execute_user_command(command, *args):
    if command not in ALLOWED_COMMANDS:
        raise ValueError(f"Unauthorized command: {command}")
    return commands(command)(*args)

# ❌ Bad: Direct user input
def execute_user_command(command, *args):
    return commands(command)(*args)  # Dangerous!
```

### Sanitize All Inputs

Always validate and sanitize inputs in your handlers:

```python
# ✅ Good: Safe string handling
@sw
def handle_api_request(path):
    if not path.startswith('/api/'):
        raise ValueError("Invalid API path")
    if '..' in path:
        raise ValueError("Path traversal detected")
    ...

# ❌ Bad: No sanitization
@sw
def handle_api_request(path):
    ...  # Vulnerable to path traversal
```

### Avoid Exposing Internal Handlers

Don't expose all handlers to external callers:

```python
# ✅ Good: Public API wrapper
class APIServer:
    _internal = Switcher()  # Private
    public = Switcher()     # Public

    @public
    def handle_get_users(self):
        return self._internal('fetch_users')()

    @_internal
    def fetch_users(self):
        # Internal implementation
        ...
```

## Next Steps

- Review [Named Handlers Guide](named-handlers.md)
- Explore [Plugin System](../plugins/index.md)
- Check out [Real-World Examples](../examples/index.md)
- Read the [API Reference](../api/switcher.md)
