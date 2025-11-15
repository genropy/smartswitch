# Plugin Composition: Chaining Multiple Plugins

This example shows how to combine multiple plugins to build a robust API handler with logging, validation, and caching.

## Scenario

You have an API service that needs:
1. **Logging** - Track all API calls for monitoring
2. **Validation** - Ensure inputs are correct before processing
3. **Caching** - Cache expensive computations

## Built-in Plugin: Logging

SmartSwitch includes a built-in logging plugin:

```python
from smartswitch import Switcher

# Create switcher with logging
api = Switcher(name="api").plug("logging", flags="print,enabled,before,after,time")

@api
def calculate_stats(dataset_id: int):
    # Expensive computation
    return {"mean": 42.5, "median": 40.0, "dataset": dataset_id}

# Automatically logs call details
result = api('calculate_stats')(123)
# Output:
# → calculate_stats(123)
# ← calculate_stats() → {'mean': 42.5, 'median': 40.0, 'dataset': 123} (0.0023s)
```

## Creating Custom Plugins

### Validation Plugin

Validates inputs before handler execution:

```python
from smartswitch import BasePlugin
from pydantic import BaseModel, Field

class ValidationConfig(BaseModel):
    enabled: bool = Field(default=True)
    strict: bool = Field(default=False)

class ValidationPlugin(BasePlugin):
    """Validate handler arguments using type hints."""

    config_model = ValidationConfig

    def wrap_handler(self, switch, entry, call_next):
        handler_name = entry.name

        def wrapper(*args, **kwargs):
            cfg = self.get_config(handler_name)
            if not cfg.get('enabled'):
                return call_next(*args, **kwargs)

            # Simple validation example
            if not args:
                raise ValueError(f"{handler_name}: No arguments provided")

            return call_next(*args, **kwargs)

        return wrapper
```

### Cache Plugin

Caches results of expensive operations:

```python
class CacheConfig(BaseModel):
    enabled: bool = Field(default=True)
    ttl: int = Field(default=300, description="Time to live in seconds")

class CachePlugin(BasePlugin):
    """Cache handler results."""

    config_model = CacheConfig

    def __init__(self, **kwargs):
        super().__init__(name="cache", **kwargs)
        self._cache = {}
        self._timestamps = {}

    def wrap_handler(self, switch, entry, call_next):
        handler_name = entry.name

        def wrapper(*args, **kwargs):
            import time
            cfg = self.get_config(handler_name)

            if not cfg.get('enabled'):
                return call_next(*args, **kwargs)

            # Create cache key
            cache_key = (handler_name, args, tuple(sorted(kwargs.items())))

            # Check cache
            if cache_key in self._cache:
                timestamp = self._timestamps[cache_key]
                age = time.time() - timestamp
                ttl = cfg.get('ttl', 300)

                if age < ttl:
                    print(f"Cache HIT: {handler_name}")
                    return self._cache[cache_key]

            # Cache miss - execute and store
            print(f"Cache MISS: {handler_name}")
            result = call_next(*args, **kwargs)
            self._cache[cache_key] = result
            self._timestamps[cache_key] = time.time()
            return result

        return wrapper

    def clear(self):
        """Clear all cached values."""
        self._cache.clear()
        self._timestamps.clear()
```

## Combining Multiple Plugins

Register and chain all three plugins:

```python
from smartswitch import Switcher

# Register custom plugins
Switcher.register_plugin('validation', ValidationPlugin)
Switcher.register_plugin('cache', CachePlugin)

# Chain plugins - executed in order
api = (Switcher(name="api")
       .plug('logging', flags='print,enabled,time')      # First: log calls
       .plug('validation')                               # Second: validate inputs
       .plug('cache', ttl=60))                          # Third: cache results

@api
def expensive_query(user_id: int, category: str):
    """Expensive database query."""
    import time
    time.sleep(0.5)  # Simulate slow query
    return {
        "user_id": user_id,
        "category": category,
        "results": ["item1", "item2", "item3"]
    }

# First call: Goes through validation, executes, caches result
result1 = api('expensive_query')(42, "electronics")
# Output:
# → expensive_query(42, 'electronics')
# Cache MISS: expensive_query
# ← expensive_query() → {...} (0.5012s)

# Second call: Returns from cache (much faster)
result2 = api('expensive_query')(42, "electronics")
# Output:
# → expensive_query(42, 'electronics')
# Cache HIT: expensive_query
# ← expensive_query() → {...} (0.0001s)
```

## Plugin Order Matters

Plugins wrap handlers in registration order:

```python
# Order: Logging → Validation → Cache → Handler
api = (Switcher()
       .plug('logging', flags='print,enabled,time')
       .plug('validation')
       .plug('cache'))

# Execution flow:
# 1. LoggingPlugin starts timer
# 2. ValidationPlugin checks inputs
# 3. CachePlugin checks cache
# 4. If cache miss, handler executes
# 5. CachePlugin stores result
# 6. ValidationPlugin passes result through
# 7. LoggingPlugin logs final result and time
```

This order ensures:
- All calls are logged (including cached ones)
- Invalid requests are rejected before cache lookup
- Expensive operations are cached after validation

## Runtime Configuration

Configure plugins at runtime:

```python
# Disable caching for specific handler
api.cache.configure['expensive_query'].enabled = False

# Enable strict validation
api.validation.configure['expensive_query'].strict = True

# Change logging output
api.logging.configure.flags = 'print,enabled,before,after,time'

# Per-method logging
api.logging.configure['expensive_query'].flags = 'enabled:off'
```

## Real-World Patterns

### API Gateway with Rate Limiting

```python
from smartswitch import Switcher, BasePlugin
import time

class RateLimitConfig(BaseModel):
    enabled: bool = True
    max_calls: int = 10
    window: int = 60  # seconds

class RateLimitPlugin(BasePlugin):
    config_model = RateLimitConfig

    def __init__(self, **kwargs):
        super().__init__(name="ratelimit", **kwargs)
        self._calls = {}

    def wrap_handler(self, switch, entry, call_next):
        handler_name = entry.name

        def wrapper(*args, **kwargs):
            cfg = self.get_config(handler_name)
            if not cfg.get('enabled'):
                return call_next(*args, **kwargs)

            now = time.time()
            max_calls = cfg.get('max_calls', 10)
            window = cfg.get('window', 60)

            # Clean old entries
            if handler_name in self._calls:
                self._calls[handler_name] = [
                    t for t in self._calls[handler_name]
                    if now - t < window
                ]
            else:
                self._calls[handler_name] = []

            # Check limit
            if len(self._calls[handler_name]) >= max_calls:
                raise RuntimeError(f"Rate limit exceeded for {handler_name}")

            # Record call
            self._calls[handler_name].append(now)
            return call_next(*args, **kwargs)

        return wrapper

# Register and use
Switcher.register_plugin('ratelimit', RateLimitPlugin)

gateway = (Switcher(name="gateway")
           .plug('logging', flags='print,enabled,time')
           .plug('ratelimit', max_calls=5, window=10)
           .plug('cache'))

@gateway
def api_endpoint(query: str):
    return {"query": query, "results": ["a", "b", "c"]}
```

### Data Processing Pipeline

```python
# Pipeline with validation, transformation, and caching
pipeline = (Switcher(name="pipeline")
            .plug('logging', flags='print,enabled,time')
            .plug('validation')
            .plug('cache', ttl=3600))

@pipeline
def transform_data(raw_data: dict) -> dict:
    """Transform and enrich data."""
    # Expensive transformation
    return {
        "processed": True,
        "data": raw_data,
        "enriched": {"timestamp": "2024-01-01"}
    }

@pipeline
def aggregate_metrics(dataset: str) -> dict:
    """Aggregate metrics from dataset."""
    # Expensive aggregation
    return {"mean": 42, "count": 1000, "dataset": dataset}

# Process data with full plugin stack
result = pipeline('transform_data')({"value": 123})
metrics = pipeline('aggregate_metrics')("users_2024")
```

## Benefits of Plugin Composition

1. **Separation of Concerns** - Each plugin handles one responsibility
2. **Reusability** - Plugins work with any handler
3. **Testability** - Test plugins independently
4. **Flexibility** - Mix and match as needed
5. **Performance** - Caching reduces load, logging helps debug

## Best Practices

1. **Order plugins carefully** - Put logging first, caching last
2. **Use per-method config** - Fine-tune behavior per handler
3. **Clear caches when needed** - `api.cache.clear()`
4. **Monitor via logging** - Track cache hits/misses
5. **Document plugin chain** - Make execution flow clear

## See Also

- [Plugin Development Guide](../plugins/development.md) - Create custom plugins
- [Middleware Pattern](../plugins/middleware.md) - How plugins work internally
- [Logging Plugin](../plugins/logging.md) - LoggingPlugin documentation
