# SmartSwitch - LLM Quick Reference

## Core Purpose
Intelligent rule-based function dispatch replacing if-elif chains with declarative rules. Supports type-based, value-based, and named dispatch with ~2μs overhead.

## Installation
```bash
pip install smartswitch
```

## Essential Patterns

### 1. Named Dispatch (Most Common)
```python
from smartswitch import Switcher

ops = Switcher()

@ops  # Auto-registers as 'save_data'
def save_data(data):
    return f"Saved: {data}"

@ops('custom_name')  # Register with alias
def process(data):
    return f"Processed: {data}"

# Call by name
result = ops('save_data')(data)
result = ops('custom_name')(data)
```

### 2. Value-Based Dispatch
```python
users = Switcher()

@users(valrule=lambda user_type, reason: 
       user_type == 'admin' and reason == 'urgent')
def escalate(user_type, reason):
    return "Escalated"

@users(valrule=lambda reason: reason == 'urgent')
def prioritize(user_type, reason):
    return "Priority"

@users  # Default fallback
def handle_normal(user_type, reason):
    return "Normal"

# Automatic dispatch by rules
result = users()(user_type='admin', reason='urgent')  # → escalate()
result = users()(user_type='user', reason='urgent')   # → prioritize()
```

### 3. Type-Based Dispatch
```python
processor = Switcher()

@processor(typerule={'data': str})
def process_string(data):
    return data.upper()

@processor(typerule={'data': int})
def process_number(data):
    return data * 2

@processor(typerule={'data': list})
def process_list(data):
    return len(data)

# Automatic dispatch by type
processor()(data="hello")  # → HELLO
processor()(data=42)       # → 84
processor()(data=[1,2,3])  # → 3
```

### 4. Hierarchical Structure (API Organization)
```python
class MyAPI:
    root = Switcher(name="api")
    users = root.add(Switcher(name="users", prefix="user_"))
    products = root.add(Switcher(name="products", prefix="product_"))
    
    @users
    def user_list(self): 
        return ["alice", "bob"]
    
    @products
    def product_list(self): 
        return ["laptop", "phone"]

api = MyAPI()
api.users('list')()              # Direct
api.root('users.list')()         # Via hierarchy
```

### 5. Prefix-Based Auto-Naming
```python
handlers = Switcher(prefix='handle_')

@handlers  # Auto-registers as 'payment'
def handle_payment(amount):
    return f"Processing ${amount}"

@handlers  # Auto-registers as 'refund'
def handle_refund(amount):
    return f"Refunding ${amount}"

handlers('payment')(100)
```

## Method Binding (Class Usage)
```python
class Service:
    ops = Switcher()
    
    @ops
    def save(self, data):
        return f"Saved by {self.name}"
    
    def __init__(self, name):
        self.name = name

svc = Service("DB")
svc.ops('save')("data")  # 'self' bound automatically
```

## Critical Rules

1. **Decorator registration** = module-level (thread-safe)
2. **Handler dispatch** = runtime (fully thread-safe)
3. **Rule priority**: specific rules → default handler
4. **valrule calling**:
   - Expanded: `lambda x, y: x > 10` 
   - Compact dict: `lambda kw: kw['x'] > 10`
   - Compact unpack: `lambda **kw: kw.get('x') > 10`

## Common Anti-Patterns

❌ **Don't**: Runtime decorator registration in threads
❌ **Don't**: Use for 2-3 simple cases (use if/elif)
❌ **Don't**: For pure type dispatch (use singledispatch)

✅ **Do**: API routers, business logic, extensible systems
✅ **Do**: When combining type + value rules
✅ **Do**: Plugin architectures

## Quick Introspection
```python
sw = Switcher(name="api")
sw.entries()        # List all handler names
sw.children         # Set of child Switchers
sw.parent           # Parent Switcher or None
```

## Advanced Features
See additional files in llm-docs/:
- **LOGGING.md**: History tracking, performance analysis (v0.4.0)
- **API-DETAILS.md**: Complete API reference
- **PATTERNS.md**: Real-world usage patterns

## Version
Current: 0.4.0 (Python 3.10+)

## Performance
~2μs dispatch overhead. Negligible for typical business logic (DB, API calls, etc.)

## Quick Troubleshooting

**"No rule matched"**: Add default handler with `@sw` (no rules)
**Name collision**: Use custom aliases `@sw('unique_name')`
**Type not matching**: Check Union syntax: `int | str` not `Union[int, str]`
