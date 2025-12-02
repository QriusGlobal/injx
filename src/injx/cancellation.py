"""Cancellation support for async dependency resolution.

This module provides cooperative cancellation for dependency resolution chains.
Cancellation tokens propagate through resolution graphs, allowing graceful
termination of long-running operations.

Example:
    async with container.with_cancellation() as token:
        task = asyncio.create_task(container.aget(SlowService))

        await asyncio.sleep(0.5)
        if should_cancel:
            token.cancel("User requested cancellation")

        try:
            result = await task
        except asyncio.CancelledError:
            print("Resolution was cancelled")
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextvars import ContextVar

# ContextVar for propagating cancellation through async resolution
_cancellation_token: ContextVar[CancellationToken | None] = ContextVar(
    "injx_cancellation_token",
    default=None,
)


class CancellationToken:
    """Cooperative cancellation for dependency resolution chains.

    CancellationToken enables graceful cancellation of ongoing resolution
    operations. When cancelled, all resolution operations that check the
    token will raise CancelledError.

    This is a cooperative mechanism - resolution code must explicitly check
    for cancellation at appropriate points.

    Attributes:
        is_cancelled: Whether cancellation has been requested
        reason: The cancellation reason (if cancelled)

    Example:
        token = CancellationToken()

        # Register callback for cancellation notification
        token.on_cancel(lambda: print("Cancelled!"))

        # Request cancellation
        token.cancel("Operation timed out")

        # Check in resolution code
        token.raise_if_cancelled()  # Raises CancelledError
    """

    __slots__ = ("_cancelled", "_reason", "_callbacks")

    def __init__(self) -> None:
        """Initialize an uncancelled token."""
        self._cancelled: bool = False
        self._reason: str | None = None
        self._callbacks: list[Callable[[], None]] = []

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled

    @property
    def reason(self) -> str | None:
        """Get the cancellation reason, if cancelled."""
        return self._reason

    def cancel(self, reason: str = "Operation cancelled") -> None:
        """Request cancellation of ongoing operations.

        This method is idempotent - calling it multiple times has no effect
        after the first call.

        Args:
            reason: Human-readable reason for cancellation
        """
        if not self._cancelled:
            self._cancelled = True
            self._reason = reason
            # Notify all registered callbacks
            for callback in self._callbacks:
                try:
                    callback()
                except Exception:
                    # Don't let callback errors prevent cancellation
                    pass

    def raise_if_cancelled(self) -> None:
        """Raise CancelledError if cancellation has been requested.

        Call this at appropriate checkpoints during resolution to
        enable cooperative cancellation.

        Raises:
            asyncio.CancelledError: If cancellation was requested
        """
        if self._cancelled:
            raise asyncio.CancelledError(self._reason or "Cancelled")

    def on_cancel(self, callback: Callable[[], None]) -> None:
        """Register a callback to invoke when cancelled.

        If already cancelled, the callback is invoked immediately.

        Args:
            callback: Function to call on cancellation
        """
        if self._cancelled:
            try:
                callback()
            except Exception:
                pass
        else:
            self._callbacks.append(callback)

    @staticmethod
    def get_current() -> CancellationToken | None:
        """Get the cancellation token for the current context.

        Returns:
            The current CancellationToken, or None if not in a cancellation context
        """
        return _cancellation_token.get()

    @staticmethod
    def check_cancelled() -> None:
        """Check the current context for cancellation.

        Convenience method that gets the current token (if any) and checks
        if cancellation was requested.

        Raises:
            asyncio.CancelledError: If cancellation was requested
        """
        token = _cancellation_token.get()
        if token is not None:
            token.raise_if_cancelled()


def set_cancellation_token(token: CancellationToken | None) -> CancellationToken | None:
    """Set the cancellation token for the current context.

    Internal API used by Container.with_cancellation().

    Args:
        token: The cancellation token to set, or None to clear

    Returns:
        The previous token (for restoration)
    """
    old = _cancellation_token.get()
    _cancellation_token.set(token)
    return old


def reset_cancellation_token(token: CancellationToken | None) -> None:
    """Reset the cancellation token to a previous value.

    Internal API used by Container.with_cancellation().

    Args:
        token: The token to restore
    """
    _cancellation_token.set(token)
