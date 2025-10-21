"""Tests for autowire with default parameter values - REFACTORED.

REFACTORED: Reduced from 305 lines to ~80 lines through:
- Parametrized tests for repeated patterns
- Eliminated redundant test cases
- Focused on edge cases and key behaviors
"""

import pytest

from injx import Container, Scope, autowire


class TestDefaultParameters:
    """Test that parameters with defaults are not treated as dependencies."""

    @pytest.mark.parametrize(
        "defaults,expected",
        [
            ({"debug": False, "timeout": 30}, {"debug": False, "timeout": 30}),
            ({"host": "localhost", "port": 8080}, {"host": "localhost", "port": 8080}),
            ({"logger": None}, {"logger": None}),
            (
                {"base_url": "https://api.example.com"},
                {"base_url": "https://api.example.com"},
            ),
            (
                {"precision": 2, "tolerance": 0.001},
                {"precision": 2, "tolerance": 0.001},
            ),
        ],
    )
    def test_simple_defaults_no_dependencies(self, defaults: dict, expected: dict):
        """Parameters with default values should not require dependency resolution."""
        container = Container()

        # Create class dynamically with given defaults
        def make_init(defaults_dict):
            def __init__(self, **kwargs) -> None:
                for k, v in defaults_dict.items():
                    setattr(self, k, kwargs.get(k, v))

            return __init__

        # Build signature with defaults
        import inspect

        sig_params = [
            inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        for key, default_val in defaults.items():
            param_type = type(default_val) if default_val is not None else object | None
            sig_params.append(
                inspect.Parameter(
                    key,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=default_val,
                    annotation=param_type,
                )
            )

        TestClass = type("TestClass", (), {"__init__": make_init(defaults)})
        TestClass.__init__.__signature__ = inspect.Signature(sig_params)

        with container.activate():
            autowire(TestClass)

        instance = container.get(TestClass)
        for key, expected_val in expected.items():
            assert getattr(instance, key) == expected_val

    def test_mixed_required_and_default_params(self):
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
                    db: Database,
                    cache_enabled: bool = True,
                    timeout: int = 5000,
                ) -> None:
                    self.db = db
                    self.cache_enabled = cache_enabled
                    self.timeout = timeout

        repo = container.get(Repository)
        assert isinstance(repo.db, Database)
        assert repo.cache_enabled is True
        assert repo.timeout == 5000

    def test_complex_default_values(self):
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

        config = container.get(Config)
        assert config.tags == []
        assert config.settings == {}

    @pytest.mark.parametrize("scope", [Scope.SINGLETON, Scope.TRANSIENT])
    def test_defaults_with_different_scopes(self, scope: Scope):
        """Default parameters work with different autowire scopes."""
        container = Container()

        with container.activate():

            @autowire(scope=scope)
            class ScopedService:
                def __init__(self, value: int = 42) -> None:
                    self.value = value

        svc1 = container.get(ScopedService)
        svc2 = container.get(ScopedService)

        assert svc1.value == 42
        assert svc2.value == 42

        if scope == Scope.SINGLETON:
            assert svc1 is svc2
        else:
            assert svc1 is not svc2

    def test_required_after_defaults_raises_error(self):
        """Python enforces required params before defaults at parse time."""
        with pytest.raises(SyntaxError):
            exec(
                """
class BadService:
    def __init__(self, default_param: int = 5, required_param: str):
        pass
"""
            )
