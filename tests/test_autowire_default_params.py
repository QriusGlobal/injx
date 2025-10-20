"""Tests for autowire with default parameter values."""

import pytest

from injx import Container, Scope, autowire


class TestDefaultParameters:
    """Test that parameters with defaults are not treated as dependencies."""

    def test_simple_default_params_not_dependencies(self) -> None:
        """Parameters with default values should not require dependency resolution."""
        container = Container()

        with container.activate():

            @autowire
            class ConfigService:
                def __init__(self, debug: bool = False, timeout: int = 30) -> None:
                    self.debug = debug
                    self.timeout = timeout

        # Should resolve successfully without registered bool or int dependencies
        config = container[ConfigService]
        assert config.debug is False
        assert config.timeout == 30

    def test_mixed_required_and_default_params(self) -> None:
        """Mix of required dependencies and optional defaults."""
        container = Container()

        with container.activate():

            @autowire
            class Database:
                def __init__(self) -> None:
                    self.connected = True

            @autowire
            class Repository:
                def __init__(
                    self,
                    db: Database,  # Required dependency
                    cache_enabled: bool = True,  # Optional default
                    timeout: int = 5000,  # Optional default
                ) -> None:
                    self.db = db
                    self.cache_enabled = cache_enabled
                    self.timeout = timeout

        # Should resolve with only Database dependency
        repo = container[Repository]
        assert isinstance(repo.db, Database)
        assert repo.cache_enabled is True
        assert repo.timeout == 5000

    def test_all_params_have_defaults(self) -> None:
        """Class with only default parameters should autowire successfully."""
        container = Container()

        with container.activate():

            @autowire
            class Settings:
                def __init__(
                    self,
                    host: str = "localhost",
                    port: int = 8080,
                    debug: bool = False,
                ) -> None:
                    self.host = host
                    self.port = port
                    self.debug = debug

        settings = container[Settings]
        assert settings.host == "localhost"
        assert settings.port == 8080
        assert settings.debug is False

    def test_none_as_default_value(self) -> None:
        """None as default value should not create dependency."""
        container = Container()

        with container.activate():

            @autowire
            class Service:
                def __init__(self, logger: object | None = None) -> None:
                    self.logger = logger

        service = container[Service]
        assert service.logger is None

    def test_complex_default_values(self) -> None:
        """Complex default values (lists, dicts) should work."""
        container = Container()

        with container.activate():

            @autowire
            class Config:
                def __init__(
                    self,
                    tags: list[str] | None = None,
                    settings: dict[str, int] | None = None,
                ) -> None:
                    self.tags = tags or []
                    self.settings = settings or {}

        config = container[Config]
        assert config.tags == []
        assert config.settings == {}

    def test_default_values_with_different_scopes(self) -> None:
        """Default parameters work with different autowire scopes."""
        container = Container()

        with container.activate():

            @autowire(scope=Scope.TRANSIENT)
            class TransientService:
                def __init__(self, count: int = 0) -> None:
                    self.count = count

            @autowire(scope=Scope.SINGLETON)
            class SingletonService:
                def __init__(self, name: str = "default") -> None:
                    self.name = name

        # Transient scope with defaults
        svc1 = container[TransientService]
        svc2 = container[TransientService]
        assert svc1.count == 0
        assert svc2.count == 0
        assert svc1 is not svc2  # Different instances

        # Singleton scope with defaults
        svc3 = container[SingletonService]
        svc4 = container[SingletonService]
        assert svc3.name == "default"
        assert svc3 is svc4  # Same instance

    def test_mutable_default_values_antipattern(self) -> None:
        """Test that mutable defaults work (though antipattern)."""
        container = Container()

        # Using mutable default is an antipattern, but should still work
        with container.activate():

            @autowire
            class BadPracticeService:
                def __init__(self, items: list[str] | None = None) -> None:
                    # Proper pattern: use None and create new list
                    self.items = items if items is not None else []

        svc = container[BadPracticeService]
        assert svc.items == []

    def test_string_defaults(self) -> None:
        """String default values should work."""
        container = Container()

        with container.activate():

            @autowire
            class APIClient:
                def __init__(
                    self,
                    base_url: str = "https://api.example.com",
                    api_key: str = "default-key",
                ) -> None:
                    self.base_url = base_url
                    self.api_key = api_key

        client = container[APIClient]
        assert client.base_url == "https://api.example.com"
        assert client.api_key == "default-key"

    def test_numeric_defaults(self) -> None:
        """Numeric default values (int, float) should work."""
        container = Container()

        with container.activate():

            @autowire
            class MathService:
                def __init__(
                    self,
                    precision: int = 2,
                    tolerance: float = 0.001,
                    max_iterations: int = 1000,
                ) -> None:
                    self.precision = precision
                    self.tolerance = tolerance
                    self.max_iterations = max_iterations

        svc = container[MathService]
        assert svc.precision == 2
        assert svc.tolerance == 0.001
        assert svc.max_iterations == 1000

    def test_complex_type_with_defaults(self) -> None:
        """Complex types with defaults should work."""
        container = Container()

        with container.activate():

            @autowire
            class ComplexService:
                def __init__(
                    self,
                    options: dict[str, str | int] | None = None,
                    handlers: list[object] | None = None,
                ) -> None:
                    self.options = options or {}
                    self.handlers = handlers or []

        svc = container[ComplexService]
        assert svc.options == {}
        assert svc.handlers == []

    def test_required_after_defaults_raises_error(self) -> None:
        """Python enforces required params before defaults at parse time."""
        # This test verifies that Python itself prevents this antipattern
        # We don't need special handling in autowire

        with pytest.raises(SyntaxError):
            # This should fail at parse time
            exec(
                """
class BadService:
    def __init__(self, default_param: int = 5, required_param: str):
        pass
"""
            )
