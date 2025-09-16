"""Lightweight decorators and markers for function parameter injection.

These tools are inspired by FastAPI but remain framework-agnostic and
work with synchronous and asynchronous callables.
"""

from __future__ import annotations

import asyncio
import builtins
import time
from dataclasses import dataclass
from enum import Enum, auto
from functools import lru_cache, wraps
from inspect import Parameter, iscoroutinefunction, signature
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Generic,
    ParamSpec,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)
from typing import (
    Union,
    cast as tcast,
)

from .container import Container
from .logging import log_performance_metric, logger
from .tokens import Token

# Type alias for dependency types
DependencyType = Union["DependencyRequest", type[Any], Token[object], "Inject[object]"]

if TYPE_CHECKING:
    pass

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


class UnresolvableForwardRefError(TypeError):
    """Raised when a forward-referenced type hint cannot be resolved."""


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


class _DepKind(Enum):
    TOKEN = auto()
    TYPE = auto()
    INJECT = auto()


@dataclass(frozen=True, slots=True)
class DependencyRequest:
    """A structured request for a dependency."""

    kind: _DepKind
    key: type[Any] | Token[Any]
    provider: Callable[[], Any] | None = None


@lru_cache(maxsize=256)
def analyze_dependencies(
    func: Callable[..., Any],
) -> dict[str, DependencyType]:
    """
    Analyze a function's signature to find injectable dependencies.

    This function is cached for performance. It uses ``get_type_hints`` to
    safely resolve forward references and extracts dependency requests from
    type annotations and default values.

    Args:
        func: The callable to analyze.

    Returns:
        A dictionary mapping parameter names to their dependency requests.
        For backward compatibility, returns the original types:
        - Raw type for ``Inject[T]`` annotations
        - ``Inject`` instances for ``Inject()`` defaults
        - ``Token`` instances for token annotations
    """
    start = time.perf_counter()

    # Guard clauses for early exit
    if (
        not callable(func)
        or func.__name__ == "<lambda>"
        or func.__module__ == "builtins"
    ):
        return {}

    try:
        sig = signature(func)
        resolved_hints = get_type_hints(func, include_extras=True)
    except (TypeError, NameError) as e:
        logger.warning(
            f"Cannot resolve type hints for {func.__name__}: {e}. "
            "Consider using 'from __future__ import annotations'"
        )
        # Try without type hints resolution
        try:
            sig = signature(func)
            resolved_hints = {}
        except Exception:
            return {}

    if not sig.parameters:
        return {}

    deps: dict[str, DependencyRequest | type[Any] | Token[object] | Inject[object]] = {}
    for name, param in sig.parameters.items():
        if param.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD):
            continue

        annotation = resolved_hints.get(name, param.annotation)
        if annotation is Parameter.empty:
            continue

        # For backward compatibility, return the original types
        # Check for Token annotation first
        if isinstance(annotation, Token):
            deps[name] = annotation
            continue

        # Check for Annotated[T, Token] or Annotated[T, Inject]
        if get_origin(annotation) is Annotated:
            dep_type, *metadata = get_args(annotation)
            for meta in metadata:
                if isinstance(meta, Token):
                    deps[name] = meta
                    break
                if isinstance(meta, Inject):
                    inject_marker = cast(Inject[object], meta)
                    # Always set the type from Annotated[T, ...]
                    if hasattr(inject_marker, "set_type"):
                        inject_marker.set_type(dep_type)
                    deps[name] = inject_marker
                    break
            if name in deps:
                continue

        # Check for Inject[T] type annotation
        if _is_inject_type(annotation):
            # For Inject[T], the annotation is a subclass with _inject_type attribute
            if isinstance(annotation, type) and issubclass(annotation, Inject):
                # This is a dynamically created Inject[T] class
                dep_type = getattr(annotation, "_inject_type", Any)
            else:
                # Standard typing.Generic style (shouldn't happen but handle it)
                args = get_args(annotation)
                dep_type = args[0] if args else Any

            if isinstance(param.default, Inject):
                # If there's an Inject default, use it with the type
                inject_marker = cast(Inject[object], param.default)
                if hasattr(inject_marker, "type") and not inject_marker.type:
                    inject_marker.set_type(dep_type)
                deps[name] = inject_marker
            else:
                # Just the type annotation Inject[T], return the type
                deps[name] = dep_type
            continue

        # Check for Inject() default value
        if isinstance(param.default, Inject):
            inject_marker = cast(Inject[object], param.default)
            if annotation is not Parameter.empty and annotation is not Any:
                if hasattr(inject_marker, "type") and not inject_marker.type:
                    inject_marker.set_type(annotation)
            deps[name] = inject_marker
            continue

        # Check if we should auto-inject
        if _should_auto_inject(annotation):
            deps[name] = annotation

    duration_ms = (time.perf_counter() - start) * 1000
    if logger.isEnabledFor(10):  # DEBUG level
        logger.debug(
            f"Analyzed dependencies for {func.__qualname__ if hasattr(func, '__qualname__') else func.__name__}: "
            f"found {len(deps)} dependencies in {duration_ms:.2f}ms"
        )

    return deps


def _extract_from_annotated(annotation: Any) -> DependencyRequest | None:
    """Extract dependency from ``Annotated[T, ...]``."""
    if get_origin(annotation) is not Annotated:
        return None

    dep_type, *metadata = get_args(annotation)
    for meta in metadata:
        if isinstance(meta, Token):
            return DependencyRequest(kind=_DepKind.TOKEN, key=meta)
        if isinstance(meta, Inject):
            provider = meta.provider
            return DependencyRequest(
                kind=_DepKind.INJECT, key=dep_type, provider=provider
            )
    return None


def _extract_from_inject_type(
    annotation: Any, default: Any
) -> DependencyRequest | None:
    """Extract from ``Inject[T]`` or ``Given[T]``."""
    if not _is_inject_type(annotation):
        return None

    args = get_args(annotation)
    dep_type = args[0] if args else Any

    # Ensure dep_type is a valid key type
    if not isinstance(dep_type, type) and dep_type is not Any:
        dep_type = cast(type[Any], dep_type)

    provider: Callable[..., Any] | None = None
    if isinstance(default, Inject) and default.provider:
        provider = default.provider

    return DependencyRequest(kind=_DepKind.INJECT, key=dep_type, provider=provider)


def _extract_from_default(default: Any, annotation: Any) -> DependencyRequest | None:
    """Extract from a default value like ``Inject()``."""
    if not isinstance(default, Inject):
        return None

    dep_type = annotation if annotation is not Parameter.empty else Any

    # Ensure dep_type is a valid key type
    if not isinstance(dep_type, type) and dep_type is not Any:
        dep_type = cast(type[Any], dep_type)

    return DependencyRequest(
        kind=_DepKind.INJECT, key=dep_type, provider=default.provider
    )


def _extract_from_token(annotation: Any) -> DependencyRequest | None:
    """Extract from a ``Token`` annotation."""
    if isinstance(annotation, Token):
        return DependencyRequest(kind=_DepKind.TOKEN, key=annotation)
    return None


def _is_inject_type(annotation: Any) -> bool:
    """Check if an annotation is of type ``Inject[T]`` or ``Given[T]``."""
    # Check if it's a dynamically created Inject[T] subclass
    if isinstance(annotation, type) and issubclass(annotation, Inject):
        return True
    # Check for standard typing.Generic style
    origin = get_origin(annotation)
    return origin is Inject or (
        hasattr(origin, "__name__") and origin.__name__ in ("Inject", "Given")
    )


def _convert_to_dependency_request(
    dep: DependencyType,
) -> DependencyRequest:
    """Convert a dependency to a DependencyRequest for internal use."""
    if isinstance(dep, DependencyRequest):
        return dep
    if isinstance(dep, Token):
        return DependencyRequest(kind=_DepKind.TOKEN, key=dep)
    if isinstance(dep, Inject):
        # Get the type from the Inject instance if set
        dep_type = dep.type if hasattr(dep, "type") and dep.type else Any
        return DependencyRequest(
            kind=_DepKind.INJECT, key=dep_type, provider=dep.provider
        )
    if isinstance(dep, type):
        return DependencyRequest(kind=_DepKind.TYPE, key=dep)
    # Fallback for any other case
    return DependencyRequest(kind=_DepKind.TYPE, key=cast(type[Any], dep))


def _should_auto_inject(annotation: Any) -> bool:
    """Determine if a plain type annotation should be auto-injected."""
    return (
        isinstance(annotation, type)
        and getattr(annotation, "__module__", "builtins") != "builtins"
    )


class InjectionAnalyzer:
    """Facade to build dependency plans, for backward compatibility."""

    @staticmethod
    def build_plan(func: Callable[..., Any]) -> dict[str, DependencyRequest]:
        return analyze_dependencies(func)


def resolve_dependencies(
    deps: dict[str, DependencyType],
    container: Any,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    """
    Resolve a dictionary of dependencies synchronously.

    Args:
        deps: A dictionary of dependency requests from ``analyze_dependencies``.
        container: The container to resolve dependencies from.
        overrides: A dictionary of pre-resolved instances to use instead of resolving.

    Returns:
        A dictionary of resolved dependency instances.
    """
    start = time.perf_counter()
    resolved: dict[str, object] = {}
    ov = overrides or {}

    for name, dep in deps.items():
        if name in ov:
            resolved[name] = ov[name]
        else:
            req = _convert_to_dependency_request(dep)
            resolved[name] = _resolve_one(req, container)

    if logger.isEnabledFor(10):  # DEBUG level
        duration_ms = (time.perf_counter() - start) * 1000
        log_performance_metric(
            "resolve_dependencies", duration_ms, {"count": len(deps)}
        )

    return resolved


def _resolve_one(req: DependencyRequest, container: Any) -> object:
    """Resolve a single dependency synchronously."""
    match req.kind:
        case _DepKind.TOKEN:
            return container.get(req.key)
        case _DepKind.INJECT if req.provider:
            return req.provider()
        case _DepKind.INJECT | _DepKind.TYPE:
            return container.get(req.key)
        case _:
            # This should be unreachable if analysis is correct
            raise TypeError(f"Unsupported dependency request: {req}")


async def _aresolve_one(req: DependencyRequest, container: Any) -> object:
    """Resolve a single dependency asynchronously."""
    aget = getattr(container, "aget", None)

    async def _resolve_via_aget(key: Any) -> object:
        if aget and iscoroutinefunction(aget):
            return await aget(key)
        # Fallback to sync `get` in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, container.get, key)

    match req.kind:
        case _DepKind.TOKEN:
            return await _resolve_via_aget(req.key)
        case _DepKind.INJECT if req.provider:
            if iscoroutinefunction(req.provider):
                return await req.provider()
            result = req.provider()
            if asyncio.iscoroutine(result):
                return await cast(Awaitable[object], result)
            return result
        case _DepKind.INJECT | _DepKind.TYPE:
            return await _resolve_via_aget(req.key)
        case _:
            # This should be unreachable if analysis is correct
            raise TypeError(f"Unsupported dependency request: {req}")


async def aresolve_dependencies(
    deps: dict[str, DependencyType],
    container: Any,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    """
    Resolve a dictionary of dependencies asynchronously and in parallel.

    Args:
        deps: A dictionary of dependency requests from ``analyze_dependencies``.
        container: The container to resolve dependencies from.
        overrides: A dictionary of pre-resolved instances to use instead of resolving.

    Returns:
        A dictionary of resolved dependency instances.
    """
    start = time.perf_counter()
    resolved: dict[str, object] = {}
    tasks: dict[str, asyncio.Task[object]] = {}
    ov = overrides or {}

    for name, dep in deps.items():
        if name in ov:
            resolved[name] = ov[name]
        else:
            req = _convert_to_dependency_request(dep)
            tasks[name] = asyncio.create_task(_aresolve_one(req, container))

    if tasks:
        results = await asyncio.gather(*tasks.values())
        for name, result in zip(tasks.keys(), results, strict=False):
            resolved[name] = result

    if logger.isEnabledFor(10):  # DEBUG level
        duration_ms = (time.perf_counter() - start) * 1000
        log_performance_metric(
            "aresolve_dependencies", duration_ms, {"count": len(deps)}
        )

    return resolved


@overload
def inject(
    func: Callable[P, R], *, container: Any | None = ..., cache: bool = ...
) -> Callable[P, R]: ...


@overload
def inject(
    func: None = ..., *, container: Any | None = ..., cache: bool = ...
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def _extract_overrides(
    deps: dict[str, DependencyRequest], kwargs: dict[str, Any]
) -> dict[str, Any]:
    """Extract explicit dependency overrides from keyword arguments."""
    overrides = {}
    for name in deps:
        if name in kwargs:
            overrides[name] = kwargs.pop(name)
    return overrides


def _rebuild_kwargs(
    fn: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    resolved: dict[str, Any],
) -> dict[str, Any]:
    """Reconstruct final keyword arguments for the decorated function."""
    sig = signature(fn)
    final_kwargs: dict[str, Any] = {}
    arg_idx = 0

    for name, param in sig.parameters.items():
        if name in resolved:
            continue  # Will be injected later
        if param.kind in (
            Parameter.POSITIONAL_ONLY,
            Parameter.POSITIONAL_OR_KEYWORD,
        ) and arg_idx < len(args):
            final_kwargs[name] = args[arg_idx]
            arg_idx += 1

    final_kwargs.update(kwargs)
    final_kwargs.update(resolved)
    return final_kwargs


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
        func: Function to decorate (or None if using with parameters).
        container: Container to resolve dependencies from. If None, the
                   default container is used.
        cache: Whether to cache dependency analysis (recommended).

    Returns:
        A decorated function with automatic dependency injection.

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
        # Use cached or uncached analysis based on cache flag
        analysis_func = (
            analyze_dependencies
            if cache
            else lru_cache(maxsize=1)(analyze_dependencies)
        )

        # Pre-analyze if caching is enabled
        deps = analysis_func(fn) if cache else None

        @wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            nonlocal deps
            if deps is None:
                deps = analysis_func(fn)

            if not deps:
                return fn(*args, **kwargs)

            active_container = container or Container.get_active()
            overrides = _extract_overrides(deps, kwargs)
            resolved = resolve_dependencies(deps, active_container, overrides)
            final_kwargs = _rebuild_kwargs(fn, args, kwargs, resolved)

            return fn(**final_kwargs)

        @wraps(fn)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            nonlocal deps
            if deps is None:
                deps = analysis_func(fn)

            if not deps:
                return await cast(Awaitable[R], fn(*args, **kwargs))

            active_container = container or Container.get_active()
            overrides = _extract_overrides(deps, kwargs)
            resolved = await aresolve_dependencies(deps, active_container, overrides)
            final_kwargs = _rebuild_kwargs(fn, args, kwargs, resolved)

            return await cast(Awaitable[R], fn(**final_kwargs))

        # NOTE: The sync/async wrapper duplication is intentional.
        # While metaprogramming could reduce duplication, it would:
        # 1. Make debugging significantly harder
        # 2. Obscure the control flow
        # 3. Add complexity without meaningful benefit
        # The explicit duplication aligns with our "minimal complexity" principle.
        if iscoroutinefunction(fn):
            return cast(Callable[P, R], async_wrapper)
        return cast(Callable[P, R], sync_wrapper)

    return decorator if func is None else decorator(func)
