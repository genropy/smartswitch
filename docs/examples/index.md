# Examples

Real-world examples of using SmartSwitch in various scenarios.

## Basic Example

A simple demonstration of SmartSwitch basics:

```python
from smartswitch import Switcher

sw = Switcher()

@sw(typerule={'data': str})
def process(data):
    return f"String: {data}"

@sw(typerule={'data': int})
def process(data):
    return f"Number: {data}"

@sw(typerule={'data': list})
def process(data):
    return f"List with {len(data)} items"

@sw
def process(data):
    return f"Unknown: {type(data).__name__}"

# Use it
print(sw()(data="hello"))    # String: hello
print(sw()(data=42))         # Number: 42
print(sw()(data=[1,2,3]))    # List with 3 items
print(sw()(data=3.14))       # Unknown: float
```

## API Request Router

Route HTTP requests based on method and path:

```python
from smartswitch import Switcher

api = Switcher()

@api(valrule=lambda method, path: method == 'GET' and path == '/users')
def handle_request(method, path, data=None):
    return {"action": "list_users"}

@api(valrule=lambda method, path: method == 'POST' and path == '/users')
def handle_request(method, path, data=None):
    return {"action": "create_user", "data": data}

@api(valrule=lambda method, path: method == 'GET' and path.startswith('/users/'))
def handle_request(method, path, data=None):
    user_id = path.split('/')[-1]
    return {"action": "get_user", "id": user_id}

@api(valrule=lambda method, path: method == 'DELETE' and path.startswith('/users/'))
def handle_request(method, path, data=None):
    user_id = path.split('/')[-1]
    return {"action": "delete_user", "id": user_id}

@api
def handle_request(method, path, data=None):
    return {"error": "Not Found", "status": 404}

# Use it
print(api()(method='GET', path='/users'))
# {'action': 'list_users'}

print(api()(method='POST', path='/users', data={'name': 'Alice'}))
# {'action': 'create_user', 'data': {'name': 'Alice'}}

print(api()(method='GET', path='/users/123'))
# {'action': 'get_user', 'id': '123'}

print(api()(method='GET', path='/products'))
# {'error': 'Not Found', 'status': 404}
```

## Data Validation

Validate different types of input data:

```python
from smartswitch import Switcher

validator = Switcher()

# Email validation
@validator(typerule={'value': str},
           valrule=lambda value: '@' in value and '.' in value.split('@')[1])
def validate(value):
    return {"valid": True, "type": "email", "value": value}

# Phone number validation (simple)
@validator(typerule={'value': str},
           valrule=lambda value: value.replace('-', '').replace(' ', '').isdigit())
def validate(value):
    return {"valid": True, "type": "phone", "value": value}

# Integer in range
@validator(typerule={'value': int},
           valrule=lambda value: 0 <= value <= 100)
def validate(value):
    return {"valid": True, "type": "percentage", "value": value}

# Positive number
@validator(typerule={'value': int | float},
           valrule=lambda value: value > 0)
def validate(value):
    return {"valid": True, "type": "positive_number", "value": value}

# Default - invalid
@validator
def validate(value):
    return {"valid": False, "type": "unknown", "value": value}

# Use it
print(validator()(value="user@example.com"))
# {'valid': True, 'type': 'email', 'value': 'user@example.com'}

print(validator()(value="555-1234"))
# {'valid': True, 'type': 'phone', 'value': '555-1234'}

print(validator()(value=75))
# {'valid': True, 'type': 'percentage', 'value': 75}

print(validator()(value=150))
# {'valid': True, 'type': 'positive_number', 'value': 150}

print(validator()(value=[1, 2, 3]))
# {'valid': False, 'type': 'unknown', 'value': [1, 2, 3]}
```

## Payment Processing

Handle different payment methods with different rules:

```python
from smartswitch import Switcher

payments = Switcher()

# Crypto payments over $1000
@payments(typerule={'method': str, 'amount': int | float},
          valrule=lambda method, amount: method == 'crypto' and amount > 1000)
def process_payment(method, amount, details):
    return {
        "processor": "crypto_large",
        "amount": amount,
        "fee": amount * 0.01,  # 1% fee
        "details": details
    }

# Regular crypto payments
@payments(typerule={'method': str},
          valrule=lambda method, **kw: method == 'crypto')
def process_payment(method, amount, details):
    return {
        "processor": "crypto_regular",
        "amount": amount,
        "fee": amount * 0.02,  # 2% fee
        "details": details
    }

# Credit card payments
@payments(valrule=lambda method, **kw: method == 'credit_card')
def process_payment(method, amount, details):
    return {
        "processor": "credit_card",
        "amount": amount,
        "fee": amount * 0.03,  # 3% fee
        "details": details
    }

# Bank transfer
@payments(valrule=lambda method, **kw: method == 'bank_transfer')
def process_payment(method, amount, details):
    return {
        "processor": "bank_transfer",
        "amount": amount,
        "fee": 0,  # No fee
        "details": details
    }

# Default - unsupported
@payments
def process_payment(method, amount, details):
    return {"error": "Unsupported payment method", "method": method}

# Use it
print(payments()(method='crypto', amount=2000, details={'wallet': '0x123'}))
# {'processor': 'crypto_large', 'amount': 2000, 'fee': 20.0, ...}

print(payments()(method='crypto', amount=500, details={'wallet': '0x456'}))
# {'processor': 'crypto_regular', 'amount': 500, 'fee': 10.0, ...}

print(payments()(method='credit_card', amount=100, details={'card': '****1234'}))
# {'processor': 'credit_card', 'amount': 100, 'fee': 3.0, ...}

print(payments()(method='paypal', amount=50, details={}))
# {'error': 'Unsupported payment method', 'method': 'paypal'}
```

## State Machine

Implement a simple state machine for order processing:

```python
from smartswitch import Switcher

order_processor = Switcher()

@order_processor(valrule=lambda state, action: state == 'pending' and action == 'confirm')
def process_order(state, action, order_id):
    return {
        "order_id": order_id,
        "old_state": state,
        "new_state": "confirmed",
        "message": "Order confirmed"
    }

@order_processor(valrule=lambda state, action: state == 'confirmed' and action == 'ship')
def process_order(state, action, order_id):
    return {
        "order_id": order_id,
        "old_state": state,
        "new_state": "shipped",
        "message": "Order shipped"
    }

@order_processor(valrule=lambda state, action: state == 'shipped' and action == 'deliver')
def process_order(state, action, order_id):
    return {
        "order_id": order_id,
        "old_state": state,
        "new_state": "delivered",
        "message": "Order delivered"
    }

@order_processor(valrule=lambda state, action: action == 'cancel')
def process_order(state, action, order_id):
    return {
        "order_id": order_id,
        "old_state": state,
        "new_state": "cancelled",
        "message": "Order cancelled"
    }

@order_processor
def process_order(state, action, order_id):
    return {
        "order_id": order_id,
        "error": f"Invalid transition: {state} -> {action}"
    }

# Use it
result = order_processor()(state='pending', action='confirm', order_id='ORD-123')
print(result)
# {'order_id': 'ORD-123', 'old_state': 'pending', 'new_state': 'confirmed', ...}

result = order_processor()(state='confirmed', action='ship', order_id='ORD-123')
print(result)
# {'order_id': 'ORD-123', 'old_state': 'confirmed', 'new_state': 'shipped', ...}

result = order_processor()(state='pending', action='ship', order_id='ORD-456')
print(result)
# {'order_id': 'ORD-456', 'error': 'Invalid transition: pending -> ship'}
```

## Command Pattern

Implement an undo/redo system:

```python
from smartswitch import Switcher

commands = Switcher()

# Document editing commands
@commands
def insert_text(doc, pos, text):
    """Insert text at position."""
    doc['content'] = doc['content'][:pos] + text + doc['content'][pos:]
    return {
        'undo': 'delete_text',
        'args': (doc, pos, len(text))
    }

@commands
def delete_text(doc, pos, length):
    """Delete text from position."""
    deleted = doc['content'][pos:pos+length]
    doc['content'] = doc['content'][:pos] + doc['content'][pos+length:]
    return {
        'undo': 'insert_text',
        'args': (doc, pos, deleted)
    }

# Use it
doc = {'content': 'Hello World'}

# Execute command
cmd = commands('insert_text')
undo_info = cmd(doc, 5, ' Beautiful')
print(doc['content'])  # Hello Beautiful World

# Undo using returned info
undo_cmd = commands(undo_info['undo'])
undo_cmd(*undo_info['args'])
print(doc['content'])  # Hello World
```

## File Format Parser

Parse different file formats based on extension and content:

```python
from smartswitch import Switcher
import json

parser = Switcher()

@parser(typerule={'filepath': str},
        valrule=lambda filepath: filepath.endswith('.json'))
def parse_file(filepath):
    with open(filepath, 'r') as f:
        return {"type": "json", "data": json.load(f)}

@parser(typerule={'filepath': str},
        valrule=lambda filepath: filepath.endswith('.txt'))
def parse_file(filepath):
    with open(filepath, 'r') as f:
        return {"type": "text", "data": f.read()}

@parser(typerule={'filepath': str},
        valrule=lambda filepath: filepath.endswith('.csv'))
def parse_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
        return {"type": "csv", "data": [line.strip().split(',') for line in lines]}

@parser
def parse_file(filepath):
    return {"type": "unknown", "error": f"Unsupported file type: {filepath}"}

# Use it (assuming files exist)
# result = parser()(filepath='data.json')
# result = parser()(filepath='document.txt')
# result = parser()(filepath='data.csv')
```

## More Examples Coming Soon

- Plugin systems
- Event handlers
- Strategy pattern implementation
- Data transformation pipelines
- Multi-tenant request routing

For more patterns and techniques, see the [Basic Usage Guide](../user-guide/basic.md).
