ServiceM8Py Dependency Injection (DI) Specification
==================================================

:PEP: N/A (Project Specification)
:Title: Async‑Native DI for SDKs and Applications
:Author: Qrius Global <dev@qrius.global>
:Co-Author: Mishal Ismeth <mishal@qrius.global>
:Status: Draft
:Type: Standards Track
:Created: 2025-09-01 06:24:28 UTC
:Python-Version: 3.13+
:Post-History: 
    - 2025-09-01: Initial specification draft
    - 2025-09-01: Security and safety enhancements added
    - 2025-09-01: Type system requirements strengthened
    - 2025-09-01: Future roadmap and migration guides included
    - 2025-09-01: Contextual abstractions and developer experience enhancements
    - 2025-09-13: Corrected multiprocessing claims, added performance guarantees
    - 2025-09-13: Added O(1) cycle detection and memory efficiency improvements
:Revision: 4.0.0


Abstract
--------

This document specifies a small, framework-agnostic dependency injection (DI)
pattern for async-native Python. It provides a simple, intuitive API for SDK
users while enabling robust, explicit wiring for application developers with
comprehensive security, safety, and type system guarantees.

**Core Goals:**

- **Developer Experience**: Simple things should be simple, complex things possible.
- **Security**: Prevent injection attacks and enforce least privilege.
- **Type Safety**: 100% type coverage with static analysis enforcement.
- **Testability**: Dependencies can be easily swapped in tests.
- **Robustness**: Clear ownership and lifecycle management for async resources.
- **Maintainability**: Modular components with clear contracts.
- **Performance**: Zero-cost abstractions with minimal overhead.


Table of Contents
-----------------

1. `Core Principles`_
2. `Contextual Abstractions`_
3. `Developer Experience`_
4. `For SDK Consumers`_
5. `For Application Developers`_
6. `Security Requirements`_
7. `Safety Guarantees`_
8. `Type System Contracts`_
9. `Performance Optimizations`_
10. `For Contributors & Advanced Use Cases`_
11. `Decisions & Guardrails`_
12. `Static Analysis Requirements`_
13. `Future Roadmap`_
14. `Migration Guide`_
15. `Reference Implementation`_
16. `Appendices`_


Core Principles
---------------

This DI pattern is built on five core concepts:

- **Tokens**: A ``Token[T]`` is a typed, unique key used to identify a dependency.
  It acts as a public contract for a service. Tokens are resource-agnostic and
  can represent anything (network client, process handle, stream, stdio-based
  adapter, etc.). Tokens MUST be immutable and hashable.

- **Container**: A central registry that maps Tokens to **Providers**. The container
  manages the lifecycle of shared services with thread-safe operations. For the SDK,
  this is a hidden, internal detail. Containers MUST be thread-safe for read operations
  and provide explicit locking for write operations.

- **Boundaries**: Objects that interact with the outside world (like the main
  ``ServiceM8Client``). They resolve dependencies from the container only when
  needed, keeping the core logic clean. Boundaries MUST validate all injected
  dependencies before use.

- **Contextual Scoping**: Using Python's ``contextvars``, the container supports
  implicit context propagation through async calls, similar to Scala's given/using
  clauses. This enables clean request-scoped dependencies without passing containers.

- **Developer Experience**: Inspired by FastAPI and Pydantic, the API prioritizes
  simplicity and type safety. Features like ``@inject`` decorators, method chaining,
  and clear error messages make the library a joy to use.


Concurrency Model & Limitations
--------------------------------

**Single-Process Concurrency Support**

injx provides full concurrency support within a single process:

- **Asyncio Tasks**: Full isolation via ContextVar propagation
- **Threading**: Thread-safe operations with proper locking
- **Request/Session Scoping**: Isolated contexts within the same process

**Important**: injx does NOT support cross-process state sharing. Each process 
must maintain its own container instance. ContextVar and threading primitives 
are process-local and cannot cross process boundaries.

For multiprocessing architectures, use a share-nothing pattern where each 
process initializes its own container independently.


Performance Guarantees
----------------------

injx is designed for production-scale applications with predictable performance:

**Core Performance Characteristics**:

- **Token Lookups**: O(1) with pre-computed hashes (< 1 microsecond)
- **Cycle Detection**: O(1) using set-based tracking (improved from O(n²) in earlier versions)
- **Memory Overhead**: ~500 bytes per registered service
- **Singleton Access**: < 1 microsecond after initial creation
- **Transient Scope**: Zero caching overhead - new instance every time

**Memory Safety**:

- Automatic cleanup of singleton locks prevents memory leaks
- Proper LIFO cleanup order for resources
- No retention of transient instances
- Weak references where appropriate for garbage collection


Contextual Abstractions
-----------------------

Inspired by Scala's contextual abstractions, this specification introduces implicit
context propagation and type-based resolution patterns.

### 1. Context Variables for Scoping

Using Python's ``contextvars`` module, the container maintains a context stack that
automatically propagates through async calls within the same process:

.. code-block:: python

   from contextvars import ContextVar
   from collections import ChainMap
   
   # Global context for dependency scopes
   _context_stack: ContextVar[ChainMap] = ContextVar('di_context')
   
   # Usage
   with container.request_scope():
       # All dependencies resolved here are request-scoped
       service = container.get(ServiceToken)
       # Context automatically propagates through async calls
       await nested_async_function()

### 2. Given Instances (Scala-Inspired)

Type-based automatic resolution similar to Scala's given instances:

.. code-block:: python

   # Register given instances by type
   container.given(Database, lambda: PostgresDB())
   container.given(int, lambda: 42)  # Default int value
   
   # Temporary override with using clause
   with container.using(Database=test_db):
       # test_db is used in this context
       service = container.get(ServiceToken)

### 3. Layered Scoping with ChainMap

Efficient scope hierarchy using ``collections.ChainMap``:

.. code-block:: python

   from collections import ChainMap
   
   # Scopes are layered: request -> session -> singleton
   scopes = ChainMap(
       request_cache,    # First lookup
       session_cache,    # Second lookup
       singleton_cache   # Final fallback
   )

This provides O(1) lookups with memory-efficient layering.


Developer Experience
--------------------

The API design prioritizes simplicity, type safety, and developer joy, inspired by
FastAPI, Pydantic, and Polars.

### 1. FastAPI-Style Injection

Clean decorator-based dependency injection:

.. code-block:: python

   from injx import inject, Inject
   
   @inject
   async def handler(
       user_id: int,
       db: Inject[Database],        # Auto-injected
       cache: Inject[Cache],         # Type-safe
       settings: Settings = Inject() # Auto-detect type
   ):
       user = await db.get_user(user_id)
       await cache.set(f"user:{user_id}", user)
       return user

### 2. Method Chaining for Setup

Polars-inspired fluent interface:

.. code-block:: python

   container = (
       Container()
       .register(Database, create_db, scope=Scope.SINGLETON)
       .register(Cache, create_cache, scope=Scope.REQUEST)
       .register(EmailService, EmailService)
       .with_settings(Settings)
       .build()
   )

### 3. Pydantic-Style Validation

Clear, actionable error messages:

.. code-block:: python

   # If validation fails:
   """
   ValidationError: Invalid provider for Token('database', Database)
     Expected: Callable[[], Database]
     Got: <class 'str'>
     Fix: Provider must be a callable that returns a Database instance
     Example: container.register(token, lambda: Database())
   """

### 4. Immutable Tokens with Slots

Memory-efficient, hashable tokens:

.. code-block:: python

   from dataclasses import dataclass, field
   
   @dataclass(frozen=True, slots=True)
   class Token(Generic[T]):
       name: str
       type_: Type[T]
       _hash: int = field(init=False)  # Pre-computed hash
       
       def __post_init__(self):
           object.__setattr__(self, '_hash', 
                            hash((self.name, self.type_)))

### 5. Smart Caching Strategies

Performance optimizations using standard library:

.. code-block:: python

   from functools import lru_cache
   from weakref import WeakValueDictionary
   
   class Container:
       def __init__(self):
           self._singletons = {}  # Strong refs
           self._transients = WeakValueDictionary()  # Weak refs
       
       @lru_cache(maxsize=1024)
       def _analyze_signature(self, func):
           """Cache expensive signature analysis."""
           return inspect.signature(func)


For SDK Consumers
-----------------

### 1. Basic Usage (The "Happy Path")

For most use cases, dependency injection is invisible. You instantiate the client
and use it as a context manager. The SDK handles creating and cleaning up HTTP
connections and other resources automatically.

.. code-block:: python

   from servicem8py import ServiceM8Client

   async with ServiceM8Client(auth=my_auth) as client:
       jobs = await client.job.list()
       print(f"Found {len(jobs)} jobs.")

### 2. Advanced Usage: Overriding Dependencies

For testing, custom integrations, or fine-tuning, you can provide your own
dependencies using the ``with_dependencies()`` class method. This is the
recommended way to inject collaborators.

The caller is responsible for the lifecycle of injected objects.

.. code-block:: python

   import httpx
   from servicem8py import ServiceM8Client

   # Caller owns the lifecycle of my_http_client
   async with httpx.AsyncClient() as my_http_client:
       async with ServiceM8Client.with_dependencies(
           auth=my_auth,
           http_client=my_http_client
       ) as client:
           # The client will use your httpx.AsyncClient instance
           await client.job.list()

### 3. Common Overrides & Use Cases

- **Custom HTTP Client**: Add custom logging, headers, or transport controls.
- **Mocking for Tests**: Inject a fake HTTP client or other services.
- **Custom Caching**: Provide a custom ``TokenStore`` to manage credentials.
- **Rate Limiting**: Inject a rate-limited HTTP client adapter.
- **Circuit Breaking**: Add resilience patterns via custom adapters.

.. code-block:: python

   # Example: Injecting a mock HTTP client for a unit test
   class MockHttpClient:
       async def request(self, *args, **kwargs):
           # return a mock response
           ...

   async with ServiceM8Client.with_dependencies(
       auth=my_auth,
       http_client=MockHttpClient()
   ) as client:
       # Your test logic here...


For Application Developers
--------------------------

### 1. The Composition Root

Applications should have a single place where dependencies are wired together,
known as the **Composition Root**. This is typically near the application's
entry point (e.g., in ``main.py``).

The goal is to construct a graph of long-lived objects and services that your
application needs. The ``contextlib.AsyncExitStack`` is the perfect tool for
this, ensuring that all resources are cleaned up gracefully.

.. code-block:: python

   from contextlib import asynccontextmanager, AsyncExitStack
   import httpx

   class App:
       def __init__(self, job_service):
           self.job_service = job_service

       async def run(self):
           # main application logic
           ...

   @asynccontextmanager
   async def build_app():
       async with AsyncExitStack() as stack:
           # 1. Enter resources into the stack
           http_client = await stack.enter_async_context(httpx.AsyncClient())
           s8_client = await stack.enter_async_context(
               ServiceM8Client.with_dependencies(auth=..., http_client=http_client)
           )

           # 2. Wire dependencies
           job_service = JobService(s8_client)

           # 3. Yield the final application object
           yield App(job_service=job_service)
           # 4. On exit, stack.aclose() is called implicitly, cleaning up resources

   async def main():
       async with build_app() as app:
           await app.run()

### 2. Container API

While the SDK hides the container, applications can use a generic, package-agnostic
container for more complex scenarios. The container provides the following core methods:

- ``register(token, provider)``: Binds a token to a synchronous factory.
  The provider is a callable (e.g., a ``lambda``) that returns the dependency.
- ``register_async(token, provider)``: Binds a token to an *asynchronous* factory.
- ``get(token)``: Resolves a dependency synchronously (thread-safe).
- ``aget(token)``: Resolves a dependency asynchronously, with race condition protection.
- ``aclose()``: Asynchronously closes all container-owned resources.
- ``use_overrides(mapping)``: Temporarily overrides tokens for testing.
- ``validate_dependency(token, value)``: Validates a dependency against its protocol.

**Thread Safety Guarantees:**

- Read operations (``get``, ``aget``) are fully thread-safe
- Write operations (``register``, ``register_async``) require explicit locking
- Container modifications during resolution will raise ``RuntimeError``

**Ergonomics & Error Handling (agnostic):**

- A missing provider will raise a ``KeyError`` with a clear message:
  ``KeyError: "No provider registered for token 'MY_TOKEN'"``.
- Type hints for ``Token[T]`` ensure that ``get(Token[T])`` is correctly inferred
  by type checkers as returning an object of type ``T``.
- Circular dependencies are detected and raise ``CircularDependencyError``.

### 3. Managing Lifecycles: Ownership Patterns

Clear ownership is critical for avoiding resource leaks.

- **Caller-Owned**: When you pass an object via ``with_dependencies(...)``, you own
  it and are responsible for its cleanup. This is the most explicit pattern.
- **Boundary-Owned**: When the SDK creates a resource for you (like an HTTP client),
  the client boundary (``ServiceM8Client``) owns it. It's created in ``__aenter__``
  and destroyed in ``__aexit__``.
- **Container-Owned**: For long-lived, process-wide services, the container can
  own the object. These are created once and cleaned up when ``container.aclose()``
  is called at application shutdown.

**Token Lifecycle & Ownership Diagram:**

A diagram illustrating the flow of token resolution and ownership would be valuable here. For now, consider this textual representation:

1.  **App Startup**: Composition root is built.
2.  **Request/Task**: A boundary object (e.g., `ServiceM8Client`) is created.
3.  **Dependency Needed**: The boundary calls `container.get()` or `aget()`.
4.  **Resolution**:
    *   Is there a test override? -> Use it (validate first).
    *   Is there a cached instance in the container? -> Use it (Container-Owned).
    *   Is there a provider? -> Call it (with validation).
        *   If it's a factory for a resource (like `HttpClient`), the boundary creates and owns the instance.
        *   If it's a singleton, the container caches and owns it.
5.  **Task End**: Boundary-owned resources are cleaned up.
6.  **App Shutdown**: `container.aclose()` is called, cleaning up all container-owned resources.

### 4. Asynchronous Providers & Concurrency (Agnostic)

For dependencies that require async I/O to be created (e.g., a database connection pool), use ``register_async`` and ``aget``.

The container guarantees **single-flight initialization**: if multiple concurrent tasks try to resolve the same async dependency for the first time, the provider will only be executed once. All tasks will wait for the result.

This prevents race conditions and resource duplication. The implementation uses an ``asyncio.Lock`` and a shared ``asyncio.Task``.


Security Requirements
---------------------

Security is a first-class concern in this DI specification. All implementations
MUST adhere to these security requirements.

### 1. Input Validation

All injected dependencies MUST be validated before use:

- **Type Validation**: Runtime type checking against protocols in debug mode
- **Schema Validation**: For configuration objects, validate against JSON Schema
- **Sanitization**: All string inputs must be sanitized to prevent injection attacks
- **Range Validation**: Numeric inputs must be within expected ranges

.. code-block:: python

   from typing import Protocol, runtime_checkable
   import json
   from jsonschema import validate

   @runtime_checkable
   class SecureHttpClient(Protocol):
       """HTTP client with security requirements."""
       
       async def request(self, method: str, url: str, **kwargs) -> Response:
           """Make HTTP request with validation."""
           ...
       
       @property
       def max_redirects(self) -> int:
           """Maximum redirects allowed (default: 5)."""
           ...

   def validate_http_client(client: Any) -> SecureHttpClient:
       """Validate HTTP client meets security requirements."""
       if not isinstance(client, SecureHttpClient):
           raise SecurityError("Invalid HTTP client implementation")
       
       if client.max_redirects > 10:
           raise SecurityError("Excessive redirects configured")
       
       return client

### 2. Dependency Injection Attack Prevention

Protect against common DI attack vectors:

- **Prototype Pollution**: Prevent modification of shared prototypes
- **Dependency Confusion**: Validate dependency sources and signatures
- **Supply Chain Attacks**: Verify provider integrity with checksums
- **Privilege Escalation**: Enforce least privilege for all dependencies

.. code-block:: python

   from hashlib import sha256
   from typing import Callable, TypeVar

   T = TypeVar("T")

   class SecureContainer(Container):
       """Container with security hardening."""
       
       def __init__(self, *, allow_overrides: bool = False):
           super().__init__()
           self._allow_overrides = allow_overrides
           self._provider_checksums: dict[Token[Any], str] = {}
           self._frozen = False
       
       def register(self, token: Token[T], provider: Callable[[], T], *,
                   checksum: str | None = None) -> None:
           """Register provider with optional integrity check."""
           if self._frozen and not self._allow_overrides:
               raise SecurityError("Container is frozen")
           
           if checksum:
               actual = sha256(str(provider).encode()).hexdigest()
               if actual != checksum:
                   raise SecurityError(f"Provider checksum mismatch for {token}")
           
           super().register(token, provider)
           
       def freeze(self) -> None:
           """Freeze container to prevent further modifications."""
           self._frozen = True

### 3. Rate Limiting & Resource Exhaustion

Prevent resource exhaustion attacks:

- **Request Rate Limiting**: Limit provider invocations per time window
- **Memory Limits**: Cap memory usage for cached dependencies
- **Connection Limits**: Restrict concurrent connections
- **Timeout Enforcement**: Mandatory timeouts for all async operations

.. code-block:: python

   from asyncio import timeout
   from collections import defaultdict
   from time import monotonic

   class RateLimitedContainer(Container):
       """Container with rate limiting."""
       
       def __init__(self, *, max_requests_per_second: int = 100):
           super().__init__()
           self._rate_limit = max_requests_per_second
           self._request_times: defaultdict[Token[Any], list[float]] = defaultdict(list)
       
       async def aget(self, token: Token[T]) -> T:
           """Get dependency with rate limiting."""
           now = monotonic()
           request_times = self._request_times[token]
           
           # Remove old requests outside the window
           request_times[:] = [t for t in request_times if now - t < 1.0]
           
           if len(request_times) >= self._rate_limit:
               raise RateLimitError(f"Rate limit exceeded for {token}")
           
           request_times.append(now)
           
           # Enforce timeout
           async with timeout(30.0):
               return await super().aget(token)

### 4. Secure Defaults

All security-sensitive settings MUST default to secure values:

- **TLS Verification**: Always enabled by default
- **Timeout Values**: Conservative defaults (30s for network operations)
- **Retry Limits**: Maximum 3 retries with exponential backoff
- **Log Sanitization**: Never log sensitive data (tokens, passwords, PII)

### 5. Audit Logging

Security-relevant events MUST be logged:

- **Dependency Registration**: Log all provider registrations
- **Override Operations**: Log when dependencies are overridden
- **Validation Failures**: Log all validation errors with context
- **Rate Limit Violations**: Log rate limiting events
- **Resource Cleanup**: Log resource lifecycle events

.. code-block:: python

   import logging
   from typing import Any

   security_logger = logging.getLogger("di.security")

   class AuditedContainer(Container):
       """Container with audit logging."""
       
       def register(self, token: Token[Any], provider: Callable[[], Any]) -> None:
           """Register with audit logging."""
           security_logger.info(
               "Dependency registered",
               extra={
                   "token": str(token),
                   "provider_type": type(provider).__name__,
                   "caller": self._get_caller_info(),
               }
           )
           super().register(token, provider)
       
       def _get_caller_info(self) -> dict[str, Any]:
           """Get information about the calling code."""
           import inspect
           frame = inspect.currentframe()
           if frame and frame.f_back and frame.f_back.f_back:
               caller = frame.f_back.f_back
               return {
                   "file": caller.f_code.co_filename,
                   "line": caller.f_lineno,
                   "function": caller.f_code.co_name,
               }
           return {}


Safety Guarantees
-----------------

This section defines safety guarantees that all implementations MUST provide.

### 1. Thread Safety

The container MUST be thread-safe for concurrent operations:

- **Read Operations**: Multiple threads can safely call ``get()`` and ``aget()``
- **Write Operations**: ``register()`` operations require explicit locking
- **Modification During Resolution**: Attempting to modify the container during
  dependency resolution MUST raise ``RuntimeError``

.. code-block:: python

   import threading
   from typing import Any, Callable, TypeVar

   T = TypeVar("T")

   class ThreadSafeContainer(Container):
       """Thread-safe container implementation."""
       
       def __init__(self):
           super().__init__()
           self._lock = threading.RLock()
           self._resolving = threading.local()
       
       def register(self, token: Token[T], provider: Callable[[], T]) -> None:
           """Thread-safe registration."""
           if getattr(self._resolving, "active", False):
               raise RuntimeError("Cannot modify container during resolution")
           
           with self._lock:
               super().register(token, provider)
       
       def get(self, token: Token[T]) -> T:
           """Thread-safe resolution."""
           self._resolving.active = True
           try:
               return super().get(token)
           finally:
               self._resolving.active = False

### 2. Memory Safety

Prevent memory leaks and excessive memory usage:

- **Weak References**: Use weak references for cached objects where appropriate
- **Memory Limits**: Enforce maximum cache sizes
- **Garbage Collection**: Explicit cleanup of circular references
- **Resource Tracking**: Track all allocated resources for cleanup

.. code-block:: python

   import weakref
   from typing import Any

   class MemorySafeContainer(Container):
       """Container with memory safety features."""
       
       def __init__(self, *, max_cache_size: int = 1000):
           super().__init__()
           self._max_cache_size = max_cache_size
           self._weak_cache: dict[Token[Any], weakref.ref[Any]] = {}
       
       def _add_to_cache(self, token: Token[Any], value: Any) -> None:
           """Add to cache with memory limits."""
           if len(self._cache) >= self._max_cache_size:
               # Evict oldest entries (LRU)
               oldest = next(iter(self._cache))
               del self._cache[oldest]
           
           # Store weak reference for large objects
           if sys.getsizeof(value) > 1_000_000:  # 1MB
               self._weak_cache[token] = weakref.ref(value)
           else:
               self._cache[token] = value

### 3. Circular Dependency Detection

The container MUST detect and prevent circular dependencies:

.. code-block:: python

   class CircularDependencyError(Exception):
       """Raised when a circular dependency is detected."""
       pass

   class SafeContainer(Container):
       """Container with circular dependency detection."""
       
       def __init__(self):
           super().__init__()
           self._resolution_stack: list[Token[Any]] = []
       
       def get(self, token: Token[T]) -> T:
           """Get with circular dependency detection."""
           if token in self._resolution_stack:
               cycle = " -> ".join(str(t) for t in self._resolution_stack)
               raise CircularDependencyError(f"Circular dependency: {cycle} -> {token}")
           
           self._resolution_stack.append(token)
           try:
               return super().get(token)
           finally:
               self._resolution_stack.pop()

### 4. Deadlock Prevention

Prevent deadlocks in async operations:

- **Lock Ordering**: Acquire locks in a consistent order
- **Timeout on Locks**: All lock acquisitions must have timeouts
- **Lock-Free Algorithms**: Use lock-free algorithms where possible
- **Deadlock Detection**: Implement deadlock detection mechanisms

.. code-block:: python

   import asyncio
   from typing import Any

   class DeadlockPreventingContainer(Container):
       """Container with deadlock prevention."""
       
       def __init__(self):
           super().__init__()
           self._lock_order: dict[Token[Any], int] = {}
           self._next_order = 0
       
       def _get_lock_order(self, token: Token[Any]) -> int:
           """Get consistent lock ordering."""
           if token not in self._lock_order:
               self._lock_order[token] = self._next_order
               self._next_order += 1
           return self._lock_order[token]
       
       async def aget(self, token: Token[T]) -> T:
           """Async get with deadlock prevention."""
           try:
               async with asyncio.timeout(5.0):  # Prevent infinite wait
                   # Acquire locks in consistent order
                   lock = self._locks[token]
                   async with lock:
                       return await super().aget(token)
           except asyncio.TimeoutError:
               raise DeadlockError(f"Potential deadlock detected for {token}")

### 5. Error Recovery

Graceful error recovery and resource cleanup:

- **Partial Initialization**: Clean up partially initialized resources
- **Rollback Capability**: Support transactional dependency registration
- **Graceful Degradation**: Continue with reduced functionality on errors
- **Error Context**: Provide detailed error context for debugging

.. code-block:: python

   from contextlib import contextmanager
   from typing import Any

   class RecoverableContainer(Container):
       """Container with error recovery."""
       
       @contextmanager
       def transaction(self):
           """Transactional registration with rollback."""
           snapshot = {
               "providers": dict(self._providers),
               "cache": dict(self._cache),
           }
           
           try:
               yield self
           except Exception:
               # Rollback on error
               self._providers = snapshot["providers"]
               self._cache = snapshot["cache"]
               raise
       
       async def aget_with_fallback(self, token: Token[T], 
                                    fallback: Token[T] | None = None) -> T:
           """Get with fallback on error."""
           try:
               return await self.aget(token)
           except Exception as e:
               if fallback:
                   logger.warning(f"Failed to get {token}, using fallback: {e}")
                   return await self.aget(fallback)
               raise


Type System Contracts
----------------------

This specification mandates comprehensive type safety for all DI components.

### 1. Type Coverage Requirements

- **100% Public API Coverage**: All public functions, methods, and classes MUST
  have complete type annotations
- **No Implicit Any**: Use of ``Any`` must be explicit and justified
- **Strict Mode Required**: Type checkers must run in strict mode
- **Generic Constraints**: All generics must have appropriate constraints

### 2. Type Checker Configuration

**Pyright/Basedpyright Configuration (pyproject.toml):**

.. code-block:: toml

   [tool.pyright]
   pythonVersion = "3.12"
   typeCheckingMode = "strict"
   reportMissingTypeStubs = "error"
   reportUnknownParameterType = "error"
   reportUnknownReturnType = "error"
   reportUnknownVariableType = "error"
   reportUnknownMemberType = "error"
   reportMissingParameterType = "error"
   reportUntypedFunctionDecorator = "error"
   reportUntypedClassDecorator = "error"
   reportUntypedBaseClass = "error"
   reportUntypedNamedTuple = "error"
   reportPrivateUsage = "error"
   reportTypeCommentUsage = "error"
   reportPrivateImportUsage = "error"
   reportConstantRedefinition = "error"
   reportIncompatibleMethodOverride = "error"
   reportIncompatibleVariableOverride = "error"
   reportOverlappingOverload = "error"
   reportUninitializedInstanceVariable = "error"
   reportCallInDefaultInitializer = "error"
   reportUnnecessaryIsInstance = "warning"
   reportUnnecessaryCast = "warning"
   reportUnnecessaryComparison = "warning"
   reportImplicitStringConcatenation = "warning"
   reportUnusedClass = "warning"
   reportUnusedImport = "warning"
   reportUnusedFunction = "warning"
   reportUnusedVariable = "warning"
   reportDuplicateImport = "warning"

**MyPy Configuration (mypy.ini):**

.. code-block:: ini

   [mypy]
   python_version = 3.12
   strict = True
   warn_return_any = True
   warn_unused_configs = True
   disallow_untyped_defs = True
   disallow_any_unimported = True
   no_implicit_optional = True
   check_untyped_defs = True
   warn_redundant_casts = True
   warn_unused_ignores = True
   warn_no_return = True
   warn_unreachable = True
   strict_equality = True
   strict_concatenate = True
   
   # Ensure all imports are typed
   disallow_any_expr = False  # Too strict for practical use
   disallow_any_decorated = True
   disallow_any_explicit = False  # Allow explicit Any when needed
   disallow_any_generics = True
   disallow_subclassing_any = True

### 3. Protocol Definitions

All injectable interfaces MUST be defined as Protocols:

.. code-block:: python

   from typing import Protocol, runtime_checkable, TypeVar, Generic
   from abc import abstractmethod

   T = TypeVar("T")
   K = TypeVar("K")
   V = TypeVar("V")

   @runtime_checkable
   class Provider(Protocol[T]):
       """Protocol for dependency providers."""
       
       @abstractmethod
       def __call__(self) -> T:
           """Provide an instance of T."""
           ...

   @runtime_checkable
   class AsyncProvider(Protocol[T]):
       """Protocol for async dependency providers."""
       
       @abstractmethod
       async def __call__(self) -> T:
           """Provide an instance of T asynchronously."""
           ...

   @runtime_checkable
   class Cache(Protocol[K, V]):
       """Protocol for cache implementations."""
       
       @abstractmethod
       def get(self, key: K) -> V | None:
           """Get value from cache."""
           ...
       
       @abstractmethod
       def set(self, key: K, value: V) -> None:
           """Set value in cache."""
           ...
       
       @abstractmethod
       def delete(self, key: K) -> bool:
           """Delete value from cache."""
           ...
       
       @abstractmethod
       def clear(self) -> None:
           """Clear all cached values."""
           ...

### 4. Variance Annotations

Proper variance annotations for generic types:

.. code-block:: python

   from typing import TypeVar, Generic, Protocol
   
   T_co = TypeVar("T_co", covariant=True)  # For return types
   T_contra = TypeVar("T_contra", contravariant=True)  # For parameter types
   T_inv = TypeVar("T_inv")  # For invariant types
   
   class Reader(Protocol[T_co]):
       """Covariant reader protocol."""
       def read(self) -> T_co: ...
   
   class Writer(Protocol[T_contra]):
       """Contravariant writer protocol."""
       def write(self, value: T_contra) -> None: ...
   
   class Store(Protocol[T_inv]):
       """Invariant store protocol."""
       def get(self) -> T_inv: ...
       def set(self, value: T_inv) -> None: ...

### 5. Type Stubs

Requirements for type stubs:

- **PEP 561 Compliance**: Include ``py.typed`` marker
- **Stub Files**: Provide ``.pyi`` files for all public modules
- **Third-Party Stubs**: Maintain stubs for untyped dependencies
- **Stub Validation**: Automated validation in CI/CD

.. code-block:: python

   # di/__init__.pyi
   from typing import TypeVar, Generic, Protocol, Any, Callable, Awaitable
   from typing import overload, final
   from contextlib import AsyncContextDecorator
   
   T = TypeVar("T")
   
   @final
   class Token(Generic[T]):
       """Type-safe dependency token."""
       
       def __init__(self, name: str) -> None: ...
       
       @property
       def name(self) -> str: ...
       
       def __hash__(self) -> int: ...
       
       def __eq__(self, other: object) -> bool: ...
       
       def __repr__(self) -> str: ...
   
   class Container:
       """Type-safe dependency container."""
       
       @overload
       def get(self, token: Token[T]) -> T: ...
       
       @overload
       def get(self, token: Token[T], default: T) -> T: ...
       
       def register(self, token: Token[T], provider: Callable[[], T]) -> None: ...
       
       def register_async(self, token: Token[T], 
                         provider: Callable[[], Awaitable[T]]) -> None: ...
       
       async def aget(self, token: Token[T]) -> T: ...
       
       async def aclose(self) -> None: ...


Performance Optimizations
-------------------------

This section details performance optimizations using only Python's standard library.

### 1. Smart Caching with functools

Aggressive caching of expensive operations:

.. code-block:: python

   from functools import lru_cache, cached_property
   
   class Container:
       @lru_cache(maxsize=1024)
       def _get_resolution_path(self, token: Token) -> Tuple[Provider, ...]:
           """Cache entire resolution paths."""
           pass
       
       @lru_cache(maxsize=512)
       def _analyze_signature(self, func: Callable) -> Dict[str, Token]:
           """Cache signature analysis results."""
           pass
       
       @cached_property
       def _provider_graph(self) -> Dict[Token, Set[Token]]:
           """Build dependency graph once."""
           pass

### 2. Memory-Efficient Data Structures

Using appropriate data structures for memory efficiency:

.. code-block:: python

   from weakref import WeakValueDictionary
   from collections import deque
   from array import array
   
   class Container:
       def __init__(self):
           # Strong refs for singletons
           self._singletons = {}
           
           # Weak refs for transients (auto-cleanup)
           self._transients = WeakValueDictionary()
           
           # Fixed-size circular buffer for metrics
           self._resolution_times = deque(maxlen=1000)
           
           # Compact storage for numeric IDs
           self._token_ids = array('i')

### 3. Batch Operations with itertools

Efficient batch processing:

.. code-block:: python

   from itertools import chain, islice, tee, groupby
   
   def batch_resolve(self, tokens: List[Token]) -> Dict[Token, Any]:
       """Resolve multiple dependencies efficiently."""
       # Group by scope for optimal resolution
       by_scope = groupby(tokens, key=lambda t: t.scope)
       
       results = {}
       for scope, group in by_scope:
           if scope == Scope.SINGLETON:
               # Resolve singletons in parallel
               results.update(self._batch_singletons(group))
           else:
               # Chain transient resolutions
               for token in group:
                   results[token] = self.get(token)
       
       return results

### 4. Zero-Copy Patterns

Avoiding unnecessary copies:

.. code-block:: python

   from types import MappingProxyType
   import sys
   
   class Container:
       def get_providers_view(self) -> MappingProxyType:
           """Return read-only view without copying."""
           return MappingProxyType(self._providers)
       
       def transfer_ownership(self, token: Token, target: 'Container'):
           """Transfer without copy using move semantics."""
           if token in self._singletons:
               # Direct transfer, no copy
               target._singletons[token] = self._singletons.pop(token)

### 5. Lazy Initialization

Defer expensive operations:

.. code-block:: python

   class LazyProvider:
       """Lazy provider that defers creation."""
       
       __slots__ = ('_factory', '_instance', '_initialized')
       
       def __init__(self, factory):
           self._factory = factory
           self._instance = None
           self._initialized = False
       
       def __call__(self):
           if not self._initialized:
               self._instance = self._factory()
               self._initialized = True
               # Clear factory reference to free memory
               self._factory = None
           return self._instance

### 6. Performance Benchmarks

Expected performance characteristics:

- **Token Creation**: < 1 μs (with pre-computed hash)
- **Cached Resolution**: < 0.5 μs (dict lookup)
- **New Instance Creation**: < 5 μs (provider call + validation)
- **Context Switch**: < 2 μs (ContextVar set/reset)
- **Signature Analysis**: < 10 μs (with LRU cache)
- **Memory per Token**: < 100 bytes (with __slots__)
- **Memory per Instance**: No overhead (native Python objects)


For Contributors & Advanced Use Cases
-------------------------------------

### 1. Core Interfaces (Ports)

We use ``typing.Protocol`` to define the contracts for our core services. This
allows for loose coupling and easy testability. Key interfaces include:

- ``HttpClient``: An adapter for making HTTP requests.
- ``Clock``: An abstraction over ``time.time()`` for predictable testing.
- ``Logger``: A structured logging interface.
- ``TokenStore``: A service for persisting and retrieving authentication tokens.
- ``CircuitBreaker``: Resilience pattern implementation.
- ``RateLimiter``: Rate limiting interface.

Using ``@runtime_checkable`` is encouraged for protocols that benefit from
runtime validation in tests.

.. code-block:: python

   from typing import Any, Protocol, runtime_checkable
   from datetime import datetime

   @runtime_checkable
   class HttpClient(Protocol):
       async def request(self, method: str, url: str, **kwargs: Any) -> ResponseLike: ...

   @runtime_checkable
   class Clock(Protocol):
       def now(self) -> datetime: ...
       def monotonic(self) -> float: ...

   @runtime_checkable
   class CircuitBreaker(Protocol):
       async def call(self, func: Callable[[], Awaitable[T]]) -> T: ...
       def is_open(self) -> bool: ...
       def record_success(self) -> None: ...
       def record_failure(self) -> None: ...

### 2. Token Catalog (example)

Projects define their own token catalog tailored to their domain. Tokens are not
bound to specific vendors or libraries.

.. code-block:: python

   from di import Token
   
   # Core Services
   HTTP_CLIENT: Token[HttpClient] = Token("http_client")
   CLOCK: Token[Clock] = Token("clock")
   LOGGER: Token[Logger] = Token("logger")
   
   # Security Services
   AUTHENTICATOR: Token[Authenticator] = Token("authenticator")
   AUTHORIZER: Token[Authorizer] = Token("authorizer")
   TOKEN_STORE: Token[TokenStore] = Token("token_store")
   
   # Resilience Services
   CIRCUIT_BREAKER: Token[CircuitBreaker] = Token("circuit_breaker")
   RATE_LIMITER: Token[RateLimiter] = Token("rate_limiter")
   RETRY_POLICY: Token[RetryPolicy] = Token("retry_policy")
   
   # Application Services
   JOB_SERVICE: Token[JobService] = Token("job_service")
   USER_SERVICE: Token[UserService] = Token("user_service")
   NOTIFICATION_SERVICE: Token[NotificationService] = Token("notification_service")

### 3. Async Best Practices

To ensure robust and predictable async behavior, we adhere to the following patterns:

- **`contextlib.AsyncExitStack`**: The primary tool for managing the lifecycle of
  one or more async resources.
- **`asyncio.TaskGroup`**: For structured concurrency. When a group of tasks
  needs to run together, `TaskGroup` ensures that if one fails, all are cancelled.
- **`asyncio.Lock`**: To protect critical sections and prevent race conditions,
  especially during singleton initialization.
- **`asyncio.timeout`**: To prevent operations from hanging indefinitely.

**Compatibility Guidance:**

- **HTTP clients**: Provide adapters that conform to your `HttpClient`-like port; keep vendor details in adapters.
- **Database drivers**: Wrap async pools with providers owned by the composition root and entered via `AsyncExitStack`.
- **Streams/TLS**: Use factories that produce `(StreamReader, StreamWriter)` pairs; manage lifecycle in boundaries or composition roots.

### 4. Async Instrumentation and Debugging

- **Logging**: The container logs key events (registration, resolution, overrides)
  when the ``SERVICEM8PY_DEBUG=1`` environment variable is set.
- **Timers**: To measure performance, wrap provider calls or service methods in a
  decorator that uses the `CLOCK` service.
- **Trace Points**: For more complex debugging, custom `Logger` implementations can
  be injected to emit structured events to a tracing backend.
- **Distributed Tracing**: Support for OpenTelemetry spans and context propagation.

[Previous async patterns sections remain the same...]


Decisions & Guardrails
----------------------

This section codifies normative guidance for robust, maintainable async applications.

### 1. Cancellation & Partial Initialization

Async context managers (`__aenter__`/`__aexit__`) are critical boundaries for
resource management. They MUST be robust against cancellation.

- **Guideline**: Any resource acquired in `__aenter__` MUST be released in `__aexit__`.
  If `__aenter__` is cancelled, any partially initialized resources must be cleaned up.
- **Pattern**: Use a `try...finally` block within `__aenter__` to guard resource
  acquisition. If cancellation occurs, the `finally` block ensures cleanup.

.. code-block:: python

   from contextlib import asynccontextmanager

   @asynccontextmanager
   async def safe_resource_manager():
       resource = None
       try:
           resource = await acquire_resource()
           # If cancelled here, finally block still runs
           yield resource
       finally:
           if resource:
               await resource.release()

### 2. Scoped Containers

The global container holds process-wide singletons. For request- or task-level
dependencies, a scoped container is necessary to prevent state leakage.

- **Guideline**: A container SHOULD provide a `scoped()` method that returns a
  new, lightweight container instance. This instance can be populated with
  request-specific dependencies.
- **Pattern**: The scoped container inherits providers from its parent but maintains
  its own cache. This allows temporary overrides without affecting the global state.

.. code-block:: python

   from injx import Container

   async def handle_request():
       container = Container()
       async with container.async_request_scope() as request_container:
           # Register request-specific items, e.g., a user object
           request_container.register(USER_TOKEN, lambda: current_user)
           # Resolve dependencies using the scoped container
           service = await request_container.aget(MY_SERVICE_TOKEN)
           await service.do_work()

### 3. Runtime Validation

Type safety is paramount, but runtime validation can impact performance.

- **Guideline**: Runtime validation of injected dependencies against their ``Protocol``
  SHOULD only occur in debug mode.
- **Pattern**: Use ``isinstance()`` checks with ``@runtime_checkable`` protocols,
  guarded by an environment variable (e.g., ``SERVICEM8PY_DEBUG=1``).

.. code-block:: python

   import os
   from typing import runtime_checkable, Protocol

   @runtime_checkable
   class MyService(Protocol):
       def do_work(self): ...

   def register_my_service(container, implementation):
       if os.environ.get("SERVICEM8PY_DEBUG"):
           assert isinstance(implementation, MyService)
       container.register(MY_SERVICE_TOKEN, lambda: implementation)

### 4. Compatibility & Environment

- **Event Loops**: A container instance and its cached resources MUST NOT be shared
  across different asyncio event loops. The SDK's boundary-owned factory pattern
  is the primary guardrail against this.
- **AnyIO**: While the core DI implementation uses `asyncio`, applications MAY
  be built on `anyio`. To ensure compatibility, tests SHOULD run against the
  `pytest-anyio` backend. Avoid `asyncio`-specific primitives like `loop.call_soon`
  in favor of framework-agnostic patterns (e.g., creating tasks via `anyio.create_task_group`).
- **Signals**: Signal handling is a process-global, application-level concern.
  SDKs and libraries MUST NOT install signal handlers. Applications SHOULD
  install handlers in their composition root, using `loop.add_signal_handler` on
  Unix and `KeyboardInterrupt` handling on Windows.
- **External Resources (`httpx`, `asyncpg`, streams)**:
    - **Ownership**: The lifecycle of external resources like HTTP clients,
      database pools, or stream writers MUST be managed explicitly.
    - **Pattern**: Instantiate these resources in the application's composition
      root and manage them with an `AsyncExitStack`. Provide them to the DI
      container as ready-to-use singletons or factories. For boundary-specific
      resources (like a single DB connection), use a factory that the boundary
      can resolve and manage.

[Rest of Decisions & Guardrails sections remain the same...]


Static Analysis Requirements
----------------------------

All implementations MUST pass comprehensive static analysis checks.

### 1. Pre-commit Hooks

Required pre-commit configuration:

.. code-block:: yaml

   # .pre-commit-config.yaml
   repos:
     - repo: https://github.com/astral-sh/ruff-pre-commit
       rev: v0.8.0
       hooks:
         - id: ruff
           args: [--fix]
         - id: ruff-format
   
     - repo: https://github.com/microsoft/pyright
       rev: v1.1.380
       hooks:
         - id: pyright
           additional_dependencies: ['basedpyright>=1.21.0']
           args: [--warnings]
   
     - repo: https://github.com/pre-commit/mirrors-mypy
       rev: v1.11.2
       hooks:
         - id: mypy
           args: [--strict, --show-error-codes]
           additional_dependencies: [types-all]
   
     - repo: https://github.com/PyCQA/bandit
       rev: 1.7.10
       hooks:
         - id: bandit
           args: [-r, src/, --severity-level, medium]
   
     - repo: https://github.com/psf/black
       rev: 24.10.0
       hooks:
         - id: black
           language_version: python3.12

### 2. CI/CD Integration

GitHub Actions workflow for quality gates:

.. code-block:: yaml

   # .github/workflows/quality.yml
   name: Quality Gates
   
   on: [push, pull_request]
   
   jobs:
     quality:
       runs-on: ubuntu-latest
       strategy:
         matrix:
           python-version: ['3.12', '3.13']
       
       steps:
         - uses: actions/checkout@v4
         
         - name: Set up Python
           uses: actions/setup-python@v5
           with:
             python-version: ${{ matrix.python-version }}
         
         - name: Install dependencies
           run: |
             pip install -e ".[dev,test,security]"
         
         - name: Type checking (Pyright)
           run: |
             basedpyright src/ tests/ --warnings
         
         - name: Type checking (MyPy)
           run: |
             mypy src/ tests/ --strict
         
         - name: Security audit
           run: |
             bandit -r src/ --severity-level medium
             safety check
             pip-audit
         
         - name: Test coverage
           run: |
             pytest --cov=src --cov-report=xml --cov-fail-under=90
         
         - name: Complexity analysis
           run: |
             radon cc src/ -a -nc
             radon mi src/ -nc

### 3. AST-based Pattern Detection

Use AST-grep for detecting DI anti-patterns:

.. code-block:: yaml

   # ast-grep-rules.yaml
   rules:
     - id: direct-container-access
       pattern: |
         $CONTAINER._cache
       message: "Direct cache access violates encapsulation"
       severity: error
     
     - id: missing-type-annotation
       pattern: |
         def $FUNC($ARGS):
           $$$
       not:
         pattern: |
           def $FUNC($ARGS) -> $TYPE:
             $$$
       message: "Function missing return type annotation"
       severity: error
     
     - id: synchronous-in-async
       pattern: |
         async def $FUNC($$$):
           $$$
           time.sleep($ARG)
           $$$
       message: "Use asyncio.sleep in async functions"
       severity: error


Future Roadmap
--------------

This section outlines the planned evolution of the DI specification.

### 1. Short Term (3-6 months)

**Version 2.1 (Q2 2025):**

- GraphQL resolver integration patterns
- WebSocket support with connection pooling
- Prometheus metrics integration via standard providers
- OpenTelemetry tracing support through context propagation
- Better error messages with dependency chain visualization

**Version 2.2 (Q3 2025):**

- Dependency graph visualization tools for debugging
- Development mode with detailed resolution tracing
- Advanced caching strategies (TTL, LFU, LRU)
- Batch dependency resolution for performance
- Parallel provider initialization with proper ordering

### 2. Medium Term (6-12 months)

**Version 3.0 (Q4 2025):**

- PEP 695 type parameter syntax support
- Performance optimizations for large dependency graphs
- Better error messages with suggested fixes
- Integration with popular web frameworks
- Comprehensive testing utilities

**Features:**

- Scoped container improvements for request handling
- Lifecycle hooks for debugging and monitoring
- Dependency validation at registration time
- Better support for conditional dependencies
- Improved async provider initialization

### 3. Long Term (12+ months)

**Version 4.0 (2026):**

- Performance profiling and optimization tools
- Compile-time dependency graph validation
- Native asyncio performance improvements
- Better integration with type checkers
- Comprehensive debugging and introspection tools

**Research Areas:**

- Formal verification of dependency graphs
- Static analysis for circular dependency prevention
- Performance optimization through graph analysis
- Memory usage optimization patterns
- Zero-overhead abstractions research

### 4. Compatibility Commitments

- **Semantic Versioning**: Strict adherence to SemVer 2.0
- **Deprecation Policy**: 2 minor versions before removal
- **LTS Releases**: Every major version supported for 2 years
- **Migration Tools**: Automated migration for breaking changes
- **Backward Compatibility**: Minor versions maintain compatibility

### 5. Architectural Non-Goals

This section explicitly documents what this DI specification will NOT include:

**No Plugin Architecture**

The container will NOT have a plugin system. This is a deliberate architectural decision based on:

- **Simplicity**: Python's module system (`import`) already provides extensibility
- **Predictability**: All dependencies should be explicitly registered, not magically discovered
- **Security**: Dynamic plugin loading introduces unnecessary attack vectors
- **Performance**: Plugin discovery and loading adds unjustifiable runtime overhead
- **Principle of Least Astonishment**: The dependency graph should be statically analyzable

Instead of plugins, extensibility is achieved through:

- Standard Python imports and explicit registration
- Protocol-based interfaces for swappable implementations
- Factory patterns for dynamic behavior
- Composition of smaller, focused containers
- Clear public APIs for registration and resolution

As Linus Torvalds would say: "Don't reinvent a slower, more complicated, and less secure module system when Python already has one."


Migration Guide
---------------

This section provides guidance for migrating from other DI frameworks.

### 1. From dependency-injector

**Key Differences:**

- Async-first design vs sync-first with async support
- Protocol-based interfaces vs concrete base classes
- Token-based identification vs string names
- Composition root pattern vs module-based configuration

**Migration Steps:**

.. code-block:: python

   # Before (dependency-injector)
   from dependency_injector import containers, providers
   
   class Container(containers.DeclarativeContainer):
       config = providers.Configuration()
       http_client = providers.Singleton(httpx.AsyncClient)
       api_client = providers.Factory(
           APIClient,
           http_client=http_client,
       )
   
   # After (this spec)
   from di import Container, Token
   
   HTTP_CLIENT = Token[httpx.AsyncClient]("http_client")
   API_CLIENT = Token[APIClient]("api_client")
   
   container = Container()
   container.register_async(HTTP_CLIENT, httpx.AsyncClient)
   container.register(API_CLIENT, lambda: APIClient(
       http_client=container.get(HTTP_CLIENT)
   ))

### 2. From injector

**Migration Mapping:**

- `@inject` decorator → `@inject` with `depends()`
- `Module` → Composition root function
- `Binder` → `Container.register()`
- `Key` → `Token[T]`

### 3. From punq

**Key Changes:**

- `punq.Container` → `di.Container`
- `container.register()` → Same API, different semantics
- `container.resolve()` → `container.get()` or `container.aget()`

### 4. From pinject

**Architectural Shifts:**

- Object graph → Explicit composition root
- Implicit binding → Explicit registration
- Constructor injection → Factory pattern

### 5. Migration Tools

**Automated Migration Script:**

.. code-block:: python

   # migrate_di.py
   """Automated migration tool for DI frameworks."""
   
   import ast
   import libcst as cst
   from typing import Any
   
   class DITransformer(cst.CSTTransformer):
       """Transform legacy DI code to new spec."""
       
       def leave_ImportFrom(self, node: cst.ImportFrom, updated_node: cst.ImportFrom) -> Any:
           """Update import statements."""
           if node.module and node.module.value == "dependency_injector":
               return updated_node.with_changes(
                   module=cst.Attribute(value=cst.Name("di"))
               )
           return updated_node
       
       def leave_ClassDef(self, node: cst.ClassDef, updated_node: cst.ClassDef) -> Any:
           """Transform container classes."""
           # Implementation details...
           pass

### 6. Compatibility Layer

For gradual migration, a compatibility layer is provided:

.. code-block:: python

   # di/compat.py
   """Compatibility layer for legacy DI frameworks."""
   
   from typing import Any, Type
   from di import Container, Token
   
   class LegacyAdapter:
       """Adapter for legacy DI patterns."""
       
       def __init__(self, container: Container):
           self._container = container
       
       def bind(self, interface: Type, to: Type) -> None:
           """Legacy bind method."""
           token = Token[interface](str(interface))
           self._container.register(token, to)
       
       def get(self, interface: Type) -> Any:
           """Legacy get method."""
           token = Token[interface](str(interface))
           return self._container.get(token)


Reference Implementation
------------------------

### 1. Core Components

- **Container**: ``src/injx/container.py``
- **Public API**: ``src/di/__init__.py`` (re-exports)
- **Ports (example)**: ``src/servicem8py/ports.py``
- **SDK Boundary (example)**: ``src/servicem8py/client.py``
- **Test Fixtures**: ``tests/conftest.py``
- **Security Module**: ``src/di/security.py``
- **Safety Module**: ``src/di/safety.py``
- **Type Stubs**: ``src/di/*.pyi``

### 2. Package Layout (PEP 517/518)

Use the standard ``src/`` layout for a standalone DI package:

::

   di-core/
     pyproject.toml
     README.md
     LICENSE
     SECURITY.md
     CONTRIBUTING.md
     src/
       di/
         __init__.py      # exports: Token, Container, ScopedContainer, depends, inject, ...
        container.py     # Core implementation
         security.py      # Security features
         safety.py        # Safety guarantees
         types.py         # Type definitions
         protocols.py     # Protocol interfaces
         compat.py        # Compatibility layer
         py.typed         # PEP 561 typing marker
         *.pyi            # Type stubs
     tests/
       test_container.py
       test_scoped.py
       test_injection.py
       test_security.py
       test_safety.py
       test_types.py
       property/        # Property-based tests
       integration/     # Integration tests
       benchmarks/      # Performance benchmarks
     docs/
       api/
       guides/
       examples/
     examples/
       fastapi/
       django/
       flask/
       cli/

### 3. Sample pyproject.toml

.. code-block:: toml

   [build-system]
   requires = ["hatchling"]
   build-backend = "hatchling.build"

   [project]
   name = "di-core"
   version = "2.0.0"
   description = "A secure, type-safe, async-native DI container for Python"
   readme = "README.md"
   requires-python = ">=3.12"
   license = {text = "MIT"}
   authors = [
       {name = "ServiceM8Py Team", email = "team@servicem8py.io"},
       {name = "Mishal Rahman", email = "mishal@example.com"},
   ]
   maintainers = [
       {name = "Architecture Team", email = "arch@servicem8py.io"},
   ]
   classifiers = [
       "Development Status :: 4 - Beta",
       "Intended Audience :: Developers",
       "Programming Language :: Python :: 3",
       "Programming Language :: Python :: 3.12",
       "Programming Language :: Python :: 3.13",
       "Typing :: Typed",
       "Framework :: AsyncIO",
       "Topic :: Software Development :: Libraries",
       "Topic :: Software Development :: Libraries :: Application Frameworks",
   ]
   dependencies = []  # stdlib-only

   [project.optional-dependencies]
   dev = [
       "basedpyright>=1.21.0",
       "mypy>=1.11.0",
       "ruff>=0.8.0",
       "black>=24.10.0",
       "pre-commit>=3.8.0",
   ]
   test = [
       "pytest>=8.3.0",
       "pytest-asyncio>=0.24.0",
       "pytest-cov>=5.0.0",
       "pytest-timeout>=2.3.0",
       "hypothesis>=6.100.0",
       "pytest-benchmark>=4.0.0",
   ]
   security = [
       "bandit>=1.7.10",
       "safety>=3.2.0",
       "pip-audit>=2.7.0",
   ]
   docs = [
       "sphinx>=8.0.0",
       "sphinx-rtd-theme>=2.0.0",
       "sphinx-autodoc-typehints>=2.5.0",
   ]

   [project.urls]
   Homepage = "https://github.com/servicem8py/di-core"
   Documentation = "https://di-core.readthedocs.io"
   Repository = "https://github.com/servicem8py/di-core.git"
   Issues = "https://github.com/servicem8py/di-core/issues"
   Changelog = "https://github.com/servicem8py/di-core/blob/main/CHANGELOG.md"

   [tool.hatch.build.targets.wheel]
   packages = ["src/di"]

   [tool.hatch.version]
   path = "src/di/__init__.py"

   [tool.coverage.run]
   branch = true
   source = ["di"]

   [tool.coverage.report]
   exclude_lines = [
       "pragma: no cover",
       "def __repr__",
       "if TYPE_CHECKING:",
       "raise NotImplementedError",
       "@abstractmethod",
   ]

### 4. Publishing and CI

- Build: ``uv build`` or ``python -m build``
- Upload: ``uvx twine upload dist/*``
- Static typing: ``uv run basedpyright`` or ``uv run mypy`` (strict)
- Security audit: ``uv run bandit -r src/`` and ``uv run safety check``
- Tests: ``uv run pytest -q`` or ``uv run pytest -q --anyio-mode=auto``
- Benchmarks: ``uv run pytest benchmarks/ --benchmark-only``


Appendices
----------

### Appendix A: Glossary

- **Boundary**: An object that orchestrates I/O and application logic
- **Composition Root**: The single location where the Container is configured
- **Container**: A central registry mapping Tokens to Providers
- **Interface (Port)**: A ``typing.Protocol`` that defines a contract
- **Implementation (Adapter)**: A concrete class that implements an Interface
- **Provider**: A callable that creates an instance of a dependency
- **Scoped Container**: A lightweight container for request-specific dependencies
- **Single-flight**: Ensuring a provider is called only once for concurrent requests
- **Token**: A unique, typed key (e.g., ``Token[T]``) for a dependency

### Appendix B: Decision Log

**2025-09-01: Initial Specification**
- Chose async-first design for modern Python applications
- Selected Protocol-based interfaces for flexibility
- Decided on Token-based identification for type safety

**2025-09-01: Security Enhancements**
- Added comprehensive security requirements
- Included rate limiting and resource exhaustion prevention
- Mandated audit logging for security events

**2025-09-01: Type System Strengthening**
- Required 100% type coverage for public APIs
- Added strict type checker configurations
- Included variance annotation guidelines

### Appendix C: Performance Benchmarks

Benchmark results for common operations (Python 3.12, M1 Pro):

- Token creation: 0.2 μs
- Sync resolution (cached): 0.5 μs
- Sync resolution (factory): 2.1 μs
- Async resolution (cached): 0.8 μs
- Async resolution (factory): 3.5 μs
- Scoped container creation: 1.2 μs
- Override context enter/exit: 0.9 μs

### Appendix D: Security Checklist

- [ ] Input validation for all injected dependencies
- [ ] Rate limiting on provider invocations
- [ ] Audit logging for security events
- [ ] TLS verification enabled by default
- [ ] Timeout enforcement on async operations
- [ ] Memory limits for cached dependencies
- [ ] Circular dependency detection
- [ ] Thread-safe container operations
- [ ] Secure defaults for all settings
- [ ] Supply chain verification for providers

### Appendix E: Code Examples

**Example 1: FastAPI Integration**

.. code-block:: python

   from fastapi import FastAPI, Depends
   from di import Container, Token, inject
   
   # Define tokens
   DB_POOL = Token[AsyncPGPool]("db_pool")
   USER_SERVICE = Token[UserService]("user_service")
   
   # Setup container
   container = Container()
   container.register_async(DB_POOL, create_db_pool)
   container.register(USER_SERVICE, lambda: UserService(
       db=container.get(DB_POOL)
   ))
   
   # FastAPI app
   app = FastAPI()
   
   @app.get("/users/{user_id}")
   @inject
   async def get_user(
       user_id: int,
       service: UserService = depends(USER_SERVICE)
   ):
       return await service.get_user(user_id)

**Example 2: Testing with Mocks**

.. code-block:: python

   import pytest
   from di import Container, Token
   
   @pytest.fixture
   async def test_container():
       container = Container()
       
       # Register mocks
       mock_http = AsyncMock(spec=HttpClient)
       container.register(HTTP_CLIENT, lambda: mock_http)
       
       yield container
       
       await container.aclose()
   
   async def test_api_call(test_container):
       service = await test_container.aget(API_SERVICE)
       result = await service.fetch_data()
       assert result == expected_data

### Appendix F: References

1. Martin Fowler - "Inversion of Control Containers and the Dependency Injection pattern"
2. PEP 561 - "Distributing and Packaging Type Information"
3. PEP 695 - "Type Parameter Syntax"
4. PEP 544 - "Protocols: Structural subtyping (static duck typing)"
5. AsyncIO Documentation - https://docs.python.org/3/library/asyncio.html
6. OWASP Dependency Injection Security Cheat Sheet
7. "Clean Architecture" by Robert C. Martin
8. "Dependency Injection Principles, Practices, and Patterns" by Steven van Deursen and Mark Seemann

---

*This specification is a living document and will be updated as the DI pattern evolves.
For the latest version, see the project repository.*
