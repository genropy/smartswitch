"""
Tests for error handling and edge cases.

These tests target uncovered error paths to improve coverage.
"""

from __future__ import annotations

import unittest

from smartswitch import BasePlugin, Switcher


class TestPluginErrorHandling(unittest.TestCase):
    """Test error handling in plugin registration."""

    def test_register_non_plugin_class(self):
        """Test that registering non-BasePlugin class raises TypeError."""

        class NotAPlugin:
            pass

        with self.assertRaises(TypeError) as cm:
            Switcher.register_plugin("invalid", NotAPlugin)

        self.assertIn("BasePlugin subclass", str(cm.exception))

    def test_plug_with_unknown_plugin_name(self):
        """Test that plug() with unknown name raises ValueError."""
        sw = Switcher()

        # String that is not a registered plugin name
        with self.assertRaises(ValueError) as cm:
            sw.plug("not_a_plugin")

        self.assertIn("Unknown plugin name", str(cm.exception))

    def test_plug_with_invalid_class(self):
        """Test that plug() with non-plugin class raises TypeError."""
        sw = Switcher()

        class NotAPlugin:
            pass

        with self.assertRaises(TypeError) as cm:
            sw.plug(NotAPlugin)

        self.assertIn("BasePlugin", str(cm.exception))


class TestSwitcherChildErrors(unittest.TestCase):
    """Test error handling in child switch management."""

    def test_get_nonexistent_child(self):
        """Test that getting nonexistent child raises KeyError."""
        sw = Switcher("parent")

        with self.assertRaises(KeyError) as cm:
            sw.get_child("nonexistent")

        self.assertIn("No child switch named 'nonexistent'", str(cm.exception))

    def test_add_switch_to_itself(self):
        """Test that adding switch to itself raises ValueError."""
        sw = Switcher("self")

        with self.assertRaises(ValueError) as cm:
            sw.add_child(sw)

        self.assertIn("Cannot attach a switch to itself", str(cm.exception))

    def test_child_name_collision(self):
        """Test that duplicate child name raises ValueError."""
        parent = Switcher("parent")
        child1 = Switcher("child")
        child2 = Switcher("another")

        parent.add_child(child1, name="duplicate")

        with self.assertRaises(ValueError) as cm:
            parent.add_child(child2, name="duplicate")

        self.assertIn("Child name collision", str(cm.exception))


class TestSwitcherMethods(unittest.TestCase):
    """Test uncovered Switcher methods."""

    def test_describe(self):
        """Test describe() method returns correct structure."""
        sw = Switcher("test")

        @sw
        def handler(x):
            return x * 2

        desc = sw.describe()

        self.assertEqual(desc["name"], "test")
        self.assertIn("methods", desc)
        self.assertIn("handler", desc["methods"])
        self.assertIn("children", desc)
        self.assertIn("plugins", desc)

    def test_plugin_to_spec(self):
        """Test plugin to_spec() method."""

        class TestPlugin(BasePlugin):
            def wrap_handler(self, switch, entry, call_next):
                return call_next

        plugin = TestPlugin(name="test", custom_param="value")
        spec = plugin.to_spec()

        self.assertEqual(spec.factory, TestPlugin)
        self.assertEqual(spec.plugin_name, "test")
        self.assertEqual(spec.kwargs["custom_param"], "value")

    def test_registered_plugins(self):
        """Test registered_plugins() returns dict."""
        registry = Switcher.registered_plugins()

        self.assertIsInstance(registry, dict)
        # Should have at least 'logging' plugin registered
        self.assertIn("logging", registry)

    def test_iter_plugins_empty(self):
        """Test iter_plugins() on Switcher without plugins."""
        sw = Switcher()

        plugins = list(sw.iter_plugins())
        self.assertEqual(len(plugins), 0)

    def test_iter_plugins_with_plugins(self):
        """Test iter_plugins() returns all plugins."""

        class Plugin1(BasePlugin):
            def wrap_handler(self, switch, entry, call_next):
                return call_next

        class Plugin2(BasePlugin):
            def wrap_handler(self, switch, entry, call_next):
                return call_next

        sw = Switcher()
        sw.plug(Plugin1, name="p1")
        sw.plug(Plugin2, name="p2")

        plugins = list(sw.iter_plugins())
        self.assertEqual(len(plugins), 2)
        names = [p.name for p in plugins]
        self.assertIn("p1", names)
        self.assertIn("p2", names)


class TestPluginConfiguration(unittest.TestCase):
    """Test plugin configuration methods."""

    def test_plugin_config_update(self):
        """Test that plugging instance updates its config."""

        class ConfigPlugin(BasePlugin):
            def wrap_handler(self, switch, entry, call_next):
                return call_next

        # Create plugin with initial config
        plugin = ConfigPlugin(name="test", param1="value1")
        self.assertEqual(plugin.config["param1"], "value1")

        # Plug it with additional config
        sw = Switcher()
        sw.plug(plugin, param2="value2")

        # Config should be updated
        self.assertEqual(plugin.config["param1"], "value1")
        self.assertEqual(plugin.config["param2"], "value2")


if __name__ == "__main__":
    unittest.main()
