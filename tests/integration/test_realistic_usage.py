"""Realistic integration tests emulating user projects with async libs.

These tests demonstrate typical project usage of injx with httpx only
to keep tests fast and network-light. Playwright-style usage is simulated via a fake to avoid
browser downloads while exercising DI patterns and cleanup behavior.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Annotated, Any

import httpx
import pytest

from injx.container import Container
from injx.injection import Inject, inject
from injx.tokens import Scope, Token


def _make_mock_httpx() -> httpx.AsyncClient:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"path": request.url.path})

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://svc"
    )


@pytest.mark.asyncio
async def test_user_style_project_di_with_httpx_only() -> None:
    container = Container()

    # Tokens a user would define centrally
    httpx_token = Token("http_client", httpx.AsyncClient, scope=Scope.SINGLETON)

    # Providers users would register during app startup
    async def create_http_client() -> httpx.AsyncClient:
        await asyncio.sleep(0)
        return _make_mock_httpx()

    container.register(httpx_token, create_http_client)

    # User endpoint using @inject
    @inject(container=container)
    async def endpoint(
        user_id: int,
        client: Annotated[httpx.AsyncClient, Inject()],
    ) -> dict[str, Any]:
        r = await client.get(f"/users/{user_id}")
        return {"status": r.status_code, "path": r.json()["path"]}

    # Simulate concurrent requests with isolated scopes
    from typing import Awaitable, Callable, cast

    async def call(uid: int) -> dict[str, Any]:
        async with container.async_request_scope():
            wrapped = cast(Callable[[int], Awaitable[dict[str, Any]]], endpoint)
            return await wrapped(uid)

    results = await asyncio.gather(*(call(i) for i in range(10)))
    assert all(r["status"] == 200 for r in results)
    assert all(r["path"].startswith("/users/") for r in results)

    # Singleton instances created only once
    c1 = await container.aget(httpx_token)
    c2 = await container.aget(httpx_token)
    assert c1 is c2

    # No DB in this variant

    await container.aclose()


@pytest.mark.asyncio
async def test_playwright_style_fake_browser_with_cleanup() -> None:
    container = Container()

    class FakeBrowser:
        def __init__(self) -> None:
            self.closed = False

        async def aclose(self) -> None:
            self.closed = True

        async def goto(self, url: str) -> dict[str, str]:  # pragma: no cover - trivial
            await asyncio.sleep(0)
            return {"url": url}

    browser_token = Token("browser", FakeBrowser, scope=Scope.SINGLETON)

    @asynccontextmanager
    async def browser_cm():
        b = FakeBrowser()
        try:
            yield b
        finally:
            await b.aclose()

    container.register_context(browser_token, lambda: browser_cm(), is_async=True)

    # Emulate concurrent test runners using the container
    async def worker(i: int) -> bool:
        b = await container.aget(browser_token)
        await b.goto(f"https://example/{i}")
        return True

    ok = await asyncio.gather(*(worker(i) for i in range(20)))
    assert all(ok)

    b = await container.aget(browser_token)
    await container.aclose()
    assert b.closed is True


@pytest.mark.asyncio
async def test_sync_cleanup_circuit_breaker_raises_for_async_resources() -> None:
    """Using sync cleanup with async-only resources should fail fast.

    This ensures developers get immediate feedback to await async cleanup
    rather than silently leaking resources.
    """
    container = Container()

    httpx_token = Token("http_client", httpx.AsyncClient, scope=Scope.SINGLETON)

    @asynccontextmanager
    async def client_cm():
        client = _make_mock_httpx()
        try:
            yield client
        finally:
            await client.aclose()

    container.register_context(httpx_token, lambda: client_cm(), is_async=True)

    # Create the async client (tracked resource)
    _ = await container.aget(httpx_token)
    # Ensure the resource is tracked
    resources = container.resources_view()
    assert len(resources) > 0

    # Using sync context manager should raise due to async cleanup required
    from injx.exceptions import AsyncCleanupRequiredError

    with pytest.raises(AsyncCleanupRequiredError):
        with container:
            pass
