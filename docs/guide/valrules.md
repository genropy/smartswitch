# Value Rules Guide

> **Test Source**: Examples in this guide are from [test_complete.py](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py)

Value rules allow you to dispatch functions based on the **runtime values** of arguments, not just their types. This enables condition-based routing similar to pattern matching or guard clauses.

<!-- test: test_complete.py::test_simple_value_rule -->

## Basic Value Rules

A value rule is a lambda or function that receives the arguments and returns `True` if the handler should be invoked:

**From test**: [test_simple_value_rule](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L168-L186)

```python
from smartswitch import Switcher

sw = Switcher()

@sw(valrule=lambda x: x < 0)
def handle_negative(x):
    return "negative"

@sw(valrule=lambda x: x > 0)
def handle_positive(x):
    return "positive"

@sw(valrule=lambda x: x == 0)
def handle_zero(x):
    return "zero"

assert sw()(x=-5) == "negative"
assert sw()(x=5) == "positive"
assert sw()(x=0) == "zero"
```

**Key Points:**
- Value rules receive the actual runtime values as arguments
- The first matching rule wins (registration order matters)
- If no rule matches, the default handler is called (if registered)

<!-- test: test_complete.py::test_value_rule_with_multiple_params -->

## Multiple Parameters

Value rules can access multiple parameters:

**From test**: [test_value_rule_with_multiple_params](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L188-L206)

```python
sw = Switcher()

@sw(valrule=lambda a, b: a > b)
def handle_greater(a, b):
    return f"{a} > {b}"

@sw(valrule=lambda a, b: a < b)
def handle_less(a, b):
    return f"{a} < {b}"

@sw(valrule=lambda a, b: a == b)
def handle_equal(a, b):
    return f"{a} == {b}"

assert sw()(a=10, b=5) == "10 > 5"
assert sw()(a=3, b=7) == "3 < 7"
assert sw()(a=5, b=5) == "5 == 5"
```

<!-- test: test_complete.py::test_complex_value_rule -->

## Complex Conditions

Value rules can use any Python expression:

**From test**: [test_complex_value_rule](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L208-L226)

```python
sw = Switcher()

@sw(valrule=lambda x: 0 <= x <= 100)
def handle_percentage(x):
    return "percentage"

@sw(valrule=lambda x: x > 100)
def handle_large(x):
    return "large"

@sw
def handle_other(x):
    return "other"

assert sw()(x=50) == "percentage"
assert sw()(x=150) == "large"
assert sw()(x=-10) == "other"
```

**Use Cases:**
- Range checking (`0 <= x <= 100`)
- String pattern matching (`x.startswith('/')`)
- List length (`len(items) > 0`)
- Complex business logic

<!-- test: test_complete.py::test_compact_lambda_single_param -->

## Compact Lambda Syntax

SmartSwitch supports a compact syntax where the lambda receives a dictionary of all arguments:

**From test**: [test_compact_lambda_single_param](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L232-L250)

```python
sw = Switcher()

@sw(valrule=lambda kw: kw['mode'] == 'test')
def handle_test(mode):
    return "test mode"

@sw(valrule=lambda kw: kw['mode'] == 'prod')
def handle_prod(mode):
    return "prod mode"

@sw
def handle_default(mode):
    return "default"

assert sw()(mode='test') == "test mode"
assert sw()(mode='prod') == "prod mode"
assert sw()(mode='other') == "default"
```

**When to Use:**
- Accessing dictionary-like parameters
- Conditional logic based on parameter existence
- More complex dictionary operations

<!-- test: test_complete.py::test_compact_lambda_with_kw_get -->

### Safe Access with `.get()`

Use `.get()` for optional parameters:

**From test**: [test_compact_lambda_with_kw_get](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L267-L280)

```python
sw = Switcher()

@sw(valrule=lambda kw: kw.get('status') == 'active')
def handle_active(status):
    return "active"

@sw
def handle_default(status):
    return "default"

assert sw()(status='active') == "active"
assert sw()(status='other') == "default"
```

<!-- test: test_complete.py::test_compact_lambda_multiple_params -->

### Multiple Conditions with Compact Syntax

**From test**: [test_compact_lambda_multiple_params](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L252-L265)

```python
sw = Switcher()

@sw(valrule=lambda kw: kw['mode'] == 'xxx' and kw['height'] > 30)
def handle_high(mode, height):
    return f"High: {height}"

@sw(valrule=lambda kw: kw['height'] <= 30)
def handle_low(mode, height):
    return f"Low: {height}"

assert sw()(mode='xxx', height=50) == "High: 50"
assert sw()(mode='xxx', height=20) == "Low: 20"
```

<!-- test: test_complete.py::test_var_keyword_lambda_syntax -->

## VAR_KEYWORD Syntax

For maximum flexibility, use `**kw` syntax:

**From test**: [test_var_keyword_lambda_syntax](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L302-L316)

```python
sw = Switcher()

@sw(valrule=lambda **kw: kw.get('y', 0) > 5)
def handle_with_y(x, y=0):
    return f"y={y}"

@sw
def handle_default(x, y=0):
    return "default"

assert sw()(x=1, y=10) == "y=10"
assert sw()(x=1, y=3) == "default"
assert sw()(x=1) == "default"
```

**Use Cases:**
- Functions with optional parameters
- Default value handling
- Flexible parameter acceptance

<!-- test: test_complete.py::test_mixed_compact_and_expanded_syntax -->

## Mixing Compact and Expanded Syntax

You can mix both styles in the same switcher:

**From test**: [test_mixed_compact_and_expanded_syntax](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L282-L300)

```python
sw = Switcher()

@sw(valrule=lambda kw: kw['x'] > 100)  # Compact
def handle_large(x):
    return "large"

@sw(valrule=lambda x: x > 50)  # Expanded
def handle_medium(x):
    return "medium"

@sw(valrule=lambda kw: kw['x'] > 0)  # Compact
def handle_small(x):
    return "small"

assert sw()(x=150) == "large"
assert sw()(x=75) == "medium"
assert sw()(x=25) == "small"
```

**Best Practice:** Choose the style that makes your code most readable. The expanded syntax is clearer for simple conditions, while compact syntax is better for complex dictionary operations.

## Combining with Type Rules

Value rules become even more powerful when combined with type rules:

```python
sw = Switcher()

@sw(typerule={'x': int}, valrule=lambda x: x > 0)
def handle_positive_int(x):
    return "positive int"

@sw(typerule={'x': int}, valrule=lambda x: x < 0)
def handle_negative_int(x):
    return "negative int"

@sw(typerule={'x': str})
def handle_string(x):
    return "string"

@sw
def handle_default(x):
    return "default"

print(sw()(x=5))     # → "positive int"
print(sw()(x=-5))    # → "negative int"
print(sw()(x="hi"))  # → "string"
print(sw()(x=0))     # → "default" (int but neither positive nor negative)
```

**Execution Order:**
1. Type rules are checked first
2. If types match, value rules are checked
3. Both must pass for the handler to match

## Rule Priority

Just like type rules, **the first matching value rule wins**:

```python
sw = Switcher()

# More specific rule registered FIRST
@sw(valrule=lambda x: x > 100)
def handle_very_large(x):
    return "very large"

# Broader rule registered SECOND
@sw(valrule=lambda x: x > 10)
def handle_large(x):
    return "large"

print(sw()(x=150))  # → "very large" (first match wins)
print(sw()(x=50))   # → "large"
```

**Best Practice:** Register more specific rules before more general ones.

## Common Patterns

### HTTP Method + Path Routing

```python
api = Switcher()

@api(valrule=lambda method, path: method == 'GET' and path == '/users')
def handle_list_users(method, path):
    return "list users"

@api(valrule=lambda method, path: method == 'POST' and path == '/users')
def handle_create_user(method, path):
    return "create user"

@api
def handle_not_found(method, path):
    return "not found"

print(api()(method='GET', path='/users'))      # → "list users"
print(api()(method='POST', path='/users'))     # → "create user"
print(api()(method='GET', path='/products'))   # → "not found"
```

### Data Validation

```python
validator = Switcher()

@validator(typerule={'value': str}, valrule=lambda value: '@' in value)
def validate_email(value):
    return "email"

@validator(typerule={'value': int}, valrule=lambda value: 0 <= value <= 100)
def validate_percentage(value):
    return "percentage"

@validator
def validate_invalid(value):
    return "invalid"

print(validator()(value="user@example.com"))  # → "email"
print(validator()(value=75))                  # → "percentage"
print(validator()(value="just text"))         # → "invalid"
print(validator()(value=150))                 # → "invalid"
```

### State Machine

```python
fsm = Switcher()

@fsm(valrule=lambda state, event: state == 'idle' and event == 'start')
def transition_to_running(state, event):
    return 'running'

@fsm(valrule=lambda state, event: state == 'running' and event == 'pause')
def transition_to_paused(state, event):
    return 'paused'

@fsm(valrule=lambda state, event: state == 'paused' and event == 'resume')
def transition_to_running_again(state, event):
    return 'running'

@fsm(valrule=lambda state, event: event == 'stop')
def transition_to_idle(state, event):
    return 'idle'
```

### Configuration-Based Dispatch

```python
handler = Switcher()

@handler(valrule=lambda **kw: kw.get('debug', False))
def handle_debug_mode(data, debug=False):
    print(f"DEBUG: {data}")
    return data

@handler
def handle_normal_mode(data, debug=False):
    return data

result = handler()(data="test", debug=True)   # Prints debug info
result = handler()(data="test", debug=False)  # Silent
```

## Performance Characteristics

Value rules have minimal overhead:
- Lambda compilation happens once at registration
- Evaluation is pure Python function call
- No additional type checking or reflection

**Overhead:** ~1-2 microseconds per dispatch (including type checks if present)

This makes value rules suitable for:
- ✅ API routing (I/O bound)
- ✅ Event processing (business logic)
- ✅ Configuration dispatch
- ❌ Ultra-fast inner loops (nanoseconds)

## Error Handling

If no rule matches and no default handler is registered, SmartSwitch raises `ValueError`:

```python
sw = Switcher()

@sw(valrule=lambda x: x > 0)
def handle_positive(x):
    return "positive"

# This will raise ValueError: No rule matched
sw()(x=-5)
```

**Best Practice:** Always register a default handler:

```python
@sw
def handle_default(x):
    return f"No rule matched for: {x}"
```

## Value Rule Exceptions

If a value rule raises an exception, the rule does **not** match:

```python
sw = Switcher()

@sw(valrule=lambda x: x['key'] == 'test')  # Will fail if 'key' missing
def handle_with_key(x):
    return "has key"

@sw
def handle_default(x):
    return "no key"

print(sw()(x={'key': 'test'}))  # → "has key"
print(sw()(x={}))               # → "no key" (KeyError caught)
```

**Best Practice:** Use `.get()` for safe dictionary access or wrap in try-except.

## Limitations

Value rules have some limitations:

1. **Performance**: Complex rules execute on every dispatch attempt
2. **Debugging**: Lambda functions can be harder to debug than named functions
3. **Side Effects**: Avoid side effects in value rules (use handlers for that)

## Advanced: Named Functions as Value Rules

For complex logic, use named functions instead of lambdas:

```python
def is_valid_user(username, role):
    """Complex validation logic."""
    if role == 'admin':
        return username.startswith('admin_')
    elif role == 'user':
        return len(username) >= 3
    return False

sw = Switcher()

@sw(valrule=is_valid_user)
def handle_valid_user(username, role):
    return f"Valid: {username} ({role})"

@sw
def handle_invalid_user(username, role):
    return f"Invalid: {username}"
```

**Benefits:**
- Better debugging (stack traces show function name)
- Reusable logic
- Testable independently
- Self-documenting code

## Next Steps

- Learn about [Type Rules](typerules.md) for type-based dispatch
- Explore [Named Handlers](named-handlers.md) for direct handler access
- See [Best Practices](best-practices.md) for production usage patterns
- Check [Real-World Examples](../examples/index.md) for practical use cases
