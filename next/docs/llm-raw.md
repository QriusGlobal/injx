# LLM Guide (Raw) - PyInj

[ ](https://github.com/QriusGlobal/pyinj/edit/master/docs/llm-raw.md "Edit this page")

# LLM Documentation Access¶

For LLM tools and agents that need direct access to Injx documentation, we provide the standard `llms.txt` endpoint:

**Standard LLM Endpoint:**
    
    
    https://qriusglobal.github.io/injx/llms.txt
    

This follows the `llms.txt` standard and provides: \- Comprehensive Injx documentation in plain text \- No HTML wrapper, CSS, or JavaScript processing \- Direct HTTP GET access optimized for LLM consumption \- Complete usage patterns, examples, and best practices \- Framework integration guides and migration documentation

**Alternative GitHub Raw:**
    
    
    https://raw.githubusercontent.com/QriusGlobal/injx/main/docs/llm.md
    

## Alternative: Copy Raw Content Below¶

* * *

# LLM Guide: Using Injx for Reliable DI¶

Purpose: concise guidance for integrating Injx into LLM-driven projects and tools.

  * Audience: engineers wiring DI into agents, tools, plugins.
  * Constraints: brief, <10k tokens, actionable.

## Core Concepts¶

  * Token[T]: typed identifier for a dependency; holds name, type, scope.
  * Scopes: SINGLETON (process), SESSION (user/session), REQUEST (per-call), TRANSIENT.
  * Resolution: `get/aget` by token or type; `@inject` for functions.
  * Registrations are immutable: re-registering a token raises.

## Setup (Minimal Boilerplate)¶
    
    
    from injx import Container, Token, Scope
    container = Container()
    
    # Tokens
    HTTP = Token[HttpClient]("http", scope=Scope.SINGLETON)
    TOOLRUN = Token[dict]("toolrun", scope=Scope.REQUEST)
    
    # Providers
    container.register(TOOLRUN, lambda: {"invocations": 0})
    
    # Context-managed async singleton
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def http_cm():
        client = HttpClient()
        try:
            yield client
        finally:
            await client.aclose()
    
    container.register_context_async(HTTP, lambda: http_cm())
    

## Per-Call Isolation (Agents/Tools)¶
    
    
    async def run_tool(container: Container, tool_input: dict) -> dict:
        async with container.async_request_scope():
            # REQUEST-scoped values
            state = container.get(TOOLRUN)
            state["invocations"] += 1
            http = await container.aget(HTTP)
            return await http.post("/run", json=tool_input)
    

## Injection in Handlers¶
    
    
    from injx.injection import Inject, inject
    
    @inject(container=container)
    async def handler(payload: dict, http: Inject[HttpClient]):
        return await http.post("/endpoint", json=payload)
    

## Overrides (Per-Call or Test)¶
    
    
    FAKEHTTP = Token("http", HttpClient)
    with container.use_overrides({FAKEHTTP: FakeHttpClient()}):
        # only this concurrent context sees the override
        ...
    

## Accepted Patterns¶

  * Use `register_context_async/sync` for resources with lifecycles.
  * Use `async_request_scope/request_scope` to delimit per-call lifetimes.
  * Use `@inject` for handler entry points; avoid sprinkling `get()` across code.
  * Prefer tokens per logical dependency; avoid string-based tokens.
  * Use `override()`/`use_overrides()` in tests or local contexts.

## Anti-Patterns (Avoid)¶

  * Re-registering tokens at runtime (immutable; raises).
  * Storing global singletons in module-level variables—use SINGLETON scope instead.
  * Long-lived REQUEST/SESSION scopes—close them promptly.
  * Mixing sync-only cleanup for async resources—use async cleanup and `aclose()`.
  * Hidden side-effects in providers—keep providers pure and fast.

## Breaking Patterns (Incorrect)¶

  * Registering async providers via `register` and resolving with `get()` — use `aget()` or `register_context_async`.
  * Entering async-only resources with sync cleanup (e.g., using `with container:` for async singletons) — this raises an error; use `await container.aclose()`.
  * Accessing request-scoped values outside of any request/session scope — value won't exist.

## Failure Modes & Diagnostics¶

  * Circular dependencies: descriptive error with resolution chain.
  * Provider setup failure: exception propagates (fail-fast); inspect the original error.
  * Missing registration: `ResolutionError` with guidance.

## Migration Notes¶

  * Registrations are now immutable; remove any re-registration logic.
  * Switch resource cleanup to `register_context_sync/async`.

## Checklist for LLM Integrations¶

  * [ ] Define tokens per tool/client/config.
  * [ ] Register context-managed singletons for IO clients.
  * [ ] Wrap each tool/agent invocation in a request scope.
  * [ ] Use `@inject` for handler entry points.
  * [ ] Add overrides for tests and per-call variations.
  * [ ] Ensure async cleanup is awaited in shutdown paths.