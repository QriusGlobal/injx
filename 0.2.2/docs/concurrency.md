# Concurrency - Injx

[ ](https://github.com/QriusGlobal/injx/edit/master/docs/concurrency.md "Edit this page")

# Concurrency¶

Injx is designed for both threaded and async-concurrent programs.

  * Thread-safe singletons: first creation is protected by locks.
  * Async-safe singletons: first creation is protected by `asyncio.Lock`.
  * Request/session scoping: implemented with `contextvars`, so context flows across awaits.
  * Overrides: per-request overrides backed by `ContextVar` for isolation.

## Threaded programs¶
    
    
    from injx import Container, Token, Scope
    import threading
    
    container = Container()
    CACHE = Token[dict[str, str]]("cache", scope=Scope.SINGLETON)
    container.register(CACHE, lambda: {"a": "1"})
    
    # Safe: every thread gets the same singleton
    values: list[dict[str, str]] = []
    
    def worker() -> None:
        values.append(container.get(CACHE))
    
    threads = [threading.Thread(target=worker) for _ in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert all(v is values[0] for v in values)
    

## Async programs¶
    
    
    import asyncio
    from typing import Awaitable
    from injx import Container, Token, Scope
    
    container = Container()
    
    class Client:
        async def aclose(self) -> None: ...
    
    CLIENT = Token[Client]("client", scope=Scope.SINGLETON)
    
    async def make_client() -> Client:
        await asyncio.sleep(0)  # simulate I/O
        return Client()
    
    container.register(CLIENT, make_client)
    
    async def main() -> None:
        # Safe: async singleton is created once under an asyncio.Lock
        c1, c2 = await asyncio.gather(container.aget(CLIENT), container.aget(CLIENT))
        assert c1 is c2
    
    asyncio.run(main())
    

## Request / session scope (web-style lifetimes)¶
    
    
    from typing import Any
    from injx import Container, Token, Scope
    
    container = Container()
    SESSION = Token[dict[str, Any]]("session", scope=Scope.SESSION)
    REQUEST = Token[dict[str, Any]]("request", scope=Scope.REQUEST)
    
    container.register(SESSION, lambda: {"s": 1})
    container.register(REQUEST, lambda: {"r": 1})
    
    # Request scope isolates per-request caches while sharing singletons
    with container.request_scope():
        assert container.get(REQUEST)["r"] == 1
        with container.request_scope():
            assert container.get(REQUEST)["r"] == 1  # new dict in inner scope
    
    Note: nested `request_scope` blocks are fully isolated; the inner scope does not inherit the parent request cache. This ensures deterministic lifetimes for per-request values.
    

## Overrides per request¶
    
    
    from typing import Any
    
    LOGGER = Token[object]("logger")
    container.register(LOGGER, lambda: object())
    
    with container.use_overrides({LOGGER: "fake"}):
        assert container.get(LOGGER) == "fake"
    # Outside override, original provider is used
    assert container.get(LOGGER) != "fake"
    

## Cleanup¶

  * Request/session scopes clean up resources stored in the scope when the scope exits.
  * Container-level `dispose()` / `aclose()` cleans up resources registered via `register_context(...)` (both sync and async).

    
    
    # Register a context-managed singleton (async)
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def client_cm():
        c = make_async_client()
        try:
            yield c
        finally:
            await c.aclose()
    
    CLIENT = Token[AsyncClient]("client", scope=Scope.SINGLETON)
    container.register_context(CLIENT, lambda: client_cm(), is_async=True)
    
    # Later, ensure cleanup runs
    await container.aclose()  # or await container.dispose()
    
    Mixed cleanup in async request scopes:
    - In `async_request_scope`, async cleanups run first, then sync cleanups. This ensures awaiting all async finalizers before executing any synchronous ones, avoiding event loop blocking.
    
    Typed registration helpers:
    - `register_context_sync(token, cm_provider, scope=...)` for sync context managers.
    - `register_context_async(token, cm_provider, scope=...)` for async context managers.