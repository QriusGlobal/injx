"""Type safety tests for Dependencies pattern - validates type checking catches errors."""

from typing import Any, Protocol

import pytest

from injx import Container, Dependencies, Token, inject
from injx.exceptions import ResolutionError


# Service protocols for type testing
class Database(Protocol):
    """Database service protocol."""

    def query(self, sql: str) -> list[dict[str, Any]]: ...


class Cache(Protocol):
    """Cache service protocol."""

    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...


class Logger(Protocol):
    """Logger service protocol."""

    def log(self, message: str) -> None: ...


class EmailService(Protocol):
    """Email service protocol."""

    def send(self, to: str, subject: str, body: str) -> bool: ...


class AuthService(Protocol):
    """Auth service protocol."""

    def validate(self, token: str) -> bool: ...


# Different protocol for type mismatch testing
class PaymentService(Protocol):
    """Payment service protocol."""

    def process(self, amount: float) -> str: ...


# Mock implementations
class MockDatabase:
    def query(self, sql: str) -> list[dict[str, Any]]:
        return [{"id": 1, "data": "test"}]


class MockCache:
    def get(self, key: str) -> Any:
        return None

    def set(self, key: str, value: Any) -> None:
        pass


class MockLogger:
    def log(self, message: str) -> None:
        pass


class MockEmailService:
    def send(self, to: str, subject: str, body: str) -> bool:
        return True


class MockPaymentService:
    def process(self, amount: float) -> str:
        return f"payment_{amount}"


# Incompatible implementation for testing
class IncompatibleService:
    """Service that doesn't match any protocol."""

    def do_something(self) -> None:
        pass


class TestDependenciesTypeSafety:
    """Test type safety aspects of Dependencies pattern."""

    def test_dependencies_missing_service_runtime_error(self):
        """Test that missing services cause runtime errors."""
        container = Container()
        container.register(Database, MockDatabase)
        # Cache not registered

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> None:
            # This should fail at runtime because Cache is not registered
            _ = deps[Database]  # This works
            _ = deps[Cache]  # This should fail

        with container.activate():
            with pytest.raises(ResolutionError):
                handler()

    def test_dependencies_wrong_type_access(self):
        """Test accessing wrong type from Dependencies."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> None:
            # Type checker should warn about this
            # Logger is not in Dependencies[Database, Cache]
            try:
                _ = deps[Logger]  # type: ignore
                pytest.fail("Should have raised KeyError")
            except KeyError as e:
                assert "Logger" in str(e)

        with container.activate():
            handler()

    def test_dependencies_protocol_satisfaction(self):
        """Test that implementations satisfy protocols."""
        container = Container()

        # These satisfy the protocols
        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> dict[str, Any]:
            db = deps[Database]
            cache = deps[Cache]

            # These methods exist per protocol
            result = db.query("SELECT 1")
            cache.set("key", result)
            cached = cache.get("key")

            return {"db_result": result, "cached": cached}

        with container.activate():
            result = handler()
            assert result["db_result"][0]["id"] == 1

    def test_dependencies_incompatible_service(self):
        """Test registering incompatible service."""
        container = Container()

        # This doesn't satisfy Database protocol
        container.register(Database, IncompatibleService)  # type: ignore

        @inject
        def handler(deps: Dependencies[Database]) -> None:
            db = deps[Database]
            # This will fail at runtime because IncompatibleService
            # doesn't have query method
            with pytest.raises(AttributeError):
                db.query("SELECT 1")  # type: ignore

        with container.activate():
            handler()

    def test_dependencies_type_variance(self):
        """Test type variance in Dependencies."""
        container = Container()

        # Base and derived types
        class BaseService:
            def base_method(self) -> str:
                return "base"

        class DerivedService(BaseService):
            def derived_method(self) -> str:
                return "derived"

        container.register(BaseService, DerivedService)

        @inject
        def handler(deps: Dependencies[BaseService]) -> str:
            service = deps[BaseService]
            # Should be able to call base method
            return service.base_method()

        with container.activate():
            result = handler()
            assert result == "base"

    def test_dependencies_generic_types(self):
        """Test Dependencies with generic types."""
        from typing import Generic, TypeVar

        T = TypeVar("T")

        class GenericService(Generic[T]):
            def __init__(self, value: T):
                self.value = value

            def get(self) -> T:
                return self.value

        # Use Token for generic types
        StringServiceToken = Token("str_service", GenericService[str])
        IntServiceToken = Token("int_service", GenericService[int])

        container = Container()
        container.register(StringServiceToken, lambda: GenericService("hello"))
        container.register(IntServiceToken, lambda: GenericService(42))

        # Test that tokens work with generic types
        with container.activate():
            str_service = container.get(StringServiceToken)
            int_service = container.get(IntServiceToken)

            # Verify the services work correctly
            assert str_service.get() == "hello"
            assert int_service.get() == 42

    def test_dependencies_optional_types(self):
        """Test Dependencies with Optional types."""
        from typing import Optional

        container = Container()
        container.register(Database, MockDatabase)
        # Cache intentionally not registered

        @inject
        def handler(deps: Dependencies[Database]) -> Optional[Cache]:
            db = deps[Database]
            assert db is not None

            # Try to get Cache (not in Dependencies declaration)
            cache = deps.get(Cache, None)  # type: ignore
            return cache

        with container.activate():
            result = handler()
            assert result is None

    def test_dependencies_union_types(self):
        """Test Dependencies behavior with Union types."""
        from typing import Union

        container = Container()
        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)

        # Service that could be one of multiple types
        DBOrCache = Union[Database, Cache]

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> str:
            # Can access both
            db: DBOrCache = deps[Database]
            cache: DBOrCache = deps[Cache]

            # Type checker should understand these
            if hasattr(db, "query"):
                db.query("SELECT 1")
            if hasattr(cache, "get"):
                cache.get("key")

            return "ok"

        with container.activate():
            result = handler()
            assert result == "ok"

    def test_dependencies_with_token_types(self):
        """Test type safety with Token-based registration."""
        container = Container()

        # Tokens with type information
        DB_TOKEN: Token[Database] = Token("db", Database)
        CACHE_TOKEN: Token[Cache] = Token("cache", Cache)

        container.register(DB_TOKEN, MockDatabase)
        container.register(CACHE_TOKEN, MockCache)

        # Map to types
        container.register(Database, lambda: container.get(DB_TOKEN))
        container.register(Cache, lambda: container.get(CACHE_TOKEN))

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> bool:
            db = deps[Database]
            cache = deps[Cache]

            # Type checker knows these are Database and Cache
            db.query("SELECT 1")
            cache.set("key", "value")

            return True

        with container.activate():
            result = handler()
            assert result is True

    def test_dependencies_literal_types(self):
        """Test Dependencies with Literal types for configuration."""
        from typing import Literal

        class ConfigService:
            def __init__(self, mode: Literal["dev", "prod"]):
                self.mode = mode

        container = Container()
        container.register(ConfigService, lambda: ConfigService("dev"))
        container.register(Database, MockDatabase)

        @inject
        def handler(deps: Dependencies[Database, ConfigService]) -> str:
            config = deps[ConfigService]
            db = deps[Database]

            # Type checker knows mode is Literal["dev", "prod"]
            if config.mode == "dev":
                db.query("SELECT * FROM debug_table")
            elif config.mode == "prod":
                db.query("SELECT * FROM users")
            # Type checker would warn about this:
            # elif config.mode == "test":  # Not in Literal

            return config.mode

        with container.activate():
            result = handler()
            assert result == "dev"

    def test_dependencies_callable_protocols(self):
        """Test Dependencies with callable protocols."""

        class ProcessorService(Protocol):
            def process(self, data: str) -> str: ...

        class ValidatorService(Protocol):
            def validate(self, data: str) -> bool: ...

        class MockProcessor:
            def process(self, data: str) -> str:
                return data.upper()

        class MockValidator:
            def validate(self, data: str) -> bool:
                return len(data) > 0

        container = Container()
        container.register(ProcessorService, MockProcessor)
        container.register(ValidatorService, MockValidator)

        @inject
        def handler(
            deps: Dependencies[ProcessorService, ValidatorService],
            data: str,
        ) -> str:
            processor = deps[ProcessorService]
            validator = deps[ValidatorService]

            if validator.validate(data):
                return processor.process(data)
            return ""

        with container.activate():
            result = handler("hello")
            assert result == "HELLO"

    def test_dependencies_type_errors_collection(self):
        """Test collection of type errors with Dependencies."""
        container = Container()
        container.register(Database, MockDatabase)

        type_errors = []

        @inject
        def handler(deps: Dependencies[Database]) -> None:
            db = deps[Database]

            # Correct usage
            db.query("SELECT 1")

            # Type errors (would be caught by type checker)
            try:
                db.nonexistent_method()  # type: ignore
            except AttributeError as e:
                type_errors.append(("method_not_found", str(e)))

            try:
                # Wrong argument type
                db.query(123)  # type: ignore
            except TypeError as e:
                type_errors.append(("wrong_arg_type", str(e)))

            try:
                # Accessing non-declared dependency
                _ = deps[EmailService]  # type: ignore
            except KeyError as e:
                type_errors.append(("missing_dependency", str(e)))

        with container.activate():
            handler()

        # Verify type errors were caught
        assert len(type_errors) >= 2
        assert any("nonexistent_method" in str(e) for _, e in type_errors)
        assert any("EmailService" in str(e) for _, e in type_errors)

    def test_dependencies_mypy_style_checks(self):
        """Test patterns that mypy/basedpyright would catch."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> dict[str, Any]:
            # These would pass type checking
            _db: Database = deps[Database]
            _cache: Cache = deps[Cache]

            # These would fail type checking (using type: ignore to run test)
            wrong_db: Cache = deps[Database]  # type: ignore
            wrong_cache: Database = deps[Cache]  # type: ignore

            # But at runtime, they still work (duck typing)
            results = []
            results.append(hasattr(wrong_db, "query"))  # True
            results.append(hasattr(wrong_cache, "get"))  # True

            return {"type_confusion": results}

        with container.activate():
            result = handler()
            # Runtime still works due to duck typing
            assert result["type_confusion"] == [True, True]
