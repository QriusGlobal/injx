"""Tests for O(1) cycle detection improvements."""

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from injx import Container, Scope, Token
from injx.container import _resolution_set, _resolution_stack
from injx.exceptions import CircularDependencyError

# Detect CI environment and apply timing multiplier for hardware variability
IS_CI = os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'
CI_MULTIPLIER = 5 if IS_CI else 1  # 5x more lenient in CI environments


class TestCycleDetection:
    """Test the O(1) cycle detection using sets."""

    def test_o1_cycle_detection_performance(self):
        """Verify cycle detection is O(1) even with very deep dependency chains."""
        container = Container()

        # Test with increasing chain depths
        depths = [10, 100, 500, 1000]
        detection_times = []

        for depth in depths:
            # Create a new container for each test
            container = Container()
            tokens = []

            # Create a chain of dependencies
            for i in range(depth):
                token = Token(f"service_{i}", type(f"Service{i}", (), {}))
                tokens.append(token)

                if i == 0:
                    # First service has no dependencies
                    container.register(token, lambda: object())
                else:
                    # Each service depends on the previous one
                    prev_token = tokens[i - 1]
                    container.register(
                        token, lambda c=container, t=prev_token: c.get(t)
                    )

            # Create a cycle by making a service that depends on itself indirectly
            # We'll create a new container with the cycle built in from the start
            container = Container()
            tokens = []

            # Register services with circular dependency from the beginning
            for i in range(depth):
                token = Token(f"service_{i}", type(f"Service{i}", (), {}))
                tokens.append(token)

            # Register all services with the cycle built in
            for i in range(depth):
                token = tokens[i]
                if i == depth - 1:
                    # Last service depends on first (creating the cycle)
                    first = tokens[0]
                    container.register(token, lambda c=container, t=first: c.get(t))
                elif i == 0:
                    # First service depends on the last
                    last = tokens[-1]
                    container.register(token, lambda c=container, t=last: c.get(t))
                else:
                    # Middle services depend on the next one
                    next_token = tokens[i + 1]
                    container.register(
                        token, lambda c=container, t=next_token: c.get(t)
                    )

            # Measure cycle detection time
            start_time = time.perf_counter()
            with pytest.raises(CircularDependencyError):
                container.get(tokens[0])
            end_time = time.perf_counter()

            detection_time = end_time - start_time
            detection_times.append(detection_time)

        # O(1) means detection time should not increase significantly with depth
        # Allow some variance but times should be in the same order of magnitude
        min_time = min(detection_times)
        max_time = max(detection_times)

        # Detection time should not grow linearly with depth
        assert max_time < min_time * 5, (
            f"Cycle detection not O(1): times={detection_times}, "
            f"depth_10={detection_times[0]:.4f}s, depth_1000={detection_times[-1]:.4f}s"
        )

        # All detections should be fast (< 100ms even for depth 1000)
        for depth, det_time in zip(depths, detection_times):
            assert det_time < 0.1 * CI_MULTIPLIER, (
                f"Cycle detection too slow at depth {depth}: {det_time:.4f}s (threshold: {0.1 * CI_MULTIPLIER:.3f}s)"
            )

    def test_resolution_set_mechanism(self):
        """Test the internal _resolution_set mechanism for cycle detection."""
        container = Container()

        # Create services with dependencies
        token_a = Token("a", object)
        token_b = Token("b", object)
        token_c = Token("c", object)

        # Track resolution path
        resolution_path = []

        def create_a():
            resolution_path.append("a")
            # Check that we're being tracked in the resolution set
            assert token_a in _resolution_set.get(), (
                "Token A should be in resolution set"
            )
            return object()

        def create_b():
            resolution_path.append("b")
            assert token_b in _resolution_set.get(), (
                "Token B should be in resolution set"
            )
            # B depends on C
            return container.get(token_c)

        def create_c():
            resolution_path.append("c")
            assert token_c in _resolution_set.get(), (
                "Token C should be in resolution set"
            )
            # Check all are in the set during nested resolution
            assert len(_resolution_set.get()) == 3, (
                "All tokens should be in resolution set"
            )
            return object()

        # Register B and C normally
        container.register(token_b, create_b)
        container.register(token_c, create_c)

        # A depends on B (register A with dependency)
        container.register(token_a, lambda: container.get(token_b))

        # Resolve A (which depends on B, which depends on C)
        container.get(token_a)

        # After resolution, sets should be cleared
        assert len(_resolution_set.get()) == 0, (
            "Resolution set should be empty after successful resolution"
        )
        assert len(_resolution_stack.get()) == 0, (
            "Resolution stack should be empty after successful resolution"
        )

        # Verify resolution order
        assert resolution_path == ["b", "c"], (
            "Resolution should follow dependency order"
        )

    def test_multiple_cycles_detection(self):
        """Test detection of multiple different cycles in the dependency graph."""
        container = Container()

        # Create a complex graph with multiple cycles
        # A -> B -> C -> A (cycle 1)
        # D -> E -> F -> D (cycle 2)
        # G -> H -> B (connects to cycle 1)

        tokens = {}
        for name in "ABCDEFGH":
            tokens[name] = Token(name, type(f"Service{name}", (), {}))

        # Set up dependencies
        container.register(tokens["A"], lambda: container.get(tokens["B"]))
        container.register(tokens["B"], lambda: container.get(tokens["C"]))
        container.register(tokens["C"], lambda: container.get(tokens["A"]))  # Cycle 1

        container.register(tokens["D"], lambda: container.get(tokens["E"]))
        container.register(tokens["E"], lambda: container.get(tokens["F"]))
        container.register(tokens["F"], lambda: container.get(tokens["D"]))  # Cycle 2

        container.register(tokens["G"], lambda: container.get(tokens["H"]))
        container.register(
            tokens["H"], lambda: container.get(tokens["B"])
        )  # Connects to cycle 1

        # Test cycle 1 detection
        with pytest.raises(CircularDependencyError) as exc1:
            container.get(tokens["A"])
        assert "Circular dependency detected" in str(exc1.value)

        # Test cycle 2 detection
        with pytest.raises(CircularDependencyError) as exc2:
            container.get(tokens["D"])
        assert "Circular dependency detected" in str(exc2.value)

        # Test that G also hits cycle 1
        with pytest.raises(CircularDependencyError) as exc3:
            container.get(tokens["G"])
        assert "Circular dependency detected" in str(exc3.value)

    def test_concurrent_cycle_detection(self):
        """Test that cycle detection works correctly with concurrent resolution."""
        container = Container()

        # Create services with potential cycles
        tokens = [Token(f"service_{i}", object) for i in range(10)]

        # Register services with some dependencies
        for i, token in enumerate(tokens):
            if i == 5:
                # Create a cycle: service_5 depends on service_2
                container.register(token, lambda c=container: c.get(tokens[2]))
            elif i == 2:
                # service_2 depends on service_5 (completing the cycle)
                container.register(token, lambda c=container: c.get(tokens[5]))
            else:
                # Others are independent
                container.register(token, lambda i=i: f"service_{i}")

        # Track exceptions from concurrent executions
        exceptions = []

        def resolve_token(token):
            try:
                return container.get(token)
            except CircularDependencyError as e:
                exceptions.append(e)
                raise

        # Resolve multiple tokens concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            # Submit resolutions for all tokens
            for token in tokens:
                futures.append(executor.submit(resolve_token, token))

            # Collect results
            results = []
            for future in futures:
                try:
                    results.append(future.result(timeout=1))
                except CircularDependencyError:
                    pass  # Expected for tokens in cycle
                except Exception as e:
                    pytest.fail(f"Unexpected exception: {e}")

        # Should have caught the cycle for tokens 2 and 5
        assert len(exceptions) >= 2, "Should detect cycle in concurrent execution"

        # Non-cycle tokens should resolve successfully
        assert len(results) >= len(tokens) - 2, "Non-cycle tokens should resolve"

    async def test_async_cycle_detection(self):
        """Test cycle detection in async resolution."""
        container = Container()

        # Create async providers with cycle
        async def create_a():
            await asyncio.sleep(0.001)
            return await container.aget(Token("b", object))

        async def create_b():
            await asyncio.sleep(0.001)
            return await container.aget(Token("c", object))

        async def create_c():
            await asyncio.sleep(0.001)
            return await container.aget(Token("a", object))  # Cycle!

        container.register(Token("a", object), create_a)
        container.register(Token("b", object), create_b)
        container.register(Token("c", object), create_c)

        # Should detect cycle in async resolution
        with pytest.raises(CircularDependencyError) as exc:
            await container.aget(Token("a", object))

        assert "Circular dependency detected" in str(exc.value)

        # Resolution set should be cleared after exception
        assert len(_resolution_set.get()) == 0, (
            "Resolution set should be cleared after async exception"
        )

    def test_self_dependency_detection(self):
        """Test detection of immediate self-dependencies."""
        container = Container()

        token = Token("self_dependent", object)

        # Register a service that depends on itself
        container.register(token, lambda: container.get(token))

        # Should detect self-dependency immediately
        with pytest.raises(CircularDependencyError) as exc:
            container.get(token)

        assert token in exc.value.chain, "Self-dependent token should be in error chain"
        assert "Circular dependency detected" in str(exc.value)

    def test_cycle_detection_with_different_scopes(self):
        """Test cycle detection works across different scopes."""
        container = Container()

        # Create tokens with different scopes
        singleton_token = Token("singleton", object, scope=Scope.SINGLETON)
        request_token = Token("request", object, scope=Scope.REQUEST)
        transient_token = Token("transient", object, scope=Scope.TRANSIENT)

        # Create cycle across scopes
        container.register(
            singleton_token, lambda: container.get(request_token), scope=Scope.SINGLETON
        )
        container.register(
            request_token, lambda: container.get(transient_token), scope=Scope.REQUEST
        )
        container.register(
            transient_token,
            lambda: container.get(singleton_token),
            scope=Scope.TRANSIENT,
        )

        # Should detect cycle regardless of scope
        with pytest.raises(CircularDependencyError):
            container.get(singleton_token)

    def test_cycle_error_provides_useful_information(self):
        """Test that cycle detection errors provide helpful debugging information."""
        container = Container()

        # Create a cycle: A -> B -> C -> D -> B
        tokens = {
            "A": Token("ServiceA", object),
            "B": Token("ServiceB", object),
            "C": Token("ServiceC", object),
            "D": Token("ServiceD", object),
        }

        container.register(tokens["A"], lambda: container.get(tokens["B"]))
        container.register(tokens["B"], lambda: container.get(tokens["C"]))
        container.register(tokens["C"], lambda: container.get(tokens["D"]))
        container.register(tokens["D"], lambda: container.get(tokens["B"]))  # Cycle!

        with pytest.raises(CircularDependencyError) as exc:
            container.get(tokens["A"])

        error = exc.value

        # Error should contain the problematic token
        assert error.token == tokens["B"], (
            "Error should identify the token creating the cycle"
        )

        # Chain should show the resolution path
        assert len(error.chain) >= 3, "Chain should show the path to the cycle"
        assert tokens["A"] in error.chain, "Starting token should be in chain"
        assert tokens["B"] in error.chain, "Cyclic token should be in chain"

        # Error message should be informative
        error_str = str(error)
        assert "ServiceB" in error_str, "Error should mention the problematic service"
        assert "Resolution chain" in error_str, "Error should show resolution chain"

    def test_resolution_guard_cleanup_on_exception(self):
        """Test that resolution guard properly cleans up on non-cycle exceptions."""
        container = Container()

        class FailingService:
            def __init__(self):
                # Check that we're in the resolution set
                Token("failing", FailingService)
                # This would be true during resolution
                raise ValueError("Intentional failure")

        token = Token("failing", FailingService)
        container.register(token, FailingService)

        # Resolution should fail with ValueError
        with pytest.raises(ValueError, match="Intentional failure"):
            container.get(token)

        # Resolution set should be cleaned up even after non-cycle exception
        assert len(_resolution_set.get()) == 0, (
            "Resolution set should be cleared after exception"
        )
        assert len(_resolution_stack.get()) == 0, (
            "Resolution stack should be cleared after exception"
        )
