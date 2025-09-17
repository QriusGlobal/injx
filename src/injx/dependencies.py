"""Type-safe dependency container for grouped injection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

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

    All dependencies are resolved eagerly at creation time to ensure
    fail-fast behavior and prevent runtime surprises.
    """

    __slots__ = ("_types", "_resolved", "_type_map")

    def __init__(self, container: ContainerProtocol, types: tuple[type, ...]):
        """
        Initialize with eager resolution.

        Args:
            container: Container to resolve from
            types: Tuple of types to resolve
        """
        self._types = types
        self._resolved: dict[type, object] = {}
        self._type_map: dict[str, type] = {}

        # Eagerly resolve all dependencies
        for t in types:
            self._resolved[t] = container.get(t)
            # Map lowercase names for convenience
            self._type_map[t.__name__.lower()] = t

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
        if key not in self._resolved:
            raise KeyError(
                f"Type {key.__name__} not in dependencies. "
                f"Available: {', '.join(t.__name__ for t in self._types)}"
            )
        return self._resolved[key]

    def get(self, key: type[T], default: T | None = None) -> T | None:
        """Safe access with default."""
        return self._resolved.get(key, default)  # type: ignore

    def __contains__(self, key: type) -> bool:
        """Check if dependency exists."""
        return key in self._resolved

    def __len__(self) -> int:
        """Number of dependencies."""
        return len(self._resolved)

    def __repr__(self) -> str:
        """String representation."""
        types = ", ".join(t.__name__ for t in self._types)
        return f"Dependencies[{types}]"

    def __bool__(self) -> bool:
        """Check if any dependencies exist."""
        return bool(self._resolved)
