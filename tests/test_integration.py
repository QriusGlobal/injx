"""Integration tests for the complete DI system."""

import asyncio
from typing import Annotated, Awaitable, Callable, Optional, cast

import pytest

from injx.container import Container
from injx.injection import Inject, inject
from injx.tokens import Token


# Test domain classes
class DatabaseConfig:
    """Database configuration."""

    def __init__(self, host: str = "localhost", port: int = 5432):
        self.host = host
        self.port = port


class Database:
    """Database connection."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.queries_executed = 0

    def execute(self, query: str):
        self.queries_executed += 1
        return f"Result from {self.config.host}:{self.config.port}: {query}"


class CacheConfig:
    """Cache configuration."""

    def __init__(self, ttl: int = 3600):
        self.ttl = ttl


class Cache:
    """Cache service."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.data: dict[str, str] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[str]:
        if key in self.data:
            self.hits += 1
            return self.data[key]
        self.misses += 1
        return None

    def set(self, key: str, value: str):
        self.data[key] = value


class UserRepository:
    """User repository using database."""

    def __init__(self, db: Database, cache: Cache):
        self.db = db
        self.cache = cache

    def get_user(self, user_id: int):
        # Check cache first
        cache_key = f"user:{user_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Query database
        result = self.db.execute(f"SELECT * FROM users WHERE id = {user_id}")
        self.cache.set(cache_key, result)
        return result


class UserService:
    """User service with business logic."""

    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_user_info(self, user_id: int):
        return {"id": user_id, "data": self.repo.get_user(user_id)}


class TestCompleteIntegration:
    """Test complete DI system integration."""

    def test_full_dependency_graph(self):
        """Test resolving complex dependency graph."""
        container = Container()

        # Register all dependencies
        container.register_singleton(DatabaseConfig, lambda: DatabaseConfig())
        container.register_singleton(CacheConfig, lambda: CacheConfig())
        container.register_singleton(
            Database, lambda: Database(container.get(DatabaseConfig))
        )
        container.register_singleton(Cache, lambda: Cache(container.get(CacheConfig)))
        container.register(
            UserRepository,
            lambda: UserRepository(container.get(Database), container.get(Cache)),
        )
        container.register(
            UserService, lambda: UserService(container.get(UserRepository))
        )

        # Resolve the service
        service = container.get(UserService)

        # Verify it works
        result = service.get_user_info(123)
        assert result["id"] == 123
        assert "localhost:5432" in str(result["data"])

        # Get service again - should reuse singletons
        service2 = container.get(UserService)
        assert service2.repo.db is service.repo.db  # Same DB instance
        assert service2.repo.cache is service.repo.cache  # Same cache instance

    def test_inject_decorator_integration(self):
        """Test @inject decorator with real container."""
        container = Container()

        # Setup dependencies
        container.register_singleton(DatabaseConfig, lambda: DatabaseConfig())
        container.register_singleton(
            Database, lambda: Database(container.get(DatabaseConfig))
        )

        @inject(container=container)
        def get_data(db: Annotated[Database, Inject()], query: str) -> str:
            return db.execute(query)

        # Call with injection
        result: str = cast(Callable[[str], str], get_data)("SELECT * FROM products")
        assert "localhost:5432" in result
        assert "SELECT * FROM products" in result

    def test_given_instances_integration(self):
        """Test Scala-style given instances."""
        container = Container()

        # Setup givens
        test_config = DatabaseConfig("testdb", 5433)
        container.given(DatabaseConfig, test_config)
        container.given(Database, lambda: Database(container.get(DatabaseConfig)))

        # Resolve through givens
        db = container.get(Database)
        assert db.config.host == "testdb"
        assert db.config.port == 5433

    def test_using_context_integration(self):
        """Test using context for temporary overrides."""
        container = Container()

        # Production config
        prod_config = DatabaseConfig("prod.db", 5432)
        container.given(DatabaseConfig, prod_config)
        container.given(Database, lambda: Database(container.get(DatabaseConfig)))

        # Normal resolution
        db1 = container.get(Database)
        assert db1.config.host == "prod.db"

        # Test override
        test_config = DatabaseConfig("test.db", 5433)
        with container.using(DatabaseConfig=test_config):
            db2 = container.get(Database)
            assert db2.config.host == "test.db"

        # Back to normal
        db3 = container.get(Database)
        assert db3.config.host == "prod.db"

    def test_request_scope_integration(self):
        """Test request scoping in real scenario."""
        container = Container()

        # Register request-scoped repository
        container.register_singleton(DatabaseConfig, lambda: DatabaseConfig())
        container.register_singleton(CacheConfig, lambda: CacheConfig())
        container.register_singleton(
            Database, lambda: Database(container.get(DatabaseConfig))
        )
        container.register_request(Cache, lambda: Cache(container.get(CacheConfig)))

        # First request
        with container.request_scope():
            cache1 = container.get(Cache)
            cache1.set("key1", "value1")

            # Same cache in same request
            cache2 = container.get(Cache)
            assert cache2.get("key1") == "value1"
            assert cache1 is cache2

        # Second request - new cache
        with container.request_scope():
            cache3 = container.get(Cache)
            assert cache3.get("key1") is None  # New cache instance
            assert cache3 is not cache1

    @pytest.mark.asyncio
    async def test_async_integration(self):
        """Test async dependency resolution."""
        container = Container()

        # Async provider
        async def create_async_db():
            await asyncio.sleep(0.01)  # Simulate async operation
            return Database(DatabaseConfig("async.db", 5432))

        container.register_singleton(Database, create_async_db)

        # Resolve async
        db = await container.aget(Database)
        assert db.config.host == "async.db"

        # Second get should return same instance
        db2 = await container.aget(Database)
        assert db is db2

    @pytest.mark.asyncio
    async def test_async_inject_integration(self):
        """Test async @inject decorator."""
        container = Container()

        # Setup async dependencies
        async def create_db():
            await asyncio.sleep(0.01)
            return Database(DatabaseConfig())

        async def create_cache():
            await asyncio.sleep(0.01)
            return Cache(CacheConfig())

        container.register(Database, create_db)
        container.register(Cache, create_cache)

        from typing import Annotated

        @inject(container=container)
        async def async_handler(
            db: Annotated[Database, Inject()],
            cache: Annotated[Cache, Inject()],
            user_id: int,
        ) -> str:
            # Store in cache
            result = db.execute(f"SELECT * FROM users WHERE id = {user_id}")
            cache.set(f"user:{user_id}", result)
            return result

        # Call with injection
        result: str = await cast(Callable[[int], Awaitable[str]], async_handler)(456)
        assert "localhost:5432" in result
        assert "456" in result

    def test_batch_operations_integration(self):
        """Test batch registration and resolution."""
        container = Container()

        # Batch register
        from typing import cast

        registrations = [
            (
                container.tokens.singleton("db_config", DatabaseConfig),
                lambda: DatabaseConfig(),
            ),
            (
                container.tokens.singleton("cache_config", CacheConfig),
                lambda: CacheConfig(),
            ),
        ]
        from injx.types import ProviderLike

        container.batch_register(
            cast(list[tuple[Token[object], ProviderLike[object]]], registrations)
        )

        # Batch resolve
        tokens = [
            container.tokens.singleton("db_config", DatabaseConfig),
            container.tokens.singleton("cache_config", CacheConfig),
        ]
        results = container.batch_resolve(cast(list[Token[object]], tokens))

        assert isinstance(results[cast(Token[object], tokens[0])], DatabaseConfig)
        assert isinstance(results[cast(Token[object], tokens[1])], CacheConfig)

    def test_performance_metrics(self):
        """Test performance tracking features."""
        container = Container()

        # Register and resolve multiple times
        container.register(Database, lambda: Database(DatabaseConfig()))

        for _ in range(10):
            container.get(Database)

        stats = container.get_stats()
        assert stats["total_providers"] == 1
        assert stats["cache_misses"] == 10
        assert stats["cache_hit_rate"] == 0.0  # No cache hits since transient

    def test_error_handling(self):
        """Test error handling and messages."""
        container = Container()

        # Unregistered dependency
        from injx.exceptions import ResolutionError

        with pytest.raises(ResolutionError) as exc_info:
            container.get(Database)

        error_msg = str(exc_info.value)
        assert "No provider registered" in error_msg
        assert "Database" in error_msg
        assert "Fix:" in error_msg  # Helpful error message

    def test_circular_dependency_detection(self):
        """Test handling of circular dependencies."""
        container = Container()

        # Create circular dependency
        token_a = Token("a", str)
        token_b = Token("b", str)

        def create_a() -> str:
            b = container.get(token_b)
            return f"A with {b}"

        def create_b() -> str:
            a = container.get(token_a)
            return f"B with {a}"

        container.register(token_a, create_a)
        container.register(token_b, create_b)

        from injx.exceptions import CircularDependencyError

        with pytest.raises(CircularDependencyError):
            container.get(token_a)
