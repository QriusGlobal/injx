"""Minimal FastAPI + Injx integration (KISS).

Run:
  uv run uvicorn docs.examples.fastapi_minimal:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from injx import Container, Scope, Token


# --- Providers (tiny, explicit) ------------------------------------------------

class Engine:
    async def aclose(self) -> None:  # Async cleanup supported
        pass


class Session:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    async def aclose(self) -> None:
        pass


def build_container() -> Container:
    container = Container()

    ENGINE = Token[Engine]("engine", Engine, scope=Scope.SINGLETON)
    SESSION = Token[Session]("session", Session, scope=Scope.REQUEST)

    # Register context-managed providers (explicit lifecycles)
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def engine_cm():
        eng = Engine()
        try:
            yield eng
        finally:
            await eng.aclose()

    @asynccontextmanager
    async def session_cm():
        # In real code create from ENGINE (kept trivial here)
        s = Session(engine=await container.aget(ENGINE))
        try:
            yield s
        finally:
            await s.aclose()

    container.register_context_async(ENGINE, lambda: engine_cm(), scope=Scope.SINGLETON)
    container.register_context_async(SESSION, lambda: session_cm(), scope=Scope.REQUEST)

    # Store tokens for use in routes
    container.set("ENGINE", ENGINE)
    container.set("SESSION", SESSION)
    return container


container = build_container()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Activate container for the app lifetime
    with container.activate():
        yield
    # Clean up singletons
    await container.aclose()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def injx_request_scope(request, call_next):
    async with container.async_request_scope():
        return await call_next(request)


@app.get("/health")
async def health() -> dict[str, Any]:
    # Minimal usage: resolve per-request session, do work, return
    session_token = container.get("SESSION")
    _session = await container.aget(session_token)
    return {"status": "ok"}

