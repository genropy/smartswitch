# SmartSwitch vs Match: A Comprehensive Comparison

Let's compare SmartSwitch with Python 3.10+'s new `match` statement (structural pattern matching).

## Match (Structural Pattern Matching)

**Strengths:**
- **Language native** - zero overhead, compiler-optimized
- **Powerful structural patterns** - destructuring, guard clauses, type patterns
- **Exhaustiveness checking** - compiler can verify all cases are covered
- **Very fast** - bytecode-level implementation

**Limitations:**
- **Static** - conditions must be expressed inline in code
- **Not extensible** - can't add cases at runtime
- **Coupling** - dispatch logic and implementation in the same place
- **Value-focused** - difficult to express complex conditions

## SmartSwitch

**Strengths:**
- **Dynamic** - register handlers at runtime, even from different modules
- **Separation of concerns** - dispatcher and handlers are separate
- **Rich conditions** - `valrule` can express arbitrary complex logic
- **Extensible** - plugins can register their own handlers
- **Named registry** - invoke handlers by name
- **Type checking + value checking** - powerful combination

**Limitations:**
- **Dispatch overhead** - ~1-2μs (negligible for real operations)
- **Not native** - external dependency
- **More verbose** - requires decorators and setup

## When to Use Match

```python
# ✅ Great for: structural pattern matching
def process_command(cmd):
    match cmd:
        case ["quit"]:
            return "bye"
        case ["load", filename]:
            return load_file(filename)
        case ["save", filename, *data]:
            return save_file(filename, data)
        case _:
            return "unknown"

# ✅ Great for: simple type patterns
def handle_response(resp):
    match resp:
        case int(x) if x > 0:
            print(f"Success: {x}")
        case int(x) if x == 0:
            print("No results")
        case str(msg):
            print(f"Error: {msg}")
```

## When to Use SmartSwitch

```python
# ✅ Great for: complex type-based dispatch
from smartswitch import Switcher

api = Switcher()

@api(typerule={'data': dict, 'format': str})
def handle(data, format):
    """Handle dict + format string"""
    return serialize(data, format)

@api(typerule={'items': list, 'format': str})
def handle(items, format):
    """Handle list + format string"""
    return serialize_list(items, format)

# ✅ Great for: complex runtime conditions
validator = Switcher()

@validator(valrule=lambda user: user.is_admin())
def validate(user, action):
    return True  # Admins can do anything

@validator(valrule=lambda user, action: action.requires_permission(user))
def validate(user, action):
    return user.has_permission(action)

# ✅ Great for: plugin architectures
# Plugin 1
@api(typerule={'doc': PDFDocument})
def process(doc):
    return process_pdf(doc)

# Plugin 2 (different module)
@api(typerule={'doc': WordDocument})
def process(doc):
    return process_word(doc)
```

## Head-to-Head: API Router

### With Match

```python
def route_api(method: str, path: str, body: dict):
    match (method, path):
        case ("GET", "/users"):
            return list_users()
        case ("GET", path) if path.startswith("/users/"):
            user_id = path.split("/")[-1]
            return get_user(user_id)
        case ("POST", "/users"):
            return create_user(body)
        case ("PUT", path) if path.startswith("/users/"):
            user_id = path.split("/")[-1]
            return update_user(user_id, body)
        case _:
            return {"error": "Not found"}, 404
```

**Pros:**
- Concise for simple cases
- Everything visible in one place
- Fast

**Cons:**
- Becomes unwieldy with many routes
- Inline path parsing is awkward
- Not modular (can't separate by modules)

### With SmartSwitch

```python
from smartswitch import Switcher

router = Switcher()

@router(valrule=lambda method, path: method == "GET" and path == "/users")
def route(method, path, body=None):
    return list_users()

@router(valrule=lambda method, path: method == "GET" and path.startswith("/users/"))
def route(method, path, body=None):
    user_id = path.split("/")[-1]
    return get_user(user_id)

@router(valrule=lambda method, path: method == "POST" and path == "/users")
def route(method, path, body):
    return create_user(body)

# Other modules can register their own routes
@router(valrule=lambda method, path: method == "GET" and path == "/products")
def route(method, path, body=None):
    return list_products()
```

**Pros:**
- Modular - handlers can be in different files
- Extensible - plugins can add routes
- Each handler is independently testable
- Separation of concerns

**Cons:**
- More verbose
- Minimal overhead (~1μs, negligible for APIs)

## Combining Both Approaches

**The best approach is often to use both!**

```python
from smartswitch import Switcher

router = Switcher()

# SmartSwitch for high-level dispatch (request type)
@router(typerule={'request': HTTPRequest})
def handle(request: HTTPRequest):
    # Match for internal routing (structural patterns)
    match (request.method, request.path):
        case ("GET", path) if path.startswith("/api/"):
            return handle_api_get(request)
        case ("POST", path) if path.startswith("/api/"):
            return handle_api_post(request)
        case _:
            return 404

@router(typerule={'request': WebSocketRequest})
def handle(request: WebSocketRequest):
    # Match for message type
    match request.message:
        case {"type": "subscribe", "channel": channel}:
            return subscribe(channel)
        case {"type": "publish", "channel": channel, "data": data}:
            return publish(channel, data)
```

## Quick Benchmark

```python
# Match: ~0.05μs (virtually instantaneous)
match value:
    case 1: return "one"
    case 2: return "two"

# SmartSwitch: ~1-2μs (negligible for real work)
@sw(valrule=lambda x: x == 1)
def handle(x): return "one"
```

**Performance conclusion:**
- For functions doing real work (>1ms), SmartSwitch overhead is **irrelevant**
- For tight loops on very fast functions (<10μs), prefer `match`

## Recommendations

| Scenario | Use Match | Use SmartSwitch |
|----------|-----------|-----------------|
| Structural pattern matching | ✅ | ❌ |
| Simple value conditions | ✅ | ❌ |
| Performance critical (<10μs) | ✅ | ❌ |
| Type-based dispatch | ❌ | ✅ |
| Complex runtime conditions | ❌ | ✅ |
| Plugin/modular architecture | ❌ | ✅ |
| Dynamic registry | ❌ | ✅ |
| API routing | ⚠️ | ✅ |
| Event handling | ⚠️ | ✅ |

## Real-World Examples

### Example 1: Data Processing Pipeline

**With Match (good for simple cases):**
```python
def process_data(data):
    match data:
        case {"type": "user", "id": user_id, "name": name}:
            return User(user_id, name)
        case {"type": "order", "id": order_id, "items": items}:
            return Order(order_id, items)
        case {"type": "product", **rest}:
            return Product(**rest)
        case _:
            raise ValueError("Unknown data type")
```

**With SmartSwitch (better for extensibility):**
```python
processor = Switcher()

@processor(valrule=lambda data: data.get("type") == "user")
def process(data):
    return User(data["id"], data["name"])

@processor(valrule=lambda data: data.get("type") == "order")
def process(data):
    return Order(data["id"], data["items"])

# External plugin can add new types
@processor(valrule=lambda data: data.get("type") == "subscription")
def process(data):
    return Subscription(data["plan"], data["user_id"])
```

### Example 2: Command Handler

**With Match:**
```python
def execute_command(cmd):
    match cmd.split():
        case ["help"]:
            return show_help()
        case ["list", category]:
            return list_items(category)
        case ["create", item_type, *args]:
            return create_item(item_type, args)
        case _:
            return "Unknown command"
```

**With SmartSwitch:**
```python
commands = Switcher()

@commands(valrule=lambda cmd: cmd.startswith("help"))
def execute(cmd):
    return show_help()

@commands(valrule=lambda cmd: cmd.startswith("list "))
def execute(cmd):
    _, category = cmd.split(maxsplit=1)
    return list_items(category)

# Plugins can add commands
@commands(valrule=lambda cmd: cmd.startswith("deploy "))
def execute(cmd):
    _, target = cmd.split(maxsplit=1)
    return deploy_to(target)
```

### Example 3: Type Conversion

**With Match (excellent for this use case):**
```python
def convert(value, target_type):
    match (value, target_type):
        case (str(s), "int"):
            return int(s)
        case (str(s), "float"):
            return float(s)
        case (int(i), "str"):
            return str(i)
        case (list(items), "tuple"):
            return tuple(items)
        case _:
            raise ValueError(f"Can't convert {type(value)} to {target_type}")
```

**With SmartSwitch (overkill for this):**
```python
# Don't do this - match is better here!
converter = Switcher()

@converter(typerule={'value': str, 'target_type': str})
def convert(value, target_type):
    if target_type == "int":
        return int(value)
    elif target_type == "float":
        return float(value)
    # ...
```

## Decision Tree

```
Need dispatch logic?
│
├─ All cases known at write-time?
│  └─ YES → Structural patterns involved?
│     ├─ YES → Use Match ✅
│     └─ NO → Simple conditions?
│        ├─ YES → Use Match ✅
│        └─ NO → Consider SmartSwitch
│
└─ NO → Runtime registration needed?
   └─ YES → Use SmartSwitch ✅
```

## Conclusion

**Match and SmartSwitch are not competitors - they solve different problems:**

- **Match** → Structural pattern matching, fast, static, language-integrated
- **SmartSwitch** → Dynamic dispatch, extensible, modular, for complex architectures

**Rule of thumb:**
- If your code fits in one function and patterns are simple → **Match**
- If you need modularity, extensibility, or complex dispatch → **SmartSwitch**
- For hybrid systems → **use both**!

## Key Differences Summary

| Feature | Match | SmartSwitch |
|---------|-------|-------------|
| Speed | ~0.05μs | ~1-2μs |
| Structural patterns | ✅ Excellent | ❌ Not supported |
| Type dispatch | ⚠️ Basic | ✅ Excellent |
| Runtime registration | ❌ No | ✅ Yes |
| Plugin architecture | ❌ No | ✅ Yes |
| Guard clauses | ✅ Yes | ✅ Yes (in lambda) |
| Named handlers | ❌ No | ✅ Yes |
| Exhaustiveness check | ✅ Possible | ❌ No |
| Learning curve | Low | Medium |
| Dependencies | None | smartswitch |
