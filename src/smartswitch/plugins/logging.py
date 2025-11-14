"""
Switcher Logging Plugin.

Provides call history tracking and performance monitoring for Switcher handlers.
"""

import json
import logging
import time
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ..core import Switcher, MethodEntry

from ..core import BasePlugin


class LoggingPlugin(BasePlugin):
    """
    Switcher plugin for call history and performance tracking.

    Tracks all handler calls with optional timing information. Supports
    three modes: silent (history only), log (Python logging), or both.

    The plugin maintains a circular buffer of call history and can log to
    both Python's logging system and optionally to a JSON file.

    Args:
        name: Plugin name (default: 'logger')
        mode: Logging mode - 'silent', 'log', or 'both' (default: 'silent')
              - 'silent': Track in history only, no external logging
              - 'log': Use Python logging only
              - 'both': Track in history AND use Python logging
        time: Track execution time for each call (default: True)
        max_history: Maximum number of history entries to keep (default: 10000)
        logger: Custom logger instance. If None, creates logger named 'smartswitch'

    Examples:
        Basic usage with silent mode (history only):

        >>> sw = Switcher().plug('logging', mode='silent', time=True)
        >>> @sw
        ... def my_handler(x):
        ...     return x * 2
        >>> sw('my_handler')(5)
        10
        >>> history = sw.logger.history()
        >>> print(history[0]['handler'], history[0]['elapsed'])
        my_handler 0.0001

        With Python logging enabled:

        >>> sw = Switcher().plug('logging', mode='log', time=True)
        >>> @sw
        ... def process_data(data):
        ...     return len(data)
        >>> sw('process_data')([1, 2, 3])  # Logs to Python logger
        3

        Query history by handler:

        >>> sw = Switcher().plug('logging', mode='silent')
        >>> @sw
        ... def fast(): time.sleep(0.01)
        >>> @sw
        ... def slow(): time.sleep(0.1)
        >>> sw('fast')()
        >>> sw('slow')()
        >>> history = sw.logger.history(handler='slow')
        >>> len(history)
        1

        Get slowest calls:

        >>> history = sw.logger.history(slowest=5)
        >>> for entry in history:
        ...     print(f"{entry['handler']}: {entry['elapsed']:.3f}s")

        Filter by execution time:

        >>> history = sw.logger.history(slower_than=0.05)  # > 50ms
        >>> history = sw.logger.history(fastest=10)  # 10 fastest

        Export to file:

        >>> sw.logger.export('calls.json')
        >>> sw.logger.set_file('calls.jsonl')  # Enable real-time logging

    Attributes:
        mode: Current logging mode
        track_time: Whether timing is enabled
        max_history: Maximum history entries
        _logger: Logger instance
        _history: List of call entries
        _log_file: Optional file path for real-time logging
    """

    def __init__(
        self,
        name: Optional[str] = None,
        mode: str = "silent",
        time: bool = True,
        max_history: int = 10000,
        logger: Optional[logging.Logger] = None,
        **config: Any,
    ):
        """Initialize the logging plugin."""
        super().__init__(name=name or "logger", **config)

        if mode not in ("silent", "log", "both"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'silent', 'log', or 'both'")

        self.mode = mode
        self.track_time = time
        self.max_history = max_history
        self._logger = logger or logging.getLogger("smartswitch")
        self._history: list[dict] = []
        self._log_file: Optional[str] = None

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

        Args:
            switch: The Switcher instance
            func: The handler function being decorated
            entry: The method entry with metadata
        """
        # No preparation needed for logging - everything happens at call time
        pass

    def wrap_handler(
        self,
        switch: "Switcher",
        entry: "MethodEntry",
        call_next: Callable,
    ) -> Callable:
        """
        Wrap a handler function with logging/history tracking.

        This method is called by Switcher when building the wrapper chain.
        It wraps the call_next function to track calls, timing, and errors.

        Args:
            switch: The Switcher instance
            entry: The method entry with metadata
            call_next: The next layer in the wrapper chain

        Returns:
            Wrapped function that logs calls
        """
        handler_name = entry.name
        switch_name = switch.name

        def logged_wrapper(*args, **kwargs):
            # Prepare log entry
            log_entry = {
                "handler": handler_name,
                "switcher": switch_name,
                "timestamp": time.time(),
                "args": args,
                "kwargs": kwargs,
            }

            # Log before if enabled
            if self.mode in ("log", "both"):
                self._logger.info(f"Calling {handler_name} with args={args}, kwargs={kwargs}")

            # Execute handler and measure time
            start_time = time.time() if self.track_time else None
            exception = None
            result = None

            try:
                result = call_next(*args, **kwargs)
                log_entry["result"] = result
            except Exception as e:
                exception = e
                log_entry["exception"] = {
                    "type": type(e).__name__,
                    "message": str(e),
                }
                raise
            finally:
                # Add elapsed time if enabled
                if start_time is not None:
                    log_entry["elapsed"] = time.time() - start_time
                    elapsed_str = f" ({log_entry['elapsed']:.4f}s)"
                else:
                    elapsed_str = ""

                # Log after (if enabled)
                if self.mode in ("log", "both"):
                    if exception:
                        exc_type = type(exception).__name__
                        self._logger.error(
                            f"{handler_name} raised {exc_type}: {exception}{elapsed_str}"
                        )
                    else:
                        self._logger.info(f"{handler_name} returned {result}{elapsed_str}")

                # Add to history (if mode is silent or both)
                if self.mode in ("silent", "both"):
                    self._history.append(log_entry)
                    # Maintain max_history limit
                    if len(self._history) > self.max_history:
                        self._history.pop(0)

                # Write to log file if configured
                if self._log_file:
                    try:
                        with open(self._log_file, "a") as f:
                            # Convert to JSON-serializable format
                            serializable_entry = {
                                "handler": log_entry["handler"],
                                "switcher": log_entry["switcher"],
                                "timestamp": log_entry["timestamp"],
                                "args": str(log_entry["args"]),
                                "kwargs": str(log_entry["kwargs"]),
                            }
                            if "result" in log_entry:
                                serializable_entry["result"] = str(log_entry["result"])
                            if "exception" in log_entry:
                                serializable_entry["exception"] = log_entry["exception"]
                            if "elapsed" in log_entry:
                                serializable_entry["elapsed"] = log_entry["elapsed"]

                            f.write(json.dumps(serializable_entry) + "\n")
                    except Exception:
                        # Silently ignore file write errors
                        pass

            return result

        return logged_wrapper

    def history(
        self,
        last: Optional[int] = None,
        first: Optional[int] = None,
        handler: Optional[str] = None,
        slowest: Optional[int] = None,
        fastest: Optional[int] = None,
        errors: Optional[bool] = None,
        slower_than: Optional[float] = None,
    ) -> list[dict]:
        """
        Query the log history with various filters.

        Args:
            last: Return last N entries
            first: Return first N entries
            handler: Filter by handler name
            slowest: Return N slowest executions (requires timing enabled)
            fastest: Return N fastest executions (requires timing enabled)
            errors: If True, return only errors; if False, return only successes
            slower_than: Return entries with elapsed time > threshold (seconds)

        Returns:
            List of log entries matching the filters

        Examples:
            >>> sw.logger.history(last=10)  # Last 10 calls
            >>> sw.logger.history(handler='my_handler')  # Specific handler
            >>> sw.logger.history(slowest=5)  # 5 slowest calls
            >>> sw.logger.history(errors=True)  # Only failed calls
            >>> sw.logger.history(slower_than=0.1)  # Calls > 100ms
        """
        result = self._history.copy()

        # Filter by handler
        if handler:
            result = [e for e in result if e["handler"] == handler]

        # Filter by errors
        if errors is not None:
            if errors:
                result = [e for e in result if "exception" in e]
            else:
                result = [e for e in result if "exception" not in e]

        # Filter by execution time
        if slower_than is not None:
            result = [e for e in result if e.get("elapsed", 0) > slower_than]

        # Sort by time if needed for slowest/fastest
        if slowest is not None or fastest is not None:
            # Filter entries that have timing
            result = [e for e in result if "elapsed" in e]
            result.sort(key=lambda e: e["elapsed"])

            if slowest is not None:
                result = result[-slowest:][::-1]  # Slowest N (descending)
            elif fastest is not None:
                result = result[:fastest]  # Fastest N (ascending)

        # Apply first/last filters
        if first is not None:
            result = result[:first]
        if last is not None:
            result = result[-last:]

        return result

    def clear(self):
        """Clear all log history."""
        self._history.clear()

    def export(self, filepath: str):
        """
        Export log history to a JSON file.

        Args:
            filepath: Path to output JSON file

        Example:
            >>> sw.logger.export('calls.json')
        """
        with open(filepath, "w") as f:
            # Convert entries to JSON-serializable format
            serializable_entries = []
            for entry in self._history:
                serializable_entry = {
                    "handler": entry["handler"],
                    "switcher": entry["switcher"],
                    "timestamp": entry["timestamp"],
                    "args": str(entry["args"]),
                    "kwargs": str(entry["kwargs"]),
                }
                if "result" in entry:
                    serializable_entry["result"] = str(entry["result"])
                if "exception" in entry:
                    serializable_entry["exception"] = entry["exception"]
                if "elapsed" in entry:
                    serializable_entry["elapsed"] = entry["elapsed"]

                serializable_entries.append(serializable_entry)

            json.dump(serializable_entries, f, indent=2)

    def set_file(self, filepath: Optional[str]):
        """
        Configure real-time logging to a file.

        When enabled, each call is appended to the file in JSON Lines format
        (one JSON object per line) immediately after execution.

        Args:
            filepath: Path to log file, or None to disable file logging

        Example:
            >>> sw.logger.set_file('calls.jsonl')
            >>> sw.logger.set_file(None)  # Disable
        """
        self._log_file = filepath

    def set_mode(self, mode: str):
        """
        Change the logging mode.

        Args:
            mode: New mode - 'silent', 'log', or 'both'

        Example:
            >>> sw.logger.set_mode('log')  # Enable Python logging
            >>> sw.logger.set_mode('silent')  # Disable, track history only
        """
        if mode not in ("silent", "log", "both"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'silent', 'log', or 'both'")
        self.mode = mode


# Register plugin globally
from ..core import Switcher
Switcher.register_plugin("logging", LoggingPlugin)
