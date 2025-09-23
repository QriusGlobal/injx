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
    Type-safe container for multiple dependencies.

    Example:
        @inject
        def process(deps: Dependencies[Database, Logger]):
            db = deps[Database]  # Type-safe access
            logger = deps[Logger]

    Dependencies are lazily resolved by the injection layer based on
    the execution context (sync or async). Direct usage falls back
    to synchronous resolution for backward compatibility.
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
        """Synchronously resolve all dependencies. Called by injection layer."""
        if self._resolved is None:
            resolved = {t: self._container.get(t) for t in self._types}
            self._resolved = MappingProxyType(resolved)

    def __await__(self) -> Generator[Any, None, Dependencies[*Ts]]:  # type: ignore
        """Make Dependencies awaitable for async resolution."""
        return self._resolve_async().__await__()

    async def _resolve_async(self) -> Dependencies[*Ts]:  # type: ignore
        """Asynchronously resolve all dependencies in parallel."""
        if self._resolved is None:
            # Resolve all dependencies concurrently for performance
            tasks = [self._container.aget(t) for t in self._types]
            results = await asyncio.gather(*tasks)
            resolved = dict(zip(self._types, results, strict=False))
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
        """
        # For direct usage (not via @inject), resolve sync on first access
        if self._resolved is None:
            self.resolve()

        if key not in self._resolved:
            raise KeyError(
                f"Type {key.__name__} not in dependencies. "
                f"Available: {', '.join(t.__name__ for t in self._types)}"
            )
        return self._resolved[key]

    def get(self, key: type[T], default: T | None = None) -> T | None:
        """Safe access with default."""
        # Ensure resolved for direct usage
        if self._resolved is None:
            self.resolve()
        return self._resolved.get(key, default)  # type: ignore

    def __contains__(self, key: type) -> bool:
        """Check if dependency exists."""
        # Ensure resolved for direct usage
        if self._resolved is None:
            self.resolve()
        return key in self._resolved

    def __len__(self) -> int:
        """Number of dependencies."""
        # Ensure resolved for direct usage
        if self._resolved is None:
            self.resolve()
        return len(self._resolved)

    def __repr__(self) -> str:
        """String representation."""
        types = ", ".join(t.__name__ for t in self._types)
        return f"Dependencies[{types}]"

    def __bool__(self) -> bool:
        """Check if any dependencies exist."""
        return len(self._types) > 0
