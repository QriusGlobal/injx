"""Immutable provider metadata with precomputed cleanup strategy.

This module provides a memory-efficient data structure for storing
provider information with precomputed cleanup strategies.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, TypeVar

from .cleanup_strategy import CleanupStrategy
from .tokens import Scope

if TYPE_CHECKING:
    from .tokens import Token

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ProviderRecord(Generic[T]):
    """Immutable provider metadata with precomputed cleanup strategy.

    A frozen dataclass that stores provider information with its
    precomputed cleanup strategy and scope. Uses __slots__ to minimize
    memory footprint and frozen=True for immutability.

    Enhanced with is_async and dependencies fields for improved
    performance and circular dependency detection.

    Memory usage with slots: ~56 bytes
        - provider: 8 bytes (reference)
        - cleanup: 4 bytes (IntEnum)
        - scope: 4 bytes (Enum)
        - is_async: 1 byte (bool)
        - dependencies: 8 bytes (tuple reference)
        - overhead: ~31 bytes

    Attributes:
        provider: Callable that produces instances of type T
        cleanup: Precomputed cleanup strategy (IntEnum)
        scope: Lifecycle scope for the provider
        is_async: Whether the provider is async (precomputed)
        dependencies: Tuple of dependency tokens for circular detection

    Example:
        >>> provider = lambda: Database()
        >>> record = ProviderRecord.create(provider, Scope.SINGLETON)
        >>> assert record.cleanup == CleanupStrategy.CLOSE
        >>> assert not record.is_async
    """

    provider: Callable[..., T]
    cleanup: CleanupStrategy
    scope: Scope
    is_async: bool
    dependencies: tuple["Token[object]", ...]

    @classmethod
    def create(
        cls,
        provider: Callable[..., T],
        scope: Scope,
        dependencies: tuple["Token[object]", ...] | None = None,
    ) -> ProviderRecord[T]:
        """Create a ProviderRecord with precomputed metadata.

        Factory method that analyzes the provider at registration time to
        determine its cleanup strategy and async nature. This eliminates
        the need for runtime type checking, improving performance.

        The cleanup strategy is determined by analyzing what cleanup protocols
        the provider supports (context manager, close(), aclose(), etc.).

        Args:
            provider: A callable that produces instances of type T.
                     Can be a class, factory function, or lambda.
            scope: The lifecycle scope (SINGLETON, REQUEST, SESSION, TRANSIENT)
                   that determines when instances are created and destroyed.
            dependencies: Optional tuple of dependency tokens for circular
                         dependency detection. If not provided, defaults to
                         an empty tuple.

        Returns:
            ProviderRecord[T]: A new immutable record with precomputed
                              metadata for efficient resource management.

        Example:
            >>> class Database:
            ...     def close(self): pass
            >>> record = ProviderRecord.create(Database, Scope.SINGLETON)
            >>> assert record.cleanup == CleanupStrategy.CLOSE
            >>> assert not record.is_async
            >>> assert record.scope == Scope.SINGLETON
        """
        cleanup = CleanupStrategy.analyze(provider)
        is_async = asyncio.iscoroutinefunction(provider)
        deps = dependencies if dependencies is not None else ()
        return cls(
            provider=provider,
            cleanup=cleanup,
            scope=scope,
            is_async=is_async,
            dependencies=deps,
        )
