"""
Tests for on_decorate() hook functionality.

Tests that plugins can implement the on_decorate() hook to be notified
when functions are decorated, separate from wrapping logic.
"""

import pytest
from functools import wraps

from smartswitch import Switcher, BasePlugin


class TestOnDecorateHook:
    """Test on_decorate() hook functionality."""

    def test_on_decorate_called_before_wrap(self):
        """Test that on_decorate() is called before wrap()."""
        call_order = []

        class TrackingPlugin(BasePlugin):
            def on_decorate(self, func, switcher):
                call_order.append(("on_decorate", func.__name__))

            def _wrap_handler(self, func, switcher):
                call_order.append(("wrap", func.__name__))
                return func

        sw = Switcher().plug(TrackingPlugin())

        @sw
        def test_func():
            return "result"

        # on_decorate should be called before wrap
        assert len(call_order) == 2
        assert call_order[0] == ("on_decorate", "test_func")
        assert call_order[1] == ("wrap", "test_func")

    def test_on_decorate_receives_original_func(self):
        """Test that on_decorate() receives the original function."""
        captured_func = None

        class CapturePlugin(BasePlugin):
            def on_decorate(self, func, switcher):
                nonlocal captured_func
                captured_func = func

            def _wrap_handler(self, func, switcher):
                return func

        sw = Switcher().plug(CapturePlugin())

        @sw
        def original_func():
            """Original docstring"""
            return "result"

        # on_decorate should receive the original undecorated function
        assert captured_func is not None
        assert captured_func.__name__ == "original_func"
        assert captured_func.__doc__ == "Original docstring"

    def test_on_decorate_metadata_collection(self):
        """Test using on_decorate() to collect metadata."""

        class MetadataPlugin(BasePlugin):
            def __init__(self, **config):
                super().__init__(**config)
                self.metadata = []

            def on_decorate(self, func, switcher):
                self.metadata.append(
                    {
                        "name": func.__name__,
                        "module": func.__module__,
                        "doc": func.__doc__,
                        "has_annotations": bool(func.__annotations__),
                    }
                )

            def _wrap_handler(self, func, switcher):
                return func

        Switcher.register_plugin("metadata", MetadataPlugin)
        sw = Switcher().plug("metadata")

        @sw
        def func1():
            """First function"""
            return 1

        @sw
        def func2(x: int) -> int:
            """Second function"""
            return x * 2

        # Check metadata was collected
        assert len(sw.metadata.metadata) == 2
        assert sw.metadata.metadata[0]["name"] == "func1"
        assert sw.metadata.metadata[0]["doc"] == "First function"
        assert sw.metadata.metadata[0]["has_annotations"] is False

        assert sw.metadata.metadata[1]["name"] == "func2"
        assert sw.metadata.metadata[1]["doc"] == "Second function"
        assert sw.metadata.metadata[1]["has_annotations"] is True

    def test_on_decorate_with_multiple_plugins(self):
        """Test on_decorate() called for all plugins in chain."""
        calls = []

        class Plugin1(BasePlugin):
            def on_decorate(self, func, switcher):
                calls.append("plugin1")

            def _wrap_handler(self, func, switcher):
                return func

        class Plugin2(BasePlugin):
            def on_decorate(self, func, switcher):
                calls.append("plugin2")

            def _wrap_handler(self, func, switcher):
                return func

        sw = Switcher().plug(Plugin1()).plug(Plugin2())

        @sw
        def test_func():
            return "result"

        # Both plugins should have their on_decorate called
        assert calls == ["plugin1", "plugin2"]

    def test_on_decorate_no_op_default(self):
        """Test that on_decorate() no-op default doesn't break anything."""

        class MinimalPlugin(BasePlugin):
            # Don't override on_decorate - use default no-op
            def _wrap_handler(self, func, switcher):
                @wraps(func)
                def wrapper(*args, **kwargs):
                    return f"wrapped:{func(*args, **kwargs)}"

                return wrapper

        sw = Switcher().plug(MinimalPlugin())

        @sw
        def test_func():
            return "result"

        # Should still work normally
        result = sw("test_func")()
        assert result == "wrapped:result"

    def test_on_decorate_access_switcher(self):
        """Test that on_decorate() can access switcher state."""

        class SwitcherAccessPlugin(BasePlugin):
            def __init__(self, **config):
                super().__init__(**config)
                self.switcher_names = []

            def on_decorate(self, func, switcher):
                # Access switcher properties
                self.switcher_names.append(switcher.name)

            def _wrap_handler(self, func, switcher):
                return func

        # Create instances directly (not via global registry)
        plugin1 = SwitcherAccessPlugin()
        plugin2 = SwitcherAccessPlugin()

        sw1 = Switcher(name="switcher1").plug(plugin1)
        sw2 = Switcher(name="switcher2").plug(plugin2)

        @sw1
        def func1():
            return 1

        @sw2
        def func2():
            return 2

        # Each plugin instance should have seen its own switcher name
        assert plugin1.switcher_names == ["switcher1"]
        assert plugin2.switcher_names == ["switcher2"]

    def test_on_decorate_exception_handling(self):
        """Test that exceptions in on_decorate() are not silently ignored."""

        class FailingPlugin(BasePlugin):
            def on_decorate(self, func, switcher):
                raise RuntimeError("on_decorate failed")

            def _wrap_handler(self, func, switcher):
                return func

        sw = Switcher().plug(FailingPlugin())

        # Exception should propagate
        with pytest.raises(RuntimeError, match="on_decorate failed"):

            @sw
            def test_func():
                return "result"


class TestPluginMetadata:
    """Test _plugin_meta functionality for inter-plugin communication."""

    def test_plugin_meta_initialized(self):
        """Test that _plugin_meta is initialized on decorated functions."""
        sw = Switcher()

        @sw
        def test_func():
            return "result"

        # Check that _plugin_meta exists
        assert hasattr(test_func, "_plugin_meta")
        assert isinstance(test_func._plugin_meta, dict)

    def test_plugin_can_write_metadata(self):
        """Test that plugins can write to _plugin_meta."""

        class MetadataWriterPlugin(BasePlugin):
            def on_decorate(self, func, switcher):
                func._plugin_meta["test_plugin"] = {
                    "timestamp": "2024-01-01",
                    "version": "1.0",
                }

            def _wrap_handler(self, func, switcher):
                return func

        sw = Switcher().plug(MetadataWriterPlugin())

        @sw
        def test_func():
            return "result"

        # Check metadata was written
        assert "test_plugin" in test_func._plugin_meta
        assert test_func._plugin_meta["test_plugin"]["version"] == "1.0"

    def test_plugin_can_read_other_plugin_metadata(self):
        """Test that plugins can read metadata from previous plugins."""
        call_log = []

        class WriterPlugin(BasePlugin):
            def on_decorate(self, func, switcher):
                func._plugin_meta["writer"] = {"data": "shared_value"}

            def _wrap_handler(self, func, switcher):
                return func

        class ReaderPlugin(BasePlugin):
            def on_decorate(self, func, switcher):
                # Read metadata from previous plugin
                writer_data = func._plugin_meta.get("writer", {})
                call_log.append(("reader_on_decorate", writer_data.get("data")))

            def _wrap_handler(self, func, switcher):
                return func

        sw = Switcher().plug(WriterPlugin()).plug(ReaderPlugin())

        @sw
        def test_func():
            return "result"

        # Verify reader saw writer's metadata
        assert len(call_log) == 1
        assert call_log[0] == ("reader_on_decorate", "shared_value")

    def test_pydantic_stores_model_in_metadata(self):
        """Test that PydanticPlugin stores validation model in _plugin_meta."""
        sw = Switcher().plug("pydantic")

        @sw
        def typed_func(x: int, y: str) -> str:
            return f"{x}:{y}"

        # Check that pydantic metadata exists
        assert hasattr(typed_func, "_plugin_meta")
        assert "pydantic" in typed_func._plugin_meta

        pydantic_meta = typed_func._plugin_meta["pydantic"]
        assert "model" in pydantic_meta
        assert "hints" in pydantic_meta
        assert "signature" in pydantic_meta

        # Verify hints were captured
        assert "x" in pydantic_meta["hints"]
        assert "y" in pydantic_meta["hints"]

    def test_pydantic_metadata_available_to_next_plugin(self):
        """Test that subsequent plugins can access Pydantic metadata."""
        captured_meta = {}

        class FastAPISimulatorPlugin(BasePlugin):
            def on_decorate(self, func, switcher):
                # Simulate FastAPI plugin reading Pydantic metadata
                pydantic_meta = func._plugin_meta.get("pydantic", {})
                if pydantic_meta:
                    captured_meta["pydantic_model"] = pydantic_meta.get("model")
                    captured_meta["hints"] = pydantic_meta.get("hints")

            def _wrap_handler(self, func, switcher):
                return func

        Switcher.register_plugin("fastapi_sim", FastAPISimulatorPlugin)
        sw = Switcher().plug("pydantic").plug("fastapi_sim")

        @sw
        def create_user(name: str, age: int) -> dict:
            return {"name": name, "age": age}

        # Verify FastAPI simulator saw Pydantic metadata
        assert "pydantic_model" in captured_meta
        assert captured_meta["pydantic_model"] is not None
        assert "hints" in captured_meta
        assert "name" in captured_meta["hints"]
        assert "age" in captured_meta["hints"]
