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
    Python's logging system. Supports composable flags to control what is shown.

    Args:
        name: Plugin name (default: 'logger')
        mode: Composable mode flags (default: 'print')
              Output destination (required, mutually exclusive):
              - 'print': Use print() for output
              - 'log': Use Python logging (with auto-fallback to print)

              Content flags (optional, combinable):
              - 'before': Show input parameters
              - 'after': Show return value
              - 'time': Show execution time

              Default: If no content flags, shows both before and after.

              Examples:
              - 'print' → print input + output
              - 'print,time' → print input + output + timing
              - 'log,after' → log only output
              - 'print,before' → print only input

        logger: Custom logger instance. If None, uses logger named 'smartswitch'

    Examples:
        Basic usage (tutorial-friendly, no logging config needed):

        >>> sw = Switcher(plugins=[LoggingPlugin(mode='print')])
        >>> @sw
        ... def add(a, b):
        ...     return a + b
        >>> sw('add')(2, 3)
        → add(a=2, b=3)
        ← add() → 5
        5

        Show only output with timing:

        >>> sw = Switcher(plugins=[LoggingPlugin(mode='print,after,time')])
        >>> sw('add')(2, 3)
        ← add() → 5 (0.0001s)
        5

        With Python logging (auto-fallback if not configured):

        >>> sw = Switcher(plugins=[LoggingPlugin(mode='log,after')])
        >>> sw('add')(2, 3)  # Uses print() if logging not configured
        ← add() → 5
        5

        Full logging with timing:

        >>> import logging
        >>> logging.basicConfig(level=logging.INFO)
        >>> sw = Switcher(plugins=[LoggingPlugin(mode='log,before,after,time')])
        >>> sw('add')(2, 3)
        INFO:smartswitch:→ add(a=2, b=3)
        INFO:smartswitch:← add() → 5 (0.0001s)
        5
    """

    def __init__(
        self,
        name: Optional[str] = None,
        mode: str = "print",
        logger: Optional[logging.Logger] = None,
        **config: Any,
    ):
        """Initialize the logging plugin."""
        super().__init__(name=name or "logger", **config)

        # Parse mode flags
        flags = set(f.strip() for f in mode.split(","))

        # Output destination (required, mutually exclusive)
        self.use_print = "print" in flags
        self.use_log = "log" in flags

        if not self.use_print and not self.use_log:
            raise ValueError("mode must include 'print' or 'log'")
        if self.use_print and self.use_log:
            raise ValueError("mode cannot include both 'print' and 'log'")

        # Content flags (optional, combinable)
        self.show_before = "before" in flags
        self.show_after = "after" in flags
        self.show_time = "time" in flags

        # Default: if no content flags, show both before and after
        if not self.show_before and not self.show_after:
            self.show_before = True
            self.show_after = True

        self._logger = logger or logging.getLogger("smartswitch")

    def _output(self, message: str, level: str = "info"):
        """
        Output message with auto-fallback.

        If use_log is True but logging is not configured (no handlers),
        automatically falls back to print().
        """
        if self.use_print:
            print(message)
        elif self.use_log:
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

        def logged_wrapper(*args, **kwargs):
            # Log before call
            if self.show_before:
                args_str = self._format_args(args, kwargs)
                self._output(f"→ {handler_name}({args_str})")

            # Execute handler with optional timing
            start_time = time.time() if self.show_time else None
            exception = None
            result = None

            try:
                result = call_next(*args, **kwargs)
            except Exception as e:
                exception = e
                # Log exception
                if self.show_after:
                    time_str = ""
                    if start_time is not None:
                        elapsed = time.time() - start_time
                        time_str = f" ({elapsed:.4f}s)"
                    exc_type = type(e).__name__
                    msg = f"✗ {handler_name}() raised {exc_type}: {e}{time_str}"
                    self._output(msg, level="error")
                raise
            finally:
                # Log after call (if no exception)
                if exception is None and self.show_after:
                    time_str = ""
                    if start_time is not None:
                        elapsed = time.time() - start_time
                        time_str = f" ({elapsed:.4f}s)"
                    self._output(f"← {handler_name}() → {result}{time_str}")

            return result

        return logged_wrapper


# Register plugin globally
from ..core import Switcher  # noqa: E402

Switcher.register_plugin("logging", LoggingPlugin)
