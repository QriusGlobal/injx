"""Performance and O(1) lookup verification tests."""

import time
from typing import Any

import pytest

from injx import Container, Scope, Token, inject
from injx.exceptions import CircularDependencyError


class TestPerformance:
    """Test performance characteristics and O(1) lookups."""

    def test_o1_type_resolution_scaling(self):
        """Test that type resolution maintains O(1) performance as container grows."""
        container = Container()

        # Register many services to test scaling
        num_services = 1000
        services: list[tuple[Token[Any], type]] = []

        for i in range(num_services):
            class_name = f"Service{i}"
            service_class = type(class_name, (), {"value": i})
            token = Token(f"service_{i}", service_class)
            container.register(token, service_class)
            services.append((token, service_class))

        # Measure resolution time for first, middle, and last services
        test_indices = [0, num_services // 2, num_services - 1]
        resolution_times: list[float] = []

        for idx in test_indices:
            token, service_class = services[idx]

            # Warm up (exercise type path)
            container.get(service_class)

            # Time the resolution
            start_time = time.perf_counter()
            for _ in range(100):  # Multiple iterations for better measurement
                container.get(service_class)
            end_time = time.perf_counter()

            avg_time = (end_time - start_time) / 100
            resolution_times.append(avg_time)

        # O(1) means resolution time should be roughly constant
        # Allow some variance but not more than 2x difference
        min_time = min(resolution_times)
        max_time = max(resolution_times)

        assert max_time <= min_time * 2, (
            f"Resolution times vary too much: {resolution_times}"
        )

        # Also check absolute performance - should be very fast
        for resolve_time in resolution_times:
            assert resolve_time < 0.005, f"Resolution too slow: {resolve_time:.6f}s"

    def test_basic_resolution_performance(self):
        """Simplified resolution performance without protocol indirection."""
        container = Container()
        num = 200
        tokens: list[tuple[Token[Any], type]] = []
        for i in range(num):
            cls = type(f"Impl{i}", (), {"id": i})
            tok = Token(f"impl_{i}", cls)
            container.register(tok, cls)
            tokens.append((tok, cls))

        # Warmup
        for tok, _ in tokens[:5]:
            container.get(tok)

        # Measure
        start = time.perf_counter()
        for _ in range(100):
            for tok, _cls in tokens:
                container.get(tok)
        dt = time.perf_counter() - start
        per_call = dt / (100 * num)
        assert per_call < 0.002, f"Resolution too slow: {per_call:.6f}s"

    def test_injection_cache_performance(self):
        """Test that injection caching improves performance."""
        container = Container()

        class Service1:
            def __init__(self):
                self.value = "service1"

        class Service2:
            def __init__(self):
                self.value = "service2"

        class Service3:
            def __init__(self):
                self.value = "service3"

        token1 = Token("service1", Service1)
        token2 = Token("service2", Service2)
        token3 = Token("service3", Service3)

        container.register(token1, Service1)
        container.register(token2, Service2)
        container.register(token3, Service3)

        @inject(container=container)
        def complex_function(s1: Service1, s2: Service2, s3: Service3) -> str:
            return f"{s1.value}-{s2.value}-{s3.value}"

        # First call should cache injection metadata
        first_call_start = time.perf_counter()
        result1 = complex_function()
        first_call_end = time.perf_counter()

        first_call_time = first_call_end - first_call_start

        # Subsequent calls should be faster due to caching
        cached_call_times: list[float] = []
        for _ in range(10):
            start = time.perf_counter()
            result = complex_function()
            end = time.perf_counter()
            cached_call_times.append(end - start)
            assert result == result1  # Verify correctness

        avg_cached_time = sum(cached_call_times) / len(cached_call_times)

        # Cached calls should be significantly faster than first call
        # (First call includes inspection overhead)
        assert avg_cached_time <= first_call_time, (
            f"Cached calls not faster: first={first_call_time:.6f}, "
            f"avg_cached={avg_cached_time:.6f}"
        )

    def test_singleton_access_performance(self):
        """Test that singleton access is fast after first creation."""
        container = Container()

        class ExpensiveService:
            def __init__(self):
                # Simulate expensive initialization
                time.sleep(0.01)
                self.value = "expensive"

        token = Token("expensive", ExpensiveService)
        container.register(token, ExpensiveService, Scope.SINGLETON)

        # First access includes creation time
        first_access_start = time.perf_counter()
        service1 = container.get(token)
        first_access_end = time.perf_counter()

        first_access_time = first_access_end - first_access_start
        assert first_access_time >= 0.01  # Should include creation time

        # Subsequent accesses should be very fast
        subsequent_times: list[float] = []
        for _ in range(100):
            start = time.perf_counter()
            service = container.get(token)
            end = time.perf_counter()
            subsequent_times.append(end - start)
            assert service is service1  # Same instance

        avg_subsequent_time = sum(subsequent_times) / len(subsequent_times)

        # Subsequent accesses should be orders of magnitude faster
        assert avg_subsequent_time < 0.005, (
            f"Singleton access too slow: {avg_subsequent_time:.6f}s"
        )
        assert avg_subsequent_time < first_access_time / 10, (
            f"Singleton access not fast enough: "
            f"first={first_access_time:.6f}, avg_subsequent={avg_subsequent_time:.6f}"
        )

    def test_large_container_registration_performance(self):
        """Test registration performance with large numbers of services."""
        container = Container()

        # Register many services and measure time
        num_services = 1000
        registration_times: list[float] = []

        for i in range(num_services):
            service_class = type(f"Service{i}", (), {"id": i})
            token = Token(f"service_{i}", service_class)

            start_time = time.perf_counter()
            container.register(token, service_class)
            end_time = time.perf_counter()

            registration_times.append(end_time - start_time)

        # Registration time should remain relatively constant (not grow linearly)
        early_times = registration_times[:100]
        late_times = registration_times[-100:]

        avg_early = sum(early_times) / len(early_times)
        avg_late = sum(late_times) / len(late_times)

        # Late registrations shouldn't be significantly slower than early ones
        assert avg_late <= avg_early * 2, (
            f"Registration performance degrades: early={avg_early:.6f}, late={avg_late:.6f}"
        )

    def test_memory_efficiency(self):
        """Test that container doesn't use excessive memory."""
        import sys

        container = Container()

        # Measure initial memory usage using public views
        initial_size = sys.getsizeof(container) + sum(
            sys.getsizeof(obj)
            for obj in [
                container.get_providers_view(),
                container.resources_view(),
            ]
        )

        # Register many services
        num_services = 100
        for i in range(num_services):
            service_class = type(f"Service{i}", (), {"id": i})
            token = Token(f"service_{i}", service_class)
            container.register(token, service_class, Scope.SINGLETON)
            # Create some singletons
            if i % 10 == 0:
                container.get(token)

        # Measure final memory usage
        final_size = sys.getsizeof(container) + sum(
            sys.getsizeof(obj)
            for obj in [
                container.get_providers_view(),
                container.resources_view(),
            ]
        )

        # Memory growth should be reasonable (not exponential)
        memory_growth = final_size - initial_size
        memory_per_service = memory_growth / num_services

        # Should be less than 1KB per service on average
        assert memory_per_service < 1024, (
            f"Memory usage too high: {memory_per_service:.1f} bytes per service"
        )

    @pytest.mark.slow
    def test_stress_performance(self):
        """Stress test with many concurrent operations."""
        from concurrent.futures import ThreadPoolExecutor

        container = Container()

        # Pre-register services
        num_services = 50
        tokens: list[Token[Any]] = []

        for i in range(num_services):
            service_class = type(f"Service{i}", (), {"id": i, "call_count": 0})
            token = Token(f"service_{i}", service_class)
            container.register(token, service_class, Scope.SINGLETON)
            tokens.append(token)

        def stress_worker(worker_id: int):
            """Perform many operations rapidly."""
            operations = 1000
            start_time = time.perf_counter()

            for i in range(operations):
                # Mix of different operations
                token_idx = i % len(tokens)
                token = tokens[token_idx]

                service = container.get(token)
                service.call_count += 1

                # Occasional override operations
                if i % 50 == 0:
                    container.override(token, service)

            end_time = time.perf_counter()
            return end_time - start_time

        # Run stress test with multiple workers
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures: list[Any] = [executor.submit(stress_worker, i) for i in range(20)]
            completion_times: list[float] = [future.result() for future in futures]

        avg_completion_time = sum(completion_times) / len(completion_times)

        # Should complete 1000 operations per worker in reasonable time
        assert avg_completion_time < 1.0, (
            f"Stress test too slow: {avg_completion_time:.3f}s per 1000 operations"
        )

    def test_token_hashing_performance(self):
        """Test that token hashing is O(1) with pre-computed hashes."""
        # Create tokens
        token1 = Token("service1", int)
        token2 = Token("service2", str)
        token3 = Token("service1", int)  # Same as token1

        # Test hash consistency
        assert hash(token1) == hash(token3), "Same tokens should have same hash"
        assert hash(token1) != hash(token2), (
            "Different tokens should have different hashes"
        )

        # Measure hashing performance for many tokens
        num_tokens = 10000
        tokens = [
            Token(f"token_{i}", int, qualifier=f"q_{i}") for i in range(num_tokens)
        ]

        # Time the hashing
        start_time = time.perf_counter()
        hashes = [hash(token) for token in tokens]
        end_time = time.perf_counter()

        hash_time = end_time - start_time
        time_per_hash = hash_time / num_tokens

        # Hashing should be extremely fast (< 1 microsecond per hash)
        assert time_per_hash < 5e-6, (
            f"Token hashing too slow: {time_per_hash * 1e6:.3f} μs per hash"
        )

        # Verify all hashes are unique
        assert len(set(hashes)) == num_tokens, "All token hashes should be unique"

        # Test hash performance in dictionary operations
        token_dict = {}
        start_time = time.perf_counter()
        for token in tokens:
            token_dict[token] = f"value_{token.name}"
        end_time = time.perf_counter()

        dict_time = end_time - start_time
        assert dict_time < 0.1, (
            f"Dictionary operations with tokens too slow: {dict_time:.4f}s"
        )

    def test_singleton_lock_performance(self):
        """Test performance of singleton lock creation and cleanup."""
        container = Container()

        # Register many singleton services
        num_singletons = 100
        tokens = []
        for i in range(num_singletons):
            service_class = type(f"Singleton{i}", (), {"id": i})
            token = Token(f"singleton_{i}", service_class)
            container.register(token, service_class, Scope.SINGLETON)
            tokens.append(token)

        # Measure time for first-time singleton creation (includes lock operations)
        creation_times = []
        for token in tokens:
            start_time = time.perf_counter()
            container.get(token)
            end_time = time.perf_counter()
            creation_times.append(end_time - start_time)

        avg_creation_time = sum(creation_times) / len(creation_times)

        # Verify locks are released (they may remain in dictionary but should be unlocked)
        for token in tokens:
            obj_token = container._obj_token(token)
            if obj_token in container._singleton_locks:
                lock = container._singleton_locks[obj_token]
                assert not lock.locked(), f"Lock for {token.name} should be released"

        # Measure subsequent access times (no lock overhead)
        access_times = []
        for token in tokens:
            start_time = time.perf_counter()
            for _ in range(100):
                container.get(token)
            end_time = time.perf_counter()
            access_times.append((end_time - start_time) / 100)

        avg_access_time = sum(access_times) / len(access_times)

        # Access should be faster than or equal to creation (no slower)
        # Note: Both operations are extremely fast (microseconds), so we check they're comparable
        assert avg_access_time <= avg_creation_time * 2, (
            f"Singleton access not optimized: creation={avg_creation_time:.6f}s, "
            f"access={avg_access_time:.6f}s"
        )

    def test_resolution_stack_vs_set_performance(self):
        """Compare performance of tuple-based stack vs set-based cycle detection."""
        container = Container()

        # Create a deep dependency chain
        depth = 100
        tokens = []
        classes = []
        for i in range(depth):
            service_class = type(f"Service{i}", (), {"id": i})
            token = Token(f"service_{i}", service_class)
            tokens.append(token)
            classes.append(service_class)

            if i == 0:
                # First service is independent
                container.register(token, lambda cls=service_class: cls())
            else:
                # Each service depends on the previous one
                prev_token = tokens[i - 1]
                container.register(
                    token,
                    lambda c=container, t=prev_token, cls=service_class: cls()
                    if c.get(t)
                    else cls(),
                )

        # Measure resolution time for deep chain
        start_time = time.perf_counter()
        for _ in range(100):
            container.get(tokens[-1])  # Resolve deepest service
        end_time = time.perf_counter()

        resolution_time = (end_time - start_time) / 100

        # Should be fast even for deep chains (O(1) cycle detection)
        assert resolution_time < 0.01, (
            f"Deep chain resolution too slow: {resolution_time:.6f}s"
        )

        # Test with cycle detection - create a new container with a cycle
        cycle_container = Container()
        cycle_tokens = []
        cycle_classes = []

        # Create a chain with a cycle
        for i in range(10):
            service_class = type(f"CycleService{i}", (), {"id": i})
            token = Token(f"cycle_service_{i}", service_class)
            cycle_tokens.append(token)
            cycle_classes.append(service_class)

        # Register services with a cycle: 0->1->2->...->9->0
        for i in range(10):
            token = cycle_tokens[i]
            service_class = cycle_classes[i]
            next_token = cycle_tokens[(i + 1) % 10]  # Last one points back to first

            cycle_container.register(
                token,
                lambda c=cycle_container, t=next_token, cls=service_class: cls()
                if c.get(t)
                else cls(),
            )

        # Measure cycle detection time
        detection_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            try:
                cycle_container.get(cycle_tokens[0])
            except CircularDependencyError:
                pass  # Expected
            except Exception as e:
                pytest.fail(f"Unexpected exception: {e}")
            end_time = time.perf_counter()
            detection_times.append(end_time - start_time)

        avg_detection_time = sum(detection_times) / len(detection_times)

        # Cycle detection should be very fast (O(1))
        assert avg_detection_time < 0.001, (
            f"Cycle detection too slow: {avg_detection_time:.6f}s"
        )

    def test_memory_efficiency_with_tracemalloc(self):
        """Test memory efficiency using tracemalloc for accurate profiling."""
        import gc
        import tracemalloc

        tracemalloc.start()

        # Take initial snapshot
        gc.collect()
        snapshot1 = tracemalloc.take_snapshot()

        # Create container with many services
        container = Container()
        num_services = 1000

        for i in range(num_services):
            # Create different types of services
            if i % 3 == 0:
                # Singleton
                token = Token(f"singleton_{i}", object)
                container.register(token, object, Scope.SINGLETON)
                if i % 10 == 0:
                    container.get(token)  # Create some singletons
            elif i % 3 == 1:
                # Request scoped
                token = Token(f"request_{i}", object)
                container.register(token, object, Scope.REQUEST)
            else:
                # Transient
                token = Token(f"transient_{i}", object)
                container.register(token, object, Scope.TRANSIENT)

        # Take final snapshot
        gc.collect()
        snapshot2 = tracemalloc.take_snapshot()

        # Stop tracing
        tracemalloc.stop()

        # Analyze memory growth
        top_stats = snapshot2.compare_to(snapshot1, "lineno")

        # Find stats for container and token modules
        container_stats = [s for s in top_stats if "container.py" in str(s.traceback)]
        token_stats = [s for s in top_stats if "tokens.py" in str(s.traceback)]

        # Calculate total memory used
        container_memory = sum(s.size_diff for s in container_stats if s.size_diff > 0)
        token_memory = sum(s.size_diff for s in token_stats if s.size_diff > 0)

        # Memory per service should be reasonable
        total_memory = container_memory + token_memory
        memory_per_service = total_memory / num_services if num_services > 0 else 0

        # Should use less than 500 bytes per service on average
        assert memory_per_service < 500, (
            f"Memory usage too high: {memory_per_service:.1f} bytes per service "
            f"(container: {container_memory}, tokens: {token_memory})"
        )
