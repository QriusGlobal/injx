"""Container protocol for type-safe contracts.

This module defines the core protocols that enable type-safe dependency
injection and provide IDE-friendly interfaces for container operations.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import (
    Any,
    AsyncContextManager,
    ContextManager,
    Protocol,
    TypeVar,
    overload,
    runtime_checkable,
)

from ..tokens import Scope, Token

T = TypeVar("T")
U = TypeVar("U")
P = TypeVar("P")


@runtime_checkable
class ContainerProtocol(Protocol):
    """Protocol defining the essential container interface for type checking.

    This protocol enables type-safe dependency resolution and provides
    contracts that IDEs can use for autocomplete and error detection.
    """

    def get(self, token: Token[T] | type[T]) -> T:
        """Resolve a dependency synchronously.

        Args:
            token: Token or type for the dependency to resolve

        Returns:
            The resolved dependency instance

        Raises:
            ResolutionError: If the dependency cannot be resolved
            CircularDependencyError: If a circular dependency is detected
        """
        ...

    async def aget(self, token: Token[T] | type[T]) -> T:
        """Resolve a dependency asynchronously.

        Args:
            token: Token or type for the dependency to resolve

        Returns:
            The resolved dependency instance

        Raises:
            ResolutionError: If the dependency cannot be resolved
            CircularDependencyError: If a circular dependency is detected
        """
        ...

    def has(self, token: Token[Any] | type[Any]) -> bool:
        """Check if a dependency is registered in the container.

        Args:
            token: Token or type to check

        Returns:
            True if the dependency is registered, False otherwise
        """
        ...

    @overload
    def __getitem__(self, token: Token[T]) -> T: ...

    @overload
    def __getitem__(self, token: type[T]) -> T: ...

    def __getitem__(self, token: Token[T] | type[T]) -> T:
        """Resolve a dependency using subscript syntax.

        Args:
            token: Token or type for the dependency to resolve

        Returns:
            The resolved dependency instance

        Raises:
            ResolutionError: If the dependency cannot be resolved
            CircularDependencyError: If a circular dependency is detected

        Example:
            db = container[Database]
        """
        ...

    @overload
    def register(
        self,
        token: Token[T],
        provider: Callable[..., T],
        *,
        scope: Scope | None = None,
        tags: tuple[str, ...] = (),
    ) -> "ContainerProtocol": ...

    @overload
    def register(
        self,
        token: type[T],
        provider: Callable[..., T],
        *,
        scope: Scope | None = None,
        tags: tuple[str, ...] = (),
    ) -> "ContainerProtocol": ...

    def register(
        self,
        token: Token[T] | type[T],
        provider: Callable[..., T],
        *,
        scope: Scope | None = None,
        tags: tuple[str, ...] = (),
    ) -> "ContainerProtocol":
        """Register a provider for a token.

        Args:
            token: Token or type to register the provider for
            provider: Callable that returns the dependency instance
            scope: Optional lifecycle scope for the dependency
            tags: Optional tags for metadata and discovery

        Returns:
            Self for method chaining

        Example:
            container.register(Database, create_db, scope=Scope.SINGLETON)
        """
        ...

    def override(self, token: Token[T], value: T) -> None:
        """Override a dependency for the current concurrent context.

        Args:
            token: Token to override
            value: Value to use instead of resolving the dependency

        Example:
            with container.use_overrides({DB: mock_db}):
                service = container.get(MyService)
        """
        ...

    def clear(self) -> None:
        """Clear all cached instances and statistics.

        Keeps provider registrations intact but clears singleton cache,
        performance metrics, and temporary state.
        """
        ...

    @classmethod
    def get_active(cls) -> "ContainerProtocol":
        """Get the active container for the current context.

        Returns:
            The active container instance, creating one if necessary
        """
        ...

    @classmethod
    def set_active(cls, container: "ContainerProtocol | None") -> None:
        """Set the active container for the current context.

        Args:
            container: Container to set as active, or None to clear
        """
        ...

    def activate(self) -> ContextManager[None]:
        """Context manager to activate this container.

        Returns:
            Context manager that activates/deactivates this container

        Example:
            with container.activate():
                service = some_injected_function()
        """
        ...

    def request_scope(self) -> ContextManager["ContainerProtocol"]:
        """Create a request scope with automatic cleanup.

        Returns:
            Context manager for the request scope

        Example:
            with container.request_scope():
                service = container.get(RequestScopedService)
        """
        ...

    def async_request_scope(self) -> AsyncContextManager["ContainerProtocol"]:
        """Create an async request scope with automatic cleanup.

        Returns:
            Async context manager for the request scope

        Example:
            async with container.async_request_scope():
                service = await container.aget(RequestScopedService)
        """
        ...

    def test_scope(self) -> ContextManager["TestScopeProtocol"]:
        """Create an isolated test scope with automatic cleanup.

        Returns:
            Context manager for isolated testing

        Example:
            with container.test_scope() as test:
                test.override(DB, MockDatabase())
                service = test.get(MyService)
        """
        ...

    def list_tokens(self) -> list[Token[Any]]:
        """List all registered tokens.

        Returns:
            List of all registered tokens in registration order
        """
        ...

    def is_singleton(self, token: Token[Any] | type[Any]) -> bool:
        """Check if a token is registered as a singleton.

        Args:
            token: Token or type to check

        Returns:
            True if the token is registered as a singleton or cached as one
        """
        ...

    def dependency_graph(self) -> dict[str, list[str]]:
        """Get a dependency graph representation.

        Returns:
            Dictionary mapping token names to their dependency names
        """
        ...

    def debug_info(self) -> dict[str, Any]:
        """Get comprehensive debugging information.

        Returns:
            Dictionary with container state, performance metrics, and statistics
        """
        ...

    def get_stats(self) -> dict[str, Any]:
        """Get performance and usage statistics.

        Returns:
            Dictionary with cache hit rates, provider counts, etc.
        """
        ...

    @property
    def cache_hit_rate(self) -> float:
        """Get the cache hit rate for dependency resolution.

        Returns:
            Float between 0.0 and 1.0 representing cache efficiency
        """
        ...

    def __enter__(self) -> "ContainerProtocol":
        """Enter container as a context manager."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit container context manager with cleanup."""
        ...

    async def __aenter__(self) -> "ContainerProtocol":
        """Enter container as an async context manager."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async container context manager with cleanup."""
        ...

    async def aclose(self) -> None:
        """Async close: close tracked resources and clear caches."""
        ...

    def __repr__(self) -> str:
        """Return a readable representation of the container."""
        ...


@runtime_checkable
class TestScopeProtocol(Protocol):
    """Protocol for test scope functionality."""

    def override(self, token: Token[T] | type[T], mock: T | Callable[[], T]) -> None:
        """Override a dependency in the test scope.

        Args:
            token: Token or type to override
            mock: Mock instance or factory function
        """
        ...

    def mock(
        self, token: Token[T] | type[T], implementation: Callable[[], T] | None = None
    ) -> None:
        """Create and register a mock for the given token.

        Args:
            token: Token or type to mock
            implementation: Optional custom implementation
        """
        ...

    def get(self, token: Token[T] | type[T]) -> T:
        """Get a dependency, applying overrides first.

        Args:
            token: Token or type to resolve

        Returns:
            The resolved instance with overrides applied
        """
        ...

    def __getitem__(self, token: Token[T] | type[T]) -> T:
        """Get a dependency using subscript syntax.

        Args:
            token: Token or type to resolve

        Returns:
            The resolved instance with overrides applied
        """
        ...

    async def aget(self, token: Token[T] | type[T]) -> T:
        """Async version of get with overrides.

        Args:
            token: Token or type to resolve

        Returns:
            The resolved instance with overrides applied
        """
        ...

    def clear_overrides(self) -> None:
        """Clear all overrides in this test scope."""
        ...

    def list_overrides(self) -> list[Token[Any]]:
        """List all overridden tokens.

        Returns:
            List of tokens that have been overridden
        """
        ...

    def __enter__(self) -> "TestScopeProtocol":
        """Enter the test scope."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the test scope with cleanup."""
        ...

    async def __aenter__(self) -> "TestScopeProtocol":
        """Enter the async test scope."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the async test scope with cleanup."""
        ...
