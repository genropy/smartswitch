"""SmartSwitch package.

High-level entrypoints:
- Switcher
- BasePlugin
- MethodEntry
- SmartAsyncPlugin
- DbOpPlugin
"""

from .core import Switcher, BasePlugin, MethodEntry
from .plugins import SmartAsyncPlugin, DbOpPlugin, LoggingPlugin, PydanticPlugin

__all__ = [
    "Switcher",
    "BasePlugin",
    "MethodEntry",
    "SmartAsyncPlugin",
    "DbOpPlugin",
    "LoggingPlugin",
    "PydanticPlugin",
]

__version__ = "0.9.0"
