# Plugin Composition: Internal + External

This example shows how to combine SmartSwitch's built-in **LoggingPlugin** with an external **AsyncPlugin** for handling async operations.

## Scenario

You have an API service that:
1. Makes async HTTP calls (external plugin)
2. Tracks all calls with logging (built-in plugin)
3. Needs both sync and async handlers

## Built-in Plugin: Logging

SmartSwitch includes a built-in logging plugin accessible via `.plug("logging")`:

```python
from smartswitch import Switcher

# Create switcher with logging
api = Switcher(name="api").plug("logging", mode="silent", time=True)

@api
def get_user(user_id):
    # Sync operation
    return {"id": user_id, "name": f"User {user_id}"}

@api
def get_posts(user_id):
    # Sync operation
    return [{"id": 1, "title": "Post 1"}]

# Make calls
api("get_user")(123)
api("get_posts")(123)

# Query history
history = api.logger.history()
print(f"Total calls: {len(history)}")
# → Total calls: 2

# Get slowest calls
slow_calls = api.logger.history(slowest=5)
for call in slow_calls:
    print(f"{call['handler']}: {call['elapsed']:.3f}s")
# → get_posts: 0.042s
# → get_user: 0.015s

# Filter by handler
user_calls = api.logger.history(handler="get_user")
print(f"User calls: {len(user_calls)}")
# → User calls: 1

# Export to JSON for analysis
api.logger.export("api_calls.json")
```

## External Plugin: Async Support

For async operations, create an external plugin:

```python
import asyncio
from functools import wraps
from typing import Callable
from smartswitch import Switcher

class AsyncPlugin:
    """
    Plugin to add async/await support to SmartSwitch.

    Wraps async handlers so they can be called from sync code,
    automatically running them in an event loop.
    """

    def wrap(self, func: Callable, switcher: Switcher) -> Callable:
        """Wrap function to handle async execution."""

        # Check if function is async
        if not asyncio.iscoroutinefunction(func):
            return func  # Pass through sync functions

        @wraps(func)
        def async_wrapper(*args, **kwargs):
            """
            Wrapper that runs async function in event loop.

            This allows calling async handlers from sync code:
                result = sw('async_handler')(arg)

            Instead of requiring:
                result = await sw('async_handler')(arg)
            """
            # Try to get existing event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're already in async context, return the coroutine
                return func(*args, **kwargs)
            except RuntimeError:
                # No event loop running, create one
                return asyncio.run(func(*args, **kwargs))

        # Preserve metadata
        async_wrapper.__wrapped__ = func
        return async_wrapper
```

## Combined Usage

Now combine both plugins:

```python
import asyncio
import httpx
from smartswitch import Switcher

# Create switcher with BOTH plugins
api = (Switcher(name="api")
       .plug("logging", mode="silent", time=True)  # Built-in
       .plug(AsyncPlugin()))                        # External

# Sync handler
@api
def get_local_user(user_id):
    """Fetch user from local database (sync)."""
    return {"id": user_id, "name": f"User {user_id}", "source": "local"}

# Async handler
@api
async def get_remote_user(user_id):
    """Fetch user from remote API (async)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://jsonplaceholder.typicode.com/users/{user_id}"
        )
        return response.json()

# Async handler with error handling
@api
async def get_user_posts(user_id):
    """Fetch user's posts from remote API (async)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://jsonplaceholder.typicode.com/posts?userId={user_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to fetch posts: {e}")

# Call handlers (both sync and async) with same syntax
user_local = api("get_local_user")(1)
user_remote = api("get_remote_user")(1)
posts = api("get_user_posts")(1)

print(f"Local user: {user_local['name']}")
print(f"Remote user: {user_remote['name']}")
print(f"Posts: {len(posts)} posts")

# Logging plugin tracked ALL calls (sync and async)
history = api.logger.history()
print(f"\nTotal API calls: {len(history)}")
# → Total API calls: 3

# Find slowest operations (likely the remote calls)
slow_calls = api.logger.history(slowest=3)
for call in slow_calls:
    handler = call['handler']
    elapsed = call['elapsed']
    success = 'exception' not in call
    status = "✓" if success else "✗"
    print(f"{status} {handler}: {elapsed:.3f}s")
# → ✓ get_user_posts: 0.245s
# → ✓ get_remote_user: 0.182s
# → ✓ get_local_user: 0.001s

# Filter only remote calls
remote_calls = [
    call for call in history
    if 'remote' in call['handler']
]
print(f"\nRemote API calls: {len(remote_calls)}")
# → Remote API calls: 2

# Check for errors
errors = api.logger.history(errors=True)
if errors:
    print(f"\nErrors: {len(errors)}")
    for error in errors:
        print(f"  {error['handler']}: {error['exception']['type']}")
```

## Plugin Order Matters

Plugins are applied in registration order:

```python
# Order 1: Logging wraps async
api1 = (Switcher()
        .plug("logging", mode="silent", time=True)  # Outer wrapper
        .plug(AsyncPlugin()))                        # Inner wrapper

# Execution flow for async handler:
# User → LoggingPlugin (start timer) → AsyncPlugin (run in loop) → Handler
#                                                ↓
# User ← LoggingPlugin (stop timer)  ← AsyncPlugin (return result) ← Handler
```

This order ensures:
1. **Logging wraps everything** - tracks total time including async overhead
2. **Async runs inside** - logging sees the final result, not a coroutine

## Real-World Usage Patterns

### Pattern 1: API Gateway

```python
# Gateway that aggregates multiple services
gateway = (Switcher(name="gateway")
           .plug("logging", mode="both", time=True)  # Log to console + history
           .plug(AsyncPlugin()))

@gateway
async def get_user_profile(user_id):
    """Aggregate data from multiple services."""
    async with httpx.AsyncClient() as client:
        # Parallel requests
        user_task = client.get(f"https://api.example.com/users/{user_id}")
        prefs_task = client.get(f"https://api.example.com/preferences/{user_id}")

        user_resp, prefs_resp = await asyncio.gather(user_task, prefs_task)

        return {
            "user": user_resp.json(),
            "preferences": prefs_resp.json()
        }

# Later: analyze performance
slow_endpoints = gateway.logger.history(slower_than=0.5)
print(f"Slow endpoints (>500ms): {len(slow_endpoints)}")
```

### Pattern 2: Background Jobs

```python
# Job processor with logging
jobs = (Switcher(name="jobs")
        .plug("logging", mode="silent", time=True, max_history=1000)
        .plug(AsyncPlugin()))

@jobs
async def send_email(recipient, subject, body):
    """Send email via external service."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.mailgun.net/v3/messages",
            data={"to": recipient, "subject": subject, "text": body}
        )
        return response.json()

@jobs
async def process_payment(amount, currency):
    """Process payment via Stripe."""
    # ... Stripe API call
    pass

# Run jobs
jobs("send_email")("user@example.com", "Welcome", "Hello!")
jobs("process_payment")(99.99, "USD")

# Export job history for monitoring
jobs.logger.export("job_history.json")

# Alert on failures
errors = jobs.logger.history(errors=True, last=100)
if len(errors) > 10:
    alert_ops_team(f"{len(errors)} job failures in last 100 runs")
```

### Pattern 3: Testing & Debugging

```python
# Test suite with detailed logging
tests = (Switcher(name="tests")
         .plug("logging", mode="silent", time=True)
         .plug(AsyncPlugin()))

@tests
async def test_api_endpoint(endpoint, expected_status):
    """Test API endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.example.com{endpoint}")
        assert response.status_code == expected_status
        return {"endpoint": endpoint, "status": response.status_code}

# Run tests
tests("test_api_endpoint")("/users", 200)
tests("test_api_endpoint")("/posts", 200)
tests("test_api_endpoint")("/invalid", 404)

# Analyze test results
history = tests.logger.history()
passed = [h for h in history if 'exception' not in h]
failed = [h for h in history if 'exception' in h]

print(f"Tests: {len(passed)} passed, {len(failed)} failed")

# Get timing stats
if passed:
    times = [h['elapsed'] for h in passed]
    avg_time = sum(times) / len(times)
    print(f"Average test time: {avg_time:.3f}s")
```

## Plugin Development Tips

### Tip 1: Pass-Through for Non-Applicable Functions

```python
def wrap(self, func, switcher):
    if not self._should_wrap(func):
        return func  # Pass through unchanged
    return self._wrap_function(func)
```

### Tip 2: Preserve Function Metadata

```python
from functools import wraps

def wrap(self, func, switcher):
    @wraps(func)  # Preserves __name__, __doc__, etc.
    def wrapper(*args, **kwargs):
        # ... your logic
        return func(*args, **kwargs)

    wrapper.__wrapped__ = func  # For introspection
    return wrapper
```

### Tip 3: Access Switcher State

```python
def wrap(self, func, switcher):
    # You can read switcher state
    switcher_name = switcher.name

    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} in {switcher_name}")
        return func(*args, **kwargs)

    return wrapper
```

## Benefits of Plugin Composition

1. **Separation of concerns** - Each plugin does one thing well
2. **Reusability** - AsyncPlugin works with any Switcher
3. **Testability** - Test plugins independently
4. **Flexibility** - Mix and match plugins as needed
5. **Observability** - LoggingPlugin tracks all handlers uniformly

## See Also

- [Plugin Development Guide](../plugins/development.md)
- [Middleware Pattern](../plugins/middleware.md)
- [Logging Documentation](../plugins/logging.md)
