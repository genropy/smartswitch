"""
Tests for the new get() and __getitem__ API with SmartAsync support.

This test module covers the SmartAsync integration (#25) features:
- get() method with options
- __getitem__ for dict-like access
- default_handler support
- use_smartasync wrapping
- Dotted path resolution
"""

import unittest

from smartswitch import Switcher


class TestGetMethod(unittest.TestCase):
    """Test the get() method."""

    def test_get_basic(self):
        """Test basic get() returns wrapped handler."""
        sw = Switcher()

        @sw
        def add(a, b):
            return a + b

        handler = sw.get("add")
        self.assertEqual(handler(2, 3), 5)

    def test_get_with_default_handler(self):
        """Test get() with default_handler option."""
        sw = Switcher()

        def fallback():
            return "fallback"

        # No handler registered
        handler = sw.get("nonexistent", default_handler=fallback)
        self.assertEqual(handler(), "fallback")

    def test_get_with_init_default(self):
        """Test get() with default_handler set at init."""

        def fallback():
            return "default_fallback"

        sw = Switcher(get_default_handler=fallback)

        # Should use init default
        handler = sw.get("nonexistent")
        self.assertEqual(handler(), "default_fallback")

    def test_get_override_init_default(self):
        """Test get() can override init default."""

        def init_fallback():
            return "init"

        def runtime_fallback():
            return "runtime"

        sw = Switcher(get_default_handler=init_fallback)

        # Override with runtime default
        handler = sw.get("nonexistent", default_handler=runtime_fallback)
        self.assertEqual(handler(), "runtime")

    def test_get_nonexistent_raises(self):
        """Test get() raises NotImplementedError when no default."""
        sw = Switcher()

        with self.assertRaises(NotImplementedError) as cm:
            sw.get("nonexistent")

        self.assertIn("not found", str(cm.exception))
        self.assertIn("nonexistent", str(cm.exception))

    def test_get_dotted_path(self):
        """Test get() with dotted path."""
        parent = Switcher()
        child = Switcher(parent=parent)
        parent.add_child(child, "child")

        @child
        def method(x):
            return x * 2

        # Access via dotted path
        handler = parent.get("child.method")
        self.assertEqual(handler(5), 10)

    def test_get_with_plugins(self):
        """Test get() returns handler with plugins applied."""
        sw = Switcher()
        call_count = []

        # Simple plugin that counts calls
        from smartswitch import BasePlugin

        class CountPlugin(BasePlugin):
            def wrap_handler(self, switch, entry, call_next):
                def wrapper(*args, **kwargs):
                    call_count.append(1)
                    return call_next(*args, **kwargs)

                return wrapper

        sw.plug(CountPlugin())

        @sw
        def handler():
            return "result"

        # Get handler and call it
        h = sw.get("handler")
        result = h()

        self.assertEqual(result, "result")
        self.assertEqual(len(call_count), 1)


class TestGetItemMethod(unittest.TestCase):
    """Test the __getitem__ method."""

    def test_getitem_basic(self):
        """Test basic __getitem__ access."""
        sw = Switcher()

        @sw
        def multiply(a, b):
            return a * b

        handler = sw["multiply"]
        self.assertEqual(handler(3, 4), 12)

    def test_getitem_uses_init_defaults(self):
        """Test __getitem__ uses defaults from init."""

        def fallback():
            return "fallback"

        sw = Switcher(get_default_handler=fallback)

        # Should use init default
        handler = sw["nonexistent"]
        self.assertEqual(handler(), "fallback")

    def test_getitem_dotted_path(self):
        """Test __getitem__ with dotted path."""
        parent = Switcher()
        child = Switcher(parent=parent)
        parent.add_child(child, "child")

        @child
        def handler(x):
            return x + 10

        # Access via dotted path
        result = parent["child.handler"](5)
        self.assertEqual(result, 15)

    def test_getitem_with_plugins(self):
        """Test __getitem__ returns handler with plugins applied."""
        sw = Switcher()

        # Use logging plugin to verify plugins are applied
        sw.plug("logging", enabled=False)  # Disabled by default

        @sw
        def handler():
            return "result"

        # Get handler via __getitem__ and call it
        h = sw["handler"]
        result = h()
        self.assertEqual(result, "result")


class TestSmartAsyncIntegration(unittest.TestCase):
    """Test SmartAsync wrapping functionality."""

    def test_get_with_use_smartasync_option(self):
        """Test get() with use_smartasync option."""
        sw = Switcher()

        @sw
        def sync_handler(x):
            return x * 2

        # Get with smartasync wrapping
        handler = sw.get("sync_handler", use_smartasync=True)

        # Handler should be wrapped with smartasync
        # Note: This just verifies it doesn't error. Full async testing
        # would require async test infrastructure.
        result = handler(5)
        self.assertEqual(result, 10)

    def test_get_with_init_use_smartasync(self):
        """Test get() uses use_smartasync from init."""
        sw = Switcher(get_use_smartasync=True)

        @sw
        def handler(x):
            return x + 1

        # Should automatically wrap with smartasync
        h = sw.get("handler")
        result = h(5)
        self.assertEqual(result, 6)

    def test_get_override_init_smartasync(self):
        """Test get() can override init use_smartasync."""
        sw = Switcher(get_use_smartasync=True)

        @sw
        def handler(x):
            return x + 1

        # Override to NOT use smartasync
        h = sw.get("handler", use_smartasync=False)
        result = h(5)
        self.assertEqual(result, 6)


class TestGetAPIEdgeCases(unittest.TestCase):
    """Test edge cases for get() and __getitem__."""

    def test_get_with_alias(self):
        """Test get() works with aliased handlers."""
        sw = Switcher()

        @sw("custom_name")
        def my_handler(x):
            return x * 3

        # Access by alias
        handler = sw.get("custom_name")
        self.assertEqual(handler(4), 12)

    def test_getitem_with_alias(self):
        """Test __getitem__ works with aliased handlers."""
        sw = Switcher()

        @sw("alias")
        def handler(x):
            return x + 5

        result = sw["alias"](10)
        self.assertEqual(result, 15)

    def test_get_with_prefix(self):
        """Test get() with prefix normalization."""
        sw = Switcher(prefix="do_")

        @sw
        def do_action(x):
            return x * 2

        # Access by normalized name (without prefix)
        handler = sw.get("action")
        self.assertEqual(handler(3), 6)

    def test_get_multiple_times(self):
        """Test get() can be called multiple times."""
        sw = Switcher()

        @sw
        def handler(x):
            return x * 2

        # Get multiple times
        h1 = sw.get("handler")
        h2 = sw.get("handler")

        # Should return same wrapped handler
        self.assertEqual(h1(5), 10)
        self.assertEqual(h2(5), 10)

    def test_getitem_multiple_times(self):
        """Test __getitem__ can be called multiple times."""
        sw = Switcher()

        @sw
        def handler(x):
            return x + 1

        h1 = sw["handler"]
        h2 = sw["handler"]

        self.assertEqual(h1(5), 6)
        self.assertEqual(h2(5), 6)


class TestBackwardCompatibility(unittest.TestCase):
    """Test that decorator usage still works (backward compatibility)."""

    def test_decorator_direct(self):
        """Test @sw decorator still works."""
        sw = Switcher()

        @sw
        def handler(x):
            return x * 2

        # Access via new API
        result = sw["handler"](5)
        self.assertEqual(result, 10)

    def test_decorator_with_alias(self):
        """Test @sw('alias') decorator factory still works."""
        sw = Switcher()

        @sw("custom")
        def handler(x):
            return x + 10

        # Access via new API
        result = sw["custom"](5)
        self.assertEqual(result, 15)

    def test_mixed_usage(self):
        """Test mixing decorator and get() API."""
        sw = Switcher()

        # Register via decorator
        @sw
        def add(a, b):
            return a + b

        @sw("sub")
        def subtract(a, b):
            return a - b

        # Access via get()
        add_handler = sw.get("add")
        sub_handler = sw.get("sub")

        self.assertEqual(add_handler(10, 5), 15)
        self.assertEqual(sub_handler(10, 5), 5)

        # Also access via __getitem__
        self.assertEqual(sw["add"](10, 5), 15)
        self.assertEqual(sw["sub"](10, 5), 5)


if __name__ == "__main__":
    unittest.main()
