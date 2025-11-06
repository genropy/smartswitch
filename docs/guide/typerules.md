# Type Rules Guide

> **Test Source**: Examples in this guide are from [test_complete.py](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py)

Type rules allow you to dispatch functions based on the **types** of arguments passed to the switcher. This is similar to function overloading in other languages, but more flexible and Pythonic.

<!-- test: test_complete.py::test_simple_type_dispatch -->

## Basic Type Dispatch

The simplest use case is dispatching based on a single parameter type:

**From test**: [test_simple_type_dispatch](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L87-L105)

```python
from smartswitch import Switcher

sw = Switcher()

@sw(typerule={'x': str})
def handle_string(x):
    return "string"

@sw(typerule={'x': int})
def handle_int(x):
    return "int"

@sw
def handle_default(x):
    return "default"

# Dispatch based on type
assert sw()(x="hello") == "string"
assert sw()(x=42) == "int"
assert sw()(x=3.14) == "default"
```

**Key Points:**
- Type rules are specified as a dictionary mapping parameter names to types
- The first matching rule wins (registration order matters)
- If no rule matches, the default handler is called (if registered)

<!-- test: test_complete.py::test_union_type_dispatch -->

## Union Types

You can use Python's union types (`|` operator) to match multiple types:

**From test**: [test_union_type_dispatch](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L107-L121)

```python
sw = Switcher()

@sw(typerule={'x': int | float})
def handle_number(x):
    return "number"

@sw(typerule={'x': str})
def handle_string(x):
    return "string"

assert sw()(x=42) == "number"
assert sw()(x=3.14) == "number"
assert sw()(x="hi") == "string"
```

**Note:** You can also use `typing.Union[int, float]` for compatibility with older Python versions.

<!-- test: test_complete.py::test_multiple_parameters_type_rules -->

## Multiple Parameters

Type rules work with multiple parameters:

**From test**: [test_multiple_parameters_type_rules](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L123-L136)

```python
sw = Switcher()

@sw(typerule={'a': int, 'b': int})
def add_ints(a, b):
    return a + b

@sw(typerule={'a': str, 'b': str})
def concat_strings(a, b):
    return a + b

assert sw()(a=5, b=10) == 15
assert sw()(a="hello", b=" world") == "hello world"
```

**Important:** All parameters in the `typerule` dictionary must match their types for the rule to succeed.

<!-- test: test_complete.py::test_custom_class_type_dispatch -->

## Custom Classes

Type rules work with any Python class, including your own:

**From test**: [test_custom_class_type_dispatch](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L138-L162)

```python
class Person:
    def __init__(self, name):
        self.name = name

class Company:
    def __init__(self, name):
        self.name = name

sw = Switcher()

@sw(typerule={'entity': Person})
def handle_person(entity):
    return f"person: {entity.name}"

@sw(typerule={'entity': Company})
def handle_company(entity):
    return f"company: {entity.name}"

person = Person("Alice")
company = Company("Acme")

assert sw()(entity=person) == "person: Alice"
assert sw()(entity=company) == "company: Acme"
```

This is especially useful for:
- Domain models (User, Admin, Guest)
- Data structures (Request, Response)
- Protocol handlers (HTTP, WebSocket, gRPC)

<!-- test: test_complete.py::test_any_type_always_matches -->

## The `Any` Type

Use `typing.Any` to create a rule that matches **any type**:

**From test**: [test_any_type_always_matches](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L650-L660)

```python
from typing import Any

sw = Switcher()

@sw(typerule={'x': Any})
def handle_any(x):
    return "any"

assert sw()(x=42) == "any"
assert sw()(x="text") == "any"
assert sw()(x=[1,2]) == "any"
```

**Use Case:** This is useful when you want to use type rules for some parameters but accept any type for others.

<!-- test: test_complete.py::test_empty_typerule_dict -->

## Empty Type Rules

An empty `typerule` dictionary creates a rule that always matches (no type constraints):

**From test**: [test_empty_typerule_dict](https://github.com/genropy/smartswitch/blob/main/tests/test_complete.py#L662-L671)

```python
sw = Switcher()

@sw(typerule={})
def handle(x):
    return "empty rule"

# Should match (no type constraints to fail)
assert sw()(x=42) == "empty rule"
```

**Note:** This is equivalent to not using `typerule` at all, but can be useful when combined with `valrule`.

## Positional vs Keyword Arguments

Type rules work with both positional and keyword arguments:

```python
sw = Switcher()

@sw(typerule={'x': int, 'y': int})
def calculate(x, y):
    return x + y

# All these work:
print(sw()(5, 10))           # Positional
print(sw()(x=5, y=10))       # Keyword
print(sw()(5, y=10))         # Mixed
```

SmartSwitch automatically maps positional arguments to parameter names based on the function signature.

## Rule Priority

When multiple rules could match, **the first registered rule wins**:

```python
sw = Switcher()

# Register more specific rule FIRST
@sw(typerule={'x': int})
def handle_int(x):
    return "int handler"

# Register broader rule SECOND
@sw(typerule={'x': int | float})
def handle_number(x):
    return "number handler"

print(sw()(x=42))  # → "int handler" (first match wins)
```

**Best Practice:** Register more specific rules before more general ones.

## Combining with Value Rules

Type rules can be combined with value rules for more precise dispatch:

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

print(sw()(x=5))     # → "positive int"
print(sw()(x=-5))    # → "negative int"
print(sw()(x="hi"))  # → "string"
```

See the [Value Rules Guide](valrules.md) for more details on combining rules.

## Performance Characteristics

SmartSwitch optimizes type checking with:
- **Pre-compiled type checks**: Type checkers are compiled once during registration
- **Cached signatures**: Function signatures are inspected only once
- **Fast path for common types**: Simple `isinstance()` checks for concrete types

**Overhead:** ~1-2 microseconds per dispatch

This makes type rules suitable for:
- ✅ API routing (handlers do I/O, milliseconds)
- ✅ Event processing (business logic, microseconds to milliseconds)
- ✅ Data validation (computation, microseconds)
- ❌ Ultra-fast inner loops (nanoseconds, called millions of times)

## Common Patterns

### Protocol Dispatcher

```python
class HTTPRequest:
    def __init__(self, method, path):
        self.method = method
        self.path = path

class WebSocketMessage:
    def __init__(self, data):
        self.data = data

protocol = Switcher()

@protocol(typerule={'msg': HTTPRequest})
def handle_http(msg):
    return f"HTTP {msg.method} {msg.path}"

@protocol(typerule={'msg': WebSocketMessage})
def handle_websocket(msg):
    return f"WS: {msg.data}"
```

### Type-Based Serialization

```python
serializer = Switcher()

@serializer(typerule={'obj': dict})
def serialize_dict(obj):
    return json.dumps(obj)

@serializer(typerule={'obj': list})
def serialize_list(obj):
    return json.dumps(obj)

@serializer(typerule={'obj': str})
def serialize_string(obj):
    return obj  # Already a string
```

### Multi-Method Dispatch

```python
math = Switcher()

@math(typerule={'a': int, 'b': int})
def compute(a, b):
    return a + b  # Integer addition

@math(typerule={'a': str, 'b': str})
def compute(a, b):
    return a + b  # String concatenation

@math(typerule={'a': list, 'b': list})
def compute(a, b):
    return a + b  # List concatenation
```

## Error Handling

If no rule matches and no default handler is registered, SmartSwitch raises `ValueError`:

```python
sw = Switcher()

@sw(typerule={'x': int})
def handle_int(x):
    return "int"

# This will raise ValueError: No rule matched
sw()(x="not an int")
```

**Best Practice:** Always register a default handler for robustness:

```python
@sw
def handle_default(x):
    return f"Unhandled type: {type(x).__name__}"
```

## Limitations

Type rules have some limitations to be aware of:

1. **Generic parameters are not checked**: `list[int]` is treated as `list`
2. **No runtime type narrowing**: Types are checked at dispatch time, not throughout execution
3. **Class inheritance**: `isinstance()` semantics apply (subclasses match parent class rules)

For more advanced type checking or runtime validation, consider combining type rules with value rules.

## Next Steps

- Learn about [Value Rules](valrules.md) for runtime condition checking
- Explore [Named Handlers](named-handlers.md) for direct handler access
- See [Real-World Examples](../examples/index.md) for practical use cases
