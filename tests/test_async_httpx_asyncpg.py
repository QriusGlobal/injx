"""Concurrency tests using httpx and a simulated asyncpg client.

These tests validate that the DI container resolves async singletons safely
under concurrency, and that ContextVar-based overrides are isolated between
tasks.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest

from injx.container import Container
from injx.tokens import Scope, Token


class FakeAsyncPGPool:
    """A lightweight asyncpg-like pool with aclose()."""

    def __init__(self) -> None:
        self.closed = False
        self.created = asyncio.get_running_loop().time()

    async def fetch(self, query: str) -> list[dict[str, Any]]:
        await asyncio.sleep(0.001)
        return [{"query": query, "at": asyncio.get_running_loop().time()}]

    async def aclose(self) -> None:
        self.closed = True


def make_httpx_client() -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"method": request.method, "url": str(request.url)}
        )

    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, base_url="https://example.test")


@pytest.mark.asyncio
async def test_async_singleton_httpx_concurrency() -> None:
    container = Container()
    client_token = Token("httpx", httpx.AsyncClient, scope=Scope.SINGLETON)

    created = 0

    async def create_client() -> httpx.AsyncClient:
        nonlocal created
        await asyncio.sleep(0.002)
        created += 1
        return make_httpx_client()

    container.register(client_token, create_client)

    async def worker(i: int) -> httpx.Response:
        client = await container.aget(client_token)
        return await client.get(f"/w/{i}")

    results = await asyncio.gather(*(worker(i) for i in range(50)))
    assert all(r.status_code == 200 for r in results)
    _first = results[0].json()
    assert all(r.json()["method"] == "GET" for r in results)
    assert created == 1  # only one AsyncClient created


@pytest.mark.asyncio
async def test_context_overrides_isolation_between_tasks() -> None:
    container = Container()
    token = Token("config", str, scope=Scope.REQUEST)
    container.register(token, lambda: "default")

    async def task_a() -> str:
        with container.use_overrides({token: "A"}):
            await asyncio.sleep(0)
            return await container.aget(token)

    async def task_b() -> str:
        with container.use_overrides({token: "B"}):
            await asyncio.sleep(0)
            return await container.aget(token)

    res_a, res_b = await asyncio.gather(task_a(), task_b())
    assert res_a == "A"
    assert res_b == "B"


@pytest.mark.asyncio
async def test_fake_asyncpg_pool_singleton_and_cleanup() -> None:
    container = Container()
    pool_token = Token("db_pool", FakeAsyncPGPool, scope=Scope.SINGLETON)

    @asynccontextmanager
    async def pool_cm():
        await asyncio.sleep(0.001)
        p = FakeAsyncPGPool()
        try:
            yield p
        finally:
            await p.aclose()

    container.register_context(pool_token, lambda: pool_cm(), is_async=True)

    # Concurrency: ensure only one pool is created
    pools = await asyncio.gather(*(container.aget(pool_token) for _ in range(20)))
    first = pools[0]
    assert all(p is first for p in pools)

    # Simulate a query
    rows = await first.fetch("select 1")
    assert rows and "query" in rows[0]

    # Cleanup
    await container.aclose()
    assert first.closed is True
