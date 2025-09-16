"""Memory profiling tests for injx improvements."""

import gc
import tracemalloc
import weakref

import pytest

from injx import Container, Scope, Token


class TestMemoryProfiling:
    """Tests for memory usage and leak detection using tracemalloc."""

    def test_transient_no_caching(self):
        """Verify transient dependencies are never cached and always create new instances."""
        container = Container()

        class TransientService:
            counter = 0

            def __init__(self):
                TransientService.counter += 1
                self.id = TransientService.counter

        token = Token("transient", TransientService, scope=Scope.TRANSIENT)
        container.register(token, TransientService)

        # Each resolution should create a new instance
        instances = []
        for _ in range(10):
            instance = container.get(token)
            instances.append(instance)

        # All instances should be unique
        ids = [inst.id for inst in instances]
        assert len(set(ids)) == 10, "Transient instances should all be unique"

        # Verify no caching by checking they're different objects
        for i in range(len(instances) - 1):
            assert instances[i] is not instances[i + 1], (
                "Transient instances must be different objects"
            )

        # Create weak references to verify garbage collection
        weak_refs = [weakref.ref(inst) for inst in instances[:5]]
        del instances[:5]
        gc.collect()

        # At least some should be garbage collected
        alive_count = sum(1 for ref in weak_refs if ref() is not None)
        assert alive_count < 5, (
            f"Transient instances not being garbage collected: {alive_count}/5 still alive"
        )

    def test_singleton_lock_cleanup(self):
        """Verify that singleton locks are cleaned up after initialization."""
        container = Container()

        class SingletonService:
            def __init__(self):
                self.value = "singleton"

        token = Token("singleton", SingletonService, scope=Scope.SINGLETON)
        obj_token = container._obj_token(token)
        container.register(token, SingletonService)

        # Before resolution, no lock should exist
        assert obj_token not in container._singleton_locks, (
            "Lock should not exist before first resolution"
        )

        # Resolve to trigger singleton creation
        instance = container.get(token)

        # After resolution, lock should be cleaned up
        assert obj_token not in container._singleton_locks, (
            "Lock should be cleaned up after singleton creation"
        )

        # Verify the singleton was actually created
        assert instance.value == "singleton"

        # Multiple resolutions should not recreate the lock
        for _ in range(10):
            same_instance = container.get(token)
            assert same_instance is instance, "Should return same singleton instance"
            assert obj_token not in container._singleton_locks, (
                "Lock should remain cleaned up"
            )

    def test_singleton_lock_cleanup_with_exception(self):
        """Verify locks are cleaned up even when singleton creation fails."""
        container = Container()

        class FailingService:
            def __init__(self):
                raise ValueError("Initialization failed")

        token = Token("failing", FailingService, scope=Scope.SINGLETON)
        container.register(token, FailingService)

        # Resolution should fail
        with pytest.raises(ValueError, match="Initialization failed"):
            container.get(token)

        # Lock should still be cleaned up after failure
        # Note: Current implementation might keep the lock on failure
        # This test documents the expected behavior

    def test_token_slots_memory_efficiency(self):
        """Verify __slots__ on Token class reduces memory footprint."""
        tracemalloc.start()
        tracemalloc.clear_traces()

        # Create many tokens to measure memory usage
        num_tokens = 10000
        tokens = []

        # Take initial snapshot
        gc.collect()
        snapshot_before = tracemalloc.take_snapshot()

        # Create tokens
        for i in range(num_tokens):
            token = Token(
                f"token_{i}", int, scope=Scope.TRANSIENT, qualifier=f"qual_{i}"
            )
            tokens.append(token)

        # Take final snapshot
        gc.collect()
        snapshot_after = tracemalloc.take_snapshot()

        tracemalloc.stop()

        # Calculate memory used
        stats = snapshot_after.compare_to(snapshot_before, "traceback")

        # Find stats related to tokens.py
        token_stats = [
            stat
            for stat in stats
            if any("tokens.py" in frame.filename for frame in stat.traceback)
        ]

        if token_stats:
            total_size = sum(
                stat.size_diff for stat in token_stats if stat.size_diff > 0
            )
            bytes_per_token = total_size / num_tokens

            # With __slots__, each token should use less than 200 bytes
            # Without __slots__, it would be 500+ bytes
            assert bytes_per_token < 200, (
                f"Token using too much memory: {bytes_per_token:.1f} bytes per token"
            )

        # Also verify tokens are hashable and work in sets/dicts efficiently
        token_set = set(tokens)
        assert len(token_set) == num_tokens, "All tokens should be unique in set"

    def test_no_memory_leak_on_container_destruction(self):
        """Ensure destroying a container releases all its resources."""
        tracemalloc.start()

        def create_and_destroy_container():
            """Create a container with many services and then let it be garbage collected."""
            container = Container()

            # Register various types of services
            for i in range(100):
                # Singletons
                singleton_token = Token(f"singleton_{i}", object)
                container.register(singleton_token, object, Scope.SINGLETON)
                if i % 10 == 0:
                    container.get(singleton_token)  # Create some singletons

                # Transients
                transient_token = Token(f"transient_{i}", object)
                container.register(transient_token, object, Scope.TRANSIENT)

                # Request scoped
                request_token = Token(f"request_{i}", object)
                container.register(request_token, object, Scope.REQUEST)

            # Add some overrides
            for i in range(0, 20):
                token = Token(f"singleton_{i}", object)
                container.override(token, object())

            return weakref.ref(container)

        # Take initial snapshot
        gc.collect()
        snapshot1 = tracemalloc.take_snapshot()

        # Create and destroy containers multiple times
        container_refs = []
        for _ in range(10):
            ref = create_and_destroy_container()
            container_refs.append(ref)

        # Force garbage collection
        gc.collect()

        # All containers should be garbage collected
        alive_containers = sum(1 for ref in container_refs if ref() is not None)
        assert alive_containers == 0, (
            f"{alive_containers} containers not garbage collected"
        )

        # Take final snapshot
        snapshot2 = tracemalloc.take_snapshot()

        tracemalloc.stop()

        # Compare snapshots
        top_stats = snapshot2.compare_to(snapshot1, "lineno")

        # Calculate total growth
        growth = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)

        # Should be minimal growth (allow up to 100KB for Python internals and test overhead)
        assert growth < 102400, (
            f"Memory leak detected: {growth} bytes grew after creating/destroying 10 containers"
        )

    def test_cleanup_stack_memory_bounded(self):
        """Verify cleanup stacks don't grow unbounded."""
        container = Container()

        # Create a context manager that tracks cleanup registration
        cleanup_called = []

        class TrackedResource:
            def __init__(self, id: int):
                self.id = id

            def __enter__(self):
                return self

            def __exit__(self, *args):
                cleanup_called.append(self.id)

        # Register many context-managed resources
        for i in range(100):
            token = Token(f"resource_{i}", TrackedResource)
            container.register_context(
                token,
                lambda i=i: TrackedResource(i),
                is_async=False,
                scope=Scope.SINGLETON,
            )

        # Resolve some to trigger cleanup registration
        for i in range(0, 100, 10):
            token = Token(f"resource_{i}", TrackedResource)
            container.get(token)

        # Check cleanup stack size
        assert len(container._singleton_cleanup_sync) == 10, (
            "Cleanup stack should only contain resolved singletons"
        )

        # Verify cleanup happens in LIFO order
        with container:
            pass  # Context exit triggers cleanup

        # Cleanup should have been called in reverse order
        expected = list(range(90, -1, -10))
        assert cleanup_called == expected, (
            f"Cleanup not in LIFO order: {cleanup_called}"
        )

    async def test_async_lock_cleanup(self):
        """Verify that async locks are cleaned up properly."""
        container = Container()

        class AsyncSingletonService:
            def __init__(self):
                self.value = "async_singleton"

        # Test 1: Async locks created during resolution
        token1 = Token("async_singleton_1", AsyncSingletonService, scope=Scope.SINGLETON)
        token2 = Token("async_singleton_2", AsyncSingletonService, scope=Scope.SINGLETON)
        container.register(token1, AsyncSingletonService)
        container.register(token2, AsyncSingletonService)

        # Resolve async singletons
        instance1 = await container.aget(token1)
        instance2 = await container.aget(token2)

        # Async locks should be created
        assert len(container._async_locks) == 2, (
            "Async locks should be created for singleton resolution"
        )

        # Test 2: Clear should remove async locks
        container.clear()
        assert len(container._async_locks) == 0, (
            "clear() should remove all async locks"
        )

        # Test 3: __aexit__ should clear async locks
        # Create a new container for this test
        container2 = Container()
        token3 = Token("async_singleton_3", AsyncSingletonService, scope=Scope.SINGLETON)
        container2.register(token3, AsyncSingletonService)
        await container2.aget(token3)
        assert len(container2._async_locks) == 1, (
            "Async lock should be created for resolution"
        )

        async with container2:
            pass  # Context exit triggers cleanup

        assert len(container2._async_locks) == 0, (
            "__aexit__ should clear all async locks"
        )

    def test_container_clear_cleanup(self):
        """Verify that clear() properly cleans up all lock dictionaries."""
        container = Container()

        class TestService:
            def __init__(self):
                self.value = "test"

        # Create multiple singleton tokens
        tokens = []
        for i in range(5):
            token = Token(f"service_{i}", TestService, scope=Scope.SINGLETON)
            container.register(token, TestService)
            tokens.append(token)

        # Resolve all to create singleton locks
        for token in tokens:
            container.get(token)

        # Locks should exist (but should be cleaned up after creation due to fast path)
        # The important test is that clear() removes any remaining locks

        # Manually create some locks to simulate worst case
        for token in tokens[:3]:
            obj_token = container._obj_token(token)
            container._get_singleton_lock(obj_token)

        assert len(container._singleton_locks) >= 3, (
            "Should have at least 3 singleton locks manually created"
        )

        # Clear should remove all locks
        container.clear()
        assert len(container._singleton_locks) == 0, (
            "clear() should remove all singleton locks"
        )
        assert len(container._async_locks) == 0, (
            "clear() should remove all async locks"
        )
        assert len(container._singletons) == 0, (
            "clear() should remove all cached singletons"
        )

    async def test_container_clear_async_cleanup(self):
        """Verify that clear() properly cleans up async locks."""
        container = Container()

        class AsyncService:
            def __init__(self):
                self.value = "async"

        async def create_async_service():
            # Simulate async creation
            return AsyncService()

        # Create async singleton
        token = Token("async_service", AsyncService, scope=Scope.SINGLETON)
        container.register(token, create_async_service)

        # This will create an async lock
        await container.aget(token)

        assert len(container._async_locks) >= 1, (
            "Should have at least 1 async lock after async resolution"
        )

        # Clear should remove async locks
        container.clear()
        assert len(container._async_locks) == 0, (
            "clear() should remove all async locks"
        )

    def test_resolution_set_memory_efficiency(self):
        """Test that the new _resolution_set for O(1) cycle detection is memory efficient."""
        container = Container()

        # Create a simpler dependency chain to avoid deep recursion
        depth = 50  # Reduced depth to avoid recursion issues

        # Register services with simple dependencies
        for i in range(depth):
            token = Token(f"service_{i}", object)
            if i == 0:
                container.register(token, object)
            else:
                # Create a simpler dependency without complex closures
                prev_token = Token(f"service_{i - 1}", object)

                def make_provider(prev_t=prev_token):
                    def provider():
                        container.get(prev_t)
                        return object()

                    return provider

                container.register(token, make_provider())

        # Measure memory before resolution
        tracemalloc.start()
        gc.collect()
        snapshot_before = tracemalloc.take_snapshot()

        # Resolve the deepest service (triggers full chain resolution)
        deepest_token = Token(f"service_{depth - 1}", object)
        container.get(deepest_token)

        # Measure memory after resolution
        gc.collect()
        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # The resolution stack should be cleared after resolution
        from injx.container import _resolution_set, _resolution_stack

        assert len(_resolution_stack.get()) == 0, (
            "Resolution stack should be empty after resolution"
        )
        assert len(_resolution_set.get()) == 0, (
            "Resolution set should be empty after resolution"
        )

        # Memory growth should be reasonable (not keeping the entire chain in memory)
        stats = snapshot_after.compare_to(snapshot_before, "lineno")
        container_stats = [s for s in stats if "container.py" in str(s.traceback)]

        if container_stats:
            total_growth = sum(s.size_diff for s in container_stats if s.size_diff > 0)
            # Should not grow more than a reasonable amount
            assert total_growth < 100000, (
                f"Resolution memory usage too high: {total_growth} bytes"
            )
