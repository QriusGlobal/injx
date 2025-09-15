PEP: DI-001
Title: Dependency Injection Container Specification for Python
Author: Qrius Global <info@qrius.ai>
Status: Draft
Type: Informational
Topic: Typing
Created: 01-Sep-2025
Python-Version: 3.13+

========================================================================
PEP DI-001 -- Dependency Injection Container Specification for Python
========================================================================

Abstract
========

This PEP defines a standardized dependency injection container specification for Python SDKs and applications. The specification provides type-safe dependency management using structural typing (Protocol), context-variable-based overrides for testing, and deterministic resource lifecycle management. Two implementation patterns are specified: SDK pattern with hidden tokenized DI for library authors, and application pattern with explicit constructor injection for backend services.

Rationale
=========

Current Python dependency injection lacks standardization, leading to:

* Inconsistent testing approaches requiring monkeypatching
* Poor type safety without Protocol-based contracts
* Non-deterministic resource cleanup
* Framework-specific solutions preventing interoperability
* Global state management causing concurrency issues

This specification addresses these issues by defining objective interfaces and behavioral contracts that implementations MUST satisfy.

Specification
=============

Core Components
---------------

Token Definition
~~~~~~~~~~~~~~~~

A Token MUST be a generic type with the following interface::

    @dataclass(frozen=True, slots=True)
    class Token(Generic[T]):
        name: str

The ``name`` field MUST be unique within a container instance and SHOULD provide meaningful debugging information.

Container Interface
~~~~~~~~~~~~~~~~~~~

A compliant container MUST implement the following Protocol::

    class Container(Protocol):
        def register(self, token: Token[T], provider: Provider[T]) -> None: ...
        def get(self, token: Token[T]) -> T: ...
        def use_overrides(self, mapping: Mapping[Token[Any], Any]) -> ContextManager[None]: ...
        async def aclose(self) -> None: ...
        def clear_overrides(self) -> None: ...

Provider Interface
~~~~~~~~~~~~~~~~~~

Providers MUST be callable objects that return instances::

    Provider = Callable[[], T]

Port Definition
~~~~~~~~~~~~~~~

Ports MUST be defined using ``typing.Protocol`` for structural typing::

    @runtime_checkable
    class HttpClient(Protocol):
        async def request(self, method: str, url: str, **kwargs: Any) -> ResponseLike: ...

Behavioral Requirements
-----------------------

Thread Safety
~~~~~~~~~~~~~

Container implementations MUST be thread-safe for all operations. Override mechanisms MUST use ``contextvars.ContextVar`` to ensure isolation between concurrent contexts.

Singleton Management
~~~~~~~~~~~~~~~~~~~~

Containers MUST cache resolved instances per token. Multiple calls to ``get()`` with the same token MUST return the identical instance within the same context.

Override Mechanism
~~~~~~~~~~~~~~~~~~

Override functionality MUST:

* Use ``contextvars.ContextVar`` for context isolation
* Support nested overrides with proper restoration
* Allow temporary replacement of any registered provider
* Not affect other concurrent contexts

Resource Cleanup
~~~~~~~~~~~~~~~~

Containers MUST implement ``SupportsAsyncClose`` Protocol::

    class SupportsAsyncClose(Protocol):
        async def aclose(self) -> None: ...

The ``aclose()`` method MUST:

* Close all cached instances implementing ``SupportsAsyncClose``
* Clear the singleton cache
* Suppress exceptions during cleanup to prevent cascading failures

Error Handling
~~~~~~~~~~~~~~

Containers MUST raise specific exceptions:

* ``ResolutionError`` when a token has no registered provider
* ``CircularDependencyError`` when circular dependencies are detected
* Include the token name in error messages for debugging

Implementation Patterns
=======================

SDK Pattern
-----------

For library authors, containers SHOULD be internal with token-based dependency resolution::

    # _internal/di_container.py
    HTTP_CLIENT_FACTORY: Token[Callable[[], HttpClient]] = Token("http_client_factory")
    container = Container()

    class Client:
        def __init__(self, *, http: HttpClient | None = None):
            self._http = http or container.get(HTTP_CLIENT_FACTORY)()

Test override helpers MUST reside in test code only::

    # tests/conftest.py
    @contextmanager
    def use_overrides(**kw: Any):
        mapping: dict[Any, Any] = {}
        if "http_client_factory" in kw: 
            mapping[HTTP_CLIENT_FACTORY] = kw["http_client_factory"]
        with container.use_overrides(mapping):
            yield

Application Pattern
-------------------

For applications, dependency injection SHOULD use explicit constructor injection::

    class OrderService:
        def __init__(self, payments: PaymentsPort) -> None:
            self._payments = payments

Composition roots SHOULD assemble dependencies explicitly::

    def build_app() -> App:
        http_client = HttpxAdapter(httpx.AsyncClient())
        payment_service = StripePayments(http_client)
        order_service = OrderService(payment_service)
        return App(order_service)

Conformance Testing
===================

Implementations MUST pass the following conformance tests:

Basic Operations
~~~~~~~~~~~~~~~~

::

    def test_token_creation():
        token = Token[str]("test")
        assert token.name == "test"

    def test_register_and_get():
        container = Container()
        token = Token[str]("test")
        container.register(token, lambda: "value")
        assert container.get(token) == "value"

    def test_singleton_behavior():
        container = Container()
        token = Token[object]("test")
        container.register(token, object)
        instance1 = container.get(token)
        instance2 = container.get(token)
        assert instance1 is instance2

Override Mechanism
~~~~~~~~~~~~~~~~~~

::

    def test_context_override():
        container = Container()
        token = Token[str]("test")
        container.register(token, lambda: "original")
        
        with container.use_overrides({token: "override"}):
            assert container.get(token) == "override"
        
        assert container.get(token) == "original"

    def test_nested_overrides():
        container = Container()
        token = Token[str]("test")
        container.register(token, lambda: "original")
        
        with container.use_overrides({token: "first"}):
            assert container.get(token) == "first"
            with container.use_overrides({token: "second"}):
                assert container.get(token) == "second"
            assert container.get(token) == "first"

Error Handling
~~~~~~~~~~~~~~

::

    def test_missing_provider():
        container = Container()
        token = Token[str]("missing")
        with pytest.raises(ResolutionError, match="missing"):
            container.get(token)

Resource Cleanup
~~~~~~~~~~~~~~~~

::

    async def test_resource_cleanup():
        mock_resource = AsyncMock()
        container = Container()
        token = Token[Any]("resource")
        container.register(token, lambda: mock_resource)
        
        # Trigger creation
        container.get(token)
        
        await container.aclose()
        mock_resource.aclose.assert_called_once()

Thread Safety
~~~~~~~~~~~~~

::

    def test_concurrent_access():
        container = Container()
        token = Token[object]("test")
        container.register(token, object)
        
        def get_instance():
            return container.get(token)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_instance) for _ in range(100)]
            instances = [f.result() for f in futures]
        
        # All instances must be identical
        assert all(instance is instances[0] for instance in instances)

Type Safety
~~~~~~~~~~~

::

    def test_protocol_compliance():
        @runtime_checkable
        class TestProtocol(Protocol):
            def method(self) -> str: ...
        
        class Implementation:
            def method(self) -> str:
                return "test"
        
        container = Container()
        token = Token[TestProtocol]("test")
        container.register(token, Implementation)
        
        instance = container.get(token)
        assert isinstance(instance, TestProtocol)
        assert instance.method() == "test"

Backwards Compatibility
=======================

This specification introduces new interfaces and does not affect existing code. Libraries implementing this specification SHOULD provide migration paths from existing dependency injection patterns.

Reference Implementation
========================

The ``pyinj`` package provides a reference implementation of this specification::

    from pyinj import Container, Token, Scope

    # Create container
    container = Container()

    # Define token
    DB_TOKEN = Token[Database]("database")

    # Register provider
    container.register(DB_TOKEN, create_database, Scope.SINGLETON)

    # Resolve dependency
    db = container.get(DB_TOKEN)

    # Cleanup
    await container.aclose()

The implementation MUST satisfy all behavioral requirements and pass all conformance tests specified in this document.

Security Considerations
=======================

Implementations MUST:

* Never expose internal provider implementations through public APIs
* Validate that override mappings do not leak across contexts
* Ensure resource cleanup cannot be bypassed
* Log container operations only under explicit debug flags
* Never log sensitive data from resolved instances

References
==========

* PEP 544 -- Protocols: Structural subtyping (static duck typing)
* PEP 526 -- Variable Annotations
* PEP 585 -- Type Hinting Generics In Standard Collections
* contextvars module documentation
* typing module documentation

Copyright
=========

This document is placed in the public domain.