# Internals

This page outlines how Injx is structured under the hood.

## Core concepts

- Token[T]: immutable, hashable identifier for a typed dependency. Holds `name`, `type_`, `scope`, optional `qualifier`, and `tags`.
- ProviderLike[T]: either a sync provider `() -> T` or async provider `() -> Awaitable[T]`.
- Scopes:
  - SINGLETON: shared across the process/container
  - REQUEST: bound to the current request context
  - SESSION: longer-lived context separate from request
  - TRANSIENT: created each resolution

## Container

- Registries
  - `_providers: dict[Token[object], ProviderLike[object]]`
  - `_singletons: dict[Token[object], object]`
  - `_token_scopes: dict[Token[object], Scope]`
  - `_async_locks: dict[Token[object], asyncio.Lock]`
- Concurrency
  - Thread-safe singleton creation (per-token `threading.Lock`)
  - Async-safe singleton creation (per-token `asyncio.Lock`)
- Contexts
  - Uses `contextvars` to implement REQUEST and SESSION scoping
  - `use_overrides()` merges override maps per context

## Resolution

- `get(Token[T] | type[T]) -> T`
  - If a `type[T]` is passed, the container finds or creates a matching token.
  - Checks overrides, request/session caches, then provider
  - Validates type using `Token.validate()` before storing
  - Disallows calling async providers in sync `get()`
- `aget(Token[T] | type[T]) -> T`
  - Async variant; awaits async providers and uses `asyncio.Lock` for singletons

## Injection

- Analyzer inspects function signatures and annotations to build a dependency plan.
- Supported patterns (preferred first):
  - `Annotated[T, Inject()]`
  - Default marker: `param: T = Inject()`
  - Direct `Token[T]` annotations
  - Plain type-only injection for non-builtin classes/protocols
- Decorator `@inject` resolves dependencies per call (sync/async) and passes them as kwargs.

## Typing model

- `get/aget` return types depend on runtime providers in a DI system; the container remains generic.
- At call sites, annotate variables that receive container results when you need static precision.
- For `@inject`, prefer `Annotated[T, Inject()]` so tools know T is the runtime type while Inject carries metadata.

