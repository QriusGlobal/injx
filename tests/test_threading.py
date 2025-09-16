"""Thread safety and concurrent access tests."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# no direct pytest usage in this module
from injx import Container, Scope, Token, inject


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_singleton_creation(self):
        """Test that concurrent singleton creation is thread-safe."""
        container = Container()
        token: Token[dict[str, int]] = Token("thread_singleton", dict[str, int])

        creation_count = 0
        creation_lock = threading.Lock()

        def create_singleton() -> dict[str, int]:
            nonlocal creation_count
            with creation_lock:
                creation_count += 1
            # Simulate slow creation to increase chance of race condition
            time.sleep(0.01)
            thread_id = int(threading.current_thread().ident or -1)
            return {"thread_id": thread_id, "count": creation_count}

        container.register(token, create_singleton, Scope.SINGLETON)

        # Launch many threads to resolve the singleton
        num_threads = 20
        results: list[dict[str, int]] = []

        def resolve_singleton():
            result = container.get(token)
            results.append(result)

        threads: list[threading.Thread] = []
        for _ in range(num_threads):
            thread = threading.Thread(target=resolve_singleton)
            threads.append(thread)

        # Start all threads simultaneously
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All results should be the same instance
        assert len(results) == num_threads
        first_result = results[0]
        for result in results:
            assert result is first_result

        # Factory should only be called once
        assert creation_count == 1

    def test_concurrent_registration_and_resolution(self):
        """Test concurrent registration and resolution operations."""
        container = Container()
        results: list[tuple[int, str]] = []
        errors: list[tuple[int, Exception]] = []

        def register_and_resolve(index: int):
            try:
                token = Token(f"concurrent_{index}", str)

                def provider(idx=index):
                    return f"value_{idx}"

                container.register(token, provider)
                result = container.get(token)
                results.append((index, result))
            except Exception as e:
                errors.append((index, e))

        # Launch concurrent operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures: list[Any] = [
                executor.submit(register_and_resolve, i) for i in range(50)
            ]
            for future in futures:
                future.result()  # Wait for completion

        # Should have no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Should have all results
        assert len(results) == 50

        # Each should have correct value
        for index, result in results:
            assert result == f"value_{index}"

    def test_thread_local_circular_dependency_detection(self):
        """Test that circular dependency detection is thread-local."""
        container = Container()

        # Create circular dependency
        token_a = Token("thread_A", str)
        token_b = Token("thread_B", str)

        container.register(token_a, lambda: container.get(token_b))
        container.register(token_b, lambda: container.get(token_a))

        errors: list[str] = []

        def try_resolve():
            try:
                container.get(token_a)
                errors.append("Should have raised CircularDependencyError")
            except Exception as e:
                # Should be CircularDependencyError
                if "Circular dependency" not in str(e):
                    errors.append(f"Wrong error type: {e}")

        # Launch multiple threads that should all detect the circular dependency
        threads: list[threading.Thread] = []
        for _ in range(5):
            thread = threading.Thread(target=try_resolve)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have no errors (all threads should properly detect circular dependency)
        assert len(errors) == 0, f"Thread safety errors: {errors}"

    def test_concurrent_override_and_resolution(self):
        """Test concurrent override operations are thread-safe."""
        container = Container()
        token = Token("override_test", str)

        container.register(token, lambda: "original")

        results: list[str] = []

        def override_and_resolve(value: str):
            container.override(token, value)
            time.sleep(0.001)  # Small delay to increase chance of race
            result = container.get(token)
            results.append(result)

        # Launch concurrent overrides
        values = [f"override_{i}" for i in range(10)]
        threads: list[threading.Thread] = []

        for value in values:
            thread = threading.Thread(target=override_and_resolve, args=(value,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All results should be one of the override values (not "original")
        assert len(results) == 10
        for result in results:
            assert result != "original"
            assert result.startswith("override_")

    def test_resource_tracking_thread_safety(self):
        """Test that resource tracking is thread-safe."""

        class CloseableResource:
            def __init__(self, resource_id: str):
                self.resource_id = resource_id
                self.closed = False

            def close(self):
                self.closed = True

        # Use explicit context-managed registration in tests instead of runtime mutation

        container = Container()
        resources_created: list[CloseableResource] = []

        def create_and_get_resource(resource_id: str) -> CloseableResource:
            token = Token(f"resource_{resource_id}", CloseableResource)
            from contextlib import contextmanager

            @contextmanager
            def cm():
                resource = CloseableResource(resource_id)
                resources_created.append(resource)
                try:
                    yield resource
                finally:
                    resource.close()

            container.register_context(
                token, lambda cm=cm: cm(), is_async=False, scope=Scope.SINGLETON
            )
            return container.get(token)

        # Create resources concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures: list[Any] = [
                executor.submit(create_and_get_resource, str(i)) for i in range(10)
            ]
            results = [future.result() for future in futures]

        # Should have created all resources
        assert len(resources_created) == 10
        assert len(results) == 10

        # All should be tracked for cleanup
        assert len(container.resources_view()) == 10

    def test_injection_cache_thread_safety(self):
        """Test that injection cache is thread-safe."""
        container = Container()

        class Service:
            def __init__(self, value: str):
                self.value = value

        service_token = Token("service", Service)
        container.register(service_token, lambda: Service("test"))

        results: list[str] = []

        @inject(container=container)
        def injected_function(service: Service) -> str:
            time.sleep(0.001)  # Small delay
            return f"Result: {service.value}"

        def call_injected_function():
            result = injected_function()
            results.append(result)

        # Call injected function concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(call_injected_function) for _ in range(20)]
            for future in futures:
                future.result()

        # All calls should succeed
        assert len(results) == 20
        for result in results:
            assert result == "Result: test"

    def test_stress_test_concurrent_operations(self):
        """Stress test with many concurrent operations of different types."""
        container = Container()

        # Pre-register some singletons and transients
        for i in range(10):
            singleton_token: Token[Any] = Token(f"singleton_{i}", dict)
            transient_token: Token[Any] = Token(f"transient_{i}", list)

            container.register(
                singleton_token,
                lambda idx=i: {"id": idx, "type": "singleton"},
                Scope.SINGLETON,
            )
            container.register(
                transient_token, lambda idx=i: [idx, "transient"], Scope.TRANSIENT
            )

        operations_completed: list[int] = []
        errors: list[tuple[int, Exception]] = []

        def mixed_operations(worker_id: int):
            try:
                for i in range(10):
                    # Get singletons
                    token: Token[Any] = Token(f"singleton_{i}", dict)
                    result = container.get(token)
                    assert result["type"] == "singleton"

                    # Get transients
                    tok2: Token[Any] = Token(f"transient_{i}", list)
                    result = container.get(tok2)
                    assert result[1] == "transient"

                    # Test overrides (scoped per-thread)
                    override_token: Token[Any] = Token("singleton_0", dict)
                    with container.use_overrides(
                        {override_token: {"overridden": True}}
                    ):
                        overridden = container.get(override_token)
                        assert overridden["overridden"] is True

                operations_completed.append(worker_id)
            except Exception as e:
                errors.append((worker_id, e))

        # Run stress test
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(mixed_operations, i) for i in range(50)]
            for future in futures:
                future.result()

        # Verify results
        assert len(errors) == 0, f"Errors in stress test: {errors}"
        assert len(operations_completed) == 50
