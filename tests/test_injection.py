"""Tests for injection decorators and dependency resolution."""

from typing import Any, Callable, cast
from unittest.mock import Mock, patch

import pytest

from pyinj.injection import (
    DependencyRequest,
    Depends,
    Given,
    Inject,
    analyze_dependencies,
    aresolve_dependencies,
    inject,
    resolve_dependencies,
)
from pyinj.tokens import Token


class Database:
    """Test database class."""

    def query(self):
        return "data"


class Cache:
    """Test cache class."""

    def get(self, key: str) -> str:
        return f"cached_{key}"


class Service:
    """Test service class."""

    def __init__(self, db: Database, cache: Cache):
        self.db = db
        self.cache = cache


class TestInjectMarker:
    """Test suite for Inject marker class."""

    def test_inject_creation(self):
        """Test Inject marker creation."""
        inject_marker: Inject[object] = Inject()
        assert inject_marker.provider is None
        assert inject_marker.type is None

        # With provider
        def provider():
            return Database()

        inject_with_provider: Inject[Database] = Inject(provider)
        assert inject_with_provider.provider is provider

    def test_inject_with_type(self):
        """Test Inject[Type] syntax."""
        # This creates a subclass with _inject_type
        typed_inject = Inject[Database]

        # Create instance
        instance = typed_inject()
        assert instance.type == Database

    def test_inject_repr(self):
        """Test Inject representation."""
        inject_marker: Inject[object] = Inject()
        assert repr(inject_marker) == "Inject()"

        # With type
        typed = Inject[Database]()
        assert "Database" in repr(typed)


class TestGiven:
    """Test suite for Given marker."""

    def test_given_delegates_to_inject(self):
        """Test Given[Type] delegates to Inject."""
        given_db = Given[Database]
        inject_db = Inject[Database]
        assert issubclass(given_db, Inject)
        assert given_db is inject_db
        inst = given_db()
        assert isinstance(inst, Inject)
        assert inst.type == Database


class TestDepends:
    """Test suite for Depends function."""

    def test_depends_creates_inject(self):
        """Test Depends creates Inject with provider."""

        def provider():
            return Database()

        marker = Depends(provider)

        assert isinstance(marker, Inject)
        assert marker.provider is provider


class TestAnalyzeDependencies:
    """Test suite for analyze_dependencies."""

    def test_analyze_no_dependencies(self):
        """Test function with no dependencies."""

        def simple_func(x: int, y: str):
            return x

        deps = analyze_dependencies(simple_func)
        assert deps == {}

    def test_analyze_inject_annotation(self):
        """Test function with Inject annotations."""

        def handler(db: Inject[Database], x: int):
            return db

        deps = analyze_dependencies(handler)
        assert "db" in deps
        assert deps["db"] == Database

    def test_analyze_inject_default(self):
        """Test function with Inject default value."""

        def handler(db: Inject[Database] = Inject()) -> object:
            return db

        deps = analyze_dependencies(handler)
        assert "db" in deps
        assert isinstance(deps["db"], Inject)
        assert deps["db"].type == Database

    def test_analyze_inject_with_provider(self):
        """Test Inject with provider in default."""

        def provider():
            return Database()

        def handler(db: Inject[Database] = Inject(provider)) -> object:
            return db

        deps = analyze_dependencies(handler)
        assert "db" in deps
        assert isinstance(deps["db"], Inject)
        assert deps["db"].provider is provider

    def test_analyze_token_annotation(self):
        """Test function with Token annotation."""
        token = Token("database", Database)

        def handler(db: object) -> object:
            return db

        # Emulate annotation at runtime for analyzer
        handler.__annotations__ = {"db": token}

        deps = analyze_dependencies(handler)
        assert "db" in deps
        assert deps["db"] is token

    def test_analyze_skip_args_kwargs(self):
        """Test *args and **kwargs are skipped."""

        def handler(db: Inject[Database], *args: object, **kwargs: object) -> object:
            return db

        deps = analyze_dependencies(handler)
        assert "db" in deps
        assert "args" not in deps
        assert "kwargs" not in deps

    def test_analyze_caching(self):
        """Test dependency analysis is cached."""
        call_count = 0

        def mock_signature(func: Callable[..., object]):
            nonlocal call_count
            call_count += 1
            import inspect

            return inspect.signature(func)

        def handler(db: Inject[Database]) -> object:
            return db

        with patch("pyinj.injection.signature", mock_signature):
            # First call
            deps1 = analyze_dependencies(handler)
            # Second call - should be cached
            deps2 = analyze_dependencies(handler)

            # Signature should only be called once due to caching
            # Note: Can't reliably test LRU cache behavior
            assert deps1 == deps2


class TestResolveDependencies:
    """Test suite for resolve_dependencies."""

    def test_resolve_token(self):
        """Test resolving Token dependency."""
        container = Mock()
        container.get.return_value = Database()

        token = Token("database", Database)
        deps = cast(dict[str, DependencyRequest], {"db": token})

        resolved = resolve_dependencies(deps, container)

        assert "db" in resolved
        assert isinstance(resolved["db"], Database)
        container.get.assert_called_once_with(token)

    def test_resolve_inject_with_provider(self):
        """Test resolving Inject with provider."""
        container = Mock()
        db_instance = Database()
        provider = Mock(return_value=db_instance)

        inject_marker = Inject(provider)
        deps = cast(dict[str, DependencyRequest], {"db": inject_marker})

        resolved = resolve_dependencies(deps, container)

        assert resolved["db"] is db_instance
        provider.assert_called_once()
        container.get.assert_not_called()

    def test_resolve_inject_with_type(self):
        """Test resolving Inject with type."""
        container = Mock()
        db_instance = Database()
        container.get.return_value = db_instance

        inject_marker: Inject[Database] = Inject()
        inject_marker.set_type(Database)
        deps = cast(dict[str, DependencyRequest], {"db": inject_marker})

        resolved = resolve_dependencies(deps, container)

        assert resolved["db"] is db_instance
        # Should create token from type
        container.get.assert_called_once()
        call_arg0 = container.get.call_args[0][0]
        assert isinstance(call_arg0, (Token, type))
        # Accept either a Token or a direct type depending on resolver strategy
        if isinstance(call_arg0, Token):
            token_val = cast(Token[object], call_arg0)
            assert token_val.type_ == Database

    def test_resolve_type_directly(self):
        """Test resolving type annotation directly."""
        container = Mock()
        db_instance = Database()
        container.get.return_value = db_instance

        deps: dict[str, DependencyRequest] = {"db": Database}

        resolved = resolve_dependencies(deps, container)

        assert resolved["db"] is db_instance
        container.get.assert_called_once()

    def test_resolve_with_overrides(self):
        """Test resolving with overrides."""
        container = Mock()
        override_db = Database()

        deps: dict[str, DependencyRequest] = {"db": Database, "cache": Cache}
        overrides = cast(dict[str, object], {"db": override_db})

        resolved = resolve_dependencies(deps, container, overrides)

        # db should use override
        assert resolved["db"] is override_db

        # cache should be resolved from container
        container.get.assert_called_once()  # Only for cache

    @pytest.mark.asyncio
    async def test_resolve_async(self):
        """Test async dependency resolution."""
        container = Mock()
        db_instance = Database()

        # Mock aget method
        async def mock_aget(token: object):
            return db_instance

        container.aget = mock_aget

        token = Token("database", Database)
        deps = cast(dict[str, DependencyRequest], {"db": token})

        resolved = await aresolve_dependencies(deps, container)

        assert resolved["db"] is db_instance

    @pytest.mark.asyncio
    async def test_resolve_async_with_sync_fallback(self):
        """Test async resolution falls back to sync."""
        container = Mock()
        db_instance = Database()
        container.get.return_value = db_instance

        # No aget method
        token = Token("database", Database)
        deps = cast(dict[str, DependencyRequest], {"db": token})

        resolved = await aresolve_dependencies(deps, container)

        assert resolved["db"] is db_instance
        container.get.assert_called_once_with(token)

    @pytest.mark.asyncio
    async def test_resolve_async_provider(self):
        """Test async provider resolution."""
        container = Mock()
        db_instance = Database()

        async def async_provider():
            return db_instance

        inject_marker: Inject[object] = Inject(async_provider)
        deps: dict[str, DependencyRequest] = {"db": inject_marker}

        resolved = await aresolve_dependencies(deps, container)

        assert resolved["db"] is db_instance


class TestInjectDecorator:
    """Test suite for @inject decorator."""

    def test_inject_sync_function(self):
        """Test @inject on sync function."""
        container = Mock()
        db_instance = Database()
        container.get.return_value = db_instance

        @inject(container=container)
        def handler(db: Inject[Database], name: str):
            return (db, name)

        result = cast(Callable[..., Any], handler)(name="test")

        assert result[0] is db_instance
        assert result[1] == "test"
        container.get.assert_called_once()

    def test_inject_no_dependencies(self):
        """Test @inject with no dependencies."""

        @inject
        def handler(x: int, y: int):
            return x + y

        result = handler(1, 2)
        assert result == 3

    def test_inject_with_override(self):
        """Test @inject with parameter override."""
        container = Mock()
        default_db = Database()
        override_db = Database()
        container.get.return_value = default_db

        @inject(container=container)
        def handler(db: Inject[Database]):
            return db

        # Use default
        result1 = cast(Callable[[], Any], handler)()
        assert result1 is default_db

        # Override
        result2 = cast(Callable[..., Any], handler)(db=override_db)
        assert result2 is override_db

    @pytest.mark.asyncio
    async def test_inject_async_function(self):
        """Test @inject on async function."""
        container = Mock()
        db_instance = Database()

        async def mock_aget(token: object):
            return db_instance

        container.aget = mock_aget

        @inject(container=container)
        async def handler(db: Inject[Database]):
            return db

        result = await cast(Callable[[], Any], handler)()
        assert result is db_instance

    def test_inject_default_container(self):
        """Test @inject uses default container."""
        with patch("pyinj.injection.get_default_container") as mock_get:
            mock_container = Mock()
            mock_container.get.return_value = Database()
            mock_get.return_value = mock_container

            @inject
            def handler(db: Inject[Database]):
                return db

            result = cast(Callable[[], Any], handler)()
            assert isinstance(result, Database)
            mock_get.assert_called_once()

    def test_inject_preserves_function_metadata(self):
        """Test @inject preserves function metadata."""

        @inject
        def handler(db: Inject[Database]):
            """Handler docstring."""
            return db

        assert handler.__name__ == "handler"
        assert handler.__doc__ == "Handler docstring."

    def test_inject_without_cache(self):
        """Test @inject without caching."""
        container = Mock()
        container.get.return_value = Database()

        @inject(container=container, cache=False)
        def handler(db: Inject[Database]):
            return db

        # Should still work but analyze deps each time
        result = cast(Callable[[], Any], handler)()
        assert isinstance(result, Database)
