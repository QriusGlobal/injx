"""Pytest configuration and shared fixtures for injx tests."""

import asyncio
import sys
import sysconfig
from typing import AsyncGenerator, Generator

import pytest

from injx.container import Container
from injx.tokens import Token


# =============================================================================
# Free-Threading Detection Fixtures
# =============================================================================


def _is_freethreaded_build() -> bool:
    """Check if this is a free-threaded Python build (compiled with --disable-gil)."""
    return bool(sysconfig.get_config_var("Py_GIL_DISABLED"))


def _is_gil_enabled() -> bool:
    """Check if the GIL is currently enabled at runtime."""
    if hasattr(sys, "_is_gil_enabled"):
        return sys._is_gil_enabled()
    return True  # Standard builds always have GIL enabled


@pytest.fixture
def is_freethreaded_build() -> bool:
    """Check if this is a free-threaded Python build.

    Returns True if Python was compiled with --disable-gil (python3.13t).
    """
    return _is_freethreaded_build()


@pytest.fixture
def is_gil_disabled() -> bool:
    """Check if running with GIL disabled.

    Returns True only on free-threaded builds when PYTHON_GIL=0 or -Xgil=0.
    """
    return _is_freethreaded_build() and not _is_gil_enabled()


@pytest.fixture
def gil_status() -> dict[str, bool]:
    """Get comprehensive GIL status information.

    Returns dict with:
        - freethreaded_build: True if compiled with --disable-gil
        - gil_enabled: True if GIL is active at runtime
        - gil_disabled: True if running without GIL (free-threaded mode)
    """
    freethreaded = _is_freethreaded_build()
    gil_enabled = _is_gil_enabled()
    return {
        "freethreaded_build": freethreaded,
        "gil_enabled": gil_enabled,
        "gil_disabled": freethreaded and not gil_enabled,
    }


@pytest.fixture
def container() -> Container:
    """Create a fresh container for testing."""
    return Container()


@pytest.fixture
def registered_container() -> Container:
    """Create a container with some pre-registered dependencies."""
    container = Container()

    # Register some test dependencies
    container.register(Token("database", TestDatabase), lambda: TestDatabase())
    container.register(Token("cache", TestCache), lambda: TestCache())
    container.register_singleton(Token("config", TestConfig), lambda: TestConfig())

    return container


@pytest.fixture
async def async_container() -> AsyncGenerator[Container, None]:
    """Create a container for async testing."""
    container = Container()
    yield container
    # Cleanup if needed
    container.clear()


# Test classes for fixtures
class TestDatabase:
    """Test database for fixtures."""

    def __init__(self):
        self.connected = True

    def query(self, sql: str) -> str:
        return f"Result of: {sql}"


class TestCache:
    """Test cache for fixtures."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value


class TestConfig:
    """Test configuration for fixtures."""

    def __init__(self) -> None:
        self.settings = {
            "debug": True,
            "host": "localhost",
            "port": 8080,
        }


# Pytest configuration
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "freethreading: tests specifically for free-threading validation"
    )

    # Log GIL status at test session start
    freethreaded = _is_freethreaded_build()
    gil_enabled = _is_gil_enabled()
    status = "DISABLED" if (freethreaded and not gil_enabled) else "ENABLED"
    build_type = "free-threaded" if freethreaded else "standard"
    print(f"\n[pytest] Python build: {build_type}, GIL: {status}")


# Async event loop fixture for pytest-asyncio
@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
