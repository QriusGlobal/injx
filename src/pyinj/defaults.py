"""Default container registry with static accessors.

Provides a neutral indirection for getting/setting the default container
without creating import cycles between modules that need to reference it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .container import Container

# Module-level container storage with proper typing.
# Uses Container type directly for type safety.
_default_container: "Container | None" = None


class DefaultContainer:
    """Container of class-level accessors for the global default container."""

    @staticmethod
    def get() -> "Container":
        """Return the default container, creating it on first access."""
        global _default_container
        if _default_container is None:
            from .container import Container

            _default_container = Container()
        return _default_container

    @staticmethod
    def set(container: "Container") -> None:
        """Replace the default container."""
        global _default_container
        _default_container = container


def get_default_container() -> "Container":
    """Function alias for DefaultContainer.get()."""
    return DefaultContainer.get()


def set_default_container(container: "Container") -> None:
    """Function alias for DefaultContainer.set()."""
    DefaultContainer.set(container)
