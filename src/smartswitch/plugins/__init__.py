"""
SmartSwitch standard plugins.

This package contains the standard plugins that implement SmartSwitch's
core functionality: logging, type-based dispatch, and value-based dispatch.
"""

from .logging import LoggingPlugin

# TODO: Implement these plugins
# from .typerule import TypeRulePlugin
# from .valrule import ValueRulePlugin

__all__ = ["LoggingPlugin"]  # "TypeRulePlugin", "ValueRulePlugin"]
