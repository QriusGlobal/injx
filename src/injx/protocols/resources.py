from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SupportsClose(Protocol):
    """Protocol for resources that support synchronous cleanup.

    This protocol identifies resources that implement the standard
    Python context manager interface and can be cleaned up synchronously.
    Examples include file handles, database connections, and network sockets.
    """

    def close(self) -> None:
        """Close the resource and release any held resources.

        This method should be idempotent - calling it multiple times
        should not cause errors.
        """
        ...

    def __enter__(self) -> "SupportsClose":
        """Enter the resource context manager.

        Returns:
            Self for use in with statements
        """
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the resource context manager with cleanup."""
        ...


@runtime_checkable
class SupportsAsyncClose(Protocol):
    """Protocol for resources that support asynchronous cleanup.

    This protocol identifies resources that implement the async context
    manager interface and require asynchronous cleanup. Examples include
    async database connections, async HTTP clients, and async file handles.
    """

    async def aclose(self) -> None:
        """Asynchronously close the resource and release any held resources.

        This method should be idempotent - calling it multiple times
        should not cause errors.
        """
        ...

    async def __aenter__(self) -> "SupportsAsyncClose":
        """Enter the async resource context manager.

        Returns:
            Self for use in async with statements
        """
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the async resource context manager with cleanup."""
        ...


@runtime_checkable
class SupportsLifecycle(Protocol):
    """Protocol for resources that support both sync and async cleanup.

    This protocol identifies resources that can be cleaned up either
    synchronously or asynchronously, depending on the context in which
    they are used.
    """

    def close(self) -> None:
        """Synchronously close the resource."""
        ...

    async def aclose(self) -> None:
        """Asynchronously close the resource."""
        ...

    def __enter__(self) -> "SupportsLifecycle":
        """Enter the resource context manager."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the resource context manager."""
        ...

    async def __aenter__(self) -> "SupportsLifecycle":
        """Enter the async resource context manager."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the async resource context manager."""
        ...
