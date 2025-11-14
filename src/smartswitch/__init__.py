"""SmartSwitch package.

High-level entrypoints:
- Switcher
- BasePlugin
- MethodEntry
- SmartAsyncPlugin
- DbOpPlugin
"""

from .core import BasePlugin, MethodEntry, Switcher
from .plugins import DbOpPlugin, LoggingPlugin, SmartAsyncPlugin

# PydanticPlugin is conditionally imported in plugins/__init__.py
# Only available if pydantic is installed
try:
    from .plugins import PydanticPlugin
    __all__ = [
        "Switcher",
        "BasePlugin",
        "MethodEntry",
        "SmartAsyncPlugin",
        "DbOpPlugin",
        "LoggingPlugin",
        "PydanticPlugin",
    ]
except ImportError:
    __all__ = [
        "Switcher",
        "BasePlugin",
        "MethodEntry",
        "SmartAsyncPlugin",
        "DbOpPlugin",
        "LoggingPlugin",
    ]

__version__ = "0.9.1"
