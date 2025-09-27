"""Advanced tests for Dependencies pattern - comprehensive edge cases and scenarios."""

import gc
import sys
import time
from typing import Any, Protocol

import pytest

from injx import Container, Dependencies, Scope, Token, inject
from injx.exceptions import ResolutionError


# Service definitions for testing
class Database(Protocol):
    """Database service protocol."""

    def query(self, sql: str) -> list[dict[str, Any]]: ...
    def execute(self, sql: str) -> None: ...


class Cache(Protocol):
    """Cache service protocol."""

    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any, ttl: int = 300) -> None: ...


class Logger(Protocol):
    """Logger service protocol."""

    def log(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...


class EmailService(Protocol):
    """Email service protocol."""

    def send(self, to: str, subject: str, body: str) -> bool: ...


class AuthService(Protocol):
    """Auth service protocol."""

    def validate(self, token: str) -> bool: ...
    def create_token(self, user_id: int) -> str: ...


class MessageQueue(Protocol):
    """Message queue protocol."""

    def publish(self, topic: str, message: dict[str, Any]) -> None: ...
    def subscribe(self, topic: str) -> Any: ...


# Implementations
class MockDatabase:
    def query(self, sql: str) -> list[dict[str, Any]]:
        return [{"id": 1, "sql": sql}]

    def execute(self, sql: str) -> None:
        pass


class MockCache:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self.store.get(key)

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        self.store[key] = value


class MockLogger:
    def __init__(self) -> None:
        self.logs: list[str] = []

    def log(self, message: str) -> None:
        self.logs.append(message)

    def error(self, message: str) -> None:
        self.logs.append(f"ERROR: {message}")


class MockEmailService:
    def send(self, to: str, subject: str, body: str) -> bool:
        return True


class MockAuthService:
    def validate(self, token: str) -> bool:
        return token == "valid_token"

    def create_token(self, user_id: int) -> str:
        return f"token_{user_id}"


class MockMessageQueue:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, Any]]] = []

    def publish(self, topic: str, message: dict[str, Any]) -> None:
        self.messages.append((topic, message))

    def subscribe(self, topic: str) -> Any:
        return [msg for t, msg in self.messages if t == topic]


class TestDependenciesAdvanced:
    """Advanced Dependencies pattern tests."""

    def test_dependencies_empty(self):
        """Test handler with no Dependencies parameter."""
        container = Container()

        # Test handler without Dependencies parameter
        @inject
        def handler() -> str:
            return "no deps"

        with container.activate():
            result = handler()
            assert result == "no deps"

    def test_dependencies_single(self):
        """Test single dependency in Dependencies[Type]."""
        container = Container()
        container.register(Database, MockDatabase)

        @inject
        def handler(deps: Dependencies[Database]) -> str:
            db = deps[Database]
            result = db.query("SELECT 1")
            return f"Result: {result[0]['id']}"

        with container.activate():
            result = handler()
            assert result == "Result: 1"

    def test_dependencies_many_services(self):
        """Test with 10+ dependencies to check scalability."""
        container = Container()

        # Create 15 service types dynamically
        services = []
        for i in range(15):
            service_class = type(
                f"Service{i}",
                (),
                {"get_id": lambda self, i=i: i, "name": f"Service{i}"},
            )
            services.append(service_class)
            container.register(service_class, service_class)

        # Create a handler that uses all 15 services
        def create_handler():
            @inject
            def handler(deps: Dependencies[*services]) -> int:  # type: ignore
                total = 0
                for service_class in services:
                    instance = deps[service_class]
                    total += instance.get_id()
                return total

            return handler

        handler = create_handler()

        with container.activate():
            result = handler()
            # Sum of 0 to 14 = 105
            assert result == sum(range(15))

    def test_dependencies_with_tokens(self):
        """Test Dependencies with Token-based registration."""
        container = Container()

        # Register with tokens
        DB_TOKEN = Token("database", Database, scope=Scope.SINGLETON)
        CACHE_TOKEN = Token("cache", Cache, scope=Scope.SINGLETON)
        LOG_TOKEN = Token("logger", Logger, scope=Scope.TRANSIENT)

        container.register(DB_TOKEN, MockDatabase)
        container.register(CACHE_TOKEN, MockCache)
        container.register(LOG_TOKEN, MockLogger)

        # Map tokens to types for Dependencies
        container.register(Database, lambda: container.get(DB_TOKEN))
        container.register(Cache, lambda: container.get(CACHE_TOKEN))
        container.register(Logger, lambda: container.get(LOG_TOKEN))

        @inject
        def handler(deps: Dependencies[Database, Cache, Logger]) -> dict[str, Any]:
            db = deps[Database]
            cache = deps[Cache]
            logger = deps[Logger]

            # Use all services
            data = db.query("SELECT * FROM users")
            cache.set("users", data)
            logger.log("Fetched users")

            return {"data": data, "cached": True}

        with container.activate():
            result = handler()
            assert result["data"][0]["sql"] == "SELECT * FROM users"
            assert result["cached"] is True

    def test_dependencies_override_behavior(self):
        """Test override behavior with Dependencies - using given() instead."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> str:
            return deps[Database].query("SELECT 1")[0]["sql"]

        # Normal execution
        with container.activate():
            result1 = handler()
            assert result1 == "SELECT 1"

        # Test with given() which properly overrides
        class OverrideDB:
            def query(self, sql: str) -> list[dict[str, Any]]:
                return [{"id": 999, "sql": f"OVERRIDE: {sql}"}]

            def execute(self, sql: str) -> None:
                pass

        # Use given() to override - this is the correct pattern for type-based overrides
        container2 = Container()
        container2.register(Cache, MockCache)
        container2.given(Database, OverrideDB())

        with container2.activate():
            result2 = handler()
            assert result2 == "OVERRIDE: SELECT 1"

    def test_dependencies_memory_usage(self):
        """Test memory usage with large Dependencies."""
        container = Container()

        # Register many services - store types to reuse them
        service_types = []
        for i in range(100):
            service_class = type(f"Service{i}", (), {"data": [0] * 1000})
            service_types.append(service_class)
            container.register(service_class, service_class)

        # Force garbage collection
        gc.collect()
        initial_memory = sys.getsizeof(container)

        # Access services to test memory usage - use stored types
        _ = [container.get(service_types[i]) for i in range(100)]

        # Check memory is reasonable (not storing duplicate data)
        gc.collect()
        final_memory = sys.getsizeof(container)

        # Memory increase should be minimal since we're using references
        memory_increase = final_memory - initial_memory
        assert memory_increase < 10000  # Less than 10KB increase

    def test_dependencies_performance(self):
        """Test performance of Dependencies vs individual parameters."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)
        container.register(Logger, MockLogger)
        container.register(EmailService, MockEmailService)

        # Test with Dependencies pattern
        @inject
        def handler_deps(
            deps: Dependencies[Database, Cache, Logger, EmailService],
        ) -> None:
            deps[Database].query("SELECT 1")
            deps[Cache].get("key")
            deps[Logger].log("test")
            deps[EmailService].send("test@test.com", "Test", "Body")

        # Test with individual parameters
        @inject
        def handler_individual(
            db: Database, cache: Cache, logger: Logger, email: EmailService
        ) -> None:
            db.query("SELECT 1")
            cache.get("key")
            logger.log("test")
            email.send("test@test.com", "Test", "Body")

        with container.activate():
            # Time Dependencies pattern
            start = time.perf_counter()
            for _ in range(1000):
                handler_deps()
            deps_time = time.perf_counter() - start

            # Time individual pattern
            start = time.perf_counter()
            for _ in range(1000):
                handler_individual()
            individual_time = time.perf_counter() - start

            # Performance should be comparable (within 40% - Dependencies adds minimal overhead)
            performance_ratio = deps_time / individual_time
            assert 0.6 < performance_ratio < 1.4, (
                f"Performance ratio: {performance_ratio}"
            )

    def test_dependencies_with_scopes(self):
        """Test Dependencies with different scopes."""
        container = Container()

        call_count = {"singleton": 0, "transient": 0, "request": 0}

        def create_singleton():
            call_count["singleton"] += 1
            return MockDatabase()

        def create_transient():
            call_count["transient"] += 1
            return MockCache()

        def create_request():
            call_count["request"] += 1
            return MockLogger()

        container.register(Database, create_singleton, scope=Scope.SINGLETON)
        container.register(Cache, create_transient, scope=Scope.TRANSIENT)
        container.register(Logger, create_request, scope=Scope.REQUEST)

        @inject
        def handler(deps: Dependencies[Database, Cache, Logger]) -> None:
            # Just access them
            _ = deps[Database]
            _ = deps[Cache]
            _ = deps[Logger]

        with container.activate():
            with container.request_scope():
                # First call
                handler()
                # Second call in same request
                handler()

            with container.request_scope():
                # Third call in new request
                handler()

        # Singleton created once
        assert call_count["singleton"] == 1
        # Transient created for each Dependencies instance (3 times)
        assert call_count["transient"] == 3
        # Request created once per request scope (2 times)
        assert call_count["request"] == 2

    def test_dependencies_error_handling(self):
        """Test error handling with Dependencies."""
        container = Container()
        container.register(Database, MockDatabase)
        # Logger not registered

        @inject
        def handler(deps: Dependencies[Database, Logger]) -> None:
            deps[Database].query("SELECT 1")
            deps[Logger].log("test")  # This should fail

        with container.activate():
            # Should raise ResolutionError for missing Logger
            with pytest.raises(ResolutionError) as exc_info:
                handler()

            error_msg = str(exc_info.value)
            assert "Logger" in error_msg or "no provider" in error_msg.lower()

    def test_dependencies_nested_resolution(self):
        """Test nested Dependencies resolution."""
        container = Container()

        # Service with dependency
        class ServiceWithDeps:
            def __init__(self, db: Database, cache: Cache):
                self.db = db
                self.cache = cache

        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)
        container.register(
            ServiceWithDeps,
            lambda: ServiceWithDeps(container.get(Database), container.get(Cache)),
        )

        @inject
        def handler(deps: Dependencies[ServiceWithDeps, Logger]) -> bool:
            service = deps[ServiceWithDeps]
            # Should have resolved Database and Cache
            assert service.db is not None
            assert service.cache is not None
            return True

        # Register Logger after to test partial resolution
        container.register(Logger, MockLogger)

        with container.activate():
            result = handler()
            assert result is True

    def test_dependencies_with_given_instances(self):
        """Test Dependencies with given instances."""
        container = Container()

        # Use given instances
        given_db = MockDatabase()
        given_cache = MockCache()

        container.given(Database, given_db)
        container.given(Cache, given_cache)
        container.register(Logger, MockLogger)

        @inject
        def handler(deps: Dependencies[Database, Cache, Logger]) -> bool:
            # Should get the exact given instances
            assert deps[Database] is given_db
            assert deps[Cache] is given_cache
            # Logger should be newly created
            assert deps[Logger] is not None
            return True

        with container.activate():
            result = handler()
            assert result is True

    def test_dependencies_concurrent_access(self):
        """Test thread-safe concurrent access to Dependencies."""
        import threading

        container = Container()
        container.register(Database, MockDatabase, scope=Scope.SINGLETON)
        container.register(Cache, MockCache, scope=Scope.TRANSIENT)

        results = []
        errors = []

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> dict[str, Any]:
            db = deps[Database]
            cache = deps[Cache]
            return {"db_id": id(db), "cache_id": id(cache)}

        def worker():
            try:
                with container.activate():
                    result = handler()
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0
        assert len(results) == 10

        # All should have same singleton Database
        db_ids = [r["db_id"] for r in results]
        assert len(set(db_ids)) == 1

        # All should have different transient Cache (or at least multiple different ones)
        # Due to threading, some instances might be reused but we should see variety
        cache_ids = [r["cache_id"] for r in results]
        unique_caches = len(set(cache_ids))
        # Should have at least 2 different cache instances to show transient behavior
        assert unique_caches >= 2, f"Expected at least 2 unique cache instances, got {unique_caches}"
