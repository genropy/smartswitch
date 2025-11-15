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

## SmartPublisher Integration

If you plan to publish your handlers as APIs using **SmartPublisher**, follow these practices to enable automatic API generation:

### Use Complete Type Hints

Type hints enable automatic parameter validation and API documentation:

```python
from __future__ import annotations

# ✅ Good: Complete type hints
@sw
def create_user(name: str, email: str, age: int | None = None) -> dict[str, Any]:
    """Create a new user account."""
    return {"id": 123, "name": name, "email": email, "age": age}

# ❌ Bad: Missing type hints
@sw
def create_user(name, email, age=None):
    """Create a new user account."""
    return {"id": 123, "name": name, "email": email, "age": age}
```

**Why it matters:**
- SmartPublisher generates API schemas from type hints
- Enables automatic request validation
- Provides clear API documentation
- Improves IDE autocompletion

### Write Comprehensive Docstrings

Use Google-style docstrings with Args, Returns, and Raises sections:

```python
# ✅ Good: Complete documentation
@sw
def transfer_funds(
    from_account: str,
    to_account: str,
    amount: float,
    currency: str = "USD"
) -> dict[str, Any]:
    """
    Transfer funds between two accounts.

    Args:
        from_account: Source account identifier (e.g., 'ACC123')
        to_account: Destination account identifier (e.g., 'ACC456')
        amount: Amount to transfer (must be positive)
        currency: Currency code (ISO 4217), defaults to 'USD'

    Returns:
        Transaction result with status and transaction ID:
        {
            "transaction_id": str,
            "status": "completed" | "pending" | "failed",
            "amount": float,
            "currency": str
        }

    Raises:
        ValueError: If amount is negative or zero
        PermissionError: If user lacks transfer permissions
        AccountError: If account is frozen or doesn't exist
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")
    # Process transfer...
    return {"transaction_id": "TXN789", "status": "completed"}

# ❌ Bad: Minimal documentation
@sw
def transfer_funds(from_account: str, to_account: str, amount: float) -> dict:
    """Transfer money."""
    return {"transaction_id": "TXN789"}
```

**Why it matters:**
- SmartPublisher extracts docstrings for API documentation
- Clear parameter descriptions help API consumers
- Raises section documents error handling
- Return type description shows response structure

### Provide Clear Parameter Descriptions

Be specific about parameter constraints and formats:

```python
# ✅ Good: Specific constraints
@sw
def schedule_meeting(
    title: str,           # "Team Standup", max 100 chars
    date: str,            # ISO 8601 format: "2024-01-15T10:00:00Z"
    duration_minutes: int # Must be 15, 30, 45, or 60
) -> dict[str, Any]:
    """
    Schedule a meeting.

    Args:
        title: Meeting title (1-100 characters)
        date: Meeting date/time in ISO 8601 format (UTC)
        duration_minutes: Meeting duration (must be 15, 30, 45, or 60)

    Returns:
        Meeting details with generated meeting ID

    Raises:
        ValueError: If duration not in allowed values or title too long
    """
    if duration_minutes not in (15, 30, 45, 60):
        raise ValueError("Duration must be 15, 30, 45, or 60 minutes")
    ...
```

### Use Modern Type Hint Syntax

Always import annotations to enable modern syntax:

```python
from __future__ import annotations

# ✅ Good: Modern syntax with union operator
@sw
def process_data(
    items: list[dict[str, Any]],
    callback: Callable[[dict], bool] | None = None
) -> list[dict[str, Any]]:
    """Process data items with optional callback."""
    ...

# ❌ Bad: Old syntax (without __future__ import)
from typing import List, Dict, Any, Optional, Callable

@sw
def process_data(
    items: List[Dict[str, Any]],
    callback: Optional[Callable[[Dict], bool]] = None
) -> List[Dict[str, Any]]:
    """Process data items with optional callback."""
    ...
```

**Why it matters:**
- Modern syntax is more readable
- Required for Python 3.10+ union syntax (`|` operator)
- Consistent with Python 3.10+ best practices

### Example: Well-Documented Handler

Here's a complete example ready for SmartPublisher:

```python
from __future__ import annotations
from typing import Any

@sw
def create_product(
    name: str,
    price: float,
    category: str,
    tags: list[str] | None = None,
    available: bool = True
) -> dict[str, Any]:
    """
    Create a new product in the catalog.

    Args:
        name: Product name (1-200 characters, must be unique)
        price: Product price in USD (must be positive)
        category: Product category (must exist in catalog)
        tags: Optional list of search tags (max 10 tags, 50 chars each)
        available: Whether product is available for purchase

    Returns:
        Created product with generated ID and timestamps:
        {
            "id": str,              # Product ID (e.g., "PROD123")
            "name": str,
            "price": float,
            "category": str,
            "tags": list[str],
            "available": bool,
            "created_at": str,      # ISO 8601 timestamp
            "updated_at": str       # ISO 8601 timestamp
        }

    Raises:
        ValueError: If price <= 0, name too long, or too many tags
        CategoryError: If category doesn't exist
        DuplicateError: If product name already exists
    """
    if price <= 0:
        raise ValueError("Price must be positive")
    if len(name) > 200:
        raise ValueError("Name too long (max 200 characters)")
    if tags and len(tags) > 10:
        raise ValueError("Too many tags (max 10)")

    # Create product...
    return {
        "id": "PROD123",
        "name": name,
        "price": price,
        "category": category,
        "tags": tags or [],
        "available": available,
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z"
    }
```

**Benefits for SmartPublisher:**
- ✅ Complete type hints enable automatic validation
- ✅ Detailed docstring generates clear API documentation
- ✅ Return structure is documented for API consumers
- ✅ All exceptions are documented for error handling
- ✅ Parameter constraints are clear for validation

## Next Steps

- Review [Named Handlers Guide](named-handlers.md)
- Explore [Plugin System](../plugins/index.md)
- Check out [Real-World Examples](../examples/index.md)
- Read the [API Reference](../api/switcher.md)
