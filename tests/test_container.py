"""Enhanced singular Container tests (consolidated)."""

import pytest

from injx.container import Container
from injx.tokens import Scope, Token


class Database:
    def __init__(self) -> None:
        self.id = id(self)


class Cache:
    def get(self, key: str) -> str:  # pragma: no cover - trivial
        return f"cached_{key}"


class Service:
    def __init__(self, db: Database, cache: Cache) -> None:
        self.db = db
        self.cache = cache


class TestContainer:
    def test_container_initialization(self) -> None:
        container = Container()
        assert hasattr(container, "tokens")
        assert len(container.get_providers_view()) == 0
        assert len(container.resources_view()) == 0
        assert container.resolve_given(int) is None
        stats = container.get_stats()
        assert stats["singletons"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0

    def test_register_provider(self) -> None:
        container = Container()

        def create_db() -> Database:
            return Database()

        result = container.register(Token("database", Database), create_db)
        assert result is container
        assert len(container.get_providers_view()) == 1

    def test_register_with_type(self) -> None:
        container = Container()

        def create_db() -> Database:
            return Database()

        container.register(Database, create_db)
        assert len(container.get_providers_view()) == 1
        token = list(container.get_providers_view().keys())[0]
        assert token.type_ == Database

    def test_register_with_string(self) -> None:
        container = Container()

        def create_db() -> Database:
            return Database()

        with pytest.raises(TypeError):
            container.register("my_database", create_db)  # type: ignore[arg-type]

    def test_register_validates_provider(self) -> None:
        container = Container()
        with pytest.raises(TypeError):
            container.register(Token("database", Database), "not_callable")  # type: ignore[arg-type]

    def test_register_chaining(self) -> None:
        container = (
            Container()
            .register(Token("db", Database), lambda: Database())
            .register(Token("cache", Cache), lambda: Cache())
            .register(Token("service", Service), lambda: Service(Database(), Cache()))
        )
        assert len(container.get_providers_view()) == 3

    def test_register_scoped_methods(self) -> None:
        container = Container()
        container.register_singleton(Database, lambda: Database())
        container.register_request(Cache, lambda: Cache())
        container.register_transient(Service, lambda: Service(Database(), Cache()))
        tokens = list(container.get_providers_view().keys())
        assert any(t.scope == Scope.SINGLETON for t in tokens)
        assert any(t.scope == Scope.REQUEST for t in tokens)
        assert any(t.scope == Scope.TRANSIENT for t in tokens)

    def test_register_value(self) -> None:
        container = Container()
        db_instance = Database()
        container.register_value(Database, db_instance)
        stats = container.get_stats()
        assert stats["singletons"] == 1
        assert container.get(Database) is db_instance

    def test_get_simple(self) -> None:
        container = Container()
        db_instance = Database()
        container.register(Database, lambda: db_instance)
        result = container.get(Database)
        assert result is db_instance

    def test_get_singleton(self) -> None:
        container = Container()
        call_count = 0

        def create_db() -> Database:
            nonlocal call_count
            call_count += 1
            return Database()

        container.register(Database, create_db, scope=Scope.SINGLETON)
        db1 = container.get(Database)
        db2 = container.get(Database)
        assert db1 is db2
        assert call_count == 1

    def test_given_instances(self) -> None:
        container = Container()
        container.given(int, 42)
        assert container.resolve_given(int) == 42

    def test_has_method(self) -> None:
        container = Container()
        assert container.has(Token("unknown", str)) is False
        container.given(str, "value")
        assert container.has(str) is True


class TestTypeResolution:
    """Test type-based resolution using direct types."""

    def test_resolve_by_concrete_type(self):
        container = Container()

        class ServiceX:
            def __init__(self) -> None:
                self.value = 42

        container.register(ServiceX, ServiceX)
        resolved = container.get(ServiceX)
        assert isinstance(resolved, ServiceX)
        assert resolved.value == 42


class TestSingletonLocks:
    """Test singleton lock creation and cleanup."""

    def test_get_singleton_lock_on_demand(self):
        """Test that _get_singleton_lock creates locks on demand."""
        container = Container()

        token = Token("test", object)
        obj_token = container._obj_token(token)

        # Initially no lock exists
        assert obj_token not in container._singleton_locks

        # Get lock creates it on demand
        lock1 = container._get_singleton_lock(obj_token)
        assert obj_token in container._singleton_locks
        assert lock1 is not None

        # Getting again returns the same lock
        lock2 = container._get_singleton_lock(obj_token)
        assert lock1 is lock2

    def test_cleanup_singleton_lock(self):
        """Test that _cleanup_singleton_lock removes locks."""
        container = Container()

        token = Token("test", object)
        obj_token = container._obj_token(token)

        # Create a lock
        container._get_singleton_lock(obj_token)
        assert obj_token in container._singleton_locks

        # Clean it up
        container._cleanup_singleton_lock(obj_token)
        assert obj_token not in container._singleton_locks

        # Cleanup is idempotent (doesn't fail if lock doesn't exist)
        container._cleanup_singleton_lock(obj_token)
        assert obj_token not in container._singleton_locks

    def test_singleton_lock_cleanup_after_successful_creation(self):
        """Test that singleton locks are cleaned up after successful singleton creation."""
        container = Container()

        class TestService:
            instances_created = 0

            def __init__(self):
                TestService.instances_created += 1
                self.id = TestService.instances_created

        token = Token("test", TestService)
        obj_token = container._obj_token(token)
        container.register(token, TestService, Scope.SINGLETON)

        # Before first get, no lock exists
        assert obj_token not in container._singleton_locks

        # Get the singleton
        instance1 = container.get(token)

        # After creation, lock should be cleaned up or unlocked
        # Note: The implementation may keep the lock object but it should be unlocked
        if obj_token in container._singleton_locks:
            lock = container._singleton_locks[obj_token]
            assert not lock.locked(), "Lock should be released after singleton creation"
        assert instance1.id == 1

        # Getting again should not recreate the lock or acquire it
        instance2 = container.get(token)
        if obj_token in container._singleton_locks:
            lock = container._singleton_locks[obj_token]
            assert not lock.locked(), "Lock should remain unlocked for cached singleton"
        assert instance1 is instance2
        assert TestService.instances_created == 1

    def test_singleton_lock_with_concurrent_access(self):
        """Test that singleton lock properly handles concurrent access."""
        import threading
        import time

        container = Container()

        class SlowService:
            instances = []

            def __init__(self):
                # Simulate slow initialization
                time.sleep(0.01)
                SlowService.instances.append(self)

        token = Token("slow", SlowService)
        container.register(token, SlowService, Scope.SINGLETON)

        # Try to create singleton from multiple threads
        threads = []
        results = []

        def get_singleton():
            result = container.get(token)
            results.append(result)

        # Start multiple threads simultaneously
        for _ in range(10):
            thread = threading.Thread(target=get_singleton)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have created only one instance
        assert len(SlowService.instances) == 1
        assert len(results) == 10

        # All results should be the same instance
        first_result = results[0]
        for result in results:
            assert result is first_result

        # Lock should be cleaned up
        obj_token = container._obj_token(token)
        assert obj_token not in container._singleton_locks

    def test_singleton_lock_cleanup_with_failing_initialization(self):
        """Test lock behavior when singleton initialization fails."""
        container = Container()

        class FailingService:
            attempt = 0

            def __init__(self):
                FailingService.attempt += 1
                if FailingService.attempt == 1:
                    raise ValueError("First attempt fails")
                # Second attempt succeeds

        token = Token("failing", FailingService)
        obj_token = container._obj_token(token)
        container.register(token, FailingService, Scope.SINGLETON)

        # First attempt should fail
        with pytest.raises(ValueError, match="First attempt fails"):
            container.get(token)

        # Lock state after failure (implementation dependent)
        # The important thing is that a retry should work

        # Second attempt should succeed
        instance = container.get(token)
        assert instance is not None
        assert FailingService.attempt == 2

        # Lock should be cleaned up after successful creation
        assert obj_token not in container._singleton_locks

    def test_multiple_singleton_locks_independence(self):
        """Test that different singletons have independent locks."""
        container = Container()

        token1 = Token("service1", object)
        token2 = Token("service2", object)
        obj_token1 = container._obj_token(token1)
        obj_token2 = container._obj_token(token2)

        # Get locks for both tokens
        lock1 = container._get_singleton_lock(obj_token1)
        lock2 = container._get_singleton_lock(obj_token2)

        # They should be different locks
        assert lock1 is not lock2

        # Cleanup one shouldn't affect the other
        container._cleanup_singleton_lock(obj_token1)
        assert obj_token1 not in container._singleton_locks
        assert obj_token2 in container._singleton_locks

        # Clean up the second one
        container._cleanup_singleton_lock(obj_token2)
        assert obj_token2 not in container._singleton_locks
