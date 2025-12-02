# Advanced

## Protocol-Based Resolution

```python
@container.inject
def business_logic(logger: Logger, db: Database) -> str:
    logger.info("Processing")
    return db.query("SELECT 1")
```

## Scopes

- SINGLETON: one instance per container
- TRANSIENT: new instance per resolve
- REQUEST: request-bound lifetime

## Testing and Overrides

```python
mock = Mock(spec=Logger)
container.override(logger_token, mock)
...
container.clear_overrides()
```

## Structured Concurrency (Python 3.11+)

Injx provides first-class support for Python's structured concurrency primitives (`asyncio.TaskGroup`, `asyncio.timeout`, `ExceptionGroup`). This ensures production-grade reliability with proper error handling, timeouts, and cancellation.

### Why Structured Concurrency?

Traditional async patterns using `asyncio.gather(return_exceptions=True)` silently swallow errors:

```python
# ❌ BAD: Silent failures
results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
# Errors are hidden in results, cleanup may fail silently
```

Structured concurrency ensures errors are always visible:

```python
# ✅ GOOD: Errors propagate properly
async with asyncio.TaskGroup() as tg:
    for task in cleanup_tasks:
        tg.create_task(task)
# ExceptionGroup raised if any task fails
```

### Timeout Policies

Configure timeouts to prevent indefinite hangs:

```python
from injx import Container, TimeoutPolicy

# Production defaults (30s provider, 60s batch)
container = Container(timeout_policy=TimeoutPolicy.default())

# Fast timeouts for tests
container = Container(timeout_policy=TimeoutPolicy.testing())

# Custom configuration
container = Container(timeout_policy=TimeoutPolicy(
    provider_timeout=10.0,    # 10s per provider resolution
    cleanup_timeout=5.0,      # 5s for cleanup operations
    batch_timeout=60.0,       # 1 minute for batch operations
    max_concurrency=20        # 20 parallel resolutions max
))
```

Timeouts are enforced on:

- **Per-provider**: Each `aget()` call respects `provider_timeout`
- **Batch operations**: `batch_resolve_async()` respects `batch_timeout`
- **Cleanup**: Context exit respects `cleanup_timeout`

### Cooperative Cancellation

Cancel long-running resolution chains gracefully:

```python
from injx import Container

container = Container()

async def fetch_with_timeout():
    async with container.with_cancellation() as token:
        # Start a slow resolution
        task = asyncio.create_task(container.aget(SlowService))

        # Cancel after timeout
        try:
            result = await asyncio.wait_for(task, timeout=5.0)
        except asyncio.TimeoutError:
            token.cancel("Operation timed out")
            raise

# Resolution code can check for cancellation
async def my_provider():
    CancellationToken.check_cancelled()  # Raises if cancelled
    await do_slow_work()
    CancellationToken.check_cancelled()  # Check again
    return result
```

### Resolution Tracing

Debug complex dependency graphs with resolution tracing:

```python
from injx import Container

container = Container()

async def debug_resolution():
    async with container.trace_resolution() as traces:
        result = await container.aget(MyService)

    # Print resolution tree
    for trace in traces:
        print(trace.format_tree())

    # Output:
    # ✓ MyService (45.2ms)
    #   ✓ Database (30.1ms)
    #     ✓ ConnectionPool (15.4ms)
    #   ✓ Logger (5.3ms)

    # Export as JSON for analysis
    import json
    print(json.dumps([t.to_dict() for t in traces], indent=2))
```

### Error Handling with ExceptionGroups

Cleanup failures are aggregated and raised properly:

```python
from injx import Container, CleanupFailureGroup

container = Container()

# Register resources that may fail cleanup
container.register_context(ResourceA, lambda: resource_a_cm())
container.register_context(ResourceB, lambda: resource_b_cm())

try:
    async with container:
        # Use resources
        pass
except CleanupFailureGroup as eg:
    # Handle multiple cleanup failures
    print(f"Cleanup failed with {len(eg.exceptions)} error(s):")
    for exc in eg.exceptions:
        print(f"  - {type(exc).__name__}: {exc}")
```

### Ergonomic APIs

Convenient methods for common patterns:

```python
from injx import Container

container = Container()

# Optional dependency (returns None if not found)
service = await container.aget_or_none(OptionalService)
if service:
    service.do_work()

# Fallback on failure
service = await container.aget_with_fallback(
    Service,
    lambda: DefaultService()
)

# Result tuple (Go-style error handling)
result, error = await container.try_aget(Service)
if error:
    logger.error(f"Resolution failed: {error}")
else:
    result.do_work()

# Batch resolution with bounded concurrency
tokens = [ServiceA, ServiceB, ServiceC]
results = await container.batch_resolve_async(
    tokens,
    max_concurrency=5  # Limit parallel resolutions
)
```

### Migration from Pre-Structured Concurrency

If you're upgrading from older Injx versions:

1. **Breaking Change**: `Container.dispose()` now raises `CleanupFailureGroup` instead of silently swallowing cleanup errors.

```python
# Old code (errors silently ignored)
await container.dispose()

# New code (handle errors explicitly)
try:
    await container.dispose()
except CleanupFailureGroup as eg:
    for exc in eg.exceptions:
        logger.error(f"Cleanup error: {exc}")
```

2. **Optional**: Add timeout policies for production reliability:

```python
# Backward compatible (no timeouts)
container = Container(timeout_policy=TimeoutPolicy.unlimited())

# Recommended for production
container = Container(timeout_policy=TimeoutPolicy.default())
```

