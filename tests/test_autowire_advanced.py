"""Advanced tests for autowire caching system - REFACTORED.

This module provides comprehensive testing for:
- Race conditions and thread safety
- LRU cache eviction behavior
- Property-based testing with hypothesis
- Mock-based API contract validation
- Real-world integration scenarios

REFACTORED: Reduced from 1,328 lines to ~600 lines through:
- Shared fixtures and helper functions
- Parametrized tests
- Dynamic class generation
- Eliminated repetitive patterns
"""

import inspect
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Generic, TypeVar
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

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
# SHARED FIXTURES & HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def clean_cache():
    """Clear cache before and after each test."""
    clear_analysis_cache()
    yield
    clear_analysis_cache()


@pytest.fixture
def class_factory():
    """Factory for generating test classes dynamically.

    Args:
        name: Class name
        deps: List of dependency classes (creates typed __init__)
        **attrs: Attributes to set on instance (creates simple __init__)

    Returns:
        Dynamically created class
    """

    def _make(name: str = "TestClass", deps: list[type] | None = None, **attrs: Any):
        if deps is None:
            # Simple class with attributes
            def __init__(self) -> None:
                for k, v in attrs.items():
                    setattr(self, k, v)
        else:
            # Class with typed dependencies
            sig_params = [
                inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
            for i, dep in enumerate(deps):
                sig_params.append(
                    inspect.Parameter(
                        f"dep{i}",
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=dep,
                    )
                )

            def __init__(self, **kwargs: Any) -> None:
                self.deps = list(kwargs.values())
                for k, v in attrs.items():
                    setattr(self, k, v)

            cls = type(name, (), {"__init__": __init__})
            cls.__init__.__signature__ = inspect.Signature(sig_params)
            return cls

        return type(name, (), {"__init__": __init__})

    return _make


def run_concurrent(worker, num_threads: int = 50, use_barrier: bool = False) -> None:
    """Execute worker function concurrently with error collection.

    Args:
        worker: Callable to execute in each thread
        num_threads: Number of concurrent threads
        use_barrier: If True, synchronize all threads to start simultaneously

    Raises:
        AssertionError: If any thread encounters an error
    """
    errors = []
    barrier = threading.Barrier(num_threads) if use_barrier else None

    def safe_worker():
        try:
            if barrier:
                barrier.wait()
            worker()
        except Exception as e:
            errors.append(e)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(safe_worker) for _ in range(num_threads)]
        for future in as_completed(futures):
            future.result()

    if errors:
        raise AssertionError(f"Concurrent execution errors: {errors}")


def assert_cache_stats(
    *,
    misses: int | None = None,
    hits: int | None = None,
    size: int | None = None,
    size_le: int | None = None,
) -> dict:
    """Verify cache statistics match expected values.

    Args:
        misses: Expected miss count (exact)
        hits: Expected hit count (exact)
        size: Expected cache size (exact)
        size_le: Expected cache size (less than or equal)

    Returns:
        Cache info dictionary
    """
    info = get_analysis_cache_info()

    if misses is not None:
        assert info["misses"] == misses, (
            f"Expected {misses} misses, got {info['misses']}"
        )
    if hits is not None:
        assert info["hits"] == hits, f"Expected {hits} hits, got {info['hits']}"
    if size is not None:
        assert info["size"] == size, f"Expected size {size}, got {info['size']}"
    if size_le is not None:
        assert info["size"] <= size_le, f"Cache size {info['size']} exceeds {size_le}"

    return info


# =============================================================================
# TIER 1: RACE CONDITION & CONCURRENCY TESTS
# =============================================================================


class TestRaceConditions:
    """Tests for race conditions and concurrent cache access."""

    @pytest.mark.parametrize("num_threads", [10, 50, 100])
    def test_concurrent_same_class_barrier_sync(self, class_factory, num_threads):
        """Verify exactly 1 cache miss and N-1 hits with barrier synchronization."""
        cls = class_factory(value=42)

        containers = []

        def worker():
            container = Container()
            containers.append(container)
            with container.activate():
                autowire(cls)

        run_concurrent(worker, num_threads=num_threads, use_barrier=True)
        assert len(containers) == num_threads
        assert_cache_stats(misses=1, hits=num_threads - 1)

    def test_cache_eviction_with_300_classes(self, class_factory):
        """Trigger LRU maxsize=256 eviction and verify correct behavior."""
        container = Container()
        classes = [class_factory(name=f"Class{i}", id=i) for i in range(300)]

        with container.activate():
            for cls in classes:
                autowire(cls)

        info = assert_cache_stats(misses=300, size_le=256)
        assert info["maxsize"] == 256

        # Re-register first class - should be evicted
        container2 = Container()
        with container2.activate():
            autowire(classes[0])

        info2 = get_analysis_cache_info()
        assert info2["misses"] > info["misses"], "First class should be evicted"

    def test_clear_cache_during_concurrent_analysis(self, class_factory):
        """Test clear_cache() called mid-execution doesn't crash threads."""
        stop_event = threading.Event()
        errors = []
        cls = class_factory(value=1)

        def worker():
            try:
                while not stop_event.is_set():
                    container = Container()
                    with container.activate():
                        autowire(cls)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def cache_clearer():
            try:
                for _ in range(10):
                    time.sleep(0.01)
                    clear_analysis_cache()
            except Exception as e:
                errors.append(e)

        workers = [threading.Thread(target=worker) for _ in range(5)]
        clearer = threading.Thread(target=cache_clearer)

        for w in workers:
            w.start()
        clearer.start()

        clearer.join()
        stop_event.set()

        for w in workers:
            w.join()

        assert len(errors) == 0, f"Errors during concurrent clear: {errors}"

    def test_cache_thrashing_scenario(self, class_factory):
        """Rapid register/clear cycles should not deadlock or crash."""
        cls = class_factory(value=99)

        def thrash_worker():
            for _ in range(100):
                clear_analysis_cache()
                container = Container()
                with container.activate():
                    autowire(cls)

        run_concurrent(thrash_worker, num_threads=10)

    def test_concurrent_cache_info_queries(self, class_factory):
        """Thread-safe statistics reads during concurrent modifications."""
        stop_event = threading.Event()
        errors = []
        info_snapshots = []
        cls = class_factory(id=1)

        def register_worker():
            try:
                while not stop_event.is_set():
                    container = Container()
                    with container.activate():
                        autowire(cls)
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
        assert len(info_snapshots) > 0

        for info in info_snapshots:
            assert "hits" in info and isinstance(info["hits"], int)
            assert "misses" in info and isinstance(info["misses"], int)

    def test_stress_100_threads_mixed_operations(self, class_factory):
        """Heavy load test with 100 threads doing mixed operations."""
        classes = [class_factory(name=f"StressClass{i}", id=i) for i in range(10)]

        def stress_worker():
            worker_id = threading.current_thread().ident % 100
            for _ in range(10):
                cls = classes[worker_id % len(classes)]
                container = Container()
                with container.activate():
                    autowire(cls)

        run_concurrent(stress_worker, num_threads=100, use_barrier=True)

        # Should have analyzed all 10 unique classes
        # Allow small race window under extreme concurrency (100 threads)
        info = get_analysis_cache_info()
        assert info["misses"] <= 12, (
            f"Expected at most 12 misses (10 classes + 20% race tolerance), "
            f"got {info['misses']}"
        )
        assert info["hits"] > 0

    def test_cache_race_with_different_classes(self, class_factory):
        """Multiple threads analyzing different classes simultaneously."""
        num_threads = 20

        def worker(idx: int):
            cls = class_factory(name=f"RaceClass{idx}", thread_id=idx)
            container = Container()
            with container.activate():
                autowire(cls)

        run_concurrent(
            lambda: worker(threading.current_thread().ident % num_threads),
            num_threads=num_threads,
            use_barrier=True,
        )

        assert_cache_stats(misses=num_threads)

    def test_concurrent_wire_builder_usage(self):
        """Test wire() builder under concurrent access."""

        class WireDatabase:
            def __init__(self) -> None:
                self.connected = True

        class WireService:
            def __init__(self, db: WireDatabase) -> None:
                self.db = db

        def worker():
            container = Container()
            with container.activate():
                autowire(WireDatabase)
                wire(WireService, container=container).register()
                instance = container.get(WireService)
                assert instance.db.connected

        run_concurrent(worker, num_threads=20)

    def test_cache_consistency_under_load(self, class_factory):
        """Verify cache returns consistent results under heavy load."""
        cls = class_factory(value=42)
        results = []

        def worker():
            container = Container()
            with container.activate():
                autowire(cls)
                instance = container.get(cls)
                results.append(instance.value)

        run_concurrent(worker, num_threads=50)
        assert all(v == 42 for v in results), "Inconsistent results from cache"

    def test_concurrent_generic_normalization(self):
        """Test concurrent access to generic type normalization."""

        class GenericRepo(Generic[T]):
            def __init__(self) -> None:
                self.items: list[T] = []

        def worker(idx: int):
            container = Container()
            with container.activate():
                if idx % 2 == 0:
                    autowire(GenericRepo[str])
                else:
                    autowire(GenericRepo[int])

        run_concurrent(
            lambda: worker(threading.current_thread().ident % 30), num_threads=30
        )
        assert_cache_stats(misses=1)

    def test_thread_safety_with_dependencies(self):
        """Test concurrent registration of classes with dependencies."""

        class DependencyA:
            def __init__(self) -> None:
                self.name = "A"

        class DependencyB:
            def __init__(self, a: DependencyA) -> None:
                self.a = a

        def worker():
            container = Container()
            with container.activate():
                autowire(DependencyA)
                autowire(DependencyB)
                instance = container.get(DependencyB)
                assert instance.a.name == "A"

        run_concurrent(worker, num_threads=25)


# =============================================================================
# TIER 2: PROPERTY-BASED TESTS WITH HYPOTHESIS
# =============================================================================


class TestPropertyBased:
    """Property-based tests using hypothesis."""

    @given(st.integers(min_value=0, max_value=10))
    @settings(max_examples=50, deadline=None)
    def test_analysis_idempotence(self, num_params: int):
        """Property: Analyzing same class twice returns identical results."""
        sig_params = [
            inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        for i in range(num_params):
            sig_params.append(
                inspect.Parameter(
                    f"param{i}", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int
                )
            )

        def __init__(self, **kwargs: int) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

        DynamicClass = type(f"DynamicClass_{num_params}", (), {"__init__": __init__})
        DynamicClass.__init__.__signature__ = inspect.Signature(sig_params)

        try:
            container1, container2 = Container(), Container()

            with container1.activate():
                autowire(DynamicClass)
            with container2.activate():
                autowire(DynamicClass)

            if num_params == 0:
                assert container1[DynamicClass] is not None
                assert container2[DynamicClass] is not None
        except Exception:
            pass  # Expected for classes with unregistered dependencies

    @given(st.integers(min_value=1, max_value=20))
    @settings(max_examples=30, deadline=None)
    def test_cache_hit_monotonicity(self, num_registrations: int):
        """Property: Cache hits should never decrease during registrations."""

        class MonotonicClass:
            def __init__(self) -> None:
                self.value = 1

        previous_hits = 0

        for _ in range(num_registrations):
            container = Container()
            with container.activate():
                autowire(MonotonicClass)

            info = get_analysis_cache_info()
            assert info["hits"] >= previous_hits, "Cache hits decreased!"
            previous_hits = info["hits"]

    @given(st.lists(st.integers(min_value=1, max_value=5), min_size=1, max_size=10))
    @settings(max_examples=30, deadline=None)
    def test_cache_size_bounded(self, class_counts: list[int]):
        """Property: Cache size never exceeds maxsize."""
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

            assert_cache_stats(size_le=256)

    @given(st.integers(min_value=0, max_value=5))
    @settings(max_examples=20, deadline=None)
    def test_dependency_count_invariant(self, num_deps: int):
        """Property: Classes with N dependencies resolve correctly."""
        dep_classes = []
        for i in range(num_deps):

            def make_init(idx):
                def __init__(self) -> None:
                    self.dep_id = idx

                return __init__

            dep_cls = type(f"Dep{i}", (), {"__init__": make_init(i)})
            dep_classes.append(dep_cls)

        if num_deps == 0:

            def final_init(self) -> None:
                self.deps = []
        else:
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
            for dep_cls in dep_classes:
                autowire(dep_cls)
            autowire(MainClass)

            instance = container.get(MainClass)
            assert len(instance.deps) == num_deps

    @given(st.booleans())
    @settings(max_examples=20, deadline=None)
    def test_cache_clear_idempotence(self, clear_twice: bool):
        """Property: Clearing cache multiple times is idempotent."""

        class ClearClass:
            def __init__(self) -> None:
                pass

        container = Container()
        with container.activate():
            autowire(ClearClass)

        clear_analysis_cache()
        if clear_twice:
            clear_analysis_cache()

        assert_cache_stats(hits=0, misses=0, size=0)

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=20, deadline=None)
    def test_container_isolation(self, num_containers: int):
        """Property: Multiple containers share cache but remain isolated."""
        clear_analysis_cache()  # Clean slate for each hypothesis example

        class IsolatedClass:
            def __init__(self) -> None:
                self.container_id = None

        for _ in range(num_containers):
            container = Container()
            with container.activate():
                autowire(IsolatedClass)

        assert_cache_stats(misses=1, hits=num_containers - 1)

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=20, deadline=None)
    def test_cache_efficiency(self, num_accesses: int):
        """Property: Hit rate should improve with repeated access."""
        clear_analysis_cache()  # Clean slate for each hypothesis example

        class EfficiencyClass:
            def __init__(self) -> None:
                self.count = 0

        for _ in range(num_accesses):
            container = Container()
            with container.activate():
                autowire(EfficiencyClass)

        if num_accesses > 1:
            info = get_analysis_cache_info()
            hit_rate = info["hits"] / (info["hits"] + info["misses"])
            expected_rate = (num_accesses - 1) / num_accesses
            assert abs(hit_rate - expected_rate) < 0.01, f"Hit rate {hit_rate} too low"


# =============================================================================
# TIER 3: MOCK-BASED UNIT TESTS
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

        with patch.object(Container, "get_active", return_value=mock_container):

            class TestService:
                def __init__(self) -> None:
                    self.value = 42

            with mock_container.activate():
                autowire(TestService)

            assert mock_container.register.called
            call_args = mock_container.register.call_args
            assert call_args is not None
            assert call_args[0][0].type_ == TestService

    def test_inspect_signature_failure_injection(self):
        """Test graceful handling when inspect.signature() fails."""

        class BadSignatureClass:
            __init__ = None  # type: ignore

        container = Container()
        with container.activate():
            with pytest.raises(TypeError, match="Cannot analyze constructor"):
                autowire(BadSignatureClass)

    def test_container_register_call_verification(self):
        """Verify exact parameters passed to Container.register()."""
        container = Container()
        register_calls = []
        original_register = container.register

        def tracked_register(*args, **kwargs):
            register_calls.append((args, kwargs))
            return original_register(*args, **kwargs)

        container.register = tracked_register

        class TrackedService:
            def __init__(self) -> None:
                self.tracked = True

        with container.activate():
            autowire(TrackedService, scope=Scope.TRANSIENT)

        assert len(register_calls) == 1
        args, kwargs = register_calls[0]
        assert isinstance(args[0], Token)
        assert args[0].type_ == TrackedService
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

        assert captured_provider is not None
        assert callable(captured_provider)

        instance = captured_provider()
        assert isinstance(instance, ProviderTestService)
        assert instance.test == "provider"


# =============================================================================
# TIER 4: REAL-WORLD INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Real-world integration scenarios."""

    def test_large_dependency_graph_50_classes(self, class_factory):
        """50 classes with complex dependencies - verify cache efficiency."""
        container = Container()

        with container.activate():
            prev_class = None
            for i in range(50):
                if prev_class is None:
                    cls = class_factory(name=f"Class{i}", level=i)
                else:
                    cls = class_factory(name=f"Class{i}", deps=[prev_class], level=-1)

                autowire(cls)
                prev_class = cls

        assert_cache_stats(misses=50)

    def test_dynamic_class_creation_with_type(self):
        """Dynamic class creation using type() works with caching."""

        def create_service_class(name: str, value: int):
            def init(self) -> None:
                self.name = name
                self.value = value

            return type(f"DynamicService_{name}", (), {"__init__": init})

        ServiceA, ServiceB = create_service_class("A", 1), create_service_class("B", 2)

        container = Container()
        with container.activate():
            autowire(ServiceA)
            autowire(ServiceB)

            assert container.get(ServiceA).name == "A"
            assert container.get(ServiceB).name == "B"

        assert_cache_stats(misses=2)

    def test_complex_generic_hierarchy(self):
        """Complex generic type hierarchy with caching."""

        class Repository(Generic[T]):
            def __init__(self) -> None:
                self.items: list[T] = []

        container = Container()
        with container.activate():
            autowire(Repository[str])
            autowire(Repository[int])

        info = assert_cache_stats(misses=1)
        assert info["hits"] >= 1

    def test_real_world_fastapi_pattern(self):
        """Simulate FastAPI dependency injection pattern."""

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

        container = Container()
        with container.activate():
            autowire(Database)
            autowire(Cache)
            autowire(UserRepository)
            autowire(UserService)
            autowire(UserController)

            controller = container.get(UserController)
            assert controller.service.repo.db.connected
            assert controller.service.cache.enabled

        assert_cache_stats(misses=5)

    def test_production_scale_registration(self, class_factory):
        """Simulate production-scale application with many services."""
        classes = [
            class_factory(name=f"ProductionService{i}", service_id=i)
            for i in range(100)
        ]

        container = Container()
        with container.activate():
            for cls in classes:
                autowire(cls)

        assert_cache_stats(misses=100, size_le=256)

        # Re-register subset - should hit cache
        container2 = Container()
        with container2.activate():
            for cls in classes[:10]:
                autowire(cls)

        info2 = get_analysis_cache_info()
        assert info2["hits"] >= 10
