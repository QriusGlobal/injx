# Injx Architecture Specification

## Abstract

Injx implements type-safe dependency injection for Python 3.13+ through a pure Python architecture designed for correctness, maintainability, and predictable performance. This specification documents architectural decisions derived from analysis of existing dependency injection library failures, particularly python-dependency-injector's Cython-related stability issues.

## Design Goals

### Primary Goals

1. **Correctness**: Zero runtime failures through comprehensive type checking and pure Python implementation
2. **Type Safety**: Complete static analysis compatibility with basedpyright and mypy
3. **Maintainability**: Standard Python debugging and contribution workflows
4. **Predictable Performance**: O(1) algorithmic complexity with measurable characteristics

### Non-Goals

1. **Maximum Performance**: Prioritizing stability over marginal performance gains
2. **Backward Compatibility**: Targeting Python 3.13+ exclusively for modern language features
3. **Framework Agnosticism**: Optimized for async-first web applications and SDK development

## Architectural Overview

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Public API Layer                        │
│  Container, Token, inject, Scope                           │
├─────────────────────────────────────────────────────────────┤
│                 Dependency Resolution                       │
│  Resolution engine, circular detection, scope management   │
├─────────────────────────────────────────────────────────────┤
│                  Provider Abstraction                      │
│  Factory, Singleton, Contextual providers                  │
├─────────────────────────────────────────────────────────────┤
│                   Token System                             │
│  Immutable tokens, hash computation, type preservation     │
├─────────────────────────────────────────────────────────────┤
│                  Foundation Layer                          │
│  Threading, error handling, performance monitoring         │
└─────────────────────────────────────────────────────────────┘
```

## Token System Design

### Token Implementation

```python
@dataclass(frozen=True, slots=True)
class Token(Generic[T]):
    name: str
    type_: type[T]
    scope: Scope = Scope.TRANSIENT
    qualifier: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    _hash: int = field(init=False, repr=False, compare=False)
```

**Design Rationale:**
- Immutability prevents runtime modification bugs
- Pre-computed hashes enable O(1) lookup performance
- Generic type preservation maintains static analysis compatibility
- Slots reduce memory overhead per token instance

### Hash Computation Strategy

**Algorithm:**
```python
hash_tuple = (
    self.name,
    self.type_.__module__,
    self.type_.__name__,
    self.scope.value,
    self.qualifier,
    self.tags,
)
```

**Collision Analysis:**
- Type module and name provide namespace isolation
- Qualifier enables multiple instances of same type
- Scope differentiation prevents cross-scope conflicts
- Expected collision rate: < 1 in 10^12 for practical applications

## Container Architecture

### Internal State Management

```python
class Container:
    _providers: dict[Token, Callable]
    _singletons: dict[Token, Any]
    _singleton_locks: dict[Token, threading.Lock]
    _metadata: dict[Token, ProviderMetadata]
```

**Thread Safety Model:**
- Global container lock for registration operations
- Per-token locks for singleton initialization
- Lock-free reads for established singletons
- ContextVar isolation for request/session scopes

### Resolution Algorithm

**Lookup Process:**
1. Token hash computation: O(1)
2. Provider retrieval: O(1) dictionary lookup
3. Dependency resolution: Recursive with cycle detection
4. Instance creation: Provider-specific strategy
5. Result caching: Scope-dependent storage

**Circular Dependency Detection:**
```python
def resolve(token: Token[T], resolution_path: set[Token]) -> T:
    if token in resolution_path:
        chain = " -> ".join(t.name for t in resolution_path)
        raise CircularDependencyError(f"Circular dependency: {chain} -> {token.name}")
```

## Scope Management

### Scope Hierarchy

```
SINGLETON    # Container lifetime, thread-safe
SESSION      # Context variable lifetime
REQUEST      # Nested context variable lifetime  
TRANSIENT    # No caching, new instance per resolution
```

### ContextVar Implementation

```python
_request_context: ContextVar[dict[Token, Any]] = ContextVar('request_context')
_session_context: ContextVar[dict[Token, Any]] = ContextVar('session_context')
```

**Isolation Guarantees:**
- Request scope isolated between concurrent requests
- Session scope maintains state across multiple requests
- No cross-contamination in async environments
- Automatic cleanup when context exits

### ChainMap Live-View Pattern

The scope hierarchy is implemented using `ChainMap` with `MappingProxyType` to create a live-view architecture:

```python
# Scope chaining: request -> session -> singletons
new_context = ChainMap(
    request_cache,                              # Layer 1: Mutable request cache
    session_cache,                              # Layer 2: Mutable session cache
    container._singletons_mapping()             # Layer 3: Live view of singletons
)  # type: ignore[arg-type]
```

**Live-View Semantics:**
- `MappingProxyType` provides read-only, live view of singleton cache
- `ChainMap` layers scopes without copying data
- Changes to singletons immediately visible to all active scopes
- Critical for `clear_all_contexts()` and resource cleanup

**Type System Conflict:**
- ChainMap expects `MutableMapping` in type signature
- MappingProxyType is not MutableMapping (read-only)
- Runtime compatibility: ChainMap only needs `Mapping` protocol
- `type: ignore[arg-type]` preserves correct behavior vs. type checker

**Why Not dict() Conversion:**
- `dict(mapping_proxy)` creates snapshots, not live views
- Cleared singletons would remain in scope snapshots
- Memory leaks from unreachable cached instances
- Inconsistent state across concurrent scopes
- Resource cleanup failures

## Type Safety Architecture

### Protocol-Based Design

```python
class Resolvable(Protocol[T]):
    def get(self, token: Token[T]) -> T: ...
    async def aget(self, token: Token[T]) -> T: ...
```

**Static Analysis Compatibility:**
- Generic type preservation through protocol inheritance
- No dynamic attribute access patterns
- Explicit return type annotations
- basedpyright and mypy compatibility verification

### Injection Decorator Implementation

```python
def inject(func: Callable[P, R]) -> Callable[P, R]:
    signature = inspect.signature(func)
    dependencies = extract_dependencies(signature)
    
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        resolved = resolve_dependencies(dependencies)
        return func(*args, **kwargs, **resolved)
    return wrapper
```

**Type Preservation:**
- ParamSpec maintains parameter specification
- TypeVar preserves return type
- Runtime signature inspection cached at decoration time
- Zero overhead for non-injected parameters

## Performance Characteristics

### Algorithmic Complexity

| Operation | Complexity | Implementation |
|-----------|------------|----------------|
| Token creation | O(1) | Hash computation |
| Provider registration | O(1) | Dictionary insertion |
| Dependency resolution | O(d) | d = dependency depth |
| Singleton access | O(1) | Dictionary lookup after creation |
| Circular detection | O(d) | Set membership testing |

### Memory Usage

**Per-Token Overhead:**
- Token instance: ~120 bytes (with slots)
- Provider metadata: ~80 bytes
- Singleton storage: ~40 bytes
- Total: ~240 bytes per registered dependency

**Scaling Characteristics:**
- Linear memory growth with dependency count
- No memory leaks through weak reference usage
- Automatic cleanup of request/session scopes

## Error Handling Strategy

### Error Hierarchy

```python
class InjxError(Exception):
    """Base exception for all injx errors."""

class ResolutionError(InjxError):
    """Dependency resolution failed."""
    
    def __init__(self, token: Token, chain: list[Token], cause: Exception):
        self.token = token
        self.chain = chain
        self.cause = cause
```

**Error Message Format:**
```
Cannot resolve token 'user_service':
  Resolution chain: user_service -> database -> connection_pool
  Cause: No provider registered for token 'connection_pool'
```

**Design Principles:**
- Complete resolution context in every error
- Structured error data for programmatic handling  
- Clear causality chains for debugging
- No silent failures or undefined behavior

## Testing Architecture

### Override Mechanism

```python
class Container:
    def override(self, token: Token[T], provider: Callable[[], T]) -> None:
        """Override provider for testing purposes."""
        
    @contextmanager
    def test_scope(self) -> Iterator['Container']:
        """Create isolated test container."""
```

**Testing Guarantees:**
- Complete isolation between test cases
- No state leakage between tests
- Deterministic behavior in concurrent test execution
- Compatible with pytest fixtures and asyncio

### Mock Integration

```python
def mock_dependency(token: Token[T]) -> Mock:
    """Create type-safe mock for dependency."""
    return Mock(spec=token.type_)
```

## Security Considerations

### Injection Attack Prevention

**Threat Model:**
- Malicious provider registration
- Type confusion attacks
- Resource exhaustion via circular dependencies

**Mitigation Strategies:**
- Immutable token design prevents runtime manipulation
- Type checking prevents incompatible provider registration
- Depth limits prevent infinite recursion
- No eval() or exec() usage in core library

### Resource Management

**Resource Lifecycle:**
- Explicit resource registration and cleanup
- LIFO cleanup order for predictable teardown
- Timeout mechanisms for async resource initialization
- Exception safety guarantees for partial initialization

## Extension Points

### Provider Interface

```python
class Provider(Protocol[T]):
    def provide(self, container: Resolvable) -> T:
        """Create instance with dependency resolution."""
        
    def cleanup(self, instance: T) -> None:
        """Clean up instance resources."""
```

### Configuration Sources

```python
class ConfigurationSource(Protocol):
    def configure(self, container: Container) -> None:
        """Apply configuration to container."""
```

**Supported Sources:**
- Pydantic Settings integration
- TOML file parsing
- Environment variable binding
- Runtime configuration

## Migration Compatibility

### From python-dependency-injector

**Breaking Changes:**
- Container API requires explicit token registration
- No string-based dependency lookup
- Scope enum instead of provider classes
- Pure Python implementation (no Cython performance claims)

**Migration Tools:**
- Automated token generation from existing providers
- Configuration conversion utilities
- Testing pattern migration guides

### From python-inject

**Breaking Changes:**
- No global injector state
- Container-scoped dependency resolution
- Explicit dependency registration required

## Performance Benchmarks

### Target Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Token creation | <1μs | timeit microbenchmark |
| Cold lookup | <2μs | First resolution timing |
| Warm lookup | <0.5μs | Cached resolution timing |
| Memory per dependency | <500 bytes | memory_profiler analysis |
| Import time | <50ms | Module import timing |

### Regression Testing

**Continuous Benchmarking:**
- Automated performance testing in CI
- Benchmark result storage and comparison
- Performance regression alerts
- Memory usage monitoring

## Maintenance Guidelines

### Code Quality Standards

**Requirements:**
- 100% type checking compliance with basedpyright
- 95%+ test coverage for core functionality
- Zero runtime warnings in test execution
- Comprehensive docstring documentation

### Dependency Management

**Core Library:**
- Zero runtime dependencies
- Development dependencies clearly separated
- Optional dependencies for extensions only
- Minimal API surface area

### Release Process

**Quality Gates:**
- All tests pass on supported Python versions
- Performance benchmarks within acceptable ranges  
- Documentation builds successfully
- Security audit completion

This architecture specification serves as the authoritative reference for Injx implementation decisions, ensuring consistency with the design principles derived from analysis of existing dependency injection library failures.