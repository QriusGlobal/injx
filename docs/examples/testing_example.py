"""Testing with Injx - Type-Safe Mocking and Dependency Overrides

This example demonstrates:
- Using pytest fixtures with proper type annotations
- Mock objects with autospec=True for type safety
- Container overrides without patching
- Testing isolation with dependency injection

Run the tests:
    pytest testing_example.py -v
"""

import pytest
from typing import Protocol, Any, Optional, Generator
from unittest.mock import Mock, MagicMock, call
from injx import Container, Token, inject, Scope, Dependencies


# 1. Service protocols (same as in basic_example.py)
class Database(Protocol):
    """Database service protocol."""

    def get_user(self, user_id: int) -> dict[str, Any]:
        ...

    def save_user(self, user: dict[str, Any]) -> None:
        ...

    def delete_user(self, user_id: int) -> bool:
        ...


class HTTPClient(Protocol):
    """HTTP client protocol."""

    def get(self, url: str) -> dict[str, Any]:
        ...

    def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        ...


class Cache(Protocol):
    """Cache service protocol."""

    def get(self, key: str) -> Optional[dict[str, Any]]:
        ...

    def set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> None:
        ...

    def delete(self, key: str) -> bool:
        ...


class EmailService(Protocol):
    """Email service protocol."""

    def send(self, to: str, subject: str, body: str) -> bool:
        ...

    def send_batch(self, recipients: list[str], subject: str, body: str) -> int:
        ...


# 2. Service tokens
DB_TOKEN: Token[Database] = Token("database", Database)
HTTP_TOKEN: Token[HTTPClient] = Token("http_client", HTTPClient)
CACHE_TOKEN: Token[Cache] = Token("cache", Cache)
EMAIL_TOKEN: Token[EmailService] = Token("email", EmailService)


# 3. Business logic to test with Dependencies pattern
@inject
def get_user_profile(
    user_id: int,
    deps: Dependencies[Database, HTTPClient, Cache]
) -> dict[str, Any]:
    """Fetch user profile with caching and external enrichment."""
    # Extract services from dependencies
    db = deps[Database]
    http = deps[HTTPClient]
    cache = deps[Cache]

    # Check cache
    cache_key: str = f"profile:{user_id}"
    cached: Optional[dict[str, Any]] = cache.get(cache_key)

    if cached:
        return cached

    # Get from DB
    user: dict[str, Any] = db.get_user(user_id)

    # Enrich from external API
    enrichment: dict[str, Any] = http.get(f"https://api.example.com/profile/{user_id}")
    user["premium"] = enrichment.get("premium", False)
    user["score"] = enrichment.get("score", 0)

    # Cache result
    cache.set(cache_key, user, ttl=300)

    return user


@inject
def register_user(
    name: str,
    email: str,
    deps: Dependencies[Database, HTTPClient, EmailService]
) -> dict[str, Any]:
    """Register a new user with email validation and notification."""
    # Extract services from dependencies
    db = deps[Database]
    http = deps[HTTPClient]
    email_service = deps[EmailService]

    # Validate email
    validation: dict[str, Any] = http.post(
        "https://api.example.com/validate",
        {"email": email}
    )

    if not validation.get("valid", False):
        raise ValueError(f"Invalid email: {email}")

    # Create user
    user: dict[str, Any] = {
        "id": validation.get("user_id", 999),
        "name": name,
        "email": email,
        "status": "pending"
    }

    # Save to database
    db.save_user(user)

    # Send welcome email
    email_sent: bool = email_service.send(
        to=email,
        subject="Welcome!",
        body=f"Welcome {name}!"
    )

    if email_sent:
        user["status"] = "active"
        db.save_user(user)

    return user


@inject
def delete_user_account(
    user_id: int,
    deps: Dependencies[Database, Cache, EmailService]
) -> bool:
    """Delete user account with cleanup."""
    # Extract services from dependencies
    db = deps[Database]
    cache = deps[Cache]
    email_service = deps[EmailService]

    # Get user for email notification
    user: dict[str, Any] = db.get_user(user_id)

    # Delete from database
    deleted: bool = db.delete_user(user_id)

    if deleted:
        # Clear cache
        cache.delete(f"profile:{user_id}")

        # Send notification
        email_service.send(
            to=user["email"],
            subject="Account Deleted",
            body="Your account has been deleted."
        )

    return deleted


# 4. Pytest fixtures with type annotations
@pytest.fixture
def container() -> Container:
    """Create a fresh container for each test."""
    return Container()


@pytest.fixture
def mock_database() -> Mock:
    """Create a mock database with autospec for type safety."""
    mock_db: Mock = Mock(spec=Database, autospec=True)

    # Setup default behaviors
    mock_db.get_user.return_value = {
        "id": 1,
        "name": "Test User",
        "email": "test@example.com"
    }
    mock_db.save_user.return_value = None
    mock_db.delete_user.return_value = True

    return mock_db


@pytest.fixture
def mock_http_client() -> Mock:
    """Create a mock HTTP client with autospec."""
    mock_http: Mock = Mock(spec=HTTPClient, autospec=True)

    # Setup default behaviors
    mock_http.get.return_value = {
        "premium": True,
        "score": 100
    }
    mock_http.post.return_value = {
        "valid": True,
        "user_id": 123
    }

    return mock_http


@pytest.fixture
def mock_cache() -> Mock:
    """Create a mock cache with autospec."""
    mock_cache: Mock = Mock(spec=Cache, autospec=True)

    # Setup default behaviors
    mock_cache.get.return_value = None  # Cache miss by default
    mock_cache.set.return_value = None
    mock_cache.delete.return_value = True

    return mock_cache


@pytest.fixture
def mock_email_service() -> Mock:
    """Create a mock email service with autospec."""
    mock_email: Mock = Mock(spec=EmailService, autospec=True)

    # Setup default behaviors
    mock_email.send.return_value = True
    mock_email.send_batch.return_value = 5  # Number of emails sent

    return mock_email


@pytest.fixture
def configured_container(
    container: Container,
    mock_database: Mock,
    mock_http_client: Mock,
    mock_cache: Mock,
    mock_email_service: Mock
) -> Generator[Container, None, None]:
    """
    Configure container with all mock services.

    This fixture demonstrates the override pattern - no patching needed!
    """
    # Register mocks in container
    container.override(DB_TOKEN, mock_database)
    container.override(HTTP_TOKEN, mock_http_client)
    container.override(CACHE_TOKEN, mock_cache)
    container.override(EMAIL_TOKEN, mock_email_service)

    # Set as active container
    Container.set_active(container)

    yield container

    # Cleanup
    container.clear_overrides()
    Container.set_active(None)


# 5. Test cases with type-safe mocks
class TestUserProfile:
    """Test suite for user profile functionality."""

    def test_get_user_profile_cache_miss(
        self,
        configured_container: Container,
        mock_database: Mock,
        mock_http_client: Mock,
        mock_cache: Mock
    ) -> None:
        """Test fetching user profile when cache is empty."""
        # Arrange
        user_id: int = 42
        mock_cache.get.return_value = None  # Cache miss

        # Act
        result: dict[str, Any] = get_user_profile(user_id)

        # Assert
        assert result["id"] == 1
        assert result["name"] == "Test User"
        assert result["premium"] is True
        assert result["score"] == 100

        # Verify mock calls with proper types
        mock_cache.get.assert_called_once_with(f"profile:{user_id}")
        mock_database.get_user.assert_called_once_with(user_id)
        mock_http_client.get.assert_called_once_with(
            f"https://api.example.com/profile/{user_id}"
        )
        mock_cache.set.assert_called_once()

    def test_get_user_profile_cache_hit(
        self,
        configured_container: Container,
        mock_database: Mock,
        mock_http_client: Mock,
        mock_cache: Mock
    ) -> None:
        """Test fetching user profile when data is cached."""
        # Arrange
        cached_data: dict[str, Any] = {
            "id": 42,
            "name": "Cached User",
            "premium": False,
            "score": 50
        }
        mock_cache.get.return_value = cached_data

        # Act
        result: dict[str, Any] = get_user_profile(42)

        # Assert
        assert result == cached_data

        # Verify no DB or HTTP calls were made
        mock_database.get_user.assert_not_called()
        mock_http_client.get.assert_not_called()
        mock_cache.set.assert_not_called()


class TestUserRegistration:
    """Test suite for user registration."""

    def test_register_user_success(
        self,
        configured_container: Container,
        mock_database: Mock,
        mock_http_client: Mock,
        mock_email_service: Mock
    ) -> None:
        """Test successful user registration."""
        # Arrange
        name: str = "Alice"
        email: str = "alice@example.com"

        # Act
        result: dict[str, Any] = register_user(name, email)

        # Assert
        assert result["name"] == name
        assert result["email"] == email
        assert result["status"] == "active"

        # Verify calls
        mock_http_client.post.assert_called_once_with(
            "https://api.example.com/validate",
            {"email": email}
        )
        assert mock_database.save_user.call_count == 2  # Once for pending, once for active
        mock_email_service.send.assert_called_once()

    def test_register_user_invalid_email(
        self,
        configured_container: Container,
        mock_http_client: Mock,
        mock_database: Mock
    ) -> None:
        """Test registration with invalid email."""
        # Arrange
        mock_http_client.post.return_value = {"valid": False}

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid email"):
            register_user("Bob", "invalid@test.com")

        # Verify no user was saved
        mock_database.save_user.assert_not_called()

    def test_register_user_email_failure(
        self,
        configured_container: Container,
        mock_database: Mock,
        mock_email_service: Mock
    ) -> None:
        """Test registration when email sending fails."""
        # Arrange
        mock_email_service.send.return_value = False

        # Act
        result: dict[str, Any] = register_user("Charlie", "charlie@example.com")

        # Assert - user remains pending
        assert result["status"] == "pending"
        mock_database.save_user.assert_called_once()  # Only initial save


class TestUserDeletion:
    """Test suite for user deletion."""

    def test_delete_user_success(
        self,
        configured_container: Container,
        mock_database: Mock,
        mock_cache: Mock,
        mock_email_service: Mock
    ) -> None:
        """Test successful user deletion with cleanup."""
        # Act
        result: bool = delete_user_account(1)

        # Assert
        assert result is True

        # Verify cleanup sequence
        mock_database.get_user.assert_called_once_with(1)
        mock_database.delete_user.assert_called_once_with(1)
        mock_cache.delete.assert_called_once_with("profile:1")
        mock_email_service.send.assert_called_once()

    def test_delete_user_database_failure(
        self,
        configured_container: Container,
        mock_database: Mock,
        mock_cache: Mock,
        mock_email_service: Mock
    ) -> None:
        """Test deletion when database operation fails."""
        # Arrange
        mock_database.delete_user.return_value = False

        # Act
        result: bool = delete_user_account(1)

        # Assert
        assert result is False

        # Verify no cleanup was performed
        mock_cache.delete.assert_not_called()
        mock_email_service.send.assert_not_called()


# 6. Integration test with partial mocking
class TestIntegration:
    """Integration tests with selective mocking."""

    @pytest.fixture
    def partial_container(
        self,
        container: Container,
        mock_http_client: Mock,
        mock_email_service: Mock
    ) -> Generator[Container, None, None]:
        """Container with only external services mocked."""
        # Use real implementations for DB and Cache
        from docs.examples.basic_example import PostgresDatabase, RedisCache

        # Register real services
        container.register(DB_TOKEN, PostgresDatabase, scope=Scope.SINGLETON)
        container.register(CACHE_TOKEN, RedisCache, scope=Scope.SINGLETON)

        # Override only external services
        container.override(HTTP_TOKEN, mock_http_client)
        container.override(EMAIL_TOKEN, mock_email_service)

        Container.set_active(container)
        yield container
        Container.set_active(None)

    def test_full_flow_with_partial_mocks(
        self,
        partial_container: Container,
        mock_http_client: Mock,
        mock_email_service: Mock
    ) -> None:
        """Test complete flow with real DB/Cache but mocked external services."""
        # Register user
        user: dict[str, Any] = register_user("Integration", "test@example.com")
        assert user["status"] == "active"

        # Fetch profile (will use real cache)
        profile1: dict[str, Any] = get_user_profile(user["id"])
        profile2: dict[str, Any] = get_user_profile(user["id"])

        # Second call should hit cache (no additional HTTP call)
        assert mock_http_client.get.call_count == 1

        # Delete user
        deleted: bool = delete_user_account(user["id"])
        assert deleted is True


# 7. Parametrized tests for edge cases
class TestParametrized:
    """Parametrized tests for comprehensive coverage."""

    @pytest.mark.parametrize("user_id,expected_cache_key", [
        (1, "profile:1"),
        (999, "profile:999"),
        (0, "profile:0"),
        (-1, "profile:-1"),
    ])
    def test_cache_key_generation(
        self,
        configured_container: Container,
        mock_cache: Mock,
        user_id: int,
        expected_cache_key: str
    ) -> None:
        """Test cache key generation for different user IDs."""
        get_user_profile(user_id)
        mock_cache.get.assert_called_with(expected_cache_key)

    @pytest.mark.parametrize("email,is_valid", [
        ("valid@example.com", True),
        ("invalid@test.com", False),
        ("", False),
        ("no-at-sign.com", False),
    ])
    def test_email_validation_scenarios(
        self,
        configured_container: Container,
        mock_http_client: Mock,
        email: str,
        is_valid: bool
    ) -> None:
        """Test various email validation scenarios."""
        mock_http_client.post.return_value = {"valid": is_valid}

        if is_valid:
            result: dict[str, Any] = register_user("Test", email)
            assert result["email"] == email
        else:
            with pytest.raises(ValueError):
                register_user("Test", email)


# Run tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--color=yes"])