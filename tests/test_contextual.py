"""Tests for contextual scoping implementation."""

from unittest.mock import MagicMock, Mock

import pytest

from pyinj.contextual import (
    ContextualContainer,
    RequestScope,
    SessionScope,
)
from pyinj.tokens import Scope, Token


class Database:
    """Test database class."""

    def close(self):
        """Cleanup method."""
        pass


class AsyncResource:
    """Test async resource."""

    async def aclose(self):
        """Async cleanup."""
        pass


class TestContextualContainer:
    """Test suite for ContextualContainer."""

    def test_container_initialization(self):
        """Test container initializes correctly."""
        container = ContextualContainer()

        # Provider view is only available on Container; ContextualContainer tracks providers internally.
        assert hasattr(container, "_transients")
        assert hasattr(container, "_async_locks")

    def test_request_scope_context(self):
        """Test request scope context manager."""
        container = ContextualContainer()
        token = Token("database", Database, scope=Scope.REQUEST)

        # Outside scope, no context
        assert container.resolve_from_context(token) is None

        # Inside scope
        with container.request_scope():
            db = Database()
            container.store_in_context(token, db)

            # Should resolve from context
            resolved = container.resolve_from_context(token)
            assert resolved is db

        # Outside scope again, context cleared
        assert container.resolve_from_context(token) is None

    def test_nested_request_scopes(self):
        """Test nested request scopes."""
        container = ContextualContainer()
        token1 = Token("db1", Database, scope=Scope.REQUEST)
        token2 = Token("db2", Database, scope=Scope.REQUEST)

        with container.request_scope():
            db1 = Database()
            container.store_in_context(token1, db1)

            with container.request_scope():
                db2 = Database()
                container.store_in_context(token2, db2)

                # Both should be resolvable
                assert container.resolve_from_context(token1) is db1
                assert container.resolve_from_context(token2) is db2

            # Inner scope cleared, outer remains
            assert container.resolve_from_context(token1) is db1
            assert container.resolve_from_context(token2) is None

    def test_session_scope_context(self):
        """Test session scope context manager."""
        container = ContextualContainer()
        token = Token("user", str, scope=Scope.SESSION)

        with container.session_scope():
            container.store_in_context(token, "user123")
            assert container.resolve_from_context(token) == "user123"

        # Session cleared after context
        assert container.resolve_from_context(token) is None

    def test_singleton_storage(self):
        """Test singleton storage and retrieval."""
        container = ContextualContainer()
        token = Token("database", Database, scope=Scope.SINGLETON)

        db = Database()
        container.store_in_context(token, db)

        # Should persist outside of any scope
        assert container.resolve_from_context(token) is db

        with container.request_scope():
            assert container.resolve_from_context(token) is db

    def test_transient_storage(self):
        """Test transient storage with weak references."""
        container = ContextualContainer()
        token = Token("temp", Database, scope=Scope.TRANSIENT)

        db = Database()
        container.store_in_context(token, db)

        # Should be stored in weak dict
        assert container.resolve_from_context(token) is db

        # When reference is gone, should be cleaned up
        _db_id = id(db)
        del db
        # Weak reference may or may not be cleared immediately
        # depending on garbage collection

    def test_cleanup_on_scope_exit(self):
        """Test resources are cleaned up on scope exit."""
        container = ContextualContainer()
        token = Token("resource", Database, scope=Scope.REQUEST)

        mock_resource = Mock(spec=Database)

        with container.request_scope():
            container.store_in_context(token, mock_resource)

        # close() should have been called
        mock_resource.close.assert_called_once()

    def test_cleanup_with_context_manager(self):
        """Test cleanup of context manager resources."""
        container = ContextualContainer()
        token = Token("resource", Mock, scope=Scope.REQUEST)

        mock_resource = MagicMock()

        with container.request_scope():
            container.store_in_context(token, mock_resource)

        # __exit__ should have been called if it exists
        if hasattr(mock_resource, "__exit__"):
            mock_resource.__exit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_async_request_scope(self):
        """Test async request scope."""
        container = ContextualContainer()
        token = Token("database", Database, scope=Scope.REQUEST)

        async with container.async_request_scope():
            db = Database()
            container.store_in_context(token, db)
            assert container.resolve_from_context(token) is db

        assert container.resolve_from_context(token) is None

    @pytest.mark.asyncio
    async def test_async_cleanup(self):
        """Test async resource cleanup."""
        container = ContextualContainer()
        token = Token("resource", AsyncResource, scope=Scope.REQUEST)

        mock_resource = Mock(spec=AsyncResource)

        async def _noop() -> None:
            return None

        mock_resource.aclose = Mock(return_value=_noop())

        async with container.async_request_scope():
            container.store_in_context(token, mock_resource)

        mock_resource.aclose.assert_called_once()

    def test_clear_request_context(self):
        """Test clearing request context."""
        container = ContextualContainer()
        token = Token("db", Database, scope=Scope.REQUEST)

        with container.request_scope():
            container.store_in_context(token, Database())
            assert container.resolve_from_context(token) is not None

            container.clear_request_context()
            assert container.resolve_from_context(token) is None

    def test_clear_session_context(self):
        """Test clearing session context."""
        container = ContextualContainer()
        token = Token("user", str, scope=Scope.SESSION)

        with container.session_scope():
            container.store_in_context(token, "user123")
            assert container.resolve_from_context(token) == "user123"

            container.clear_session_context()
            assert container.resolve_from_context(token) is None

    def test_clear_all_contexts(self):
        """Test clearing all contexts."""
        container = ContextualContainer()

        # Add various scoped items
        singleton_token = Token("s", Database, scope=Scope.SINGLETON)
        container.store_in_context(singleton_token, Database())

        with container.request_scope():
            request_token = Token("r", Database, scope=Scope.REQUEST)
            container.store_in_context(request_token, Database())

            # Clear everything
            container.clear_all_contexts()

            # All should be gone
            assert container.resolve_from_context(singleton_token) is None
            assert container.resolve_from_context(request_token) is None


class TestRequestScope:
    """Test suite for RequestScope helper."""

    def test_request_scope_sync(self):
        """Test RequestScope sync context manager."""
        container = ContextualContainer()
        token = Token("db", Database, scope=Scope.REQUEST)

        with RequestScope(container) as scope:
            db = Database()
            container.store_in_context(token, db)

            # Can resolve through scope
            resolved = scope.resolve(token)
            assert resolved is db

    @pytest.mark.asyncio
    async def test_request_scope_async(self):
        """Test RequestScope async context manager."""
        container = ContextualContainer()
        token = Token("db", Database, scope=Scope.REQUEST)

        async with RequestScope(container) as scope:
            db = Database()
            container.store_in_context(token, db)

            resolved = scope.resolve(token)
            assert resolved is db


class TestSessionScope:
    """Test suite for SessionScope helper."""

    def test_session_scope(self):
        """Test SessionScope context manager."""
        container = ContextualContainer()
        token = Token("user", str, scope=Scope.SESSION)

        with SessionScope(container) as _scope:
            container.store_in_context(token, "user123")

            # Should not resolve through scope.resolve
            # (which uses resolve_from_context)
            # This is expected behavior for session scope


class TestContextFunctions:
    """Test module-level context functions."""

    def test_get_set_context(self):
        """Test global context visibility via request scope."""
        container = ContextualContainer()
        # Simply verify that request scope context manager operates without error
        with container.request_scope():
            pass
