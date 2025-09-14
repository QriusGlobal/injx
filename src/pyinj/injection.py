"""Lightweight decorators and markers for function parameter injection.

These tools are inspired by FastAPI but remain framework-agnostic and
work with synchronous and asynchronous callables.
"""

from __future__ import annotations

import asyncio
import builtins
from dataclasses import dataclass
from enum import Enum, auto
from functools import lru_cache, wraps
from inspect import Parameter, iscoroutinefunction, signature
from typing import (
    Annotated,
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Generic,
    ParamSpec,
    TypeAlias,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)
from typing import (
    cast as tcast,
)

from .defaults import get_default_container
from .tokens import Token

__all__ = [
    "Depends",
    "Given",
    "Inject",
    "InjectionAnalyzer",
    "analyze_dependencies",
    "inject",
    "resolve_dependencies",
]

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")


class Inject(Generic[T]):
    """
    Marker for injected dependencies (similar to FastAPI's ``Depends``).

    Usage:
        def handler(db: Inject[Database]):
            # db is auto-injected
            ...

        # Or with default provider
        def handler(db: Inject[Database] = Inject(create_db)):
            ...
    """

    def __init__(self, provider: Callable[..., T] | None = None) -> None:
        """
        Initialize an injection marker optionally carrying a provider.

        Args:
            provider: Optional provider function
        """
        self.provider = provider
        self._type: type[T] | None = None

    _typed_cache: ClassVar[dict[type[object], builtins.type]] = {}

    def __class_getitem__(cls, item: builtins.type[T]) -> builtins.type["Inject[T]"]:
        """Support Inject[Type] syntax without recursion and with caching.

        Returns a cached subclass carrying the injection type, so that
        repeated references to Inject[T] are identical across calls.
        """
        cached = cls._typed_cache.get(item)
        if cached is not None:
            return cached

        name = f"Inject_{getattr(item, '__name__', 'T')}"
        TypedInject = type(name, (cls,), {"_inject_type": item})
        cls._typed_cache[item] = TypedInject
        return tcast(builtins.type, TypedInject)

    @property
    def type(self) -> builtins.type[T] | None:
        """Get the injected type if available."""
        t = getattr(self.__class__, "_inject_type", None)
        if isinstance(t, type):
            return t
        return self._type

    def set_type(self, type_: builtins.type[T]) -> None:
        """Set the injected type explicitly (used by analyzers)."""
        self._type = type_

    def __repr__(self) -> str:
        """Readable representation."""
        if self.type:
            return f"Inject[{self.type.__name__}]"
        return "Inject()"


class Given:
    """
    Scala-style given marker for implicit dependencies.

    Usage:
        def handler(db: Given[Database]):
            # db is resolved from given instances
            ...
    """

    def __class_getitem__(cls, item: type[T]) -> builtins.type["Inject[T]"]:
        """Support Given[Type] syntax by delegating to Inject."""
        return Inject[item]


def Depends[T](provider: Callable[..., T]) -> T:  # noqa: N802
    """
    FastAPI-compatible ``Depends`` marker.

    Args:
        provider: Provider function for the dependency

    Returns:
        An :class:`Inject` marker usable as a default parameter value.
    """
    return Inject(provider)  # type: ignore


DependencyRequest: TypeAlias = type | Token[object] | Inject[object]


class _DepKind(Enum):
    TOKEN = auto()
    TYPE = auto()
    INJECT = auto()


@dataclass(frozen=True)
class _DepSpec:
    kind: _DepKind
    type_: type[Any] | None = None
    token: Token[object] | None = None
    provider: Callable[[], Any] | None = None


@lru_cache(maxsize=256)
def analyze_dependencies(func: Callable[..., Any]) -> dict[str, DependencyRequest]:
    """
    Analyze function signature for injected dependencies.

    This is cached for performance as signature analysis is expensive.

    Args:
        func: Function to analyze

    Returns:
        Dictionary mapping parameter names to their injection specs
    """
    sig = signature(func)
    # Resolve annotations (handles from __future__ import annotations)
    try:
        resolved = get_type_hints(func, include_extras=True)
    except Exception:
        resolved = {}
    deps: dict[str, DependencyRequest] = {}

    for name, param in sig.parameters.items():
        # Skip *args and **kwargs
        if param.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD):
            continue

        annotation = resolved.get(name, param.annotation)

        # Skip if no annotation
        if annotation is Parameter.empty:
            continue

        # Check various injection patterns
        origin = get_origin(annotation)
        args = get_args(annotation)

        # 1) Annotated[T, Inject(...) | Token(...)]
        if origin is Annotated and args:
            dep_type = args[0]
            metadata = args[1:]
            for meta in metadata:
                if isinstance(meta, Inject):
                    marker = cast(Inject[Any], meta)
                    if not marker.type and isinstance(dep_type, type):
                        marker.set_type(dep_type)
                    deps[name] = marker
                    break
                if isinstance(meta, Token):
                    deps[name] = meta
                    break

        elif _is_inject_type(annotation):
            # It's Inject[T] or Given[T]
            deps[name] = _extract_inject_spec(annotation, param.default)

        elif isinstance(param.default, Inject):
            # Default value is Inject()
            marker = cast(Inject[Any], param.default)
            deps[name] = marker
            if annotation != Parameter.empty and isinstance(annotation, type):
                # Store the type from annotation
                marker.set_type(annotation)

        elif isinstance(annotation, Token):
            # Direct Token annotation
            deps[name] = annotation

        elif _is_plain_injectable_type(annotation):
            # Fallback: plain type annotation (non-builtin class/protocol)
            deps[name] = annotation

        elif isinstance(param.annotation, str) and "Inject[" in param.annotation:
            # Last-resort: parse string annotations from future annotations
            inner = param.annotation.strip()
            try:
                inner_type_str = inner[inner.find("[") + 1 : inner.rfind("]")]
                inner_type = eval(inner_type_str, func.__globals__, {})  # noqa: S307 (trusted test context)
                inner_type = tcast(type[object], inner_type)
                marker = Inject[object]()
                marker.set_type(inner_type)
                deps[name] = marker
            except Exception:
                # Ignore if we cannot resolve
                pass

    return deps


class InjectionAnalyzer:
    """Small analyzer facade to build dependency plans.

    This class enables decomposition and easier testing while
    remaining backward-compatible with analyze_dependencies.
    """

    @staticmethod
    def build_plan(func: Callable[..., Any]) -> dict[str, DependencyRequest]:
        return analyze_dependencies(func)


def _is_inject_type(annotation: Any) -> bool:
    """Check if annotation is Inject[T] or Given[T] type."""
    # Check for our custom TypedInject classes
    if hasattr(annotation, "_inject_type"):
        return True

    # Check using get_origin for generic types
    origin = get_origin(annotation)
    if origin is not None:
        return origin is Inject or (
            hasattr(origin, "__name__") and origin.__name__ in ("Inject", "Given")
        )

    # Check if it's a direct Inject class
    return isinstance(annotation, type) and issubclass(annotation, Inject)


def _is_plain_injectable_type(annotation: Any) -> bool:
    """Heuristically decide whether a plain type hint should be injected.

    We inject only for non-builtin classes/protocols to avoid surprising
    behavior with primitives like ``int`` or ``str``.
    """
    try:
        return (
            isinstance(annotation, type)
            and getattr(annotation, "__module__", "builtins") != "builtins"
        )
    except Exception:
        return False


def _extract_inject_spec(
    annotation: Any, default: Inject[object] | object = Parameter.empty
) -> DependencyRequest:
    """Extract injection specification from annotation."""
    # Get the type from Inject[T]
    if hasattr(annotation, "_inject_type"):
        type_ = annotation._inject_type
    else:
        args = get_args(annotation)
        type_ = args[0] if args else None

    # If there's a default Inject instance, use it
    if default is Parameter.empty:
        return type_ or annotation
    if isinstance(default, Inject):
        marker = cast(Inject[Any], default)
        if type_ and not marker.type:
            marker.set_type(type_)
        return marker

    # Return just the type
    return type_ or annotation


def resolve_dependencies(
    deps: dict[str, DependencyRequest],
    container: Any,  # Container type, but avoiding circular import
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    """
    Resolve dependencies synchronously.

    Args:
        deps: Dependencies to resolve
        container: Container to resolve from
        overrides: Optional overrides for specific dependencies

    Returns:
        Dictionary of resolved dependencies
    """
    resolved: dict[str, object] = {}
    ov = overrides or {}
    for name, req in deps.items():
        if name in ov:
            resolved[name] = ov[name]
            continue
        spec = _to_spec(req)
        resolved[name] = _resolve_one(spec, container)
    return resolved


def _to_spec(spec: DependencyRequest) -> _DepSpec:
    if isinstance(spec, Token):
        return _DepSpec(kind=_DepKind.TOKEN, token=spec)
    if isinstance(spec, Inject):
        return _DepSpec(kind=_DepKind.INJECT, type_=spec.type, provider=spec.provider)
    # else it's a type
    return _DepSpec(kind=_DepKind.TYPE, type_=cast(type[Any], spec))


def _resolve_one(spec: _DepSpec, container: Any) -> object:
    if spec.kind is _DepKind.TOKEN:
        token = spec.token
        assert token is not None
        return container.get(token)
    if spec.kind is _DepKind.INJECT:
        if spec.provider is not None:
            return spec.provider()
        return container.get(cast(type[Any], spec.type_))
    # TYPE
    return container.get(cast(type[Any], spec.type_))


async def _aresolve_one(spec: _DepSpec, container: Any) -> object:
    if spec.kind is _DepKind.TOKEN:
        aget = getattr(container, "aget", None)
        if aget and iscoroutinefunction(aget):
            token = spec.token
            assert token is not None
            return await aget(token)
        # Fallback
        loop = asyncio.get_event_loop()
        token = spec.token
        assert token is not None
        return await loop.run_in_executor(None, container.get, token)
    if spec.kind is _DepKind.INJECT:
        if spec.provider is not None:
            if iscoroutinefunction(spec.provider):
                return await spec.provider()  # type: ignore[misc]
            # Might return awaitable by convention
            result = spec.provider()
            if asyncio.iscoroutine(result):
                return await cast(asyncio.Future[object], result)
            return result
        aget = getattr(container, "aget", None)
        if aget and iscoroutinefunction(aget):
            return await aget(cast(type[Any], spec.type_))
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, container.get, cast(type[Any], spec.type_)
        )
    # TYPE
    aget = getattr(container, "aget", None)
    if aget and iscoroutinefunction(aget):
        return await aget(cast(type[Any], spec.type_))
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, container.get, cast(type[Any], spec.type_))


async def resolve_dependencies_async(
    deps: dict[str, DependencyRequest],
    container: Any,  # Container type, but avoiding circular import
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    """
    Resolve dependencies asynchronously.

    Args:
        deps: Dependencies to resolve
        container: Container to resolve from
        overrides: Optional overrides for specific dependencies

    Returns:
        Dictionary of resolved dependencies
    """
    resolved: dict[str, object] = {}
    overrides = overrides or {}
    tasks: dict[str, asyncio.Task[object]] = {}

    for name, req in deps.items():
        if name in overrides:
            resolved[name] = overrides[name]
            continue
        spec = _to_spec(req)
        tasks[name] = asyncio.create_task(_aresolve_one(spec, container))

    # Resolve all tasks in parallel
    if tasks:
        results: list[Any] = await asyncio.gather(*tasks.values())
        for name, result in zip(tasks.keys(), results, strict=False):
            resolved[name] = result

    return resolved


@overload
def inject(
    func: Callable[P, R], *, container: Any | None = ..., cache: bool = ...
) -> Callable[P, R]: ...


@overload
def inject(
    func: None = ..., *, container: Any | None = ..., cache: bool = ...
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


# NOTE: Container type is Any to avoid circular imports.
# At runtime, this accepts any object with get/aget methods.
# The actual type checking happens via protocols.


def inject(
    func: Callable[P, R] | None = None,
    *,
    container: Any | None = None,
    cache: bool = True,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator that injects dependencies into function parameters.

    This is the main entry point for dependency injection, inspired by
    FastAPI's dependency injection system.

    Args:
        func: Function to decorate (or None if using with parameters)
        container: Container to resolve dependencies from
        cache: Whether to cache dependency analysis

    Returns:
        Decorated function with automatic dependency injection

    Examples:
        @inject
        def service(db: Inject[Database]):
            return db.query()

        @inject(container=my_container)
        async def handler(cache: Inject[Cache]):
            return await cache.get("key")

        @inject
        async def endpoint(
            user_id: int,
            db: Inject[Database],
            cache: Given[Cache],
            settings: Settings = Inject()
        ):
            # Mixed regular and injected parameters
            pass
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        # Analyze dependencies (cached if cache=True)
        deps = InjectionAnalyzer.build_plan(fn) if cache else None

        if iscoroutinefunction(fn):
            # NOTE: The sync/async wrapper duplication below is intentional.
            # While metaprogramming could reduce duplication, it would:
            # 1. Make debugging significantly harder
            # 2. Obscure the control flow
            # 3. Add complexity without meaningful benefit
            # The explicit duplication aligns with our "minimal complexity" principle.
            @wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> R:
                # Get dependencies if not cached
                nonlocal deps
                if deps is None:
                    deps = InjectionAnalyzer.build_plan(fn)

                if not deps:
                    # No dependencies, call original
                    return await fn(*args, **kwargs)

                # Get container
                nonlocal container
                if container is None:
                    container = get_default_container()

                # Extract overrides from kwargs
                overrides: dict[str, Any] = {}
                for name in deps:
                    if name in kwargs:  # type: ignore[operator]
                        overrides[name] = cast(Any, kwargs.pop(name))  # type: ignore[call-arg]

                # Resolve dependencies
                resolved = await resolve_dependencies_async(deps, container, overrides)

                # Rebind arguments: skip injected params from positional binding
                sig = signature(fn)
                new_kwargs: dict[str, Any] = {}
                arg_i = 0
                for pname, param in sig.parameters.items():
                    if pname in resolved:
                        # will be injected
                        continue
                    if param.kind in (
                        Parameter.POSITIONAL_ONLY,
                        Parameter.POSITIONAL_OR_KEYWORD,
                    ) and arg_i < len(args):
                        new_kwargs[pname] = args[arg_i]
                        arg_i += 1
                # bring through any explicit kwargs provided
                new_kwargs.update(kwargs)
                # inject resolved deps
                new_kwargs.update(resolved)

                return await cast(Callable[..., Awaitable[R]], fn)(**new_kwargs)

            return cast(Callable[P, R], async_wrapper)

        else:

            @wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> R:
                # Get dependencies if not cached
                nonlocal deps
                if deps is None:
                    deps = InjectionAnalyzer.build_plan(fn)

                if not deps:
                    # No dependencies, call original
                    return fn(*args, **kwargs)

                # Get container
                nonlocal container
                if container is None:
                    container = get_default_container()

                # Extract overrides from kwargs
                overrides: dict[str, Any] = {}
                for name in deps:
                    if name in kwargs:  # type: ignore[operator]
                        overrides[name] = cast(Any, kwargs.pop(name))  # type: ignore[call-arg]

                # Resolve dependencies
                resolved = resolve_dependencies(deps, container, overrides)

                # Rebind arguments: skip injected params from positional binding
                sig = signature(fn)
                new_kwargs: dict[str, Any] = {}
                arg_i = 0
                for pname, param in sig.parameters.items():
                    if pname in resolved:
                        continue
                    if param.kind in (
                        Parameter.POSITIONAL_ONLY,
                        Parameter.POSITIONAL_OR_KEYWORD,
                    ) and arg_i < len(args):
                        new_kwargs[pname] = args[arg_i]
                        arg_i += 1
                new_kwargs.update(kwargs)
                new_kwargs.update(resolved)

                return cast(Callable[..., R], fn)(**new_kwargs)

            return sync_wrapper

    # Handle both @inject and @inject(...) syntax
    if func is None:
        # Called with parameters: @inject(container=...)
        return decorator
    else:
        # Called without parameters: @inject
        return decorator(func)
