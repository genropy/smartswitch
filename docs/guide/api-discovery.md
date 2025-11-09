# API Discovery and Introspection

SmartSwitch provides basic features for inspecting and organizing your handler registries. These are primarily useful for building frameworks and tools that need runtime introspection.

> **For production examples**, see [smpub](https://github.com/genropy/smpub) - a CLI/API framework built on SmartSwitch that demonstrates advanced usage patterns.

## Listing Registered Handlers

<!-- test: test_entries_empty_switcher -->
<!-- test: test_entries_with_simple_decorator -->

Use the `entries()` method to get a list of all registered handler names:

```python
from smartswitch import Switcher

api = Switcher()

@api
def save_user(name, email):
    """Save a user to the database."""
    pass

@api
def delete_user(user_id):
    """Delete a user from the database."""
    pass

# List all registered handlers
handlers = api.entries()
print(handlers)  # Output: ['save_user', 'delete_user']
```

### With Prefix Stripping

<!-- test: test_entries_with_prefix -->

When using prefix auto-stripping, `entries()` returns the stripped names:

```python
api = Switcher(prefix="api_")

@api
def api_create(data):
    pass

@api
def api_delete(id):
    pass

# Returns stripped names
print(api.entries())  # Output: ['create', 'delete']
```

## Organizing Multiple Switchers

<!-- test: test_switcher_parent_parameter -->
<!-- test: test_parent_hierarchy -->

Use the `parent` parameter to organize multiple Switchers in the same class:

```python
from smartswitch import Switcher

class MyAPI:
    # Main aggregator
    main = Switcher(name="main")

    # Logical groupings with parent reference
    users = Switcher(name="users", parent=main)
    posts = Switcher(name="posts", parent=main)
    comments = Switcher(name="comments", parent=main)

    @users
    def create_user(self, data):
        """Create a new user."""
        pass

    @users
    def delete_user(self, user_id):
        """Delete a user."""
        pass

    @posts
    def create_post(self, data):
        """Create a new post."""
        pass

# Inspect each area independently
api = MyAPI()
print(api.users.entries())    # ['create_user', 'delete_user']
print(api.posts.entries())    # ['create_post']

# Navigate hierarchy
assert api.users.parent is MyAPI.main
```

This pattern is useful for:
- **Logical organization** - Group related handlers together
- **Selective introspection** - Query specific functional areas
- **Framework building** - Tools can discover and traverse the structure

## API Reference

- `Switcher.entries()` - List registered handler names
- `Switcher.parent` - Access parent Switcher
