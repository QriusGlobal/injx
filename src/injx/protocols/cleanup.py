"""Cleanup protocols for resource management.

These protocols define the contracts for resources that require cleanup,
enabling type-safe resource management and precomputed cleanup strategies.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CleanupSync(Protocol):
    """Protocol for synchronous resource cleanup."""

    def close(self) -> None:
        """Close the resource synchronously."""
        ...


@runtime_checkable
class CleanupAsync(Protocol):
    """Protocol for asynchronous resource cleanup."""

    async def aclose(self) -> None:
        """Close the resource asynchronously."""
        ...


@runtime_checkable
class ContextManagedSync(Protocol):
    """Protocol for synchronous context managers."""

    def __enter__(self) -> Any:
        """Enter the context."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context."""
        ...


@runtime_checkable
class ContextManagedAsync(Protocol):
    """Protocol for asynchronous context managers."""

    async def __aenter__(self) -> Any:
        """Enter the async context."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context."""
        ...
