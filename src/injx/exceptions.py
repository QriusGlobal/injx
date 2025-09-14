"""Exception classes for injx dependency injection container."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from injx.tokens import Token

__all__ = [
    "CircularDependencyError",
    "InjxError",
    "ResolutionError",
    "AsyncCleanupRequiredError",
    "CleanupContractError",
]


class InjxError(Exception):
    """Base exception for all injx errors."""


class ResolutionError(InjxError):
    """Raised when a dependency cannot be resolved."""

    def __init__(
        self, token: "Token[Any]", chain: list["Token[Any]"], cause: str
    ) -> None:
        """Initialize resolution error with context.

        Args:
            token: The token that couldn't be resolved
            chain: The current resolution chain
            cause: Human-readable cause description
        """
        self.token = token
        self.chain = chain
        self.cause = cause

        chain_str = " -> ".join(t.name for t in chain) if chain else "root"
        super().__init__(
            f"Cannot resolve token '{token.name}':\n"
            f"  Resolution chain: {chain_str}\n"
            f"  Cause: {cause}"
        )


class CircularDependencyError(ResolutionError):
    """Raised when a circular dependency is detected during resolution."""

    def __init__(self, token: "Token[Any]", chain: list["Token[Any]"]) -> None:
        """Initialize circular dependency error.

        Args:
            token: The token that created the cycle
            chain: The resolution chain showing the cycle
        """
        super().__init__(
            token,
            chain,
            f"Circular dependency detected: {' -> '.join(t.name for t in chain)} -> {token.name}",
        )


class AsyncCleanupRequiredError(InjxError):
    """Raised when a synchronous cleanup is attempted for an async-only resource.

    This indicates incorrect usage by the caller. Use an async scope or
    call ``await container.aclose()`` to clean up asynchronous resources.
    """

    def __init__(self, resource_type: str, advice: str) -> None:
        super().__init__(
            f"Resource {resource_type} requires asynchronous cleanup. {advice}"
        )


class CleanupContractError(InjxError):
    """Raised when a registration declares an invalid or inconsistent cleanup contract."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
