"""Token implementation with immutability and optimizations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from types import MappingProxyType
from typing import Any, Generic, TypeVar, cast

__all__ = ["Scope", "Token", "TokenFactory"]

T = TypeVar("T")


class Scope(Enum):
    """Lifecycle scope for dependencies.

    Values:
        SINGLETON: One instance for the process/container.
        REQUEST: One instance per request context.
        SESSION: One instance per longer-lived session context.
        TRANSIENT: A new instance for every resolution.
    """

    SINGLETON = auto()  # Process-wide singleton
    REQUEST = auto()  # Request/context scoped
    SESSION = auto()  # Session scoped
    TRANSIENT = auto()  # New instance every time


@dataclass(frozen=True, slots=True)
class Token(Generic[T]):
    """Immutable, hashable identifier for a typed dependency.

    Args:
        name: Human-readable name for the binding.
        type_: The expected Python type of the dependency.
        scope: Lifecycle scope. Defaults to TRANSIENT.
        qualifier: Optional qualifier to differentiate multiple bindings of the same type.
        tags: Optional tags for discovery/metadata.

    Example:
        LOGGER = Token[Logger]("logger", scope=Scope.SINGLETON)
    """

    name: str
    type_: type[T]
    scope: Scope = Scope.TRANSIENT
    qualifier: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    _hash: int = field(init=False, repr=False, compare=False)
    _metadata: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        hash_tuple = (
            self.name,
            self.type_.__module__ if hasattr(self.type_, "__module__") else "",
            self.type_.__name__ if hasattr(self.type_, "__name__") else str(self.type_),
            self.scope.value,
            self.qualifier,
            self.tags,
        )
        object.__setattr__(self, "_hash", hash(hash_tuple))

        if self._metadata:
            object.__setattr__(self, "_metadata", MappingProxyType(self._metadata))

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Token):
            return False
        other_token = cast("Token[object]", other)
        if self._hash != other_token._hash:
            return False
        return (
            self.name == other.name
            and self.type_ == other_token.type_
            and self.scope == other_token.scope
            and self.qualifier == other_token.qualifier
            and self.tags == other_token.tags
        )

    @property
    def metadata(self) -> MappingProxyType[str, Any]:
        """Read-only view of metadata."""
        return self._metadata  # type: ignore[return-value]

    @property
    def qualified_name(self) -> str:
        """Fully qualified name including module, type, qualifier, and token name."""
        parts: list[str] = []
        if hasattr(self.type_, "__module__"):
            parts.append(self.type_.__module__)  # type: ignore[arg-type]
        parts.append(getattr(self.type_, "__name__", str(self.type_)))
        if self.qualifier:
            parts.append(self.qualifier)
        parts.append(self.name)
        return ".".join(parts)

    def with_scope(self, scope: Scope) -> Token[T]:
        """Return a copy of this token with a different scope."""
        return Token(
            name=self.name,
            type_=self.type_,
            scope=scope,
            qualifier=self.qualifier,
            tags=self.tags,
            _metadata=dict(self._metadata) if self._metadata else {},
        )

    def with_qualifier(self, qualifier: str) -> Token[T]:
        """Return a copy of this token with a qualifier."""
        return Token(
            name=self.name,
            type_=self.type_,
            scope=self.scope,
            qualifier=qualifier,
            tags=self.tags,
            _metadata=dict(self._metadata) if self._metadata else {},
        )

    def with_tags(self, *tags: str) -> Token[T]:
        """Return a copy of this token with tags merged in (set semantics)."""
        return Token(
            name=self.name,
            type_=self.type_,
            scope=self.scope,
            qualifier=self.qualifier,
            tags=tuple(set(self.tags) | set(tags)),
            _metadata=dict(self._metadata) if self._metadata else {},
        )

    def __repr__(self) -> str:
        type_name = getattr(self.type_, "__name__", str(self.type_))
        parts = [f"Token('{self.name}', {type_name}"]
        if self.scope != Scope.TRANSIENT:
            parts.append(f", scope={self.scope.name}")
        if self.qualifier:
            parts.append(f", qualifier='{self.qualifier}'")
        if self.tags:
            parts.append(f", tags={self.tags}")
        return "".join(parts) + ")"

    def validate(self, instance: object) -> bool:
        """Validate instance type against the token's expected type.

        Returns False only when ``isinstance(instance, type_)`` is definitively False.
        If runtime type information is insufficient, returns True.
        """
        try:
            return isinstance(instance, self.type_)
        except Exception:
            return True


class TokenFactory:
    """Factory for creating and caching commonly used tokens."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, type[Any], Scope, str | None], Token[Any]] = {}

    def create(
        self,
        name: str,
        type_: type[T],
        scope: Scope = Scope.TRANSIENT,
        qualifier: str | None = None,
        tags: tuple[str, ...] = (),
    ) -> Token[T]:
        """Create a token, with a small internal cache for common shapes."""
        cache_key = (name, type_, scope, qualifier)
        if not tags and cache_key in self._cache:
            return cast(Token[T], self._cache[cache_key])
        token: Token[T] = Token(
            name=name, type_=type_, scope=scope, qualifier=qualifier, tags=tags
        )
        if not tags:
            self._cache[cache_key] = cast(Token[Any], token)
        return token

    def singleton(self, name: str, type_: type[T]) -> Token[T]:
        """Create a singleton-scoped token."""
        return self.create(name, type_, scope=Scope.SINGLETON)

    def request(self, name: str, type_: type[T]) -> Token[T]:
        """Create a request-scoped token."""
        return self.create(name, type_, scope=Scope.REQUEST)

    def session(self, name: str, type_: type[T]) -> Token[T]:
        """Create a session-scoped token."""
        return self.create(name, type_, scope=Scope.SESSION)

    def transient(self, name: str, type_: type[T]) -> Token[T]:
        """Create a transient-scoped token (default)."""
        return self.create(name, type_, scope=Scope.TRANSIENT)

    def qualified(
        self, qualifier: str, type_: type[T], scope: Scope = Scope.TRANSIENT
    ) -> Token[T]:
        """Create a qualified token for the given type and scope."""
        name = getattr(type_, "__name__", str(type_))
        return self.create(name, type_, scope=scope, qualifier=qualifier)

    def clear_cache(self) -> None:
        """Clear the internal token cache."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        """Number of cached token shapes currently held."""
        return len(self._cache)


# test comment
