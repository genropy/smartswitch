"""SmartSwitch package.

High-level entrypoints:
- Switcher
- BasePlugin
- MethodEntry
- SmartAsyncPlugin
- DbOpPlugin
"""

from .core import Switcher, BasePlugin, MethodEntry
from .plugins import SmartAsyncPlugin, DbOpPlugin, LoggingPlugin

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
