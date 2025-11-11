# SmartSwitch - Logging & Performance Analysis

**New in v0.4.0**: Call history tracking, performance analysis, error tracking

## Quick Start

### Enable Silent Mode (Production)
```python
sw = Switcher()

# Enable silent history tracking (zero-overhead, no console output)
sw.enable_log(mode='silent', max_history=1000)

@sw
def process(data):
    return data * 2

# Calls are tracked silently
sw('process')(42)

# Query history later
history = sw.get_log_history(last=10)
stats = sw.get_log_stats()
```

### Enable Logging Mode (Development)
```python
sw = Switcher()

# Enable immediate console logging
sw.enable_log(
    mode='log',           # 'log', 'silent', or 'both'
    before=True,          # Log args before execution
    after=True,           # Log result after execution
    time=True,            # Measure execution time
)

@sw
def save_data(data):
    return f"Saved: {data}"

# Logs to console:
# INFO: Calling save_data with args=(42,), kwargs={}
# INFO: save_data returned Saved: 42 (elapsed: 0.0001s)
```

## Logging Modes

| Mode | Console Output | History | Use Case |
|------|---------------|---------|----------|
| `'silent'` | ❌ | ✅ | Production (zero overhead) |
| `'log'` | ✅ | ❌ | Development/debugging |
| `'both'` | ✅ | ✅ | Staging/analysis |

## Configuration Options

### Global Configuration
```python
# All handlers use these settings
sw.enable_log(
    mode='silent',
    before=True,          # Track args
    after=True,           # Track results
    time=True,            # Measure time
    max_history=1000,     # History size
    log_file='calls.jsonl'  # Optional file logging
)
```

### Per-Handler Configuration
```python
# Only track specific handlers
sw.enable_log(
    'critical_handler',
    'slow_operation',
    mode='both',
    time=True
)

# Disable specific handlers
sw.disable_log('noisy_handler', 'debug_only')
```

## Querying History

### Recent Calls
```python
# Last 10 calls
recent = sw.get_log_history(last=10)

# First 5 calls
first = sw.get_log_history(first=5)

# Specific handler
user_calls = sw.get_log_history(handler='save_user')
```

### Performance Analysis
```python
# 5 slowest executions
slow = sw.get_log_history(slowest=5)

# 5 fastest executions
fast = sw.get_log_history(fastest=5)

# Calls slower than 100ms
slow_calls = sw.get_log_history(slower_than=0.1)
```

### Error Tracking
```python
# Only errors
errors = sw.get_log_history(errors=True)

# Only successes
successes = sw.get_log_history(errors=False)

# Errors for specific handler
user_errors = sw.get_log_history(handler='save_user', errors=True)
```

### Combined Queries
```python
# Last 20 slow errors
critical = sw.get_log_history(
    errors=True,
    slower_than=1.0,
    last=20
)
```

## Statistics

### Get Handler Stats
```python
stats = sw.get_log_stats()

# Returns:
{
    'save_user': {
        'calls': 150,
        'errors': 3,
        'avg_time': 0.0234,
        'min_time': 0.0120,
        'max_time': 0.0890,
        'total_time': 3.51
    },
    'delete_user': {
        'calls': 45,
        'errors': 0,
        'avg_time': 0.0156,
        ...
    }
}

# Find slowest handler
slowest = max(stats.items(), key=lambda x: x[1]['avg_time'])
print(f"Slowest: {slowest[0]} - avg {slowest[1]['avg_time']:.4f}s")

# Find most errors
most_errors = max(stats.items(), key=lambda x: x[1]['errors'])
```

## Export & Persistence

### Export to JSON
```python
# Export complete history
sw.export_log_history('call_history.json')

# Clear history after export
sw.clear_log_history()
```

### File Logging (JSONL Format)
```python
# Log to file as calls happen
sw.enable_log(
    mode='silent',
    log_file='production_calls.jsonl'
)

# Each line is a JSON entry:
# {"handler":"save","timestamp":1234567890.123,"args":"...","elapsed":0.023}
```

## Log Entry Format

```python
{
    'handler': 'save_user',
    'switcher': 'api',
    'timestamp': 1699876543.123,
    'args': (42,),
    'kwargs': {'name': 'Alice'},
    'result': 'Saved: Alice',       # If successful
    'exception': {                  # If error
        'type': 'ValueError',
        'message': 'Invalid data'
    },
    'elapsed': 0.0234              # If time=True
}
```

## Real-World Examples

### Production Monitoring
```python
class ProductionAPI:
    api = Switcher(name='api')
    
    def __init__(self):
        # Silent tracking for all handlers
        self.api.enable_log(
            mode='silent',
            time=True,
            max_history=10000,
            log_file='api_calls.jsonl'
        )
    
    @api
    def critical_operation(self, data):
        # ... implementation
        pass
    
    def get_performance_report(self):
        """Generate performance report"""
        stats = self.api.get_log_stats()
        slow = self.api.get_log_history(slower_than=1.0)
        errors = self.api.get_log_history(errors=True, last=50)
        
        return {
            'stats': stats,
            'slow_calls': slow,
            'recent_errors': errors
        }
```

### Debug Mode Toggle
```python
class Service:
    ops = Switcher()
    
    @classmethod
    def enable_debug(cls):
        cls.ops.enable_log(mode='both', before=True, after=True, time=True)
    
    @classmethod
    def disable_debug(cls):
        cls.ops.disable_log()
    
    @ops
    def process(self, data):
        return data * 2

# Production: silent
service = Service()

# Debug session
Service.enable_debug()
service.ops('process')(42)  # Logs to console
Service.disable_debug()
```

### Performance Profiling
```python
# Before optimization
sw.clear_log_history()
sw.enable_log(mode='silent', time=True)

# Run workload
for i in range(1000):
    sw('process')(data)

# Analyze
stats = sw.get_log_stats()
print(f"Avg time: {stats['process']['avg_time']:.4f}s")
print(f"Max time: {stats['process']['max_time']:.4f}s")

slowest = sw.get_log_history(slowest=10)
for entry in slowest:
    print(f"Slow call: {entry['elapsed']:.4f}s with args={entry['args']}")
```

### Error Rate Monitoring
```python
def check_error_rate(sw):
    """Alert if error rate > 5%"""
    stats = sw.get_log_stats()
    
    for handler, data in stats.items():
        if data['calls'] > 100:  # Only check handlers with enough calls
            error_rate = data['errors'] / data['calls']
            if error_rate > 0.05:
                print(f"⚠️  {handler} has {error_rate:.1%} error rate")
                
                # Get recent errors for analysis
                recent_errors = sw.get_log_history(
                    handler=handler,
                    errors=True,
                    last=5
                )
                for err in recent_errors:
                    print(f"  - {err['exception']}")
```

## Performance Impact

- **Silent mode**: ~0.5μs overhead (negligible)
- **Log mode**: ~50μs overhead (I/O bound)
- **Both mode**: ~50μs overhead (I/O bound)

Silent mode is production-ready for any workload.

## Best Practices

1. **Use silent mode in production** for zero-overhead tracking
2. **Export history periodically** to prevent memory growth
3. **Set appropriate max_history** (default: 1000)
4. **Use handler-specific configs** to focus on critical paths
5. **Query by handler name** for targeted analysis
6. **Monitor error rates** with get_log_stats()
7. **Use log_file** for persistent historical data

## Thread Safety

- History tracking is thread-safe (internal locking)
- Multiple threads can call handlers concurrently
- History order may be non-deterministic in multi-threaded scenarios
