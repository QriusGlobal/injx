"""Async functionality and race condition tests."""

import asyncio

import pytest

from injx import Container, ResolutionError, Scope, Token


class MockAsyncResource:
    """Mock resource that supports async cleanup."""

    def __init__(self):
        self.value = "test"
        self.closed = False

    async def aclose(self) -> None:
        """Async cleanup."""
        self.closed = True


class TestAsyncResolution:
    """Test async dependency resolution."""

    @pytest.mark.asyncio
    async def test_async_provider_resolution(self):
        """Test resolving async providers."""
        container = Container()
        token = Token("async_string", str)

        async def async_provider() -> str:
            await asyncio.sleep(0.001)  # Simulate async work
            return "async result"

        container.register(token, async_provider, Scope.TRANSIENT)

        result = await container.aget(token)
        assert result == "async result"

    @pytest.mark.asyncio
    async def test_sync_provider_in_async_context(self):
        """Test that sync providers work in async resolution."""
        container = Container()
        token = Token("sync_string", str)

        def sync_provider() -> str:
            return "sync result"

        container.register(token, sync_provider, Scope.TRANSIENT)

        result = await container.aget(token)
        assert result == "sync result"

    def test_async_provider_in_sync_context_raises_error(self):
        """Test that async providers raise error in sync context."""
        container = Container()
        token = Token("async_string", str)

        async def async_provider() -> str:
            return "async result"

        container.register(token, async_provider)

        with pytest.raises(ResolutionError) as exc_info:
            container.get(token)

        assert "Use aget() for async providers" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_singleton_creation(self):
        """Test that async singletons are created properly."""
        container = Container()
        token = Token("async_singleton", MockAsyncResource)

        creation_count = 0

        async def create_resource() -> MockAsyncResource:
            nonlocal creation_count
            creation_count += 1
            await asyncio.sleep(0.001)  # Simulate async initialization
            return MockAsyncResource()

        container.register(token, create_resource, Scope.SINGLETON)

        # Resolve multiple times
        result1 = await container.aget(token)
        result2 = await container.aget(token)

        # Should be same instance
        assert result1 is result2
        # Should only be created once
        assert creation_count == 1

    @pytest.mark.asyncio
    async def test_async_singleton_race_condition(self):
        """Test that concurrent async singleton creation doesn't cause race conditions."""
        container = Container()
        token = Token("race_test", dict[str, object])

        creation_count = 0

        async def create_resource() -> dict[str, object]:
            nonlocal creation_count
            creation_count += 1
            # Simulate longer async work to increase chance of race
            await asyncio.sleep(0.01)
            return {
                "id": creation_count,
                "created_at": asyncio.get_running_loop().time(),
            }

        container.register(token, create_resource, Scope.SINGLETON)

        # Launch many concurrent resolutions
        from collections.abc import Awaitable

        tasks: list[Awaitable[dict[str, object]]] = [
            container.aget(token) for _ in range(50)
        ]
        results: list[dict[str, object]] = await asyncio.gather(*tasks)

        # All results should be the same instance
        first_result = results[0]
        for result in results:
            assert result is first_result

        # Factory should only be called once
        assert creation_count == 1
        assert first_result["id"] == 1

    @pytest.mark.asyncio
    async def test_mixed_async_sync_dependencies(self):
        """Test resolving mixed async and sync dependencies."""
        container = Container()

        sync_token = Token("sync_dep", str)
        async_token = Token("async_dep", str)
        combined_token = Token("combined", dict[str, str])

        def sync_provider() -> str:
            return "sync_value"

        async def async_provider() -> str:
            await asyncio.sleep(0.001)
            return "async_value"

        async def combined_provider() -> dict[str, str]:
            sync_val = container.get(sync_token)
            async_val = await container.aget(async_token)
            return {"sync": sync_val, "async": async_val}

        container.register(sync_token, sync_provider)
        container.register(async_token, async_provider)
        container.register(combined_token, combined_provider)

        result: dict[str, str] = await container.aget(combined_token)

        assert result == {"sync": "sync_value", "async": "async_value"}


class TestAsyncCleanup:
    """Test async resource cleanup."""

    @pytest.mark.asyncio
    async def test_async_resource_tracking(self):
        """Test that async resources are tracked for cleanup."""
        container = Container()
        from contextlib import asynccontextmanager

        token = Token("async_resource", MockAsyncResource)

        @asynccontextmanager
        async def cm():
            r = MockAsyncResource()
            try:
                yield r
            finally:
                await r.aclose()

        container.register_context(
            token, lambda: cm(), is_async=True, scope=Scope.SINGLETON
        )

        resource: MockAsyncResource = await container.aget(token)
        assert not resource.closed

        # Dispose should close the resource
        await container.dispose()
        assert resource.closed

    @pytest.mark.asyncio
    async def test_dispose_multiple_async_resources(self):
        """Test disposing of multiple async resources."""
        container = Container()

        resources_created: list[MockAsyncResource] = []

        def create_resource() -> MockAsyncResource:
            resource = MockAsyncResource()
            resources_created.append(resource)
            return resource

        # Register multiple singleton resources
        from contextlib import asynccontextmanager

        for i in range(3):
            token = Token(f"resource_{i}", MockAsyncResource)

            @asynccontextmanager
            async def cm():
                r = create_resource()
                try:
                    yield r
                finally:
                    await r.aclose()

            container.register_context(
                token, lambda cm=cm: cm(), is_async=True, scope=Scope.SINGLETON
            )
            _ = await container.aget(token)

        # All should be open
        assert len(resources_created) == 3
        for resource in resources_created:
            assert not resource.closed

        # Dispose should close all
        await container.dispose()

        for resource in resources_created:
            assert resource.closed

    @pytest.mark.asyncio
    async def test_dispose_with_cleanup_errors(self):
        """Test that dispose handles cleanup errors gracefully."""

        class ProblematicResource:
            def __init__(self):
                self.closed = False

            async def aclose(self) -> None:
                self.closed = True
                raise RuntimeError("Cleanup error!")

        container = Container()
        from contextlib import asynccontextmanager

        token = Token("problematic", ProblematicResource)

        @asynccontextmanager
        async def cm():
            r = ProblematicResource()
            try:
                yield r
            finally:
                await r.aclose()

        container.register_context(
            token, lambda: cm(), is_async=True, scope=Scope.SINGLETON
        )
        resource: ProblematicResource = await container.aget(token)

        # Dispose should not raise even if cleanup fails
        await container.dispose()

        # Resource should still be marked as closed
        assert resource.closed

    @pytest.mark.asyncio
    async def test_dispose_clears_state(self):
        """Test that dispose clears container state."""
        container = Container()

        class Thing:
            pass

        token = Token("test", Thing)

        container.register(token, lambda: Thing(), Scope.SINGLETON)

        # Create singleton
        result1 = container.get(token)
        assert isinstance(result1, Thing)

        # Dispose
        await container.dispose()

        # Singleton should be recreated
        result2: Thing = container.get(token)
        assert isinstance(result2, Thing)
        assert result1 is not result2  # Different instance after dispose


class TestAsyncInjection:
    """Test async dependency injection."""

    @pytest.mark.asyncio
    async def test_inject_async_function(self):
        """Test injecting dependencies into async functions."""
        container = Container()

        class Service:
            def __init__(self, value: str):
                self.value = value

        service_token = Token("service", Service)
        container.register(service_token, lambda: Service("injected"))

        @container.inject
        async def async_function(service: Service) -> str:
            await asyncio.sleep(0.001)
            return f"Result: {service.value}"

        result = await async_function()
        assert result == "Result: injected"

    @pytest.mark.asyncio
    async def test_async_circular_dependency_detection(self):
        """Test circular dependency detection in async context."""
        container = Container()
        token_a = Token("async_A", str)
        token_b = Token("async_B", str)

        async def provider_a() -> str:
            return await container.aget(token_b)

        async def provider_b() -> str:
            return await container.aget(token_a)

        container.register(token_a, provider_a)
        container.register(token_b, provider_b)

        from injx.exceptions import CircularDependencyError

        with pytest.raises(CircularDependencyError):
            await container.aget(token_a)
