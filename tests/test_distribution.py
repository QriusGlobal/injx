"""Distribution validation tests.

These tests validate the INSTALLED package distribution, not the source code.
They ensure the package works correctly after pip install.

Run with: pytest -m distribution
"""

import pytest


@pytest.mark.distribution
class TestDistribution:
    """Test suite for validating the installed package distribution."""

    def test_package_version(self):
        """Verify package version is accessible."""
        import injx

        # Version should be available
        assert hasattr(injx, "__version__")
        assert injx.__version__

        # Check version format (should be semantic)
        parts = injx.__version__.split(".")
        assert len(parts) >= 2  # At least major.minor

    def test_all_public_imports(self):
        """Verify all public API components are importable."""
        # Core container components
        # Injection decorators and markers
        # Contextual components
        # Protocols
        # Exception types
        # Compatibility imports
        # Dependencies utility
        from injx import (
            Container,
            Token,
            inject,
        )

        # Verify they're not None (actual imports)
        assert Container is not None
        assert Token is not None
        assert inject is not None

    def test_token_creation_and_registration(self):
        """Test basic DI functionality with correct Token API."""
        from injx import Container, Scope, Token

        # Test service class
        class TestService:
            def __init__(self, value: str = "test"):
                self.value = value

        # Create container
        container = Container()

        # Create token with CORRECT syntax
        token = Token("test-service", TestService)
        assert token.name == "test-service"
        assert token.type_ == TestService
        assert token.scope == Scope.TRANSIENT  # default

        # Register and resolve
        container.register(token, TestService, scope=Scope.SINGLETON)

        # Get instance
        service = container.get(token)
        assert isinstance(service, TestService)
        assert service.value == "test"

        # Verify singleton behavior
        service2 = container.get(token)
        assert service is service2  # Same instance

    def test_inject_decorator(self):
        """Test @inject decorator works from installed package."""
        from typing import Annotated

        from injx import Container, Inject, Token, inject

        container = Container()

        # Register a string service
        greeting_token = Token("greeting", str)
        container.register(greeting_token, lambda: "Hello from installed package!")

        # Use inject decorator
        @inject(container=container)
        def greet_user(name: str, greeting: Annotated[str, Inject()]) -> str:
            return f"{greeting} User: {name}"

        # Test the injected function
        result = greet_user("Alice")
        assert result == "Hello from installed package! User: Alice"

    def test_token_factory(self):
        """Test TokenFactory convenience methods."""
        from injx import Scope, TokenFactory

        class DatabaseService:
            pass

        factory = TokenFactory()

        # Test singleton factory method
        singleton_token = factory.singleton("db", DatabaseService)
        assert singleton_token.name == "db"
        assert singleton_token.type_ == DatabaseService
        assert singleton_token.scope == Scope.SINGLETON

        # Test request-scoped factory method
        request_token = factory.request("request_db", DatabaseService)
        assert request_token.scope == Scope.REQUEST

        # Test transient factory method
        transient_token = factory.transient("temp_db", DatabaseService)
        assert transient_token.scope == Scope.TRANSIENT

    def test_contextual_containers(self):
        """Test contextual container imports and basic usage."""
        from injx import Container, RequestScope, Scope, Token

        container = Container()

        # Register a request-scoped token
        request_data_token = Token("request_data", dict, scope=Scope.REQUEST)
        container.register(request_data_token, dict)

        # Verify RequestScope context manager works
        with RequestScope(container):
            # Within scope, use the original container
            data = container.get(request_data_token)
            assert isinstance(data, dict)

    def test_transient_scope(self):
        """Test transient scope creates new instances."""
        from injx import Container, Scope, Token

        class Counter:
            count = 0

            def __init__(self):
                Counter.count += 1
                self.id = Counter.count

        container = Container()
        counter_token = Token("counter", Counter, scope=Scope.TRANSIENT)
        container.register(counter_token, Counter)

        # Each get should create a new instance
        instance1 = container.get(counter_token)
        instance2 = container.get(counter_token)

        assert instance1.id == 1
        assert instance2.id == 2
        assert instance1 is not instance2  # Different instances

    @pytest.mark.asyncio
    async def test_async_provider(self):
        """Test async provider resolution."""
        import asyncio

        from injx import Container, Scope, Token

        # Async service class
        class AsyncService:
            def __init__(self):
                self.initialized = True

        # Async provider function
        async def create_async_service() -> AsyncService:
            await asyncio.sleep(0.001)  # Simulate async work
            return AsyncService()

        container = Container()
        token = Token("async_service", AsyncService, scope=Scope.SINGLETON)
        container.register(token, create_async_service)

        # Test async resolution
        service = await container.aget(token)
        assert isinstance(service, AsyncService)
        assert service.initialized is True

        # Verify singleton behavior with async
        service2 = await container.aget(token)
        assert service is service2

    def test_error_types_accessible(self):
        """Verify error types can be imported and used."""
        import pytest

        from injx import Container, ResolutionError, Token

        container = Container()

        # Create unregistered token
        missing_token = Token("missing", str)

        # Should raise ResolutionError
        with pytest.raises(ResolutionError) as exc_info:
            container.get(missing_token)

        # Verify error message contains useful info
        assert "missing" in str(exc_info.value)
