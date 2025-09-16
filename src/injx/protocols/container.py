"""Container protocol for type-safe contracts."""

from typing import Callable, Protocol, TypeVar, runtime_checkable

from ..tokens import Scope, Token

T = TypeVar("T")


@runtime_checkable
class ContainerProtocol(Protocol):
    """Minimal protocol for type checking."""

    def get(self, token: Token[T] | type[T]) -> T:
        """Get a dependency from the container."""
        ...

    def register(
        self, token: Token[T], provider: Callable[..., T], scope: Scope | None = None
    ) -> None:
        """Register a provider in the container."""
        ...

    @classmethod
    def get_active(cls) -> "ContainerProtocol":
        """Get the active container for current context."""
        ...
