"""Enhanced DI Container with all optimizations and features."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from contextvars import Token as CtxToken
from functools import lru_cache
from itertools import groupby
from types import MappingProxyType, TracebackType
from typing import (
    Any,
    AsyncContextManager,
    Awaitable,
    ContextManager,
    Literal,
    Mapping,
    TypeVar,
    cast,
    overload,
)

from . import analyzer
from .cleanup_strategy import CleanupStrategy
from .contextual import ContextualContainer
from .exceptions import (
    AsyncCleanupRequiredError,
    CircularDependencyError,
    ResolutionError,
)
from .logging import log_performance_metric, log_resolution_path, logger
from .metaclasses import Injectable
from .protocols.resources import SupportsAsyncClose, SupportsClose
from .provider_record import ProviderRecord
from .tokens import Scope, Token, TokenFactory
from .types import ProviderAsync, ProviderLike, ProviderSync

__all__ = ["Container"]

T = TypeVar("T")
U = TypeVar("U")


# Module-level ContextVars provide async task isolation, ensuring each
# concurrent execution context maintains its own resolution stack.
# This is NOT global state - each async task/thread gets its own copy.
# ContextVars are specifically designed for context-local state management
# that is isolated between different asynchronous tasks and threads.
_resolution_stack: ContextVar[tuple[Token[Any], ...]] = ContextVar(
    "injx_resolution_stack", default=()
)

# O(1) cycle detection using set membership.
# Each concurrent context gets its own set for tracking resolution chains.
_resolution_set: ContextVar[set[Token[Any]]] = ContextVar(
    "injx_resolution_set", default=set()
)


class Container:
    """Ergonomic, type-safe DI container with async support.

    Features:
    - O(1) lookups with a compact registry
    - Thread/async-safe singleton initialization
    - Context-local active container management
    - Contextual scoping using ``contextvars`` (request/session)
    - Scala-inspired "given" instances for testability
    - Method chaining for concise setup and batch operations

    Class-level active container management using ContextVar ensures
    proper isolation between async tasks and threads.

    Example:
        container = Container()
        LOGGER = Token[Logger]("logger")
        container.register_singleton(LOGGER, ConsoleLogger)

        @inject
        def handler(logger: Inject[Logger]):
            logger.info("hello")
    """

    # Class-level ContextVar for active container management
    _active: ContextVar["Container | None"] = ContextVar(
        "injx_active_container", default=None
    )

    def __init__(self) -> None:
        """Initialize container."""
        logger.info("Initializing container")

        # Composition instead of inheritance
        self._contextual = ContextualContainer()
        # Set back-reference for contextual to access container methods
        if hasattr(self._contextual, "_container"):
            self._contextual._container = self

        self.tokens: TokenFactory = TokenFactory()
        self._given_providers: dict[type[object], ProviderSync[object]] = {}
        # Consolidated registry: single source of truth for all provider information
        self._registry: dict[Token[object], ProviderRecord[object]] = {}
        self._singletons: dict[Token[object], object] = {}
        self._async_locks: dict[Token[object], asyncio.Lock] = {}

        self._resolution_times: deque[float] = deque(maxlen=1000)
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        self._lock: threading.RLock = threading.RLock()
        self._singleton_locks: dict[Token[object], threading.Lock] = {}

        self._overrides: ContextVar[dict[Token[object], object] | None] = ContextVar(
            "injx_overrides",
            default=None,
        )

        self._type_index: dict[type[object], Token[object]] = {}
        self._singleton_cleanup_sync: list[Callable[[], None]] = []
        self._singleton_cleanup_async: list[Callable[[], Awaitable[None]]] = []

        # Legacy resource tracking for compatibility
        self._resources: list[SupportsClose | SupportsAsyncClose] = []

        self._auto_register()

    def _auto_register(self) -> None:
        """Automatically register classes marked with Injectable metaclass.

        Examines the Injectable registry and registers each class with its
        dependencies automatically resolved.
        """
        registry = Injectable.get_registry()

        for cls, token in registry.items():
            scope = analyzer.get_token_metadata(cls)[1]
            deps = analyzer.analyze_dependencies(cls)

            provider = self._create_provider_for_class(cls, deps)
            self.register(token, provider, scope=scope)

    def _create_provider_for_class(
        self, cls: type[object], deps: dict[str, type[object]]
    ) -> ProviderLike[object]:
        """Create a provider function for a class with dependencies.

        Args:
            cls: The class to create a provider for
            deps: Dictionary of dependency names to types

        Returns:
            A provider function that resolves dependencies and instantiates the class
        """
        # Early return for classes without dependencies
        if not deps:
            return cast(ProviderLike[object], cls)

        # Create factory with dependency injection
        def make_factory(
            target_cls: type[object] = cls,
            deps_map: dict[str, type[object]] = deps,
        ) -> Callable[[], object]:
            def provider() -> object:
                kwargs = {name: self.get(typ) for name, typ in deps_map.items()}
                return target_cls(**kwargs)

            return provider

        return make_factory()

    def _coerce_to_token(self, spec: Token[U] | type[U]) -> Token[U]:
        """Convert a type or token specification to a Token instance.

        Args:
            spec: Either a Token[T] or a type[T]

        Returns:
            A Token[T] instance, either existing or newly created
        """
        if isinstance(spec, Token):
            return spec
        # spec must be a type at this point due to type hints
        return self._find_or_create_token(spec)

    def _find_or_create_token(self, cls: type[U]) -> Token[U]:
        """Find an existing token for a type or create a new one.

        Args:
            cls: The type to find a token for

        Returns:
            An existing token if found, otherwise a new token
        """
        # Fast path: check type index
        found = self._type_index.get(cast(type[object], cls))  # type: ignore[reportGeneralTypeIssues]
        if found is not None:
            # Cast to the expected type
            return cast(Token[U], found)

        # Check registered providers and singletons
        token = self._search_for_token_by_type(cls)
        if token is not None:
            return token

        # Create new token as fallback
        return Token(cls.__name__, cls)

    def _search_for_token_by_type(self, cls: type[U]) -> Token[U] | None:
        """Search for a token matching the given type.

        Args:
            cls: The type to search for

        Returns:
            The matching token if found, None otherwise
        """
        # Search in registry
        for registered in self._registry:
            if registered.type_ == cls:
                return cast(Token[U], registered)

        # Search in singletons
        for registered in self._singletons:
            if registered.type_ == cls:
                return cast(Token[U], registered)

        return None

    def _get_override(self, token: Token[U]) -> U | None:
        current = self._overrides.get()
        if current is not None:
            val = current.get(cast(Token[object], token))
            if val is not None:
                return cast(U, val)
        return None

    @contextmanager
    def _resolution_guard(self, token: Token[Any]):
        """Guard against circular dependencies with O(1) cycle detection using sets."""
        resolution_set = _resolution_set.get()
        # O(1) lookup for cycle detection
        if token in resolution_set:
            # Get stack for error reporting
            stack = _resolution_stack.get()
            logger.error(
                f"Circular dependency detected for token '{token.name}': {list(stack)}"
            )
            raise CircularDependencyError(token, list(stack))

        new_set = resolution_set | {token}
        new_stack = (*_resolution_stack.get(), token)

        reset_set = _resolution_set.set(new_set)
        reset_stack = _resolution_stack.set(new_stack)
        try:
            yield
        finally:
            _resolution_set.reset(reset_set)
            _resolution_stack.reset(reset_stack)

    def register(
        self,
        token: Token[U] | type[U],
        provider: ProviderLike[U],
        scope: Scope | None = None,
        *,
        tags: tuple[str, ...] = (),
    ) -> "Container":
        """Register a provider for a token.

        Args:
            token: A ``Token[T]`` or a concrete ``type[T]``. If a type is
                provided, a token is created automatically.
            provider: Callable that returns the dependency instance.
            scope: Optional lifecycle override (defaults to token.scope or TRANSIENT).
            tags: Optional tags for discovery/metadata.

        Returns:
            Self, to allow method chaining.

        Example:
            container.register(Token[DB]("db"), create_db, scope=Scope.SINGLETON)
        """
        if not isinstance(token, (Token, type)):
            raise TypeError(
                "Token specification must be a Token or type; strings are not supported"
            )

        if not isinstance(token, Token):
            token = self.tokens.create(
                token.__name__, token, scope=scope or Scope.TRANSIENT, tags=tags
            )

        if not callable(provider):
            raise TypeError(
                f"Provider must be callable, got {type(provider).__name__}\n"
                f"  Fix: Pass a function or lambda that returns an instance\n"
                f"  Example: container.register(token, lambda: {token.type_.__name__}())"
            )

        with self._lock:
            obj_token = cast(Token[object], token)
            if obj_token in self._registry or obj_token in self._singletons:
                logger.error(
                    f"Registration conflict: Token '{obj_token.name}' is already registered"
                )
                raise ValueError(f"Token '{obj_token.name}' is already registered")

            # Determine the actual scope to use
            actual_scope = (
                scope
                if scope is not None
                else getattr(obj_token, "scope", Scope.TRANSIENT)
            )

            # Create ProviderRecord with precomputed metadata
            record: ProviderRecord[object] = ProviderRecord.create(  # type: ignore[reportUnknownVariableType]
                provider=cast(Callable[..., object], provider),
                scope=actual_scope,
                dependencies=(),  # TODO: Analyze dependencies when we have analyzer support
            )
            self._registry[obj_token] = record
            self._type_index[obj_token.type_] = obj_token
            logger.debug(
                f"Registered provider for token '{obj_token.name}' with scope {actual_scope}"
            )

        return self

    def register_singleton(
        self, token: Token[U] | type[U], provider: ProviderLike[U]
    ) -> "Container":
        """Register a singleton-scoped dependency."""
        return self.register(token, provider, scope=Scope.SINGLETON)

    def register_request(
        self, token: Token[U] | type[U], provider: ProviderLike[U]
    ) -> "Container":
        """Register a request-scoped dependency."""
        return self.register(token, provider, scope=Scope.REQUEST)

    def register_transient(
        self, token: Token[U] | type[U], provider: ProviderLike[U]
    ) -> "Container":
        """Register a transient-scoped dependency."""
        return self.register(token, provider, scope=Scope.TRANSIENT)

    @overload
    def register_context(
        self,
        token: Token[U] | type[U],
        cm_provider: Callable[[], ContextManager[U]],
        *,
        is_async: Literal[False],
        scope: Scope | None = None,
    ) -> "Container": ...

    @overload
    def register_context(
        self,
        token: Token[U] | type[U],
        cm_provider: Callable[[], AsyncContextManager[U]],
        *,
        is_async: Literal[True],
        scope: Scope | None = None,
    ) -> "Container": ...

    def register_context(
        self,
        token: Token[U] | type[U],
        cm_provider: Callable[[], Any],
        *,
        is_async: bool,
        scope: Scope | None = None,
    ) -> "Container":
        """Register a context-managed dependency.

        - When ``is_async=False``, ``cm_provider`` must return a ``ContextManager[T]``.
        - When ``is_async=True``, ``cm_provider`` must return an ``AsyncContextManager[T]``.

        The context is entered on first resolution within the declared scope and
        exited during scope cleanup (request/session), or on container close for
        singletons.
        """
        if not isinstance(token, (Token, type)):
            raise TypeError(
                "Token specification must be a Token or type; strings are not supported"
            )
        if not isinstance(token, Token):
            token = self.tokens.create(
                token.__name__, token, scope=scope or Scope.TRANSIENT
            )

        if not callable(cm_provider):
            raise TypeError(
                "cm_provider must be callable and return a (async) context manager"
            )

        with self._lock:
            obj_token = cast(Token[object], token)
            if obj_token in self._registry or obj_token in self._singletons:
                raise ValueError(f"Token '{obj_token.name}' is already registered")

            # Determine the actual scope to use
            actual_scope = (
                scope
                if scope is not None
                else getattr(obj_token, "scope", Scope.TRANSIENT)
            )

            # Context managers have special cleanup strategies
            cleanup = (
                CleanupStrategy.ASYNC_CONTEXT if is_async else CleanupStrategy.CONTEXT
            )

            # Create ProviderRecord with explicit cleanup strategy
            record = ProviderRecord(
                provider=cast(Callable[..., object], cm_provider),
                cleanup=cleanup,
                scope=actual_scope,
                is_async=is_async,
                dependencies=(),
            )
            self._registry[obj_token] = record
            self._type_index[obj_token.type_] = obj_token
        return self

    def register_context_sync(
        self,
        token: Token[U] | type[U],
        cm_provider: Callable[[], ContextManager[U]],
        *,
        scope: Scope | None = None,
    ) -> "Container":
        """Typed helper to register a sync context-managed provider.

        Equivalent to ``register_context(..., is_async=False)``.
        """
        return self.register_context(token, cm_provider, is_async=False, scope=scope)

    def register_context_async(
        self,
        token: Token[U] | type[U],
        cm_provider: Callable[[], AsyncContextManager[U]],
        *,
        scope: Scope | None = None,
    ) -> "Container":
        """Typed helper to register an async context-managed provider.

        Equivalent to ``register_context(..., is_async=True)``.
        """
        return self.register_context(token, cm_provider, is_async=True, scope=scope)

    def register_value(self, token: Token[U] | type[U], value: U) -> "Container":
        """Register a pre-created value as a singleton."""
        if isinstance(token, type):
            token = self.tokens.singleton(token.__name__, token)

        obj_token = cast(Token[object], token)
        if obj_token in self._registry or obj_token in self._singletons:
            raise ValueError(f"Token '{obj_token.name}' is already registered")
        self._singletons[obj_token] = value
        return self

    def override(self, token: Token[U], value: U) -> None:
        """Override a dependency for the current concurrent context only.

        Uses a ContextVar-backed mapping so overrides are isolated between
        threads/tasks. Prefer ``use_overrides`` for scoped overrides.
        """
        parent = self._overrides.get()
        merged: dict[Token[object], object] = dict(parent) if parent else {}
        merged[cast(Token[object], token)] = value
        self._overrides.set(merged)

    def given(self, type_: type[U], provider: ProviderSync[U] | U) -> "Container":
        """Register a given instance for a type (Scala-style)."""
        if callable(provider):
            self._given_providers[type_] = cast(ProviderSync[object], provider)
        else:
            self._given_providers[type_] = lambda p=provider: p

        return self

    def resolve_given(self, type_: type[U]) -> U | None:
        """Resolve a given instance by type."""
        provider = self._given_providers.get(type_)
        if provider:
            return cast(ProviderSync[U], provider)()
        return None

    @contextmanager
    def using(
        self,
        mapping: Mapping[type[object], object] | None = None,
        **givens: object,
    ) -> Iterator[Container]:
        """Temporarily register "given" instances for the current block.

        Supports both an explicit mapping of types to instances and
        keyword arguments that match type names previously registered
        via ``given()``.
        """
        old_givens = self._given_providers.copy()

        if mapping:
            for t, instance in mapping.items():
                self.given(t, instance)

        if givens:
            known_types = list(self._given_providers.keys())
            for name, instance in givens.items():
                for t in known_types:
                    if getattr(t, "__name__", "") == name:
                        self.given(t, instance)
                        break

        try:
            yield self
        finally:
            self._given_providers = old_givens

    def _obj_token(self, token: Token[U]) -> Token[object]:
        return cast(Token[object], token)

    def _get_singleton_lock(self, token: Token[object]) -> threading.Lock:
        """Get or create a singleton lock for the token, with cleanup after use."""
        with self._lock:
            if token not in self._singleton_locks:
                self._singleton_locks[token] = threading.Lock()
            return self._singleton_locks[token]

    def _cleanup_singleton_lock(self, token: Token[object]) -> None:
        """Remove singleton lock after successful initialization to prevent memory leak."""
        with self._lock:
            self._singleton_locks.pop(token, None)

    def _canonicalize(self, token: Token[U]) -> Token[U]:
        """Return the registered token that matches by name and type (ignore scope).

        This allows callers to construct a token with the same name/type but different
        scope and still resolve the registered binding.
        """
        obj_token = self._obj_token(token)
        if obj_token in self._registry or obj_token in self._singletons:
            return token
        for t in self._registry.keys():
            if t.name == token.name and t.type_ == token.type_:
                return cast(Token[U], t)
        for t in self._singletons.keys():
            if t.name == token.name and t.type_ == token.type_:
                return cast(Token[U], t)
        return token

    def _get_provider(self, token: Token[U]) -> ProviderLike[U]:
        token = self._canonicalize(token)
        obj_token = self._obj_token(token)
        record = self._registry.get(obj_token)
        if record is None:
            logger.error(f"No provider registered for token '{obj_token.name}'")
            raise ResolutionError(
                token,
                [],
                (
                    f"No provider registered for token '{token.name}'. "
                    f"Fix: register a provider for this token before resolving."
                ),
            )
        return cast(ProviderLike[U], record.provider)

    def _get_scope(self, token: Token[U]) -> Scope:
        token = self._canonicalize(token)
        obj_token = self._obj_token(token)
        record = self._registry.get(obj_token)
        if record is not None:
            return record.scope
        return token.scope

    def _get_singleton_cached(self, token: Token[U]) -> U | None:
        token = self._canonicalize(token)
        obj_token = self._obj_token(token)
        if obj_token in self._singletons:
            return cast(U, self._singletons[obj_token])
        return None

    def _set_singleton_cached(self, token: Token[U], value: U) -> None:
        self._singletons[self._obj_token(token)] = value

    def _ensure_async_lock(self, token: Token[U]) -> asyncio.Lock:
        obj_token = self._obj_token(token)
        lock = self._async_locks.get(obj_token)
        if lock is None:
            lock = asyncio.Lock()
            self._async_locks[obj_token] = lock
        return lock

    def get(self, token: Token[U] | type[U]) -> U:
        """Resolve a dependency synchronously.

        Args:
            token: The ``Token[T]`` or ``type[T]`` to resolve.

        Returns:
            The resolved instance.

        Raises:
            ResolutionError: If no provider is registered or resolution fails.
        """
        # Fast path: check for given instances (85% case)
        instance = self._resolve_fast_path(token)
        if instance is not None:
            return instance

        # Normalize token for resolution
        token = self._prepare_token_for_resolution(token)

        # Standard resolution path
        self._cache_misses += 1
        with self._resolution_guard(token):
            if logger.isEnabledFor(logging.DEBUG):
                log_resolution_path(token, list(_resolution_stack.get()))
            start_time = time.perf_counter()
            result = self._resolve_sync(token)
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_performance_metric(
                "resolve", duration_ms, {"token": token.name, "scope": token.scope.name}
            )
            return result

    def _resolve_fast_path(self, token: Token[U] | type[U]) -> U | None:
        """Attempt fast resolution for cached or given instances.

        Args:
            token: The token or type to resolve

        Returns:
            The resolved instance if found in cache, None otherwise
        """
        # Check givens for types
        if isinstance(token, type):
            given = self.resolve_given(token)
            if given is not None:
                self._cache_hits += 1
                return given

        # Normalize and check overrides/context
        normalized = self._coerce_to_token(token)
        normalized = self._canonicalize(normalized)

        # Check override
        override = self._get_override(normalized)
        if override is not None:
            self._cache_hits += 1
            return override

        # Check context
        instance = self.resolve_from_context(normalized)
        if instance is not None:
            self._cache_hits += 1
            return instance

        return None

    def _prepare_token_for_resolution(self, token: Token[U] | type[U]) -> Token[U]:
        """Prepare a token for resolution by normalizing it.

        Args:
            token: The token or type to prepare

        Returns:
            A normalized Token instance
        """
        token = self._coerce_to_token(token)
        return self._canonicalize(token)

    def _resolve_sync(self, token: Token[U]) -> U:
        """Resolve a dependency synchronously.

        Args:
            token: The normalized token to resolve

        Returns:
            The resolved instance

        Raises:
            ResolutionError: If resolution fails
        """
        obj_token = cast(Token[object], token)
        record = self._registry.get(obj_token)
        effective_scope = self._get_scope(token)

        # Dispatch based on registration type
        if record is not None:
            if record.cleanup == CleanupStrategy.ASYNC_CONTEXT:
                raise ResolutionError(
                    token,
                    [],
                    "Context-managed provider is async; Use aget() for async providers",
                )
            elif record.cleanup == CleanupStrategy.CONTEXT:
                return self._resolve_sync_context(token, record, effective_scope)

        return self._resolve_sync_provider(token, effective_scope)

    def _resolve_sync_context(
        self, token: Token[U], record: ProviderRecord[object], scope: Scope
    ) -> U:
        """Resolve a sync context-managed dependency.

        Args:
            token: The token to resolve
            record: The provider record with context manager
            scope: The effective scope

        Returns:
            The resolved instance
        """
        match scope:
            case Scope.SINGLETON:
                return self._resolve_singleton_context_sync(token, record)
            case Scope.REQUEST | Scope.SESSION:
                return self._resolve_scoped_context_sync(token, record, scope)
            case _:
                return self._resolve_transient_context_sync(token, record)

    def _resolve_singleton_context_sync(
        self, token: Token[U], record: ProviderRecord[object]
    ) -> U:
        """Resolve a singleton context-managed dependency.

        Args:
            token: The token to resolve
            record: The provider record with context manager

        Returns:
            The resolved instance
        """
        obj_token = self._obj_token(token)
        with self._get_singleton_lock(obj_token):
            # Check cache inside lock
            cached = self._get_singleton_cached(token)
            if cached is not None:
                return cached

            # Enter context and cache
            cm = cast(ContextManager[U], record.provider())
            value = cm.__enter__()
            self._set_singleton_cached(token, value)

            # Register cleanup
            self._register_singleton_context_cleanup(cm, value)

        self._cleanup_singleton_lock(obj_token)
        return value

    def _resolve_scoped_context_sync(
        self, token: Token[U], record: ProviderRecord[object], scope: Scope
    ) -> U:
        """Resolve a scoped context-managed dependency.

        Args:
            token: The token to resolve
            record: The provider record with context manager
            scope: The scope (REQUEST or SESSION)

        Returns:
            The resolved instance
        """
        cm = cast(ContextManager[U], record.provider())
        value = cm.__enter__()
        self.store_in_context(token, value)

        # Register scope-specific cleanup
        def cleanup(cm: ContextManager[Any] = cm) -> None:
            cm.__exit__(None, None, None)

        match scope:
            case Scope.REQUEST:
                self._register_request_cleanup_sync(cleanup)
            case Scope.SESSION:
                self._register_session_cleanup_sync(cleanup)
            case _:
                pass  # SINGLETON and TRANSIENT don't need scoped cleanup

        self._track_resource(value)
        return value

    def _resolve_transient_context_sync(
        self, token: Token[U], record: ProviderRecord[object]
    ) -> U:
        """Resolve a transient context-managed dependency.

        Args:
            token: The token to resolve
            record: The provider record with context manager

        Returns:
            The resolved instance
        """
        cm = cast(ContextManager[U], record.provider())
        value = cm.__enter__()
        # Note: transient context managers are not tracked for cleanup
        # as they have no defined lifecycle
        return value

    def _resolve_sync_provider(self, token: Token[U], scope: Scope) -> U:
        """Resolve a standard synchronous provider.

        Args:
            token: The token to resolve
            scope: The effective scope

        Returns:
            The resolved instance

        Raises:
            ResolutionError: If provider is async
        """
        provider = self._get_provider(token)

        # Validate sync provider
        if asyncio.iscoroutinefunction(cast(Callable[..., Any], provider)):
            raise ResolutionError(
                token, [], "Provider is async; Use aget() for async providers"
            )

        match scope:
            case Scope.SINGLETON:
                return self._resolve_singleton_sync(token, provider)
            case Scope.REQUEST | Scope.SESSION:
                return self._resolve_scoped_sync(token, provider, scope)
            case _:
                return self._resolve_transient_sync(token, provider)

    def _resolve_singleton_sync(self, token: Token[U], provider: ProviderLike[U]) -> U:
        """Resolve a singleton provider synchronously.

        Args:
            token: The token to resolve
            provider: The provider function

        Returns:
            The resolved instance
        """
        obj_token = self._obj_token(token)
        with self._get_singleton_lock(obj_token):
            # Double-check pattern
            cached = self._get_singleton_cached(token)
            if cached is not None:
                return cached

            # Create and cache instance
            instance = cast(ProviderSync[U], provider)()
            self._validate_and_track(token, instance)
            self._set_singleton_cached(token, instance)

        self._cleanup_singleton_lock(obj_token)
        return instance

    def _resolve_scoped_sync(
        self, token: Token[U], provider: ProviderLike[U], scope: Scope
    ) -> U:
        """Resolve a scoped provider synchronously.

        Args:
            token: The token to resolve
            provider: The provider function
            scope: The scope (REQUEST or SESSION)

        Returns:
            The resolved instance
        """
        instance = cast(ProviderSync[U], provider)()
        self._validate_and_track(token, instance)
        self.store_in_context(token, instance)
        return instance

    def _resolve_transient_sync(self, token: Token[U], provider: ProviderLike[U]) -> U:
        """Resolve a transient provider synchronously.

        Args:
            token: The token to resolve
            provider: The provider function

        Returns:
            The resolved instance
        """
        instance = cast(ProviderSync[U], provider)()
        self._validate_and_track(token, instance)
        return instance

    def _register_singleton_context_cleanup(
        self, cm: ContextManager[Any], value: Any
    ) -> None:
        """Register cleanup for a singleton context manager.

        Args:
            cm: The context manager
            value: The managed value
        """

        def cleanup(cm: ContextManager[Any] = cm) -> None:
            cm.__exit__(None, None, None)

        self._singleton_cleanup_sync.append(cleanup)
        self._track_resource(value)

    def _track_resource(self, value: Any) -> None:
        """Track a resource for cleanup if it supports close methods.

        Args:
            value: The value to track
        """
        if isinstance(value, (SupportsClose, SupportsAsyncClose)):
            self._resources.append(value)

    async def aget(self, token: Token[U] | type[U]) -> U:
        """Resolve a dependency asynchronously.

        Equivalent to :meth:`get` but awaits async providers and uses
        async locks for singleton initialization.
        """
        # Fast path: check for cached instances (85% case)
        instance = self._resolve_fast_path(token)
        if instance is not None:
            return instance

        # Normalize token for resolution
        token = self._prepare_token_for_resolution(token)

        # Async resolution path
        self._cache_misses += 1
        with self._resolution_guard(token):
            return await self._resolve_async(token)

    async def _resolve_async(self, token: Token[U]) -> U:
        """Resolve a dependency asynchronously.

        Args:
            token: The normalized token to resolve

        Returns:
            The resolved instance
        """
        obj_token = cast(Token[object], token)
        record = self._registry.get(obj_token)
        effective_scope = self._get_scope(token)

        # Dispatch based on registration type
        if record is not None:
            if record.cleanup == CleanupStrategy.ASYNC_CONTEXT:
                return await self._resolve_async_context(token, record, effective_scope)
            elif record.cleanup == CleanupStrategy.CONTEXT:
                # Sync context managers can be used in async context
                return self._resolve_sync_context(token, record, effective_scope)

        return await self._resolve_async_provider(token, effective_scope)

    async def _resolve_async_context(
        self, token: Token[U], record: ProviderRecord[object], scope: Scope
    ) -> U:
        """Resolve an async context-managed dependency.

        Args:
            token: The token to resolve
            reg: The registration with async context manager
            scope: The effective scope

        Returns:
            The resolved instance
        """
        match scope:
            case Scope.SINGLETON:
                return await self._resolve_singleton_context_async(token, record)
            case Scope.REQUEST | Scope.SESSION:
                return await self._resolve_scoped_context_async(token, record, scope)
            case _:
                return await self._resolve_transient_context_async(token, record)

    async def _resolve_singleton_context_async(
        self, token: Token[U], record: ProviderRecord[object]
    ) -> U:
        """Resolve a singleton async context-managed dependency.

        Args:
            token: The token to resolve
            reg: The registration with async context manager

        Returns:
            The resolved instance
        """
        lock = self._ensure_async_lock(token)
        async with lock:
            # Check cache inside lock
            cached = self._get_singleton_cached(token)
            if cached is not None:
                return cached

            # Enter async context and cache
            cm = cast(AsyncContextManager[U], record.provider())
            value = await cm.__aenter__()
            self._set_singleton_cached(token, value)

            # Register async cleanup
            await self._register_singleton_context_cleanup_async(cm, value)

        return value

    async def _resolve_scoped_context_async(
        self, token: Token[U], record: ProviderRecord[object], scope: Scope
    ) -> U:
        """Resolve a scoped async context-managed dependency.

        Args:
            token: The token to resolve
            reg: The registration with async context manager
            scope: The scope (REQUEST or SESSION)

        Returns:
            The resolved instance
        """
        cm = cast(AsyncContextManager[U], record.provider())
        value = await cm.__aenter__()
        self.store_in_context(token, value)

        # Register scope-specific async cleanup
        async def cleanup(cm: AsyncContextManager[U] = cm) -> None:
            await cm.__aexit__(None, None, None)

        match scope:
            case Scope.REQUEST:
                self._register_request_cleanup_async(cleanup)
            case Scope.SESSION:
                self._register_session_cleanup_async(cleanup)
            case _:
                pass  # SINGLETON and TRANSIENT don't need scoped cleanup

        self._track_resource(value)
        return value

    async def _resolve_transient_context_async(
        self, token: Token[U], record: ProviderRecord[object]
    ) -> U:
        """Resolve a transient async context-managed dependency.

        Args:
            token: The token to resolve
            reg: The registration with async context manager

        Returns:
            The resolved instance
        """
        cm = cast(AsyncContextManager[U], record.provider())
        value = await cm.__aenter__()
        # Note: transient context managers are not tracked for cleanup
        return value

    async def _resolve_async_provider(self, token: Token[U], scope: Scope) -> U:
        """Resolve a standard provider asynchronously.

        Args:
            token: The token to resolve
            scope: The effective scope

        Returns:
            The resolved instance
        """
        provider = self._get_provider(token)

        match scope:
            case Scope.SINGLETON:
                return await self._resolve_singleton_async(token, provider)
            case Scope.REQUEST | Scope.SESSION:
                return await self._resolve_scoped_async(token, provider, scope)
            case _:
                return await self._resolve_transient_async(token, provider)

    async def _resolve_singleton_async(
        self, token: Token[U], provider: ProviderLike[U]
    ) -> U:
        """Resolve a singleton provider asynchronously.

        Args:
            token: The token to resolve
            provider: The provider function

        Returns:
            The resolved instance
        """
        lock = self._ensure_async_lock(token)
        async with lock:
            # Double-check pattern
            cached = self._get_singleton_cached(token)
            if cached is not None:
                return cached

            # Create instance (async or sync)
            instance = await self._call_provider_async(provider)
            self._validate_and_track(token, instance)
            self._set_singleton_cached(token, instance)

        return instance

    async def _resolve_scoped_async(
        self, token: Token[U], provider: ProviderLike[U], scope: Scope
    ) -> U:
        """Resolve a scoped provider asynchronously.

        Args:
            token: The token to resolve
            provider: The provider function
            scope: The scope (REQUEST or SESSION)

        Returns:
            The resolved instance
        """
        instance = await self._call_provider_async(provider)
        self._validate_and_track(token, instance)
        self.store_in_context(token, instance)
        return instance

    async def _resolve_transient_async(
        self, token: Token[U], provider: ProviderLike[U]
    ) -> U:
        """Resolve a transient provider asynchronously.

        Args:
            token: The token to resolve
            provider: The provider function

        Returns:
            The resolved instance
        """
        instance = await self._call_provider_async(provider)
        self._validate_and_track(token, instance)
        return instance

    async def _call_provider_async(self, provider: ProviderLike[U]) -> U:
        """Call a provider function, handling both sync and async providers.

        Args:
            provider: The provider function

        Returns:
            The resolved instance
        """
        if asyncio.iscoroutinefunction(cast(Callable[..., Any], provider)):
            return await cast(ProviderAsync[U], provider)()
        return cast(ProviderSync[U], provider)()

    async def _register_singleton_context_cleanup_async(
        self, cm: AsyncContextManager[Any], value: Any
    ) -> None:
        """Register cleanup for a singleton async context manager.

        Args:
            cm: The async context manager
            value: The managed value
        """

        async def cleanup(cm: AsyncContextManager[Any] = cm) -> None:
            await cm.__aexit__(None, None, None)

        self._singleton_cleanup_async.append(cleanup)
        self._track_resource(value)

    def batch_register(
        self, registrations: list[tuple[Token[object], ProviderLike[object]]]
    ) -> Container:
        """Register multiple dependencies at once."""
        for token, provider in registrations:
            self.register(token, provider)
        return self

    def batch_resolve(self, tokens: list[Token[object]]) -> dict[Token[object], object]:
        """Resolve multiple dependencies efficiently (sync)."""
        sorted_tokens = sorted(tokens, key=lambda t: t.scope.value)
        results: dict[Token[object], object] = {}
        for _scope, group in groupby(sorted_tokens, key=lambda t: t.scope):
            group_list = list(group)
            for tk in group_list:
                results[tk] = self.get(tk)
        return results

    async def batch_resolve_async(
        self, tokens: list[Token[object]]
    ) -> dict[Token[object], object]:
        """Async batch resolution with parallel execution."""
        tasks = {token: self.aget(token) for token in tokens}
        results_list: list[object] = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results_list, strict=True))

    @lru_cache(maxsize=512)
    def _get_resolution_path(self, token: Token[Any]) -> tuple[Token[Any], ...]:
        """Get resolution path for a token (cached)."""
        return (token,)

    @property
    def cache_hit_rate(self) -> float:
        total = self._cache_hits + self._cache_misses
        return 0.0 if total == 0 else self._cache_hits / total

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_providers": len(self._registry),
            "singletons": len(self._singletons),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "avg_resolution_time": (
                sum(self._resolution_times) / len(self._resolution_times)
                if self._resolution_times
                else 0
            ),
        }

    def get_providers_view(
        self,
    ) -> MappingProxyType[Token[object], ProviderRecord[object]]:
        """Return a read-only view of registered providers."""
        return MappingProxyType(self._registry)

    def resources_view(self) -> tuple[SupportsClose | SupportsAsyncClose, ...]:
        """Return a read-only snapshot of tracked resources for tests/inspection."""
        return tuple(self._resources)

    def inject(
        self, func: Callable[..., Any] | None = None, *, cache: bool = True
    ) -> Callable[..., Any]:
        """Alias to injx.injection.inject bound to this container.

        Enables ``@container.inject`` usage in addition to
        ``@inject(container=container)``.
        """
        from .injection import inject as _inject

        if func is None:
            return _inject(container=self, cache=cache)
        return _inject(func, container=self, cache=cache)

    def has(self, token: Token[Any] | type[Any]) -> bool:
        """Return True if the token/type is known to the container."""
        if isinstance(token, type):
            if token in self._given_providers:
                return True
            token = Token(token.__name__, token)
        obj_token = cast(Token[object], token)
        return obj_token in self._registry or obj_token in self._singletons

    def clear(self) -> None:
        """Clear caches and statistics; keep provider registrations intact."""
        with self._lock:
            self._singletons.clear()
            self._given_providers.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            self._resolution_times.clear()
        self.clear_all_contexts()

    def __repr__(self) -> str:
        return (
            "Container("
            f"providers={len(self._registry)}, "
            f"singletons={len(self._singletons)}, "
            f"cache_hit_rate={self.cache_hit_rate:.2%})"
        )

    def __enter__(self) -> Container:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._singleton_cleanup_async:
            raise AsyncCleanupRequiredError(
                "singleton",
                "Use 'await container.aclose()' or an async scope.",
            )
        for fn in reversed(self._singleton_cleanup_sync):
            try:
                fn()
            except Exception:
                pass

    async def __aenter__(self) -> Container:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._singleton_cleanup_async:
            tasks = [fn() for fn in reversed(self._singleton_cleanup_async)]
            await asyncio.gather(*tasks, return_exceptions=True)
        for fn in reversed(self._singleton_cleanup_sync):
            try:
                fn()
            except Exception:
                pass

    async def aclose(self) -> None:
        """Async close: close tracked resources and clear caches."""
        await self.__aexit__(None, None, None)
        self.clear()

    async def dispose(self) -> None:
        """Alias for aclose to align with tests and docs."""
        await self.aclose()

    @contextmanager
    def use_overrides(self, mapping: dict[Token[Any], object]) -> Iterator[None]:
        """Temporarily override tokens for this concurrent context.

        Example:
            with container.use_overrides({LOGGER: fake_logger}):
                svc = container.get(SERVICE)
                ...
        """
        parent = self._overrides.get()
        merged: dict[Token[object], object] = dict(parent) if parent else {}
        merged.update(cast(dict[Token[object], object], mapping))
        token: CtxToken[dict[Token[object], object] | None] = self._overrides.set(
            merged
        )
        try:
            yield
        finally:
            self._overrides.reset(token)

    def clear_overrides(self) -> None:
        """Clear all overrides for the current context."""
        if self._overrides.get() is not None:
            self._overrides.set(None)

    def _validate_and_track(self, token: Token[Any], instance: object) -> None:
        if not token.validate(instance):
            raise TypeError(
                f"Provider for token '{token.name}' returned {type(instance).__name__}, expected {token.type_.__name__}"
            )

    @classmethod
    def get_active(cls) -> "Container":
        """Get or create the active container for the current context.

        Uses ContextVar to ensure proper isolation between async tasks and threads.
        Creates a new container on first access in each context.

        Returns:
            The active container for the current context
        """
        container = cls._active.get()
        if container is None:
            container = cls()
            cls._active.set(container)
        return container

    @classmethod
    def set_active(cls, container: "Container | None") -> None:
        """Set the active container for the current context.

        Args:
            container: Container to set as active, or None to clear
        """
        cls._active.set(container)

    def activate(self) -> ContextManager[None]:
        """Context manager to activate this container.

        Example:
            container = Container()
            with container.activate():
                # This container is now active
                service = some_injected_function()
        """

        @contextmanager
        def _activate():
            old = self._active.get()
            self._active.set(self)
            try:
                yield
            finally:
                self._active.set(old)

        return _activate()

    # Delegate contextual methods to composed ContextualContainer
    def request_scope(self):
        """Create a request scope. Delegates to ContextualContainer."""
        return self._contextual.request_scope()

    def async_request_scope(self):
        """Create an async request scope. Delegates to ContextualContainer."""
        return self._contextual.async_request_scope()

    def session_scope(self):
        """Create a session scope. Delegates to ContextualContainer."""
        return self._contextual.session_scope()

    def resolve_from_context(self, token: Token[T]) -> T | None:
        """Resolve from context. Delegates to ContextualContainer."""
        return self._contextual.resolve_from_context(token)

    def store_in_context(self, token: Token[T], instance: T) -> None:
        """Store in context. Delegates to ContextualContainer."""
        self._contextual.store_in_context(token, instance)

    def clear_request_context(self) -> None:
        """Clear request context. Delegates to ContextualContainer."""
        self._contextual.clear_request_context()

    def clear_session_context(self) -> None:
        """Clear session context. Delegates to ContextualContainer."""
        self._contextual.clear_session_context()

    def clear_all_contexts(self) -> None:
        """Clear all contexts. Delegates to ContextualContainer."""
        self._contextual.clear_all_contexts()
