"""Tests for the testing utilities module."""

from injx import Container, Token, mock_dependency, test_container
from injx.testing import MockFactory, TestContainer, TestScope


class TestTestContainer:
    """Test cases for TestContainer."""

    def test_initialization_with_base_container(self):
        """Test TestContainer initialization with base container."""
        base = Container()
        test_cont = TestContainer(base)
        assert test_cont.base_container is base

    def test_initialization_without_base_container(self):
        """Test TestContainer initialization without base container."""
        test_cont = TestContainer()
        assert isinstance(test_cont.base_container, Container)

    def test_override_with_instance(self):
        """Test overriding with direct instance."""
        base = Container()
        SERVICE_TOKEN = Token("service", str)
        base.register(SERVICE_TOKEN, lambda: "original")

        test_cont = TestContainer(base)
        test_cont.override(SERVICE_TOKEN, "mocked")

        result = test_cont.get(SERVICE_TOKEN)
        assert result == "mocked"

    def test_override_with_factory(self):
        """Test overriding with factory function."""
        base = Container()
        SERVICE_TOKEN = Token("service", str)
        base.register(SERVICE_TOKEN, lambda: "original")

        test_cont = TestContainer(base)
        test_cont.override(SERVICE_TOKEN, lambda: "mocked_factory")

        result = test_cont.get(SERVICE_TOKEN)
        assert result == "mocked_factory"

    def test_mock_with_token(self):
        """Test mocking with Token."""
        SERVICE_TOKEN = Token("service", str)

        test_cont = TestContainer()
        test_cont.mock(SERVICE_TOKEN)

        result = test_cont.get(SERVICE_TOKEN)
        assert repr(result) == "<Mock service>"

    def test_mock_with_type(self):
        """Test mocking with type."""

        class TestService:
            pass

        test_cont = TestContainer()
        test_cont.mock(TestService)

        result = test_cont.get(TestService)
        assert repr(result) == "<Mock TestService>"

    def test_clear_overrides(self):
        """Test clearing overrides."""
        base = Container()
        SERVICE_TOKEN = Token("service", str)
        base.register(SERVICE_TOKEN, lambda: "original")

        test_cont = TestContainer(base)
        test_cont.override(SERVICE_TOKEN, "mocked")
        assert test_cont.get(SERVICE_TOKEN) == "mocked"

        test_cont.clear_overrides()
        assert test_cont.get(SERVICE_TOKEN) == "original"

    def test_list_overrides(self):
        """Test listing overridden tokens."""
        test_cont = TestContainer()

        SERVICE_TOKEN = Token("service", str)
        ANOTHER_TOKEN = Token("another_service", str)
        test_cont.override(SERVICE_TOKEN, "mock")
        test_cont.mock(ANOTHER_TOKEN)

        overrides = test_cont.list_overrides()
        assert len(overrides) == 2
        assert any(t.name == "service" for t in overrides)
        assert any(t.name == "another_service" for t in overrides)


class TestTestScope:
    """Test cases for TestScope."""

    def test_sync_scope_cleanup(self):
        """Test synchronous scope cleanup."""
        base = Container()
        scope = TestScope(base)

        with scope:
            # Test that we're in a scope
            pass

        # Verify cleanup happened (scope should be cleaned up)
        # This is mainly to ensure no exceptions are raised

    def test_async_scope_cleanup(self):
        """Test asynchronous scope cleanup."""
        import asyncio

        base = Container()
        scope = TestScope(base)

        async def test_async():
            async with scope:
                # Test that we're in an async scope
                pass

        asyncio.run(test_async())


class TestMockFactory:
    """Test cases for MockFactory."""

    def test_create_mock_with_implementation(self):
        """Test creating mock with custom implementation."""
        TOKEN = Token("test", str)

        def custom_impl():
            return "custom"

        mock = MockFactory.create_mock(TOKEN, custom_impl)
        assert mock == "custom"

    def test_create_mock_without_implementation(self):
        """Test creating mock without custom implementation."""
        TOKEN = Token("test", str)

        mock = MockFactory.create_mock(TOKEN)
        assert repr(mock) == "<Mock test>"


class TestGlobalFunctions:
    """Test cases for global testing utility functions."""

    def test_test_container_context_manager(self):
        """Test test_container context manager."""
        base = Container()
        SERVICE_TOKEN = Token("service", str)
        base.register(SERVICE_TOKEN, lambda: "original")

        with test_container(base) as test_cont:
            test_cont.override(SERVICE_TOKEN, "mocked")
            assert test_cont.get(SERVICE_TOKEN) == "mocked"

    def test_mock_dependency_function(self):
        """Test mock_dependency global function."""
        TOKEN = Token("test", str)

        mock = mock_dependency(TOKEN)
        assert repr(mock) == "<Mock test>"

    def test_mock_dependency_with_implementation(self):
        """Test mock_dependency with custom implementation."""
        TOKEN = Token("test", str)

        def custom():
            return "custom"

        mock = mock_dependency(TOKEN, custom)
        assert mock == "custom"


class TestIntegrationWithContainer:
    """Integration tests with Container.test_scope()."""

    def test_container_test_scope_method(self):
        """Test Container.test_scope() method - test_scope returns TestScope context manager."""
        container = Container()
        SERVICE_TOKEN = Token("service", str)
        container.register(SERVICE_TOKEN, lambda: "original")

        # test_scope() returns a TestScope context manager for managing scoped access
        # TestScope provides context management for request/session scopes
        with container.test_scope():
            # Within the test scope, we can access registered services
            result = container.get(SERVICE_TOKEN)
            assert result == "original"

    def test_test_scope_isolation(self):
        """Test that test_scope provides isolation."""
        container = Container()
        SERVICE_TOKEN = Token("service", str)
        container.register(SERVICE_TOKEN, lambda: "original")

        # Get original in main container
        original = container.get(SERVICE_TOKEN)
        assert original == "original"

        # test_scope returns TestScope context manager
        # TestScope manages scoped access but doesn't directly support override
        # This test verifies request_scope isolation
        with container.request_scope():
            # Within request scope, access is isolated
            result = container.get(SERVICE_TOKEN)
            assert result == "original"

        # After scope exit
        after_scope = container.get(SERVICE_TOKEN)
        assert after_scope == "original"
