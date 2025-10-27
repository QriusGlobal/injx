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
    "DependencyChainError",
]


class InjxError(Exception):
    """Base exception for all injx errors."""


class DependencyChainError(InjxError):
    """Raised when dependency chain analysis fails."""

    def __init__(self, message: str, chain: list["Token[Any]"] | None = None) -> None:
        self.chain = chain or []
        super().__init__(message)


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

        # Enhanced error message with full dependency resolution chain
        chain_str = self._format_resolution_chain(chain)
        super().__init__(
            f"Cannot resolve token '{token.name}':\n"
            f"  Resolution chain:\n{chain_str}"
            f"  Missing dependency: {cause}"
        )

    def _format_resolution_chain(self, chain: list["Token[Any]"]) -> str:
        """Format the resolution chain with type information and indentation."""
        if not chain:
            return "    [root]\n"

        formatted_lines: list[str] = []
        for i, token in enumerate(chain):
            indent = "    " * (i + 1)
            type_info = (
                f" ({token.type_.__name__})" if hasattr(token.type_, "__name__") else ""
            )
            scope_info = f" [{token.scope.name}]" if hasattr(token, "scope") else ""
            formatted_lines.append(f"{indent}└─ {token.name}{type_info}{scope_info}\n")

        return "".join(formatted_lines)


class CircularDependencyError(ResolutionError):
    """Raised when a circular dependency is detected during resolution."""

    def __init__(self, token: "Token[Any]", chain: list["Token[Any]"]) -> None:
        """Initialize circular dependency error.

        Args:
            token: The token that created the cycle
            chain: The resolution chain showing the cycle
        """
        # Include the problematic token in the chain to show the full cycle
        full_cycle = chain + [token]
        cycle_names = " -> ".join(t.name for t in full_cycle)

        super().__init__(
            token,
            chain,
            f"Circular dependency detected: {cycle_names}",
        )

        # Override the message to highlight the cycle
        chain_str = self._format_resolution_chain(full_cycle)
        self.args = (
            f"Circular dependency detected for token '{token.name}':\n"
            f"  Dependency cycle:\n{chain_str}"
            f"  Fix: Break the cycle by removing one of the dependencies\n"
            f"  or redesign the dependency structure.",
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
