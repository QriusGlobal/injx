"""Contextual abstractions for dependency injection using contextvars."""

from __future__ import annotations

import asyncio
from collections import ChainMap, deque
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from contextvars import Token as ContextToken
from types import TracebackType
from typing import Any, Awaitable, Callable, TypeVar, cast

from .cleanup_strategy import CleanupStrategy
from .exceptions import AsyncCleanupRequiredError
from .tokens import Scope, Token

__all__ = [
    "ContextualContainer",
    "RequestScope",
    "SessionScope",
    "get_current_context",
    "set_context",
]

T = TypeVar("T")

_context_stack: ContextVar[ChainMap[Token[object], object] | None] = ContextVar(
    "pyinj_context_stack", default=None
)

_session_context: ContextVar[dict[Token[object], object] | None] = ContextVar(
    "pyinj_session_context", default=None
)

_request_cleanup_sync: ContextVar[list[Callable[[], None]] | None] = ContextVar(
    "pyinj_request_cleanup_sync", default=None
)
_request_cleanup_async: ContextVar[list[Callable[[], Awaitable[None]]] | None] = (
    ContextVar("pyinj_request_cleanup_async", default=None)
)

_session_cleanup_sync: ContextVar[list[Callable[[], None]] | None] = ContextVar(
    "pyinj_session_cleanup_sync", default=None
)
_session_cleanup_async: ContextVar[list[Callable[[], Awaitable[None]]] | None] = (
    ContextVar("pyinj_session_cleanup_async", default=None)
)


def get_current_context() -> ChainMap[Token[object], object] | None:
    """Get current dependency context."""
    return _context_stack.get()


def set_context(
    context: ChainMap[Token[object], object],
) -> ContextToken[ChainMap[Token[object], object] | None]:
    """
    Set the current dependency context.

    Args:
        context: ChainMap of dependency caches

    Returns:
        Token for resetting context
    """
    return _context_stack.set(context)


class ContextualContainer:
    """Base container adding request/session context via ``contextvars``.

    Context flows implicitly across awaits; request/session lifetimes
    are enforced by the :class:`ScopeManager`.
    """

    def __init__(self) -> None:
        """Initialize contextual container."""
        self._singletons: dict[Token[object], object] = {}
        self._providers: dict[Token[object], Any] = {}
        self._async_locks: dict[Token[object], asyncio.Lock] = {}
        # Use deque for LIFO cleanup ordering with precomputed strategies
        self._cleanup_stack: deque[CleanupStrategy] = deque()
        self._scope_manager = ScopeManager(self)

    def _register_request_cleanup_sync(self, fn: Callable[[], None]) -> None:
        """Register a sync cleanup for the current request scope.

        Internal API called by the container when a sync context-managed resource
        is entered within a request scope. Cleanups run in LIFO order on scope exit.
        """
        stack = _request_cleanup_sync.get()
        if stack is None:
            raise RuntimeError("No active request scope for registering cleanup")
        stack.append(fn)

    def _register_request_cleanup_async(
        self, fn: Callable[[], Awaitable[None]]
    ) -> None:
        """Register an async cleanup for the current request scope.

        Internal API called by the container for async context-managed resources.
        Cleanups run before sync cleanups on async scope exit.
        """
        stack = _request_cleanup_async.get()
        if stack is None:
            raise RuntimeError("No active request scope for registering async cleanup")
        stack.append(fn)

    def _register_session_cleanup_sync(self, fn: Callable[[], None]) -> None:
        """Register a sync cleanup for the active session scope.

        Internal API used for session-scoped sync context-managed resources.
        """
        stack = _session_cleanup_sync.get()
        if stack is None:
            raise RuntimeError("No active session scope for registering cleanup")
        stack.append(fn)

    def _register_session_cleanup_async(
        self, fn: Callable[[], Awaitable[None]]
    ) -> None:
        """Register an async cleanup for the active session scope.

        Internal API used for session-scoped async context-managed resources.
        """
        stack = _session_cleanup_async.get()
        if stack is None:
            raise RuntimeError("No active session scope for registering async cleanup")
        stack.append(fn)

    def _put_in_current_request_cache(self, token: Token[T], instance: T) -> None:
        """Insert a value into the current request cache unconditionally.

        This bypasses scope checks and is intended for temporary overrides
        that should only affect the current context.
        """
        context = _context_stack.get()
        if context is not None and hasattr(context, "maps") and len(context.maps) > 0:
            # The top-most map holds request-local values
            context.maps[0][cast(Token[object], token)] = cast(object, instance)

    @contextmanager
    def request_scope(self) -> Iterator[ContextualContainer]:
        """Create a request scope (similar to a web request lifecycle).

        Example:
            with container.request_scope():
                service = container.get(ServiceToken)

        Yields:
            Self for chaining.
        """
        with self._scope_manager.request_scope():
            yield self

    @asynccontextmanager
    async def async_request_scope(self) -> AsyncIterator[ContextualContainer]:
        """Async context manager variant of :meth:`request_scope`.

        Example:
            async with container.async_request_scope():
                service = await container.aget(ServiceToken)
        """
        async with self._scope_manager.async_request_scope():
            yield self

    @contextmanager
    def session_scope(self) -> Iterator[ContextualContainer]:
        """
        Create a session scope (longer-lived than request).

        Session scopes persist across multiple requests but are
        isolated between different sessions (e.g., users).
        """
        with self._scope_manager.session_scope():
            yield self

    def _cleanup_scope(self, cleanup_tasks: deque[Callable[[], Any]]) -> None:
        """Clean up resources in LIFO order using cleanup tasks.

        This method uses tasks created at scope exit time,
        eliminating runtime type checking and improving performance.

        Args:
            cleanup_tasks: Deque of cleanup task callables
        """
        # Execute cleanup in LIFO order
        while cleanup_tasks:
            task = cleanup_tasks.pop()
            result = task()
            
            # Check for async cleanup in sync context (fail fast)
            if asyncio.iscoroutine(result):
                raise AsyncCleanupRequiredError(
                    "scope",
                    "Use an async request/session scope.",
                )

    async def _async_cleanup_scope(
        self, cleanup_tasks: deque[Callable[[], Any]]
    ) -> None:
        """Async cleanup of resources using cleanup tasks.

        This method uses tasks created at scope exit time,
        eliminating runtime type checking and improving performance.

        Args:
            cleanup_tasks: Deque of cleanup task callables
        """
        tasks: list[Awaitable[Any]] = []
        loop = asyncio.get_running_loop()

        # Execute cleanup in LIFO order
        while cleanup_tasks:
            task = cleanup_tasks.pop()
            result = task()
            
            if asyncio.iscoroutine(result):
                # Execute async cleanup directly
                tasks.append(result)
            else:
                # Sync cleanup already executed by calling task()
                pass

        # Execute all cleanup tasks concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def resolve_from_context(self, token: Token[T]) -> T | None:
        """
        Resolve dependency from current context.

        Args:
            token: Token to resolve

        Returns:
            Resolved instance or None if not in context
        """
        return self._scope_manager.resolve_from_context(token)

    def store_in_context(self, token: Token[T], instance: T) -> None:
        """
        Store instance in appropriate context.

        Args:
            token: Token for the instance
            instance: Instance to store
        """
        self._scope_manager.store_in_context(token, instance)

    def clear_request_context(self) -> None:
        """Clear current request context."""
        self._scope_manager.clear_request_context()

    def clear_session_context(self) -> None:
        """Clear current session context."""
        self._scope_manager.clear_session_context()

    def clear_all_contexts(self) -> None:
        """Clear all contexts including singletons."""
        self._scope_manager.clear_all_contexts()


class ScopeManager:
    """Scope orchestration with RAII managers and explicit precedence.

    Precedence: REQUEST > SESSION > SINGLETON. Uses ContextVars for async safety.
    """

    def __init__(self, container: ContextualContainer) -> None:
        self._container = container

    @contextmanager
    def request_scope(self) -> Iterator[None]:
        request_cache: dict[Token[object], object] = {}
        request_cleanup: deque[CleanupStrategy] = deque()
        current = _context_stack.get()
        if current is None:
            new_context = ChainMap(request_cache, self._container._singletons)
        else:
            new_context = ChainMap(request_cache, *current.maps)
        token = _context_stack.set(new_context)
        req_sync_token = _request_cleanup_sync.set([])
        req_async_token = _request_cleanup_async.set([])
        try:
            yield
        finally:
            # Create cleanup tasks for all cached resources
            for resource in request_cache.values():
                strategy = CleanupStrategy.analyze(resource)
                if strategy != CleanupStrategy.NONE:
                    task = CleanupStrategy.create_task(resource, strategy)
                    request_cleanup.append(task)
            # Clean up resources using cleanup tasks
            self._container._cleanup_scope(request_cleanup)
            try:
                sync_fns = _request_cleanup_sync.get() or []
                for fn in reversed(sync_fns):
                    try:
                        fn()
                    except Exception:
                        pass
            finally:
                _request_cleanup_sync.reset(req_sync_token)
            _request_cleanup_async.reset(req_async_token)
            _context_stack.reset(token)

    @asynccontextmanager
    async def async_request_scope(self) -> AsyncIterator[None]:
        request_cache: dict[Token[object], object] = {}
        request_cleanup: deque[CleanupStrategy] = deque()
        current = _context_stack.get()
        if current is None:
            new_context = ChainMap(request_cache, self._container._singletons)
        else:
            new_context = ChainMap(request_cache, *current.maps)
        token = _context_stack.set(new_context)
        req_sync_token = _request_cleanup_sync.set([])
        req_async_token = _request_cleanup_async.set([])
        try:
            yield
        finally:
            # Create cleanup tasks for all cached resources
            for resource in request_cache.values():
                strategy = CleanupStrategy.analyze(resource)
                if strategy != CleanupStrategy.NONE:
                    task = CleanupStrategy.create_task(resource, strategy)
                    request_cleanup.append(task)
            # Clean up resources using cleanup tasks
            await self._container._async_cleanup_scope(request_cleanup)
            async_fns = _request_cleanup_async.get() or []
            if async_fns:
                await asyncio.gather(
                    *[fn() for fn in reversed(async_fns)], return_exceptions=True
                )
            sync_fns = _request_cleanup_sync.get() or []
            for fn in reversed(sync_fns):
                try:
                    fn()
                except Exception:
                    pass
            _request_cleanup_sync.reset(req_sync_token)
            _request_cleanup_async.reset(req_async_token)
            _context_stack.reset(token)

    @contextmanager
    def session_scope(self) -> Iterator[None]:
        existing = _session_context.get()
        if existing is None:
            session_cache: dict[Token[object], object] = {}
            session_token = _session_context.set(session_cache)
            sess_sync_token = _session_cleanup_sync.set([])
            sess_async_token = _session_cleanup_async.set([])
        else:
            session_cache = existing
            session_token = None
            sess_sync_token = None
            sess_async_token = None
        current = _context_stack.get()
        if current is None:
            new_context = ChainMap(session_cache, self._container._singletons)
        else:
            new_context = ChainMap(
                current.maps[0], session_cache, self._container._singletons
            )
        context_token = _context_stack.set(new_context)
        try:
            yield
        finally:
            _context_stack.reset(context_token)
            if session_token:
                try:
                    sync_fns = _session_cleanup_sync.get() or []
                    for fn in reversed(sync_fns):
                        try:
                            fn()
                        except Exception:
                            pass
                finally:
                    if sess_sync_token is not None:
                        _session_cleanup_sync.reset(sess_sync_token)
                if sess_async_token is not None:
                    _session_cleanup_async.reset(sess_async_token)
                _session_context.reset(session_token)

    def resolve_from_context(self, token: Token[T]) -> T | None:
        context = _context_stack.get()
        if context is not None:
            key = cast(Token[object], token)
            if key in context:
                return cast(T, context[key])
        if token.scope == Scope.SESSION:
            session = _session_context.get()
            if session and token in session:
                return cast(T, session[cast(Token[object], token)])
        if token.scope == Scope.SINGLETON and token in self._container._singletons:
            return cast(T, self._container._singletons[cast(Token[object], token)])
        # Transients are never cached - always return None to force new instance
        return None

    def store_in_context(self, token: Token[T], instance: T) -> None:
        if token.scope == Scope.SINGLETON:
            self._container._singletons[cast(Token[object], token)] = cast(
                object, instance
            )
        elif token.scope == Scope.REQUEST:
            self._container._put_in_current_request_cache(token, instance)
        elif token.scope == Scope.SESSION:
            session = _session_context.get()
            if session is not None:
                session[cast(Token[object], token)] = cast(object, instance)
        elif token.scope == Scope.TRANSIENT:
            pass

    def clear_request_context(self) -> None:
        context = _context_stack.get()
        if context is not None and hasattr(context, "maps") and len(context.maps) > 0:
            context.maps[0].clear()

    def clear_session_context(self) -> None:
        session = _session_context.get()
        if session is not None:
            session.clear()

    def clear_all_contexts(self) -> None:
        self._container._singletons.clear()
        self.clear_request_context()
        self.clear_session_context()


class RequestScope:
    """
    Helper class for request-scoped dependencies.

    Example:
        async with RequestScope(container) as scope:
            service = scope.resolve(ServiceToken)
    """

    def __init__(self, container: ContextualContainer):
        """Initialize request scope."""
        self.container = container
        self._context_manager = None
        self._async_context_manager = None

    def __enter__(self) -> RequestScope:
        """Enter request scope."""
        self._context_manager = self.container.request_scope()
        self._context_manager.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit request scope."""
        if self._context_manager:
            self._context_manager.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self) -> RequestScope:
        """Async enter request scope."""
        self._async_context_manager = self.container.async_request_scope()
        await self._async_context_manager.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async exit request scope."""
        if self._async_context_manager:
            await self._async_context_manager.__aexit__(exc_type, exc_val, exc_tb)

    def resolve(self, token: Token[T]) -> T | None:
        """Resolve dependency in this scope."""
        return self.container.resolve_from_context(token)


class SessionScope:
    """
    Helper class for session-scoped dependencies.

    Example:
        with SessionScope(container) as scope:
            user = scope.resolve(UserToken)
    """

    def __init__(self, container: ContextualContainer):
        """Initialize session scope."""
        self.container = container
        self._context_manager = None

    def __enter__(self) -> SessionScope:
        """Enter session scope."""
        self._context_manager = self.container.session_scope()
        self._context_manager.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit session scope."""
        if self._context_manager:
            self._context_manager.__exit__(exc_type, exc_val, exc_tb)
