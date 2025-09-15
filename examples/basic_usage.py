"""Basic usage example for injx dependency injection."""

import asyncio
from typing import Protocol, runtime_checkable

from injx import Container, Injectable, Scope, Token


# Define protocols for type safety
@runtime_checkable
class Logger(Protocol):
    """Protocol for logging services."""

    def info(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...


@runtime_checkable
class Database(Protocol):
    """Protocol for database services."""

    async def connect(self) -> None: ...
    async def execute(self, query: str) -> str: ...
    async def aclose(self) -> None: ...


# Concrete implementations
class ConsoleLogger:
    """Simple console logger implementation."""

    def info(self, message: str) -> None:
        print(f"INFO: {message}")

    def error(self, message: str) -> None:
        print(f"ERROR: {message}")


class MockDatabase:
    """Mock database for demonstration."""

    def __init__(self):
        self.connected = False
        self.queries = []

    async def connect(self) -> None:
        await asyncio.sleep(0.1)  # Simulate connection time
        self.connected = True
        print("Database connected")

    async def execute(self, query: str) -> str:
        if not self.connected:
            raise RuntimeError("Database not connected")

        self.queries.append(query)
        await asyncio.sleep(0.01)  # Simulate query time
        return f"Result for: {query}"

    async def aclose(self) -> None:
        self.connected = False
        print("Database connection closed")


# Service using dependency injection
class UserService:
    """Service that depends on logger and database."""

    def __init__(self, logger: Logger, database: Database):
        self.logger = logger
        self.database = database

    async def create_user(self, name: str, email: str) -> str:
        self.logger.info(f"Creating user: {name}")

        try:
            await self.database.connect()
            query = f"INSERT INTO users (name, email) VALUES ('{name}', '{email}')"
            result = await self.database.execute(query)

            self.logger.info(f"User created successfully: {name}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to create user {name}: {e}")
            raise


# Auto-registration with metaclass (alternative approach)
class EmailService(metaclass=Injectable):
    """Email service with auto-registration."""

    __injectable__ = True
    __token_name__ = "email_service"
    __scope__ = Scope.SINGLETON

    def __init__(self, logger: ConsoleLogger):
        self.logger = logger

    def send_email(self, to: str, subject: str, body: str) -> bool:
        self.logger.info(f"Sending email to {to}: {subject}")
        # Simulate email sending
        print(f"📧 To: {to}")
        print(f"📧 Subject: {subject}")
        print(f"📧 Body: {body}")
        return True


async def main():
    """Demonstrate basic usage of injx container."""
    print("=== Basic Injx Usage Example ===\n")

    # Create container
    container = Container()

    # Define tokens
    logger_token = Token[Logger]("logger", protocol=Logger)
    database_token = Token[Database]("database", protocol=Database)
    user_service_token = Token[UserService]("user_service", expected_type=UserService)

    # Register providers
    container.register(logger_token, ConsoleLogger, Scope.SINGLETON)
    container.register(database_token, MockDatabase, Scope.SINGLETON)

    # Register service with dependencies
    def create_user_service() -> UserService:
        logger = container.resolve_protocol(Logger)
        database = container.resolve_protocol(Database)
        return UserService(logger, database)

    container.register(user_service_token, create_user_service, Scope.SINGLETON)

    print("1. Manual registration and resolution:")
    user_service = container.get(user_service_token)
    result = await user_service.create_user("Alice", "alice@example.com")
    print(f"Result: {result}\n")

    print("2. Using @inject decorator:")

    @container.inject
    def business_logic(logger: Logger, database: Database) -> str:
        """Function with automatic dependency injection."""
        logger.info("Executing business logic")
        return "Business logic executed"

    business_result = business_logic()
    print(f"Business result: {business_result}\n")

    print("3. Auto-registered services (metaclass):")
    # Email service was auto-registered via metaclass
    email_token = Injectable.get_registry()[EmailService]
    email_service = container.get(email_token)
    email_service.send_email("bob@example.com", "Welcome!", "Welcome to our service!")

    print("\n4. Protocol-based resolution:")
    # Resolve by protocol instead of token
    direct_logger = container.resolve_protocol(Logger)
    direct_logger.info("This logger was resolved by protocol")

    print("\n5. Testing with overrides:")

    class TestLogger:
        """Test logger for demonstration."""

        def info(self, message: str) -> None:
            print(f"TEST-INFO: {message}")

        def error(self, message: str) -> None:
            print(f"TEST-ERROR: {message}")

    # Override for testing
    container.override(logger_token, TestLogger())

    test_logger = container.get(logger_token)
    test_logger.info("This is from the test logger")

    # Clear override
    container.clear_overrides()
    normal_logger = container.get(logger_token)
    normal_logger.info("Back to normal logger")

    print("\n6. Async cleanup:")
    await container.dispose()
    print("All resources cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
