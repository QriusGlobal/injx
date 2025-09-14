"""Logging configuration and utilities for PyInj.

This module provides centralized logging configuration for the PyInj library,
with separate loggers for operational events and performance metrics.

Example:
    Configure logging for development::

        from pyinj.logging import configure_logging
        import logging

        configure_logging(logging.INFO)
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .tokens import Token

__all__ = ["logger", "perf_logger", "configure_logging"]

# Main logger for operational events
logger = logging.getLogger("pyinj")

# Separate logger for performance metrics
perf_logger = logging.getLogger("pyinj.perf")


def configure_logging(level: int = logging.WARNING) -> None:
    """Configure PyInj logging levels.

    Sets the logging level for the main PyInj logger. The performance
    logger must be configured separately if needed.

    Args:
        level: Logging level (default: WARNING).
               Use logging.INFO for lifecycle events,
               logging.DEBUG for detailed traces.

    Example:
        Production configuration (default)::

            configure_logging()  # WARNING level

        Development configuration::

            configure_logging(logging.INFO)

        Debugging configuration::

            configure_logging(logging.DEBUG)

        Performance monitoring::

            import logging
            perf_handler = logging.StreamHandler()
            logging.getLogger("pyinj.perf").addHandler(perf_handler)
            logging.getLogger("pyinj.perf").setLevel(logging.INFO)
    """
    logger.setLevel(level)

    # Only configure handler if none exists (avoid duplicate handlers)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False


def log_resolution_path(token: "Token[Any]", path: list["Token[Any]"]) -> None:
    """Log a dependency resolution path at DEBUG level.

    Args:
        token: The token being resolved
        path: The resolution path taken
    """
    if logger.isEnabledFor(logging.DEBUG):
        path_str = " -> ".join(str(t) for t in path)
        logger.debug(f"Resolution path for {token}: {path_str}")


def log_performance_metric(
    operation: str,
    duration_ms: float,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log a performance metric.

    Args:
        operation: Name of the operation (e.g., "resolve", "register")
        duration_ms: Duration in milliseconds
        metadata: Optional additional metadata
    """
    if perf_logger.isEnabledFor(logging.INFO):
        meta_str = f" {metadata}" if metadata else ""
        perf_logger.info(f"{operation}: {duration_ms:.2f}ms{meta_str}")
