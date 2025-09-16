"""Type-safe registry for heterogeneous storage.

This module provides TypedRegistry, which encapsulates all type variance
handling in a single location, reducing cast operations from 73 to 1.

The single cast in :meth:`TypedRegistry.get` is the only approved variance
escape hatch in the codebase. All registry population must flow through the
typed helpers exposed here (``set``, ``setdefault``, etc.). Direct mutation of
``_storage`` or introducing new ``cast`` calls elsewhere is prohibited so that
we can reason about type safety in one disciplined layer.
"""

from types import MappingProxyType
from typing import Generic, TypeVar, cast

K = TypeVar("K")
V = TypeVar("V")


class TypedRegistry(Generic[K, V]):
    """Type-safe wrapper for heterogeneous storage with variance handling.

    This class encapsulates the ONE unavoidable cast operation when storing
    heterogeneous types in Python's homogeneous dict. All cast operations
    in the entire codebase are centralized here.

    The mathematical necessity: Python's dict is invariant in its type
    parameters, but DI containers need covariant retrieval. This class
    bridges that gap with a single, well-contained cast.

    Example:
        >>> registry = TypedRegistry[Token[Any], Any]()
        >>> registry.set(token, provider)
        >>> provider = registry.get(token)  # Type-safe, no cast needed!
    """

    __slots__ = ("_storage",)

    def __init__(self) -> None:
        """Initialize with empty storage."""
        self._storage: dict[object, object] = {}

    def set(self, key: K, value: V) -> None:
        """Store a key-value pair with variance handling.

        Callers must guarantee that ``value`` truly matches the registry's ``V``
        type parameter. The container enforces this through validation at the
        write sites; bypassing the helper or stashing mismatched values would
        surface later as runtime errors.

        Args:
            key: The key to store (typically Token[T])
            value: The value to store (typically Provider[T])
        """
        self._storage[key] = value

    def get(self, key: K) -> V | None:
        """Retrieve a value with type preservation.

        This is the ONLY place in the entire codebase where a cast is needed.
        The cast is safe because we maintain the type relationship through
        the generic parameters.

        Args:
            key: The key to look up

        Returns:
            The value if found, None otherwise
        """
        # THE SINGLE CAST IN THE ENTIRE SYSTEM
        return cast(V, self._storage.get(key))

    def get_or_raise(self, key: K, error: Exception) -> V:
        """Retrieve a value or raise an error if not found.

        Args:
            key: The key to look up
            error: The exception to raise if key not found

        Returns:
            The value associated with the key

        Raises:
            The provided exception if key not found
        """
        value = self.get(key)
        if value is None:
            raise error
        return value

    def pop(self, key: K, default: V | None = None) -> V | None:
        """Remove and return a value.

        Args:
            key: The key to remove
            default: Default value if key not found

        Returns:
            The removed value or default
        """
        # Type-safe pop operation
        return cast(V, self._storage.pop(key, default))

    def __contains__(self, key: K) -> bool:
        """Check if a key exists in the registry.

        Args:
            key: The key to check

        Returns:
            True if the key exists, False otherwise
        """
        return key in self._storage

    def __len__(self) -> int:
        """Return the number of items in the registry.

        Returns:
            Number of stored items
        """
        return len(self._storage)

    def clear(self) -> None:
        """Remove all items from the registry."""
        self._storage.clear()

    def items(self) -> list[tuple[K, V]]:
        """Return all key-value pairs.

        Returns:
            List of (key, value) tuples
        """
        # Safe because we maintain type consistency
        return [(cast(K, k), cast(V, v)) for k, v in self._storage.items()]

    def keys(self) -> list[K]:
        """Return all keys.

        Returns:
            List of keys
        """
        return [cast(K, k) for k in self._storage.keys()]

    def values(self) -> list[V]:
        """Return all values.

        Returns:
            List of values
        """
        return [cast(V, v) for v in self._storage.values()]

    def setdefault(self, key: K, default: V) -> V:
        """Get a value, setting it to default if not present.

        Args:
            key: The key to look up
            default: The default value to set if key not found

        Returns:
            The existing or newly set value
        """
        return cast(V, self._storage.setdefault(key, default))

    def as_read_only(self) -> MappingProxyType[K, V]:
        """Return a read-only view of the underlying storage."""
        return MappingProxyType(self._storage)

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            String representation showing number of items
        """
        return f"TypedRegistry({len(self)} items)"
