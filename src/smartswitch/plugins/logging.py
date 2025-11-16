"""
Switcher Logging Plugin.

Provides real-time output for handler calls with composable display flags.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

if TYPE_CHECKING:
    from ..core import MethodEntry, Switcher

from ..core import BasePlugin

try:
    from pydantic import BaseModel, Field

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Fallback for when Pydantic is not available
    BaseModel = object  # type: ignore

    def Field(*args, **kwargs):  # type: ignore  # noqa: N802
        return kwargs.get("default")


class LoggingConfig(BaseModel if PYDANTIC_AVAILABLE else object):  # type: ignore
    """
    Configuration model for LoggingPlugin.

    All boolean flags can be set via the 'flags' parameter:
        flags='print,enabled,after'  →  print=True, enabled=True, after=True
        flags='print:off,log'        →  print=False, log=True
    """

    # State flag
    enabled: bool = Field(default=False, description="Enable plugin")

    # Output destination (mutually exclusive in practice)
    print: bool = Field(default=False, description="Use print() for output")
    log: bool = Field(default=True, description="Use Python logging")

    # Content flags
    before: bool = Field(default=True, description="Show input parameters")
    after: bool = Field(default=False, description="Show return value")
    time: bool = Field(default=False, description="Show execution time")

    # Per-method overrides (handled by BasePlugin)
    methods: Optional[Dict[str, "LoggingConfig"]] = Field(
        default=None, description="Per-method configuration overrides"
    )

    if PYDANTIC_AVAILABLE:

        class Config:
            """Pydantic model configuration."""

            extra = "forbid"  # Reject unknown fields


class LoggingPlugin(BasePlugin):
    """
    Switcher plugin for real-time handler logging with Pydantic configuration.

    Displays handler calls and results in real-time using either print() or
    Python's logging system. Supports composable flags and granular per-method
    configuration.

    Configuration:
        Use 'flags' parameter for boolean settings:
            flags='print,enabled,after,time'

        Or use individual parameters:
            print=True, enabled=True, after=True

        Available flags:
            - enabled: Enable plugin (default: False)
            - print: Use print() for output
            - log: Use Python logging (default: True)
            - before: Show input parameters
            - after: Show return value
            - time: Show execution time

    Examples:
        Basic usage with flags:

        >>> sw = Switcher().plug('logging', flags='print,enabled')
        >>> @sw
        ... def add(a, b):
        ...     return a + b
        >>> sw('add')(2, 3)
        → add(2, 3)
        ← add() → 5
        5

        Per-method configuration:

        >>> sw = Switcher().plug('logging', flags='print,enabled', method_config={
        ...     'calculate': 'after,time',
        ...     'internal': 'enabled:off'
        ... })

        Runtime configuration:

        >>> sw.logging.configure.flags = 'log,enabled,time'
        >>> sw.logging.configure['calculate'].flags = 'enabled:off'
    """

    config_model = LoggingConfig

    def __init__(
        self,
        name: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        **kwargs: Any,
    ):
        """
        Initialize the logging plugin.

        Args:
            name: Plugin instance name (default: 'logger')
            logger: Custom logger instance (default: logger named 'smartswitch')
            **kwargs: Configuration parameters (flags, print, enabled, etc.)
        """
        # Let BasePlugin handle all configuration via Pydantic
        super().__init__(name=name or "logger", **kwargs)

        # Set logger
        self._logger = logger or logging.getLogger("smartswitch")

    def _output(self, message: str, level: str = "info", cfg: Optional[dict] = None):
        """
        Output message with auto-fallback.

        If log is True but logging is not configured (no handlers),
        automatically falls back to print().
        """
        if cfg is None:
            cfg = self._global_config

        if cfg.get("print"):
            print(message)
        elif cfg.get("log"):
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

    def on_decore(
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
            # Get merged configuration at runtime (dynamic config)
            cfg = self.get_config(handler_name)

            # If disabled for this method, return passthrough
            if not cfg.get("enabled", True):
                return call_next(*args, **kwargs)

            # Log before call
            if cfg.get("before"):
                args_str = self._format_args(args, kwargs)
                self._output(f"→ {handler_name}({args_str})", cfg=cfg)

            # Execute handler with optional timing
            start_time = time.time() if cfg.get("time") else None
            exception = None
            result = None

            try:
                result = call_next(*args, **kwargs)
            except Exception as e:
                exception = e
                # Log exception
                if cfg.get("after"):
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
                if exception is None and cfg.get("after"):
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
