"""Async-specific tests for Dependencies pattern."""

import asyncio
from typing import Any, Protocol

import pytest

from injx import Container, Dependencies, Scope, Token, inject
from injx.exceptions import ResolutionError


# Async service protocols
class AsyncDatabase(Protocol):
    """Async database protocol."""

    async def query(self, sql: str) -> list[dict[str, Any]]: ...
    async def execute(self, sql: str) -> None: ...
    async def close(self) -> None: ...


class AsyncCache(Protocol):
    """Async cache protocol."""

    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: Any, ttl: int = 300) -> None: ...
    async def close(self) -> None: ...


class AsyncHTTPClient(Protocol):
    """Async HTTP client protocol."""

    async def get(self, url: str) -> dict[str, Any]: ...
    async def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]: ...
    async def close(self) -> None: ...


class AsyncMessageQueue(Protocol):
    """Async message queue protocol."""

    async def publish(self, topic: str, message: dict[str, Any]) -> None: ...
    async def subscribe(self, topic: str) -> list[dict[str, Any]]: ...
    async def close(self) -> None: ...


# Async implementations
class MockAsyncDatabase:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.closed = False

    async def query(self, sql: str) -> list[dict[str, Any]]:
        await asyncio.sleep(0.01)  # Simulate I/O
        self.queries.append(sql)
        return [{"id": 1, "sql": sql}]

    async def execute(self, sql: str) -> None:
        await asyncio.sleep(0.01)
        self.queries.append(sql)

    async def close(self) -> None:
        await asyncio.sleep(0.01)
        self.closed = True


class MockAsyncCache:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self.closed = False

    async def get(self, key: str) -> Any:
        await asyncio.sleep(0.005)
        return self.store.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        await asyncio.sleep(0.005)
        self.store[key] = value

    async def close(self) -> None:
        await asyncio.sleep(0.005)
        self.closed = True


class MockAsyncHTTPClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, Any]] = []
        self.closed = False

    async def get(self, url: str) -> dict[str, Any]:
        await asyncio.sleep(0.02)  # Simulate network delay
        self.requests.append(("GET", url, None))
        return {"status": 200, "data": {"url": url}}

    async def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.02)
        self.requests.append(("POST", url, data))
        return {"status": 201, "id": 123}

    async def close(self) -> None:
        await asyncio.sleep(0.01)
        self.closed = True


class MockAsyncMessageQueue:
    def __init__(self) -> None:
        self.messages: dict[str, list[dict[str, Any]]] = {}
        self.closed = False

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        await asyncio.sleep(0.01)
        if topic not in self.messages:
            self.messages[topic] = []
        self.messages[topic].append(message)

    async def subscribe(self, topic: str) -> list[dict[str, Any]]:
        await asyncio.sleep(0.01)
        return self.messages.get(topic, [])

    async def close(self) -> None:
        await asyncio.sleep(0.01)
        self.closed = True


class TestDependenciesAsync:
    """Test Dependencies pattern with async services."""

    @pytest.mark.asyncio
    async def test_async_dependencies_basic(self):
        """Test basic async Dependencies resolution."""
        container = Container()

        # Async factory functions
        async def create_db() -> AsyncDatabase:
            await asyncio.sleep(0.01)
            return MockAsyncDatabase()

        async def create_cache() -> AsyncCache:
            await asyncio.sleep(0.01)
            return MockAsyncCache()

        # Register async services directly with types
        container.register(AsyncDatabase, create_db)
        container.register(AsyncCache, create_cache)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, AsyncCache],
        ) -> dict[str, Any]:
            db = deps[AsyncDatabase]
            cache = deps[AsyncCache]

            # Use services
            data = await db.query("SELECT * FROM users")
            await cache.set("users", data)
            cached = await cache.get("users")

            return {"data": data, "cached": cached}

        # Use async context
        async with container:
            result = await handler()
            assert result["data"][0]["sql"] == "SELECT * FROM users"
            assert result["cached"] == result["data"]

    @pytest.mark.asyncio
    async def test_async_dependencies_concurrent_operations(self):
        """Test concurrent async operations with Dependencies."""
        container = Container()

        container.register(AsyncDatabase, MockAsyncDatabase)
        container.register(AsyncCache, MockAsyncCache)
        container.register(AsyncHTTPClient, MockAsyncHTTPClient)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, AsyncCache, AsyncHTTPClient],
        ) -> dict[str, Any]:
            db = deps[AsyncDatabase]
            cache = deps[AsyncCache]
            http = deps[AsyncHTTPClient]

            # Concurrent operations
            results = await asyncio.gather(
                db.query("SELECT * FROM users"),
                cache.get("key"),
                http.get("https://api.example.com/data"),
            )

            return {
                "db_result": results[0],
                "cache_result": results[1],
                "http_result": results[2],
            }

        async with container:
            result = await handler()
            assert result["db_result"][0]["sql"] == "SELECT * FROM users"
            assert result["cache_result"] is None  # Empty cache
            assert result["http_result"]["status"] == 200

    @pytest.mark.asyncio
    async def test_async_dependencies_mixed_sync_async(self):
        """Test Dependencies with mixed sync and async services."""
        container = Container()

        # Sync service
        class SyncLogger:
            def log(self, msg: str) -> None:
                self.last_log = msg

        # Register async services
        container.register(AsyncDatabase, MockAsyncDatabase)
        container.register(AsyncCache, MockAsyncCache)
        # Register sync service
        container.register(SyncLogger, SyncLogger)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, AsyncCache, SyncLogger],
        ) -> str:
            db = deps[AsyncDatabase]
            cache = deps[AsyncCache]
            logger = deps[SyncLogger]

            # Use async services
            data = await db.query("SELECT 1")
            await cache.set("result", data)

            # Use sync service
            logger.log(f"Processed {len(data)} records")

            return logger.last_log

        async with container:
            result = await handler()
            assert result == "Processed 1 records"

    @pytest.mark.asyncio
    async def test_async_dependencies_cleanup(self):
        """Test proper cleanup of async resources with Dependencies."""
        container = Container()

        # Track cleanup
        cleanup_order = []

        class TrackableAsyncDB(MockAsyncDatabase):
            async def close(self) -> None:
                await super().close()
                cleanup_order.append("db")

        class TrackableAsyncCache(MockAsyncCache):
            async def close(self) -> None:
                await super().close()
                cleanup_order.append("cache")

        async def create_db() -> AsyncDatabase:
            return TrackableAsyncDB()

        async def create_cache() -> AsyncCache:
            return TrackableAsyncCache()

        container.register_context(AsyncDatabase, create_db, is_async=True)
        container.register_context(AsyncCache, create_cache, is_async=True)

        @inject
        async def handler(deps: Dependencies[AsyncDatabase, AsyncCache]) -> bool:
            db = deps[AsyncDatabase]
            cache = deps[AsyncCache]
            await db.query("SELECT 1")
            await cache.set("key", "value")
            return True

        async with container:
            result = await handler()
            assert result is True

        # Verify cleanup happened
        assert cleanup_order == ["cache", "db"]  # LIFO order

    @pytest.mark.asyncio
    async def test_async_dependencies_error_handling(self):
        """Test error handling in async Dependencies."""
        container = Container()

        class FailingAsyncService:
            async def process(self) -> None:
                await asyncio.sleep(0.01)
                raise ValueError("Async operation failed")

        container.register(AsyncDatabase, MockAsyncDatabase)
        container.register(FailingAsyncService, FailingAsyncService)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, FailingAsyncService],
        ) -> None:
            db = deps[AsyncDatabase]
            service = deps[FailingAsyncService]

            await db.query("SELECT 1")
            await service.process()  # This will fail

        async with container:
            with pytest.raises(ValueError, match="Async operation failed"):
                await handler()

    @pytest.mark.asyncio
    async def test_async_dependencies_with_async_context_manager(self):
        """Test Dependencies with async context manager services."""
        container = Container()

        class AsyncContextService:
            def __init__(self) -> None:
                self.entered = False
                self.exited = False

            async def __aenter__(self):
                await asyncio.sleep(0.01)
                self.entered = True
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await asyncio.sleep(0.01)
                self.exited = True

            async def process(self) -> str:
                return "processed"

        container.register(AsyncContextService, AsyncContextService)
        container.register(AsyncDatabase, MockAsyncDatabase)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, AsyncContextService],
        ) -> str:
            db = deps[AsyncDatabase]
            service = deps[AsyncContextService]

            await db.query("SELECT 1")

            async with service:
                result = await service.process()

            return result

        async with container:
            result = await handler()
            assert result == "processed"

    @pytest.mark.asyncio
    async def test_async_dependencies_performance(self):
        """Test performance of async Dependencies resolution."""
        container = Container()

        # Register multiple async services
        container.register(AsyncDatabase, MockAsyncDatabase)
        container.register(AsyncCache, MockAsyncCache)
        container.register(AsyncHTTPClient, MockAsyncHTTPClient)
        container.register(AsyncMessageQueue, MockAsyncMessageQueue)

        @inject
        async def handler(
            deps: Dependencies[
                AsyncDatabase, AsyncCache, AsyncHTTPClient, AsyncMessageQueue
            ],
        ) -> int:
            # Just access all services
            _ = deps[AsyncDatabase]
            _ = deps[AsyncCache]
            _ = deps[AsyncHTTPClient]
            _ = deps[AsyncMessageQueue]
            return 1

        async with container:
            # Time multiple calls
            import time

            start = time.perf_counter()
            tasks = [handler() for _ in range(100)]
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start

            assert len(results) == 100
            assert all(r == 1 for r in results)
            # Should complete reasonably fast (< 1 second for 100 calls)
            assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_async_dependencies_with_sync_resolution_error(self):
        """Test that async services fail properly with sync resolution."""
        container = Container()

        async def create_async_db() -> AsyncDatabase:
            await asyncio.sleep(0.01)
            return MockAsyncDatabase()

        container.register(AsyncDatabase, create_async_db)

        @inject
        def sync_handler(deps: Dependencies[AsyncDatabase]) -> None:
            # This should fail because AsyncDatabase needs async resolution
            _ = deps[AsyncDatabase]

        with container.activate():
            # This should raise a ResolutionError for async provider in sync context
            with pytest.raises(ResolutionError):
                sync_handler()

    @pytest.mark.asyncio
    async def test_async_dependencies_scoped_resolution(self):
        """Test async Dependencies with different scopes."""
        container = Container()

        call_count = {"singleton": 0, "transient": 0, "request": 0}

        async def create_singleton() -> AsyncDatabase:
            call_count["singleton"] += 1
            await asyncio.sleep(0.01)
            return MockAsyncDatabase()

        async def create_transient() -> AsyncCache:
            call_count["transient"] += 1
            await asyncio.sleep(0.01)
            return MockAsyncCache()

        async def create_request() -> AsyncHTTPClient:
            call_count["request"] += 1
            await asyncio.sleep(0.01)
            return MockAsyncHTTPClient()

        container.register(AsyncDatabase, create_singleton, scope=Scope.SINGLETON)
        container.register(AsyncCache, create_transient, scope=Scope.TRANSIENT)
        container.register(AsyncHTTPClient, create_request, scope=Scope.REQUEST)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, AsyncCache, AsyncHTTPClient],
        ) -> None:
            _ = deps[AsyncDatabase]
            _ = deps[AsyncCache]
            _ = deps[AsyncHTTPClient]

        async with container:
            # First request scope
            async with container.request_scope():
                await handler()
                await handler()

            # Second request scope
            async with container.request_scope():
                await handler()

        # Verify scope behavior
        assert call_count["singleton"] == 1  # Created once
        assert call_count["transient"] == 3  # Created for each handler call
        assert call_count["request"] == 2  # Created once per request

    @pytest.mark.asyncio
    async def test_async_dependencies_with_streaming(self):
        """Test Dependencies with async streaming operations."""
        container = Container()

        class AsyncStreamService:
            async def stream_data(self, count: int):
                """Async generator for streaming data."""
                for i in range(count):
                    await asyncio.sleep(0.01)
                    yield {"index": i, "data": f"item_{i}"}

        container.register(AsyncStreamService, AsyncStreamService)
        container.register(AsyncCache, MockAsyncCache)

        @inject
        async def handler(
            deps: Dependencies[AsyncStreamService, AsyncCache],
        ) -> list[dict[str, Any]]:
            stream_service = deps[AsyncStreamService]
            cache = deps[AsyncCache]

            results = []
            async for item in stream_service.stream_data(3):
                results.append(item)
                await cache.set(f"stream_{item['index']}", item)

            return results

        async with container:
            result = await handler()
            assert len(result) == 3
            assert result[0]["index"] == 0
            assert result[2]["data"] == "item_2"

    @pytest.mark.asyncio
    async def test_async_dependencies_cancellation(self):
        """Test proper cancellation handling with async Dependencies."""
        container = Container()

        cancelled = False

        class CancellableService:
            async def long_operation(self) -> str:
                nonlocal cancelled
                try:
                    await asyncio.sleep(10)  # Long operation
                    return "completed"
                except asyncio.CancelledError:
                    cancelled = True
                    raise

        container.register(CancellableService, CancellableService)
        container.register(AsyncDatabase, MockAsyncDatabase)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, CancellableService],
        ) -> str:
            db = deps[AsyncDatabase]
            service = deps[CancellableService]

            await db.query("SELECT 1")
            return await service.long_operation()

        async with container:
            # Create task and cancel it
            task = asyncio.create_task(handler())
            await asyncio.sleep(0.1)  # Let it start
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await task

            assert cancelled is True
