"""Collection of optional Switcher plugins."""

from __future__ import annotations

from ..core import BasePlugin, MethodEntry, Switcher


class DbOpPlugin(BasePlugin):
    """Database operation plugin that injects cursors and manages transactions."""

    def wrap_handler(self, switch, entry: MethodEntry, call_next):  # type: ignore[override]
        def wrapper(*args, **kwargs):
            if not args:
                raise TypeError(f"{entry.name}() missing required positional argument 'self'")
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

# Import logging plugin (always available)
from .logging import LoggingPlugin  # noqa: E402

# Import pydantic plugin only if pydantic is installed
try:
    from .pydantic import PydanticPlugin  # noqa: E402

    __all__ = ["DbOpPlugin", "LoggingPlugin", "PydanticPlugin"]
except ImportError:
    # Pydantic not installed - plugin not available
    __all__ = ["DbOpPlugin", "LoggingPlugin"]
