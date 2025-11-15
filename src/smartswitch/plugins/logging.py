"""
Switcher Logging Plugin.

Provides real-time output for handler calls with composable display flags.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ..core import MethodEntry, Switcher

from ..core import BasePlugin


class LoggingPlugin(BasePlugin):
    """
    Switcher plugin for real-time handler logging.

    Displays handler calls and results in real-time using either print() or
    Python's logging system. Supports composable flags and granular per-method
    configuration.

    Args:
        name: Plugin name (default: 'logger')
        mode: Global mode flags (default: 'log,disabled')
              Output destination (required, mutually exclusive):
              - 'print': Use print() for output
              - 'log': Use Python logging (with auto-fallback to print)

              State flag (optional):
              - 'enabled': Plugin enabled (default if neither specified)
              - 'disabled': Plugin disabled

              Content flags (optional, combinable):
              - 'before': Show input parameters
              - 'after': Show return value
              - 'time': Show execution time

              Default: If no content flags, shows both before and after.

              Examples:
              - 'log,disabled' → plugin registered but inactive (DEFAULT)
              - 'print' → print input + output for all methods
              - 'print,after,time' → print only output with timing
              - 'log,after' → log only output

        logger: Custom logger instance. If None, uses logger named 'smartswitch'

        config: Dict with per-method configuration overrides.
                Keys: method name or comma-separated names ('alfa,beta,gamma')
                Values: mode string (same format as 'mode' parameter)

                Examples:
                - {'calculate': 'print,after,time'}
                - {'history': 'disabled'}
                - {'alfa,beta,gamma': 'disabled'}

    Examples:
        Default: plugin disabled (opt-in behavior):

        >>> sw = Switcher().plug('logging')  # Disabled by default
        >>> @sw
        ... def add(a, b):
        ...     return a + b
        >>> sw('add')(2, 3)  # No output
        5

        Basic usage (enable globally):

        >>> sw = Switcher().plug('logging', mode='print')
        >>> sw('add')(2, 3)
        → add(2, 3)
        ← add() → 5
        5

        Granular configuration (enable only specific methods):

        >>> sw = Switcher().plug('logging', config={
        ...     'calculate': 'print,after,time',
        ...     'process': 'print,before'
        ... })
        >>> sw('calculate')(2, 3)  # Logs with timing
        ← calculate() → 5 (0.0001s)
        >>> sw('other_method')(1)  # No logging (global disabled)

        Disable specific methods:

        >>> sw = Switcher().plug('logging', mode='print,after', config={
        ...     'internal_helper': 'disabled',
        ...     'alfa,beta,gamma': 'disabled'  # Multiple methods
        ... })
        >>> sw('public_api')(1)  # Logs
        ← public_api() → 1
        >>> sw('internal_helper')(2)  # No logging

        With Python logging:

        >>> import logging
        >>> logging.basicConfig(level=logging.INFO)
        >>> sw = Switcher().plug('logging', mode='log,after,time')
        >>> sw('add')(2, 3)
        INFO:smartswitch:← add() → 5 (0.0001s)
        5
    """

    def __init__(
        self,
        name: Optional[str] = None,
        mode: str = "log,disabled",
        logger: Optional[logging.Logger] = None,
        config: Optional[dict] = None,
        **kwargs: Any,
    ):
        """Initialize the logging plugin."""
        super().__init__(name=name or "logger", **kwargs)

        # Parse global mode flags and store in BasePlugin's _global_config
        global_cfg = self._parse_mode(mode)
        self._global_config.update(global_cfg)

        # Parse per-method configurations using BasePlugin's system
        if config:
            for method_names, method_mode in config.items():
                # Parse method mode, inheriting from global if needed
                parsed = self._parse_mode(method_mode, inherit_from=global_cfg)
                # Support comma-separated method names: 'alfa,beta,gamma'
                for method_name in method_names.split(","):
                    method_name = method_name.strip()
                    # Use BasePlugin's configure() to store per-method config
                    self.configure(method_name, **parsed)

        self._logger = logger or logging.getLogger("smartswitch")

    def _parse_mode(self, mode: str, inherit_from: Optional[dict] = None) -> dict:
        """
        Parse mode string into configuration dict.

        Args:
            mode: Mode string with flags
            inherit_from: Optional config to inherit missing flags from

        Returns:
            Configuration dictionary
        """
        flags = set(f.strip() for f in mode.split(","))

        # Output destination (optional if inheriting)
        use_print = "print" in flags
        use_log = "log" in flags

        # If neither specified and we're inheriting, use inherited values
        if not use_print and not use_log:
            if inherit_from:
                use_print = inherit_from["use_print"]
                use_log = inherit_from["use_log"]
            else:
                raise ValueError("mode must include 'print' or 'log'")

        if use_print and use_log:
            raise ValueError("mode cannot include both 'print' and 'log'")

        # Enabled/disabled flag
        is_enabled = "enabled" in flags
        is_disabled = "disabled" in flags

        if is_enabled and is_disabled:
            raise ValueError("mode cannot include both 'enabled' and 'disabled'")

        # Default to enabled if neither specified
        enabled = is_enabled or not is_disabled

        # Content flags (optional, combinable)
        has_before = "before" in flags
        has_after = "after" in flags
        has_time = "time" in flags

        # If inheriting and no content flags specified, use inherited
        if inherit_from and not (has_before or has_after or has_time):
            show_before = inherit_from["show_before"]
            show_after = inherit_from["show_after"]
            show_time = inherit_from["show_time"]
        else:
            show_before = has_before
            show_after = has_after
            show_time = has_time

            # Default: if no content flags explicitly set, show both before and after
            if not show_before and not show_after:
                show_before = True
                show_after = True

        return {
            "enabled": enabled,
            "use_print": use_print,
            "use_log": use_log,
            "show_before": show_before,
            "show_after": show_after,
            "show_time": show_time,
        }

    def _output(self, message: str, level: str = "info", cfg: Optional[dict] = None):
        """
        Output message with auto-fallback.

        If use_log is True but logging is not configured (no handlers),
        automatically falls back to print().
        """
        if cfg is None:
            cfg = self._global_config

        if cfg["use_print"]:
            print(message)
        elif cfg["use_log"]:
            if self._logger.hasHandlers():
                # Logger configured -> use it
                getattr(self._logger, level)(message)
            else:
                # Logger not configured -> fallback to print
                print(message)

    def _format_args(self, args: tuple, kwargs: dict) -> str:
        """Format arguments for display."""
        parts = []
        if args:
            parts.extend(repr(arg) for arg in args)
        if kwargs:
            parts.extend(f"{k}={repr(v)}" for k, v in kwargs.items())
        return ", ".join(parts)

    def on_decorate(
        self,
        switch: "Switcher",
        func: Callable,
        entry: "MethodEntry",
    ) -> None:
        """
        Hook called when a function is decorated (no-op for LoggingPlugin).

        LoggingPlugin doesn't need to prepare anything during decoration,
        all work is done in wrap_handler() at call time.
        """
        pass

    def wrap_handler(
        self,
        switch: "Switcher",
        entry: "MethodEntry",
        call_next: Callable,
    ) -> Callable:
        """
        Wrap a handler function with logging.

        Args:
            switch: The Switcher instance
            entry: The method entry with metadata
            call_next: The next layer in the wrapper chain

        Returns:
            Wrapped function that logs calls
        """
        handler_name = entry.name

        # Get merged configuration for this method (uses BasePlugin's system)
        cfg = self.get_config(handler_name)

        # If disabled for this method, return passthrough
        if not cfg.get("enabled", True):
            return call_next

        def logged_wrapper(*args, **kwargs):
            # Log before call
            if cfg["show_before"]:
                args_str = self._format_args(args, kwargs)
                self._output(f"→ {handler_name}({args_str})", cfg=cfg)

            # Execute handler with optional timing
            start_time = time.time() if cfg["show_time"] else None
            exception = None
            result = None

            try:
                result = call_next(*args, **kwargs)
            except Exception as e:
                exception = e
                # Log exception
                if cfg["show_after"]:
                    time_str = ""
                    if start_time is not None:
                        elapsed = time.time() - start_time
                        time_str = f" ({elapsed:.4f}s)"
                    exc_type = type(e).__name__
                    msg = f"✗ {handler_name}() raised {exc_type}: {e}{time_str}"
                    self._output(msg, level="error", cfg=cfg)
                raise
            finally:
                # Log after call (if no exception)
                if exception is None and cfg["show_after"]:
                    time_str = ""
                    if start_time is not None:
                        elapsed = time.time() - start_time
                        time_str = f" ({elapsed:.4f}s)"
                    self._output(f"← {handler_name}() → {result}{time_str}", cfg=cfg)

            return result

        return logged_wrapper


# Register plugin globally
from ..core import Switcher  # noqa: E402

Switcher.register_plugin("logging", LoggingPlugin)
