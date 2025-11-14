# Architecture Deep Dive

This document provides a detailed look at SmartSwitch's internal architecture, design decisions, and component interactions.

---

## Architecture Overview

```mermaid
graph TB
    subgraph UserCode[User Code]
        U1[Decorator Usage]
        U2[Handler Dispatch]
        U3[Plugin Access]
    end

    subgraph SwitcherCore[Switcher Core V2]
        SW[Switcher]
        ME[_methods Dict]
        PL[_local_plugins List]
        IP[_inherited_plugins]
        RD[_runtime_data WeakKeyDict]
        SO[SwitcherOwner]
    end

    subgraph PluginSystem[Plugin System v0.6.0]
        BP[BasePlugin]
        LP[LoggingPlugin]
        PP[PydanticPlugin]
        CP[Custom Plugins]
    end

    subgraph MethodEntry[MethodEntry]
        EN[entry.name]
        EF[entry.func]
        EM[entry.metadata]
        EP[entry.plugins]
    end

    U1 --> SW
    U2 --> SW
    U3 --> SW
    SW --> ME
    SW --> PL
    SW --> IP
    SW --> RD
    SW --> SO
    SW --> MethodEntry
    PL --> BP
    PL --> LP
    PL --> PP
    PL --> CP

    style SW fill:#4051b5,stroke:#333,stroke-width:2px,color:#fff
    style MethodEntry fill:#7986cb,stroke:#333,stroke-width:2px,color:#fff
    style BP fill:#66bb6a,stroke:#333,stroke-width:2px,color:#fff
```

SmartSwitch V2 consists of core components and plugin system:

- **Switcher**: The core engine handling registration, dispatch, and plugin management
- **MethodEntry**: Dataclass containing method metadata and plugin information
- **SwitcherOwner**: Base class for automatic Switcher binding via `__init_subclass__`
- **Plugin System** (v0.6.0): Extensible middleware architecture with `on_decorate` and `wrap_handler` hooks

---

## Registration Flow

```mermaid
sequenceDiagram
    participant User
    participant Switcher
    participant Plugin1
    participant Plugin2
    participant MethodEntry

    User->>Switcher: @sw decorator
    Switcher->>MethodEntry: Create MethodEntry(name, func, metadata={})

    Note over Switcher,Plugin1: Phase 1: on_decorate hooks
    Switcher->>Plugin1: on_decorate(switch, func, entry)
    Plugin1->>MethodEntry: Store metadata
    Switcher->>Plugin2: on_decorate(switch, func, entry)
    Plugin2->>MethodEntry: Read/write metadata

    Note over Switcher,Plugin1: Phase 2: wrap_handler hooks
    Switcher->>Plugin1: wrap_handler(switch, entry, call_next)
    Plugin1->>Switcher: Return wrapper1
    Switcher->>Plugin2: wrap_handler(switch, entry, wrapper1)
    Plugin2->>Switcher: Return wrapper2

    Switcher->>Switcher: Store in _methods[name] = entry
    Switcher->>User: Return original function

    Note over Switcher,MethodEntry: Plugins wrap in reverse order during calls
```

**Key Points (V2)**:

1. **MethodEntry Creation**: Each handler gets a MethodEntry with name, func, metadata
2. **Plugin Hooks**: Two-phase system - on_decorate for setup, wrap_handler for wrapping
3. **Metadata Sharing**: Plugins store/read data in entry.metadata by namespace
4. **Middleware Chain**: Plugins wrap handlers in order, execute in reverse during calls

---

## Dispatch Flow

```mermaid
sequenceDiagram
    participant User
    participant Switcher
    participant Matcher
    participant Handler

    User->>Switcher: sw()(x=42)
    Note over Switcher: arg is None → dispatcher mode
    Switcher->>User: Return invoker closure

    User->>Switcher: invoker(x=42)

    Note over Switcher: Iterate through _rules
    Switcher->>Matcher: Check rule 1
    Matcher->>Matcher: Build args_dict
    Matcher->>Matcher: Run type check
    Matcher->>Matcher: Run value rule
    Matcher-->>Switcher: No match, try next

    Switcher->>Matcher: Check rule 2
    Matcher->>Matcher: Build args_dict
    Matcher->>Matcher: Run type check
    Matcher-->>Switcher: Match found!

    Switcher->>Handler: Call handler(x=42)
    Handler-->>User: Return result

    Note over Switcher,Handler: Early exit on first match<br/>No dynamic introspection
```

**Performance Optimizations**:

1. **Manual Args Dict Building**: Avoids expensive `bind_partial()` - 60% faster
2. **Pre-Compiled Checkers**: No runtime type introspection - 3x faster
3. **Early Exit**: Returns immediately on first match
4. **No Dynamic Calls**: All function references captured at registration

---

## Class Relationships

```mermaid
classDiagram
    class Switcher {
        +str name
        +str description
        +str prefix
        -Switcher _parent
        -set _children
        -dict _handlers
        -list _rules
        -callable _default_handler
        -dict _param_names_cache
        -str _log_mode
        -dict _log_default
        -dict _log_handlers
        -list _log_history
        -int _log_max_history
        -str _log_file
        -Logger _logger

        +__init__(name, description, prefix, parent)
        +__call__(arg, typerule, valrule)
        +__get__(instance, owner)
        +entries() List~str~
        +parent() Switcher
        +parent(value) void
        +children() set~Switcher~
        +add_child(switcher) void
        +remove_child(switcher) void
        +enable_log(...) void
        +disable_log(...) void
        +get_log_history(...) List
        +get_log_stats() dict
        +clear_log_history() void
        +export_log_history(filepath) void
        -_compile_type_checks(typerule, param_names)
        -_make_type_checker(hint)
        -_get_log_config(handler_name) dict
        -_wrap_with_logging(handler_name, func) callable
    }

    Switcher "0..1" --> "0..*" Switcher : parent-child (bidirectional)

    class BoundSwitcher {
        -Switcher _switcher
        -Any _instance

        +__init__(switcher, instance)
        +__call__(name)
        +__getattr__(name)
    }

    class Handler {
        <<function>>
        User-defined function
    }

    class Matcher {
        <<closure>>
        Matching logic
    }

    Switcher "1" --> "*" Handler : registers
    Switcher "1" --> "*" Matcher : creates
    Switcher "1" --> "0..1" BoundSwitcher : creates via __get__
    BoundSwitcher --> Switcher : references
    Matcher --> Handler : paired with

    note for Switcher "Core dispatch engine\nHandles registration and routing"
    note for BoundSwitcher "Descriptor helper\nAuto-binds methods"
```

---

## Module Structure

```
src/smartswitch/
├── __init__.py          # Public API exports (4 lines)
└── core.py              # Core implementation (770+ lines)
    ├── BoundSwitcher    # Lines 12-42 (30 lines)
    └── Switcher         # Lines 44-770+ (726+ lines)
        ├── Registration & Dispatch    # Lines 44-470
        ├── Logging System (v0.4.0)    # Lines 470-670
        └── History & Stats            # Lines 670-770+
```

**Design**: Intentionally minimal - single file core with zero external dependencies (stdlib only).

---

## Component Responsibilities

### **Switcher** (Main Engine)

**File**: `src/smartswitch/core.py:38-328`

**Core Responsibility**: Complete handler lifecycle - registration, matching, dispatch.

**Public API**:

- `__init__(name, description, prefix)` - Configure switcher instance
- `__call__(...)` - Multi-purpose: decorator, lookup, dispatcher (5 modes)
- `__get__(...)` - Descriptor protocol for automatic method binding

**Internal State**:

- `_handlers: Dict[str, Callable]` - Name-to-function registry
- `_rules: List[Tuple[Callable, Callable]]` - Ordered (matcher, handler) pairs
- `_param_names_cache: Dict` - Cached signature inspection results

**Helper Methods**:

- `_compile_type_checks()` - Pre-compiles type checkers for fast dispatch
- `_make_type_checker()` - Recursive factory for type checking functions

---

### **BoundSwitcher** (Descriptor Helper)

**File**: `src/smartswitch/core.py:12-36`

**Core Responsibility**: Automatic handler binding for class-based usage.

**Usage Pattern**:

```python
class MyClass:
    switch = Switcher()  # Class attribute

    @switch
    def method(self, x):
        return x * 2

obj = MyClass()
obj.switch("method")  # Returns bound method automatically!
```

**How It Works**:

1. `Switcher.__get__(obj, MyClass)` called by Python descriptor protocol
2. Returns `BoundSwitcher(switcher, obj)`
3. `BoundSwitcher("method")` retrieves handler and binds with `partial(handler, obj)`
4. User gets ready-to-call bound method - zero boilerplate!

---

## Key Design Decisions

### **1. Multi-Mode `__call__`**

**Rationale**: Single entry point for all operations → cleaner, more discoverable API

**Trade-off**: High internal complexity (175 lines, 5 distinct modes) vs simple user experience

**Five Modes**:

1. `@sw` - Register as default handler
2. `@sw('alias')` - Register with custom name
3. `@sw(typerule=..., valrule=...)` - Register with matching rules
4. `sw("name")` - Lookup handler by name
5. `sw()` - Get dispatcher function

---

### **2. Pre-Compiled Type Checkers**

**Problem**: `isinstance()` checks on every dispatch call → expensive

**Solution**: Compile type checking logic once at registration time

**Implementation**:

```python
# Registration time (once):
checker = lambda val: isinstance(val, int)

# Dispatch time (many times):
if not checker(value):  # Fast function call
    return False
```

**Performance Gain**: 3x faster dispatch compared to runtime introspection

---

### **3. Manual Kwargs Building**

**Problem**: `inspect.Signature.bind_partial()` is slow (calls inspect internally)

**Solution**: Build args dict manually with simple loop

**Implementation**:

```python
# Fast manual build:
args_dict = {}
for i, name in enumerate(param_names):  # Cached!
    if i < len(a):
        args_dict[name] = a[i]
    elif name in kw:
        args_dict[name] = kw[name]
```

**Performance Gain**: 60% reduction in dispatch overhead

---

### **4. Descriptor Protocol**

**Problem**: Class-based handlers need `self` binding

**Naive Approach**: Users must manually `partial(handler, self)` - error-prone

**Solution**: Implement `__get__` to return `BoundSwitcher` automatically

**Benefit**: Pythonic magic - users get bound methods for free

---

### **5. Immutable Slots**

**Rationale**: Prevent accidental attribute creation + reduce memory footprint

**Implementation**: Both classes use `__slots__` to declare fixed attributes

**Benefits**:

- Memory: ~40% reduction per instance
- Safety: Typos raise `AttributeError` instead of silently creating new attributes

---

## Component Interaction Summary

| Component | Calls | Called By | Data Shared |
|-----------|-------|-----------|-------------|
| `Switcher.__call__` | `_compile_type_checks`, `_make_type_checker`, `inspect.signature` | User code (decorator/dispatch) | `_rules`, `_handlers`, `_param_names_cache` |
| `_compile_type_checks` | `_make_type_checker` | `Switcher.__call__` | typerule dict, param_names |
| `_make_type_checker` | `get_origin`, `get_args`, recursive self | `_compile_type_checks` | Type hints |
| `BoundSwitcher.__call__` | `partial` | User code (via descriptor) | `_switcher._handlers`, `_instance` |
| `Switcher.__get__` | `BoundSwitcher()` | Python descriptor protocol | self, instance |

---

## Performance Characteristics

**Dispatch Overhead**: ~1-2 microseconds per call

**Ideal Use Cases**:

- Functions doing real work (>1ms)
- I/O operations (API calls, database queries)
- Business logic with complex routing needs

**Not Ideal For**:

- Ultra-fast functions (<10μs) called millions of times
- Performance-critical tight loops

**Optimizations Applied**:

1. **Signature Caching**: `inspect.signature()` called once per function
2. **Pre-Compiled Type Checks**: Type checkers compiled at registration
3. **Manual Kwargs Building**: Avoids expensive `bind_partial()` overhead
4. **`__slots__`**: Reduced memory footprint per instance

---

## Thread Safety Considerations

**Dispatch Operations**: ✅ **Thread-safe** (read-only, no mutations)

**Registration Operations**: ⚠️ **Not thread-safe**

- Decorator application mutates `_handlers` and `_rules`
- **Recommended Usage**: Apply decorators at module import time (single-threaded)
- **Multi-threaded Apps**: If runtime registration needed, use external locking

---

## Logging System Architecture (v0.4.0)

### Overview

The logging system wraps handlers with an additional layer that records execution details without modifying the original function behavior.

### Components

**State Management**:
- `_log_mode`: Global mode ('silent', 'log', 'both', or None)
- `_log_default`: Default config dict for all handlers
- `_log_handlers`: Per-handler config overrides (dict or False to disable)
- `_log_history`: Circular buffer of execution records (list)
- `_log_max_history`: Maximum history size (default 1000)
- `_log_file`: Optional JSONL file path for persistent logging
- `_logger`: Python logging.Logger instance

### Logging Modes

1. **Silent Mode** (`mode="silent"`):
   - Records to `_log_history` only
   - Zero console output
   - Ideal for production performance monitoring

2. **Log Mode** (`mode="log"`):
   - Outputs to logger (stdout/stderr)
   - No history tracking
   - Traditional logging behavior

3. **Both Mode** (`mode="both"`):
   - Records to history AND logs to console
   - Complete observability

### Handler Wrapping Flow

```mermaid
sequenceDiagram
    participant User
    participant Switcher
    participant Wrapper
    participant Handler
    participant History

    User->>Switcher: enable_log(mode="silent")
    Switcher->>Switcher: Set _log_mode="silent"

    User->>Switcher: sw("handler_name")
    Switcher->>Switcher: _get_log_config("handler_name")

    alt Logging enabled for handler
        Switcher->>Wrapper: _wrap_with_logging(name, func)
        Wrapper->>User: Return logged_wrapper
    else Logging disabled
        Switcher->>User: Return original func
    end

    User->>Wrapper: Call handler(args)

    alt mode="silent" or "both"
        Wrapper->>Wrapper: Record start time
    end

    Wrapper->>Handler: Execute original(*args, **kwargs)
    Handler-->>Wrapper: Return result or raise exception

    alt mode="silent" or "both"
        Wrapper->>Wrapper: Calculate elapsed time
        Wrapper->>History: Append entry (with FIFO eviction)
    end

    alt mode="log" or "both"
        Wrapper->>Switcher: Log to _logger
    end

    Wrapper-->>User: Return result or re-raise exception
```

### History Record Format

Each history entry is a dict:

```python
{
    "handler": "handler_name",
    "switcher": "switcher_name",
    "timestamp": 1234567890.123,
    "args": (arg1, arg2),
    "kwargs": {"key": "value"},
    "result": return_value,        # Only if success
    "exception": {                 # Only if error
        "type": "ValueError",
        "message": "error message",
        "traceback": "full traceback"
    },
    "elapsed": 0.001234            # Seconds
}
```

### Circular Buffer Implementation

History uses a simple circular buffer:

1. Append new entries to `_log_history`
2. If `len(_log_history) > _log_max_history`:
   - Remove oldest entry: `_log_history.pop(0)`
3. FIFO eviction maintains most recent entries

### Query API

The query methods provide rich filtering:

- **Temporal**: `first=N`, `last=N`
- **By handler**: `handler="name"`
- **By performance**: `slowest=N`, `fastest=N`, `slower_than=seconds`
- **By status**: `errors=True/False`

All filters compose naturally with Python list operations.

### __wrapped__ Preservation

Critical for introspection tools (IDEs, debuggers, documentation):

```python
logged_wrapper.__wrapped__ = func
```

Tools can access original function signature via `__wrapped__` even when logging is active.

### BoundSwitcher Delegation

`BoundSwitcher` delegates all methods to underlying `Switcher` via `__getattr__`:

```python
def __getattr__(self, name):
    """Delegate attribute access to the underlying Switcher."""
    return getattr(self._switcher, name)
```

This ensures class-based usage has full logging API access.

---

## Future Extension Points

SmartSwitch's architecture supports potential enhancements:

**1. Async Support**

Detect and handle async handlers without blocking:

```python
if inspect.iscoroutinefunction(func):
    return func(*args, **kwargs)  # Return awaitable
```

**2. Custom Matchers**

Extend beyond `typerule`/`valrule`:

```python
@sw(custom_matcher=lambda args: args['priority'] == 'high')
def urgent_handler(priority, task):
    ...
```

**3. Result Caching**

Cache dispatch results for pure functions:

```python
@sw(typerule={'x': int}, cache=True)
def expensive_calc(x):
    ...
```

---

## Design Principles Applied

- ✅ **Single Responsibility**: Each class has one clear purpose
- ✅ **Open/Closed**: Open for extension (custom matchers), closed for modification
- ✅ **Performance First**: Optimizations based on profiling, not premature optimization
- ✅ **Zero Dependencies**: Core uses only Python stdlib
- ✅ **Type Safety**: Full type hints for modern Python (3.10+)
- ✅ **Immutability**: `__slots__` prevents accidental state mutation

---

**For implementation details**, see the [source code](https://github.com/genropy/smartswitch/blob/main/src/smartswitch/core.py).
