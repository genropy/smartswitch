"""SmartSwitch package.

High-level entrypoints:
- Switcher
- BasePlugin
- SwitcherOwner
- MethodEntry
- SmartAsyncPlugin
- DbOpPlugin
"""

from .core import Switcher, BasePlugin, SwitcherOwner, MethodEntry
from .plugins import SmartAsyncPlugin, DbOpPlugin, LoggingPlugin, PydanticPlugin

__all__ = [
    "Switcher",
    "BasePlugin",
    "SwitcherOwner",
    "MethodEntry",
    "SmartAsyncPlugin",
    "DbOpPlugin",
    "LoggingPlugin",
    "PydanticPlugin",
]

__version__ = "1.0.0-alpha"
