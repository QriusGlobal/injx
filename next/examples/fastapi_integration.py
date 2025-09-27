"""FastAPI Integration with Injx - Type-Safe Web Services

This example demonstrates:
- FastAPI integration with dependency injection
- Request-scoped dependencies
- Async endpoints with proper type hints
- Pydantic models for validation
- Background tasks with injected services

Run the application:
    uvicorn fastapi_integration:app --reload

Test endpoints:
    curl http://localhost:8000/users/123
    curl -X POST http://localhost:8000/users -d '{"name":"Alice","email":"alice@example.com"}'
"""

from typing import Optional, Any, Annotated
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from injx import Container, Token, inject, Scope, RequestScope, Dependencies
import asyncio


# 1. Pydantic models for type-safe request/response
class UserCreateRequest(BaseModel):
    """Request model for creating a user."""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    newsletter: bool = Field(default=True)


class UserResponse(BaseModel):
    """Response model for user data."""
    id: int
    name: str
    email: str
    status: str
    score: Optional[int] = None
    verified: bool = False


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str
    database: bool
    cache: bool
    external_api: bool


# 2. Service protocols (reusing from basic_example)
from typing import Protocol


class Database(Protocol):
    """Database service protocol."""
    async def get_user(self, user_id: int) -> dict[str, Any]: ...
    async def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]: ...
    async def list_users(self, limit: int = 10) -> list[dict[str, Any]]: ...
    async def health_check(self) -> bool: ...


class Cache(Protocol):
    """Cache service protocol."""
    async def get(self, key: str) -> Optional[dict[str, Any]]: ...
    async def set(self, key: str, value: dict[str, Any], ttl: int = 300) -> None: ...
    async def delete(self, key: str) -> bool: ...
    async def health_check(self) -> bool: ...


class HTTPClient(Protocol):
    """External API client protocol."""
    async def get(self, url: str) -> dict[str, Any]: ...
    async def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]: ...
    async def health_check(self) -> bool: ...


class EmailService(Protocol):
    """Email service protocol."""
    async def send_welcome(self, email: str, name: str) -> bool: ...
    async def send_newsletter(self, email: str, content: str) -> bool: ...


# 3. Service implementations
class AsyncPostgresDB:
    """Async PostgreSQL implementation."""

    def __init__(self) -> None:
        self.connection_pool: Optional[Any] = None
        self._users: dict[int, dict[str, Any]] = {}
        self._next_id: int = 1

    async def get_user(self, user_id: int) -> dict[str, Any]:
        """Get user from database."""
        await asyncio.sleep(0.01)  # Simulate DB latency
        if user_id not in self._users:
            raise ValueError(f"User {user_id} not found")
        return self._users[user_id].copy()

    async def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create new user."""
        await asyncio.sleep(0.02)  # Simulate DB latency
        user = {
            "id": self._next_id,
            **user_data,
            "status": "active"
        }
        self._users[self._next_id] = user
        self._next_id += 1
        return user.copy()

    async def list_users(self, limit: int = 10) -> list[dict[str, Any]]:
        """List users with pagination."""
        await asyncio.sleep(0.01)
        users = list(self._users.values())[:limit]
        return [u.copy() for u in users]

    async def health_check(self) -> bool:
        """Check database health."""
        await asyncio.sleep(0.001)
        return True


class RedisCache:
    """Async Redis cache implementation."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    async def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get from cache."""
        await asyncio.sleep(0.001)
        return self._cache.get(key)

    async def set(self, key: str, value: dict[str, Any], ttl: int = 300) -> None:
        """Set in cache."""
        await asyncio.sleep(0.001)
        self._cache[key] = value

    async def delete(self, key: str) -> bool:
        """Delete from cache."""
        await asyncio.sleep(0.001)
        return self._cache.pop(key, None) is not None

    async def health_check(self) -> bool:
        """Check cache health."""
        return True


class ExternalAPIClient:
    """External API client implementation."""

    async def get(self, url: str) -> dict[str, Any]:
        """Make GET request."""
        await asyncio.sleep(0.05)  # Simulate network latency
        return {
            "score": 85,
            "verified": True,
            "premium": False
        }

    async def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make POST request."""
        await asyncio.sleep(0.05)
        return {"status": "success", "id": 12345}

    async def health_check(self) -> bool:
        """Check external API health."""
        await asyncio.sleep(0.01)
        return True


class AsyncEmailService:
    """Async email service."""

    async def send_welcome(self, email: str, name: str) -> bool:
        """Send welcome email."""
        await asyncio.sleep(0.02)
        print(f"📧 Sending welcome email to {email}")
        return True

    async def send_newsletter(self, email: str, content: str) -> bool:
        """Send newsletter."""
        await asyncio.sleep(0.02)
        print(f"📰 Sending newsletter to {email}")
        return True


# 4. Define tokens
DB_TOKEN: Token[Database] = Token("database", Database)
CACHE_TOKEN: Token[Cache] = Token("cache", Cache)
HTTP_TOKEN: Token[HTTPClient] = Token("http_client", HTTPClient)
EMAIL_TOKEN: Token[EmailService] = Token("email_service", EmailService)


# 5. Dependency injection setup
def setup_container() -> Container:
    """Configure DI container for FastAPI."""
    container = Container()

    # Register services with appropriate scopes
    container.register(DB_TOKEN, AsyncPostgresDB, scope=Scope.SINGLETON)
    container.register(CACHE_TOKEN, RedisCache, scope=Scope.SINGLETON)
    container.register(HTTP_TOKEN, ExternalAPIClient, scope=Scope.SINGLETON)
    container.register(EMAIL_TOKEN, AsyncEmailService, scope=Scope.SINGLETON)

    return container


# 6. FastAPI dependency functions
async def get_database() -> Database:
    """FastAPI dependency for database."""
    container = Container.get_active()
    return await container.aget(DB_TOKEN)


async def get_cache() -> Cache:
    """FastAPI dependency for cache."""
    container = Container.get_active()
    return await container.aget(CACHE_TOKEN)


async def get_http_client() -> HTTPClient:
    """FastAPI dependency for HTTP client."""
    container = Container.get_active()
    return await container.aget(HTTP_TOKEN)


async def get_email_service() -> EmailService:
    """FastAPI dependency for email service."""
    container = Container.get_active()
    return await container.aget(EMAIL_TOKEN)


# Type aliases for cleaner annotations using Dependencies pattern
async def get_services() -> Dependencies[Database, Cache, HTTPClient, EmailService]:
    """FastAPI dependency for all services grouped."""
    container = Container.get_active()
    return Dependencies(container, (Database, Cache, HTTPClient, EmailService))

ServicesDep = Annotated[Dependencies[Database, Cache, HTTPClient, EmailService], Depends(get_services)]


# 7. Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with proper DI setup."""
    # Startup
    print("🚀 Starting FastAPI with Injx DI")
    container = setup_container()
    Container.set_active(container)

    # Initialize async resources
    db = await container.aget(DB_TOKEN)
    cache = await container.aget(CACHE_TOKEN)

    yield

    # Shutdown
    print("🛑 Shutting down FastAPI")
    # Cleanup would happen here in production


# 8. Create FastAPI app
app = FastAPI(
    title="Injx FastAPI Example",
    description="Type-safe dependency injection in FastAPI",
    version="1.0.0",
    lifespan=lifespan
)


# 9. API endpoints with dependency injection
@app.get("/health", response_model=HealthCheckResponse)
async def health_check(
    deps: ServicesDep
) -> HealthCheckResponse:
    """Health check endpoint with service status using Dependencies pattern."""
    # Extract services from dependencies
    db = deps[Database]
    cache = deps[Cache]
    http_client = deps[HTTPClient]

    # Check all services concurrently
    db_health, cache_health, api_health = await asyncio.gather(
        db.health_check(),
        cache.health_check(),
        http_client.health_check()
    )

    return HealthCheckResponse(
        status="healthy" if all([db_health, cache_health, api_health]) else "degraded",
        database=db_health,
        cache=cache_health,
        external_api=api_health
    )


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    deps: ServicesDep
) -> UserResponse:
    """Get user by ID with caching and enrichment using Dependencies pattern."""
    # Extract services from dependencies
    db = deps[Database]
    cache = deps[Cache]
    http_client = deps[HTTPClient]

    # Check cache first
    cache_key = f"user:{user_id}"
    cached_user = await cache.get(cache_key)

    if cached_user:
        return UserResponse(**cached_user)

    # Get from database
    try:
        user = await db.get_user(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )

    # Enrich with external API
    enrichment = await http_client.get(f"https://api.example.com/users/{user_id}")
    user.update(enrichment)

    # Cache the result
    await cache.set(cache_key, user, ttl=600)

    return UserResponse(**user)


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    background_tasks: BackgroundTasks,
    deps: ServicesDep
) -> UserResponse:
    """Create new user with email validation and notification using Dependencies pattern."""
    # Extract services from dependencies
    db = deps[Database]
    http_client = deps[HTTPClient]
    email_service = deps[EmailService]

    # Validate email with external service
    validation = await http_client.post(
        "https://api.example.com/validate/email",
        {"email": request.email}
    )

    if not validation.get("status") == "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address"
        )

    # Create user in database
    user_data = request.model_dump()
    new_user = await db.create_user(user_data)

    # Send welcome email in background
    background_tasks.add_task(
        email_service.send_welcome,
        request.email,
        request.name
    )

    # Send newsletter if opted in
    if request.newsletter:
        background_tasks.add_task(
            email_service.send_newsletter,
            request.email,
            "Welcome to our newsletter!"
        )

    return UserResponse(**new_user)


@app.get("/users", response_model=list[UserResponse])
async def list_users(
    limit: int = 10,
    deps: ServicesDep
) -> list[UserResponse]:
    """List users with caching using Dependencies pattern."""
    # Extract services from dependencies
    db = deps[Database]
    cache = deps[Cache]

    # Check cache for user list
    cache_key = f"users:list:{limit}"
    cached_list = await cache.get(cache_key)

    if cached_list:
        return [UserResponse(**u) for u in cached_list["users"]]

    # Get from database
    users = await db.list_users(limit=limit)

    # Cache the result
    await cache.set(cache_key, {"users": users}, ttl=60)

    return [UserResponse(**u) for u in users]


@app.delete("/cache/users/{user_id}")
async def invalidate_user_cache(
    user_id: int,
    deps: ServicesDep
) -> JSONResponse:
    """Invalidate user cache entry using Dependencies pattern."""
    cache = deps[Cache]
    deleted = await cache.delete(f"user:{user_id}")
    return JSONResponse(
        content={"message": f"Cache invalidated for user {user_id}", "deleted": deleted}
    )


# 10. Request-scoped dependencies example
@app.post("/batch/users")
async def batch_create_users(
    users: list[UserCreateRequest],
    deps: ServicesDep,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """Batch create users with request-scoped transaction using Dependencies pattern."""
    # Extract services from dependencies
    db = deps[Database]
    email_service = deps[EmailService]

    created_users: list[dict[str, Any]] = []

    # In production, this would be a database transaction
    async with RequestScope() as request_scope:
        for user_request in users:
            user_data = user_request.model_dump()
            new_user = await db.create_user(user_data)
            created_users.append(new_user)

            # Queue email for each user
            background_tasks.add_task(
                email_service.send_welcome,
                user_request.email,
                user_request.name
            )

    return JSONResponse(
        content={
            "message": f"Created {len(created_users)} users",
            "users": created_users
        },
        status_code=status.HTTP_201_CREATED
    )


# 11. Error handling with DI
@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError) -> JSONResponse:
    """Handle value errors with proper logging."""
    # In production, you'd inject a logger service here
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


# Run with: uvicorn fastapi_integration:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)