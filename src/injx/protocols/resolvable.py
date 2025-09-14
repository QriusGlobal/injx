from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

if True:
    try:
        from ..tokens import Token
    except Exception:
        from typing import Any as Token

T = TypeVar("T")


@runtime_checkable
class Resolvable(Protocol[T]):
    """Protocol for containers that can resolve dependencies sync/async."""

    def get(self, token: Token[T] | type[T]) -> T: ...

    async def aget(self, token: Token[T] | type[T]) -> T: ...
