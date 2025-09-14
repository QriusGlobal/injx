"""Module-level scope management functions.

Simple functions for scope management without OOP abstraction layers.
Uses ContextVar directly for async task isolation.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar

from .scope_data import ScopeData

# Module-level state, not class state
_current_scope: ContextVar[ScopeData | None] = ContextVar("scope", default=None)


@contextmanager
def request_scope() -> Iterator[ScopeData]:
    """Create and manage a request scope.

    Simple context manager, not a class.

    Yields:
        The scope data for the request
    """
    scope = ScopeData()
    token = _current_scope.set(scope)
    try:
        yield scope
    finally:
        ScopeData.execute_cleanup_sync(scope)
        _current_scope.reset(token)


@asynccontextmanager
async def async_request_scope() -> AsyncIterator[ScopeData]:
    """Async variant of request scope.

    Yields:
        The scope data for the async request
    """
    scope = ScopeData()
    token = _current_scope.set(scope)
    try:
        yield scope
    finally:
        await ScopeData.execute_cleanup_async(scope)
        _current_scope.reset(token)


def get_current_scope() -> ScopeData:
    """Get active scope or raise.

    Simple function, not a class method.

    Returns:
        The current scope data

    Raises:
        RuntimeError: If no active scope
    """
    scope = _current_scope.get()
    if scope is None:
        raise RuntimeError("No active scope")
    return scope


def has_active_scope() -> bool:
    """Check if there's an active scope.

    Returns:
        True if scope is active, False otherwise
    """
    return _current_scope.get() is not None
