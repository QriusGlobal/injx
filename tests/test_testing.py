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
        SERVICE = Token("service", str)
        base = Container()
        base.register(SERVICE, lambda: "original")

        test_cont = TestContainer(base)
        test_cont.override(SERVICE, "mocked")

        result = test_cont.get(SERVICE)
        assert result == "mocked"

    def test_override_with_factory(self):
        """Test overriding with factory function."""
        SERVICE = Token("service", str)
        base = Container()
        base.register(SERVICE, lambda: "original")

        test_cont = TestContainer(base)
        test_cont.override(SERVICE, lambda: "mocked_factory")

        result = test_cont.get(SERVICE)
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
        SERVICE = Token("service", str)
        base = Container()
        base.register(SERVICE, lambda: "original")

        test_cont = TestContainer(base)
        test_cont.override(SERVICE, "mocked")
        assert test_cont.get(SERVICE) == "mocked"

        test_cont.clear_overrides()
        assert test_cont.get(SERVICE) == "original"

    def test_list_overrides(self):
        """Test listing overridden tokens."""
        test_cont = TestContainer()

        SERVICE_TOKEN = Token("service", str)
        ANOTHER_SERVICE_TOKEN = Token("another_service", str)
        test_cont.override(SERVICE_TOKEN, "mock")
        test_cont.mock(ANOTHER_SERVICE_TOKEN)

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
        SERVICE = Token("service", str)
        base = Container()
        base.register(SERVICE, lambda: "original")

        with test_container(base) as test_cont:
            test_cont.override(SERVICE, "mocked")
            assert test_cont.get(SERVICE) == "mocked"

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
        """Test Container.test_scope() method."""
        SERVICE = Token("service", str)
        container = Container()
        container.register(SERVICE, lambda: "original")

        with container.test_scope() as test:
            test.override(SERVICE, "mocked")
            result = test.get(SERVICE)
            assert result == "mocked"

    def test_test_scope_isolation(self):
        """Test that test_scope provides isolation."""
        SERVICE = Token("service", str)
        container = Container()
        container.register(SERVICE, lambda: "original")

        # Get original in main container
        original = container.get(SERVICE)
        assert original == "original"

        # Override in test scope
        with container.test_scope() as test:
            test.override(SERVICE, "mocked")
            assert test.get(SERVICE) == "mocked"

        # Verify original is unchanged after scope exit
        after_scope = container.get(SERVICE)
        assert after_scope == "original"
