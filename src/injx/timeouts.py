"""Timeout policies for bounded async operations.

This module provides TimeoutPolicy configuration for controlling
resolution timeouts, cleanup timeouts, and batch operation bounds.
Timeouts prevent indefinite hangs and enable graceful degradation.

Example:
    container = Container(timeout_policy=TimeoutPolicy.default())

    # Or with custom settings
    container = Container(timeout_policy=TimeoutPolicy(
        provider_timeout=10.0,  # 10s per provider
        cleanup_timeout=5.0,    # 5s for cleanup
        batch_timeout=60.0      # 1 minute for batch ops
    ))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class TimeoutPolicy:
    """Timeout configuration for async operations.

    All timeout values are in seconds. None means unlimited (no timeout).

    Attributes:
        provider_timeout: Max time for single provider resolution.
            Applies to each aget() call. Default: None (unlimited).
        cleanup_timeout: Max time for cleanup operations during scope exit.
            Prevents hanging on stuck cleanup. Default: 5.0 seconds.
        batch_timeout: Max time for batch_resolve_async operations.
            Bounds total time for resolving multiple tokens. Default: None.
        max_concurrency: Max parallel resolutions in batch operations.
            Prevents resource exhaustion. Default: 10.

    Example:
        # Production defaults
        policy = TimeoutPolicy.default()

        # Fast timeouts for tests
        policy = TimeoutPolicy.testing()

        # Custom configuration
        policy = TimeoutPolicy(
            provider_timeout=30.0,
            cleanup_timeout=10.0,
            batch_timeout=120.0,
            max_concurrency=20
        )
    """

    provider_timeout: float | None = None
    cleanup_timeout: float = 5.0
    batch_timeout: float | None = None
    max_concurrency: int = 10

    def __post_init__(self) -> None:
        """Validate timeout values."""
        if self.provider_timeout is not None and self.provider_timeout <= 0:
            raise ValueError("provider_timeout must be positive or None")
        if self.cleanup_timeout <= 0:
            raise ValueError("cleanup_timeout must be positive")
        if self.batch_timeout is not None and self.batch_timeout <= 0:
            raise ValueError("batch_timeout must be positive or None")
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")

    @classmethod
    def default(cls) -> Self:
        """Sensible defaults for production use.

        Returns:
            TimeoutPolicy with conservative timeouts suitable for
            most production environments.
        """
        return cls(
            provider_timeout=30.0,  # 30s per provider
            cleanup_timeout=5.0,  # 5s cleanup
            batch_timeout=60.0,  # 1min batch ops
            max_concurrency=10,  # 10 parallel resolutions
        )

    @classmethod
    def testing(cls) -> Self:
        """Fast timeouts for test environments.

        Returns:
            TimeoutPolicy with short timeouts for fast test feedback.
        """
        return cls(
            provider_timeout=1.0,  # 1s per provider
            cleanup_timeout=0.5,  # 500ms cleanup
            batch_timeout=2.0,  # 2s batch ops
            max_concurrency=5,  # 5 parallel resolutions
        )

    @classmethod
    def unlimited(cls) -> Self:
        """No timeouts - use for backward compatibility.

        Returns:
            TimeoutPolicy with no timeouts (original behavior).
        """
        return cls(
            provider_timeout=None,
            cleanup_timeout=30.0,  # Still have cleanup timeout
            batch_timeout=None,
            max_concurrency=100,  # High concurrency limit
        )
