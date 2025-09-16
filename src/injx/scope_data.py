"""Functional scope management with class methods.

This module provides a simple data container with associated pure functions
for scope management, avoiding OOP ceremony while maintaining organization.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Awaitable, Callable, TypeVar, cast

from .cleanup_strategy import CleanupStrategy
from .exceptions import AsyncCleanupRequiredError
from .provider_spec import ProviderSpec
from .tokens import Token

T = TypeVar("T")
CleanupTask = Callable[[], None] | Callable[[], Awaitable[None]]


@dataclass(slots=True)
class ScopeData:
    """Data container for scope-specific instance cache and cleanup tasks.

    A simple data structure that holds cached instances and their cleanup
    tasks for a specific scope (request, session, etc.). Uses class methods
    for operations instead of instance methods, following a functional
    programming approach.

    This is not a complex object with behavior, but rather structured data
    with associated pure functions as class methods. This design eliminates
    OOP ceremony while maintaining code organization.

    Attributes:
        cache: Dictionary mapping tokens to cached instances
        cleanup: Deque of cleanup tasks in LIFO order

    Example:
        >>> scope = ScopeData()
        >>> token = Token("db", Database)
        >>> db = Database()
        >>> record = ProviderSpec.create(Database, Scope.REQUEST)
        >>> ScopeData.store(scope, token, db, record)
        >>> retrieved = ScopeData.get(scope, token)
        >>> assert retrieved is db
    """

    cache: dict[Token[object], object] = field(default_factory=dict)
    cleanup: deque[CleanupTask] = field(default_factory=deque)

    @classmethod
    def store(
        cls, scope: ScopeData, token: Token[T], instance: T, record: ProviderSpec[T]
    ) -> None:
        """Store an instance in scope cache and register its cleanup task.

        Stores the instance in the scope's cache and, if the provider record
        indicates cleanup is needed, creates and registers a cleanup task.
        This is an explicit mutation point that modifies the scope in place.

        The cleanup task is added to the front of the deque (appendleft) to
        ensure LIFO (Last In, First Out) cleanup order - resources are cleaned
        up in reverse order of their creation.

        Args:
            scope: The scope data to modify (mutated in place)
            token: The token identifying this instance
            instance: The instance to store in the cache
            record: The provider specification describing cleanup strategy

        Note:
            Type casts to Token[object] and object are necessary because
            the cache uses object types internally for type erasure, but
            type safety is restored in the get() method.
        """
        # Controlled type cast point
        scope.cache[cast(Token[object], token)] = cast(object, instance)

        if record.cleanup != CleanupStrategy.NONE:
            # Create task at storage time, not cleanup time
            task = CleanupStrategy.create_task(instance, record.cleanup)
            scope.cleanup.appendleft(task)  # LIFO order

    @classmethod
    def get(cls, scope: ScopeData, token: Token[T]) -> T | None:
        """Type-safe retrieval from scope cache.

        Restores type information lost in internal storage.

        Args:
            scope: The scope data to read from
            token: The token to look up

        Returns:
            The cached instance or None
        """
        # Controlled type cast point
        value = scope.cache.get(cast(Token[object], token))
        return cast(T, value) if value is not None else None

    @classmethod
    def execute_cleanup_sync(cls, scope: ScopeData) -> None:
        """Execute all cleanup tasks synchronously.

        LIFO order guaranteed by deque.pop().

        Args:
            scope: The scope data with cleanup tasks

        Raises:
            AsyncCleanupRequiredError: If async cleanup found in sync context
        """
        while scope.cleanup:
            task = scope.cleanup.pop()
            result = task()
            if asyncio.iscoroutine(result):
                raise AsyncCleanupRequiredError(
                    "scope", "Async cleanup in sync context. Use async scope."
                )

    @classmethod
    async def execute_cleanup_async(cls, scope: ScopeData) -> None:
        """Execute all cleanup tasks asynchronously.

        Handles both sync and async cleanup tasks.

        Args:
            scope: The scope data with cleanup tasks
        """
        while scope.cleanup:
            task = scope.cleanup.pop()
            result = task()
            if asyncio.iscoroutine(result):
                await result
