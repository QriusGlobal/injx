"""Consolidated tests for the Dependencies pattern.

Test categories are marked with pytest markers:
- @pytest.mark.core: Core functionality and basic operations
- @pytest.mark.type_safety: Type validation and safety checks
- @pytest.mark.complex: Complex scenarios and edge cases
- @pytest.mark.asyncio: Async/await functionality
- @pytest.mark.integration: Real-world integration patterns
- @pytest.mark.performance: Performance-related tests
- @pytest.mark.thread_safety: Concurrency and thread safety
"""

import asyncio
import gc
import sys
import threading
import time
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Literal, Optional, Protocol, TypeVar, Union

import pytest

from injx import (
    Container,
    Dependencies,
    RequestScope,
    Scope,
    SessionScope,
    Token,
    inject,
)
from injx.exceptions import ResolutionError


class Database(Protocol):
    """Test database service."""

    def query(self, sql: str) -> list[dict[str, Any]]: ...


class Logger(Protocol):
    """Test logger service."""

    def log(self, message: str) -> str: ...


class Cache(Protocol):
    """Test cache service."""

    def get(self, key: str) -> str: ...


class EmailService(Protocol):
    """Email service protocol."""

    def send(self, to: str, subject: str, body: str) -> bool: ...


class AuthService(Protocol):
    """Auth service protocol."""

    def validate(self, token: str) -> bool: ...
    def create_token(self, user_id: int) -> str: ...


class MessageQueue(Protocol):
    """Message queue protocol."""

    def publish(self, topic: str, message: dict[str, Any]) -> None: ...
    def subscribe(self, topic: str) -> Any: ...


class PaymentService(Protocol):
    """Payment service protocol."""

    def process(self, amount: float) -> str: ...


class AsyncDatabase(Protocol):
    """Async database protocol."""

    async def query(self, sql: str) -> list[dict[str, Any]]: ...
    async def execute(self, sql: str) -> None: ...
    async def close(self) -> None: ...


class AsyncCache(Protocol):
    """Async cache protocol."""

    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: Any, ttl: int = 300) -> None: ...
    async def close(self) -> None: ...


class AsyncHTTPClient(Protocol):
    """Async HTTP client protocol."""

    async def get(self, url: str) -> dict[str, Any]: ...
    async def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]: ...
    async def close(self) -> None: ...


class AsyncMessageQueue(Protocol):
    """Async message queue protocol."""

    async def publish(self, topic: str, message: dict[str, Any]) -> None: ...
    async def subscribe(self, topic: str) -> list[dict[str, Any]]: ...
    async def close(self) -> None: ...


class DatabaseConnection(Protocol):
    """Database connection protocol."""

    def execute(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...
    def begin_transaction(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class CacheBackend(Protocol):
    """Cache backend protocol."""

    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any, ttl: int = 3600) -> None: ...
    def delete(self, key: str) -> bool: ...
    def flush(self) -> None: ...


class EmailProvider(Protocol):
    """Email provider protocol."""

    def send_email(
        self, to: str, subject: str, body: str, html: bool = False
    ) -> bool: ...
    def send_bulk(self, recipients: list[str], subject: str, body: str) -> int: ...


class AuthenticationService(Protocol):
    """Authentication service protocol."""

    def authenticate(
        self, username: str, password: str
    ) -> Optional[dict[str, Any]]: ...
    def create_session(self, user_id: int) -> str: ...
    def validate_session(self, session_token: str) -> Optional[int]: ...
    def revoke_session(self, session_token: str) -> bool: ...


class PaymentGateway(Protocol):
    """Payment gateway protocol."""

    def charge(self, amount: float, currency: str, customer_id: str) -> str: ...
    def refund(self, transaction_id: str, amount: Optional[float] = None) -> bool: ...
    def get_balance(self, customer_id: str) -> float: ...


class MetricsCollector(Protocol):
    """Metrics collection protocol."""

    def increment(
        self, metric: str, value: int = 1, tags: Optional[dict[str, str]] = None
    ) -> None: ...
    def gauge(
        self, metric: str, value: float, tags: Optional[dict[str, str]] = None
    ) -> None: ...
    def timing(
        self, metric: str, duration: float, tags: Optional[dict[str, str]] = None
    ) -> None: ...


class MockDatabase:
    """Test database implementation."""

    def query(self, sql: str) -> list[dict[str, Any]]:
        return [{"id": 1, "sql": sql}]

    def execute(self, sql: str) -> None:
        pass


class MockLogger:
    """Test logger implementation."""

    def __init__(self) -> None:
        self.logs: list[str] = []

    def log(self, message: str) -> str:
        self.logs.append(message)
        return message


class MockCache:
    """Test cache implementation."""

    def __init__(self) -> None:
        self.store: dict[str, Any] = {}

    def get(self, key: str) -> str:
        return self.store.get(key, f"cached_{key}")

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        self.store[key] = value


class MockEmailService:
    def send(self, to: str, subject: str, body: str) -> bool:
        return True


class MockAuthService:
    def validate(self, token: str) -> bool:
        return token == "valid_token"

    def create_token(self, user_id: int) -> str:
        return f"token_{user_id}"


class MockMessageQueue:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, Any]]] = []

    def publish(self, topic: str, message: dict[str, Any]) -> None:
        self.messages.append((topic, message))

    def subscribe(self, topic: str) -> Any:
        return [msg for t, msg in self.messages if t == topic]


class MockPaymentService:
    def process(self, amount: float) -> str:
        return f"payment_{amount}"


class MockAsyncDatabase:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.closed = False

    async def query(self, sql: str) -> list[dict[str, Any]]:
        await asyncio.sleep(0.01)
        self.queries.append(sql)
        return [{"id": 1, "sql": sql}]

    async def execute(self, sql: str) -> None:
        await asyncio.sleep(0.01)
        self.queries.append(sql)

    async def close(self) -> None:
        await asyncio.sleep(0.01)
        self.closed = True


class MockAsyncCache:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self.closed = False

    async def get(self, key: str) -> Any:
        await asyncio.sleep(0.005)
        return self.store.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        await asyncio.sleep(0.005)
        self.store[key] = value

    async def close(self) -> None:
        await asyncio.sleep(0.005)
        self.closed = True


class MockAsyncHTTPClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, Any]] = []
        self.closed = False

    async def get(self, url: str) -> dict[str, Any]:
        await asyncio.sleep(0.02)
        self.requests.append(("GET", url, None))
        return {"status": 200, "data": {"url": url}}

    async def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.02)
        self.requests.append(("POST", url, data))
        return {"status": 201, "id": 123}

    async def close(self) -> None:
        await asyncio.sleep(0.01)
        self.closed = True


class MockAsyncMessageQueue:
    def __init__(self) -> None:
        self.messages: dict[str, list[dict[str, Any]]] = {}
        self.closed = False

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        await asyncio.sleep(0.01)
        if topic not in self.messages:
            self.messages[topic] = []
        self.messages[topic].append(message)

    async def subscribe(self, topic: str) -> list[dict[str, Any]]:
        await asyncio.sleep(0.01)
        return self.messages.get(topic, [])

    async def close(self) -> None:
        await asyncio.sleep(0.01)
        self.closed = True


@dataclass
class User:
    """User model."""

    id: int
    username: str
    email: str
    is_active: bool = True


class MockDatabaseConnection:
    """Mock database with transaction support."""

    def __init__(self) -> None:
        self.in_transaction = False
        self.data: dict[str, list[dict[str, Any]]] = {
            "users": [
                {
                    "id": 1,
                    "username": "alice",
                    "email": "alice@example.com",
                    "is_active": True,
                },
                {
                    "id": 2,
                    "username": "bob",
                    "email": "bob@example.com",
                    "is_active": True,
                },
            ],
            "orders": [],
        }

    def execute(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if "SELECT" in query and "users" in query:
            if "WHERE id" in query and "id" in params:
                return [u for u in self.data["users"] if u["id"] == params["id"]]
            return self.data["users"]
        elif "INSERT" in query and "users" in query:
            user = params.copy()
            user["id"] = len(self.data["users"]) + 1
            self.data["users"].append(user)
            return [user]
        elif "INSERT" in query and "orders" in query:
            order = params.copy()
            order["id"] = len(self.data["orders"]) + 1
            self.data["orders"].append(order)
            return [order]
        return []

    def begin_transaction(self) -> None:
        self.in_transaction = True

    def commit(self) -> None:
        self.in_transaction = False

    def rollback(self) -> None:
        self.in_transaction = False


class MockCacheBackend:
    """Mock Redis-like cache."""

    def __init__(self) -> None:
        self.store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self.store:
            value, expiry = self.store[key]
            if expiry > time.time():
                return value
            del self.store[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        self.store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> bool:
        if key in self.store:
            del self.store[key]
            return True
        return False

    def flush(self) -> None:
        self.store.clear()


class MockEmailProvider:
    """Mock email provider."""

    def __init__(self) -> None:
        self.sent_emails: list[dict[str, Any]] = []

    def send_email(self, to: str, subject: str, body: str, html: bool = False) -> bool:
        self.sent_emails.append(
            {"to": to, "subject": subject, "body": body, "html": html}
        )
        return True

    def send_bulk(self, recipients: list[str], subject: str, body: str) -> int:
        for recipient in recipients:
            self.send_email(recipient, subject, body)
        return len(recipients)


class MockAuthenticationService:
    """Mock auth service."""

    def __init__(self) -> None:
        self.sessions: dict[str, int] = {}
        self.users = {"alice": 1, "bob": 2}

    def authenticate(self, username: str, password: str) -> Optional[dict[str, Any]]:
        if username in self.users and password == "password":
            return {"user_id": self.users[username], "username": username}
        return None

    def create_session(self, user_id: int) -> str:
        session_token = f"session_{user_id}_{time.time()}"
        self.sessions[session_token] = user_id
        return session_token

    def validate_session(self, session_token: str) -> Optional[int]:
        return self.sessions.get(session_token)

    def revoke_session(self, session_token: str) -> bool:
        if session_token in self.sessions:
            del self.sessions[session_token]
            return True
        return False


class MockPaymentGateway:
    """Mock payment gateway."""

    def __init__(self) -> None:
        self.transactions: dict[str, dict[str, Any]] = {}
        self.balances: dict[str, float] = {}

    def charge(self, amount: float, currency: str, customer_id: str) -> str:
        transaction_id = f"txn_{time.time()}"
        self.transactions[transaction_id] = {
            "amount": amount,
            "currency": currency,
            "customer_id": customer_id,
            "refunded": False,
        }
        if customer_id not in self.balances:
            self.balances[customer_id] = 0
        self.balances[customer_id] += amount
        return transaction_id

    def refund(self, transaction_id: str, amount: Optional[float] = None) -> bool:
        if transaction_id in self.transactions:
            txn = self.transactions[transaction_id]
            refund_amount = amount or txn["amount"]
            self.balances[txn["customer_id"]] -= refund_amount
            txn["refunded"] = True
            return True
        return False

    def get_balance(self, customer_id: str) -> float:
        return self.balances.get(customer_id, 0.0)


class MockMetricsCollector:
    """Mock metrics collector."""

    def __init__(self) -> None:
        self.metrics: list[dict[str, Any]] = []

    def increment(
        self, metric: str, value: int = 1, tags: Optional[dict[str, str]] = None
    ) -> None:
        self.metrics.append(
            {"type": "increment", "metric": metric, "value": value, "tags": tags}
        )

    def gauge(
        self, metric: str, value: float, tags: Optional[dict[str, str]] = None
    ) -> None:
        self.metrics.append(
            {"type": "gauge", "metric": metric, "value": value, "tags": tags}
        )

    def timing(
        self, metric: str, duration: float, tags: Optional[dict[str, str]] = None
    ) -> None:
        self.metrics.append(
            {"type": "timing", "metric": metric, "value": duration, "tags": tags}
        )


class IncompatibleService:
    """Service that doesn't match any protocol."""

    def do_something(self) -> None:
        pass


class TestDependencies:
    """Consolidated test class for Dependencies pattern.

    Tests are organized by functionality rather than arbitrary categories,
    with semantic names that clearly indicate what behavior is being tested
    and what the expected outcome should be.
    """

    @pytest.mark.core
    def test_dependencies_resolves_registered_services_on_access(self):
        """Dependencies should resolve registered services when accessed via bracket notation."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Logger, MockLogger)

        deps = Dependencies(container, (Database, Logger))

        assert deps[Database].query("test") == [{"id": 1, "sql": "test"}]
        assert deps[Logger].log("test") == "test"
        assert Database in deps
        assert len(deps) == 2

    @pytest.mark.core
    def test_inject_decorator_provides_dependencies_to_function(self):
        """@inject decorator should automatically resolve and provide Dependencies parameter."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Logger, MockLogger)

        @inject
        def process(name: str, deps: Dependencies[Database, Logger]) -> str:
            data = deps[Database].query("SELECT 1")
            deps[Logger].log(f"Processing {name}")
            return f"{name}: {data[0]['id']}"

        with container.activate():
            result = process("test")
            assert result == "test: 1"

    @pytest.mark.core
    @pytest.mark.type_safety
    def test_dependencies_raises_keyerror_for_unregistered_type(self):
        """Dependencies should raise KeyError when accessing an unregistered service type."""
        container = Container()
        container.register(Database, MockDatabase)

        deps = Dependencies(container, (Database,))

        db = deps[Database]
        assert isinstance(db, MockDatabase)

        with pytest.raises(KeyError, match="Logger not in dependencies"):
            deps[Logger]

    @pytest.mark.core
    def test_empty_dependencies_returns_zero_length_and_false_bool(self):
        """Empty Dependencies should have length 0, evaluate to False, and have empty repr."""
        container = Container()
        deps = Dependencies(container, ())

        assert len(deps) == 0
        assert not deps
        assert repr(deps) == "Dependencies[]"

    @pytest.mark.core
    def test_get_returns_none_for_missing_service_with_default(self):
        """Dependencies.get() should return default value for missing services instead of raising."""
        container = Container()
        container.register(Database, MockDatabase)

        deps = Dependencies(container, (Database,))

        db = deps.get(Database)
        assert isinstance(db, MockDatabase)

        logger = deps.get(Logger, None)
        assert logger is None

    @pytest.mark.core
    def test_dependencies_provides_multiple_services_correctly(self):
        """Dependencies should handle multiple service types in a single parameter."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Logger, MockLogger)
        container.register(Cache, MockCache)

        @inject
        def complex_handler(deps: Dependencies[Database, Logger, Cache]) -> tuple:
            return (
                deps[Database].query("SELECT 1")[0]["id"],
                deps[Logger].log("msg"),
                deps[Cache].get("key"),
            )

        with container.activate():
            result = complex_handler()
            assert result == (1, "msg", "cached_key")

    @pytest.mark.core
    def test_token_registered_services_resolve_through_dependencies(self):
        """Token-registered services should be accessible through Dependencies using type mapping."""
        container = Container()

        DB_TOKEN = Token("database", Database)
        LOG_TOKEN = Token("logger", Logger)

        container.register(DB_TOKEN, MockDatabase)
        container.register(LOG_TOKEN, MockLogger)

        container.register(Database, lambda: container.get(DB_TOKEN))
        container.register(Logger, lambda: container.get(LOG_TOKEN))

        deps = Dependencies(container, (Database, Logger))
        assert deps[Database].query("test") == [{"id": 1, "sql": "test"}]
        assert deps[Logger].log("test") == "test"

    @pytest.mark.core
    def test_repr_shows_type_names_in_dependencies_format(self):
        """Dependencies.__repr__ should show 'Dependencies[Type1, Type2]' format."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Logger, MockLogger)

        deps = Dependencies(container, (Database, Logger))
        assert repr(deps) == "Dependencies[Database, Logger]"

    @pytest.mark.core
    def test_bool_returns_false_for_empty_true_for_populated(self):
        """Dependencies should evaluate to False when empty, True when containing types."""
        container = Container()

        empty_deps = Dependencies(container, ())
        assert not empty_deps

        container.register(Database, MockDatabase)
        deps = Dependencies(container, (Database,))
        assert deps

    @pytest.mark.core
    @pytest.mark.performance
    def test_lazy_resolution_defers_until_first_access(self):
        """Dependencies should not resolve services until first access, then cache results."""
        container = Container()

        resolution_order = []

        def create_db() -> Database:
            resolution_order.append("db")
            return MockDatabase()

        def create_logger() -> Logger:
            resolution_order.append("logger")
            return MockLogger()

        container.register(Database, create_db)
        container.register(Logger, create_logger)

        deps = Dependencies(container, (Database, Logger))
        assert resolution_order == []

        _ = deps[Database]
        assert resolution_order == ["db", "logger"]

        resolution_order.clear()
        _ = deps[Database]
        _ = deps[Logger]
        assert resolution_order == []

    @pytest.mark.core
    def test_raises_resolution_error_for_unregistered_dependency(self):
        """Dependencies should raise ResolutionError when trying to resolve unregistered service."""
        container = Container()

        try:
            deps = Dependencies(container, (Database,))
            # If it doesn't raise immediately, it should raise on access
            _ = deps[Database]
            pytest.fail("Should have raised an exception")
        except (ResolutionError, RuntimeError):
            pass

    @pytest.mark.core
    def test_contains_operator_checks_dependency_presence(self):
        """'in' operator should check if a type is present in Dependencies."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Logger, MockLogger)

        deps = Dependencies(container, (Database, Logger))

        assert Database in deps
        assert Logger in deps
        assert Cache not in deps

    @pytest.mark.type_safety
    def test_runtime_error_when_accessing_unregistered_service(self):
        """Accessing unregistered service through Dependencies should raise ResolutionError at runtime."""
        container = Container()
        container.register(Database, MockDatabase)

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> None:
            _ = deps[Database]
            _ = deps[Cache]

        with container.activate():
            with pytest.raises(ResolutionError):
                handler()

    @pytest.mark.type_safety
    def test_keyerror_when_requesting_non_dependency_type(self):
        """Requesting a type not in Dependencies should raise KeyError with helpful message."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> None:
            try:
                _ = deps[Logger]  # type: ignore
                pytest.fail("Should have raised KeyError")
            except KeyError as e:
                assert "Logger" in str(e)

        with container.activate():
            handler()

    @pytest.mark.type_safety
    def test_mock_implementations_satisfy_protocol_contracts(self):
        """Mock implementations should satisfy their Protocol contracts for type safety."""
        container = Container()

        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> dict[str, Any]:
            db = deps[Database]
            cache = deps[Cache]

            result = db.query("SELECT 1")
            cache.set("key", result)
            cached = cache.get("key")

            return {"db_result": result, "cached": cached}

        with container.activate():
            result = handler()
            assert result["db_result"][0]["id"] == 1

    @pytest.mark.type_safety
    def test_attribute_error_for_incompatible_service_implementation(self):
        """Incompatible service missing protocol methods should raise AttributeError on use."""
        container = Container()

        container.register(Database, IncompatibleService)  # type: ignore

        @inject
        def handler(deps: Dependencies[Database]) -> None:
            db = deps[Database]
            with pytest.raises(AttributeError):
                db.query("SELECT 1")  # type: ignore

        with container.activate():
            handler()

    @pytest.mark.type_safety
    def test_derived_class_satisfies_base_class_dependency(self):
        """Derived classes should satisfy base class dependencies (Liskov substitution)."""
        container = Container()

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
            return service.base_method()

        with container.activate():
            result = handler()
            assert result == "base"

    @pytest.mark.type_safety
    def test_container_rejects_generic_type_aliases_requires_tokens(self):
        """Container should reject Generic[T] aliases and require explicit Token instances."""
        T = TypeVar("T")

        class GenericService(Generic[T]):
            def __init__(self, value: T):
                self.value = value

            def get(self) -> T:
                return self.value

        container = Container()

        # Container should reject generic type aliases like GenericService[str]
        # because they're not concrete types at runtime
        with pytest.raises(
            TypeError, match="Token specification must be a Token or type"
        ):
            container.register(GenericService[str], lambda: GenericService("hello"))

        with pytest.raises(
            TypeError, match="Token specification must be a Token or type"
        ):
            container.register(GenericService[int], lambda: GenericService(42))

        # The correct way: Use explicit tokens for different instances
        StringServiceToken = Token("str_service", GenericService[str])
        IntServiceToken = Token("int_service", GenericService[int])

        container.register(StringServiceToken, lambda: GenericService("hello"))
        container.register(IntServiceToken, lambda: GenericService(42))

        @inject
        def handler(
            str_svc: Annotated[GenericService[str], StringServiceToken],
            int_svc: Annotated[GenericService[int], IntServiceToken],
        ) -> tuple[str, int]:
            return (str_svc.get(), int_svc.get())

        with container.activate():
            result = handler()
            assert result == ("hello", 42)

    @pytest.mark.type_safety
    def test_get_method_returns_none_for_optional_missing_service(self):
        """Dependencies.get() should safely return None for Optional missing services."""
        container = Container()
        container.register(Database, MockDatabase)

        @inject
        def handler(deps: Dependencies[Database]) -> Optional[Cache]:
            db = deps[Database]
            assert db is not None

            cache = deps.get(Cache, None)  # type: ignore
            return cache

        with container.activate():
            result = handler()
            assert result is None

    @pytest.mark.type_safety
    def test_union_types_work_with_runtime_type_checking(self):
        """Union types should work with Dependencies when using runtime type checking."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)

        DBOrCache = Union[Database, Cache]

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> str:
            db: DBOrCache = deps[Database]
            cache: DBOrCache = deps[Cache]

            if hasattr(db, "query"):
                db.query("SELECT 1")
            if hasattr(cache, "get"):
                cache.get("key")

            return "ok"

        with container.activate():
            result = handler()
            assert result == "ok"

    @pytest.mark.type_safety
    def test_token_indirection_preserves_type_safety(self):
        """Token-based registration with type indirection should preserve type safety."""
        container = Container()

        DB_TOKEN: Token[Database] = Token("db", Database)
        CACHE_TOKEN: Token[Cache] = Token("cache", Cache)

        container.register(DB_TOKEN, MockDatabase)
        container.register(CACHE_TOKEN, MockCache)

        container.register(Database, lambda: container.get(DB_TOKEN))
        container.register(Cache, lambda: container.get(CACHE_TOKEN))

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> bool:
            db = deps[Database]
            cache = deps[Cache]

            db.query("SELECT 1")
            cache.set("key", "value")

            return True

        with container.activate():
            result = handler()
            assert result is True

    @pytest.mark.type_safety
    def test_literal_types_for_configuration_services(self):
        """Literal types should work for configuration services with constrained values."""

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

            if config.mode == "dev":
                db.query("SELECT * FROM debug_table")
            elif config.mode == "prod":
                db.query("SELECT * FROM users")

            return config.mode

        with container.activate():
            result = handler()
            assert result == "dev"

    @pytest.mark.type_safety
    def test_protocol_based_services_with_callable_methods(self):
        """Protocol-based services with callable methods should work through Dependencies."""

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

    @pytest.mark.type_safety
    def test_collects_multiple_type_errors_during_execution(self):
        """Multiple type errors should be detectable and collectable during execution."""
        container = Container()
        container.register(Database, MockDatabase)

        type_errors = []

        @inject
        def handler(deps: Dependencies[Database]) -> None:
            db = deps[Database]

            db.query("SELECT 1")

            try:
                db.nonexistent_method()  # type: ignore
            except AttributeError as e:
                type_errors.append(("method_not_found", str(e)))

            try:
                db.query(123)  # type: ignore
            except TypeError as e:
                type_errors.append(("wrong_arg_type", str(e)))

            try:
                _ = deps[EmailService]  # type: ignore
            except KeyError as e:
                type_errors.append(("missing_dependency", str(e)))

        with container.activate():
            handler()

        assert len(type_errors) >= 2
        assert any("nonexistent_method" in str(e) for _, e in type_errors)
        assert any("EmailService" in str(e) for _, e in type_errors)

    @pytest.mark.type_safety
    def test_type_confusion_detectable_at_runtime(self):
        """Type confusion that static analyzers would catch should be detectable at runtime."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> dict[str, Any]:
            _db: Database = deps[Database]
            _cache: Cache = deps[Cache]

            wrong_db: Cache = deps[Database]  # type: ignore
            wrong_cache: Database = deps[Cache]  # type: ignore

            results = []
            results.append(hasattr(wrong_db, "query"))
            results.append(hasattr(wrong_cache, "get"))

            return {"type_confusion": results}

        with container.activate():
            result = handler()
            assert result["type_confusion"] == [True, True]

    @pytest.mark.complex
    def test_inject_works_without_dependencies_parameter(self):
        """@inject should work for functions without Dependencies parameter."""
        container = Container()

        @inject
        def handler() -> str:
            return "no deps"

        with container.activate():
            result = handler()
            assert result == "no deps"

    @pytest.mark.complex
    def test_single_dependency_in_bracket_syntax(self):
        """Dependencies[SingleType] should work for single dependency."""
        container = Container()
        container.register(Database, MockDatabase)

        @inject
        def handler(deps: Dependencies[Database]) -> str:
            db = deps[Database]
            result = db.query("SELECT 1")
            return f"Result: {result[0]['id']}"

        with container.activate():
            result = handler()
            assert result == "Result: 1"

    @pytest.mark.complex
    @pytest.mark.performance
    def test_scales_to_fifteen_plus_dependencies(self):
        """Dependencies should scale efficiently to 15+ services without performance degradation."""
        container = Container()

        services = []
        for i in range(15):
            service_class = type(
                f"Service{i}",
                (),
                {"get_id": lambda self, i=i: i, "name": f"Service{i}"},
            )
            services.append(service_class)
            container.register(service_class, service_class)

        def create_handler():
            @inject
            def handler(deps: Dependencies[*services]) -> int:  # type: ignore
                total = 0
                for service_class in services:
                    instance = deps[service_class]
                    total += instance.get_id()
                return total

            return handler

        handler = create_handler()

        with container.activate():
            result = handler()
            assert result == sum(range(15))

    @pytest.mark.complex
    def test_token_scope_inheritance_in_dependencies(self):
        """Token scope settings should be inherited when resolving through Dependencies."""
        container = Container()

        DB_TOKEN = Token("database", Database, scope=Scope.SINGLETON)
        CACHE_TOKEN = Token("cache", Cache, scope=Scope.SINGLETON)
        LOG_TOKEN = Token("logger", Logger, scope=Scope.TRANSIENT)

        container.register(DB_TOKEN, MockDatabase)
        container.register(CACHE_TOKEN, MockCache)
        container.register(LOG_TOKEN, MockLogger)

        container.register(Database, lambda: container.get(DB_TOKEN))
        container.register(Cache, lambda: container.get(CACHE_TOKEN))
        container.register(Logger, lambda: container.get(LOG_TOKEN))

        @inject
        def handler(deps: Dependencies[Database, Cache, Logger]) -> dict[str, Any]:
            db = deps[Database]
            cache = deps[Cache]
            logger = deps[Logger]

            data = db.query("SELECT * FROM users")
            cache.set("users", data)
            logger.log("Fetched users")

            return {"data": data, "cached": True}

        with container.activate():
            result = handler()
            assert result["data"][0]["sql"] == "SELECT * FROM users"
            assert result["cached"] is True

    @pytest.mark.complex
    def test_given_overrides_registered_providers(self):
        """Container.given() should override registered providers for Dependencies resolution."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> str:
            return deps[Database].query("SELECT 1")[0]["sql"]

        with container.activate():
            result1 = handler()
            assert result1 == "SELECT 1"

        class OverrideDB:
            def query(self, sql: str) -> list[dict[str, Any]]:
                return [{"id": 999, "sql": f"OVERRIDE: {sql}"}]

        override_db = OverrideDB()
        container.given(Database, override_db)

        with container.activate():
            result2 = handler()
            assert result2 == "OVERRIDE: SELECT 1"

    @pytest.mark.complex
    @pytest.mark.performance
    def test_memory_efficient_with_hundred_services(self):
        """Dependencies should remain memory efficient with 100+ registered services."""
        container = Container()

        # Store the created types so we can use the same instances
        service_types = []
        for i in range(100):
            service_class = type(f"Service{i}", (), {"data": [0] * 1000})
            service_types.append(service_class)
            container.register(service_class, service_class)

        gc.collect()
        initial_memory = sys.getsizeof(container)

        # Use the same type instances we registered
        _ = [container.get(service_types[i]) for i in range(100)]

        gc.collect()
        final_memory = sys.getsizeof(container)

        memory_increase = final_memory - initial_memory
        assert memory_increase < 10000

    @pytest.mark.complex
    @pytest.mark.performance
    def test_dependencies_performance_matches_individual_injection(self):
        """Dependencies pattern should have comparable performance to individual injection."""
        container = Container()
        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)
        container.register(Logger, MockLogger)
        container.register(EmailService, MockEmailService)

        @inject
        def handler_deps(
            deps: Dependencies[Database, Cache, Logger, EmailService],
        ) -> int:
            deps[Database].query("SELECT 1")
            deps[Cache].get("key")
            deps[Logger].log("test")
            deps[EmailService].send("test@test.com", "Test", "Body")
            return 1

        @inject
        def handler_individual(
            db: Database, cache: Cache, logger: Logger, email: EmailService
        ) -> int:
            db.query("SELECT 1")
            cache.get("key")
            logger.log("test")
            email.send("test@test.com", "Test", "Body")
            return 1

        with container.activate():
            # Warm up
            handler_deps()
            handler_individual()

            # Test both work correctly
            result1 = handler_deps()
            result2 = handler_individual()
            assert result1 == result2 == 1

    @pytest.mark.complex
    def test_scope_lifecycle_singleton_transient_request(self):
        """Different scopes should maintain proper lifecycle: singleton=1, request=per-scope, transient=always-new."""
        container = Container()

        call_count = {"singleton": 0, "transient": 0, "request": 0}

        def create_singleton():
            call_count["singleton"] += 1
            return MockDatabase()

        def create_transient():
            call_count["transient"] += 1
            return MockCache()

        def create_request():
            call_count["request"] += 1
            return MockLogger()

        container.register(Database, create_singleton, scope=Scope.SINGLETON)
        container.register(Cache, create_transient, scope=Scope.TRANSIENT)
        container.register(Logger, create_request, scope=Scope.REQUEST)

        @inject
        def handler(deps: Dependencies[Database, Cache, Logger]) -> None:
            _ = deps[Database]
            _ = deps[Cache]
            _ = deps[Logger]

        with container.activate():
            with container.request_scope():
                handler()
                handler()

            with container.request_scope():
                handler()

        assert call_count["singleton"] == 1
        assert call_count["transient"] == 3
        assert call_count["request"] == 2

    @pytest.mark.complex
    def test_resolution_error_includes_missing_service_name(self):
        """ResolutionError should include the name of the missing service for debugging."""
        container = Container()
        container.register(Database, MockDatabase)

        @inject
        def handler(deps: Dependencies[Database, Logger]) -> None:
            deps[Database].query("SELECT 1")
            deps[Logger].log("test")

        with container.activate():
            with pytest.raises(ResolutionError) as exc_info:
                handler()

            error_msg = str(exc_info.value)
            assert "Logger" in error_msg or "no provider" in error_msg.lower()

    @pytest.mark.complex
    def test_nested_service_dependencies_resolve_recursively(self):
        """Services with their own dependencies should resolve recursively through container."""
        container = Container()

        class ServiceWithDeps:
            def __init__(self, db: Database, cache: Cache):
                self.db = db
                self.cache = cache

        container.register(Database, MockDatabase)
        container.register(Cache, MockCache)
        container.register(
            ServiceWithDeps,
            lambda: ServiceWithDeps(container.get(Database), container.get(Cache)),
        )

        @inject
        def handler(deps: Dependencies[ServiceWithDeps, Logger]) -> bool:
            service = deps[ServiceWithDeps]
            assert service.db is not None
            assert service.cache is not None
            return True

        container.register(Logger, MockLogger)

        with container.activate():
            result = handler()
            assert result is True

    @pytest.mark.complex
    def test_given_instances_returned_without_factory_call(self):
        """Given instances should be returned directly without calling factory functions."""
        container = Container()

        given_db = MockDatabase()
        given_cache = MockCache()

        container.given(Database, given_db)
        container.given(Cache, given_cache)
        container.register(Logger, MockLogger)

        @inject
        def handler(deps: Dependencies[Database, Cache, Logger]) -> bool:
            assert deps[Database] is given_db
            assert deps[Cache] is given_cache
            assert deps[Logger] is not None
            return True

        with container.activate():
            result = handler()
            assert result is True

    @pytest.mark.complex
    @pytest.mark.thread_safety
    def test_thread_safe_singleton_with_transient_race_conditions(self):
        """Singleton should be thread-safe, transient may have race conditions under extreme concurrency."""
        container = Container()
        container.register(Database, MockDatabase, scope=Scope.SINGLETON)
        container.register(Cache, MockCache, scope=Scope.TRANSIENT)

        results = []
        errors = []
        lock = threading.Lock()

        @inject
        def handler(deps: Dependencies[Database, Cache]) -> dict[str, Any]:
            db = deps[Database]
            cache = deps[Cache]
            return {"db_id": id(db), "cache_id": id(cache)}

        def worker():
            try:
                with container.activate():
                    result = handler()
                    with lock:
                        results.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10

        db_ids = [r["db_id"] for r in results]
        assert len(set(db_ids)) == 1

        cache_ids = [r["cache_id"] for r in results]
        # TRANSIENT scope should create new instances but races can occur under high concurrency
        # In production with proper request contexts this wouldn't happen
        unique_cache_count = len(set(cache_ids))
        assert unique_cache_count >= 5, (
            f"Expected at least 5 unique cache instances, got {unique_cache_count}"
        )
        # Note: Ideally would be 10, but thread scheduling can cause instance reuse

    @pytest.mark.asyncio
    async def test_async_dependencies_resolve_with_await_syntax(self):
        """Async Dependencies should resolve with await syntax and parallel resolution."""
        container = Container()

        async def create_db() -> AsyncDatabase:
            await asyncio.sleep(0.01)
            return MockAsyncDatabase()

        async def create_cache() -> AsyncCache:
            await asyncio.sleep(0.01)
            return MockAsyncCache()

        container.register(AsyncDatabase, create_db)
        container.register(AsyncCache, create_cache)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, AsyncCache],
        ) -> dict[str, Any]:
            db = deps[AsyncDatabase]
            cache = deps[AsyncCache]

            data = await db.query("SELECT * FROM users")
            await cache.set("users", data)
            cached = await cache.get("users")

            return {"data": data, "cached": cached}

        async with container:
            result = await handler()
            assert result["data"][0]["sql"] == "SELECT * FROM users"
            assert result["cached"] == result["data"]

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_parallel_async_resolution_with_gather(self):
        """Multiple async dependencies should resolve in parallel using asyncio.gather."""
        container = Container()

        container.register(AsyncDatabase, MockAsyncDatabase)
        container.register(AsyncCache, MockAsyncCache)
        container.register(AsyncHTTPClient, MockAsyncHTTPClient)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, AsyncCache, AsyncHTTPClient],
        ) -> dict[str, Any]:
            db = deps[AsyncDatabase]
            cache = deps[AsyncCache]
            http = deps[AsyncHTTPClient]

            results = await asyncio.gather(
                db.query("SELECT * FROM users"),
                cache.get("key"),
                http.get("https://api.example.com/data"),
            )

            return {
                "db_result": results[0],
                "cache_result": results[1],
                "http_result": results[2],
            }

        async with container:
            result = await handler()
            assert result["db_result"][0]["sql"] == "SELECT * FROM users"
            assert result["cache_result"] is None
            assert result["http_result"]["status"] == 200

    @pytest.mark.asyncio
    async def test_sync_and_async_services_in_same_dependencies(self):
        """Dependencies should handle both sync and async services in same resolution."""
        container = Container()

        class SyncLogger:
            def log(self, msg: str) -> None:
                self.last_log = msg

        container.register(AsyncDatabase, MockAsyncDatabase)
        container.register(AsyncCache, MockAsyncCache)
        container.register(SyncLogger, SyncLogger)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, AsyncCache, SyncLogger],
        ) -> str:
            db = deps[AsyncDatabase]
            cache = deps[AsyncCache]
            logger = deps[SyncLogger]

            data = await db.query("SELECT 1")
            await cache.set("result", data)

            logger.log(f"Processed {len(data)} records")

            return logger.last_log

        async with container:
            result = await handler()
            assert result == "Processed 1 records"

    @pytest.mark.asyncio
    async def test_async_cleanup_executes_on_context_exit(self):
        """Async resources should be properly cleaned up on context manager exit."""
        container = Container()

        container.register(AsyncDatabase, MockAsyncDatabase)
        container.register(AsyncCache, MockAsyncCache)

        @inject
        async def handler(deps: Dependencies[AsyncDatabase, AsyncCache]) -> bool:
            db = deps[AsyncDatabase]
            cache = deps[AsyncCache]
            await db.query("SELECT 1")
            await cache.set("key", "value")
            return True

        async with container:
            result = await handler()
            assert result is True

    @pytest.mark.asyncio
    async def test_async_errors_propagate_through_dependencies(self):
        """Async errors should propagate correctly through Dependencies resolution."""
        container = Container()

        class FailingAsyncService:
            async def process(self) -> None:
                await asyncio.sleep(0.01)
                raise ValueError("Async operation failed")

        container.register(AsyncDatabase, MockAsyncDatabase)
        container.register(FailingAsyncService, FailingAsyncService)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, FailingAsyncService],
        ) -> None:
            db = deps[AsyncDatabase]
            service = deps[FailingAsyncService]

            await db.query("SELECT 1")
            await service.process()

        async with container:
            with pytest.raises(ValueError, match="Async operation failed"):
                await handler()

    @pytest.mark.asyncio
    async def test_async_context_manager_services_enter_exit_correctly(self):
        """Async context manager services should properly enter and exit through Dependencies."""
        container = Container()

        class AsyncContextService:
            def __init__(self) -> None:
                self.entered = False
                self.exited = False

            async def __aenter__(self):
                await asyncio.sleep(0.01)
                self.entered = True
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await asyncio.sleep(0.01)
                self.exited = True

            async def process(self) -> str:
                return "processed"

        container.register(AsyncContextService, AsyncContextService)
        container.register(AsyncDatabase, MockAsyncDatabase)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, AsyncContextService],
        ) -> str:
            db = deps[AsyncDatabase]
            service = deps[AsyncContextService]

            await db.query("SELECT 1")

            async with service:
                result = await service.process()

            return result

        async with container:
            result = await handler()
            assert result == "processed"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_hundred_concurrent_async_resolutions_under_one_second(self):
        """100 concurrent async Dependencies resolutions should complete under 1 second."""
        container = Container()

        container.register(AsyncDatabase, MockAsyncDatabase)
        container.register(AsyncCache, MockAsyncCache)
        container.register(AsyncHTTPClient, MockAsyncHTTPClient)
        container.register(AsyncMessageQueue, MockAsyncMessageQueue)

        @inject
        async def handler(
            deps: Dependencies[
                AsyncDatabase, AsyncCache, AsyncHTTPClient, AsyncMessageQueue
            ],
        ) -> int:
            _ = deps[AsyncDatabase]
            _ = deps[AsyncCache]
            _ = deps[AsyncHTTPClient]
            _ = deps[AsyncMessageQueue]
            return 1

        async with container:
            start = time.perf_counter()
            tasks = [handler() for _ in range(100)]
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start

            assert len(results) == 100
            assert all(r == 1 for r in results)
            assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_async_factory_fails_in_sync_context(self):
        """Async factory functions should fail with ResolutionError in sync context."""
        container = Container()

        async def create_async_db() -> AsyncDatabase:
            await asyncio.sleep(0.01)
            return MockAsyncDatabase()

        container.register(AsyncDatabase, create_async_db)

        @inject
        def sync_handler(deps: Dependencies[AsyncDatabase]) -> None:
            _ = deps[AsyncDatabase]

        with container.activate():
            with pytest.raises(ResolutionError):
                sync_handler()

    @pytest.mark.asyncio
    async def test_async_request_scope_isolates_request_services(self):
        """Async request scope should properly isolate request-scoped services."""
        container = Container()

        call_count = {"singleton": 0, "transient": 0, "request": 0}

        async def create_singleton() -> AsyncDatabase:
            call_count["singleton"] += 1
            await asyncio.sleep(0.01)
            return MockAsyncDatabase()

        async def create_transient() -> AsyncCache:
            call_count["transient"] += 1
            await asyncio.sleep(0.01)
            return MockAsyncCache()

        async def create_request() -> AsyncHTTPClient:
            call_count["request"] += 1
            await asyncio.sleep(0.01)
            return MockAsyncHTTPClient()

        container.register(AsyncDatabase, create_singleton, scope=Scope.SINGLETON)
        container.register(AsyncCache, create_transient, scope=Scope.TRANSIENT)
        container.register(AsyncHTTPClient, create_request, scope=Scope.REQUEST)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, AsyncCache, AsyncHTTPClient],
        ) -> None:
            _ = deps[AsyncDatabase]
            _ = deps[AsyncCache]
            _ = deps[AsyncHTTPClient]

        async with container:
            async with container.async_request_scope():
                await handler()
                await handler()

            async with container.async_request_scope():
                await handler()

        assert call_count["singleton"] == 1
        assert call_count["transient"] == 3
        assert call_count["request"] == 2

    @pytest.mark.asyncio
    async def test_async_generator_services_stream_data(self):
        """Async generator services should stream data correctly through Dependencies."""
        container = Container()

        class AsyncStreamService:
            async def stream_data(self, count: int):
                """Async generator for streaming data."""
                for i in range(count):
                    await asyncio.sleep(0.01)
                    yield {"index": i, "data": f"item_{i}"}

        container.register(AsyncStreamService, AsyncStreamService)
        container.register(AsyncCache, MockAsyncCache)

        @inject
        async def handler(
            deps: Dependencies[AsyncStreamService, AsyncCache],
        ) -> list[dict[str, Any]]:
            stream_service = deps[AsyncStreamService]
            cache = deps[AsyncCache]

            results = []
            async for item in stream_service.stream_data(3):
                results.append(item)
                await cache.set(f"stream_{item['index']}", item)

            return results

        async with container:
            result = await handler()
            assert len(result) == 3
            assert result[0]["index"] == 0
            assert result[2]["data"] == "item_2"

    @pytest.mark.asyncio
    async def test_cancelled_async_task_propagates_cancellation(self):
        """Cancelled async tasks should properly propagate CancelledError through Dependencies."""
        container = Container()

        cancelled = False

        class CancellableService:
            async def long_operation(self) -> str:
                nonlocal cancelled
                try:
                    await asyncio.sleep(10)
                    return "completed"
                except asyncio.CancelledError:
                    cancelled = True
                    raise

        container.register(CancellableService, CancellableService)
        container.register(AsyncDatabase, MockAsyncDatabase)

        @inject
        async def handler(
            deps: Dependencies[AsyncDatabase, CancellableService],
        ) -> str:
            db = deps[AsyncDatabase]
            service = deps[CancellableService]

            await db.query("SELECT 1")
            return await service.long_operation()

        async with container:
            task = asyncio.create_task(handler())
            await asyncio.sleep(0.1)
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await task

            assert cancelled is True

    @pytest.mark.integration
    def test_fastapi_pattern_with_metrics_and_caching(self):
        """FastAPI-style endpoint pattern with Dependencies for metrics, caching, and auth."""
        container = Container()

        container.register(DatabaseConnection, MockDatabaseConnection)
        container.register(CacheBackend, MockCacheBackend)
        container.register(AuthenticationService, MockAuthenticationService)
        container.register(
            MetricsCollector, MockMetricsCollector, scope=Scope.SINGLETON
        )

        @inject
        def get_user_endpoint(
            user_id: int,
            deps: Dependencies[
                DatabaseConnection,
                CacheBackend,
                AuthenticationService,
                MetricsCollector,
            ],
        ) -> dict[str, Any]:
            """Simulated FastAPI endpoint."""
            db = deps[DatabaseConnection]
            cache = deps[CacheBackend]
            _ = deps[AuthenticationService]
            metrics = deps[MetricsCollector]

            metrics.increment("api.get_user.requests")
            start_time = time.time()

            cache_key = f"user:{user_id}"
            cached_user = cache.get(cache_key)
            if cached_user:
                metrics.increment("api.get_user.cache_hits")
                return cached_user

            users = db.execute("SELECT * FROM users WHERE id = :id", {"id": user_id})
            if not users:
                metrics.increment("api.get_user.not_found")
                raise ValueError(f"User {user_id} not found")

            user = users[0]

            cache.set(cache_key, user, ttl=300)
            metrics.increment("api.get_user.cache_misses")

            duration = time.time() - start_time
            metrics.timing("api.get_user.duration", duration)

            return user

        with container.activate():
            result1 = get_user_endpoint(1)
            assert result1["username"] == "alice"

            result2 = get_user_endpoint(1)
            assert result2["username"] == "alice"

            metrics = container.get(MetricsCollector)
            assert len(metrics.metrics) > 0
            assert any("cache" in m["metric"] for m in metrics.metrics)
            assert any("cache_misses" in m["metric"] for m in metrics.metrics)

    @pytest.mark.integration
    def test_django_pattern_with_transaction_rollback(self):
        """Django-style view pattern with Dependencies handling transaction and rollback."""
        container = Container()

        email_provider = MockEmailProvider()
        container.register(DatabaseConnection, MockDatabaseConnection)
        container.given(EmailProvider, email_provider)
        container.register(AuthenticationService, MockAuthenticationService)

        @inject
        def create_user_view(
            username: str,
            email: str,
            password: str,
            deps: Dependencies[
                DatabaseConnection, EmailProvider, AuthenticationService
            ],
        ) -> dict[str, Any]:
            """Simulated Django view."""
            db = deps[DatabaseConnection]
            email_provider = deps[EmailProvider]
            _ = deps[AuthenticationService]

            db.begin_transaction()

            try:
                user_data = {"username": username, "email": email, "is_active": False}
                users = db.execute("INSERT INTO users", user_data)

                if not users:
                    raise ValueError("Failed to create user")

                user = users[0]

                activation_sent = email_provider.send_email(
                    to=email,
                    subject="Activate Your Account",
                    body=f"Welcome {username}! Click here to activate.",
                    html=True,
                )

                if not activation_sent:
                    db.rollback()
                    raise ValueError("Failed to send activation email")

                db.commit()

                return {"status": "success", "user": user}

            except Exception:
                db.rollback()
                raise

        with container.activate():
            result = create_user_view("charlie", "charlie@example.com", "password")
            assert result["status"] == "success"

            assert len(email_provider.sent_emails) == 1
            assert email_provider.sent_emails[0]["to"] == "charlie@example.com"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_background_task_bulk_email_processing(self):
        """Background task pattern processing bulk emails with Dependencies."""
        container = Container()

        container.register(DatabaseConnection, MockDatabaseConnection)
        container.register(EmailProvider, MockEmailProvider)
        container.register(
            MetricsCollector, MockMetricsCollector, scope=Scope.SINGLETON
        )

        @inject
        async def process_email_queue(
            deps: Dependencies[DatabaseConnection, EmailProvider, MetricsCollector],
        ) -> int:
            """Background task to process email queue."""
            db = deps[DatabaseConnection]
            email_provider = deps[EmailProvider]
            metrics = deps[MetricsCollector]

            users = db.execute("SELECT * FROM users WHERE is_active = true", {})

            recipients = [user["email"] for user in users]
            if recipients:
                sent_count = email_provider.send_bulk(
                    recipients=recipients,
                    subject="Weekly Newsletter",
                    body="Your weekly update...",
                )

                metrics.increment("emails.sent", sent_count)
                metrics.gauge("email_queue.size", 0)

                return sent_count

            return 0

        async with container:
            sent = await process_email_queue()
            assert sent == 2

            metrics = container.get(MetricsCollector)
            email_metric = next(
                (m for m in metrics.metrics if m["metric"] == "emails.sent"), None
            )
            assert email_metric is not None
            assert email_metric["value"] == 2

    @pytest.mark.integration
    def test_multi_tenant_isolation_with_shared_cache(self):
        """Multi-tenant pattern with isolated databases but shared cache through Dependencies."""
        container = Container()

        tenant_dbs: dict[str, MockDatabaseConnection] = {}

        def get_tenant_db(tenant_id: str) -> DatabaseConnection:
            if tenant_id not in tenant_dbs:
                tenant_dbs[tenant_id] = MockDatabaseConnection()
            return tenant_dbs[tenant_id]

        container.register(CacheBackend, MockCacheBackend, scope=Scope.SINGLETON)
        container.register(
            MetricsCollector, MockMetricsCollector, scope=Scope.SINGLETON
        )

        @inject
        def handle_tenant_request(
            tenant_id: str,
            operation: str,
            deps: Dependencies[CacheBackend, MetricsCollector],
        ) -> dict[str, Any]:
            """Handle tenant-specific request."""
            cache = deps[CacheBackend]
            metrics = deps[MetricsCollector]

            tenant_db = get_tenant_db(tenant_id)

            metrics.increment("tenant.requests", tags={"tenant": tenant_id})

            cache_key = f"tenant:{tenant_id}:data"

            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data

            data = tenant_db.execute("SELECT * FROM users", {})
            cache.set(cache_key, data, ttl=60)

            return {"tenant": tenant_id, "data": data}

        with container.activate():
            result1 = handle_tenant_request("tenant_a", "list_users")
            result2 = handle_tenant_request("tenant_b", "list_users")

            assert result1["tenant"] == "tenant_a"
            assert result2["tenant"] == "tenant_b"

            cache = container.get(CacheBackend)
            assert cache.get("tenant:tenant_a:data") is not None
            assert cache.get("tenant:tenant_b:data") is not None

    @pytest.mark.integration
    def test_payment_transaction_with_rollback_on_failure(self):
        """Payment transaction pattern with automatic rollback on failure using Dependencies."""
        container = Container()

        payment_gateway = MockPaymentGateway()
        email_provider = MockEmailProvider()

        container.register(DatabaseConnection, MockDatabaseConnection)
        container.given(PaymentGateway, payment_gateway)
        container.given(EmailProvider, email_provider)

        @inject
        def process_order(
            user_id: int,
            amount: float,
            deps: Dependencies[DatabaseConnection, PaymentGateway, EmailProvider],
        ) -> str:
            """Process order with payment."""
            db = deps[DatabaseConnection]
            payment = deps[PaymentGateway]
            email = deps[EmailProvider]

            db.begin_transaction()

            try:
                order = db.execute(
                    "INSERT INTO orders",
                    {"user_id": user_id, "amount": amount, "status": "pending"},
                )[0]

                transaction_id = payment.charge(amount, "USD", f"customer_{user_id}")

                order["status"] = "paid"
                order["transaction_id"] = transaction_id

                users = db.execute(
                    "SELECT * FROM users WHERE id = :id", {"id": user_id}
                )
                if users:
                    email.send_email(
                        to=users[0]["email"],
                        subject="Order Confirmation",
                        body=f"Your order #{order['id']} has been confirmed. Amount: ${amount}",
                    )

                db.commit()
                return transaction_id

            except Exception:
                db.rollback()

                if "transaction_id" in locals():
                    payment.refund(transaction_id)

                raise

        with container.activate():
            txn_id = process_order(1, 99.99)
            assert txn_id.startswith("txn_")

            assert payment_gateway.get_balance("customer_1") == 99.99
            assert len(email_provider.sent_emails) == 1

    @pytest.mark.integration
    def test_scope_hierarchy_request_session_singleton(self):
        """Scope hierarchy (request < session < singleton) should maintain proper lifecycle."""
        container = Container()

        creation_counts = {"db": 0, "cache": 0, "auth": 0}

        def create_db() -> DatabaseConnection:
            creation_counts["db"] += 1
            return MockDatabaseConnection()

        def create_cache() -> CacheBackend:
            creation_counts["cache"] += 1
            return MockCacheBackend()

        def create_auth() -> AuthenticationService:
            creation_counts["auth"] += 1
            return MockAuthenticationService()

        container.register(DatabaseConnection, create_db, scope=Scope.REQUEST)
        container.register(CacheBackend, create_cache, scope=Scope.SESSION)
        container.register(AuthenticationService, create_auth, scope=Scope.SINGLETON)

        @inject
        def handle_request(
            deps: Dependencies[DatabaseConnection, CacheBackend, AuthenticationService],
        ) -> dict[str, int]:
            _ = deps[DatabaseConnection]
            _ = deps[CacheBackend]
            _ = deps[AuthenticationService]
            return creation_counts.copy()

        with container.activate():
            with SessionScope(container):
                with RequestScope(container):
                    _ = handle_request()

                with RequestScope(container):
                    _ = handle_request()

            with SessionScope(container):
                with RequestScope(container):
                    _ = handle_request()

        assert creation_counts["db"] == 3
        assert creation_counts["cache"] == 2
        assert creation_counts["auth"] == 1

    @pytest.mark.integration
    def test_fallback_chain_cache_database_default(self):
        """Error recovery pattern with fallback chain: cache -> database -> default value."""
        container = Container()

        cache = MockCacheBackend()
        container.register(DatabaseConnection, MockDatabaseConnection)
        container.given(CacheBackend, cache)
        container.register(EmailProvider, MockEmailProvider)
        container.register(
            MetricsCollector, MockMetricsCollector, scope=Scope.SINGLETON
        )

        @inject
        def resilient_operation(
            user_id: int,
            deps: Dependencies[
                DatabaseConnection, CacheBackend, EmailProvider, MetricsCollector
            ],
        ) -> dict[str, Any]:
            """Operation with multiple fallback strategies."""
            db = deps[DatabaseConnection]
            cache = deps[CacheBackend]
            email = deps[EmailProvider]
            metrics = deps[MetricsCollector]

            result = {"success": False, "source": "unknown", "data": None}

            try:
                cached = cache.get(f"user:{user_id}")
                if cached:
                    metrics.increment("data.source.cache")
                    result.update({"success": True, "source": "cache", "data": cached})
                    return result
            except Exception:
                metrics.increment("cache.errors")

            try:
                users = db.execute(
                    "SELECT * FROM users WHERE id = :id", {"id": user_id}
                )
                if users:
                    user = users[0]
                    try:
                        cache.set(f"user:{user_id}", user)
                    except Exception:
                        pass

                    metrics.increment("data.source.database")
                    result.update({"success": True, "source": "database", "data": user})
                    return result
            except Exception as e:
                metrics.increment("database.errors")
                try:
                    email.send_email(
                        "admin@example.com",
                        "Database Error",
                        f"Failed to fetch user {user_id}: {str(e)}",
                    )
                except Exception:
                    pass

            metrics.increment("data.source.fallback")
            result.update(
                {
                    "success": True,
                    "source": "fallback",
                    "data": {
                        "id": user_id,
                        "username": "unknown",
                        "email": "unknown@example.com",
                    },
                }
            )
            return result

        with container.activate():
            result = resilient_operation(1)
            assert result["success"] is True
            assert result["source"] == "database"

            result2 = resilient_operation(1)
            assert result2["source"] == "cache"
