"""
Tests for new API discovery features:
- parent parameter
- entries() method
"""

import pytest
from smartswitch import Switcher


def test_switcher_parent_parameter():
    """Test that Switcher accepts parent parameter."""
    parent_sw = Switcher(name="parent")
    child_sw = Switcher(name="child", parent=parent_sw)

    assert child_sw.parent is parent_sw
    assert parent_sw.parent is None


def test_entries_empty_switcher():
    """Test entries() returns empty list for new Switcher."""
    sw = Switcher()
    assert sw.entries() == []


def test_entries_with_simple_decorator():
    """Test entries() returns handler names for simple decorators."""
    sw = Switcher()

    @sw
    def handler_one():
        return "one"

    @sw("custom_name")
    def handler_two():
        return "two"

    entries = sw.entries()
    assert "handler_one" in entries
    assert "custom_name" in entries
    assert len(entries) == 2


def test_entries_with_prefix():
    """Test entries() with prefix stripping."""
    sw = Switcher(prefix="api_")

    @sw
    def api_create():
        return "created"

    @sw
    def api_delete():
        return "deleted"

    entries = sw.entries()
    assert "create" in entries
    assert "delete" in entries
    assert len(entries) == 2


def test_entries_with_typerule():
    """Test entries() includes handlers registered with typerule."""
    sw = Switcher()

    @sw(typerule={"x": int})
    def process_int(x):
        return f"int: {x}"

    @sw(typerule={"x": str})
    def process_str(x):
        return f"str: {x}"

    entries = sw.entries()
    assert "process_int" in entries
    assert "process_str" in entries
    assert len(entries) == 2


def test_entries_with_valrule():
    """Test entries() includes handlers registered with valrule."""
    sw = Switcher()

    @sw(valrule=lambda x: x > 0)
    def positive(x):
        return "positive"

    @sw(valrule=lambda x: x < 0)
    def negative(x):
        return "negative"

    entries = sw.entries()
    assert "positive" in entries
    assert "negative" in entries
    assert len(entries) == 2


def test_parent_hierarchy():
    """Test parent hierarchy with multiple levels."""
    root_sw = Switcher(name="root")
    child_sw = Switcher(name="child", parent=root_sw)
    grandchild_sw = Switcher(name="grandchild", parent=child_sw)

    assert grandchild_sw.parent is child_sw
    assert child_sw.parent is root_sw
    assert root_sw.parent is None


def test_entries_order_preserved():
    """Test that entries() returns handlers in registration order."""
    sw = Switcher()

    @sw("first")
    def handler_a():
        pass

    @sw("second")
    def handler_b():
        pass

    @sw("third")
    def handler_c():
        pass

    entries = sw.entries()
    # Python 3.7+ dicts preserve insertion order
    assert entries == ["first", "second", "third"]
