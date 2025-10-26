"""First-class testing utilities for Injx dependency injection.

This module provides comprehensive testing support with scoped overrides,
isolated test contexts, and utilities for common testing patterns.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from types import TracebackType
from typing import Any, Callable, TypeVar, cast

from .container import Container
from .tokens import Token

__all__ = [
    "TestContainer",
    "TestScope",
    "MockFactory",
    "test_container",
    "mock_dependency",
    "override_dependency",
]

T = TypeVar("T")


class MockFactory:
    """Factory for creating spec-compliant mock objects."""

    @staticmethod
    def create_mock(
        token: Token[T],
        implementation: Callable[[], T] | None = None,
        *,
        use_autospec: bool = True,
    ) -> T:
        """Create a mock instance for the given token.

        Args:
            token: The token to create a mock for
            implementation: Optional custom implementation
            use_autospec: If True, use create_autospec for signature validation (default: True)

        Returns:
            A mock instance with optional signature validation
        """
        if implementation:
            return implementation()

        # Use unittest.mock autospec for validation if type available
        # However, for primitive types (str, int, etc), use simple mock instead
        # because autospec(str) returns NonCallableMagicMock which breaks test expectations
        if (
            use_autospec
            and token.type_ is not None
            and not isinstance(token.type_, type(str))
        ):
            from unittest.mock import create_autospec

            try:
                return cast(T, create_autospec(token.type_, instance=True))
            except (TypeError, ValueError):
                # Fall back to simple mock if autospec fails
                pass

        # Fallback to simple mock for tokens without type_
        class MockInstance:
            def __init__(self, token_name: str) -> None:
                self._mock_token_name = token_name

            def __repr__(self) -> str:
                return f"<Mock {self._mock_token_name}>"

        return cast(T, MockInstance(token.name))


class TestContainer:
    """Container wrapper specifically for testing with enhanced override capabilities.

    Provides isolated testing contexts, automatic cleanup, and convenient
    methods for common testing patterns.
    """

    def __init__(self, base_container: Container | None = None) -> None:
        """Initialize test container.

        Args:
            base_container: Optional base container to copy providers from
        """
        self.base_container = base_container or Container()
        self._overrides: dict[Token[Any], Any] = {}
        self._temp_providers: dict[Token[Any], Callable[[], Any]] = {}

    def override(self, token: Token[T] | type[T], mock: T | Callable[[], T]) -> None:
        """Override a dependency with a mock or implementation.

        Args:
            token: The token or type to override
            mock: Mock instance or factory function
        """
        normalized_token = self._normalize_token(token)

        if callable(mock) and not isinstance(mock, type):
            # Factory function
            self._temp_providers[normalized_token] = cast(Callable[[], Any], mock)
        else:
            # Direct instance
            self._overrides[normalized_token] = mock

    def mock(
        self, token: Token[T] | type[T], implementation: Callable[[], T] | None = None
    ) -> None:
        """Create and register a mock for the given token.

        Args:
            token: The token or type to mock
            implementation: Optional custom implementation
        """
        normalized_token = self._normalize_token(token)
        mock_instance = MockFactory.create_mock(normalized_token, implementation)
        self._overrides[normalized_token] = mock_instance

    def _normalize_token(self, token: Token[T] | type[T]) -> Token[Any]:
        """Normalize token specification to a Token instance."""
        if isinstance(token, Token):
            return cast(Token[Any], token)
        # Create a token from the type
        return Token(token.__name__, token)

    def get(self, token: Token[T] | type[T]) -> T:
        """Get a dependency, applying overrides first.

        Args:
            token: The token or type to resolve

        Returns:
            The resolved instance
        """
        normalized_token = self._normalize_token(token)

        # Check overrides first
        if normalized_token in self._overrides:
            return cast(T, self._overrides[normalized_token])

        # Check temporary providers
        if normalized_token in self._temp_providers:
            return cast(T, self._temp_providers[normalized_token]())

        # Fall back to base container
        return self.base_container.get(normalized_token)

    async def aget(self, token: Token[T] | type[T]) -> T:
        """Async version of get.

        Args:
            token: The token or type to resolve

        Returns:
            The resolved instance
        """
        normalized_token = self._normalize_token(token)

        # Check overrides first
        if normalized_token in self._overrides:
            return cast(T, self._overrides[normalized_token])

        # Check temporary providers
        if normalized_token in self._temp_providers:
            result = self._temp_providers[normalized_token]()
            if asyncio.iscoroutine(result):
                return cast(T, await result)
            return cast(T, result)

        # Fall back to base container
        return await self.base_container.aget(normalized_token)

    def clear_overrides(self) -> None:
        """Clear all overrides."""
        self._overrides.clear()
        self._temp_providers.clear()

    def list_overrides(self) -> list[Token[Any]]:
        """List all overridden tokens."""
        return list(self._overrides.keys()) + list(self._temp_providers.keys())


class TestScope:
    """Context manager for isolated test scopes with automatic cleanup."""

    def __init__(self, container: Container | TestContainer) -> None:
        """Initialize test scope.

        Args:
            container: Container to use for the test scope
        """
        self.container = container
        self._context_manager: Any = None
        self._async_context_manager: Any = None

    def __enter__(self) -> TestScope:
        """Enter test scope."""
        self._context_manager = (
            self.container.base_container.request_scope()
            if hasattr(self.container, "base_container")
            else self.container.request_scope()
        )
        self._context_manager.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit test scope with cleanup."""
        if self._context_manager:
            self._context_manager.__exit__(exc_type, exc_val, exc_tb)

        # Clear test overrides
        if hasattr(self.container, "clear_overrides"):
            self.container.clear_overrides()

    async def __aenter__(self) -> TestScope:
        """Enter async test scope."""
        if hasattr(self.container, "base_container"):
            self._async_context_manager = (
                self.container.base_container.async_request_scope()
            )
        else:
            self._async_context_manager = self.container.async_request_scope()
        await self._async_context_manager.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async test scope with cleanup."""
        if self._async_context_manager:
            await self._async_context_manager.__aexit__(exc_type, exc_val, exc_tb)

        # Clear test overrides
        if hasattr(self.container, "clear_overrides"):
            self.container.clear_overrides()


@contextmanager
def test_container(base_container: Container | None = None) -> Iterator[TestContainer]:
    """Create a test container with automatic cleanup.

    Args:
        base_container: Optional base container to copy from

    Yields:
        A TestContainer instance ready for testing
    """
    test_cont = TestContainer(base_container)
    try:
        yield test_cont
    finally:
        test_cont.clear_overrides()


def mock_dependency(
    token: Token[T] | type[T], implementation: Callable[[], T] | None = None
) -> T:
    """Create a mock dependency for testing.

    Args:
        token: The token or type to mock
        implementation: Optional custom implementation

    Returns:
        A mock instance
    """
    normalized_token = (
        token if isinstance(token, Token) else Token(token.__name__, token)
    )
    return MockFactory.create_mock(normalized_token, implementation)


def override_dependency(
    container: Container | TestContainer,
    token: Token[T] | type[T],
    mock: T | Callable[[], T],
) -> None:
    """Override a dependency in the given container.

    Args:
        container: The container to override in
        token: The token or type to override
        mock: Mock instance or factory function
    """
    if hasattr(container, "override"):
        container.override(token, mock)
    else:
        # For regular Container, use the override method
        normalized_token = (
            token if isinstance(token, Token) else Token(token.__name__, token)
        )

        if callable(mock) and not isinstance(mock, type):
            container.override(normalized_token, mock())
        else:
            container.override(normalized_token, mock)
