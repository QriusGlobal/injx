# Getting Started

This guide covers the fundamentals of using Injx for type-safe dependency injection in Python 3.13+.

## Installation

```
# UV (recommended)
uv add injx

# Or pip
pip install injx
```

## Core Concepts

### Token

A typed identifier that represents a dependency. Tokens are immutable and use pre-computed hashes for O(1) lookups.

```
from injx import Token
from typing import Protocol

class Logger(Protocol):
    def info(self, message: str) -> None: ...

# Create a token for the Logger protocol
LOGGER = Token[Logger]("logger", scope=Scope.SINGLETON)
```

### Container

The central registry that manages dependencies and their lifecycles.

```
from injx import Container

container = Container()
```

### Provider

A function or class that creates instances of dependencies.

```
class ConsoleLogger:
    def info(self, message: str) -> None:
        print(f"INFO: {message}")

# Register the provider
container.register(LOGGER, ConsoleLogger)
```

### Scope

Defines the lifecycle of dependencies:

- **SINGLETON**: One instance per container (shared across all requests)
- **REQUEST**: One instance per request context
- **SESSION**: One instance per session context
- **TRANSIENT**: New instance every time

## Basic Example

Here's a complete example showing the fundamental pattern:

```
from typing import Protocol
from injx import Container, Token, Scope

# Define interfaces using protocols
class Logger(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...

class Database(Protocol):
    def query(self, sql: str) -> list[dict[str, str]]: ...

# Implement the interfaces
class ConsoleLogger:
    def info(self, message: str) -> None:
        print(f"INFO: {message}")

    def error(self, message: str) -> None:
        print(f"ERROR: {message}")

class PostgreSQLDatabase:
    def query(self, sql: str) -> list[dict[str, str]]:
        # Mock implementation
        return [{"id": "1", "name": "Alice"}]

# Create container and tokens
container = Container()
LOGGER = Token[Logger]("logger", scope=Scope.SINGLETON)
DATABASE = Token[Database]("database", scope=Scope.SINGLETON)

# Register providers
container.register(LOGGER, ConsoleLogger)
container.register(DATABASE, PostgreSQLDatabase)

# Resolve dependencies manually
logger = container.get(LOGGER)
db = container.get(DATABASE)

# Use the dependencies
logger.info("Application started")
users = db.query("SELECT * FROM users")
logger.info(f"Found {len(users)} users")
```

## Type-Safe Injection Patterns

Injx provides multiple ways to inject dependencies. Here's the recommended approach:

### ⭐ Recommended: `@inject` with Type Annotations

This is the cleanest and most type-safe approach:

```
from injx import inject, set_default_container

# Set up a default container (optional)
set_default_container(container)

@inject  # Uses default container
def process_users(logger: Logger, db: Database) -> None:
    """Dependencies are automatically injected based on type annotations."""
    logger.info("Processing users")
    users = db.query("SELECT * FROM users")

    for user in users:
        logger.info(f"Processing user: {user['name']}")

# Call without providing dependencies - they're auto-injected
process_users()
```

### Mixed Parameters

You can mix injected dependencies with regular parameters:

```
@inject
def process_user_by_id(
    user_id: int,           # Regular parameter
    logger: Logger,         # Injected dependency
    db: Database           # Injected dependency
) -> dict[str, str] | None:
    logger.info(f"Looking up user {user_id}")
    users = db.query(f"SELECT * FROM users WHERE id = '{user_id}'")
    return users[0] if users else None

# Call with only regular parameters
user = process_user_by_id(user_id=123)
```

### Async Support

Injx fully supports async functions and providers:

```
import asyncio
from typing import Protocol

class AsyncDatabase(Protocol):
    async def connect(self) -> None: ...
    async def query(self, sql: str) -> list[dict[str, str]]: ...
    async def aclose(self) -> None: ...

class AsyncPostgreSQLDatabase:
    def __init__(self) -> None:
        self.connected = False

    async def connect(self) -> None:
        print("Connecting to async database...")
        await asyncio.sleep(0.1)  # Simulate connection time
        self.connected = True

    async def query(self, sql: str) -> list[dict[str, str]]:
        if not self.connected:
            await self.connect()
        return [{"id": "1", "name": "Alice"}]

    async def aclose(self) -> None:
        print("Closing async database...")
        self.connected = False

# Register async provider
ASYNC_DB = Token[AsyncDatabase]("async_db", scope=Scope.SINGLETON)

async def create_async_db() -> AsyncDatabase:
    db = AsyncPostgreSQLDatabase()
    await db.connect()
    return db

container.register(ASYNC_DB, create_async_db)

# Async injection
@inject
async def process_users_async(
    logger: Logger,           # Sync dependency
    db: AsyncDatabase        # Async dependency  
) -> None:
    logger.info("Processing users asynchronously")
    users = await db.query("SELECT * FROM users")

    for user in users:
        logger.info(f"Processing user: {user['name']}")

# Usage
async def main() -> None:
    await process_users_async()
    await container.aclose()  # Cleanup async resources

asyncio.run(main())
```

## Common Anti-Patterns to Avoid

### ❌ Wrong: `Inject[T] = None`

```
# ❌ DON'T DO THIS - Breaks type safety
from injx import Inject

def bad_handler(logger: Inject[Logger] = None) -> None:
    # This breaks static type checking and is confusing
    pass
```

### ❌ Wrong: Unnecessary Inject[T] Markers

```
# ❌ UNNECESSARY - Just use plain type annotations
def confusing_handler(logger: Inject[Logger]) -> None:
    # This works but is unnecessarily complex
    pass
```

### ✅ Correct: Simple Type Annotations

```
# ✅ CLEAN AND TYPE-SAFE
@inject
def good_handler(logger: Logger) -> None:
    logger.info("This is the recommended pattern")
```

## Scoped Dependencies

Injx supports different dependency scopes for various use cases:

### Singleton Scope

One instance shared across the entire application:

```
CONFIG = Token[Configuration]("config", scope=Scope.SINGLETON)

class Configuration:
    def __init__(self) -> None:
        self.database_url = "postgresql://localhost/myapp"
        self.debug = True

container.register(CONFIG, Configuration)

# Same instance returned every time
config1 = container.get(CONFIG)
config2 = container.get(CONFIG)
assert config1 is config2
```

### Request Scope

One instance per request context (useful for web applications):

```
USER = Token[User]("current_user", scope=Scope.REQUEST)

def get_current_user() -> User:
    # This would typically extract user from request context
    return User(id=123, name="Alice")

container.register(USER, get_current_user)

# Different instances in different request scopes
with container.request_scope():
    user1 = container.get(USER)
    user2 = container.get(USER)
    assert user1 is user2  # Same instance within scope

with container.request_scope():
    user3 = container.get(USER)
    assert user1 is not user3  # Different instance in new scope
```

## Resource Cleanup

Injx provides automatic resource cleanup using context managers:

### Sync Resource Cleanup

```
from contextlib import contextmanager
from typing import Generator

@contextmanager 
def database_connection() -> Generator[Database, None, None]:
    print("Opening database connection")
    db = PostgreSQLDatabase()
    try:
        yield db
    finally:
        print("Closing database connection")
        db.close()

container.register_context_sync(DATABASE, database_connection)

# Resources are automatically cleaned up
with container:
    db = container.get(DATABASE)
    # Use database
# Database connection closed automatically
```

### Async Resource Cleanup

```
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def async_database_connection() -> AsyncGenerator[AsyncDatabase, None]:
    print("Opening async database connection")
    db = AsyncPostgreSQLDatabase()
    await db.connect()
    try:
        yield db
    finally:
        print("Closing async database connection")
        await db.aclose()

container.register_context_async(ASYNC_DB, async_database_connection)

# Async cleanup
async def main() -> None:
    db = await container.aget(ASYNC_DB)
    # Use database
    await container.aclose()  # Proper async cleanup

asyncio.run(main())
```

### Circuit Breaker for Mixed Cleanup

Injx prevents resource leaks by raising `AsyncCleanupRequiredError` when you try to use sync cleanup on async-only resources:

```
from injx import AsyncCleanupRequiredError

# Register an async-only resource
container.register_context_async(ASYNC_DB, async_database_connection)

try:
    # This will raise AsyncCleanupRequiredError
    with container:
        db = container.get(ASYNC_DB)  
except AsyncCleanupRequiredError as e:
    print(f"Use async cleanup: {e}")

# Correct way:
async def main() -> None:
    async with container.async_context():
        db = await container.aget(ASYNC_DB)
        # Use database
    # Automatic async cleanup

asyncio.run(main())
```

## TokenFactory for Convenience

The `TokenFactory` provides convenient methods for creating tokens:

```
from injx import TokenFactory

factory = TokenFactory()

# Convenient creation methods
LOGGER = factory.singleton("logger", Logger)
CACHE = factory.request("cache", CacheService)
CONFIG = factory.session("config", Configuration)
TEMP_FILE = factory.transient("temp_file", TempFile)

# With qualifiers for multiple instances
PRIMARY_DB = factory.qualified("primary", Database, Scope.SINGLETON)
SECONDARY_DB = factory.qualified("secondary", Database, Scope.SINGLETON)
```

## Next Steps

Now that you understand the basics, explore these advanced topics:

- **[Type Safety](../type-safety/)** - Learn about PEP 561 compliance and static type checking
- **[Usage](../usage/)** - Framework integration and real-world patterns
- **[Advanced](../advanced/)** - Complex patterns and performance optimization
- **[Testing](../testing/)** - Testing strategies with dependency overrides
- **[API Reference](../api/)** - Complete API documentation

## Quick Reference

### Essential Imports

```
from typing import Protocol
from injx import Container, Token, Scope, inject
```

### Basic Pattern

```
# 1. Define interface
class Service(Protocol):
    def method(self) -> str: ...

# 2. Create implementation  
class ServiceImpl:
    def method(self) -> str:
        return "result"

# 3. Register with container
container = Container()
SERVICE = Token[Service]("service", scope=Scope.SINGLETON)
container.register(SERVICE, ServiceImpl)

# 4. Use with injection
@inject
def handler(service: Service) -> None:
    result = service.method()
```

This covers the fundamentals of Injx. The key is to use type annotations with the `@inject` decorator for clean, type-safe dependency injection.
