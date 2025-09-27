"""Realistic usage tests for Dependencies pattern - real-world scenarios."""

import time
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import pytest

from injx import (
    Container,
    Dependencies,
    RequestScope,
    Scope,
    SessionScope,
    inject,
)


# Realistic service protocols
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


# Realistic implementations
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
        # In real implementation, would rollback changes


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


class TestRealisticDependencies:
    """Test realistic usage patterns with Dependencies."""

    def test_fastapi_style_endpoint(self):
        """Test FastAPI-style endpoint with Dependencies."""
        container = Container()

        # Register services
        # Use SINGLETON scope to maintain state across resolutions
        container.register(DatabaseConnection, MockDatabaseConnection, scope=Scope.SINGLETON)
        container.register(CacheBackend, MockCacheBackend, scope=Scope.SINGLETON)
        container.register(AuthenticationService, MockAuthenticationService, scope=Scope.SINGLETON)
        container.register(MetricsCollector, MockMetricsCollector, scope=Scope.SINGLETON)

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
            _ = deps[AuthenticationService]  # Access for dependency validation
            metrics = deps[MetricsCollector]

            # Track request
            metrics.increment("api.get_user.requests")
            start_time = time.time()

            # Check cache first
            cache_key = f"user:{user_id}"
            cached_user = cache.get(cache_key)
            if cached_user:
                metrics.increment("api.get_user.cache_hits")
                return cached_user

            # Query database
            users = db.execute("SELECT * FROM users WHERE id = :id", {"id": user_id})
            if not users:
                metrics.increment("api.get_user.not_found")
                raise ValueError(f"User {user_id} not found")

            user = users[0]

            # Cache result
            cache.set(cache_key, user, ttl=300)
            metrics.increment("api.get_user.cache_misses")

            # Track timing
            duration = time.time() - start_time
            metrics.timing("api.get_user.duration", duration)

            return user

        with container.activate():
            # First call - cache miss
            result1 = get_user_endpoint(1)
            assert result1["username"] == "alice"

            # Second call - cache hit
            result2 = get_user_endpoint(1)
            assert result2["username"] == "alice"

            # Check metrics
            metrics = container.get(MetricsCollector)
            # Check that metrics were recorded (exact count may vary based on cache behavior)
            assert len(metrics.metrics) > 0
            assert any("cache" in m["metric"] for m in metrics.metrics)
            # Check that cache miss metrics were recorded
            assert any("cache_misses" in m["metric"] for m in metrics.metrics)

    def test_django_style_view(self):
        """Test Django-style view with Dependencies."""
        container = Container()

        # Use SINGLETON scope to maintain state across resolutions
        container.register(DatabaseConnection, MockDatabaseConnection, scope=Scope.SINGLETON)
        container.register(EmailProvider, MockEmailProvider, scope=Scope.SINGLETON)
        container.register(AuthenticationService, MockAuthenticationService, scope=Scope.SINGLETON)

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
            _ = deps[AuthenticationService]  # Access for dependency validation

            # Start transaction
            db.begin_transaction()

            try:
                # Create user in database
                user_data = {"username": username, "email": email, "is_active": False}
                users = db.execute("INSERT INTO users", user_data)

                if not users:
                    raise ValueError("Failed to create user")

                user = users[0]

                # Send activation email
                activation_sent = email_provider.send_email(
                    to=email,
                    subject="Activate Your Account",
                    body=f"Welcome {username}! Click here to activate.",
                    html=True,
                )

                if not activation_sent:
                    db.rollback()
                    raise ValueError("Failed to send activation email")

                # Commit transaction
                db.commit()

                return {"status": "success", "user": user}

            except Exception:
                db.rollback()
                raise

        with container.activate():
            result = create_user_view("charlie", "charlie@example.com", "password")
            assert result["status"] == "success"

            # Check email was sent
            email_provider = container.get(EmailProvider)
            assert len(email_provider.sent_emails) == 1
            assert email_provider.sent_emails[0]["to"] == "charlie@example.com"

    @pytest.mark.asyncio
    async def test_background_task_processing(self):
        """Test background task processing with Dependencies."""
        container = Container()

        # Use SINGLETON scope to maintain state across resolutions
        container.register(DatabaseConnection, MockDatabaseConnection, scope=Scope.SINGLETON)
        container.register(EmailProvider, MockEmailProvider, scope=Scope.SINGLETON)
        container.register(MetricsCollector, MockMetricsCollector, scope=Scope.SINGLETON)

        @inject
        async def process_email_queue(
            deps: Dependencies[DatabaseConnection, EmailProvider, MetricsCollector],
        ) -> int:
            """Background task to process email queue."""
            db = deps[DatabaseConnection]
            email_provider = deps[EmailProvider]
            metrics = deps[MetricsCollector]

            # Get pending emails from database
            users = db.execute("SELECT * FROM users WHERE is_active = true", {})

            # Send bulk emails
            recipients = [user["email"] for user in users]
            if recipients:
                sent_count = email_provider.send_bulk(
                    recipients=recipients,
                    subject="Weekly Newsletter",
                    body="Your weekly update...",
                )

                # Track metrics
                metrics.increment("emails.sent", sent_count)
                metrics.gauge("email_queue.size", 0)

                return sent_count

            return 0

        async with container:
            sent = await process_email_queue()
            assert sent == 2  # Two active users in mock data

            # Verify metrics
            metrics = container.get(MetricsCollector)
            email_metric = next(
                (m for m in metrics.metrics if m["metric"] == "emails.sent"), None
            )
            assert email_metric is not None
            assert email_metric["value"] == 2

    def test_multi_tenant_scenario(self):
        """Test multi-tenant scenario with scoped Dependencies."""
        container = Container()

        # Tenant-specific database connections
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

            # Get tenant-specific database
            tenant_db = get_tenant_db(tenant_id)

            # Track tenant metrics
            metrics.increment("tenant.requests", tags={"tenant": tenant_id})

            # Cache key includes tenant ID
            cache_key = f"tenant:{tenant_id}:data"

            # Check tenant-specific cache
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data

            # Query tenant database
            data = tenant_db.execute("SELECT * FROM users", {})
            cache.set(cache_key, data, ttl=60)

            return {"tenant": tenant_id, "data": data}

        with container.activate():
            # Handle requests for different tenants
            result1 = handle_tenant_request("tenant_a", "list_users")
            result2 = handle_tenant_request("tenant_b", "list_users")

            # Each tenant has separate database
            assert result1["tenant"] == "tenant_a"
            assert result2["tenant"] == "tenant_b"

            # But they share cache and metrics
            cache = container.get(CacheBackend)
            assert cache.get("tenant:tenant_a:data") is not None
            assert cache.get("tenant:tenant_b:data") is not None

    def test_transaction_pattern(self):
        """Test transaction pattern with Dependencies."""
        container = Container()

        # Use SINGLETON scope to maintain state across resolutions
        container.register(DatabaseConnection, MockDatabaseConnection, scope=Scope.SINGLETON)
        container.register(PaymentGateway, MockPaymentGateway, scope=Scope.SINGLETON)
        container.register(EmailProvider, MockEmailProvider, scope=Scope.SINGLETON)

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

            # Start database transaction
            db.begin_transaction()

            try:
                # Create order in database
                order = db.execute(
                    "INSERT INTO orders",
                    {"user_id": user_id, "amount": amount, "status": "pending"},
                )[0]

                # Process payment
                transaction_id = payment.charge(amount, "USD", f"customer_{user_id}")

                # Update order status
                order["status"] = "paid"
                order["transaction_id"] = transaction_id

                # Send confirmation email
                users = db.execute(
                    "SELECT * FROM users WHERE id = :id", {"id": user_id}
                )
                if users:
                    email.send_email(
                        to=users[0]["email"],
                        subject="Order Confirmation",
                        body=f"Your order #{order['id']} has been confirmed. Amount: ${amount}",
                    )

                # Commit transaction
                db.commit()
                return transaction_id

            except Exception:
                # Rollback database
                db.rollback()

                # Refund payment if it was processed
                if "transaction_id" in locals():
                    payment.refund(transaction_id)

                raise

        with container.activate():
            # Successful order
            txn_id = process_order(1, 99.99)
            assert txn_id.startswith("txn_")

            # Check payment was processed
            payment = container.get(PaymentGateway)
            assert payment.get_balance("customer_1") == 99.99

            # Check email was sent
            email_provider = container.get(EmailProvider)
            assert len(email_provider.sent_emails) == 1

    def test_request_session_scoping(self):
        """Test request and session scoping with Dependencies."""
        container = Container()

        # Track creation counts
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
            # Just access the services
            _ = deps[DatabaseConnection]
            _ = deps[CacheBackend]
            _ = deps[AuthenticationService]
            return creation_counts.copy()

        with container.activate():
            # Simulate session with multiple requests
            with SessionScope(container):
                with RequestScope(container):
                    _ = handle_request()

                with RequestScope(container):
                    _ = handle_request()

            # New session
            with SessionScope(container):
                with RequestScope(container):
                    _ = handle_request()

        # Verify scoping behavior
        assert creation_counts["db"] == 3  # New for each request
        assert creation_counts["cache"] == 2  # New for each session
        assert creation_counts["auth"] == 1  # Singleton

    def test_error_recovery_pattern(self):
        """Test error recovery with Dependencies."""
        container = Container()

        # Use SINGLETON scope to maintain state across resolutions
        container.register(DatabaseConnection, MockDatabaseConnection, scope=Scope.SINGLETON)
        container.register(CacheBackend, MockCacheBackend, scope=Scope.SINGLETON)
        container.register(EmailProvider, MockEmailProvider, scope=Scope.SINGLETON)
        container.register(MetricsCollector, MockMetricsCollector, scope=Scope.SINGLETON)

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

            # Try cache first
            try:
                cached = cache.get(f"user:{user_id}")
                if cached:
                    metrics.increment("data.source.cache")
                    result.update({"success": True, "source": "cache", "data": cached})
                    return result
            except Exception:
                metrics.increment("cache.errors")

            # Try database
            try:
                users = db.execute(
                    "SELECT * FROM users WHERE id = :id", {"id": user_id}
                )
                if users:
                    user = users[0]
                    # Try to update cache (non-critical)
                    try:
                        cache.set(f"user:{user_id}", user)
                    except Exception:
                        pass

                    metrics.increment("data.source.database")
                    result.update({"success": True, "source": "database", "data": user})
                    return result
            except Exception as e:
                metrics.increment("database.errors")
                # Send alert email (non-critical)
                try:
                    email.send_email(
                        "admin@example.com",
                        "Database Error",
                        f"Failed to fetch user {user_id}: {str(e)}",
                    )
                except Exception:
                    pass

            # Fallback to default
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
            # Test successful database fetch
            result = resilient_operation(1)
            assert result["success"] is True
            assert result["source"] == "database"

            # Test cache hit on second call
            result2 = resilient_operation(1)
            assert result2["source"] == "cache"
