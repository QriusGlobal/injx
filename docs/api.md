# API Reference

This page provides a comprehensive reference for all Injx classes, functions, and constants.

## Core Classes

### Container

**`injx.Container`**

The main dependency injection container that manages services and their lifecycles.

#### Performance Features (v1.2.0)

- **O(1) circular dependency detection**: Uses set-based tracking instead of O(n²) list concatenation
- **Memory-efficient singleton locks**: Proper cleanup after initialization prevents memory leaks
- **Transient scope correctness**: Ensures new instances are created on every resolution (no caching)
- **Batch operations**: Efficiently register and resolve multiple dependencies

#### Methods

**`register(token: Token[T], provider: Callable[[], T], scope: Scope = Scope.TRANSIENT) -> None`**

Register a provider function for a token.

- `token`: Token identifying the dependency
- `provider`: Function that creates instances
- `scope`: Lifecycle scope (SINGLETON, REQUEST, SESSION, TRANSIENT)

**`get(token: Token[T]) -> T`**

Synchronously resolve a dependency.

- `token`: Token to resolve
- **Returns**: Instance of type T
- **Raises**: `ResolutionError` if dependency cannot be resolved

**`aget(token: Token[T]) -> Awaitable[T]`**

Asynchronously resolve a dependency.

- `token`: Token to resolve  
- **Returns**: Awaitable instance of type T
- **Raises**: `ResolutionError` if dependency cannot be resolved

**`override(token: Token[T], instance: T) -> None`**

Override a registered dependency with a specific instance (useful for testing).

- `token`: Token to override
- `instance`: Instance to use instead of the registered provider

**`clear_overrides() -> None`**

Clear all dependency overrides.

**`register_context_sync(token: Token[T], context_provider: Callable[[], ContextManager[T]]) -> None`**

Register a synchronous context manager provider.

- `token`: Token identifying the dependency
- `context_provider`: Function returning a context manager

**`register_context_async(token: Token[T], context_provider: Callable[[], AsyncContextManager[T]]) -> None`**

Register an asynchronous context manager provider.

- `token`: Token identifying the dependency
- `context_provider`: Function returning an async context manager

**`request_scope() -> ContextManager[Container]`**

Create a synchronous request scope context manager.

**`async_request_scope() -> AsyncContextManager[Container]`**

Create an asynchronous request scope context manager.

**`session_scope() -> ContextManager[Container]`**

Create a session scope context manager.

**`aclose() -> Awaitable[None]`**

Asynchronously clean up all managed resources.

**`dispose() -> Awaitable[None]`**

Alias for `aclose()`. Asynchronously clean up all managed resources.

**`batch_register(registrations: list[tuple[Token[object], ProviderLike[object]]]) -> Container`**

Register multiple dependencies at once for improved performance.

- `registrations`: List of (token, provider) tuples
- **Returns**: Self for chaining

**`batch_resolve(tokens: list[Token[object]]) -> dict[Token[object], object]`**

Resolve multiple dependencies efficiently in a single operation.

- `tokens`: List of tokens to resolve
- **Returns**: Dictionary mapping tokens to resolved instances

**`batch_resolve_async(tokens: list[Token[object]]) -> Awaitable[dict[Token[object], object]]`**

Asynchronously resolve multiple dependencies with parallel execution.

- `tokens`: List of tokens to resolve
- **Returns**: Awaitable dictionary mapping tokens to resolved instances

**`use_overrides(mapping: dict[Token[Any], object]) -> ContextManager[None]`**

Temporarily override tokens within a context block.

```python
with container.use_overrides({LOGGER: fake_logger}):
    service = container.get(SERVICE)
    # service uses fake_logger
```

**`get_stats() -> dict[str, Any]`**

Get container performance statistics.

- **Returns**: Dictionary with:
  - `total_providers`: Number of registered providers
  - `singletons`: Number of cached singletons
  - `cache_hits`: Number of cache hits
  - `cache_misses`: Number of cache misses
  - `cache_hit_rate`: Cache hit ratio (0.0 to 1.0)
  - `avg_resolution_time`: Average resolution time in seconds

**`cache_hit_rate: float`**

Property returning the cache hit rate (0.0 to 1.0).

### Token

**`injx.Token[T]`**

A typed identifier for dependencies with pre-computed hash for O(1) lookups.

#### Performance Optimizations

- **Pre-computed hash**: Hash value calculated once during `__post_init__`
- **Immutable design**: Frozen dataclass with `__slots__` for memory efficiency
- **O(1) lookups**: Used as dictionary keys for constant-time container operations

#### Constructor

**`Token(name: str, type_: type[T], scope: Scope = Scope.TRANSIENT, qualifier: str | None = None, tags: tuple[str, ...] = ())`**

- `name`: Human-readable name
- `type_`: Expected Python type
- `scope`: Default lifecycle scope
- `qualifier`: Optional qualifier for multiple instances of same type
- `tags`: Optional tags for discovery/metadata

#### Properties

**`name: str`**

Human-readable name of the token.

**`type_: type[T]`**

The expected Python type for this token.

**`scope: Scope`**

Default lifecycle scope.

**`qualifier: str | None`**

Optional qualifier string.

**`tags: tuple[str, ...]`**

Immutable tuple of tags.

**`qualified_name: str`**

Fully qualified name including module, type, qualifier, and token name.

#### Methods

**`with_scope(scope: Scope) -> Token[T]`**

Return a copy with a different scope.

**`with_qualifier(qualifier: str) -> Token[T]`**

Return a copy with a qualifier.

**`with_tags(*tags: str) -> Token[T]`**

Return a copy with additional tags.

**`validate(instance: object) -> bool`**

Validate that an instance matches the token's expected type.

### TokenFactory

**`injx.TokenFactory`**

Factory for creating and caching commonly used tokens.

#### Methods

**`create(name: str, type_: type[T], scope: Scope = Scope.TRANSIENT, qualifier: str | None = None, tags: tuple[str, ...] = ()) -> Token[T]`**

Create a token with caching for common patterns.

**`singleton(name: str, type_: type[T]) -> Token[T]`**

Create a singleton-scoped token.

**`request(name: str, type_: type[T]) -> Token[T]`**

Create a request-scoped token.

**`session(name: str, type_: type[T]) -> Token[T]`**

Create a session-scoped token.

**`transient(name: str, type_: type[T]) -> Token[T]`**

Create a transient-scoped token.

**`qualified(qualifier: str, type_: type[T], scope: Scope = Scope.TRANSIENT) -> Token[T]`**

Create a qualified token.

**`clear_cache() -> None`**

Clear the internal token cache.

**`cache_size: int`**

Number of cached tokens.

## Enums

### Scope

**`injx.Scope`**

Enumeration of dependency lifecycle scopes.

#### Values

**`SINGLETON`**

One instance per container (process-wide).

**`REQUEST`**

One instance per request context.

**`SESSION`**

One instance per session context.

**`TRANSIENT`**

New instance for every resolution.

## Decorators and Markers

### inject

**`injx.inject(func: Callable = None, *, container: Container | None = None, cache: bool = True) -> Callable`**

Decorator that automatically injects dependencies based on type annotations.

- `func`: Function to decorate
- `container`: Container to use (uses default if None)
- `cache`: Whether to cache dependency analysis
- **Returns**: Decorated function with dependency injection

#### Usage

```python
@inject
def handler(logger: Logger, db: Database) -> None:
    # Dependencies automatically injected
    pass

@inject(container=my_container)
async def async_handler(service: AsyncService) -> None:
    # Use specific container
    pass
```

### Inject

**`injx.Inject[T]`**

Marker class for explicit dependency injection.

#### Usage

```python
from typing import Annotated

@inject
def handler(
    logger: Logger,  # Simple injection
    cache: Annotated[Cache, Inject(lambda: MockCache())]  # Custom provider
) -> None:
    pass
```

### Given

**`injx.Given[T]`**

Scala-style marker for implicit dependencies (alias for Inject[T]).

### Depends

**`injx.Depends(provider: Callable[[], T]) -> T`**

FastAPI-compatible dependency marker.

```python
def handler(service: Service = Depends(lambda: ServiceImpl())) -> None:
    pass
```

## Contextual Containers

### ContextualContainer

**`injx.ContextualContainer`**

Base class adding request/session context support via `contextvars`. The main `Container` class inherits from this.

#### Methods

**`resolve_from_context(token: Token[T]) -> T | None`**

Resolve dependency from current context without creating new instances.

**`store_in_context(token: Token[T], instance: T) -> None`**

Store instance in appropriate context based on token scope.

**`clear_request_context() -> None`**

Clear current request context.

**`clear_session_context() -> None`**

Clear current session context.

**`clear_all_contexts() -> None`**

Clear all contexts including singletons.

### RequestScope

**`injx.RequestScope`**

Helper class for managing request-scoped dependencies.

#### Usage

```python
async with RequestScope(container) as scope:
    service = scope.resolve(ServiceToken)
```

### SessionScope

**`injx.SessionScope`**

Helper class for managing session-scoped dependencies.

## Exceptions

### InjxError

**`injx.exceptions.InjxError`**

Base exception for all Injx errors.

### ResolutionError

**`injx.exceptions.ResolutionError`**

Raised when a dependency cannot be resolved.

#### Properties

**`token: Token[Any]`**

The token that couldn't be resolved.

**`chain: list[Token[Any]]`**

The resolution chain leading to the error.

**`cause: str`**

Human-readable cause description.

### CircularDependencyError

**`injx.exceptions.CircularDependencyError`**

Raised when circular dependency is detected. Inherits from `ResolutionError`.

### AsyncCleanupRequiredError

**`injx.exceptions.AsyncCleanupRequiredError`**

Raised when synchronous cleanup is attempted on async-only resources.

### CleanupFailureGroup

**`injx.exceptions.CleanupFailureGroup`** *(Python 3.11+)*

Raised when multiple cleanup operations fail during scope exit. Wraps `BaseExceptionGroup` (Python 3.11+) to provide structured error reporting for cleanup failures.

#### Properties

**`exceptions: list[BaseException]`**

List of individual cleanup exceptions.

#### Usage

```python
try:
    await container.dispose()
except CleanupFailureGroup as eg:
    for exc in eg.exceptions:
        logger.error(f"Cleanup failed: {exc}")
```

## Structured Concurrency (Python 3.11+)

### TimeoutPolicy

**`injx.TimeoutPolicy`**

Configuration for async operation timeouts. Prevents indefinite hangs and enables graceful degradation.

#### Constructor

**`TimeoutPolicy(provider_timeout: float | None = None, cleanup_timeout: float = 5.0, batch_timeout: float | None = None, max_concurrency: int = 10)`**

- `provider_timeout`: Max seconds for single provider resolution (None = unlimited)
- `cleanup_timeout`: Max seconds for cleanup operations (default: 5.0)
- `batch_timeout`: Max seconds for batch operations (None = unlimited)
- `max_concurrency`: Max parallel resolutions in batch operations (default: 10)

#### Class Methods

**`TimeoutPolicy.default() -> TimeoutPolicy`**

Sensible defaults for production (30s provider, 60s batch, 10 concurrent).

**`TimeoutPolicy.testing() -> TimeoutPolicy`**

Fast timeouts for tests (1s provider, 2s batch, 5 concurrent).

**`TimeoutPolicy.unlimited() -> TimeoutPolicy`**

No timeouts for backward compatibility.

#### Usage

```python
# Production with defaults
container = Container(timeout_policy=TimeoutPolicy.default())

# Custom configuration
container = Container(timeout_policy=TimeoutPolicy(
    provider_timeout=10.0,  # 10s per provider
    cleanup_timeout=5.0,    # 5s cleanup
    batch_timeout=60.0,     # 1 minute for batch ops
    max_concurrency=20      # 20 parallel resolutions
))

# Test environment
container = Container(timeout_policy=TimeoutPolicy.testing())
```

### CancellationToken

**`injx.CancellationToken`**

Cooperative cancellation for dependency resolution chains.

#### Properties

**`is_cancelled: bool`**

Whether cancellation has been requested.

**`reason: str | None`**

The cancellation reason, if cancelled.

#### Methods

**`cancel(reason: str = "Operation cancelled") -> None`**

Request cancellation of ongoing operations. Idempotent.

**`raise_if_cancelled() -> None`**

Raise `CancelledError` if cancellation was requested.

**`on_cancel(callback: Callable[[], None]) -> None`**

Register a callback to invoke when cancelled.

**`CancellationToken.get_current() -> CancellationToken | None`**

Get the cancellation token for the current context.

**`CancellationToken.check_cancelled() -> None`**

Check the current context for cancellation. Raises `CancelledError` if cancelled.

#### Usage

```python
async with container.with_cancellation() as token:
    task = asyncio.create_task(container.aget(SlowService))

    await asyncio.sleep(0.5)
    if should_cancel:
        token.cancel("User requested cancellation")

    try:
        result = await task
    except asyncio.CancelledError:
        print("Resolution was cancelled")
```

### ResolutionTrace

**`injx.ResolutionTrace`**

Trace information for a single dependency resolution. Used for debugging and performance analysis.

#### Properties

**`token_name: str`**

Name of the token being resolved.

**`duration_ms: float`**

Resolution duration in milliseconds.

**`success: bool`**

Whether resolution succeeded.

**`error: str | None`**

Error message if resolution failed.

**`children: list[ResolutionTrace]`**

Nested resolution traces for dependencies.

#### Methods

**`format_tree(indent: int = 0) -> str`**

Format the trace as a tree for display.

**`to_dict() -> dict[str, Any]`**

Convert trace to dictionary for JSON serialization.

#### Usage

```python
async with container.trace_resolution() as traces:
    result = await container.aget(MyService)

for trace in traces:
    print(trace.format_tree())

# Output:
# ✓ MyService (45.2ms)
#   ✓ Database (30.1ms)
#     ✓ ConnectionPool (15.4ms)
#   ✓ Logger (5.3ms)
```

### Container Structured Concurrency Methods

**`Container.with_cancellation() -> AsyncContextManager[CancellationToken]`**

Create a cancellation context for async operations.

```python
async with container.with_cancellation() as token:
    # Operations can check token.is_cancelled
    result = await container.aget(Service)
```

**`Container.trace_resolution() -> AsyncContextManager[list[ResolutionTrace]]`**

Enable resolution tracing for debugging.

```python
async with container.trace_resolution() as traces:
    await container.aget(MyService)
print(traces[0].format_tree())
```

**`Container.aget_or_none(token: Token[T]) -> T | None`**

Resolve a dependency, returning None if not found.

```python
service = await container.aget_or_none(OptionalService)
if service:
    service.do_work()
```

**`Container.aget_with_fallback(token: Token[T], fallback: Callable[[], T | Awaitable[T]]) -> T`**

Resolve with a fallback if resolution fails.

```python
service = await container.aget_with_fallback(
    Service,
    lambda: DefaultService()
)
```

**`Container.try_aget(token: Token[T]) -> tuple[T | None, Exception | None]`**

Resolve returning (value, None) on success or (None, error) on failure.

```python
result, error = await container.try_aget(Service)
if error:
    logger.error(f"Resolution failed: {error}")
else:
    result.do_work()
```

**`Container.batch_resolve_async(tokens: list[Token[object]], max_concurrency: int | None = None) -> dict[Token[object], object]`**

Resolve multiple dependencies with bounded concurrency and optional batch timeout.

```python
tokens = [ServiceA, ServiceB, ServiceC]
results = await container.batch_resolve_async(tokens, max_concurrency=5)
```

## Container Management Functions

### get_default_container

**`injx.get_default_container() -> Container`**

Get the global default container.

- **Returns**: The default container instance
- **Raises**: `RuntimeError` if no default container is set

### set_default_container

**`injx.set_default_container(container: Container) -> None`**

Set the global default container.

- `container`: Container instance to use as default

## Metaclass Support

### Injectable

**`injx.Injectable`**

Metaclass for automatic service registration.

#### Usage

```python
class EmailService(metaclass=Injectable):
    __injectable__ = True
    __token_name__ = "email_service"
    __scope__ = Scope.SINGLETON
    
    def __init__(self, logger: Logger):
        self.logger = logger
```

## Type Annotations

### Protocols

Injx works with Python's `Protocol` system for structural typing:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Logger(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
```

### Generic Support

Injx fully supports generic types:

```python
from typing import Generic, TypeVar

T = TypeVar('T')

class Repository(Protocol, Generic[T]):
    def save(self, entity: T) -> None: ...
    def find_by_id(self, id: int) -> T | None: ...

USER_REPO = Token[Repository[User]]("user_repo")
```

## Constants and Configuration

### Version Information

**`injx.__version__`**

String containing the current Injx version.

**`injx.__author__`**

Author information.

## Performance Characteristics

- **Token resolution**: O(1) time complexity due to pre-computed hashes
- **Injection analysis**: Cached for repeated use of `@inject`
- **Memory overhead**: ~500 bytes per registered service
- **Thread safety**: Full thread and async safety via `contextvars`
- **Circular dependency detection**: Early detection with detailed error chains

## Type Safety Features

- **PEP 561 compliant**: Includes `py.typed` marker file
- **Full static analysis**: Works with mypy, basedpyright, pyright
- **Protocol validation**: Runtime checking with `@runtime_checkable`
- **Generic preservation**: Complete generic type support throughout the API
- **Zero runtime type overhead**: Type checking is compile-time only (unless explicitly requested)

This API reference covers all public interfaces in Injx. For examples and usage patterns, see the other documentation sections.