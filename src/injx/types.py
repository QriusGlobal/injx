"""Type definitions and aliases for pyinj."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

__all__ = [
    "ProviderSync",
    "ProviderAsync",
    "ProviderLike",
]

T = TypeVar("T")

# Generic provider types
type ProviderSync[T] = Callable[[], T]
type ProviderAsync[T] = Callable[[], Awaitable[T]]
type ProviderLike[T] = ProviderSync[T] | ProviderAsync[T]
