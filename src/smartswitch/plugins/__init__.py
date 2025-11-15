"""Collection of optional Switcher plugins."""

from __future__ import annotations

# Import logging plugin (always available)
from .logging import LoggingPlugin

# Import pydantic plugin only if pydantic is installed
try:
    from .pydantic import PydanticPlugin

    __all__ = ["LoggingPlugin", "PydanticPlugin"]
except ImportError:
    # Pydantic not installed - plugin not available
    __all__ = ["LoggingPlugin"]
