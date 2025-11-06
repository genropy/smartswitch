# Best Practices

> **Test Source**: Examples in this guide are from [test_complete.py](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py)

This guide provides production-ready patterns and best practices for using SmartSwitch effectively.

## Design Principles

<!-- test: test_complete.py::test_rule_priority_by_registration_order -->

### 1. Register Specific Rules First

Rules are evaluated in **registration order**. Always register more specific rules before more general ones:

**From test**: [test_rule_priority_by_registration_order](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L347-L371)

```python
# ✅ Good: Specific rule first
sw = Switcher()

@sw(typerule={'x': int}, valrule=lambda x: x > 100)
def handle_large_int(x):
    return "large int"

@sw(typerule={'x': int})
def handle_any_int(x):
    return "any int"

# ❌ Bad: General rule first (specific rule never matches)
sw = Switcher()

@sw(typerule={'x': int})
def handle_any_int(x):
    return "any int"

@sw(typerule={'x': int}, valrule=lambda x: x > 100)
def handle_large_int(x):
    return "large int"  # Never called!
```

<!-- test: test_complete.py::test_default_handler_catches_all -->

### 2. Always Provide a Default Handler

Unless you're certain all cases are covered, always register a default handler:

**From test**: [test_default_handler_catches_all](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L518-L534)

```python
# ✅ Good: Default handler catches unexpected cases
sw = Switcher()

@sw(typerule={'x': int})
def handle_int(x):
    return "int"

@sw(typerule={'x': str})
def handle_string(x):
    return "string"

@sw
def handle_default(x):
    return f"Unexpected type: {type(x).__name__}"

# ❌ Bad: No default handler (raises ValueError for float)
sw = Switcher()

@sw(typerule={'x': int})
def handle_int(x):
    return "int"

@sw(typerule={'x': str})
def handle_string(x):
    return "string"

# sw()(x=3.14) → ValueError: No rule matched
```

**Exception:** When you want strict validation and prefer errors for unhandled cases.

### 3. Use Descriptive Names

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

### 4. Use Prefix Conventions

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

## Type Rules Best Practices

### Use Union Types for Flexibility

```python
# ✅ Good: Handles multiple numeric types
@sw(typerule={'value': int | float})
def handle_number(value):
    return value * 2

# ❌ Bad: Only handles int
@sw(typerule={'value': int})
def handle_number(value):
    return value * 2
```

### Leverage Custom Classes

Use custom classes for domain-specific dispatch:

```python
# ✅ Good: Type-safe domain dispatch
class AdminUser:
    pass

class RegularUser:
    pass

@sw(typerule={'user': AdminUser})
def handle_admin(user):
    return "admin access"

@sw(typerule={'user': RegularUser})
def handle_regular(user):
    return "regular access"

# ❌ Bad: String-based type checking
@sw(valrule=lambda user: user['type'] == 'admin')
def handle_admin(user):
    return "admin access"
```

### Check All Parameters

When using multiple parameters, specify type rules for all relevant parameters:

```python
# ✅ Good: All parameters validated
@sw(typerule={'a': int, 'b': int, 'c': int})
def handle_ints(a, b, c):
    return a + b + c

# ❌ Bad: Partial validation
@sw(typerule={'a': int})
def handle_ints(a, b, c):
    return a + b + c  # b and c might not be ints!
```

## Value Rules Best Practices

### Use Named Functions for Complex Logic

For complex value rules, use named functions instead of lambdas:

```python
# ✅ Good: Named function for complex logic
def is_valid_user(username, role, age):
    """Check if user is valid based on role and age."""
    if role == 'admin' and age < 21:
        return False
    if role == 'moderator' and age < 18:
        return False
    return len(username) >= 3

@sw(valrule=is_valid_user)
def handle_valid_user(username, role, age):
    ...

# ❌ Bad: Unreadable lambda
@sw(valrule=lambda username, role, age: not (role == 'admin' and age < 21) and not (role == 'moderator' and age < 18) and len(username) >= 3)
def handle_valid_user(username, role, age):
    ...
```

**Benefits:**
- Easier to test independently
- Better stack traces
- Reusable across multiple handlers
- Self-documenting with docstrings

### Safe Dictionary Access

Use `.get()` for optional parameters:

```python
# ✅ Good: Safe access with defaults
@sw(valrule=lambda **kw: kw.get('status', 'pending') == 'active')
def handle_active(status='pending'):
    ...

# ❌ Bad: KeyError if 'status' missing
@sw(valrule=lambda **kw: kw['status'] == 'active')
def handle_active(status='pending'):
    ...
```

### Avoid Side Effects in Rules

Value rules should be pure functions without side effects:

```python
# ✅ Good: Pure function
@sw(valrule=lambda x: x > 0)
def handle_positive(x):
    print(f"Processing {x}")  # Side effect in handler
    return x * 2

# ❌ Bad: Side effect in rule
@sw(valrule=lambda x: print(f"Checking {x}") or x > 0)
def handle_positive(x):
    return x * 2
```

**Reason:** Rules may be evaluated multiple times or in unexpected order.

### Choose Appropriate Syntax

Use expanded syntax for simple conditions, compact for dictionary operations:

```python
# ✅ Good: Expanded for simple condition
@sw(valrule=lambda x: x > 0)
def handle_positive(x):
    ...

# ✅ Good: Compact for dictionary logic
@sw(valrule=lambda kw: kw.get('mode') == 'test' and kw.get('debug', False))
def handle_debug_test(mode, debug=False):
    ...

# ❌ Bad: Compact when not needed
@sw(valrule=lambda kw: kw['x'] > 0)
def handle_positive(x):
    ...  # Expanded syntax is clearer here
```

## Performance Best Practices

### When to Use SmartSwitch

SmartSwitch is optimized for functions that do **real work** (>1ms):

```python
# ✅ Good: I/O-bound operation
@sw(typerule={'url': str})
def fetch_from_api(url):
    response = requests.get(url)  # Milliseconds
    return response.json()

# ✅ Good: Business logic
@sw(valrule=lambda amount: amount > 1000)
def process_large_transaction(amount):
    # Complex validation, database queries, etc.
    ...

# ❌ Bad: Ultra-fast inner loop
for i in range(1_000_000):
    result = sw()(x=i)  # Overhead dominates
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

### Use Named Handlers for Hot Paths

For performance-critical code, use named handlers directly:

```python
# ✅ Good: Direct access (50-100ns)
handler = sw('process_payment')
result = handler(transaction)

# ❌ Slower: Rule-based dispatch (~1-2μs)
result = sw()(transaction)
```

**Use case:** When you know the handler name at runtime and need maximum performance.

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

Don't rely solely on rules for validation:

```python
# ✅ Good: Additional validation in handler
@sw(typerule={'amount': int | float})
def process_payment(amount):
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if amount > 1_000_000:
        raise ValueError("Amount too large")
    # Process payment
    ...

# ❌ Bad: No validation in handler
@sw(typerule={'amount': int | float})
def process_payment(amount):
    # Assumes amount is valid
    charge_card(amount)  # What if amount is negative?
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
@sw(typerule={'user': AdminUser})
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

### Document Rule Intent with Comments

For complex rules, add comments:

```python
@sw(
    typerule={'amount': int | float},
    # Large transactions require special processing and auditing
    valrule=lambda amount: amount > 10_000
)
def process_large_transaction(amount):
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

### Sanitize Inputs in Value Rules

```python
# ✅ Good: Safe string handling
@sw(valrule=lambda path: path.startswith('/api/') and '..' not in path)
def handle_api_request(path):
    ...

# ❌ Bad: No sanitization
@sw(valrule=lambda path: path.startswith('/api/'))
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

- Review [Type Rules Guide](typerules.md)
- Review [Value Rules Guide](valrules.md)
- Review [Named Handlers Guide](named-handlers.md)
- Explore [Real-World Examples](../examples/index.md)
- Read the [API Reference](../api/switcher.md)
