"""Tests for enhanced Token implementation (singular)."""

from dataclasses import FrozenInstanceError

import pytest

from injx.tokens import Scope, Token, TokenFactory


class Database:
    """Test class for type annotations."""

    pass


class Cache:
    """Another test class."""

    pass


class TestToken:
    """Test suite for Token class."""

    def test_token_creation(self) -> None:
        token = Token("database", Database)
        assert token.name == "database"
        assert token.type_ == Database
        assert token.scope == Scope.TRANSIENT
        assert token.qualifier is None
        assert token.tags == ()

    def test_token_immutability(self) -> None:
        token = Token("database", Database)
        with pytest.raises(FrozenInstanceError):
            token.name = "cache"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            token.scope = Scope.SINGLETON  # type: ignore[misc]

    def test_token_hashing(self) -> None:
        token1 = Token("database", Database)
        token2 = Token("database", Database)
        token3 = Token("cache", Cache)
        assert hash(token1) == hash(token2)
        assert hash(token1) != hash(token3)
        token_dict = {token1: "value1"}
        assert token_dict[token2] == "value1"

    def test_token_equality(self) -> None:
        token1 = Token("database", Database, scope=Scope.SINGLETON)
        token2 = Token("database", Database, scope=Scope.SINGLETON)
        token3 = Token("database", Database, scope=Scope.REQUEST)
        token4 = Token("cache", Cache, scope=Scope.SINGLETON)
        assert token1 == token2
        assert token1 != token3
        assert token1 != token4
        assert token1 != "not a token"

    def test_token_with_qualifier(self) -> None:
        token1 = Token("database", Database, qualifier="primary")
        token2 = Token("database", Database, qualifier="secondary")
        token3 = Token("database", Database, qualifier="primary")
        assert token1 != token2
        assert token1 == token3
        assert token1.qualifier == "primary"

    def test_token_with_tags(self) -> None:
        token1 = Token("database", Database, tags=("production", "critical"))
        token2 = Token("database", Database, tags=("testing",))
        token3 = Token("database", Database, tags=("production", "critical"))
        assert token1 != token2
        assert token1 == token3
        assert "production" in token1.tags
        assert "critical" in token1.tags

    def test_token_with_scope(self) -> None:
        token = Token("database", Database, scope=Scope.SINGLETON)
        new_token = token.with_scope(Scope.REQUEST)
        assert token.scope == Scope.SINGLETON
        assert new_token.scope == Scope.REQUEST
        assert new_token.name == token.name
        assert new_token.type_ == token.type_

    def test_token_with_qualifier_method(self) -> None:
        token = Token("database", Database)
        qualified = token.with_qualifier("primary")
        assert token.qualifier is None
        assert qualified.qualifier == "primary"
        assert qualified.name == token.name

    def test_token_with_tags_method(self) -> None:
        token = Token("database", Database, tags=("existing",))
        tagged = token.with_tags("new1", "new2")
        assert "existing" in tagged.tags
        assert "new1" in tagged.tags
        assert "new2" in tagged.tags
        assert len(token.tags) == 1

    def test_token_qualified_name(self) -> None:
        token = Token("database", Database)
        assert Database.__name__ in token.qualified_name


class TestTokenFactory:
    def test_factory_creation(self) -> None:
        factory = TokenFactory()
        token = factory.create("database", Database)
        assert isinstance(token, Token)
        assert token.name == "database"
        assert token.type_ == Database

    def test_factory_caching(self) -> None:
        factory = TokenFactory()
        token1 = factory.create("database", Database)
        token2 = factory.create("database", Database)
        assert token1 is token2

    def test_factory_singleton_method(self) -> None:
        factory = TokenFactory()
        token = factory.singleton("db", Database)
        assert token.scope == Scope.SINGLETON

    def test_factory_request_method(self) -> None:
        factory = TokenFactory()
        token = factory.request("req", Database)
        assert token.scope == Scope.REQUEST

    def test_factory_session_method(self) -> None:
        factory = TokenFactory()
        token = factory.session("user", str)
        assert token.scope == Scope.SESSION

    def test_factory_transient_method(self) -> None:
        factory = TokenFactory()
        token = factory.transient("temp", object)
        assert token.scope == Scope.TRANSIENT

    def test_factory_qualified_method(self) -> None:
        factory = TokenFactory()
        token = factory.qualified("primary", Database)
        assert token.name == "Database"
        assert token.qualifier == "primary"
        assert token.type_ == Database

    def test_factory_cache_clearing(self) -> None:
        factory = TokenFactory()
        token1 = factory.create("database", Database)
        assert factory.cache_size == 1
        factory.clear_cache()
        assert factory.cache_size == 0
        token2 = factory.create("database", Database)
        assert token1 is not token2
        assert token1 == token2

    def test_factory_cache_size(self) -> None:
        factory = TokenFactory()
        assert factory.cache_size == 0
        factory.create("db1", Database)
        factory.create("db2", Database)
        factory.create("db3", Database, scope=Scope.SINGLETON)
        assert factory.cache_size == 3
        factory.create("db4", Database, tags=("test",))
        assert factory.cache_size == 3


class TestScope:
    def test_scope_values(self) -> None:
        assert Scope.SINGLETON
        assert Scope.REQUEST
        assert Scope.SESSION
        assert Scope.TRANSIENT

    def test_scope_comparison(self) -> None:
        assert Scope.SINGLETON != Scope.REQUEST
