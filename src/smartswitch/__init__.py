"""SmartSwitch package.

High-level entrypoints:
- SmartSwitch (formerly Switcher)
- SmartPlugin (formerly BasePlugin)
- SmartSwitchOwner
- MethodEntry
- SmartAsyncPlugin
- DbOpPlugin
"""

from .core import SmartSwitch, SmartPlugin, SmartSwitchOwner, MethodEntry
from .plugins import SmartAsyncPlugin, DbOpPlugin

# Backward compatibility aliases (deprecated)
Switcher = SmartSwitch
BasePlugin = SmartPlugin

__all__ = [
    "SmartSwitch",
    "SmartPlugin",
    "SmartSwitchOwner",
    "MethodEntry",
    "SmartAsyncPlugin",
    "DbOpPlugin",
    # Legacy names
    "Switcher",
    "BasePlugin",
]

__version__ = "1.0.0-alpha"
