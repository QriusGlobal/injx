"""Injx - Type-safe dependency injection for modern Python.

Status: Alpha - APIs will change. Not recommended for production use.

Highlights:
- Immutable tokens with pre-computed hashes (O(1) lookups)
- ContextVar-based scoping for async and thread safety
- `@inject` decorator (FastAPI-inspired) and lightweight markers
- Scala-style "given" instances for ergonomic overrides
- Zero runtime dependencies

Quick start:
    from injx import Container, Token, Scope

    container = Container()
    DB = Token[Database]("database")
    container.register(DB, create_database, scope=Scope.SINGLETON)

    db = container.get(DB)
    # ... use db ...
"""

from injx._metadata import __author__, __docs__, __email__, __org__, __repo__
from injx._version import __version__
from injx.container import Container
from injx.contextual import ContextualContainer, RequestScope, SessionScope

# Compatibility imports - these will be deprecated
from injx.exceptions import CircularDependencyError, InjxError, ResolutionError
from injx.injection import Depends, Given, Inject, inject
from injx.metaclasses import Injectable
from injx.tokens import Scope, Token, TokenFactory

__all__ = [
    # Core classes
    "Container",
    "ContextualContainer",
    "Depends",
    "Given",
    "Inject",
    "Injectable",
    "RequestScope",
    "Scope",
    "SessionScope",
    "Token",
    "TokenFactory",
    # Exceptions
    "InjxError",
    "ResolutionError",
    "CircularDependencyError",
    # Functions
    "get_default_container",
    "inject",
    "set_default_container",
    # Metadata
    "__version__",
    "__author__",
    "__docs__",
    "__email__",
    "__org__",
    "__repo__",
]


# Compatibility functions with deprecation warnings
def get_default_container():
    """Deprecated: Use Container.get_active() instead.

    Will be removed in v2.0.0.
    """
    import warnings

    warnings.warn(
        "get_default_container() is deprecated. Use Container.get_active() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return Container.get_active()


def set_default_container(container):
    """Deprecated: Use Container.set_active() instead.

    Will be removed in v2.0.0.
    """
    import warnings

    warnings.warn(
        "set_default_container() is deprecated. Use Container.set_active() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    Container.set_active(container)
