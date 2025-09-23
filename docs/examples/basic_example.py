"""Basic Injx Example - Dependency Injection with Type Safety

This example demonstrates:
- Type-safe dependency injection with Protocol definitions
- Real-world I/O services (Database, HTTP, Cache, Email)
- Proper type annotations throughout
- Service lifecycle management with scopes

Run this file directly to see it in action:
    python basic_example.py
"""

from typing import Protocol, Any, Optional
from injx import Container, Token, inject, Scope, Dependencies


# 1. Define service interfaces using Protocols with full type annotations
class Database(Protocol):
    """Database service protocol with type-safe methods."""

    def get_user(self, user_id: int) -> dict[str, Any]:
        """Fetch a user by ID."""
        ...

    def save_user(self, user: dict[str, Any]) -> None:
        """Save a user to the database."""
        ...


class HTTPClient(Protocol):
    """HTTP client protocol for external API calls."""

    def get(self, url: str) -> dict[str, Any]:
        """Make a GET request."""
        ...

    def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request."""
        ...


class Cache(Protocol):
    """Cache service protocol for performance optimization."""

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get a value from cache."""
        ...

    def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        """Set a value in cache with optional TTL."""
        ...


class EmailService(Protocol):
    """Email service protocol for notifications."""

    def send(self, to: str, subject: str, body: str) -> bool:
        """Send an email."""
        ...


# 2. Implement the services with proper type annotations
class PostgresDatabase:
    """PostgreSQL database implementation."""

    def __init__(self) -> None:
        print("📦 Connecting to PostgreSQL database...")
        # In production: psycopg2.connect(...)
        self.connected: bool = True

    def get_user(self, user_id: int) -> dict[str, Any]:
        """Fetch user from database."""
        print(f"  └─ DB: Fetching user {user_id}")
        return {
            "id": user_id,
            "name": f"User_{user_id}",
            "email": f"user{user_id}@example.com",
            "created_at": "2024-01-01T00:00:00Z"
        }

    def save_user(self, user: dict[str, Any]) -> None:
        """Save user to database."""
        print(f"  └─ DB: Saving user {user['id']}")


class APIClient:
    """HTTP client implementation with connection pooling."""

    def __init__(self) -> None:
        print("🌐 Initializing HTTP client with connection pool...")
        # In production: httpx.Client() or requests.Session()
        self.session_active: bool = True

    def get(self, url: str) -> dict[str, Any]:
        """Execute GET request."""
        print(f"  └─ HTTP: GET {url}")
        return {"status": "success", "data": {"score": 95, "verified": True}}

    def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        """Execute POST request."""
        print(f"  └─ HTTP: POST {url}")
        return {"status": "created", "id": 123, "timestamp": "2024-01-01T00:00:00Z"}


class RedisCache:
    """Redis cache implementation."""

    def __init__(self) -> None:
        print("⚡ Connecting to Redis cache...")
        # In production: redis.Redis()
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve from cache."""
        return self._cache.get(key)

    def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        """Store in cache."""
        self._cache[key] = value
        print(f"  └─ Cache: Stored {key} (TTL: {ttl}s)")


class SMTPEmailService:
    """SMTP email service implementation."""

    def __init__(self) -> None:
        print("📧 Connecting to SMTP server...")
        # In production: smtplib.SMTP()
        self.smtp_connected: bool = True

    def send(self, to: str, subject: str, body: str) -> bool:
        """Send email via SMTP."""
        print(f"  └─ Email: Sending to {to}: '{subject}'")
        return True


# 3. Define typed tokens for dependency injection
DB_TOKEN: Token[Database] = Token("database", Database)
HTTP_TOKEN: Token[HTTPClient] = Token("http_client", HTTPClient)
CACHE_TOKEN: Token[Cache] = Token("cache", Cache)
EMAIL_TOKEN: Token[EmailService] = Token("email", EmailService)


# 4. Setup DI container with proper type hints
def setup_container() -> Container:
    """Configure the dependency injection container."""
    container = Container()

    # Register services with appropriate scopes
    container.register(DB_TOKEN, PostgresDatabase, scope=Scope.SINGLETON)
    container.register(HTTP_TOKEN, APIClient, scope=Scope.SINGLETON)
    container.register(CACHE_TOKEN, RedisCache, scope=Scope.SINGLETON)
    container.register(EMAIL_TOKEN, SMTPEmailService, scope=Scope.SINGLETON)

    return container


# 5. Business logic functions with @inject decorator and Dependencies pattern
@inject
def get_user_with_enrichment(
    user_id: int,
    deps: Dependencies[Database, HTTPClient, Cache]
) -> dict[str, Any]:
    """
    Fetch user data enriched with external API data.

    This function demonstrates:
    - Automatic dependency injection via @inject with Dependencies pattern
    - Type-safe service access through deps[Type]
    - Cache-aside pattern
    """
    # Extract services from dependencies
    db = deps[Database]
    http = deps[HTTPClient]
    cache = deps[Cache]

    # Check cache first
    cache_key: str = f"user:{user_id}:enriched"
    cached_data: Optional[dict[str, Any]] = cache.get(cache_key)

    if cached_data is not None:
        print(f"✅ Cache hit for user {user_id}")
        return cached_data

    print(f"🔍 Cache miss for user {user_id}, fetching fresh data...")

    # Fetch from database
    user_data: dict[str, Any] = db.get_user(user_id)

    # Enrich with external API
    enrichment: dict[str, Any] = http.get(f"https://api.example.com/enrich/{user_id}")
    user_data["score"] = enrichment["data"]["score"]
    user_data["verified"] = enrichment["data"]["verified"]

    # Store in cache
    cache.set(cache_key, user_data, ttl=300)

    return user_data


@inject
def create_user_account(
    name: str,
    email: str,
    deps: Dependencies[Database, HTTPClient, EmailService]
) -> dict[str, Any]:
    """
    Create a new user account with validation and notification.

    Demonstrates:
    - Grouped service dependencies using Dependencies pattern
    - Type-safe error handling
    - Service orchestration
    """
    # Extract services from dependencies
    db = deps[Database]
    http = deps[HTTPClient]
    email_service = deps[EmailService]

    print(f"\n📝 Creating account for {name}")

    # Validate email with external service
    validation_result: dict[str, Any] = http.post(
        "https://api.example.com/validate/email",
        {"email": email}
    )

    if validation_result["status"] != "created":
        raise ValueError(f"Invalid email: {email}")

    # Create user record
    new_user: dict[str, Any] = {
        "id": validation_result["id"],
        "name": name,
        "email": email,
        "status": "active"
    }

    # Save to database
    db.save_user(new_user)

    # Send welcome email
    email_sent: bool = email_service.send(
        to=email,
        subject="Welcome to Our Platform!",
        body=f"Hello {name},\n\nWelcome aboard! Your account is now active."
    )

    if email_sent:
        print("  └─ ✅ Welcome email sent successfully")

    return new_user


# 6. Main execution block
def main() -> None:
    """Main function demonstrating the complete DI setup."""
    # Initialize container
    print("🚀 Starting Application with Dependency Injection\n")
    print("=" * 50)

    container: Container = setup_container()
    Container.set_active(container)

    print("\n" + "=" * 50)
    print("Container initialized with all services")
    print("=" * 50)

    # Example 1: Fetch user with enrichment (cache miss)
    print("\n📊 Example 1: Fetching user with enrichment")
    print("-" * 40)
    user1: dict[str, Any] = get_user_with_enrichment(42)
    print(f"Result: {user1}")

    # Example 2: Same user (cache hit)
    print("\n📊 Example 2: Fetching same user (should hit cache)")
    print("-" * 40)
    user2: dict[str, Any] = get_user_with_enrichment(42)
    print(f"Result: {user2}")

    # Example 3: Create new user
    print("\n📊 Example 3: Creating new user account")
    print("-" * 40)
    new_user: dict[str, Any] = create_user_account(
        name="Alice Johnson",
        email="alice@example.com"
    )
    print(f"Created user: {new_user}")

    print("\n" + "=" * 50)
    print("✅ Application completed successfully")
    print("=" * 50)


if __name__ == "__main__":
    main()