"""SmartSwitch package.

High-level entrypoints:
- Switcher
- BasePlugin
- MethodEntry
"""

from .core import BasePlugin, MethodEntry, Switcher
from .plugins import LoggingPlugin

# PydanticPlugin is conditionally imported in plugins/__init__.py
# Only available if pydantic is installed
try:
    from .plugins import PydanticPlugin

    __all__ = [
        "Switcher",
        "BasePlugin",
        "MethodEntry",
        "LoggingPlugin",
        "PydanticPlugin",
    ]
except ImportError:
    __all__ = [
        "Switcher",
        "BasePlugin",
        "MethodEntry",
        "LoggingPlugin",
    ]

__version__ = "0.11.0"
