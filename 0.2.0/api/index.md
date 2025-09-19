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

```
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

```
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

```
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

```
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

```
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

```
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

```
from typing import Protocol, runtime_checkable

@runtime_checkable
class Logger(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
```

### Generic Support

Injx fully supports generic types:

```
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
