# Injx - Type-Safe Dependency Injection

[![Python Version](https://img.shields.io/pypi/pyversions/injx.svg)](https://pypi.org/project/injx/)
[![PyPI Version](https://img.shields.io/pypi/v/injx.svg)](https://pypi.org/project/injx/)
[![Tests](https://github.com/QriusGlobal/injx/actions/workflows/ci.yml/badge.svg)](https://github.com/QriusGlobal/injx/actions/workflows/ci.yml)
[![Type Checked](https://img.shields.io/badge/type--checked-basedpyright-blue.svg)](https://github.com/DetachHead/basedpyright)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

Type-safe dependency injection for Python 3.13+ with zero external dependencies.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Why Dependency Injection?](#why-dependency-injection)
- [Examples](#examples)
- [Framework Integration](#framework-integration)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Installation

```bash
# Using pip
pip install injx

# Using UV (recommended)
uv add injx
```

## Quick Start

Copy this complete example to `main.py` and run it:

```python
"""Complete working example of dependency injection with Injx."""

from typing import Protocol, Any, Optional
from injx import Container, Token, inject, Scope


# 1. Define service interfaces using Protocols with type annotations
class Database(Protocol):
    """Database service protocol."""
    def get_user(self, user_id: int) -> dict[str, Any]: ...
    def save_user(self, user: dict[str, Any]) -> None: ...


class HTTPClient(Protocol):
    """HTTP client protocol."""
    def get(self, url: str) -> dict[str, Any]: ...
    def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]: ...


class Cache(Protocol):
    """Cache service protocol."""
    def get(self, key: str) -> Optional[dict[str, Any]]: ...
    def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None: ...


# 2. Implement the services
class PostgresDatabase:
    """PostgreSQL database implementation."""

    def __init__(self) -> None:
        print("📦 Connecting to PostgreSQL...")
        # In production: psycopg2.connect(...)

    def get_user(self, user_id: int) -> dict[str, Any]:
        print(f"  └─ Fetching user {user_id} from database")
        return {
            "id": user_id,
            "name": f"User_{user_id}",
            "email": f"user{user_id}@example.com"
        }

    def save_user(self, user: dict[str, Any]) -> None:
        print(f"  └─ Saving user {user['id']} to database")


class APIClient:
    """HTTP client implementation."""

    def __init__(self) -> None:
        print("🌐 Initializing HTTP client...")
        # In production: httpx.Client() or requests.Session()

    def get(self, url: str) -> dict[str, Any]:
        print(f"  └─ GET {url}")
        return {"status": "success", "data": {"verified": True}}

    def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        print(f"  └─ POST {url}")
        return {"status": "created", "id": 123}


class RedisCache:
    """Redis cache implementation."""

    def __init__(self) -> None:
        print("⚡ Connecting to Redis cache...")
        # In production: redis.Redis()
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Optional[dict[str, Any]]:
        return self._cache.get(key)

    def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        self._cache[key] = value
        print(f"  └─ Cached {key} (TTL: {ttl}s)")


# 3. Setup dependency injection container
def setup_container() -> Container:
    """Configure the DI container with all services."""
    container = Container()

    # Define typed tokens for each service
    DB = Token[Database]("database", Database)
    HTTP = Token[HTTPClient]("http_client", HTTPClient)
    CACHE = Token[Cache]("cache", Cache)

    # Register services with appropriate scopes
    container.register(DB, PostgresDatabase, scope=Scope.SINGLETON)
    container.register(HTTP, APIClient, scope=Scope.SINGLETON)
    container.register(CACHE, RedisCache, scope=Scope.SINGLETON)

    # Store tokens for global access
    container.set("DB_TOKEN", DB)
    container.set("HTTP_TOKEN", HTTP)
    container.set("CACHE_TOKEN", CACHE)

    return container


# 4. Use @inject decorator for automatic dependency injection
@inject
def get_user_info(
    user_id: int,
    db: Database,
    http: HTTPClient,
    cache: Cache
) -> dict[str, Any]:
    """
    Fetch user info with caching and external validation.

    Dependencies are automatically injected based on type annotations.
    """
    # Check cache first
    cache_key = f"user:{user_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        print(f"✅ Cache hit for user {user_id}")
        return cached_data

    # Fetch from database
    user = db.get_user(user_id)

    # Validate with external API
    validation = http.get(f"https://api.example.com/validate/{user_id}")
    user["verified"] = validation["data"]["verified"]

    # Store in cache
    cache.set(cache_key, user)

    return user


# 5. Alternative: Create user with validation
@inject
def create_user(
    name: str,
    email: str,
    db: Database,
    http: HTTPClient
) -> dict[str, Any]:
    """Create a new user with external validation."""
    # Validate email
    validation = http.post(
        "https://api.example.com/validate/email",
        {"email": email}
    )

    if validation["status"] != "created":
        raise ValueError(f"Invalid email: {email}")

    # Create user
    user = {
        "id": validation["id"],
        "name": name,
        "email": email
    }
    db.save_user(user)

    return user


# 6. Run the application
if __name__ == "__main__":
    print("🚀 Starting application\n")

    # Initialize container once at startup
    container = setup_container()
    Container.set_active(container)

    print("\n" + "=" * 50)
    print("Container ready with all services")
    print("=" * 50 + "\n")

    # Example 1: Get user (cache miss)
    print("📊 Fetching user 42...")
    user = get_user_info(42)
    print(f"Result: {user}\n")

    # Example 2: Get same user (cache hit)
    print("📊 Fetching user 42 again...")
    user = get_user_info(42)
    print(f"Result: {user}\n")

    # Example 3: Create new user
    print("📊 Creating new user...")
    new_user = create_user("Alice", "alice@example.com")
    print(f"Created: {new_user}\n")

    print("✅ Application completed successfully!")
```

## Core Concepts

### Tokens
Type-safe service identifiers that preserve type information at runtime:
```python
DB_TOKEN: Token[Database] = Token("database", Database)
```

### Container
Service registry that manages registration and resolution:
```python
container = Container()
container.register(DB_TOKEN, PostgresDatabase, scope=Scope.SINGLETON)
```

### @inject Decorator
Automatically resolves and injects dependencies based on type annotations:
```python
@inject
def my_service(db: Database, cache: Cache) -> None:
    # db and cache are automatically injected
    ...
```

### Scopes
Control service lifetime and instantiation:
- `SINGLETON`: One instance for container lifetime
- `TRANSIENT`: New instance for each resolution
- `REQUEST`: One instance per request context
- `SESSION`: One instance per session context

## Why Dependency Injection?

### 1. Testability
Replace real services with mocks without modifying code:
```python
# In tests
mock_db = Mock(spec=Database)
container.override(DB_TOKEN, mock_db)
```

### 2. Flexibility
Swap implementations without changing business logic:
```python
# Switch from PostgreSQL to MongoDB
container.register(DB_TOKEN, MongoDatabase)
```

### 3. Lifecycle Management
Automatic resource initialization and cleanup:
```python
async with container:
    # Services initialized
    await my_service()
    # Services cleaned up automatically
```

### 4. Type Safety
Catch dependency errors at development time:
```python
# Type checker warns if Database protocol not satisfied
container.register(DB_TOKEN, InvalidClass)  # Type error!
```

## Examples

All examples include comprehensive type annotations and are immediately runnable.

### Basic Patterns
- [Basic DI Setup](docs/examples/basic_example.py) - Complete working example with DB, HTTP, Cache, Email services
- [Async Services](docs/examples/async_example.py) - Async/await patterns with proper cleanup
- [Testing with DI](docs/examples/testing_example.py) - Pytest fixtures with Mock(autospec=True)

### Framework Integration
- [FastAPI Integration](docs/examples/fastapi_integration.py) - Request-scoped dependencies and background tasks
- [Django Integration](docs/examples/django_integration.py) - Views, middleware, and DRF integration

## Framework Integration

### FastAPI
```python
@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: Database = Depends(get_database)
):
    return await db.get_user(user_id)
```

### Django
```python
@inject_services
def user_view(request, user_id: int):
    user_service: UserService = request.user_service
    return JsonResponse(user_service.get_user(user_id))
```

## Documentation

- **Full Documentation**: https://qriusglobal.github.io/injx/
- **API Reference**: https://qriusglobal.github.io/injx/api/
- **Advanced Patterns**: https://qriusglobal.github.io/injx/advanced/

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone the repository
git clone https://github.com/QriusGlobal/injx.git
cd injx

# Install with UV
uv venv
uv pip install -e ".[dev]"

# Run tests
uv run pytest
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.