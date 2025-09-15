"""FastAPI integration example with injx dependency injection."""

import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Protocol, runtime_checkable

# FastAPI imports (install with: pip install fastapi uvicorn)
try:
    from fastapi import Depends, FastAPI, HTTPException
    from pydantic import BaseModel

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("FastAPI not available. Install with: pip install fastapi uvicorn")

    # Mock classes for demonstration
    class BaseModel:
        pass

    class FastAPI:
        def __init__(self, **kwargs):
            pass

        def get(self, path):
            return lambda f: f

        def post(self, path):
            return lambda f: f

    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            pass


from injx import Container, Injectable, Scope, Token


# Domain models
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str


class CreateUserRequest(BaseModel):
    name: str
    email: str


# Protocols for dependency inversion
@runtime_checkable
class UserRepository(Protocol):
    """Protocol for user data access."""

    async def create_user(self, user: User) -> User: ...
    async def get_user(self, user_id: int) -> Optional[User]: ...
    async def get_all_users(self) -> List[User]: ...


@runtime_checkable
class EmailService(Protocol):
    """Protocol for email sending."""

    async def send_welcome_email(self, user: User) -> bool: ...


@runtime_checkable
class Logger(Protocol):
    """Protocol for logging."""

    def info(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...


# Implementations
class InMemoryUserRepository:
    """In-memory user repository implementation."""

    def __init__(self):
        self._users: List[User] = []
        self._next_id = 1

    async def create_user(self, user: User) -> User:
        user.id = self._next_id
        self._next_id += 1
        self._users.append(user)
        return user

    async def get_user(self, user_id: int) -> Optional[User]:
        for user in self._users:
            if user.id == user_id:
                return user
        return None

    async def get_all_users(self) -> List[User]:
        return self._users.copy()


class MockEmailService:
    """Mock email service for demonstration."""

    def __init__(self, logger: Logger):
        self.logger = logger

    async def send_welcome_email(self, user: User) -> bool:
        self.logger.info(f"Sending welcome email to {user.email}")
        # Simulate async email sending
        await asyncio.sleep(0.1)
        print(f"📧 Welcome email sent to {user.name} at {user.email}")
        return True


class ConsoleLogger:
    """Simple console logger."""

    def info(self, message: str) -> None:
        print(f"INFO: {message}")

    def error(self, message: str) -> None:
        print(f"ERROR: {message}")


# Database connection with cleanup support
class DatabaseConnection:
    """Mock database connection with async cleanup."""

    def __init__(self):
        self.connected = False
        self.connection_pool = None

    async def connect(self) -> None:
        await asyncio.sleep(0.1)  # Simulate connection time
        self.connected = True
        self.connection_pool = "mock_pool"
        print("Database connected")

    async def aclose(self) -> None:
        """Async cleanup implementation."""
        if self.connected:
            self.connected = False
            self.connection_pool = None
            print("Database connection closed")


# Business services using auto-registration
class UserService(metaclass=Injectable):
    """User service with dependency injection via metaclass."""

    __injectable__ = True
    __token_name__ = "user_service"
    __scope__ = Scope.SINGLETON

    def __init__(
        self,
        repository: InMemoryUserRepository,
        email: MockEmailService,
        logger: ConsoleLogger,
    ):
        self.repository = repository
        self.email_service = email
        self.logger = logger

    async def create_user(self, user_data: CreateUserRequest) -> User:
        """Create a new user with welcome email."""
        self.logger.info(f"Creating user: {user_data.name}")

        user = User(name=user_data.name, email=user_data.email)

        try:
            created_user = await self.repository.create_user(user)
            await self.email_service.send_welcome_email(created_user)

            self.logger.info(f"User created successfully: {created_user.id}")
            return created_user

        except Exception as e:
            self.logger.error(f"Failed to create user: {e}")
            raise

    async def get_user(self, user_id: int) -> User:
        """Get user by ID."""
        user = await self.repository.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def get_all_users(self) -> List[User]:
        """Get all users."""
        return await self.repository.get_all_users()


# Global container
container = Container()


def setup_dependencies():
    """Setup dependency injection container."""
    # Define tokens
    logger_token = Token[Logger]("logger", protocol=Logger)
    db_token = Token[DatabaseConnection]("database", expected_type=DatabaseConnection)
    user_repo_token = Token[UserRepository]("user_repository", protocol=UserRepository)
    email_service_token = Token[EmailService]("email_service", protocol=EmailService)

    # Register implementations
    container.register(logger_token, ConsoleLogger, Scope.SINGLETON)
    container.register(db_token, DatabaseConnection, Scope.SINGLETON)
    container.register(user_repo_token, InMemoryUserRepository, Scope.SINGLETON)

    # Register email service with dependency
    def create_email_service() -> MockEmailService:
        logger = container.resolve_protocol(Logger)
        return MockEmailService(logger)

    container.register(email_service_token, create_email_service, Scope.SINGLETON)

    # Initialize database connection
    async def init_database():
        db = container.get(db_token)
        await db.connect()

    return init_database


# FastAPI dependency injection bridge
def get_container() -> Container:
    """FastAPI dependency to get the container."""
    return container


def get_user_service(container: Container = Depends(get_container)) -> UserService:
    """FastAPI dependency to get user service."""
    # Get auto-registered service
    user_service_token = Injectable.get_registry()[UserService]
    return container.get(user_service_token)


# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with proper cleanup."""
    print("Starting up...")

    # Setup dependencies and initialize
    init_db = setup_dependencies()
    await init_db()

    yield

    print("Shutting down...")
    # Clean up all resources
    await container.dispose()


# Create FastAPI app
app = FastAPI(
    title="Injx FastAPI Example",
    description="Demonstration of injx dependency injection with FastAPI",
    lifespan=lifespan,
)


# API routes
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Injx FastAPI Example is running!"}


@app.post("/users", response_model=User)
async def create_user(
    user_data: CreateUserRequest, user_service: UserService = Depends(get_user_service)
) -> User:
    """Create a new user."""
    return await user_service.create_user(user_data)


@app.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: int, user_service: UserService = Depends(get_user_service)
) -> User:
    """Get user by ID."""
    return await user_service.get_user(user_id)


@app.get("/users", response_model=List[User])
async def get_all_users(
    user_service: UserService = Depends(get_user_service),
) -> List[User]:
    """Get all users."""
    return await user_service.get_all_users()


@app.get("/health")
async def health_check(container: Container = Depends(get_container)):
    """Health check with container status."""
    user_service_token = Injectable.get_registry()[UserService]
    is_registered = container.is_registered(user_service_token)

    return {
        "status": "healthy",
        "services_registered": len(container._providers),
        "user_service_registered": is_registered,
    }


# Manual testing function
async def test_manually():
    """Test the application manually without FastAPI server."""
    print("=== FastAPI Integration Test ===\n")

    # Setup
    init_db = setup_dependencies()
    await init_db()

    # Get user service
    user_service_token = Injectable.get_registry()[UserService]
    user_service = container.get(user_service_token)

    # Test user creation
    user_data = CreateUserRequest(name="Alice", email="alice@example.com")
    user1 = await user_service.create_user(user_data)
    print(f"Created user: {user1}")

    # Test user retrieval
    retrieved_user = await user_service.get_user(user1.id)
    print(f"Retrieved user: {retrieved_user}")

    # Test all users
    all_users = await user_service.get_all_users()
    print(f"All users: {all_users}")

    # Cleanup
    await container.dispose()
    print("Test completed and cleaned up")


if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        print("To run the FastAPI server:")
        print("uvicorn fastapi_app:app --reload")
        print("\nRunning manual test:")

    asyncio.run(test_manually())
