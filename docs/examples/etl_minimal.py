"""Minimal ETL script using Injx (KISS).

Run:
  uv run python docs/examples/etl_minimal.py
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from injx import Container, Scope, Token


class Engine:
    async def aclose(self) -> None:
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

    @asynccontextmanager
    async def engine_cm():
        eng = Engine()
        try:
            yield eng
        finally:
            await eng.aclose()

    @asynccontextmanager
    async def session_cm():
        s = Session(engine=await container.aget(ENGINE))
        try:
            yield s
        finally:
            await s.aclose()

    container.register_context_async(ENGINE, lambda: engine_cm(), scope=Scope.SINGLETON)
    container.register_context_async(SESSION, lambda: session_cm(), scope=Scope.REQUEST)
    container.set("ENGINE", ENGINE)
    container.set("SESSION", SESSION)
    return container


async def run_etl() -> None:
    container = build_container()
    async with container:  # sets active + cleans on exit
        async with container.async_request_scope():
            session_token = container.get("SESSION")
            session = await container.aget(session_token)
            # Do ETL work with session
            _ = session


if __name__ == "__main__":
    asyncio.run(run_etl())

