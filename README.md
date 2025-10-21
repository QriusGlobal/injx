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

Keep it simple. Declare lifecycles once, then write application code.

1) Build a container (explicit, minimal)
```python
from contextlib import asynccontextmanager
from injx import Container, Scope, Token

class Engine:
    async def aclose(self) -> None: ...

class Session:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
    async def aclose(self) -> None: ...

def build_container() -> Container:
    c = Container()
    ENGINE = Token[Engine]("engine", Engine, scope=Scope.SINGLETON)
    SESSION = Token[Session]("session", Session, scope=Scope.REQUEST)

    @asynccontextmanager
    async def engine_cm():
        eng = Engine();
        try:
            yield eng
        finally:
            await eng.aclose()

    @asynccontextmanager
    async def session_cm():
        s = Session(engine=await c.aget(ENGINE))
        try:
            yield s
        finally:
            await s.aclose()

    c.register_context_async(ENGINE, lambda: engine_cm(), scope=Scope.SINGLETON)
    c.register_context_async(SESSION, lambda: session_cm(), scope=Scope.REQUEST)
    c.set("ENGINE", ENGINE); c.set("SESSION", SESSION)
    return c
```

2) FastAPI (request scope + lifespan)
```python
from fastapi import FastAPI
container = build_container()

from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    with container.activate():
        yield
    await container.aclose()

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def injx_request_scope(request, call_next):
    async with container.async_request_scope():
        return await call_next(request)

@app.get("/health")
async def health():
    session_token = container.get("SESSION")
    _ = await container.aget(session_token)
    return {"status": "ok"}
```

3) ETL (one job scope)
```python
import asyncio

async def run():
    c = build_container()
    async with c:
        async with c.async_request_scope():
            session = await c.aget(c.get("SESSION"))
            # do ETL with session

<<<<<<< HEAD
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


# 4. Use @inject decorator with Dependencies pattern for clean DI
@inject
def get_user_info(
    user_id: int,
    deps: Dependencies[Database, HTTPClient, Cache]
) -> dict[str, Any]:
    """
    Fetch user info with caching and external validation.

    Dependencies are grouped and injected as a single parameter.
    This follows modern Python patterns used by FastAPI and Pydantic.
    """
    # Extract services from dependencies container
    db = deps[Database]
    http = deps[HTTPClient]
    cache = deps[Cache]

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


# 5. Alternative: Create user with validation using Dependencies
@inject
def create_user(
    name: str,
    email: str,
    deps: Dependencies[Database, HTTPClient]
) -> dict[str, Any]:
    """Create a new user with external validation using grouped dependencies."""
    # Extract services
    db = deps[Database]
    http = deps[HTTPClient]

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
    asyncio.run(run())
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

### @inject Decorator with Dependencies Pattern
Automatically resolves and injects grouped dependencies:
```python
@inject
def my_service(deps: Dependencies[Database, Cache]) -> None:
    # Access dependencies with type safety
    db = deps[Database]
    cache = deps[Cache]
    ...
```

This pattern:
- Groups related dependencies into a single parameter
- Follows modern Python conventions (FastAPI, Pydantic)
- Keeps function signatures clean and maintainable
- Provides full type safety

### Async Support with Dependencies
Dependencies are fully awaitable for async contexts:
```python
@inject
async def async_handler(
    deps: Dependencies[AsyncDatabase, AsyncCache, AsyncHTTPClient]
) -> dict[str, Any]:
    # Dependencies are automatically resolved in parallel for performance
    db = deps[AsyncDatabase]
    cache = deps[AsyncCache]
    http = deps[AsyncHTTPClient]

    # Use async services
    results = await asyncio.gather(
        db.query("SELECT * FROM users"),
        cache.get("key"),
        http.get("https://api.example.com/data")
    )
    return process_results(results)
```

The Dependencies container intelligently handles resolution:
- In sync contexts: Uses `resolve()` for synchronous resolution
- In async contexts: Automatically awaitable with parallel resolution
- Optimal performance: All dependencies resolved concurrently

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

Canonical examples (minimal, production-ready patterns):
- FastAPI minimal: `docs/examples/fastapi_minimal.py`
- ETL minimal: `docs/examples/etl_minimal.py`

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
