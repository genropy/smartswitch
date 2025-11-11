"""
Tests for global plugin registry system.

Tests the ability for external plugins to register globally using
Switcher.register_plugin() class method.
"""

import pytest
from functools import wraps

from smartswitch import Switcher, BasePlugin


class TestGlobalPluginRegistry:
    """Test global plugin registry functionality."""

    def test_builtin_plugins_preregistered(self):
        """Test that built-in plugins are pre-registered."""
        assert "logging" in Switcher._global_plugin_registry
        assert "pydantic" in Switcher._global_plugin_registry

    def test_register_external_plugin(self):
        """Test registering an external plugin globally."""

        class CustomPlugin(BasePlugin):
            def _wrap_handler(self, func, switcher):
                @wraps(func)
                def wrapper(*args, **kwargs):
                    return f"custom:{func(*args, **kwargs)}"

                return wrapper

        # Register plugin
        Switcher.register_plugin("custom", CustomPlugin)

        # Verify it's in the registry
        assert "custom" in Switcher._global_plugin_registry

        # Use it in a Switcher instance
        sw = Switcher().plug("custom")

        @sw
        def test_func():
            return "result"

        result = sw("test_func")()
        assert result == "custom:result"

    def test_registered_plugin_available_everywhere(self):
        """Test that registered plugin is available in all Switcher instances."""

        class GlobalPlugin(BasePlugin):
            def _wrap_handler(self, func, switcher):
                @wraps(func)
                def wrapper(*args, **kwargs):
                    return f"global:{func(*args, **kwargs)}"

                return wrapper

        # Register once
        Switcher.register_plugin("global_test", GlobalPlugin)

        # Use in multiple different Switcher instances
        sw1 = Switcher().plug("global_test")
        sw2 = Switcher().plug("global_test")

        @sw1
        def func1():
            return "one"

        @sw2
        def func2():
            return "two"

        assert sw1("func1")() == "global:one"
        assert sw2("func2")() == "global:two"

    def test_unknown_plugin_error_message(self):
        """Test that unknown plugin gives helpful error message."""
        sw = Switcher()

        with pytest.raises(ValueError) as exc_info:
            sw.plug("nonexistent")

        error_msg = str(exc_info.value)
        assert "nonexistent" in error_msg
        assert "Available plugins:" in error_msg
        assert "register_plugin" in error_msg

    def test_plugin_with_kwargs(self):
        """Test registering plugin that accepts configuration."""

        class ConfigurablePlugin(BasePlugin):
            def _wrap_handler(self, func, switcher):
                config = self.get_config(func.__name__)

                @wraps(func)
                def wrapper(*args, **kwargs):
                    prefix = config.get("prefix", "default")
                    return f"{prefix}:{func(*args, **kwargs)}"

                return wrapper

        Switcher.register_plugin("configurable", ConfigurablePlugin)

        # Use with configuration
        sw = Switcher().plug("configurable", prefix="test")

        @sw
        def my_func():
            return "result"

        assert sw("my_func")() == "test:result"

    def test_registry_is_class_level(self):
        """Test that registry is shared at class level, not instance level."""

        class SharedPlugin(BasePlugin):
            def _wrap_handler(self, func, switcher):
                return func

        # Register using class method
        Switcher.register_plugin("shared", SharedPlugin)

        # All instances see it
        sw1 = Switcher()
        sw2 = Switcher()

        assert "shared" in sw1._global_plugin_registry
        assert "shared" in sw2._global_plugin_registry
        # Same object
        assert sw1._global_plugin_registry is sw2._global_plugin_registry
