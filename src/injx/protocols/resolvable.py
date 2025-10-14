from __future__ import annotations

from typing import Any, ContextManager, Protocol, TypeVar, Union, runtime_checkable

from ..tokens import Token

T = TypeVar("T")


@runtime_checkable
class Resolvable(Protocol[T]):
    """Protocol for containers that can resolve dependencies synchronously and asynchronously.

    This protocol defines the core resolution capabilities that any dependency
    injection container must implement. It enables generic type preservation
    through the resolution chain.
    """

    def get(self, token: Token[T] | type[T]) -> T:
        """Resolve a dependency synchronously.

        Args:
            token: Token or type representing the dependency to resolve

        Returns:
            The resolved dependency instance of type T

        Raises:
            ResolutionError: If the dependency cannot be resolved
            CircularDependencyError: If a circular dependency is detected
        """
        ...

    async def aget(self, token: Token[T] | type[T]) -> T:
        """Resolve a dependency asynchronously.

        Args:
            token: Token or type representing the dependency to resolve

        Returns:
            The resolved dependency instance of type T

        Raises:
            ResolutionError: If the dependency cannot be resolved
            CircularDependencyError: If a circular dependency is detected
        """
        ...

    def has(self, token: Union[Token[Any], type[Any]]) -> bool:
        """Check if a dependency is registered.

        Args:
            token: Token or type to check

        Returns:
            True if the dependency can be resolved, False otherwise
        """
        ...


@runtime_checkable
class AsyncResolvable(Protocol[T]):
    """Protocol for containers that can only resolve dependencies asynchronously.

    This protocol is used for containers or contexts that operate in
    async-only environments, such as request-scoped containers in web
    frameworks.
    """

    async def aget(self, token: Token[T] | type[T]) -> T:
        """Resolve a dependency asynchronously.

        Args:
            token: Token or type representing the dependency to resolve

        Returns:
            The resolved dependency instance of type T

        Raises:
            ResolutionError: If the dependency cannot be resolved
            CircularDependencyError: If a circular dependency is detected
        """
        ...

    def has(self, token: Union[Token[Any], type[Any]]) -> bool:
        """Check if a dependency is registered.

        Args:
            token: Token or type to check

        Returns:
            True if the dependency can be resolved, False otherwise
        """
        ...


@runtime_checkable
class SupportsOverride(Protocol):
    """Protocol for containers that support temporary overrides.

    This protocol enables testing scenarios where dependencies need to be
    replaced with mock implementations or test doubles.
    """

    def override(self, token: Token[T], value: T) -> None:
        """Temporarily override a dependency value.

        Args:
            token: Token identifying the dependency to override
            value: Value to use instead of normal resolution

        Note:
            Overrides are scoped to the current concurrent context
            and do not affect the global container state.
        """
        ...

    def use_overrides(self, overrides: dict[Token[Any], Any]) -> ContextManager[None]:
        """Context manager for applying multiple overrides.

        Args:
            overrides: Mapping of tokens to override values

        Returns:
            Context manager that applies and removes the overrides

        Example:
            with container.use_overrides({DB: mock_db}):
                service = container.get(MyService)
        """
        ...

    def clear_overrides(self) -> None:
        """Clear all current overrides for this context."""
        ...
