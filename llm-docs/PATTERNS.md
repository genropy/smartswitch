# SmartSwitch - Real-World Patterns

## API Request Routing

### HTTP Method + Path Dispatch
```python
api = Switcher()

@api(valrule=lambda method, path: method == 'GET' and path.startswith('/users'))
def list_users(method, path, **kw):
    return {"users": [...]}

@api(valrule=lambda method, path: method == 'POST' and path == '/users')
def create_user(method, path, data):
    return {"created": data['name']}

@api(valrule=lambda method, path: method == 'DELETE' and path.startswith('/users/'))
def delete_user(method, path):
    user_id = path.split('/')[-1]
    return {"deleted": user_id}

@api  # 404 fallback
def not_found(method, path, **kw):
    return {"error": "Not Found", "status": 404}

# Usage
api()('GET', '/users')              # → list_users
api()('POST', '/users', data={...}) # → create_user
api()('GET', '/unknown')            # → not_found
```

## Payment Processing

### Amount + Method Dispatch
```python
payments = Switcher()

@payments(
    typerule={'amount': int | float},
    valrule=lambda method, amount: method == 'crypto' and amount > 1000
)
def process_large_crypto(method, amount, details):
    return {"processor": "crypto_large", "fee": amount * 0.01}

@payments(valrule=lambda method: method == 'credit_card')
def process_card(method, amount, details):
    return {"processor": "stripe", "fee": amount * 0.03}

@payments(valrule=lambda method: method == 'wire')
def process_wire(method, amount, details):
    return {"processor": "bank", "fee": 25.0}

@payments
def unsupported_method(method, amount, details):
    return {"error": "Unsupported payment method"}
```

## File Format Handlers

### Extension-Based Dispatch
```python
parsers = Switcher()

@parsers(valrule=lambda filepath: filepath.endswith('.json'))
def parse_json(filepath):
    import json
    with open(filepath) as f:
        return json.load(f)

@parsers(valrule=lambda filepath: filepath.endswith(('.yml', '.yaml')))
def parse_yaml(filepath):
    import yaml
    with open(filepath) as f:
        return yaml.safe_load(f)

@parsers(valrule=lambda filepath: filepath.endswith('.csv'))
def parse_csv(filepath):
    import csv
    with open(filepath) as f:
        return list(csv.DictReader(f))

@parsers
def parse_text(filepath):
    with open(filepath) as f:
        return f.read()

# Usage
data = parsers()('/path/to/config.json')
data = parsers()('/path/to/data.csv')
```

## State Machine

### Status-Based Transitions
```python
workflow = Switcher()

@workflow(valrule=lambda current_state: current_state == 'draft')
def submit_for_review(current_state, doc):
    doc['state'] = 'review'
    return doc

@workflow(valrule=lambda current_state, approved: 
          current_state == 'review' and approved)
def approve(current_state, doc, approved):
    doc['state'] = 'approved'
    return doc

@workflow(valrule=lambda current_state, approved: 
          current_state == 'review' and not approved)
def reject(current_state, doc, approved):
    doc['state'] = 'draft'
    doc['feedback'] = "Needs revision"
    return doc

@workflow(valrule=lambda current_state: current_state == 'approved')
def publish(current_state, doc):
    doc['state'] = 'published'
    doc['published_at'] = time.time()
    return doc
```

## Plugin System

### Plugin Type Dispatch
```python
plugins = Switcher()

@plugins(typerule={'plugin': ImagePlugin})
def handle_image(plugin, data):
    return plugin.process_image(data)

@plugins(typerule={'plugin': VideoPlugin})
def handle_video(plugin, data):
    return plugin.process_video(data)

@plugins(typerule={'plugin': AudioPlugin})
def handle_audio(plugin, data):
    return plugin.process_audio(data)

# Usage
result = plugins()(plugin=my_image_plugin, data=image_data)
```

## Multi-Tenant Routing

### Tenant-Aware Dispatch
```python
handlers = Switcher()

@handlers(valrule=lambda tenant_id: tenant_id in ENTERPRISE_TENANTS)
def handle_enterprise(tenant_id, request):
    # Enterprise features + priority support
    return process_with_sla(request, sla_tier='gold')

@handlers(valrule=lambda tenant_id: tenant_id in PREMIUM_TENANTS)
def handle_premium(tenant_id, request):
    return process_with_sla(request, sla_tier='silver')

@handlers
def handle_free(tenant_id, request):
    return process_basic(request)

# Usage
result = handlers()(tenant_id='acme_corp', request=req)
```

## Complex Rule Combinations

### Multiple Condition Checks
```python
orders = Switcher()

@orders(
    typerule={'amount': int | float, 'items': list},
    valrule=lambda region, amount, items: 
        region == 'EU' and amount > 100 and len(items) > 5
)
def process_eu_bulk(region, amount, items):
    return {"discount": 0.15, "shipping": "free"}

@orders(
    valrule=lambda region, amount: region == 'EU' and amount > 100
)
def process_eu_high_value(region, amount, items):
    return {"discount": 0.10, "shipping": "free"}

@orders(valrule=lambda region: region == 'EU')
def process_eu_normal(region, amount, items):
    return {"discount": 0.05, "shipping": 9.99}

@orders
def process_rest_of_world(region, amount, items):
    return {"discount": 0, "shipping": 19.99}
```

## Hierarchical API (Production Pattern)

### Organized Multi-Domain API
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
    @orders(valrule=lambda status: status == 'pending')
    def order_process_pending(self, order_id, status):
        return process_order(order_id)
    
    @orders
    def order_get(self, order_id):
        return db.orders.get(order_id)

# Usage
api = ProductionAPI()

# Direct access
api.users('list')(filters={'active': True})

# Hierarchical access
api.api('users.list')(filters={'active': True})
api.api('products.search')(query="laptop")
api.api('orders.get')(order_id=123)

# Introspection
api.api.entries()              # ['users', 'products', 'orders']
api.users.entries()            # ['list', 'create', 'update']
for child in api.api.children:
    print(f"{child.name}: {child.entries()}")
```

## Validation Pattern

### Pre-Validation with Rules
```python
validators = Switcher()

@validators(
    typerule={'email': str, 'age': int},
    valrule=lambda age, email: age >= 18 and '@' in email
)
def validate_adult_registration(email, age, **kw):
    return {"valid": True, "tier": "adult"}

@validators(
    typerule={'email': str, 'age': int},
    valrule=lambda age: 13 <= age < 18
)
def validate_teen_registration(email, age, **kw):
    return {"valid": True, "tier": "teen", "requires_consent": True}

@validators
def reject_registration(email, age, **kw):
    return {"valid": False, "error": "Invalid registration"}

# Usage
result = validators()(email="user@example.com", age=25)
```

## Best Practices

1. **Rule Specificity**: Order rules from most specific to least specific
2. **Always Have Default**: Use `@sw` (no rules) as fallback
3. **Compact valrules**: Use `lambda kw: kw['x'] > 10` for clarity
4. **Type Unions**: Use `int | str` for Python 3.10+
5. **Naming Convention**: Use prefix for auto-derived names
6. **Hierarchical APIs**: Organize related handlers in child Switchers
7. **Testing**: Each handler is a pure function - easy to unit test

## Performance Tips

- Rules evaluated in registration order (first match wins)
- Type checks cached after first use (~2μs overhead)
- Default handler bypasses rule evaluation (fastest path)
- For ultra-hot paths (<10μs functions), use direct function calls
