from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SupportsClose(Protocol):
    """Protocol for resources that can be synchronously closed."""

    def close(self) -> None: ...


@runtime_checkable
class SupportsAsyncClose(Protocol):
    """Protocol for resources that can be asynchronously closed."""

    async def aclose(self) -> None: ...
