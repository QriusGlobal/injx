"""Async Injx Example - Asynchronous Services with Type Safety

This example demonstrates:
- Async service implementations with proper type hints
- AsyncContextManager for resource cleanup
- Mixing sync and async dependencies
- Proper async/await patterns with dependency injection

Run this file directly:
    python async_example.py
"""

import asyncio
from typing import Protocol, Any, Optional, AsyncContextManager
from contextlib import asynccontextmanager
from injx import Container, Token, inject, Scope, Dependencies


# 1. Define async service protocols with type annotations
class AsyncDatabase(Protocol):
    """Async database protocol."""

    async def get_user(self, user_id: int) -> dict[str, Any]:
        """Fetch user asynchronously."""
        ...

    async def save_user(self, user: dict[str, Any]) -> None:
        """Save user asynchronously."""
        ...

    async def close(self) -> None:
        """Close database connection."""
        ...


class AsyncHTTPClient(Protocol):
    """Async HTTP client protocol."""

    async def get(self, url: str) -> dict[str, Any]:
        """Async GET request."""
        ...

    async def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        """Async POST request."""
        ...

    async def close(self) -> None:
        """Close HTTP session."""
        ...


class AsyncCache(Protocol):
    """Async cache protocol."""

    async def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get from cache asynchronously."""
        ...

    async def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        """Set in cache asynchronously."""
        ...


class MessageQueue(Protocol):
    """Async message queue protocol."""

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        """Publish message to queue."""
        ...

    async def consume(self, topic: str) -> AsyncContextManager[dict[str, Any]]:
        """Consume messages from queue."""
        ...


# 2. Implement async services with proper lifecycle management
class AsyncPostgresDatabase:
    """Async PostgreSQL implementation using asyncpg patterns."""

    def __init__(self) -> None:
        self.pool: Optional[Any] = None  # In production: asyncpg.Pool
        self.connected: bool = False

    async def initialize(self) -> None:
        """Initialize database connection pool."""
        print("📦 Creating async database connection pool...")
        await asyncio.sleep(0.1)  # Simulate connection time
        self.connected = True
        print("  └─ Database pool ready")

    async def get_user(self, user_id: int) -> dict[str, Any]:
        """Fetch user from database asynchronously."""
        print(f"  └─ Async DB: Fetching user {user_id}")
        await asyncio.sleep(0.05)  # Simulate query time
        return {
            "id": user_id,
            "name": f"AsyncUser_{user_id}",
            "email": f"async_user{user_id}@example.com",
            "status": "active"
        }

    async def save_user(self, user: dict[str, Any]) -> None:
        """Save user to database asynchronously."""
        print(f"  └─ Async DB: Saving user {user['id']}")
        await asyncio.sleep(0.05)  # Simulate write time

    async def close(self) -> None:
        """Close database connection pool."""
        if self.connected:
            print("  └─ Closing database pool...")
            await asyncio.sleep(0.05)
            self.connected = False


class AsyncAPIClient:
    """Async HTTP client using httpx/aiohttp patterns."""

    def __init__(self) -> None:
        self.session: Optional[Any] = None  # In production: httpx.AsyncClient
        self.active: bool = False

    async def initialize(self) -> None:
        """Initialize HTTP session."""
        print("🌐 Creating async HTTP session...")
        await asyncio.sleep(0.05)
        self.active = True
        print("  └─ HTTP session ready")

    async def get(self, url: str) -> dict[str, Any]:
        """Execute async GET request."""
        print(f"  └─ Async HTTP: GET {url}")
        await asyncio.sleep(0.1)  # Simulate network latency
        return {
            "status": "success",
            "data": {"metrics": {"latency": 42, "throughput": 1000}}
        }

    async def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        """Execute async POST request."""
        print(f"  └─ Async HTTP: POST {url}")
        await asyncio.sleep(0.15)  # Simulate network latency
        return {"status": "created", "id": 456, "async": True}

    async def close(self) -> None:
        """Close HTTP session."""
        if self.active:
            print("  └─ Closing HTTP session...")
            await asyncio.sleep(0.05)
            self.active = False


class AsyncRedisCache:
    """Async Redis cache implementation."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self.connected: bool = False

    async def initialize(self) -> None:
        """Connect to Redis."""
        print("⚡ Connecting to async Redis...")
        await asyncio.sleep(0.05)
        self.connected = True
        print("  └─ Redis ready")

    async def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get value from cache asynchronously."""
        await asyncio.sleep(0.01)  # Simulate Redis latency
        return self._cache.get(key)

    async def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        """Set value in cache asynchronously."""
        await asyncio.sleep(0.01)  # Simulate Redis latency
        self._cache[key] = value
        print(f"  └─ Cached: {key} (TTL: {ttl}s)")


class AsyncMessageQueue:
    """Async message queue implementation."""

    def __init__(self) -> None:
        self.connected: bool = False

    async def initialize(self) -> None:
        """Connect to message queue."""
        print("📬 Connecting to message queue...")
        await asyncio.sleep(0.05)
        self.connected = True
        print("  └─ Message queue ready")

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        """Publish message asynchronously."""
        print(f"  └─ Publishing to {topic}: {message.get('type', 'unknown')}")
        await asyncio.sleep(0.02)

    @asynccontextmanager
    async def consume(self, topic: str) -> AsyncContextManager[dict[str, Any]]:
        """Consume messages with context manager."""
        print(f"  └─ Consuming from {topic}")
        await asyncio.sleep(0.01)
        message = {"type": "test", "data": {"value": 123}}
        try:
            yield message
            print(f"  └─ Message processed successfully")
        except Exception as e:
            print(f"  └─ Message processing failed: {e}")
            raise


# 3. Factory functions with async initialization
async def create_async_database() -> AsyncDatabase:
    """Factory function for async database with initialization."""
    db = AsyncPostgresDatabase()
    await db.initialize()
    return db


async def create_async_http_client() -> AsyncHTTPClient:
    """Factory function for async HTTP client."""
    client = AsyncAPIClient()
    await client.initialize()
    return client


async def create_async_cache() -> AsyncCache:
    """Factory function for async cache."""
    cache = AsyncRedisCache()
    await cache.initialize()
    return cache


async def create_message_queue() -> MessageQueue:
    """Factory function for message queue."""
    queue = AsyncMessageQueue()
    await queue.initialize()
    return queue


# 4. Define typed tokens
ASYNC_DB: Token[AsyncDatabase] = Token("async_database", AsyncDatabase)
ASYNC_HTTP: Token[AsyncHTTPClient] = Token("async_http_client", AsyncHTTPClient)
ASYNC_CACHE: Token[AsyncCache] = Token("async_cache", AsyncCache)
MESSAGE_QUEUE: Token[MessageQueue] = Token("message_queue", MessageQueue)


# 5. Business logic with async dependency injection using Dependencies pattern
@inject
async def fetch_user_async(
    user_id: int,
    deps: Dependencies[AsyncDatabase, AsyncCache, AsyncHTTPClient]
) -> dict[str, Any]:
    """
    Fetch user with async operations.

    Type annotations ensure proper async handling with grouped dependencies.
    """
    # Extract services from dependencies
    db = deps[AsyncDatabase]
    cache = deps[AsyncCache]
    http = deps[AsyncHTTPClient]

    # Try cache first
    cache_key: str = f"async_user:{user_id}"
    cached: Optional[dict[str, Any]] = await cache.get(cache_key)

    if cached:
        print(f"✅ Async cache hit for user {user_id}")
        return cached

    # Fetch from database and external API concurrently
    print(f"🔍 Fetching user {user_id} from multiple sources...")

    # Concurrent operations with proper typing
    user_task: asyncio.Task[dict[str, Any]] = asyncio.create_task(
        db.get_user(user_id)
    )
    metrics_task: asyncio.Task[dict[str, Any]] = asyncio.create_task(
        http.get(f"https://api.example.com/metrics/{user_id}")
    )

    # Await both operations
    user_data, metrics_data = await asyncio.gather(user_task, metrics_task)

    # Combine results
    user_data["metrics"] = metrics_data["data"]["metrics"]

    # Cache the result
    await cache.set(cache_key, user_data, ttl=600)

    return user_data


@inject
async def process_user_event(
    event_type: str,
    user_id: int,
    deps: Dependencies[AsyncDatabase, MessageQueue, AsyncHTTPClient]
) -> None:
    """
    Process user events with message queue.

    Demonstrates async context managers and error handling with Dependencies pattern.
    """
    # Extract services from dependencies
    db = deps[AsyncDatabase]
    queue = deps[MessageQueue]
    http = deps[AsyncHTTPClient]

    print(f"\n📤 Processing {event_type} event for user {user_id}")

    # Fetch user
    user: dict[str, Any] = await db.get_user(user_id)

    # Create event message
    message: dict[str, Any] = {
        "type": event_type,
        "user_id": user_id,
        "user_name": user["name"],
        "timestamp": "2024-01-01T00:00:00Z"
    }

    # Publish to queue
    await queue.publish("user_events", message)

    # Notify external service
    await http.post(
        "https://api.example.com/events",
        {"event": event_type, "user": user_id}
    )


# 6. Container setup with async services
async def setup_async_container() -> Container:
    """Setup container with async services."""
    container = Container()

    # Register async factories
    container.register(ASYNC_DB, create_async_database, scope=Scope.SINGLETON)
    container.register(ASYNC_HTTP, create_async_http_client, scope=Scope.SINGLETON)
    container.register(ASYNC_CACHE, create_async_cache, scope=Scope.SINGLETON)
    container.register(MESSAGE_QUEUE, create_message_queue, scope=Scope.SINGLETON)

    return container


# 7. Main async function with proper cleanup
async def main() -> None:
    """Main async function demonstrating complete async DI."""
    print("🚀 Starting Async Application\n")
    print("=" * 50)

    # Setup container
    container: Container = await setup_async_container()
    Container.set_active(container)

    print("\n" + "=" * 50)
    print("All async services initialized")
    print("=" * 50)

    try:
        # Example 1: Fetch user with concurrent operations
        print("\n📊 Example 1: Fetching user with concurrent async operations")
        print("-" * 40)
        user1: dict[str, Any] = await fetch_user_async(100)
        print(f"Result: {user1}")

        # Example 2: Same user (cache hit)
        print("\n📊 Example 2: Fetching same user (async cache hit)")
        print("-" * 40)
        user2: dict[str, Any] = await fetch_user_async(100)
        print(f"Result: {user2}")

        # Example 3: Process event
        print("\n📊 Example 3: Processing user event with message queue")
        print("-" * 40)
        await process_user_event("login", 100)

        # Example 4: Concurrent event processing
        print("\n📊 Example 4: Processing multiple events concurrently")
        print("-" * 40)
        events: list[asyncio.Task[None]] = [
            asyncio.create_task(process_user_event("view", 101)),
            asyncio.create_task(process_user_event("click", 102)),
            asyncio.create_task(process_user_event("purchase", 103))
        ]
        await asyncio.gather(*events)

    finally:
        # Cleanup async resources
        print("\n" + "=" * 50)
        print("🧹 Cleaning up async resources...")

        # Get services for cleanup
        db: AsyncDatabase = await container.aget(ASYNC_DB)
        http: AsyncHTTPClient = await container.aget(ASYNC_HTTP)

        # Clean up in parallel
        await asyncio.gather(
            db.close(),
            http.close()
        )

        print("✅ Async application completed successfully")
        print("=" * 50)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())