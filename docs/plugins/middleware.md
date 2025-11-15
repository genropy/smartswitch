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

> **USE THIS AS YOUR TEMPLATE**: The `LoggingPlugin` is the canonical example of the middleware pattern in SmartSwitch. When creating your own plugins, follow this structure.

Let's dissect the LoggingPlugin in extreme detail to understand every aspect of the pattern.

### Complete Code with Detailed Annotations

```python
class LoggingPlugin:
    # Plugin name for attribute access: sw.logging.history()
    plugin_name = "logging"

    def __init__(self, mode='silent', time=True, max_history=10000, logger=None):
        """
        Plugin configuration (happens ONCE when plugin is created).

        This is NOT the middleware wrapper - this is plugin setup.
        """
        self.mode = mode                    # silent/log/both
        self.track_time = time              # Enable timing?
        self.max_history = max_history      # History buffer size
        self._logger = logger or logging.getLogger("smartswitch")
        self._history = []                  # In-memory call history
        self._log_file = None              # Optional file logging
        self._switcher = None              # Set by wrap()

    def wrap(self, func, switcher):
        """
        THE MIDDLEWARE FACTORY: Creates the wrapper for ONE function.

        This method is called ONCE per handler function during registration.
        It returns a wrapper that executes on EVERY call to that handler.

        Args:
            func: The handler function to wrap (e.g., process_order)
            switcher: The Switcher instance managing this handler

        Returns:
            A wrapper function that implements the middleware pattern
        """
        # Store switcher reference (needed for history queries)
        if self._switcher is None:
            self._switcher = switcher

        handler_name = func.__name__

        @wraps(func)
        def logged_wrapper(*args, **kwargs):
            """
            THE ACTUAL MIDDLEWARE: Runs on EVERY function call.

            This is where the bidirectional pattern happens:
            1. onCalling phase (before function)
            2. Function execution
            3. onCalled phase (after function)
            """

            # ================================================================
            # PHASE 1: onCalling (BEFORE function execution)
            # ================================================================
            # This code runs BEFORE the wrapped function.
            # Use for: validation, setup, logging entry, start timers

            # Create log entry with call metadata
            entry = {
                "handler": handler_name,
                "switcher": switcher.name,
                "timestamp": time.time(),      # When did call start?
                "args": args,                  # What arguments?
                "kwargs": kwargs,              # What keyword arguments?
            }

            # If mode is 'log' or 'both', log to Python logger NOW
            if self.mode in ("log", "both"):
                self._logger.info(
                    f"Calling {handler_name} with args={args}, kwargs={kwargs}"
                )

            # Start performance timer (if timing enabled)
            start_time = time.time() if self.track_time else None

            # Variables to capture result/exception
            exception = None
            result = None

            try:
                # ============================================================
                # PHASE 2: FUNCTION EXECUTION
                # ============================================================
                # The actual wrapped function executes here.
                # This is the "application" in the WSGI analogy.

                result = func(*args, **kwargs)

                # If we get here, function succeeded
                entry["result"] = result

                # ============================================================
                # PHASE 3a: onCalled (AFTER - SUCCESS path)
                # ============================================================
                # This code runs ONLY if function succeeded.
                # We already stored result in entry.

            except Exception as e:
                # ============================================================
                # PHASE 3b: onCalled (AFTER - ERROR path)
                # ============================================================
                # This code runs ONLY if function raised an exception.

                exception = e

                # Store exception details in log entry
                entry["exception"] = {
                    "type": type(e).__name__,    # Exception class name
                    "message": str(e),           # Error message
                }

                # CRITICAL: Re-raise to preserve error propagation
                # The caller needs to know the function failed!
                raise

            finally:
                # ============================================================
                # PHASE 3c: onCalled (ALWAYS executed)
                # ============================================================
                # This code runs REGARDLESS of success or failure.
                # Perfect for: cleanup, timing, history, file writes

                # Stop timer and calculate elapsed time
                if start_time is not None:
                    entry["elapsed"] = time.time() - start_time
                    elapsed_str = f" ({entry['elapsed']:.4f}s)"
                else:
                    elapsed_str = ""

                # Log result or error (if Python logging enabled)
                if self.mode in ("log", "both"):
                    if exception:
                        exc_type = type(exception).__name__
                        self._logger.error(
                            f"{handler_name} raised {exc_type}: "
                            f"{exception}{elapsed_str}"
                        )
                    else:
                        self._logger.info(
                            f"{handler_name} returned {result}{elapsed_str}"
                        )

                # Add to in-memory history (if mode is silent or both)
                if self.mode in ("silent", "both"):
                    self._history.append(entry)

                    # Maintain circular buffer (prevent memory leak)
                    if len(self._history) > self.max_history:
                        self._history.pop(0)  # Remove oldest

                # Write to log file if configured (real-time logging)
                if self._log_file:
                    try:
                        with open(self._log_file, "a") as f:
                            # Convert to JSON-serializable format
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

                            # Write as JSON Lines (one object per line)
                            f.write(json.dumps(serializable_entry) + "\n")
                    except Exception:
                        # IMPORTANT: Silently ignore file write errors
                        # Don't let logging failures crash the application!
                        pass

            # Return the result to the caller
            return result

        # Preserve original function (for introspection)
        logged_wrapper.__wrapped__ = func
        return logged_wrapper
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
      .plug('logging', mode='silent', time=True)
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
- `async` (async support)
- `retry` (retry logic)

### Why This Matters

The plugin name becomes the attribute for accessing it:

```python
# Plugin with plugin_name = "logging"
sw.logging.history()      # ✅ Clear: accessing logging functionality

# Plugin with plugin_name = "smartswitch-logger"
sw.smartswitch-logger.history()  # ❌ Redundant: we know it's SmartSwitch!
```

### External Package Naming

When publishing plugin packages to PyPI:

**Package name** (on PyPI): Can reference the ecosystem for discoverability
- ✅ `smartasync` (if part of SmartSwitch ecosystem)
- ✅ `gtext-cache` (if from gtext family)

**Plugin name** (in code): Should describe functionality only
- ✅ `plugin_name = "async"`
- ✅ `plugin_name = "cache"`

**Example**:

```python
# Package on PyPI: "smartasync"
# pip install smartasync

from smartasync import SmartAsyncPlugin

# Plugin name in code: just "async"
class SmartAsyncPlugin:
    plugin_name = "async"  # ✅ Not "smartasync"!

# Usage - attribute is clean
sw = Switcher().plug(SmartAsyncPlugin())
sw.async.is_async('my_handler')  # ✅ Clear
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

    def wrap(self, func, switcher):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # onCalling: Start timer
            start = time.time()
            status = "success"

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                # onCalled: Record metrics
                elapsed = time.time() - start
                self.duration_histogram.labels(handler=func.__name__).observe(elapsed)
                self.call_counter.labels(handler=func.__name__, status=status).inc()

        return wrapper
```

### 2. External Metrics: DataDog/StatsD

```python
from datadog import statsd

class DataDogPlugin:
    plugin_name = "metrics"  # ✅ Not "datadog"!

    def wrap(self, func, switcher):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # onCalling: Increment call counter
            statsd.increment(f'function.{func.__name__}.calls')
            start = time.time()

            try:
                result = func(*args, **kwargs)

                # onCalled (success): Mark as success
                statsd.increment(f'function.{func.__name__}.success')
                return result
            except Exception:
                # onCalled (error): Mark as error
                statsd.increment(f'function.{func.__name__}.error')
                raise
            finally:
                # onCalled (always): Send timing
                elapsed = time.time() - start
                statsd.histogram(f'function.{func.__name__}.duration', elapsed)

        return wrapper
```

### 3. Distributed Tracing: OpenTelemetry

```python
from opentelemetry import trace

class TracingPlugin:
    plugin_name = "tracing"  # ✅ Not "opentelemetry"!

    def __init__(self):
        self.tracer = trace.get_tracer(__name__)

    def wrap(self, func, switcher):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # onCalling: Start span
            with self.tracer.start_as_current_span(func.__name__) as span:
                span.set_attribute("function.args", str(args))
                span.set_attribute("function.kwargs", str(kwargs))

                try:
                    # Execute function
                    result = func(*args, **kwargs)

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
dev_sw = Switcher().plug('logging', mode='verbose')

# Production
prod_sw = (Switcher()
           .plug('logging', mode='silent')
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
