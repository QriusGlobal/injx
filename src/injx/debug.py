"""Debugging utilities for Injx dependency injection container.

This module provides tools for inspecting container state, visualizing
dependency graphs, and debugging resolution issues.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, TypeVar

from .container import Container
from .tokens import Token

__all__ = [
    "ContainerDebugger",
    "DependencyVisualizer",
]

T = TypeVar("T")


class ContainerDebugger:
    """Debugger for container state and dependency resolution."""

    def __init__(self, container: Container) -> None:
        """Initialize debugger.

        Args:
            container: The container to debug
        """
        self.container = container

    def get_container_state(self) -> Dict[str, Any]:
        """Get comprehensive container state information.

        Returns:
            Dictionary with container state details
        """
        providers_view = self.container.get_providers_view()
        singletons_view = self.container._runtime.singletons.as_read_only()

        return {
            "providers": {
                "count": len(providers_view),
                "by_scope": self._group_by_scope(providers_view),
                "details": self._format_providers(providers_view),
            },
            "singletons": {
                "count": len(singletons_view),
                "instances": self._format_singletons(singletons_view),
            },
            "performance": {
                "cache_hit_rate": self.container.cache_hit_rate,
                "stats": self.container.get_stats(),
            },
            "contexts": {
                "request_active": self._has_request_context(),
                "session_active": self._has_session_context(),
            },
        }

    def _group_by_scope(self, providers: Any) -> Dict[str, int]:
        """Group providers by scope."""
        scope_counts: Dict[str, int] = defaultdict(int)
        for token in providers.keys():
            scope_counts[token.scope.name] += 1
        return dict(scope_counts)

    def _format_providers(self, providers: Any) -> List[Dict[str, Any]]:
        """Format provider information for display."""
        formatted: List[Dict[str, Any]] = []
        for token, spec in providers.items():
            formatted.append(
                {
                    "name": token.name,
                    "type": getattr(token.type_, "__name__", str(token.type_)),
                    "scope": token.scope.name,
                    "is_async": getattr(spec, "is_async", False),
                    "cleanup": getattr(getattr(spec, "cleanup", None), "name", "NONE"),
                }
            )
        return formatted

    def _format_singletons(self, singletons: Any) -> List[Dict[str, Any]]:
        """Format singleton information for display."""
        formatted: List[Dict[str, Any]] = []
        for token, instance in singletons.items():
            formatted.append(
                {
                    "name": token.name,
                    "type": type(instance).__name__,
                    "module": getattr(type(instance), "__module__", "unknown"),
                    "id": id(instance),
                }
            )
        return formatted

    def _has_request_context(self) -> bool:
        """Check if request context is active."""
        try:
            from .contextual import get_current_context

            return get_current_context() is not None
        except Exception:
            return False

    def _has_session_context(self) -> bool:
        """Check if session context is active."""
        try:
            from .contextual import _session_context

            return _session_context.get() is not None
        except Exception:
            return False

    def check_token_resolution(self, token: Token[T] | type[T]) -> Dict[str, Any]:
        """Check if a token can be resolved and provide diagnostic information.

        Args:
            token: The token to check

        Returns:
            Diagnostic information about the token
        """
        normalized_token = (
            token if isinstance(token, Token) else Token(token.__name__, token)
        )

        diagnostic = {
            "token": {
                "name": normalized_token.name,
                "type": normalized_token.type_.__name__
                if hasattr(normalized_token.type_, "__name__")
                else str(normalized_token.type_),
                "scope": normalized_token.scope.name,
            },
            "registered": normalized_token in self.container.get_providers_view(),
            "singleton_cached": self.container.get_singleton_cached(normalized_token)
            is not None,
            "has_context": self.container.resolve_from_context(normalized_token)
            is not None,
            "can_resolve": False,
            "resolution_path": [],
            "issues": [],
        }

        # Try to resolve and capture any issues
        try:
            instance = self.container.get(normalized_token)
            diagnostic["can_resolve"] = True
            diagnostic["instance_type"] = type(instance).__name__
            diagnostic["instance_id"] = id(instance)
        except Exception as e:
            diagnostic["issues"].append(str(e))

        return diagnostic

    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze container performance metrics.

        Returns:
            Performance analysis data
        """
        stats = self.container.get_stats()
        resolution_times = list(self.container._runtime.resolution_times)

        return {
            "cache_performance": {
                "hit_rate": self.container.cache_hit_rate,
                "hits": stats["cache_hits"],
                "misses": stats["cache_misses"],
            },
            "resolution_times": {
                "count": len(resolution_times),
                "average_ms": sum(resolution_times) / len(resolution_times)
                if resolution_times
                else 0,
                "min_ms": min(resolution_times) if resolution_times else 0,
                "max_ms": max(resolution_times) if resolution_times else 0,
            },
            "memory_usage": {
                "providers": stats["total_providers"],
                "singletons": stats["singletons"],
                "tracked_resources": len(self.container._runtime.resources),
            },
        }


class DependencyVisualizer:
    """Visualizer for dependency graphs and relationships."""

    def __init__(self, container: Container) -> None:
        """Initialize visualizer.

        Args:
            container: The container to visualize
        """
        self.container = container

    def get_dependency_graph(self) -> Dict[str, Any]:
        """Get dependency graph representation.

        Returns:
            Graph data structure with nodes and edges
        """
        providers = self.container.get_providers_view()
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # Build nodes
        for token in providers.keys():
            nodes.append(
                {
                    "id": token.name,
                    "type": token.type_.__name__
                    if hasattr(token.type_, "__name__")
                    else str(token.type_),
                    "scope": token.scope.name,
                    "is_singleton": self.container.get_singleton_cached(token)
                    is not None,
                }
            )

        # TODO: Build edges when we have dependency analysis
        # This would require analyzing provider functions to extract their dependencies

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "singletons": sum(1 for n in nodes if n["is_singleton"]),
            },
        }

    def print_graph(
        self, include_types: bool = True, include_scopes: bool = True
    ) -> str:
        """Print a text representation of the dependency graph.

        Args:
            include_types: Whether to include type information
            include_scopes: Whether to include scope information

        Returns:
            Formatted string representation of the graph
        """
        graph = self.get_dependency_graph()
        lines = ["Dependency Graph:", "=" * 50]

        for node in sorted(graph["nodes"], key=lambda n: n["id"]):
            parts = [f"  {node['id']}"]
            if include_types:
                parts.append(f" ({node['type']})")
            if include_scopes:
                parts.append(f" [{node['scope']}]")
            if node["is_singleton"]:
                parts.append(" [SINGLETON]")
            lines.append("".join(parts))

        if graph["edges"]:
            lines.append("\nDependencies:")
            for edge in graph["edges"]:
                lines.append(f"  {edge['from']} -> {edge['to']}")
        else:
            lines.append("\nNo dependency information available")

        return "\n".join(lines)


def debug_container(container: Container) -> ContainerDebugger:
    """Create a debugger for the given container.

    Args:
        container: The container to debug

    Returns:
        A ContainerDebugger instance
    """
    return ContainerDebugger(container)
