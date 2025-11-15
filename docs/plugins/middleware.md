# Plugin Middleware Pattern

## Overview

SmartSwitch plugins follow the **middleware pattern**, similar to WSGI middleware in web frameworks. This pattern allows you to wrap function execution with cross-cutting concerns (logging, metrics, caching, authentication) without modifying the function itself.

## The Middleware Analogy

If you're familiar with WSGI middleware, the concept is the same:

```text
Request  → Middleware 1 → Middleware 2 → Application → Response
           (onCalling)    (onCalling)                  (onCalled)
                                                       (onCalled)
```

With SmartSwitch plugins:

```text
Arguments → Plugin 1 → Plugin 2 → Function → Result
           (onCalling) (onCalling)          (onCalled)
                                            (onCalled)
```

**Key insight**: Execution flows through the plugin chain **twice**:
1. **Forward** (onCalling): Before function execution
2. **Backward** (onCalled): After function execution (in reverse order)

## Execution Phases

### Phase 1: onCalling (Before)

This is where you can:
- **Validate** arguments
- **Log** function entry with parameters
- **Start timing** for performance tracking
- **Check cache** before expensive operations
- **Record metrics** about invocations

### Phase 2: Function Execution

The actual function runs with the provided arguments.

### Phase 3: onCalled (After)

This is where you can:
- **Log** function exit with result
- **Stop timing** and calculate elapsed time
- **Save to cache** for future calls
- **Send metrics** to external systems
- **Handle errors** and log exceptions

## Reference Implementation: LoggingPlugin

> **USE THIS AS YOUR TEMPLATE**: The `LoggingPlugin` (v0.10.0+) is the canonical example of the middleware pattern in SmartSwitch. When creating your own plugins, follow this structure.

Let's dissect the LoggingPlugin in detail to understand the middleware pattern with **v0.10.0 Pydantic-based configuration**.

### Complete Code with Detailed Annotations

```python
from smartswitch import BasePlugin
from pydantic import BaseModel, Field
import time

class LoggingConfig(BaseModel):
    """Pydantic configuration model for LoggingPlugin."""
    enabled: bool = Field(default=False, description="Enable plugin")
    print: bool = Field(default=False, description="Use print() for output")
    log: bool = Field(default=True, description="Use Python logging")
    before: bool = Field(default=True, description="Show input parameters")
    after: bool = Field(default=False, description="Show return value")
    time: bool = Field(default=False, description="Show execution time")

class LoggingPlugin(BasePlugin):
    """Real-time call logging with Pydantic configuration."""

    config_model = LoggingConfig  # Pydantic model for validation

    def __init__(self, name=None, logger=None, **kwargs):
        """
        Plugin initialization (happens ONCE when plugin is created).

        BasePlugin handles all Pydantic configuration via **kwargs.
        """
        super().__init__(name=name or "logger", **kwargs)
        self._logger = logger or logging.getLogger("smartswitch")

    def wrap_handler(self, switch, entry, call_next):
        """
        THE MIDDLEWARE FACTORY: Creates the wrapper for ONE function.

        This method is called ONCE per handler during registration.
        It returns a wrapper that executes on EVERY call to that handler.

        Args:
            switch: The Switcher instance
            entry: MethodEntry with handler metadata
            call_next: The next layer in the middleware chain

        Returns:
            A wrapper function that implements the middleware pattern
        """
        handler_name = entry.name

        def logged_wrapper(*args, **kwargs):
            """
            THE ACTUAL MIDDLEWARE: Runs on EVERY function call.

            This is where the bidirectional pattern happens:
            1. onCalling phase (before function)
            2. Function execution (via call_next)
            3. onCalled phase (after function)
            """

            # ================================================================
            # PHASE 1: onCalling (BEFORE function execution)
            # ================================================================
            # Get runtime config (supports dynamic changes!)
            cfg = self.get_config(handler_name)

            # If disabled, skip all processing
            if not cfg.get("enabled"):
                return call_next(*args, **kwargs)

            # Log BEFORE if configured
            if cfg.get("before"):
                args_str = self._format_args(args, kwargs)
                self._output(f"→ {handler_name}({args_str})", cfg=cfg)

            # Start performance timer if configured
            start_time = time.time() if cfg.get("time") else None

            # Variables to capture result/exception
            exception = None
            result = None

            try:
                # ============================================================
                # PHASE 2: FUNCTION EXECUTION (via call_next)
                # ============================================================
                # Call the next layer in the middleware chain
                result = call_next(*args, **kwargs)


            except Exception as e:
                # ============================================================
                # PHASE 3b: onCalled (AFTER - ERROR path)
                # ============================================================
                # This code runs ONLY if function raised an exception.
                exception = e

                # Log exception if configured
                if cfg.get("after"):
                    time_str = ""
                    if start_time is not None:
                        elapsed = time.time() - start_time
                        time_str = f" ({elapsed:.4f}s)"
                    exc_type = type(e).__name__
                    msg = f"✗ {handler_name}() raised {exc_type}: {e}{time_str}"
                    self._output(msg, level="error", cfg=cfg)

                # CRITICAL: Re-raise to preserve error propagation
                raise

            finally:
                # ============================================================
                # PHASE 3c: onCalled (AFTER - SUCCESS path in finally)
                # ============================================================
                # Log result AFTER function succeeds (if no exception)
                if exception is None and cfg.get("after"):
                    time_str = ""
                    if start_time is not None:
                        elapsed = time.time() - start_time
                        time_str = f" ({elapsed:.4f}s)"
                    self._output(f"← {handler_name}() → {result}{time_str}", cfg=cfg)

            # Return the result to the caller
            return result

        return logged_wrapper

    def _format_args(self, args, kwargs):
        """Helper: Format arguments for display."""
        parts = []
        if args:
            parts.extend(repr(arg) for arg in args)
        if kwargs:
            parts.extend(f"{k}={repr(v)}" for k, v in kwargs.items())
        return ", ".join(parts)

    def _output(self, message, level="info", cfg=None):
        """Helper: Output message to print or logger."""
        if cfg is None:
            cfg = self._global_config

        if cfg.get("print"):
            print(message)
        elif cfg.get("log"):
            if self._logger.hasHandlers():
                getattr(self._logger, level)(message)
            else:
                # Fallback to print if logger not configured
                print(message)
```

### Execution Flow Diagram

```text
User calls: sw('process_order')('ORD-123')
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ LoggingPlugin.logged_wrapper()  [MIDDLEWARE STARTS]         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌────────────────────────────────────────────────────┐     │
│ │ PHASE 1: onCalling (BEFORE)                        │     │
│ │                                                     │     │
│ │ • Create entry dict                                │     │
│ │   {"handler": "process_order",                     │     │
│ │    "timestamp": 1699123456.789,                    │     │
│ │    "args": ("ORD-123",),                           │     │
│ │    "kwargs": {}}                                   │     │
│ │                                                     │     │
│ │ • IF mode in ('log', 'both'):                      │     │
│ │   → logger.info("Calling process_order...")        │     │
│ │                                                     │     │
│ │ • start_time = time.time()                         │     │
│ │   → 1699123456.789                                 │     │
│ └────────────────────────────────────────────────────┘     │
│                         ↓                                   │
│ ┌────────────────────────────────────────────────────┐     │
│ │ PHASE 2: FUNCTION EXECUTION                        │     │
│ │                                                     │     │
│ │ result = process_order("ORD-123")                  │     │
│ │                                                     │     │
│ │ [Business logic executes here]                     │     │
│ │ [Could be API calls, DB queries, calculations]     │     │
│ │                                                     │     │
│ │ → Returns: {"order_id": "ORD-123", "status": "ok"} │     │
│ └────────────────────────────────────────────────────┘     │
│                         ↓                                   │
│ ┌────────────────────────────────────────────────────┐     │
│ │ PHASE 3: onCalled (AFTER - SUCCESS)                │     │
│ │                                                     │     │
│ │ • entry["result"] = result                         │     │
│ │   → {"order_id": "ORD-123", "status": "ok"}        │     │
│ │                                                     │     │
│ │ • [finally block ALWAYS runs]                      │     │
│ │                                                     │     │
│ │ • entry["elapsed"] = time.time() - start_time      │     │
│ │   → 0.1523 seconds                                 │     │
│ │                                                     │     │
│ │ • IF mode in ('log', 'both'):                      │     │
│ │   → logger.info("process_order returned {...}")    │     │
│ │                                                     │     │
│ │ • IF mode in ('silent', 'both'):                   │     │
│ │   → self._history.append(entry)                    │     │
│ │                                                     │     │
│ │ • IF self._log_file:                               │     │
│ │   → Write JSON line to file                        │     │
│ └────────────────────────────────────────────────────┘     │
│                         ↓                                   │
│ return result                                               │
└─────────────────────────────────────────────────────────────┘
                    ↓
Result returned to caller: {"order_id": "ORD-123", "status": "ok"}
```

### Error Flow Diagram

```text
User calls: sw('process_order')('BAD-ID')
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ LoggingPlugin.logged_wrapper()                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌────────────────────────────────────────────────────┐     │
│ │ PHASE 1: onCalling (BEFORE)                        │     │
│ │                                                     │     │
│ │ • entry = {"handler": "process_order", ...}        │     │
│ │ • start_time = 1699123456.789                      │     │
│ └────────────────────────────────────────────────────┘     │
│                         ↓                                   │
│ ┌────────────────────────────────────────────────────┐     │
│ │ PHASE 2: FUNCTION EXECUTION                        │     │
│ │                                                     │     │
│ │ result = process_order("BAD-ID")                   │     │
│ │                                                     │     │
│ │ [Function raises ValueError]                       │     │
│ │ → raise ValueError("Invalid order ID")             │     │
│ └────────────────────────────────────────────────────┘     │
│                         ↓                                   │
│ ┌────────────────────────────────────────────────────┐     │
│ │ PHASE 3: onCalled (AFTER - ERROR)                  │     │
│ │                                                     │     │
│ │ • [except Exception as e block runs]               │     │
│ │                                                     │     │
│ │ • exception = e                                    │     │
│ │                                                     │     │
│ │ • entry["exception"] = {                           │     │
│ │     "type": "ValueError",                          │     │
│ │     "message": "Invalid order ID"                  │     │
│ │   }                                                │     │
│ │                                                     │     │
│ │ • raise  [RE-THROW EXCEPTION]                      │     │
│ │                                                     │     │
│ │ • [finally block ALWAYS runs BEFORE re-throw]      │     │
│ │                                                     │     │
│ │ • entry["elapsed"] = 0.0012                        │     │
│ │                                                     │     │
│ │ • logger.error("process_order raised ValueError")  │     │
│ │                                                     │     │
│ │ • self._history.append(entry)                      │     │
│ │   [Entry now has "exception" key, no "result"]     │     │
│ │                                                     │     │
│ │ • Write to log file                                │     │
│ └────────────────────────────────────────────────────┘     │
│                         ↓                                   │
│ Exception propagates to caller                              │
└─────────────────────────────────────────────────────────────┘
                    ↓
ValueError: Invalid order ID  [caller receives this]
```

### Key Implementation Details

#### 1. Why `try/except/finally`?

```python
try:
    result = func(*args, **kwargs)      # May succeed or fail
    entry["result"] = result            # Only runs if success
except Exception as e:
    entry["exception"] = {...}          # Only runs if error
    raise                               # CRITICAL: re-throw
finally:
    # ALWAYS runs - perfect for:
    # • Stopping timers
    # • Writing to history
    # • Writing to files
    # • Cleanup operations
```

**Why this matters**:
- `finally` guarantees logging happens even if function crashes
- Re-raising exception preserves error propagation (caller knows function failed)
- Entry has either `"result"` OR `"exception"` key, never both

#### 2. The Three Modes

```python
if self.mode in ("log", "both"):
    self._logger.info(...)              # Python logging

if self.mode in ("silent", "both"):
    self._history.append(entry)         # In-memory history
```

**Mode comparison**:

| Mode | Python Logging | In-Memory History | Use Case |
|------|----------------|-------------------|----------|
| `silent` | ❌ No | ✅ Yes | Production (zero overhead) |
| `log` | ✅ Yes | ❌ No | Traditional logging |
| `both` | ✅ Yes | ✅ Yes | Development/debugging |

#### 3. Timing Implementation

```python
# onCalling: Start timer
start_time = time.time() if self.track_time else None

# onCalled (finally): Calculate elapsed
if start_time is not None:
    entry["elapsed"] = time.time() - start_time
```

**Why conditional**:
- `track_time=False` → No timing overhead
- `track_time=True` → Precise timing with `time.time()`

#### 4. Circular Buffer for History

```python
self._history.append(entry)

# Prevent memory leak
if len(self._history) > self.max_history:
    self._history.pop(0)  # Remove oldest
```

**Why this matters**:
- Without limit: memory grows unbounded
- With limit: keeps last N calls (FIFO)
- Default 10,000 entries ≈ reasonable for most apps

#### 5. Silent File Write Failures

```python
if self._log_file:
    try:
        with open(self._log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Silently ignore
```

**Why silent**:
- Logging should NEVER crash the application
- If disk full, permission denied, etc. → continue running
- Main function result is more important than logging

## Chain of Execution with Multiple Plugins

When multiple plugins are registered:

```python
sw = (Switcher()
      .plug('logging', flags='print,enabled,after,time')
      .plug('metrics')
      .plug('cache'))

@sw
def add(a, b):
    return a + b

result = sw('add')(2, 3)
```

**Execution flow:**

```text
User: add(2, 3)
    ↓
┌─────────────────────────────────────────────────────────┐
│ LoggingPlugin (outer layer)                             │
│   ┌─────────────────────────────────────────────────┐   │
│   │ onCalling: entry={...}, start_time=...         │   │
│   └─────────────────────────────────────────────────┘   │
│                       ↓                                  │
│   ┌─────────────────────────────────────────────────────┐
│   │ MetricsPlugin (middle layer)                       │
│   │   ┌────────────────────────────────────────────┐   │
│   │   │ onCalling: counter++, start_timer          │   │
│   │   └────────────────────────────────────────────┘   │
│   │                   ↓                                 │
│   │   ┌─────────────────────────────────────────────────┐
│   │   │ CachePlugin (inner layer)                      │
│   │   │   ┌────────────────────────────────────────┐   │
│   │   │   │ onCalling: check cache → miss          │   │
│   │   │   └────────────────────────────────────────┘   │
│   │   │                   ↓                             │
│   │   │   ╔════════════════════════════════════════╗   │
│   │   │   ║ add(2, 3)  [ACTUAL FUNCTION]          ║   │
│   │   │   ║ return 5                               ║   │
│   │   │   ╚════════════════════════════════════════╝   │
│   │   │                   ↓                             │
│   │   │   ┌────────────────────────────────────────┐   │
│   │   │   │ onCalled: cache[key] = 5               │   │
│   │   │   └────────────────────────────────────────┘   │
│   │   └─────────────────────────────────────────────────┘
│   │                   ↓                                 │
│   │   ┌────────────────────────────────────────────┐   │
│   │   │ onCalled: histogram.observe(elapsed)       │   │
│   │   └────────────────────────────────────────────┘   │
│   └─────────────────────────────────────────────────────┘
│                       ↓                                  │
│   ┌─────────────────────────────────────────────────┐   │
│   │ onCalled: history.append(), elapsed=0.0001s    │   │
│   └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
    ↓
Result: 5
```

**Key insight**: Plugins execute like **onion layers**:
1. **Outer → Inner** (onCalling): LoggingPlugin → MetricsPlugin → CachePlugin
2. **Function executes** (center of onion)
3. **Inner → Outer** (onCalled): CachePlugin → MetricsPlugin → LoggingPlugin

## Plugin Naming Guidelines

### Rule: Name by Function, Not by Framework

**❌ BAD - Names reference SmartSwitch**:
- `smartswitch-logger`
- `smartswitch-metrics`
- `switcher-cache`

**✅ GOOD - Names describe what plugin does**:
- `logger` (logs function calls)
- `metrics` (collects metrics)
- `cache` (caches results)
- `validation` (validates inputs)
- `retry` (retry logic)

### Why This Matters

The plugin name becomes the attribute for accessing it:

```python
# Plugin with plugin_name = "logging"

# Plugin with plugin_name = "smartswitch-logger"
```

### External Package Naming

When publishing plugin packages to PyPI:

**Package name** (on PyPI): Can reference the ecosystem for discoverability
- ✅ `smartcache` (if part of SmartSwitch ecosystem)
- ✅ `gtext-validation` (if from gtext family)

**Plugin name** (in code): Should describe functionality only
- ✅ `plugin_name = "cache"`
- ✅ `plugin_name = "validation"`

**Example**:

```python
# Package on PyPI: "smartcache"
# pip install smartcache

from smartcache import SmartCachePlugin

# Plugin name in code: just "cache"
class SmartCachePlugin(BasePlugin):
    def __init__(self, **kwargs):
        super().__init__(name="cache", **kwargs)  # ✅ Not "smartcache"!

# Usage - attribute is clean
Switcher.register_plugin('cache', SmartCachePlugin)
sw = Switcher().plug('cache')
sw.cache.clear()  # ✅ Clear
```

## Use Cases and Examples

### 1. External Metrics: Prometheus

```python
from prometheus_client import Counter, Histogram

class PrometheusPlugin:
    plugin_name = "metrics"  # ✅ Not "prometheus"!

    def __init__(self):
        self.call_counter = Counter(
            'function_calls_total',
            'Total function calls',
            ['handler', 'status']
        )
        self.duration_histogram = Histogram(
            'function_duration_seconds',
            'Function execution time',
            ['handler']
        )

    def wrap_handler(self, switch, entry, call_next):
        handler_name = entry.name

        def wrapper(*args, **kwargs):
            # onCalling: Start timer
            start = time.time()
            status = "success"

            try:
                result = call_next(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                # onCalled: Record metrics
                elapsed = time.time() - start
                self.duration_histogram.labels(handler=handler_name).observe(elapsed)
                self.call_counter.labels(handler=handler_name, status=status).inc()

        return wrapper
```

### 2. External Metrics: DataDog/StatsD

```python
from datadog import statsd

class DataDogPlugin(BasePlugin):
    def __init__(self, **kwargs):
        super().__init__(name="metrics", **kwargs)  # ✅ Not "datadog"!

    def wrap_handler(self, switch, entry, call_next):
        handler_name = entry.name

        def wrapper(*args, **kwargs):
            # onCalling: Increment call counter
            statsd.increment(f'function.{handler_name}.calls')
            start = time.time()

            try:
                result = call_next(*args, **kwargs)

                # onCalled (success): Mark as success
                statsd.increment(f'function.{handler_name}.success')
                return result
            except Exception:
                # onCalled (error): Mark as error
                statsd.increment(f'function.{handler_name}.error')
                raise
            finally:
                # onCalled (always): Send timing
                elapsed = time.time() - start
                statsd.histogram(f'function.{handler_name}.duration', elapsed)

        return wrapper
```

### 3. Distributed Tracing: OpenTelemetry

```python
from opentelemetry import trace

class TracingPlugin(BasePlugin):
    def __init__(self, **kwargs):
        super().__init__(name="tracing", **kwargs)  # ✅ Not "opentelemetry"!
        self.tracer = trace.get_tracer(__name__)

    def wrap_handler(self, switch, entry, call_next):
        handler_name = entry.name

        def wrapper(*args, **kwargs):
            # onCalling: Start span
            with self.tracer.start_as_current_span(handler_name) as span:
                span.set_attribute("function.args", str(args))
                span.set_attribute("function.kwargs", str(kwargs))

                try:
                    # Execute function
                    result = call_next(*args, **kwargs)

                    # onCalled (success): Mark span as success
                    span.set_attribute("function.result", str(result))
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    # onCalled (error): Record error in span
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                    span.record_exception(e)
                    raise

        return wrapper
```

## Why Plugins Are Useful

### 1. **Separation of Concerns**

Business logic stays clean:

```python
@sw
def process_order(order_id: str):
    # ONLY business logic - no logging, metrics, etc.
    return f"Processed {order_id}"
```

### 2. **Composability**

Mix and match as needed:

```python
# Development
dev_sw = Switcher().plug('logging', flags='print,enabled,before,after,time')

# Production
prod_sw = (Switcher()
           .plug('logging', flags='print,enabled')
           .plug(PrometheusPlugin())
           .plug('cache'))
```

### 3. **Zero Code Modification**

Add cross-cutting concerns without touching functions:

```python
# Original code unchanged
@sw
def add(a, b):
    return a + b

# Just configure plugins
sw.plug('logging')
sw.plug(PrometheusPlugin())
```

### 4. **Reusability**

Write once, use everywhere:

```python
prometheus_plugin = PrometheusPlugin()

api_sw = Switcher().plug(prometheus_plugin)
worker_sw = Switcher().plug(prometheus_plugin)
scheduler_sw = Switcher().plug(prometheus_plugin)
```

## Summary

The middleware pattern in SmartSwitch plugins provides:

1. **Bidirectional wrapping**: onCalling → function → onCalled
2. **Clean separation**: Business logic vs cross-cutting concerns
3. **Composability**: Stack multiple plugins
4. **Error safety**: `try/except/finally` ensures cleanup
5. **Flexibility**: Configure per-environment

**Use LoggingPlugin as your reference implementation** - it demonstrates all best practices:
- Clear phase separation
- Proper exception handling
- Optional features (timing, file logging)
- Memory management (circular buffer)
- Silent error handling (file writes)

When creating plugins, follow this structure and you'll have robust, production-ready middleware.
