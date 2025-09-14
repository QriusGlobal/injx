"""Metaclass auto-registration tests."""

from typing import Protocol, runtime_checkable

from injx import Container, Injectable, Scope


class TestMetaclassRegistration:
    """Test automatic registration via Injectable metaclass."""

    def test_basic_auto_registration(self):
        """Test basic auto-registration of injectable classes."""

        class SimpleService(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "simple_service"
            __scope__ = Scope.SINGLETON

            def __init__(self):
                self.value = "auto-registered"

        container = Container()

        # Service should be auto-registered
        assert SimpleService in Injectable.get_registry()

        # Should be able to resolve via token
        token = Injectable.get_registry()[SimpleService]
        service = container.get(token)

        assert isinstance(service, SimpleService)
        assert service.value == "auto-registered"

    def test_auto_registration_with_dependencies(self):
        """Test auto-registration of classes with dependencies."""

        # First, create a dependency
        class Logger(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "logger"
            __scope__ = Scope.SINGLETON

            def log(self, message: str) -> str:
                return f"LOG: {message}"

        # Then create a service that depends on it
        class ServiceWithDeps(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "service_with_deps"
            __scope__ = Scope.SINGLETON

            def __init__(self, logger: Logger):
                self.logger = logger

            def do_work(self) -> str:
                return self.logger.log("work completed")

        container = Container()

        # Both should be auto-registered
        _logger_token = Injectable.get_registry()[Logger]
        service_token = Injectable.get_registry()[ServiceWithDeps]

        # Should be able to resolve service with auto-injected logger
        service = container.get(service_token)

        assert isinstance(service, ServiceWithDeps)
        assert isinstance(service.logger, Logger)
        assert service.do_work() == "LOG: work completed"

    def test_no_auto_registration_without_flag(self):
        """Test that classes without __injectable__ flag are not registered."""

        class NotInjectable(metaclass=Injectable):
            # Missing __injectable__ = True
            __token_name__ = "not_injectable"

            def __init__(self):
                self.value = "should not be registered"

        # Should not be in registry
        assert NotInjectable not in Injectable.get_registry()

    def test_auto_registration_with_protocol(self):
        """Test auto-registration works with protocol-based dependencies."""

        @runtime_checkable
        class DataStore(Protocol):
            def save(self, data: str) -> bool: ...
            def load(self) -> str: ...

        class MemoryDataStore(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "memory_store"
            __scope__ = Scope.SINGLETON

            def __init__(self):
                self._data = ""

            def save(self, data: str) -> bool:
                self._data = data
                return True

            def load(self) -> str:
                return self._data

        class DataService(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "data_service"
            __scope__ = Scope.SINGLETON

            def __init__(self, store: MemoryDataStore):  # Note: using concrete type
                self.store = store

            def process_data(self, data: str) -> str:
                self.store.save(data)
                return f"Processed: {self.store.load()}"

        container = Container()

        # Resolve data service
        service_token = Injectable.get_registry()[DataService]
        service = container.get(service_token)

        result = service.process_data("test data")
        assert result == "Processed: test data"

        # Verify store is a proper implementation
        assert isinstance(service.store, DataStore)

    def test_custom_token_names(self):
        """Test that custom token names are respected."""

        class CustomNamedService(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "my_custom_service_name"
            __scope__ = Scope.TRANSIENT

            def get_name(self) -> str:
                return "custom"

        container = Container()

        # Get token and verify name
        token = Injectable.get_registry()[CustomNamedService]
        assert token.name == "my_custom_service_name"

        # Should be able to resolve
        service = container.get(token)
        assert service.get_name() == "custom"

    def test_different_scopes(self):
        """Test that different scopes are respected in auto-registration."""

        class SingletonService(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "singleton_service"
            __scope__ = Scope.SINGLETON

            def __init__(self):
                self.created_at = id(self)

        class TransientService(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "transient_service"
            __scope__ = Scope.TRANSIENT

            def __init__(self):
                self.created_at = id(self)

        container = Container()

        singleton_token = Injectable.get_registry()[SingletonService]
        transient_token = Injectable.get_registry()[TransientService]

        # Singleton should return same instance
        s1 = container.get(singleton_token)
        s2 = container.get(singleton_token)
        assert s1 is s2
        assert s1.created_at == s2.created_at

        # Transient should return different instances
        t1 = container.get(transient_token)
        t2 = container.get(transient_token)
        assert t1 is not t2
        assert t1.created_at != t2.created_at

    def test_registry_isolation(self):
        """Registry should include newly defined services for this test."""

        class FirstService(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "first"

        assert FirstService in Injectable.get_registry()

        class SecondService(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "second"

        assert SecondService in Injectable.get_registry()

    def test_inheritance_with_metaclass(self):
        """Test that inheritance works properly with Injectable metaclass."""

        class BaseService(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "base_service"
            __scope__ = Scope.SINGLETON

            def base_method(self) -> str:
                return "base"

        class DerivedService(BaseService):
            __injectable__ = True
            __token_name__ = "derived_service"
            __scope__ = Scope.SINGLETON

            def derived_method(self) -> str:
                return "derived"

        container = Container()

        # Both should be registered
        base_token = Injectable.get_registry()[BaseService]
        derived_token = Injectable.get_registry()[DerivedService]

        base_service = container.get(base_token)
        derived_service = container.get(derived_token)

        assert base_service.base_method() == "base"
        assert derived_service.base_method() == "base"
        assert derived_service.derived_method() == "derived"

        # Should be different instances
        assert base_service is not derived_service

    def test_complex_dependency_chain(self):
        """Test complex dependency chains with auto-registration."""

        class ConfigService(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "config"
            __scope__ = Scope.SINGLETON

            def get_setting(self, key: str) -> str:
                return f"config_value_for_{key}"

        class DatabaseService(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "database"
            __scope__ = Scope.SINGLETON

            def __init__(self, config: ConfigService):
                self.config = config
                self.connection_string = config.get_setting("db_url")

            def query(self, sql: str) -> str:
                return f"DB[{self.connection_string}]: {sql}"

        class UserService(metaclass=Injectable):
            __injectable__ = True
            __token_name__ = "user_service"
            __scope__ = Scope.SINGLETON

            def __init__(self, db: DatabaseService, config: ConfigService):
                self.db = db
                self.config = config
                self.cache_enabled = config.get_setting("cache_enabled")

            def get_user(self, user_id: int) -> str:
                query_result = self.db.query(
                    f"SELECT * FROM users WHERE id = {user_id}"
                )
                return f"User[cache={self.cache_enabled}]: {query_result}"

        container = Container()

        # Should be able to resolve the complex dependency chain
        user_service_token = Injectable.get_registry()[UserService]
        user_service = container.get(user_service_token)

        result = user_service.get_user(123)

        # Verify the entire chain worked
        expected = "User[cache=config_value_for_cache_enabled]: DB[config_value_for_db_url]: SELECT * FROM users WHERE id = 123"
        assert result == expected

        # Verify singletons are shared
        db_token = Injectable.get_registry()[DatabaseService]
        config_token = Injectable.get_registry()[ConfigService]

        direct_db = container.get(db_token)
        direct_config = container.get(config_token)

        assert user_service.db is direct_db
        assert user_service.config is direct_config
        assert direct_db.config is direct_config
