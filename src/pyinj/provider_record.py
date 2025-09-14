"""Immutable provider metadata with precomputed cleanup strategy.

This module provides a memory-efficient data structure for storing
provider information with precomputed cleanup strategies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from .cleanup_strategy import CleanupStrategy
from .tokens import Scope

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ProviderRecord(Generic[T]):
    """Immutable provider metadata with precomputed cleanup strategy.
    
    A frozen dataclass that stores provider information with its
    precomputed cleanup strategy and scope. Uses __slots__ to minimize
    memory footprint and frozen=True for immutability.
    
    Memory usage with slots: ~32 bytes
        - provider: 8 bytes (reference)
        - cleanup: 4 bytes (IntEnum)
        - scope: 4 bytes (Enum) 
        - overhead: ~16 bytes
    
    Attributes:
        provider: Callable that produces instances of type T
        cleanup: Precomputed cleanup strategy (IntEnum)
        scope: Lifecycle scope for the provider
        
    Example:
        >>> provider = lambda: Database()
        >>> record = ProviderRecord.create(provider, Scope.SINGLETON)
        >>> assert record.cleanup == CleanupStrategy.CLOSE
    """

    provider: Callable[..., T]
    cleanup: CleanupStrategy
    scope: Scope

    @classmethod
    def create(cls, provider: Callable[..., T], scope: Scope) -> ProviderRecord[T]:
        """Create a ProviderRecord with precomputed cleanup strategy.
        
        Factory method that analyzes the provider at registration time to
        determine its cleanup strategy. This eliminates the need for runtime
        type checking during cleanup, improving performance.
        
        The cleanup strategy is determined by analyzing what cleanup protocols
        the provider supports (context manager, close(), aclose(), etc.).
        
        Args:
            provider: A callable that produces instances of type T.
                     Can be a class, factory function, or lambda.
            scope: The lifecycle scope (SINGLETON, REQUEST, SESSION, TRANSIENT)
                   that determines when instances are created and destroyed.
            
        Returns:
            ProviderRecord[T]: A new immutable record with precomputed cleanup
                              strategy for efficient resource management.
            
        Example:
            >>> class Database:
            ...     def close(self): pass
            >>> record = ProviderRecord.create(Database, Scope.SINGLETON)
            >>> assert record.cleanup == CleanupStrategy.CLOSE
            >>> assert record.scope == Scope.SINGLETON
        """
        cleanup = CleanupStrategy.analyze(provider)
        return cls(provider=provider, cleanup=cleanup, scope=scope)
