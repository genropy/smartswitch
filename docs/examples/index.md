# Examples

This section will contain real-world examples of using SmartSwitch.

## Coming Soon

- Data validation and parsing
- API request routing
- Plugin systems
- State machines
- Command pattern implementation

## Basic Example

Here's a simple example to get started:

```python
from smartswitch import Switcher

sw = Switcher()

@sw.typerule(str)
def process(data):
    return f"String: {data}"

@sw.typerule(int)
def process(data):
    return f"Number: {data}"

# Use it
print(sw('process', "hello"))  # String: hello
print(sw('process', 42))        # Number: 42
```

More examples coming soon!
