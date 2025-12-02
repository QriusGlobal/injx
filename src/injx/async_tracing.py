"""Async resolution tracing for debugging and observability.

This module provides tracing infrastructure for dependency resolution,
enabling developers to understand resolution timing, identify bottlenecks,
and debug complex dependency graphs.

Example:
    async with container.trace_resolution() as traces:
        result = await container.aget(MyService)

    for trace in traces:
        print(trace.format_tree())

    # Output:
    # ✓ MyService (45.2ms)
    #   ✓ Database (30.1ms)
    #     ✓ ConnectionPool (15.4ms)
    #   ✓ Logger (5.3ms)
"""

from __future__ import annotations

import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResolutionTrace:
    """Trace information for a single dependency resolution.

    Captures timing, success/failure status, and hierarchical relationships
    between resolved dependencies.

    Attributes:
        token_name: Name of the token being resolved
        start_time: High-resolution start timestamp
        end_time: High-resolution end timestamp (None if not completed)
        success: Whether resolution succeeded
        error: Error message if resolution failed
        children: Nested resolution traces for dependencies
    """

    token_name: str
    start_time: float = field(default_factory=time.perf_counter)
    end_time: float | None = None
    success: bool = False
    error: str | None = None
    children: list[ResolutionTrace] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        """Resolution duration in milliseconds."""
        if self.end_time is not None:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def complete(self, success: bool = True, error: str | None = None) -> None:
        """Mark the trace as complete.

        Args:
            success: Whether resolution succeeded
            error: Error message if failed
        """
        self.end_time = time.perf_counter()
        self.success = success
        self.error = error

    def format_tree(self, indent: int = 0) -> str:
        """Format the trace as a tree for display.

        Args:
            indent: Current indentation level

        Returns:
            Formatted string representation
        """
        prefix = "  " * indent
        status = "✓" if self.success else "✗"
        line = f"{prefix}{status} {self.token_name} ({self.duration_ms:.1f}ms)"

        if self.error:
            line += f"\n{prefix}  Error: {self.error}"

        for child in self.children:
            line += "\n" + child.format_tree(indent + 1)

        return line

    def to_dict(self) -> dict[str, Any]:
        """Convert trace to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the trace
        """
        return {
            "token": self.token_name,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "children": [c.to_dict() for c in self.children],
        }


# Context variables for tracing state
_trace_enabled: ContextVar[bool] = ContextVar("injx_trace_enabled", default=False)
_trace_stack: ContextVar[list[ResolutionTrace] | None] = ContextVar(
    "injx_trace_stack", default=None
)
_trace_current: ContextVar[ResolutionTrace | None] = ContextVar(
    "injx_trace_current", default=None
)


def is_tracing_enabled() -> bool:
    """Check if tracing is currently enabled."""
    return _trace_enabled.get()


def get_traces() -> list[ResolutionTrace]:
    """Get the accumulated traces for the current context."""
    stack = _trace_stack.get()
    return stack if stack is not None else []


def start_trace(token_name: str) -> ResolutionTrace | None:
    """Start tracing a resolution if tracing is enabled.

    Args:
        token_name: Name of the token being resolved

    Returns:
        The trace object, or None if tracing is disabled
    """
    if not _trace_enabled.get():
        return None

    trace = ResolutionTrace(token_name=token_name)

    # Add to parent's children if nested
    parent = _trace_current.get()
    if parent is not None:
        parent.children.append(trace)
    else:
        # Top-level trace
        existing_stack = _trace_stack.get()
        if existing_stack is None:
            new_stack: list[ResolutionTrace] = []
            _trace_stack.set(new_stack)
            new_stack.append(trace)
        else:
            existing_stack.append(trace)

    # Set as current trace
    _trace_current.set(trace)
    return trace


def end_trace(
    trace: ResolutionTrace | None, success: bool = True, error: str | None = None
) -> None:
    """Complete a trace.

    Args:
        trace: The trace to complete (None is a no-op)
        success: Whether resolution succeeded
        error: Error message if failed
    """
    if trace is None:
        return

    trace.complete(success=success, error=error)

    # Restore parent as current
    # Find parent by checking which trace has this as a child
    stack = _trace_stack.get()
    if stack is None:
        stack = []

    def find_parent(
        traces: list[ResolutionTrace], target: ResolutionTrace
    ) -> ResolutionTrace | None:
        for t in traces:
            if target in t.children:
                return t
            parent = find_parent(t.children, target)
            if parent:
                return parent
        return None

    parent = find_parent(stack, trace)
    _trace_current.set(parent)


class TracingContext:
    """Context manager for enabling tracing.

    Used internally by Container.trace_resolution().
    """

    def __init__(self) -> None:
        self._old_enabled: bool = False
        self._old_stack: list[ResolutionTrace] | None = None
        self._old_current: ResolutionTrace | None = None

    def __enter__(self) -> list[ResolutionTrace]:
        self._old_enabled = _trace_enabled.get()
        self._old_stack = _trace_stack.get()
        self._old_current = _trace_current.get()

        # Initialize fresh tracing state
        new_stack: list[ResolutionTrace] = []
        _trace_enabled.set(True)
        _trace_stack.set(new_stack)
        _trace_current.set(None)

        return new_stack

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        _trace_enabled.set(self._old_enabled)
        _trace_stack.set(self._old_stack)
        _trace_current.set(self._old_current)

    async def __aenter__(self) -> list[ResolutionTrace]:
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)
