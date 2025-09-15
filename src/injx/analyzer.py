"""Pure dependency analysis functions for the container."""

from __future__ import annotations

from typing import Any, Optional, Type, get_type_hints


def analyze_dependencies(cls: Type[Any]) -> dict[str, Type[Any]]:
    """Analyze class constructor dependencies.

    Args:
        cls: The class to analyze

    Returns:
        Dictionary of parameter names to their types
    """
    try:
        hints = get_type_hints(cls.__init__)
        return {
            k: v
            for k, v in hints.items()
            if k not in ("self", "return") and isinstance(v, type)
        }
    except (TypeError, AttributeError):
        return {}


def should_auto_register(cls: Type[Any]) -> bool:
    """Check if a class should be auto-registered.

    Args:
        cls: The class to check

    Returns:
        True if the class has __injectable__ = True
    """
    return getattr(cls, "__injectable__", False) is True


def get_token_metadata(cls: Type[Any]) -> tuple[str, Any]:
    """Extract token metadata from an injectable class.

    Args:
        cls: The injectable class

    Returns:
        Tuple of (token_name, scope)
    """
    from injx.tokens import Scope

    token_name = getattr(cls, "__token_name__", cls.__name__.lower())
    scope = getattr(cls, "__scope__", Scope.TRANSIENT)

    return (token_name, scope)


def is_valid_provider(provider: Any) -> bool:
    """Validate that a provider is callable.

    Args:
        provider: The provider to validate

    Returns:
        True if the provider is callable
    """
    return callable(provider)


def extract_type_from_token(token: Any) -> Optional[Type[Any]]:
    """Extract the type from a Token instance.

    Args:
        token: The token to extract from

    Returns:
        The type if token is a Token[T], None otherwise
    """
    from injx.tokens import Token

    if isinstance(token, Token):
        # Token.type_ is always a Type[Any]
        # Use cast to satisfy type checker since we know Token has type_
        from typing import cast

        token_obj = cast(Any, token)  # Cast to Any to avoid type issues
        return getattr(token_obj, "type_", None)
    return None
