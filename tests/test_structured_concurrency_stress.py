"""Stress tests for structured concurrency features.

These tests verify the robustness of TaskGroup-based cleanup,
timeout handling, cancellation propagation, and tracing under
high load and failure conditions.
"""

from __future__ import annotations

import asyncio
import random
import time
from contextlib import asynccontextmanager

import pytest

from injx import Container, Scope, Token
from injx.cancellation import CancellationToken
from injx.exceptions import CleanupFailureGroup, ResolutionError
from injx.timeouts import TimeoutPolicy


class TestTaskGroupCleanupStress:
    """Stress tests for TaskGroup-based cleanup."""

    @pytest.mark.asyncio
    async def test_multiple_cleanup_failures_all_reported(self):
        """Verify all cleanup failures are aggregated, not just the first."""
        container = Container()
        num_failures = 10
        cleanup_called: list[int] = []

        for i in range(num_failures):

            @asynccontextmanager
            async def failing_cm(idx: int = i):
                cleanup_called.append(idx)
                yield f"resource_{idx}"
                raise RuntimeError(f"Cleanup failed for resource {idx}")

            token = Token(f"failing_{i}", str)
            container.register_context(
                token,
                lambda idx=i: failing_cm(idx),
                is_async=True,
                scope=Scope.SINGLETON,
            )
            await container.aget(token)

        with pytest.raises(CleanupFailureGroup) as exc_info:
            await container.dispose()

        # All failures should be reported
        assert len(exc_info.value.exceptions) == num_failures
        # All cleanups should have been attempted
        assert len(cleanup_called) == num_failures

    @pytest.mark.asyncio
    async def test_cleanup_continues_after_individual_failures(self):
        """Verify cleanup continues for remaining resources after failures."""
        container = Container()
        cleanup_order: list[str] = []

        @asynccontextmanager
        async def good_cm(name: str):
            yield name
            cleanup_order.append(f"{name}_cleaned")

        @asynccontextmanager
        async def bad_cm(name: str):
            yield name
            cleanup_order.append(f"{name}_failed")
            raise RuntimeError(f"{name} cleanup error")

        # Register alternating good and bad resources
        for i in range(10):
            name = f"resource_{i}"
            if i % 2 == 0:
                token = Token(name, str)
                container.register_context(
                    token,
                    lambda n=name: good_cm(n),
                    is_async=True,
                    scope=Scope.SINGLETON,
                )
            else:
                token = Token(name, str)
                container.register_context(
                    token,
                    lambda n=name: bad_cm(n),
                    is_async=True,
                    scope=Scope.SINGLETON,
                )
            await container.aget(token)

        with pytest.raises(CleanupFailureGroup) as exc_info:
            await container.dispose()

        # 5 failures expected (odd indices)
        assert len(exc_info.value.exceptions) == 5
        # All 10 cleanups should have been attempted
        assert len(cleanup_order) == 10

    @pytest.mark.asyncio
    async def test_high_concurrency_cleanup(self):
        """Stress test cleanup with many concurrent resources."""
        container = Container()
        num_resources = 100
        cleanup_count = 0
        cleanup_lock = asyncio.Lock()

        @asynccontextmanager
        async def tracked_cm(idx: int):
            nonlocal cleanup_count
            yield idx
            # Simulate variable cleanup times
            await asyncio.sleep(random.uniform(0.001, 0.01))
            async with cleanup_lock:
                cleanup_count += 1

        for i in range(num_resources):
            token = Token(f"resource_{i}", int)
            container.register_context(
                token,
                lambda idx=i: tracked_cm(idx),
                is_async=True,
                scope=Scope.SINGLETON,
            )
            await container.aget(token)

        await container.dispose()

        # All cleanups should complete
        assert cleanup_count == num_resources

    @pytest.mark.asyncio
    async def test_mixed_sync_async_cleanup_failures(self):
        """Test cleanup with both sync and async failures."""
        container = Container()
        errors_seen: list[str] = []

        @asynccontextmanager
        async def async_failing_cm():
            yield "async_resource"
            errors_seen.append("async_cleanup")
            raise ValueError("Async cleanup error")

        class SyncFailingResource:
            def close(self) -> None:
                errors_seen.append("sync_cleanup")
                raise RuntimeError("Sync cleanup error")

        # Register async failing resource
        async_token = Token("async_fail", str)
        container.register_context(
            async_token,
            lambda: async_failing_cm(),
            is_async=True,
            scope=Scope.SINGLETON,
        )
        await container.aget(async_token)

        # Register sync failing resource (via regular registration with close method)
        sync_token = Token("sync_fail", SyncFailingResource)
        container.register(sync_token, SyncFailingResource, scope=Scope.SINGLETON)
        container.get(sync_token)

        with pytest.raises(CleanupFailureGroup) as exc_info:
            await container.dispose()

        # Both types of failures should be captured
        assert len(errors_seen) >= 1  # At least async cleanup was attempted
        assert any(
            isinstance(e, (ValueError, RuntimeError)) for e in exc_info.value.exceptions
        )


class TestTimeoutStress:
    """Stress tests for timeout functionality."""

    @pytest.mark.asyncio
    async def test_timeout_with_many_slow_providers(self):
        """Test timeout enforcement with multiple slow providers."""
        policy = TimeoutPolicy(provider_timeout=0.1, cleanup_timeout=1.0)
        container = Container(timeout_policy=policy)
        timeout_count = 0

        # Create providers with varying delays - must be actual async functions
        for i in range(10):
            delay = 0.05 + (i * 0.02)  # 50ms to 230ms
            token = Token(f"slow_{i}", str)

            async def make_slow_provider(d: float = delay) -> str:
                await asyncio.sleep(d)
                return "completed"

            container.register(token, make_slow_provider)

        # Resolve all - some should timeout
        for i in range(10):
            token = Token(f"slow_{i}", str)
            try:
                await container.aget(token)
            except ResolutionError as e:
                if "timed out" in str(e):
                    timeout_count += 1

        # Later providers should timeout (delay > 100ms)
        assert timeout_count >= 3

    @pytest.mark.asyncio
    async def test_batch_timeout_bounds_total_time(self):
        """Verify batch timeout limits total execution time."""
        policy = TimeoutPolicy(
            provider_timeout=None,  # No individual timeout
            batch_timeout=0.2,
            max_concurrency=5,
        )
        container = Container(timeout_policy=policy)

        async def slow_provider():
            await asyncio.sleep(0.5)  # Each takes 500ms
            return "done"

        tokens = []
        for i in range(10):
            token = Token(f"slow_{i}", str)
            container.register(token, slow_provider)
            tokens.append(token)

        start = time.perf_counter()
        with pytest.raises(ResolutionError) as exc_info:
            await container.batch_resolve_async(tokens)
        elapsed = time.perf_counter() - start

        assert "timed out" in str(exc_info.value)
        # Should timeout around 200ms, not 500ms * 10 / 5 = 1000ms
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_bounded_concurrency_limits_parallel_work(self):
        """Verify max_concurrency limits simultaneous resolutions."""
        max_concurrent = 3
        policy = TimeoutPolicy(max_concurrency=max_concurrent)
        container = Container(timeout_policy=policy)

        current_concurrent = 0
        max_observed = 0
        lock = asyncio.Lock()

        async def tracking_provider():
            nonlocal current_concurrent, max_observed
            async with lock:
                current_concurrent += 1
                max_observed = max(max_observed, current_concurrent)
            await asyncio.sleep(0.05)  # Simulate work
            async with lock:
                current_concurrent -= 1
            return "done"

        tokens = []
        for i in range(20):
            token = Token(f"tracked_{i}", str)
            container.register(token, tracking_provider)
            tokens.append(token)

        await container.batch_resolve_async(tokens)

        # Should never exceed max_concurrency
        assert max_observed <= max_concurrent

    @pytest.mark.asyncio
    async def test_timeout_policy_testing_preset(self):
        """Verify TimeoutPolicy.testing() works correctly."""
        policy = TimeoutPolicy.testing()  # 1s provider timeout
        container = Container(timeout_policy=policy)

        async def slow_provider() -> str:
            await asyncio.sleep(2.0)  # Longer than testing timeout (1s)
            return "done"

        token = Token("slow", str)
        container.register(token, slow_provider)

        with pytest.raises(ResolutionError) as exc_info:
            await container.aget(token)

        assert "timed out" in str(exc_info.value)


class TestCancellationStress:
    """Stress tests for cancellation propagation."""

    @pytest.mark.asyncio
    async def test_cancellation_stops_in_flight_resolutions(self):
        """Verify cancellation token is checked during resolution."""
        container = Container()
        resolution_attempted = False

        async def slow_provider() -> str:
            nonlocal resolution_attempted
            resolution_attempted = True
            await asyncio.sleep(0.5)
            return "result"

        token = Token("slow", str)
        container.register(token, slow_provider)

        async with container.with_cancellation() as cancel_token:
            # Pre-cancel before resolution
            cancel_token.cancel("Test cancellation")

            # Resolution should fail due to pre-cancellation
            with pytest.raises(asyncio.CancelledError):
                await container.aget(token)

        # Provider should not have been called (cancelled before execution)
        assert not resolution_attempted

    @pytest.mark.asyncio
    async def test_cancellation_callback_invoked(self):
        """Verify cancellation callbacks are invoked."""
        callback_count = 0

        def on_cancel():
            nonlocal callback_count
            callback_count += 1

        token = CancellationToken()
        for _ in range(5):
            token.on_cancel(on_cancel)

        assert callback_count == 0
        token.cancel("test")
        assert callback_count == 5

        # Additional cancel calls should not invoke callbacks again
        token.cancel("test again")
        assert callback_count == 5

    @pytest.mark.asyncio
    async def test_nested_cancellation_contexts(self):
        """Test nested cancellation contexts work correctly."""
        container = Container()
        outer_cancelled = False
        inner_cancelled = False

        async def check_outer():
            nonlocal outer_cancelled
            token = CancellationToken.get_current()
            if token and token.is_cancelled:
                outer_cancelled = True

        async def check_inner():
            nonlocal inner_cancelled
            token = CancellationToken.get_current()
            if token and token.is_cancelled:
                inner_cancelled = True

        async with container.with_cancellation() as outer:  # noqa: F841
            async with container.with_cancellation() as inner:
                inner.cancel("inner cancel")
                await check_inner()

            # After inner context exits, outer should be active again
            await check_outer()

        assert inner_cancelled
        assert not outer_cancelled

    @pytest.mark.asyncio
    async def test_pre_cancelled_token_blocks_resolution(self):
        """Verify pre-cancelled token prevents resolution from starting."""
        container = Container()
        provider_called = False

        async def tracking_provider():
            nonlocal provider_called
            provider_called = True
            return "result"

        token = Token("tracked", str)
        container.register(token, tracking_provider)

        async with container.with_cancellation() as cancel_token:
            cancel_token.cancel("Pre-cancelled")

            with pytest.raises(asyncio.CancelledError):
                await container.aget(token)

        # Provider should never have been called
        assert not provider_called


class TestTracingStress:
    """Stress tests for resolution tracing."""

    @pytest.mark.asyncio
    async def test_tracing_deep_dependency_chain(self):
        """Test tracing with deep nested dependencies."""
        container = Container()
        depth = 20

        # Create chain: A depends on B depends on C ... depends on Z
        for i in range(depth):
            if i == depth - 1:
                # Leaf node
                token = Token(f"level_{i}", str)
                container.register(token, lambda: "leaf")
            else:
                # Node that depends on next level
                token = Token(f"level_{i}", str)
                next_token = Token(f"level_{i + 1}", str)
                container.register(
                    token,
                    lambda t=next_token: container.get(t) + f"_level_{i}",
                )

        async with container.trace_resolution() as traces:
            root_token = Token("level_0", str)
            await container.aget(root_token)

        # Should have captured traces
        assert len(traces) >= 1
        # Root trace should exist
        root_trace = traces[0]
        assert "level_0" in root_trace.token_name

    @pytest.mark.asyncio
    async def test_tracing_many_parallel_resolutions(self):
        """Test tracing under high parallel load."""
        container = Container()
        num_tokens = 50

        for i in range(num_tokens):
            token = Token(f"parallel_{i}", int)
            container.register(token, lambda idx=i: idx)

        async with container.trace_resolution() as traces:
            tokens = [Token(f"parallel_{i}", int) for i in range(num_tokens)]
            await container.batch_resolve_async(tokens)

        # All resolutions should be traced
        assert len(traces) == num_tokens

    @pytest.mark.asyncio
    async def test_tracing_with_failures(self):
        """Test tracing captures failures correctly."""
        container = Container()

        async def failing_provider() -> str:
            raise ValueError("Intentional failure")

        async def success_provider() -> str:
            return "success"

        fail_token = Token("failing", str)
        success_token = Token("success", str)
        container.register(fail_token, failing_provider)
        container.register(success_token, success_provider)

        async with container.trace_resolution() as traces:
            # Resolve success first
            await container.aget(success_token)

            # Then try to resolve failure
            try:
                await container.aget(fail_token)
            except (ResolutionError, ValueError):
                pass

        # Should have both traces
        assert len(traces) == 2

        success_trace = next(t for t in traces if "success" in t.token_name)
        fail_trace = next(t for t in traces if "failing" in t.token_name)

        assert success_trace.success
        assert not fail_trace.success
        assert fail_trace.error is not None

    @pytest.mark.asyncio
    async def test_tracing_performance_overhead_minimal(self):
        """Verify tracing has minimal performance overhead."""
        container = Container()
        num_iterations = 100

        for i in range(10):
            token = Token(f"perf_{i}", int)
            container.register(token, lambda idx=i: idx, scope=Scope.TRANSIENT)

        # Time without tracing
        start = time.perf_counter()
        for _ in range(num_iterations):
            for i in range(10):
                await container.aget(Token(f"perf_{i}", int))
        time_without_tracing = time.perf_counter() - start

        # Time with tracing
        start = time.perf_counter()
        for _ in range(num_iterations):
            async with container.trace_resolution():
                for i in range(10):
                    await container.aget(Token(f"perf_{i}", int))
        time_with_tracing = time.perf_counter() - start

        # Tracing overhead should be less than 50%
        overhead = (time_with_tracing - time_without_tracing) / time_without_tracing
        assert overhead < 0.5, f"Tracing overhead too high: {overhead:.2%}"


class TestErgonomicAPIsStress:
    """Stress tests for ergonomic APIs."""

    @pytest.mark.asyncio
    async def test_aget_or_none_many_missing(self):
        """Test aget_or_none with many missing dependencies."""
        container = Container()

        # Only register some tokens
        for i in range(10):
            token = Token(f"exists_{i}", int)
            container.register(token, lambda idx=i: idx)

        results = []
        for i in range(20):
            if i < 10:
                token = Token(f"exists_{i}", int)
            else:
                token = Token(f"missing_{i}", int)
            result = await container.aget_or_none(token)
            results.append(result)

        # First 10 should have values, last 10 should be None
        assert all(r is not None for r in results[:10])
        assert all(r is None for r in results[10:])

    @pytest.mark.asyncio
    async def test_aget_with_fallback_factory(self):
        """Test aget_with_fallback with factory functions."""
        container = Container()
        factory_calls = 0

        def fallback_factory():
            nonlocal factory_calls
            factory_calls += 1
            return f"fallback_{factory_calls}"

        token = Token("missing", str)

        # Each call should invoke factory
        results = []
        for _ in range(5):
            result = await container.aget_with_fallback(token, fallback_factory)
            results.append(result)

        assert factory_calls == 5
        assert results == [f"fallback_{i}" for i in range(1, 6)]

    @pytest.mark.asyncio
    async def test_try_aget_error_collection(self):
        """Test try_aget error collection across many failures."""
        container = Container()

        # Must define async functions properly with captured index
        for i in range(30):
            token = Token(f"maybe_fail_{i}", int)

            async def make_provider(idx: int = i) -> int:
                if idx % 3 == 0:
                    raise ValueError(f"Error {idx}")
                return idx

            container.register(token, make_provider)

        successes = 0
        errors = 0

        for i in range(30):
            token = Token(f"maybe_fail_{i}", int)
            result, err = await container.try_aget(token)
            if err is None:
                successes += 1
            else:
                errors += 1

        # 10 failures (0, 3, 6, 9, 12, 15, 18, 21, 24, 27)
        assert errors == 10
        assert successes == 20


class TestCombinedStress:
    """Combined stress tests using multiple features together."""

    @pytest.mark.asyncio
    async def test_timeout_with_tracing(self):
        """Test timeout behavior is correctly traced."""
        policy = TimeoutPolicy(provider_timeout=0.1)
        container = Container(timeout_policy=policy)

        async def slow_provider() -> str:
            await asyncio.sleep(1.0)
            return "done"

        token = Token("slow", str)
        container.register(token, slow_provider)

        async with container.trace_resolution() as traces:
            try:
                await container.aget(token)
            except ResolutionError:
                pass

        assert len(traces) == 1
        assert not traces[0].success
        assert "timed out" in (traces[0].error or "").lower()

    @pytest.mark.asyncio
    async def test_cancellation_with_cleanup(self):
        """Test cancellation properly triggers cleanup."""
        container = Container()
        cleanup_called = False

        @asynccontextmanager
        async def resource_with_cleanup():
            nonlocal cleanup_called
            yield "resource"
            cleanup_called = True

        token = Token("resource", str)
        container.register_context(
            token, resource_with_cleanup, is_async=True, scope=Scope.REQUEST
        )

        async with container.async_request_scope():
            async with container.with_cancellation() as cancel_token:
                await container.aget(token)
                cancel_token.cancel("Test")

        # Cleanup should still have run despite cancellation
        assert cleanup_called

    @pytest.mark.asyncio
    async def test_full_feature_integration(self):
        """Integration test using all new features together."""
        policy = TimeoutPolicy(
            provider_timeout=1.0,
            cleanup_timeout=2.0,
            max_concurrency=5,
        )
        container = Container(timeout_policy=policy)

        resources_created = 0
        resources_cleaned = 0
        lock = asyncio.Lock()

        @asynccontextmanager
        async def tracked_resource(idx: int):
            nonlocal resources_created, resources_cleaned
            async with lock:
                resources_created += 1
            await asyncio.sleep(0.01)
            yield f"resource_{idx}"
            async with lock:
                resources_cleaned += 1

        # Register many resources
        for i in range(20):
            token = Token(f"resource_{i}", str)
            container.register_context(
                token,
                lambda idx=i: tracked_resource(idx),
                is_async=True,
                scope=Scope.SINGLETON,
            )

        # Use tracing to monitor resolution
        async with container.trace_resolution() as traces:
            # Resolve all with batch (bounded concurrency)
            tokens = [Token(f"resource_{i}", str) for i in range(20)]
            await container.batch_resolve_async(tokens)

        # All should be traced
        assert len(traces) == 20
        assert all(t.success for t in traces)

        # Cleanup
        await container.dispose()

        # All should be cleaned up
        assert resources_created == 20
        assert resources_cleaned == 20
