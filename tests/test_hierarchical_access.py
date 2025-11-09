"""
Tests for hierarchical access features:
- add() method that returns child
- Dot notation for accessing handlers through hierarchy
"""

import pytest
from smartswitch import Switcher


def test_add_method_returns_child():
    """Test that add() returns the child for assignment."""
    parent = Switcher(name="parent")
    child = parent.add(Switcher(name="child"))

    assert child.parent is parent
    assert child in parent.children
    assert child.name == "child"


def test_add_method_can_be_used_as_decorator():
    """Test that returned child can be used as decorator."""
    mainswitch = Switcher(name="main")
    users = mainswitch.add(Switcher(name="users", prefix="user_"))

    @users
    def user_create():
        return "user_created"

    # Handler should be registered in child
    assert 'create' in users.entries()
    assert users('create')() == "user_created"


def test_dot_notation_basic():
    """Test basic dot notation for accessing handlers."""
    mainswitch = Switcher(name="main")
    users = mainswitch.add(Switcher(name="users", prefix="user_"))

    @users
    def user_list():
        return "user_list"

    # Access via dot notation
    handler = mainswitch('users.list')
    assert handler() == "user_list"


def test_dot_notation_multiple_levels():
    """Test dot notation with multiple levels of hierarchy."""
    root = Switcher(name="root")
    level1 = root.add(Switcher(name="level1"))
    level2 = level1.add(Switcher(name="level2"))

    @level2
    def my_handler():
        return "deep"

    # Access through hierarchy
    handler = root('level1.level2.my_handler')
    assert handler() == "deep"


def test_dot_notation_with_arguments():
    """Test dot notation with handler that takes arguments."""
    mainswitch = Switcher(name="main")
    products = mainswitch.add(Switcher(name="products", prefix="product_"))

    @products
    def product_calculate_price(quantity, unit_price):
        return quantity * unit_price

    # Access and call
    result = mainswitch('products.calculate_price')(10, 5.50)
    assert result == 55.0


def test_dot_notation_child_not_found():
    """Test that dot notation raises KeyError if child not found."""
    mainswitch = Switcher(name="main")
    users = mainswitch.add(Switcher(name="users"))

    with pytest.raises(KeyError, match="Child Switcher 'nonexistent' not found"):
        mainswitch('nonexistent.handler')


def test_dot_notation_handler_not_found():
    """Test that dot notation returns decorator for nonexistent handler."""
    mainswitch = Switcher(name="main")
    users = mainswitch.add(Switcher(name="users"))

    @users
    def existing_handler():
        return "exists"

    # Child exists, but handler doesn't - should return decorator for registration
    result = mainswitch('users.nonexistent')
    assert callable(result)  # It's a decorator function


def test_complete_workflow():
    """Test complete workflow with add() and dot notation."""

    class MyAPI:
        mainswitch = Switcher(name="main")

        # Add children using add()
        users = mainswitch.add(Switcher(name="users", prefix="user_"))
        products = mainswitch.add(Switcher(name="products", prefix="product_"))

        @users
        def user_list(self):
            return "users_list"

        @users
        def user_create(self):
            return "user_created"

        @products
        def product_list(self):
            return "products_list"

    api = MyAPI()

    # Direct access (still works)
    assert api.users('list')() == "users_list"
    assert api.products('list')() == "products_list"

    # Hierarchical access via mainswitch
    assert api.mainswitch('users.list')() == "users_list"
    assert api.mainswitch('users.create')() == "user_created"
    assert api.mainswitch('products.list')() == "products_list"


def test_add_method_backward_compatible():
    """Test that add_child() still works (backward compatibility)."""
    parent = Switcher(name="parent")
    child = Switcher(name="child")

    returned = parent.add_child(child)

    assert returned is child
    assert child.parent is parent
    assert child in parent.children


def test_mixed_add_methods():
    """Test mixing add() and add_child()."""
    parent = Switcher(name="parent")

    child1 = parent.add(Switcher(name="child1"))
    child2 = parent.add_child(Switcher(name="child2"))

    assert child1 in parent.children
    assert child2 in parent.children
    assert len(parent.children) == 2


def test_dot_notation_with_bound_switcher():
    """Test dot notation works with instance methods (BoundSwitcher)."""

    class ShoppingCart:
        mainswitch = Switcher(name="main")
        items = mainswitch.add(Switcher(name="items", prefix="item_"))

        @items
        def item_count(self):
            return self.item_total

        def __init__(self):
            self.item_total = 42

    cart = ShoppingCart()

    # Access through mainswitch with bound method
    result = cart.mainswitch('items.count')()
    assert result == 42


def test_multiple_children_same_level():
    """Test dot notation with multiple children at same level."""
    root = Switcher(name="root")

    users = root.add(Switcher(name="users", prefix="user_"))
    products = root.add(Switcher(name="products", prefix="product_"))
    orders = root.add(Switcher(name="orders", prefix="order_"))

    @users
    def user_list():
        return "users"

    @products
    def product_list():
        return "products"

    @orders
    def order_list():
        return "orders"

    # All accessible via root
    assert root('users.list')() == "users"
    assert root('products.list')() == "products"
    assert root('orders.list')() == "orders"


def test_dot_notation_preserves_handler_functionality():
    """Test that dot notation preserves full handler functionality."""
    root = Switcher(name="root")
    operations = root.add(Switcher(name="operations"))

    @operations(typerule={"x": int})
    def process_int(x):
        return f"int: {x}"

    @operations(typerule={"x": str})
    def process_str(x):
        return f"str: {x}"

    # Dot notation to get specific handler
    handler = root('operations.process_int')
    assert handler(42) == "int: 42"

    handler = root('operations.process_str')
    assert handler("hello") == "str: hello"
