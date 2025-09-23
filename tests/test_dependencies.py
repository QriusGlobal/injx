"""Tests for the Dependencies pattern."""

import pytest

from injx import Container, Dependencies, Token, inject


class Database:
    """Test database service."""

    def query(self) -> str:
        """Return test data."""
        return "data"


class Logger:
    """Test logger service."""

    def log(self, msg: str) -> str:
        """Log and return message."""
        return msg


class Cache:
    """Test cache service."""

    def get(self, key: str) -> str:
        """Get cached value."""
        return f"cached_{key}"


def test_dependencies_basic():
    """Test basic Dependencies functionality."""
    container = Container()
    container.register(Database, Database)
    container.register(Logger, Logger)

    deps = Dependencies(container, (Database, Logger))

    assert deps[Database].query() == "data"
    assert deps[Logger].log("test") == "test"
    assert Database in deps
    assert len(deps) == 2


def test_dependencies_with_inject():
    """Test Dependencies with @inject decorator."""
    container = Container()
    container.register(Database, Database)
    container.register(Logger, Logger)

    @inject
    def process(name: str, deps: Dependencies[Database, Logger]) -> str:
        data = deps[Database].query()
        deps[Logger].log(f"Processing {name}")
        return f"{name}: {data}"

    with container.activate():
        result = process("test")
        assert result == "test: data"


def test_dependencies_type_safety():
    """Test type safety of Dependencies."""
    container = Container()
    container.register(Database, Database)

    deps = Dependencies(container, (Database,))

    # Should work
    db = deps[Database]
    assert isinstance(db, Database)

    # Should raise KeyError
    with pytest.raises(KeyError, match="Logger not in dependencies"):
        deps[Logger]


def test_dependencies_empty():
    """Test empty Dependencies."""
    container = Container()
    deps = Dependencies(container, ())

    assert len(deps) == 0
    assert not deps
    assert repr(deps) == "Dependencies[]"


def test_dependencies_get_method():
    """Test Dependencies.get() method with default."""
    container = Container()
    container.register(Database, Database)

    deps = Dependencies(container, (Database,))

    # Existing dependency
    db = deps.get(Database)
    assert isinstance(db, Database)

    # Non-existing with default
    logger = deps.get(Logger, None)
    assert logger is None


def test_dependencies_multiple_types():
    """Test Dependencies with multiple types."""
    container = Container()
    container.register(Database, Database)
    container.register(Logger, Logger)
    container.register(Cache, Cache)

    @inject
    def complex_handler(deps: Dependencies[Database, Logger, Cache]) -> tuple:
        return (
            deps[Database].query(),
            deps[Logger].log("msg"),
            deps[Cache].get("key"),
        )

    with container.activate():
        result = complex_handler()
        assert result == ("data", "msg", "cached_key")


def test_dependencies_with_tokens():
    """Test Dependencies with Token-registered services."""
    container = Container()

    DB_TOKEN = Token("database", Database)
    LOG_TOKEN = Token("logger", Logger)

    container.register(DB_TOKEN, Database)
    container.register(LOG_TOKEN, Logger)

    # Dependencies works with types directly
    container.register(Database, lambda: container.get(DB_TOKEN))
    container.register(Logger, lambda: container.get(LOG_TOKEN))

    deps = Dependencies(container, (Database, Logger))
    assert deps[Database].query() == "data"
    assert deps[Logger].log("test") == "test"


def test_dependencies_repr():
    """Test Dependencies string representation."""
    container = Container()
    container.register(Database, Database)
    container.register(Logger, Logger)

    deps = Dependencies(container, (Database, Logger))
    assert repr(deps) == "Dependencies[Database, Logger]"


def test_dependencies_bool():
    """Test Dependencies boolean evaluation."""
    container = Container()

    # Empty dependencies
    empty_deps = Dependencies(container, ())
    assert not empty_deps

    # Non-empty dependencies
    container.register(Database, Database)
    deps = Dependencies(container, (Database,))
    assert deps


def test_dependencies_lazy_resolution():
    """Test that Dependencies resolves all dependencies lazily."""
    container = Container()

    resolution_order = []

    def create_db() -> Database:
        resolution_order.append("db")
        return Database()

    def create_logger() -> Logger:
        resolution_order.append("logger")
        return Logger()

    container.register(Database, create_db)
    container.register(Logger, create_logger)

    # Creation should NOT trigger resolution (lazy)
    deps = Dependencies(container, (Database, Logger))
    assert resolution_order == []

    # First access triggers resolution of all dependencies
    _ = deps[Database]
    assert resolution_order == ["db", "logger"]

    # Subsequent access uses cached values
    resolution_order.clear()
    _ = deps[Database]
    _ = deps[Logger]
    assert resolution_order == []


def test_dependencies_error_on_missing():
    """Test Dependencies raises error for missing dependencies."""
    container = Container()

    # Try to create Dependencies with unregistered type
    with pytest.raises(Exception):  # Container will raise on missing type
        Dependencies(container, (Database,))


def test_dependencies_contains():
    """Test __contains__ operator for Dependencies."""
    container = Container()
    container.register(Database, Database)
    container.register(Logger, Logger)

    deps = Dependencies(container, (Database, Logger))

    assert Database in deps
    assert Logger in deps
    assert Cache not in deps
