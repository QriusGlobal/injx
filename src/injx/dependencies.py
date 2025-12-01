"""Type-safe dependency container for grouped injection."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Generic, Mapping, TypeVar

if TYPE_CHECKING:
    from .protocols.container import ContainerProtocol

# Support variadic generics (Python 3.11+)
try:
    from typing import TypeVarTuple

    Ts = TypeVarTuple("Ts")
except ImportError:
    # Fallback for Python < 3.11
    Ts = TypeVar("Ts")  # type: ignore

T = TypeVar("T")


class Dependencies(Generic[*Ts]):  # type: ignore
    """
    Type-safe container for multiple dependencies with structured concurrency.

    Example (Sync):
        @inject
        def process(deps: Dependencies[Database, Logger]):
            db = deps[Database]  # Type-safe access
            logger = deps[Logger]

    Example (Async):
        @inject
        async def process(deps: Dependencies[AsyncDB, AsyncCache]):
            # Dependencies are automatically awaitable
            db = deps[AsyncDB]
            cache = deps[AsyncCache]
            # All dependencies resolved in parallel with TaskGroup

    The Dependencies container uses structured concurrency:
    - Sync context: Uses resolve() for synchronous resolution
    - Async context: TaskGroup with automatic cancellation on failure
    - Direct usage: Falls back to synchronous resolution

    Structured Concurrency Benefits:
    - If any dependency fails, remaining resolutions are cancelled
    - No wasted work on dependencies that won't be used
    - Clear error aggregation via ExceptionGroup
    """

    __slots__ = ("_container", "_types", "_resolved", "__weakref__")

    def __init__(self, container: ContainerProtocol, types: tuple[type, ...]):
        """
        Initialize with container and types for lazy resolution.

        Args:
            container: Container to resolve from
            types: Tuple of types to resolve
        """
        self._container = container
        self._types = types
        self._resolved: Mapping[type, Any] | None = None

    def resolve(self) -> None:
        """
        Synchronously resolve all dependencies.

        Called by the injection layer in synchronous contexts. For async contexts,
        the Dependencies object is awaitable and will resolve dependencies in parallel.
        """
        if self._resolved is None:
            resolved: dict[type, Any] = {t: self._container.get(t) for t in self._types}
            self._resolved = MappingProxyType(resolved)

    def __await__(self) -> Generator[Any, None, Dependencies[*Ts]]:  # type: ignore[misc]
        """
        Make Dependencies awaitable for async resolution.

        This enables the Dependencies container to be used with await syntax,
        automatically resolving all dependencies in parallel when in an async context.
        """
        return self._resolve_async().__await__()  # type: ignore[return-value]

    async def _resolve_async(self) -> Dependencies[*Ts]:  # type: ignore
        """
        Asynchronously resolve all dependencies with structured concurrency.

        Uses TaskGroup for automatic cancellation if any resolution fails,
        preventing wasted work on dependencies that won't be used due to
        earlier failures. This provides better resource utilization and
        clearer error reporting compared to asyncio.gather.

        Raises:
            ResolutionError: If any dependency resolution fails
        """
        from .cancellation import CancellationToken

        if self._resolved is None:
            # Check for cancellation before batch resolution
            CancellationToken.check_cancelled()

            resolved: dict[type, Any] = {}

            async def resolve_one(typ: type) -> None:
                """Resolve single dependency and store result."""
                CancellationToken.check_cancelled()
                resolved[typ] = await self._container.aget(typ)

            # Resolve all dependencies concurrently with TaskGroup
            async with asyncio.TaskGroup() as tg:
                for typ in self._types:
                    tg.create_task(resolve_one(typ), name=f"resolve_{typ.__name__}")

            self._resolved = MappingProxyType(resolved)
        return self

    def __getitem__(self, key: type[T]) -> T:
        """
        Type-safe dependency access.

        Args:
            key: Type to retrieve

        Returns:
            Resolved instance of the type

        Raises:
            KeyError: If type not in dependencies
            RuntimeError: If dependencies not resolved
        """
        # For direct usage (not via @inject), resolve sync on first access
        if self._resolved is None:
            self.resolve()

        # After resolve(), _resolved is guaranteed to be set
        resolved = self._resolved
        if resolved is None:  # This should never happen, but satisfies type checker
            raise RuntimeError("Failed to resolve dependencies")

        if key not in resolved:
            raise KeyError(
                f"Type {key.__name__} not in dependencies. "
                f"Available: {', '.join(t.__name__ for t in self._types)}"
            )
        return resolved[key]

    def get(self, key: type[T], default: T | None = None) -> T | None:
        """Safe access with default."""
        # Ensure resolved for direct usage
        if self._resolved is None:
            self.resolve()

        resolved = self._resolved
        if resolved is None:  # Should never happen
            return default
        return resolved.get(key, default)

    def __contains__(self, key: type) -> bool:
        """Check if dependency exists."""
        # Ensure resolved for direct usage
        if self._resolved is None:
            self.resolve()

        resolved = self._resolved
        return resolved is not None and key in resolved

    def __len__(self) -> int:
        """Number of dependencies."""
        # Ensure resolved for direct usage
        if self._resolved is None:
            self.resolve()

        resolved = self._resolved
        return len(resolved) if resolved is not None else 0

    def __repr__(self) -> str:
        """String representation."""
        types = ", ".join(t.__name__ for t in self._types)
        return f"Dependencies[{types}]"

    def __bool__(self) -> bool:
        """Check if any dependencies exist."""
        return len(self._types) > 0
