"""
Tests for parent-child relationship management.
"""

import pytest
from smartswitch import Switcher


def test_parent_property_getter():
    """Test parent property returns correct parent."""
    parent_sw = Switcher(name="parent")
    child_sw = Switcher(name="child", parent=parent_sw)

    assert child_sw.parent is parent_sw
    assert parent_sw.parent is None


def test_parent_property_setter():
    """Test parent property setter with automatic registration."""
    parent_sw = Switcher(name="parent")
    child_sw = Switcher(name="child")

    # Initially no parent
    assert child_sw.parent is None

    # Set parent
    child_sw.parent = parent_sw

    # Child should have parent
    assert child_sw.parent is parent_sw

    # Parent should have child
    assert child_sw in parent_sw.children


def test_parent_setter_unregisters_from_old_parent():
    """Test that setting a new parent unregisters from old parent."""
    old_parent = Switcher(name="old_parent")
    new_parent = Switcher(name="new_parent")
    child_sw = Switcher(name="child", parent=old_parent)

    # Verify initial state
    assert child_sw in old_parent.children
    assert child_sw not in new_parent.children

    # Change parent
    child_sw.parent = new_parent

    # Should be unregistered from old, registered with new
    assert child_sw not in old_parent.children
    assert child_sw in new_parent.children
    assert child_sw.parent is new_parent


def test_parent_setter_none_unregisters():
    """Test that setting parent to None unregisters from parent."""
    parent_sw = Switcher(name="parent")
    child_sw = Switcher(name="child", parent=parent_sw)

    # Verify initial state
    assert child_sw in parent_sw.children

    # Unset parent
    child_sw.parent = None

    # Should be unregistered
    assert child_sw not in parent_sw.children
    assert child_sw.parent is None


def test_children_property_returns_copy():
    """Test that children property returns a copy, not the internal set."""
    parent_sw = Switcher(name="parent")
    child_sw = Switcher(name="child", parent=parent_sw)

    children = parent_sw.children

    # Modifying returned set should not affect internal state
    children.clear()

    # Original should still have the child
    assert child_sw in parent_sw.children


def test_add_child_method():
    """Test add_child() method."""
    parent_sw = Switcher(name="parent")
    child_sw = Switcher(name="child")

    # Add child
    parent_sw.add_child(child_sw)

    # Should be bidirectionally linked
    assert child_sw.parent is parent_sw
    assert child_sw in parent_sw.children


def test_add_child_type_check():
    """Test add_child() raises TypeError for non-Switcher."""
    parent_sw = Switcher(name="parent")

    with pytest.raises(TypeError, match="Expected Switcher instance"):
        parent_sw.add_child("not a switcher")


def test_remove_child_method():
    """Test remove_child() method."""
    parent_sw = Switcher(name="parent")
    child_sw = Switcher(name="child", parent=parent_sw)

    # Verify initial state
    assert child_sw in parent_sw.children

    # Remove child
    parent_sw.remove_child(child_sw)

    # Should be unlinked
    assert child_sw.parent is None
    assert child_sw not in parent_sw.children


def test_remove_child_not_present():
    """Test remove_child() handles non-child gracefully."""
    parent_sw = Switcher(name="parent")
    other_sw = Switcher(name="other")

    # Should not raise, just no-op
    parent_sw.remove_child(other_sw)

    assert other_sw.parent is None


def test_multiple_children():
    """Test parent can have multiple children."""
    parent_sw = Switcher(name="parent")
    child1 = Switcher(name="child1", parent=parent_sw)
    child2 = Switcher(name="child2", parent=parent_sw)
    child3 = Switcher(name="child3", parent=parent_sw)

    assert len(parent_sw.children) == 3
    assert child1 in parent_sw.children
    assert child2 in parent_sw.children
    assert child3 in parent_sw.children


def test_multi_level_hierarchy():
    """Test hierarchies with multiple levels."""
    root = Switcher(name="root")
    level1 = Switcher(name="level1", parent=root)
    level2 = Switcher(name="level2", parent=level1)
    level3 = Switcher(name="level3", parent=level2)

    # Verify chain
    assert level3.parent is level2
    assert level2.parent is level1
    assert level1.parent is root
    assert root.parent is None

    # Verify children at each level
    assert level2 in level1.children
    assert level1 in root.children
    assert level3 in level2.children


def test_reparenting_multiple_times():
    """Test that a child can be reparented multiple times."""
    parent1 = Switcher(name="parent1")
    parent2 = Switcher(name="parent2")
    parent3 = Switcher(name="parent3")
    child = Switcher(name="child")

    # Move through parents
    child.parent = parent1
    assert child in parent1.children
    assert child not in parent2.children
    assert child not in parent3.children

    child.parent = parent2
    assert child not in parent1.children
    assert child in parent2.children
    assert child not in parent3.children

    child.parent = parent3
    assert child not in parent1.children
    assert child not in parent2.children
    assert child in parent3.children


def test_parent_child_with_handlers():
    """Test that parent-child works correctly with registered handlers."""
    parent_sw = Switcher(name="parent", prefix="parent_")
    child_sw = Switcher(name="child", prefix="child_", parent=parent_sw)

    @parent_sw
    def parent_handler():
        return "parent"

    @child_sw
    def child_handler():
        return "child"

    # Verify handlers work
    assert parent_sw("handler")() == "parent"
    assert child_sw("handler")() == "child"

    # Verify parent-child relationship intact
    assert child_sw.parent is parent_sw
    assert child_sw in parent_sw.children


def test_init_with_parent_parameter():
    """Test that parent parameter in __init__ works correctly."""
    parent_sw = Switcher(name="parent")
    child_sw = Switcher(name="child", parent=parent_sw)

    # Should be automatically registered
    assert child_sw.parent is parent_sw
    assert child_sw in parent_sw.children


def test_children_empty_by_default():
    """Test that a new Switcher has no children by default."""
    sw = Switcher(name="test")

    assert len(sw.children) == 0
    assert sw.children == set()


def test_recursive_api_discovery_use_case():
    """Test the real-world use case: recursive API discovery."""
    # Root API
    root_api = Switcher(name="root")

    # Handler class with its own API
    class HandlerA:
        api = Switcher(name="handler_a", prefix="handler_")

        @api
        def handler_list(self):
            return ["a", "b", "c"]

        @api
        def handler_get(self, item):
            return f"get {item}"

    class HandlerB:
        api = Switcher(name="handler_b", prefix="cmd_")

        @api
        def cmd_start(self):
            return "started"

        @api
        def cmd_stop(self):
            return "stopped"

    # Link handlers to root
    HandlerA.api.parent = root_api
    HandlerB.api.parent = root_api

    # Discovery: iterate all children
    assert len(root_api.children) == 2
    assert HandlerA.api in root_api.children
    assert HandlerB.api in root_api.children

    # Can access handler names from each child
    handler_a_entries = HandlerA.api.entries()
    assert "list" in handler_a_entries
    assert "get" in handler_a_entries

    handler_b_entries = HandlerB.api.entries()
    assert "start" in handler_b_entries
    assert "stop" in handler_b_entries
