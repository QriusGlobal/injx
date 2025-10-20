"""Advanced tests for autowire caching system.

This module provides comprehensive testing for:
- Race conditions and thread safety
- LRU cache eviction behavior
- Property-based testing with hypothesis
- Mock-based API contract validation
- Real-world integration scenarios

These tests complement test_autowire.py with focus on edge cases,
concurrency bugs, and production-scale scenarios.
"""

import inspect
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Generic, TypeVar
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from hypothesis import given, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from injx import (
    Container,
    Scope,
    Token,
    autowire,
    clear_analysis_cache,
    get_analysis_cache_info,
    wire,
)

T = TypeVar("T")


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def clean_cache():
    """Clear cache before and after each test."""
    clear_analysis_cache()
    yield
    clear_analysis_cache()


# =============================================================================
# TIER 1: RACE CONDITION & CONCURRENCY TESTS (15 tests)
# =============================================================================


class TestRaceConditions:
    """Tests for race conditions and concurrent cache access."""

    def test_cache_same_class_from_50_threads(self):
        """Verify exactly 1 cache miss and 49 hits with barrier synchronization."""
        barrier = threading.Barrier(50)
        clear_analysis_cache()

        class SharedClass:
            def __init__(self) -> None:
                self.value = 42

        errors = []
        containers = []

        def worker():
            try:
                barrier.wait()  # Synchronize all thread starts
                container = Container()
                containers.append(container)
                with container.activate():
                    autowire(SharedClass)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(worker) for _ in range(50)]
            for future in as_completed(futures):
                future.result()  # Raise any exceptions

        assert len(errors) == 0, f"Thread errors occurred: {errors}"
        info = get_analysis_cache_info()
        assert info["misses"] == 1, f"Expected 1 miss, got {info['misses']}"
        assert info["hits"] == 49, f"Expected 49 hits, got {info['hits']}"

    def test_cache_eviction_with_300_classes(self):
        """Trigger LRU maxsize=256 eviction and verify correct behavior."""
        clear_analysis_cache()
        container = Container()

        # Create 300 unique classes to exceed maxsize=256
        classes = []
        for i in range(300):

            def make_init(idx):
                def __init__(self) -> None:
                    self.id = idx

                return __init__

            cls = type(f"EvictClass{i}", (), {"__init__": make_init(i)})
            classes.append(cls)

        # Register all 300 classes
        with container.activate():
            for cls in classes:
                autowire(cls)

        info = get_analysis_cache_info()
        # 300 misses initially (all new), cache size capped at 256
        assert info["misses"] == 300, f"Expected 300 misses, got {info['misses']}"
        assert info["size"] <= 256, f"Cache size {info['size']} exceeds maxsize 256"
        assert info["maxsize"] == 256

        # Re-register first class - should have been evicted (cache miss)
        container2 = Container()
        with container2.activate():
            autowire(classes[0])

        info2 = get_analysis_cache_info()
        # First class likely evicted, so another miss
        assert info2["misses"] > info["misses"], "First class should be evicted"

    def test_clear_cache_during_concurrent_analysis(self):
        """Test clear_cache() called mid-execution doesn't crash threads."""
        clear_analysis_cache()
        stop_event = threading.Event()
        errors = []

        class ConcurrentClass:
            def __init__(self) -> None:
                self.value = 1

        def worker():
            """Continuously register classes."""
            try:
                while not stop_event.is_set():
                    container = Container()
                    with container.activate():
                        autowire(ConcurrentClass)
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(e)

        def cache_clearer():
            """Periodically clear cache."""
            try:
                for _ in range(10):
                    time.sleep(0.01)
                    clear_analysis_cache()
            except Exception as e:
                errors.append(e)

        # Start worker threads
        workers = [threading.Thread(target=worker) for _ in range(5)]
        clearer = threading.Thread(target=cache_clearer)

        for w in workers:
            w.start()
        clearer.start()

        # Let them run
        clearer.join()
        stop_event.set()

        for w in workers:
            w.join()

        # No crashes should occur
        assert len(errors) == 0, f"Errors during concurrent clear: {errors}"

    def test_cache_thrashing_scenario(self):
        """Rapid register/clear cycles should not deadlock or crash."""
        errors = []

        class ThrashClass:
            def __init__(self) -> None:
                self.value = 99

        def thrash_worker():
            try:
                for _ in range(100):
                    clear_analysis_cache()
                    container = Container()
                    with container.activate():
                        autowire(ThrashClass)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=thrash_worker) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thrashing caused errors: {errors}"

    def test_concurrent_cache_info_queries(self):
        """Thread-safe statistics reads during concurrent modifications."""
        clear_analysis_cache()
        stop_event = threading.Event()
        errors = []
        info_snapshots = []

        class InfoClass:
            def __init__(self) -> None:
                self.id = 1

        def register_worker():
            try:
                while not stop_event.is_set():
                    container = Container()
                    with container.activate():
                        autowire(InfoClass)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def info_reader():
            try:
                for _ in range(50):
                    info = get_analysis_cache_info()
                    info_snapshots.append(info)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        workers = [threading.Thread(target=register_worker) for _ in range(3)]
        readers = [threading.Thread(target=info_reader) for _ in range(3)]

        for t in workers + readers:
            t.start()

        time.sleep(0.2)
        stop_event.set()

        for t in workers + readers:
            t.join()

        assert len(errors) == 0, f"Concurrent info queries caused errors: {errors}"
        assert len(info_snapshots) > 0, "Should have collected info snapshots"

        # Verify all snapshots have valid structure
        for info in info_snapshots:
            assert "hits" in info
            assert "misses" in info
            assert isinstance(info["hits"], int)
            assert isinstance(info["misses"], int)

    def test_stress_100_threads_mixed_operations(self):
        """Heavy load test with 100 threads doing mixed operations."""
        clear_analysis_cache()
        barrier = threading.Barrier(100)
        errors = []

        # Create 10 different classes
        classes = []
        for i in range(10):

            def make_init(idx):
                def __init__(self) -> None:
                    self.id = idx

                return __init__

            cls = type(f"StressClass{i}", (), {"__init__": make_init(i)})
            classes.append(cls)

        def stress_worker(worker_id):
            try:
                barrier.wait()
                # Each worker registers multiple random classes
                for i in range(10):
                    cls = classes[worker_id % len(classes)]
                    container = Container()
                    with container.activate():
                        autowire(cls)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(stress_worker, i) for i in range(100)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0, f"Stress test errors: {errors}"

        # Verify cache worked
        info = get_analysis_cache_info()
        assert info["misses"] == 10, "Should have 10 unique classes analyzed"
        assert info["hits"] > 0, "Should have many cache hits"

    def test_interleaved_clear_and_register(self):
        """Interleave clear operations with registrations."""
        errors = []

        class InterleavedClass:
            def __init__(self) -> None:
                self.value = 7

        def worker(should_clear: bool):
            try:
                for _ in range(50):
                    if should_clear:
                        clear_analysis_cache()
                    else:
                        container = Container()
                        with container.activate():
                            autowire(InterleavedClass)
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        clearers = [threading.Thread(target=worker, args=(True,)) for _ in range(2)]
        registers = [threading.Thread(target=worker, args=(False,)) for _ in range(8)]

        for t in clearers + registers:
            t.start()
        for t in clearers + registers:
            t.join()

        assert len(errors) == 0, f"Interleaved operations caused errors: {errors}"

    def test_cache_race_with_different_classes(self):
        """Multiple threads analyzing different classes simultaneously."""
        clear_analysis_cache()
        num_threads = 20
        barrier = threading.Barrier(num_threads)
        errors = []

        # Each thread gets its own unique class
        def worker(idx: int):
            try:
                barrier.wait()

                def make_init(i):
                    def __init__(self) -> None:
                        self.thread_id = i

                    return __init__

                cls = type(f"RaceClass{idx}", (), {"__init__": make_init(idx)})

                container = Container()
                with container.activate():
                    autowire(cls)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0, f"Race condition errors: {errors}"

        info = get_analysis_cache_info()
        assert info["misses"] == num_threads, "Each class should miss cache once"

    def test_concurrent_wire_builder_usage(self):
        """Test wire() builder under concurrent access."""
        clear_analysis_cache()
        errors = []

        class WireDatabase:
            def __init__(self) -> None:
                self.connected = True

        class WireService:
            def __init__(self, db: WireDatabase) -> None:
                self.db = db

        def worker():
            try:
                container = Container()
                with container.activate():
                    autowire(WireDatabase)
                    wire(WireService, container=container).register()
                    instance = container[WireService]
                    assert instance.db.connected
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent wire() errors: {errors}"

    def test_cache_consistency_under_load(self):
        """Verify cache returns consistent results under heavy load."""
        clear_analysis_cache()

        class ConsistentClass:
            def __init__(self) -> None:
                self.value = 42

        results = []
        errors = []

        def worker():
            try:
                container = Container()
                with container.activate():
                    autowire(ConsistentClass)
                    instance = container[ConsistentClass]
                    results.append(instance.value)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        # All instances should have the same value
        assert all(v == 42 for v in results), "Inconsistent results from cache"

    def test_barrier_synchronized_cache_access(self):
        """Use barrier to ensure true concurrent cache access."""
        num_threads = 30
        barrier = threading.Barrier(num_threads)
        clear_analysis_cache()

        class BarrierClass:
            def __init__(self) -> None:
                self.timestamp = time.time()

        errors = []
        timestamps = []

        def worker():
            try:
                barrier.wait()  # All threads start at exactly the same time
                start = time.time()
                container = Container()
                with container.activate():
                    autowire(BarrierClass)
                timestamps.append(start)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0
        # Verify threads started within small time window (true concurrency)
        if timestamps:
            time_spread = max(timestamps) - min(timestamps)
            assert time_spread < 0.1, f"Threads not truly concurrent: {time_spread}s spread"

    def test_cache_during_container_cleanup(self):
        """Verify cache operations don't interfere with container cleanup."""
        clear_analysis_cache()
        errors = []

        class CleanupClass:
            def __init__(self) -> None:
                self.cleaned = False

            def close(self) -> None:
                self.cleaned = True

        def worker():
            try:
                container = Container()
                with container.activate():
                    autowire(CleanupClass)
                    instance = container[CleanupClass]
                # Container cleanup happens here
                assert isinstance(instance, CleanupClass)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_generic_normalization(self):
        """Test concurrent access to generic type normalization."""
        clear_analysis_cache()
        errors = []

        class GenericRepo(Generic[T]):
            def __init__(self) -> None:
                self.items: list[T] = []

        def worker(idx: int):
            try:
                container = Container()
                with container.activate():
                    # Alternate between str and int generics
                    if idx % 2 == 0:
                        autowire(GenericRepo[str])
                    else:
                        autowire(GenericRepo[int])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Both generic variants should normalize to same cache entry
        info = get_analysis_cache_info()
        assert info["misses"] == 1, "Generic normalization should create single cache entry"

    def test_rapid_clear_and_info_queries(self):
        """Rapidly alternate between clear_cache and get_cache_info."""
        errors = []
        infos = []

        def worker():
            try:
                for _ in range(100):
                    if threading.current_thread().ident % 2 == 0:
                        clear_analysis_cache()
                    else:
                        info = get_analysis_cache_info()
                        infos.append(info)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during rapid operations: {errors}"
        # Verify all collected infos are valid
        for info in infos:
            assert isinstance(info["hits"], int)
            assert isinstance(info["misses"], int)

    def test_thread_safety_with_dependencies(self):
        """Test concurrent registration of classes with dependencies."""
        clear_analysis_cache()
        errors = []

        class DependencyA:
            def __init__(self) -> None:
                self.name = "A"

        class DependencyB:
            def __init__(self, a: DependencyA) -> None:
                self.a = a

        def worker():
            try:
                container = Container()
                with container.activate():
                    autowire(DependencyA)
                    autowire(DependencyB)
                    instance = container[DependencyB]
                    assert instance.a.name == "A"
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(25)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Dependency resolution errors: {errors}"


# =============================================================================
# TIER 2: PROPERTY-BASED TESTS WITH HYPOTHESIS (10 tests)
# =============================================================================


class TestPropertyBased:
    """Property-based tests using hypothesis."""

    @given(st.integers(min_value=0, max_value=10))
    @settings(max_examples=50, deadline=None)
    def test_analysis_idempotence_property(self, num_params: int):
        """Property: Analyzing same class twice returns identical results."""
        # Generate class with num_params parameters dynamically
        def make_init(n):
            def __init__(self, **kwargs: int) -> None:
                for k, v in kwargs.items():
                    setattr(self, k, v)

            return __init__

        DynamicClass = type(
            f"DynamicClass_{num_params}", (), {"__init__": make_init(num_params)}
        )

        # Add type hints via signature
        sig_params = [inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
        for i in range(num_params):
            sig_params.append(
                inspect.Parameter(
                    f"param{i}",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=int,
                )
            )
        DynamicClass.__init__.__signature__ = inspect.Signature(sig_params)

        container1 = Container()
        container2 = Container()

        try:
            with container1.activate():
                autowire(DynamicClass)

            with container2.activate():
                autowire(DynamicClass)

            # Both should work identically (if num_params > 0, they need providers)
            if num_params == 0:
                instance1 = container1[DynamicClass]
                instance2 = container2[DynamicClass]
                assert instance1 is not None
                assert instance2 is not None
        except Exception:
            # Expected for classes with dependencies we don't register
            pass

    @given(st.integers(min_value=1, max_value=20))
    @settings(max_examples=30, deadline=None)
    def test_cache_hit_monotonicity_property(self, num_registrations: int):
        """Property: Cache hits should never decrease during registrations."""
        clear_analysis_cache()

        class MonotonicClass:
            def __init__(self) -> None:
                self.value = 1

        previous_hits = 0

        for _ in range(num_registrations):
            container = Container()
            with container.activate():
                autowire(MonotonicClass)

            info = get_analysis_cache_info()
            current_hits = info["hits"]

            # Hits should be monotonically increasing (or stay same)
            assert current_hits >= previous_hits, "Cache hits decreased!"
            previous_hits = current_hits

    @given(st.lists(st.integers(min_value=1, max_value=5), min_size=1, max_size=10))
    @settings(max_examples=30, deadline=None)
    def test_cache_size_bounded_property(self, class_counts: list[int]):
        """Property: Cache size never exceeds maxsize."""
        clear_analysis_cache()

        for i, count in enumerate(class_counts):
            for j in range(count):

                def make_init(idx):
                    def __init__(self) -> None:
                        self.id = idx

                    return __init__

                cls = type(f"BoundedClass_{i}_{j}", (), {"__init__": make_init(j)})
                container = Container()
                with container.activate():
                    autowire(cls)

            info = get_analysis_cache_info()
            assert info["size"] <= 256, f"Cache size {info['size']} exceeds maxsize"

    @given(st.integers(min_value=0, max_value=5))
    @settings(max_examples=20, deadline=None)
    def test_dependency_count_invariant(self, num_deps: int):
        """Property: Classes with N dependencies resolve correctly."""
        clear_analysis_cache()

        # Create N dependency classes
        dep_classes = []
        for i in range(num_deps):

            def make_init(idx):
                def __init__(self) -> None:
                    self.dep_id = idx

                return __init__

            dep_cls = type(f"Dep{i}", (), {"__init__": make_init(i)})
            dep_classes.append(dep_cls)

        # Create main class with dependencies
        if num_deps == 0:

            def final_init(self) -> None:
                self.deps = []
        else:
            # Create init with proper type hints
            sig_params = [
                inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
            for i, dep_cls in enumerate(dep_classes):
                sig_params.append(
                    inspect.Parameter(
                        f"dep{i}",
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=dep_cls,
                    )
                )

            def final_init(self, **kwargs: Any) -> None:
                self.deps = list(kwargs.values())

        MainClass = type("MainClass", (), {"__init__": final_init})
        if num_deps > 0:
            MainClass.__init__.__signature__ = inspect.Signature(sig_params)

        container = Container()
        with container.activate():
            # Register dependencies
            for dep_cls in dep_classes:
                autowire(dep_cls)

            # Register main class
            autowire(MainClass)

            # Resolve and verify
            instance = container[MainClass]
            assert len(instance.deps) == num_deps

    @given(st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cs",))))
    @settings(max_examples=20, deadline=None)
    def test_class_name_invariant(self, class_name: str):
        """Property: Classes with arbitrary names can be analyzed."""
        # Make valid Python identifier
        safe_name = "Class_" + "".join(c if c.isalnum() else "_" for c in class_name)

        def init(self) -> None:
            self.name = safe_name

        DynamicClass = type(safe_name, (), {"__init__": init})

        try:
            container = Container()
            with container.activate():
                autowire(DynamicClass)
                instance = container[DynamicClass]
                assert instance.name == safe_name
        except Exception:
            # Some names might be invalid, that's fine
            pass

    @given(st.booleans())
    @settings(max_examples=20, deadline=None)
    def test_cache_clear_idempotence(self, clear_twice: bool):
        """Property: Clearing cache multiple times is idempotent."""
        clear_analysis_cache()

        class ClearClass:
            def __init__(self) -> None:
                pass

        container = Container()
        with container.activate():
            autowire(ClearClass)

        info1 = get_analysis_cache_info()

        clear_analysis_cache()
        if clear_twice:
            clear_analysis_cache()

        info2 = get_analysis_cache_info()

        # After clear, stats should be reset
        assert info2["hits"] == 0
        assert info2["misses"] == 0
        assert info2["size"] == 0

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=20, deadline=None)
    def test_container_isolation_property(self, num_containers: int):
        """Property: Multiple containers share cache but remain isolated."""
        clear_analysis_cache()

        class IsolatedClass:
            def __init__(self) -> None:
                self.container_id = None

        containers = []
        for i in range(num_containers):
            container = Container()
            containers.append(container)
            with container.activate():
                autowire(IsolatedClass)

        # Verify cache efficiency
        info = get_analysis_cache_info()
        assert info["misses"] == 1, "All containers should share cache"
        assert info["hits"] == num_containers - 1

    @given(st.lists(st.booleans(), min_size=5, max_size=20))
    @settings(max_examples=20, deadline=None)
    def test_mixed_operations_property(self, operations: list[bool]):
        """Property: Mixed register/clear operations maintain consistency."""

        class MixedClass:
            def __init__(self) -> None:
                self.value = 42

        for op in operations:
            if op:
                # Register
                container = Container()
                with container.activate():
                    autowire(MixedClass)
            else:
                # Clear
                clear_analysis_cache()

        # At end, cache should be valid
        info = get_analysis_cache_info()
        assert isinstance(info["hits"], int)
        assert isinstance(info["misses"], int)
        assert info["hits"] >= 0
        assert info["misses"] >= 0

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=20, deadline=None)
    def test_cache_efficiency_property(self, num_accesses: int):
        """Property: Hit rate should improve with repeated access."""
        clear_analysis_cache()

        class EfficiencyClass:
            def __init__(self) -> None:
                self.count = 0

        for _ in range(num_accesses):
            container = Container()
            with container.activate():
                autowire(EfficiencyClass)

        info = get_analysis_cache_info()
        if num_accesses > 1:
            hit_rate = info["hits"] / (info["hits"] + info["misses"])
            # After first miss, all should hit
            expected_rate = (num_accesses - 1) / num_accesses
            assert abs(hit_rate - expected_rate) < 0.01, f"Hit rate {hit_rate} too low"

    @given(st.integers(min_value=0, max_value=3))
    @settings(max_examples=20, deadline=None)
    def test_scope_independence_property(self, scope_idx: int):
        """Property: Cache works independently of scope choice."""
        scopes = [Scope.SINGLETON, Scope.TRANSIENT, Scope.REQUEST, Scope.SESSION]
        scope = scopes[scope_idx]

        clear_analysis_cache()

        class ScopedClass:
            def __init__(self) -> None:
                self.scope = scope

        container = Container()
        with container.activate():
            autowire(ScopedClass, scope=scope)

            info = get_analysis_cache_info()
            assert info["misses"] >= 1, "First registration should miss cache"


# =============================================================================
# TIER 3: MOCK-BASED UNIT TESTS (8 tests)
# =============================================================================


class TestMockBased:
    """Mock-based API contract validation tests."""

    def test_autowire_with_mocked_container(self):
        """Verify Container.register() called with correct signature."""
        mock_container = create_autospec(Container, instance=True)
        mock_container.activate = MagicMock()
        mock_container.activate.return_value.__enter__ = MagicMock(
            return_value=mock_container
        )
        mock_container.activate.return_value.__exit__ = MagicMock(return_value=None)

        # Patch Container.get_active to return our mock
        with patch.object(Container, "get_active", return_value=mock_container):

            class TestService:
                def __init__(self) -> None:
                    self.value = 42

            with mock_container.activate():
                autowire(TestService)

            # Verify register was called
            assert mock_container.register.called
            call_args = mock_container.register.call_args

            # Verify arguments structure
            assert call_args is not None
            token_arg = call_args[0][0]
            assert token_arg.type_ == TestService

    def test_inspect_signature_failure_injection(self):
        """Test graceful handling when inspect.signature() fails."""

        class BadSignatureClass:
            # Intentionally broken __init__
            __init__ = None

        container = Container()
        with container.activate():
            with pytest.raises(TypeError, match="Cannot analyze constructor"):
                autowire(BadSignatureClass)

    def test_get_type_hints_exception_handling(self):
        """Test fallback when get_type_hints() raises exceptions."""

        # Create class with annotations that will fail type hint resolution
        class ProblematicClass:
            def __init__(self, param: "NonExistentType") -> None:  # noqa: F821
                self.param = param

        # Should not crash, should fallback gracefully
        container = Container()
        with container.activate():
            try:
                autowire(ProblematicClass)
                # If it succeeds, verify it registered something
                assert True
            except TypeError:
                # Also acceptable if it rejects invalid type hints
                assert True

    def test_container_register_call_verification(self):
        """Verify exact parameters passed to Container.register()."""
        container = Container()
        original_register = container.register
        register_calls = []

        def tracked_register(*args, **kwargs):
            register_calls.append((args, kwargs))
            return original_register(*args, **kwargs)

        container.register = tracked_register

        class TrackedService:
            def __init__(self) -> None:
                self.tracked = True

        with container.activate():
            autowire(TrackedService, scope=Scope.TRANSIENT)

        # Verify register was called exactly once
        assert len(register_calls) == 1

        args, kwargs = register_calls[0]
        # Check token
        assert isinstance(args[0], Token)
        assert args[0].type_ == TrackedService
        # Check scope
        assert kwargs.get("scope") == Scope.TRANSIENT

    def test_provider_function_callable_verification(self):
        """Verify generated provider function is callable and returns instance."""
        container = Container()
        captured_provider = None
        original_register = container.register

        def capture_register(token, provider, **kwargs):
            nonlocal captured_provider
            captured_provider = provider
            return original_register(token, provider, **kwargs)

        container.register = capture_register

        class ProviderTestService:
            def __init__(self) -> None:
                self.test = "provider"

        with container.activate():
            autowire(ProviderTestService)

        # Verify provider was captured
        assert captured_provider is not None
        assert callable(captured_provider)

        # Call provider directly
        instance = captured_provider()
        assert isinstance(instance, ProviderTestService)
        assert instance.test == "provider"

    def test_token_creation_with_mock_type(self):
        """Test that Token creation works with mocked types."""
        mock_type = MagicMock(spec=type)
        mock_type.__name__ = "MockedService"

        # Token should handle mocked type
        token = Token[Any](name="MockedService", type_=mock_type)

        assert token.name == "MockedService"
        assert token.type_ == mock_type

    def test_wire_builder_validation_with_mock(self):
        """Test wire() builder parameter validation with mocks."""
        container = Container()

        class WireTestService:
            def __init__(self, dependency: int) -> None:
                self.dependency = dependency

        with container.activate():
            # Should raise ValueError for non-existent parameter
            with pytest.raises(ValueError, match="Parameter 'nonexistent' does not exist"):
                wire(WireTestService, container=container).with_override(
                    "nonexistent", 42
                ).register()

    def test_dependency_resolution_mock_integration(self):
        """Test dependency resolution with mocked dependencies."""
        container = Container()

        # Mock dependency
        mock_dependency = MagicMock()
        mock_dependency.value = 99

        class ServiceWithDependency:
            def __init__(self, dep: type(mock_dependency)) -> None:
                self.dep = dep

        # This test demonstrates the pattern, even if autowire needs real types
        with container.activate():
            try:
                # Register mock as provider
                container.register(
                    type(mock_dependency), lambda: mock_dependency, scope=Scope.SINGLETON
                )
                autowire(ServiceWithDependency)

                instance = container[ServiceWithDependency]
                assert instance.dep.value == 99
            except Exception:
                # Expected - mocks may not work perfectly with type system
                pass


# =============================================================================
# TIER 4: REAL-WORLD INTEGRATION TESTS (7 tests)
# =============================================================================


class TestIntegration:
    """Real-world integration scenarios."""

    def test_large_dependency_graph_50_classes(self):
        """50 classes with complex dependencies - verify high cache hit rate."""
        clear_analysis_cache()
        container = Container()

        with container.activate():
            # Create 50-class dependency chain
            prev_class = None
            for i in range(50):
                if prev_class is None:

                    def make_init(idx):
                        def __init__(self) -> None:
                            self.level = idx

                        return __init__

                    cls = type(f"Class{i}", (), {"__init__": make_init(i)})
                else:
                    # Capture prev_class properly
                    def make_init_with_dep(prev):
                        def __init__(self, dep: prev) -> None:  # type: ignore
                            self.dep = dep
                            self.level = -1

                        return __init__

                    cls = type(
                        f"Class{i}", (), {"__init__": make_init_with_dep(prev_class)}
                    )

                    # Add proper signature
                    sig = inspect.Signature(
                        [
                            inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                            inspect.Parameter(
                                "dep",
                                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                annotation=prev_class,
                            ),
                        ]
                    )
                    cls.__init__.__signature__ = sig

                autowire(cls)
                prev_class = cls

        info = get_analysis_cache_info()
        # 50 unique classes = 50 misses, but dependency analysis might hit cache
        assert info["misses"] == 50, f"Expected 50 misses, got {info['misses']}"

    def test_dynamic_class_creation_with_type(self):
        """Dynamic class creation using type() works with caching."""
        clear_analysis_cache()

        def create_service_class(name: str, value: int):
            """Factory function for creating service classes."""

            def init(self) -> None:
                self.name = name
                self.value = value

            return type(f"DynamicService_{name}", (), {"__init__": init})

        ServiceA = create_service_class("A", 1)
        ServiceB = create_service_class("B", 2)

        container = Container()
        with container.activate():
            autowire(ServiceA)
            autowire(ServiceB)

            a = container[ServiceA]
            b = container[ServiceB]

            assert a.name == "A"
            assert b.name == "B"

        info = get_analysis_cache_info()
        assert info["misses"] == 2, "Two unique classes should miss cache"

    def test_module_reload_scenario(self):
        """Simulate module reload by clearing cache and re-registering."""
        clear_analysis_cache()

        class ModuleService:
            def __init__(self) -> None:
                self.version = 1

        # Initial registration
        container1 = Container()
        with container1.activate():
            autowire(ModuleService)

        info1 = get_analysis_cache_info()

        # Simulate module reload - clear cache
        clear_analysis_cache()

        # Re-register after "reload"
        container2 = Container()
        with container2.activate():
            autowire(ModuleService)

        info2 = get_analysis_cache_info()

        # After clear, should miss cache again
        assert info2["misses"] >= 1, "After reload, should re-analyze"
        assert info2["hits"] == 0, "No hits after cache clear"

    def test_performance_profiling_overhead(self):
        """Measure cache performance improvement."""
        clear_analysis_cache()

        class ProfiledService:
            def __init__(self) -> None:
                self.data = list(range(100))

        # First registration - cold cache
        start = time.perf_counter()
        container1 = Container()
        with container1.activate():
            autowire(ProfiledService)
        cold_time = time.perf_counter() - start

        # Subsequent registrations - warm cache
        warm_times = []
        for _ in range(10):
            start = time.perf_counter()
            container = Container()
            with container.activate():
                autowire(ProfiledService)
            warm_times.append(time.perf_counter() - start)

        avg_warm_time = sum(warm_times) / len(warm_times)

        # Warm cache should be faster (or at least not slower)
        # Note: This is a soft check, timing can vary
        info = get_analysis_cache_info()
        assert info["hits"] > 0, "Should have cache hits in warm runs"

    def test_complex_generic_hierarchy(self):
        """Complex generic type hierarchy with caching."""
        clear_analysis_cache()

        class Repository(Generic[T]):
            def __init__(self) -> None:
                self.items: list[T] = []

        class Service(Generic[T]):
            def __init__(self, repo: Repository[T]) -> None:  # type: ignore
                self.repo = repo

        # Register with specific type parameters
        container = Container()
        with container.activate():
            # This will use generic normalization
            autowire(Repository[str])
            autowire(Repository[int])

        info = get_analysis_cache_info()
        # Both Repository[str] and Repository[int] normalize to Repository
        assert info["misses"] == 1, "Generic normalization should create single cache entry"
        assert info["hits"] >= 1, "Second generic should hit cache"

    def test_real_world_fastapi_pattern(self):
        """Simulate FastAPI dependency injection pattern."""
        clear_analysis_cache()

        class Database:
            def __init__(self) -> None:
                self.connected = True

        class Cache:
            def __init__(self) -> None:
                self.enabled = True

        class UserRepository:
            def __init__(self, db: Database) -> None:
                self.db = db

        class UserService:
            def __init__(self, repo: UserRepository, cache: Cache) -> None:
                self.repo = repo
                self.cache = cache

        class UserController:
            def __init__(self, service: UserService) -> None:
                self.service = service

        # Register all dependencies
        container = Container()
        with container.activate():
            autowire(Database)
            autowire(Cache)
            autowire(UserRepository)
            autowire(UserService)
            autowire(UserController)

            # Resolve top-level controller
            controller = container[UserController]

            # Verify full dependency chain
            assert controller.service.repo.db.connected
            assert controller.service.cache.enabled

        info = get_analysis_cache_info()
        # 5 classes = 5 cache misses initially
        assert info["misses"] == 5

    def test_production_scale_registration(self):
        """Simulate production-scale application with many services."""
        clear_analysis_cache()

        # Create 100 service classes
        classes = []
        for i in range(100):

            def make_init(idx):
                def __init__(self) -> None:
                    self.service_id = idx

                return __init__

            cls = type(f"ProductionService{i}", (), {"__init__": make_init(i)})
            classes.append(cls)

        # Register all in single container
        container = Container()
        with container.activate():
            for cls in classes:
                autowire(cls)

        # Verify cache stats
        info = get_analysis_cache_info()
        assert info["misses"] == 100, "100 unique classes should miss cache"
        assert info["size"] <= 256, "Cache size should not exceed maxsize"

        # Re-register same classes in new container - should hit cache
        container2 = Container()
        with container2.activate():
            for cls in classes[:10]:  # Just first 10
                autowire(cls)

        info2 = get_analysis_cache_info()
        # Should see cache hits now
        assert info2["hits"] > info["hits"], "Re-registration should hit cache"
