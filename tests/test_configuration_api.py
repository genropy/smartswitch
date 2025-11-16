"""
Test suite for ConfigureProxy and MethodConfigProxy API.

Coverage targets:
- ConfigureProxy.flags property (getter/setter)
- MethodConfigProxy.flags property (getter/setter)
- .config property on both proxies
- __getattr__/__setattr__ with private attributes
- method_config with dict/object parameters
- Edge cases in configuration parsing
"""

import pytest
from pydantic import BaseModel, Field

from smartswitch import BasePlugin, Switcher

# ==============================================================================
# Test Plugin with Pydantic Config
# ==============================================================================


class TestPluginConfig(BaseModel):
    enabled: bool = Field(default=False)
    verbose: bool = Field(default=False)
    debug: bool = Field(default=False)
    timeout: int = Field(default=30)


class TestPlugin(BasePlugin):
    """Test plugin with Pydantic config."""

    config_model = TestPluginConfig

    def wrap_handler(self, switch, entry, call_next):
        def wrapper(*args, **kwargs):
            return call_next(*args, **kwargs)

        return wrapper


# Register plugin globally
Switcher.register_plugin("testplugin", TestPlugin)


# ==============================================================================
# ConfigureProxy Tests
# ==============================================================================


class TestConfigureProxyFlags:
    """Test ConfigureProxy.flags getter and setter."""

    def test_flags_getter_returns_active_boolean_flags(self):
        """Test that .flags returns only active boolean flags."""
        sw = Switcher().plug("testplugin", flags="enabled,verbose")

        # Should return comma-separated active flags
        flags = sw.testplugin.configure.flags
        assert isinstance(flags, str)
        assert "enabled" in flags
        assert "verbose" in flags
        # timeout is int, not boolean, so not in flags
        assert "timeout" not in flags

    def test_flags_setter_updates_configuration(self):
        """Test that .flags setter updates configuration."""
        sw = Switcher().plug("testplugin")

        # Initially no flags
        initial_flags = sw.testplugin.configure.flags
        assert "enabled" not in initial_flags

        # Set flags
        sw.testplugin.configure.flags = "enabled,verbose"

        # Verify flags updated
        assert sw.testplugin.configure.config["enabled"] is True
        assert sw.testplugin.configure.config["verbose"] is True

    def test_flags_setter_with_negation(self):
        """Test flags setter with :off negation."""
        sw = Switcher().plug("testplugin", flags="enabled,verbose")

        # Turn off verbose
        sw.testplugin.configure.flags = "enabled,verbose:off"

        assert sw.testplugin.configure.config["enabled"] is True
        assert sw.testplugin.configure.config["verbose"] is False


class TestConfigureProxyConfig:
    """Test ConfigureProxy.config property."""

    def test_config_property_returns_full_dict(self):
        """Test that .config returns complete configuration dict."""
        sw = Switcher().plug("testplugin", flags="enabled", timeout=60)

        config = sw.testplugin.configure.config

        assert isinstance(config, dict)
        assert "enabled" in config
        assert config["enabled"] is True
        assert "timeout" in config
        assert config["timeout"] == 60

    def test_config_property_includes_all_fields(self):
        """Test that .config includes all model fields with defaults."""
        sw = Switcher().plug("testplugin")

        config = sw.testplugin.configure.config

        # Should include all fields from TestPluginConfig
        assert "enabled" in config
        assert "verbose" in config
        assert "debug" in config
        assert "timeout" in config


class TestConfigureProxyPrivateAttributes:
    """Test ConfigureProxy.__getattr__ and __setattr__ with private attributes."""

    def test_getattr_private_attribute_raises(self):
        """Test that accessing private attributes uses normal attribute access."""
        sw = Switcher().plug("testplugin")

        # Private attributes should not be proxied to config
        # They should raise AttributeError if they don't exist
        with pytest.raises(AttributeError):
            _ = sw.testplugin.configure._nonexistent_private_attr

    def test_getattr_public_returns_config_value(self):
        """Test that public attributes return config values."""
        sw = Switcher().plug("testplugin", flags="enabled", timeout=45)

        # Public attributes should return config values
        assert sw.testplugin.configure.enabled is True
        assert sw.testplugin.configure.timeout == 45

    def test_setattr_public_updates_config(self):
        """Test that setting public attributes updates config."""
        sw = Switcher().plug("testplugin")

        # Set public attribute
        sw.testplugin.configure.timeout = 100

        # Should update config
        assert sw.testplugin.configure.config["timeout"] == 100


# ==============================================================================
# MethodConfigProxy Tests
# ==============================================================================


class TestMethodConfigProxyFlags:
    """Test MethodConfigProxy.flags getter and setter."""

    def test_method_flags_getter_returns_active_flags(self):
        """Test that method-specific .flags returns active boolean flags."""
        sw = Switcher().plug("testplugin", flags="enabled")

        @sw
        def handler():
            return "test"

        # Set method-specific flags
        sw.testplugin.configure["handler"].flags = "enabled,verbose"

        # Get flags
        flags = sw.testplugin.configure["handler"].flags
        assert isinstance(flags, str)
        assert "enabled" in flags
        assert "verbose" in flags

    def test_method_flags_setter_updates_method_config(self):
        """Test that method .flags setter updates method-specific config."""
        sw = Switcher().plug("testplugin")

        @sw
        def handler():
            return "test"

        # Set method flags
        sw.testplugin.configure["handler"].flags = "enabled,debug"

        # Verify method config
        cfg = sw.testplugin.configure["handler"].config
        assert cfg["enabled"] is True
        assert cfg["debug"] is True

    def test_method_flags_with_multiple_methods(self):
        """Test flags setter with multiple methods (comma-separated)."""
        sw = Switcher().plug("testplugin")

        @sw
        def handler1():
            return "test1"

        @sw
        def handler2():
            return "test2"

        # Set flags for multiple methods at once
        sw.testplugin.configure["handler1,handler2"].flags = "enabled,verbose"

        # Both should have same flags
        assert sw.testplugin.configure["handler1"].config["enabled"] is True
        assert sw.testplugin.configure["handler2"].config["enabled"] is True


class TestMethodConfigProxyConfig:
    """Test MethodConfigProxy.config property."""

    def test_method_config_property_returns_merged_config(self):
        """Test that method .config returns merged global + method config."""
        sw = Switcher().plug("testplugin", flags="enabled", timeout=30)

        @sw
        def handler():
            return "test"

        # Override method-specific
        sw.testplugin.configure["handler"].verbose = True

        # Get merged config
        config = sw.testplugin.configure["handler"].config

        # Should have global + method-specific
        assert config["enabled"] is True  # from global
        assert config["timeout"] == 30  # from global
        assert config["verbose"] is True  # method-specific override

    def test_method_config_overrides_global(self):
        """Test that method config overrides global config."""
        sw = Switcher().plug("testplugin", flags="enabled")

        @sw
        def handler():
            return "test"

        # Override at method level
        sw.testplugin.configure["handler"].enabled = False

        # Method config should win
        assert sw.testplugin.configure["handler"].config["enabled"] is False
        # Global should be unchanged
        assert sw.testplugin.configure.config["enabled"] is True


class TestMethodConfigProxyPrivateAttributes:
    """Test MethodConfigProxy.__getattr__ and __setattr__ with private attrs."""

    def test_method_getattr_public_returns_config(self):
        """Test that public attributes return config values."""
        sw = Switcher().plug("testplugin", timeout=50)

        @sw
        def handler():
            return "test"

        # Should return config value
        assert sw.testplugin.configure["handler"].timeout == 50

    def test_method_setattr_public_updates_config(self):
        """Test that setting public attributes updates method config."""
        sw = Switcher().plug("testplugin")

        @sw
        def handler():
            return "test"

        # Set public attribute
        sw.testplugin.configure["handler"].timeout = 90

        # Should update method config
        assert sw.testplugin.configure["handler"].config["timeout"] == 90


# ==============================================================================
# Method Config Initialization Tests
# ==============================================================================


class TestMethodConfigWithDict:
    """Test method_config parameter with dict values."""

    def test_method_config_with_dict(self):
        """Test plugin initialization with method_config as dict."""
        sw = Switcher().plug(
            "testplugin",
            method_config={
                "handler1": {"enabled": True, "timeout": 60},
                "handler2": {"verbose": True, "debug": True},
            },
        )

        @sw
        def handler1():
            return "test1"

        @sw
        def handler2():
            return "test2"

        # Verify method configs
        cfg1 = sw.testplugin.configure["handler1"].config
        assert cfg1["enabled"] is True
        assert cfg1["timeout"] == 60

        cfg2 = sw.testplugin.configure["handler2"].config
        assert cfg2["verbose"] is True
        assert cfg2["debug"] is True

    def test_method_config_with_pydantic_model(self):
        """Test method_config with Pydantic model instances."""
        # Create Pydantic model instance
        config_instance = TestPluginConfig(enabled=True, verbose=True, timeout=45)

        sw = Switcher().plug("testplugin", method_config={"handler": config_instance})

        @sw
        def handler():
            return "test"

        # Verify config was parsed from model
        cfg = sw.testplugin.configure["handler"].config
        assert cfg["enabled"] is True
        assert cfg["verbose"] is True
        assert cfg["timeout"] == 45


# ==============================================================================
# Plugin Without Pydantic Tests
# ==============================================================================


class NonPydanticPlugin(BasePlugin):
    """Plugin without Pydantic config_model."""

    # No config_model defined

    def wrap_handler(self, switch, entry, call_next):
        def wrapper(*args, **kwargs):
            return call_next(*args, **kwargs)

        return wrapper


Switcher.register_plugin("nonpydantic", NonPydanticPlugin)


class TestPluginWithoutPydantic:
    """Test plugin configuration without Pydantic BaseModel."""

    def test_plugin_without_config_model(self):
        """Test plugin that doesn't define config_model."""
        # Should work with basic dict-based config
        sw = Switcher().plug("nonpydantic", custom_param="value")

        @sw
        def handler():
            return "test"

        # Should not raise, uses dict-based config
        result = sw["handler"]()
        assert result == "test"

    def test_flags_parsing_without_pydantic(self):
        """Test flags parsing when config_model is not BaseModel."""
        sw = Switcher().plug("nonpydantic", flags="flag1,flag2")

        @sw
        def handler():
            return "test"

        # Should parse flags even without Pydantic
        # flags become boolean config values
        result = sw["handler"]()
        assert result == "test"


# ==============================================================================
# Edge Cases
# ==============================================================================


class TestConfigurationEdgeCases:
    """Test edge cases in configuration parsing."""

    def test_flags_with_empty_values(self):
        """Test flags string with empty values (double commas)."""
        sw = Switcher().plug("testplugin", flags="enabled,,verbose")

        @sw
        def handler():
            return "test"

        # Should skip empty flags
        cfg = sw.testplugin.configure.config
        assert cfg["enabled"] is True
        assert cfg["verbose"] is True

    def test_update_config_with_flags_parameter(self):
        """Test _update_config method with flags parameter."""
        sw = Switcher().plug("testplugin")

        @sw
        def handler():
            return "test"

        # Use _update_config directly (internal API)
        sw.testplugin._update_config("handler", flags="enabled,debug")

        # Verify update
        cfg = sw.testplugin.configure["handler"].config
        assert cfg["enabled"] is True
        assert cfg["debug"] is True

    def test_plugin_returns_none_for_nonexistent(self):
        """Test Switcher.plugin() returns None when plugin not found."""
        sw = Switcher()

        result = sw.plugin("nonexistent_plugin")

        assert result is None
