"""Collection of optional Switcher plugins."""

from __future__ import annotations

import inspect
from typing import Optional

from ..core import MethodEntry, BasePlugin, Switcher


class SmartAsyncPlugin(BasePlugin):
    """Wrap async handlers with smartasync so they work in sync contexts."""

    def __init__(self, name: Optional[str] = None, *, marker_attr: str = "_smartasync_reset_cache"):
        super().__init__(name=name)
        self.marker_attr = marker_attr

    def _should_wrap(self, func) -> bool:
        if not inspect.iscoroutinefunction(func):
            return False
        return not hasattr(func, self.marker_attr)

    def on_decore(self, switch, func, entry: MethodEntry) -> None:  # type: ignore[override]
        info = entry.metadata.setdefault("smartasync", {})
        if not self._should_wrap(func):
            info.setdefault("wrapped", False)
            return
        try:
            from smartasync import smartasync
        except ImportError as exc:  # pragma: no cover - defensive guard
            raise RuntimeError("smartasync package is required for SmartAsyncPlugin") from exc
        wrapped = smartasync(func)
        info["wrapped"] = True
        entry.func = wrapped

    def wrap_handler(self, switch, entry: MethodEntry, call_next):  # type: ignore[override]
        return call_next


# Register plugin for convenience so users can do .plug("smartasync")
Switcher.register_plugin("smartasync", SmartAsyncPlugin)

class DbOpPlugin(BasePlugin):
    """Database operation plugin that injects cursors and manages transactions."""

    def wrap_handler(self, switch, entry: MethodEntry, call_next):  # type: ignore[override]
        def wrapper(*args, **kwargs):
            if not args:
                raise TypeError(
                    f"{entry.name}() missing required positional argument 'self'"
                )
            instance = args[0]
            if not hasattr(instance, "db"):
                raise AttributeError(
                    f"{instance.__class__.__name__} must expose 'db' attribute for DbOpPlugin"
                )
            db = instance.db
            autocommit = kwargs.get("autocommit", True)
            if "cursor" not in kwargs or kwargs["cursor"] is None:
                kwargs["cursor"] = db.cursor()
            try:
                result = call_next(*args, **kwargs)
                if autocommit:
                    db.commit()
                return result
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
                raise

        return wrapper


Switcher.register_plugin("dbop", DbOpPlugin)

# Import logging and pydantic plugins
from .logging import LoggingPlugin
from .pydantic import PydanticPlugin

__all__ = ["SmartAsyncPlugin", "DbOpPlugin", "LoggingPlugin", "PydanticPlugin"]
