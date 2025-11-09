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

<!-- test: test_add_method_can_be_used_as_decorator -->
<!-- test: test_complete_workflow -->

Use the `add()` method to organize multiple Switchers within a single class:

```python
from smartswitch import Switcher

class MyAPI:
    # Main switcher
    mainswitch = Switcher(name="main")

    # Add child switchers
    users = mainswitch.add(Switcher(name="users", prefix="user_"))
    posts = mainswitch.add(Switcher(name="posts", prefix="post_"))
    products = mainswitch.add(Switcher(name="products", prefix="product_"))

    @users
    def user_create(self, data):
        """Create a new user."""
        return "user_created"

    @users
    def user_delete(self, user_id):
        """Delete a user."""
        return "user_deleted"

    @posts
    def post_create(self, data):
        """Create a new post."""
        return "post_created"

# Use directly
api = MyAPI()
api.users('create')()  # Direct access
api.posts('create')()

# Or via mainswitch with dot notation
api.mainswitch('users.create')()  # Hierarchical access
api.mainswitch('posts.create')()

# Discover all children
for child in api.mainswitch.children:
    print(f"{child.name}: {child.entries()}")
```

This pattern is useful for:

- **Logical organization** - Group related handlers together in one class
- **Flexible access** - Use child switchers directly or via mainswitch
- **Dot notation** - Navigate with `mainswitch('users.create')`
- **Discovery** - Iterate children to find all registered switchers

## Parent-Child Relationship Management

<!-- test: test_parent_property_setter -->
<!-- test: test_add_child_method -->
<!-- test: test_multiple_children -->
<!-- test: test_recursive_api_discovery_use_case -->

SmartSwitch provides automatic bidirectional parent-child relationship management. When you set a parent, the child is automatically registered with the parent's children.

### Setting Parent Dynamically

```python
from smartswitch import Switcher

# Create independent Switchers
root = Switcher(name="root")
child = Switcher(name="child")

# Set parent dynamically - automatic bidirectional registration
child.parent = root

# Both sides are linked
assert child.parent is root
assert child in root.children
```

### Adding Children

```python
parent = Switcher(name="parent")
child = Switcher(name="child")

# Add child - automatically sets parent
parent.add_child(child)

assert child.parent is parent
assert child in parent.children
```

### Querying Children

<!-- test: test_children_property_returns_copy -->

```python
parent = Switcher(name="parent")
child1 = Switcher(name="child1", parent=parent)
child2 = Switcher(name="child2", parent=parent)

# Get all children
children = parent.children
print(len(children))  # Output: 2

# Iterate children
for child in parent.children:
    print(child.name, child.entries())
```

### Reparenting

<!-- test: test_parent_setter_unregisters_from_old_parent -->
<!-- test: test_reparenting_multiple_times -->

When you change a child's parent, it's automatically unregistered from the old parent:

```python
old_parent = Switcher(name="old")
new_parent = Switcher(name="new")
child = Switcher(name="child", parent=old_parent)

# Change parent
child.parent = new_parent

# Automatically unregistered from old, registered with new
assert child not in old_parent.children
assert child in new_parent.children
```

### Removing Children

<!-- test: test_remove_child_method -->
<!-- test: test_parent_setter_none_unregisters -->

```python
parent = Switcher(name="parent")
child = Switcher(name="child", parent=parent)

# Option 1: Unset parent
child.parent = None

# Option 2: Remove from parent
parent.remove_child(child)

# Both ways unlink the relationship
assert child.parent is None
assert child not in parent.children
```

### Recursive API Discovery

A real-world use case for hierarchical Switchers is discovering all APIs in a system:

```python
# Root API
root_api = Switcher(name="root")

# Handler classes with their own APIs
class UserHandler:
    api = Switcher(name="users", prefix="user_", parent=root_api)

    @api
    def user_list(self):
        return ["alice", "bob"]

    @api
    def user_get(self, name):
        return f"User: {name}"

class PostHandler:
    api = Switcher(name="posts", prefix="post_", parent=root_api)

    @api
    def post_list(self):
        return ["post1", "post2"]

    @api
    def post_create(self, title):
        return f"Created: {title}"

# Discovery: iterate all children
for child in root_api.children:
    print(f"\n{child.name} API:")
    for handler_name in child.entries():
        print(f"  - {handler_name}")

# Output:
# users API:
#   - list
#   - get
# posts API:
#   - list
#   - create
```

This pattern enables:

- **Automatic API registration** - Handlers register themselves on creation
- **Framework introspection** - Tools can discover all available APIs
- **Documentation generation** - Generate docs from the hierarchy
- **Testing utilities** - Find and test all handlers automatically

## API Reference

### Methods

- `Switcher.entries()` - List registered handler names
- `Switcher.add_child(switcher)` - Add a child Switcher (sets parent automatically)
- `Switcher.remove_child(switcher)` - Remove a child Switcher (unsets parent)

### Properties

- `Switcher.parent` - Get or set parent Switcher (bidirectional)
- `Switcher.children` - Get set of child Switchers (read-only copy)
