# Testing with Injx

This guide covers comprehensive testing strategies when using Injx for dependency injection, including mocking, test isolation, and async testing patterns.

## Overview

Injx makes testing easier by:

- **Type-safe mocking** with protocol-based interfaces
- **Dependency overrides** for isolated testing
- **Request/session scoped** test isolation
- **Async testing support** with proper cleanup
- **Zero test pollution** between test cases

## Basic Testing Pattern

### Test Structure

```
import pytest
from unittest.mock import Mock, AsyncMock
from injx import Container, Token, Scope

class TestUserService:
    def setup_method(self):
        """Setup for each test method."""
        # Fresh container for each test
        self.container = Container()

        # Define tokens
        self.db_token = Token[Database]("database", scope=Scope.SINGLETON)
        self.email_token = Token[EmailService]("email_service", scope=Scope.SINGLETON)
        self.logger_token = Token[Logger]("logger", scope=Scope.SINGLETON)
        self.user_service_token = Token[UserService]("user_service")

        # Register production implementations
        self.container.register(self.db_token, PostgreSQLDatabase)
        self.container.register(self.email_token, SMTPEmailService)
        self.container.register(self.logger_token, ConsoleLogger)
        self.container.register(
            self.user_service_token,
            lambda: UserService(
                db=self.container.get(self.db_token),
                email=self.container.get(self.email_token),
                logger=self.container.get(self.logger_token)
            )
        )

    def teardown_method(self):
        """Cleanup after each test."""
        self.container.clear_overrides()
```

### Type-Safe Mocking

```
from typing import Protocol

class Database(Protocol):
    def create_user(self, email: str, name: str) -> dict[str, str]: ...
    def get_user(self, user_id: int) -> dict[str, str] | None: ...
    def update_user(self, user_id: int, data: dict[str, str]) -> dict[str, str]: ...

class EmailService(Protocol):
    def send_welcome_email(self, email: str) -> bool: ...
    def send_notification(self, email: str, subject: str, body: str) -> bool: ...

def test_create_user_success(self):
    """Test successful user creation with type-safe mocks."""
    # Create type-safe mocks
    mock_db = Mock(spec=Database)
    mock_email = Mock(spec=EmailService)
    mock_logger = Mock(spec=Logger)

    # Configure mock behavior
    mock_db.create_user.return_value = {
        "id": 1, 
        "email": "alice@example.com", 
        "name": "Alice"
    }
    mock_email.send_welcome_email.return_value = True

    # Override dependencies for this test
    self.container.override(self.db_token, mock_db)
    self.container.override(self.email_token, mock_email)
    self.container.override(self.logger_token, mock_logger)

    # Get service with mocked dependencies
    user_service = self.container.get(self.user_service_token)

    # Execute test
    result = user_service.create_user("alice@example.com", "Alice")

    # Verify behavior
    assert result["id"] == 1
    assert result["name"] == "Alice"

    # Verify interactions
    mock_db.create_user.assert_called_once_with("alice@example.com", "Alice")
    mock_email.send_welcome_email.assert_called_once_with("alice@example.com")
    mock_logger.info.assert_called()
```

## Advanced Testing Patterns

### Base Test Class

Create a reusable base class for DI-enabled tests:

```
import pytest
from unittest.mock import Mock
from injx import Container, Token

class DITestCase:
    """Base class for dependency injection tests."""

    def setup_method(self):
        """Setup fresh container for each test."""
        self.container = Container()
        self.mocks: dict[str, Mock] = {}
        self._original_registrations: dict[Token[object], object] = {}

    def mock_service(self, token: Token[T], **mock_kwargs) -> Mock:
        """Create and register a type-safe mock for a token."""
        mock = Mock(spec=token.type_, **mock_kwargs)
        self.container.override(token, mock)
        self.mocks[token.name] = mock
        return mock

    def register_real_service(self, token: Token[T], provider: type[T] | Callable[[], T]) -> None:
        """Register a real service implementation."""
        self.container.register(token, provider)
        self._original_registrations[token] = provider

    def get_mock(self, token_name: str) -> Mock:
        """Get a previously created mock by token name."""
        return self.mocks[token_name]

    def verify_no_unexpected_calls(self) -> None:
        """Verify no mocks received unexpected calls."""
        for name, mock in self.mocks.items():
            # Reset mock to clear any expected calls
            # This is useful for verifying clean state
            pass

    def teardown_method(self):
        """Clean up after each test."""
        self.container.clear_overrides()
        self.mocks.clear()
        self._original_registrations.clear()

# Usage example
class TestUserService(DITestCase):
    def setup_method(self):
        super().setup_method()

        # Define tokens
        self.DB_TOKEN = Token[Database]("database", scope=Scope.SINGLETON)
        self.EMAIL_TOKEN = Token[EmailService]("email_service", scope=Scope.SINGLETON)
        self.USER_SERVICE_TOKEN = Token[UserService]("user_service")

        # Register real service implementations
        self.register_real_service(self.DB_TOKEN, PostgreSQLDatabase)
        self.register_real_service(self.EMAIL_TOKEN, SMTPEmailService)
        self.register_real_service(
            self.USER_SERVICE_TOKEN,
            lambda: UserService(
                db=self.container.get(self.DB_TOKEN),
                email=self.container.get(self.EMAIL_TOKEN)
            )
        )

    def test_user_creation_flow(self):
        """Test complete user creation with selective mocking."""
        # Mock only what we need to control
        mock_db = self.mock_service(self.DB_TOKEN)
        mock_email = self.mock_service(self.EMAIL_TOKEN)

        # Configure expected behavior
        mock_db.create_user.return_value = {"id": 123, "name": "Alice", "email": "alice@example.com"}
        mock_email.send_welcome_email.return_value = True

        # Execute test
        service = self.container.get(self.USER_SERVICE_TOKEN)
        result = service.create_user("alice@example.com", "Alice")

        # Verify results and interactions
        assert result["id"] == 123
        mock_db.create_user.assert_called_once()
        mock_email.send_welcome_email.assert_called_once()
```

### Parametrized Testing

```
import pytest

class TestUserValidation(DITestCase):
    def setup_method(self):
        super().setup_method()
        self.VALIDATOR_TOKEN = Token[UserValidator]("validator")
        self.register_real_service(self.VALIDATOR_TOKEN, EmailUserValidator)

    @pytest.mark.parametrize("email,expected", [
        ("valid@example.com", True),
        ("invalid-email", False),
        ("", False),
        ("user@domain.co.uk", True),
        ("user+tag@example.com", True),
    ])
    def test_email_validation(self, email: str, expected: bool):
        """Test email validation with multiple cases."""
        validator = self.container.get(self.VALIDATOR_TOKEN)
        result = validator.is_valid_email(email)
        assert result == expected

    @pytest.mark.parametrize("user_data,should_raise", [
        ({"email": "valid@example.com", "name": "Alice"}, False),
        ({"email": "invalid", "name": "Bob"}, True),
        ({"name": "Charlie"}, True),  # Missing email
        ({"email": "test@example.com"}, True),  # Missing name
    ])
    def test_user_data_validation(self, user_data: dict[str, str], should_raise: bool):
        """Test user data validation with various inputs."""
        validator = self.container.get(self.VALIDATOR_TOKEN)

        if should_raise:
            with pytest.raises(ValidationError):
                validator.validate_user_data(user_data)
        else:
            # Should not raise
            validator.validate_user_data(user_data)
```

## Async Testing

### Async Service Testing

```
import asyncio
import pytest
from unittest.mock import AsyncMock

class TestAsyncUserService(DITestCase):
    def setup_method(self):
        super().setup_method()

        # Define async service tokens
        self.ASYNC_DB_TOKEN = Token[AsyncDatabase]("async_db", scope=Scope.SINGLETON)
        self.ASYNC_EMAIL_TOKEN = Token[AsyncEmailService]("async_email", scope=Scope.SINGLETON)
        self.ASYNC_USER_SERVICE_TOKEN = Token[AsyncUserService]("async_user_service")

        # Register async services
        self.register_real_service(self.ASYNC_DB_TOKEN, AsyncPostgreSQLDatabase)
        self.register_real_service(self.ASYNC_EMAIL_TOKEN, AsyncSMTPEmailService)
        self.register_real_service(
            self.ASYNC_USER_SERVICE_TOKEN,
            lambda: AsyncUserService(
                db=self.container.get(self.ASYNC_DB_TOKEN),
                email=self.container.get(self.ASYNC_EMAIL_TOKEN)
            )
        )

    @pytest.mark.asyncio
    async def test_async_user_creation(self):
        """Test async user service with async mocks."""
        # Create async mocks
        mock_async_db = AsyncMock(spec=AsyncDatabase)
        mock_async_email = AsyncMock(spec=AsyncEmailService)

        # Configure async mock behavior
        mock_async_db.create_user.return_value = {
            "id": 1, 
            "name": "Alice", 
            "email": "alice@example.com"
        }
        mock_async_email.send_welcome_email.return_value = True

        # Override with async mocks
        self.container.override(self.ASYNC_DB_TOKEN, mock_async_db)
        self.container.override(self.ASYNC_EMAIL_TOKEN, mock_async_email)

        # Test async service
        service = self.container.get(self.ASYNC_USER_SERVICE_TOKEN)
        result = await service.create_user("alice@example.com", "Alice")

        # Verify async interactions
        assert result["id"] == 1
        mock_async_db.create_user.assert_called_once_with("alice@example.com", "Alice")
        mock_async_email.send_welcome_email.assert_called_once_with("alice@example.com")

    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """Test error handling in async services."""
        mock_async_db = AsyncMock(spec=AsyncDatabase)
        mock_async_email = AsyncMock(spec=AsyncEmailService)

        # Configure mock to raise exception
        mock_async_db.create_user.side_effect = DatabaseConnectionError("Connection failed")

        self.container.override(self.ASYNC_DB_TOKEN, mock_async_db)
        self.container.override(self.ASYNC_EMAIL_TOKEN, mock_async_email)

        service = self.container.get(self.ASYNC_USER_SERVICE_TOKEN)

        # Verify exception propagation
        with pytest.raises(DatabaseConnectionError):
            await service.create_user("alice@example.com", "Alice")

        # Verify email was not sent due to database error
        mock_async_email.send_welcome_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_async_operations(self):
        """Test concurrent async operations with proper isolation."""
        mock_async_db = AsyncMock(spec=AsyncDatabase)
        self.container.override(self.ASYNC_DB_TOKEN, mock_async_db)

        # Configure mock for concurrent calls
        mock_async_db.get_user.side_effect = lambda user_id: {
            "id": user_id, 
            "name": f"User{user_id}"
        }

        service = self.container.get(self.ASYNC_USER_SERVICE_TOKEN)

        # Execute concurrent operations
        tasks = [
            service.get_user(i) 
            for i in range(1, 11)
        ]
        results = await asyncio.gather(*tasks)

        # Verify all operations completed successfully
        assert len(results) == 10
        for i, result in enumerate(results, 1):
            assert result["id"] == i
            assert result["name"] == f"User{i}"

        # Verify all calls were made
        assert mock_async_db.get_user.call_count == 10
```

### Resource Cleanup Testing

```
@pytest.mark.asyncio
async def test_async_resource_cleanup(self):
    """Test proper cleanup of async resources."""
    cleanup_called = False

    class MockAsyncResource:
        async def aclose(self) -> None:
            nonlocal cleanup_called
            cleanup_called = True

    # Register resource with cleanup
    resource_token = Token[MockAsyncResource]("resource", scope=Scope.SINGLETON)
    self.container.register(resource_token, MockAsyncResource)

    # Use resource
    resource = await self.container.aget(resource_token)
    assert not cleanup_called

    # Cleanup should be called
    await self.container.aclose()
    assert cleanup_called
```

## Request/Session Scope Testing

### Request Scope Isolation

```
def test_request_scope_isolation(self):
    """Test that request-scoped dependencies are isolated between requests."""
    request_service_token = Token[RequestService]("request_service", scope=Scope.REQUEST)

    # Mock that tracks instance creation
    creation_count = 0

    def create_request_service() -> RequestService:
        nonlocal creation_count
        creation_count += 1
        return RequestService(id=creation_count)

    self.container.register(request_service_token, create_request_service)

    # Request 1
    with self.container.request_scope():
        service1a = self.container.get(request_service_token)
        service1b = self.container.get(request_service_token)

        # Same instance within request scope
        assert service1a is service1b
        assert service1a.id == 1
        assert creation_count == 1

    # Request 2
    with self.container.request_scope():
        service2 = self.container.get(request_service_token)

        # Different instance in new request scope
        assert service1a is not service2
        assert service2.id == 2
        assert creation_count == 2

def test_session_scope_persistence(self):
    """Test that session-scoped dependencies persist across requests."""
    session_service_token = Token[SessionService]("session_service", scope=Scope.SESSION)

    creation_count = 0

    def create_session_service() -> SessionService:
        nonlocal creation_count
        creation_count += 1
        return SessionService(id=creation_count)

    self.container.register(session_service_token, create_session_service)

    # Session with multiple requests
    with self.container.session_scope():
        # Request 1
        with self.container.request_scope():
            service1 = self.container.get(session_service_token)
            assert service1.id == 1
            assert creation_count == 1

        # Request 2 - same session service
        with self.container.request_scope():
            service2 = self.container.get(session_service_token)
            assert service1 is service2
            assert service2.id == 1
            assert creation_count == 1  # No new creation
```

## Integration Testing

### End-to-End Testing

```
class TestUserRegistrationFlow(DITestCase):
    """End-to-end testing of user registration flow."""

    def setup_method(self):
        super().setup_method()

        # Setup complete service stack
        self.setup_database_stack()
        self.setup_email_stack()
        self.setup_user_services()

    def setup_database_stack(self):
        """Setup database-related services."""
        self.DB_TOKEN = Token[Database]("database", scope=Scope.SINGLETON)
        self.USER_REPO_TOKEN = Token[UserRepository]("user_repo", scope=Scope.SINGLETON)

        self.register_real_service(self.DB_TOKEN, InMemoryDatabase)  # Use in-memory for tests
        self.register_real_service(
            self.USER_REPO_TOKEN,
            lambda: UserRepository(db=self.container.get(self.DB_TOKEN))
        )

    def setup_email_stack(self):
        """Setup email-related services."""
        self.EMAIL_TOKEN = Token[EmailService]("email_service", scope=Scope.SINGLETON)
        self.register_real_service(self.EMAIL_TOKEN, MockEmailService)  # Mock for tests

    def setup_user_services(self):
        """Setup user service layer."""
        self.USER_SERVICE_TOKEN = Token[UserService]("user_service", scope=Scope.SINGLETON)
        self.REGISTRATION_SERVICE_TOKEN = Token[RegistrationService]("registration_service")

        self.register_real_service(
            self.USER_SERVICE_TOKEN,
            lambda: UserService(
                user_repo=self.container.get(self.USER_REPO_TOKEN),
                email_service=self.container.get(self.EMAIL_TOKEN)
            )
        )

        self.register_real_service(
            self.REGISTRATION_SERVICE_TOKEN,
            lambda: RegistrationService(
                user_service=self.container.get(self.USER_SERVICE_TOKEN)
            )
        )

    def test_complete_user_registration(self):
        """Test complete user registration flow end-to-end."""
        # Get the registration service
        registration_service = self.container.get(self.REGISTRATION_SERVICE_TOKEN)

        # Execute registration
        user_data = {
            "email": "alice@example.com",
            "name": "Alice Smith",
            "password": "secure_password"
        }

        result = registration_service.register_user(user_data)

        # Verify user was created
        assert "id" in result
        assert result["email"] == "alice@example.com"
        assert result["name"] == "Alice Smith"

        # Verify user exists in database
        db = self.container.get(self.DB_TOKEN)
        stored_user = db.get_user(result["id"])
        assert stored_user is not None
        assert stored_user["email"] == "alice@example.com"

        # Verify welcome email was sent
        email_service = self.container.get(self.EMAIL_TOKEN)
        assert email_service.last_sent_email["to"] == "alice@example.com"
        assert "welcome" in email_service.last_sent_email["subject"].lower()

    def test_duplicate_email_registration(self):
        """Test that duplicate email registration is handled properly."""
        registration_service = self.container.get(self.REGISTRATION_SERVICE_TOKEN)

        user_data = {
            "email": "duplicate@example.com",
            "name": "First User",
            "password": "password1"
        }

        # First registration should succeed
        result1 = registration_service.register_user(user_data)
        assert "id" in result1

        # Second registration with same email should fail
        user_data["name"] = "Second User"
        user_data["password"] = "password2"

        with pytest.raises(DuplicateEmailError):
            registration_service.register_user(user_data)
```

## Test Fixtures and Utilities

### Pytest Fixtures

```
import pytest
from injx import Container

@pytest.fixture
def container() -> Container:
    """Provide a fresh container for each test."""
    return Container()

@pytest.fixture
def user_service_stack(container: Container) -> dict[str, Token]:
    """Setup complete user service stack."""
    # Define tokens
    tokens = {
        "db": Token[Database]("database", scope=Scope.SINGLETON),
        "email": Token[EmailService]("email_service", scope=Scope.SINGLETON),
        "logger": Token[Logger]("logger", scope=Scope.SINGLETON),
        "user_service": Token[UserService]("user_service")
    }

    # Register services
    container.register(tokens["db"], InMemoryDatabase)
    container.register(tokens["email"], MockEmailService)
    container.register(tokens["logger"], TestLogger)
    container.register(
        tokens["user_service"],
        lambda: UserService(
            db=container.get(tokens["db"]),
            email=container.get(tokens["email"]),
            logger=container.get(tokens["logger"])
        )
    )

    return tokens

@pytest.fixture
async def async_container() -> Container:
    """Provide container with async cleanup."""
    container = Container()
    yield container
    await container.aclose()

# Usage in tests
def test_user_service_with_fixture(user_service_stack: dict[str, Token], container: Container):
    """Test using fixture-provided service stack."""
    user_service = container.get(user_service_stack["user_service"])
    result = user_service.create_user("test@example.com", "Test User")
    assert result["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_async_service_with_fixture(async_container: Container):
    """Test async service with fixture cleanup."""
    # Setup async service
    async_token = Token[AsyncService]("async_service")
    async_container.register(async_token, AsyncServiceImpl)

    # Use service
    service = await async_container.aget(async_token)
    result = await service.process_data("test")

    assert result == "processed: test"
    # Cleanup handled by fixture
```

## Best Practices

### 1. Test Isolation

```
# ✅ Good - Fresh container per test
class TestService:
    def setup_method(self):
        self.container = Container()  # Fresh instance

    def teardown_method(self):
        self.container.clear_overrides()

# ❌ Bad - Shared container between tests
class TestService:
    container = Container()  # Shared - tests can interfere
```

### 2. Mock Scope

```
# ✅ Good - Mock only what you need to control
def test_user_service(self):
    mock_db = Mock(spec=Database)
    self.container.override(DB_TOKEN, mock_db)
    # Use real email service if not relevant to test

# ❌ Bad - Over-mocking
def test_user_service(self):
    mock_db = Mock(spec=Database)
    mock_email = Mock(spec=EmailService)
    mock_logger = Mock(spec=Logger)
    mock_validator = Mock(spec=Validator)
    # Too many mocks make tests brittle
```

### 3. Verification Focus

```
# ✅ Good - Verify behavior that matters
def test_user_creation(self):
    # ... setup ...
    user_service.create_user("test@example.com", "Test")

    # Verify the important interactions
    mock_db.create_user.assert_called_once()
    mock_email.send_welcome_email.assert_called_once()

# ❌ Bad - Over-verification
def test_user_creation(self):
    # ... setup ...
    user_service.create_user("test@example.com", "Test")

    # Too detailed - tests become brittle
    mock_db.create_user.assert_called_once_with("test@example.com", "Test")
    mock_email.send_welcome_email.assert_called_once_with("test@example.com")
    mock_logger.info.assert_called_with("Creating user: Test")
    # ... many more detailed assertions
```

### 4. Async Testing

```
# ✅ Good - Proper async test setup
@pytest.mark.asyncio
async def test_async_service():
    mock_async_db = AsyncMock(spec=AsyncDatabase)
    # Test async behavior properly

# ❌ Bad - Missing async markers
def test_async_service():  # Missing @pytest.mark.asyncio
    # Will fail at runtime
```

This comprehensive testing guide ensures your Injx-based applications are thoroughly tested with type safety and proper isolation.
