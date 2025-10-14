"""Tests for the debugging utilities module."""


from injx import Container, Scope, Token
from injx.debug import ContainerDebugger, DependencyVisualizer, debug_container


class TestContainerDebugger:
    """Test cases for ContainerDebugger."""

    def test_get_container_state(self):
        """Test getting container state."""
        container = Container()
        debugger = ContainerDebugger(container)

        # Register some providers
        SERVICE_TOKEN = Token[str]("service")
        container.register(SERVICE_TOKEN, lambda: "test", scope=Scope.SINGLETON)

        state = debugger.get_container_state()

        assert "providers" in state
        assert "singletons" in state
        assert "performance" in state
        assert "contexts" in state

        assert state["providers"]["count"] == 1
        assert state["providers"]["by_scope"]["SINGLETON"] == 1

    def test_check_token_resolution(self):
        """Test checking token resolution."""
        container = Container()
        debugger = ContainerDebugger(container)

        SERVICE_TOKEN = Token[str]("service")
        container.register(SERVICE_TOKEN, lambda: "test")

        diagnostic = debugger.check_token_resolution(SERVICE_TOKEN)

        assert diagnostic["token"]["name"] == "service"
        assert diagnostic["registered"] is True
        assert diagnostic["can_resolve"] is True
        assert diagnostic["instance_type"] == "str"

    def test_check_unregistered_token(self):
        """Test checking unregistered token."""
        container = Container()
        debugger = ContainerDebugger(container)

        UNREGISTERED_TOKEN = Token[str]("unregistered")

        diagnostic = debugger.check_token_resolution(UNREGISTERED_TOKEN)

        assert diagnostic["registered"] is False
        assert diagnostic["can_resolve"] is False
        assert len(diagnostic["issues"]) > 0

    def test_analyze_performance(self):
        """Test performance analysis."""
        container = Container()
        debugger = ContainerDebugger(container)

        # Trigger some resolutions to generate stats
        SERVICE_TOKEN = Token[str]("service")
        container.register(SERVICE_TOKEN, lambda: "test")
        container.get(SERVICE_TOKEN)

        analysis = debugger.analyze_performance()

        assert "cache_performance" in analysis
        assert "resolution_times" in analysis
        assert "memory_usage" in analysis

        assert "hit_rate" in analysis["cache_performance"]
        assert "providers" in analysis["memory_usage"]


class TestDependencyVisualizer:
    """Test cases for DependencyVisualizer."""

    def test_get_dependency_graph(self):
        """Test getting dependency graph."""
        container = Container()
        visualizer = DependencyVisualizer(container)

        SERVICE_TOKEN = Token[str]("service")
        container.register(SERVICE_TOKEN, lambda: "test")

        graph = visualizer.get_dependency_graph()

        assert "nodes" in graph
        assert "edges" in graph
        assert "stats" in graph

        assert len(graph["nodes"]) == 1
        assert graph["nodes"][0]["name"] == "service"
        assert graph["nodes"][0]["type"] == "str"

    def test_print_graph(self):
        """Test printing dependency graph."""
        container = Container()
        visualizer = DependencyVisualizer(container)

        SERVICE_TOKEN = Token[str]("service")
        container.register(SERVICE_TOKEN, lambda: "test")

        output = visualizer.print_graph()

        assert "Dependency Graph:" in output
        assert "service" in output
        assert "str" in output
        assert "TRANSIENT" in output


class TestGlobalFunctions:
    """Test cases for global debugging utility functions."""

    def test_debug_container_function(self):
        """Test debug_container global function."""
        container = Container()
        debugger = debug_container(container)

        assert isinstance(debugger, ContainerDebugger)


class TestIntegrationWithContainer:
    """Integration tests with Container debugging methods."""

    def test_container_debug_info_method(self):
        """Test Container.debug_info() method."""
        container = Container()
        SERVICE_TOKEN = Token[str]("service")
        container.register(SERVICE_TOKEN, lambda: "test", scope=Scope.SINGLETON)

        debug_info = container.debug_info()

        assert "providers_count" in debug_info
        assert "singletons_count" in debug_info
        assert "cache_hit_rate" in debug_info
        assert "tokens" in debug_info
        assert "scopes" in debug_info
        assert "performance_stats" in debug_info

        assert debug_info["providers_count"] == 1
        assert "service" in debug_info["tokens"]
        assert debug_info["scopes"]["service"] == "SINGLETON"

    def test_container_list_tokens_method(self):
        """Test Container.list_tokens() method."""
        container = Container()
        SERVICE_TOKEN = Token[str]("service")
        container.register(SERVICE_TOKEN, lambda: "test")

        tokens = container.list_tokens()

        assert len(tokens) == 1
        assert tokens[0].name == "service"

    def test_container_is_singleton_method(self):
        """Test Container.is_singleton() method."""
        container = Container()

        SINGLETON_TOKEN = Token[str]("singleton")
        TRANSIENT_TOKEN = Token[str]("transient")

        container.register(SINGLETON_TOKEN, lambda: "test", scope=Scope.SINGLETON)
        container.register(TRANSIENT_TOKEN, lambda: "test", scope=Scope.TRANSIENT)

        assert container.is_singleton(SINGLETON_TOKEN) is True
        assert container.is_singleton(TRANSIENT_TOKEN) is False

    def test_container_dependency_graph_method(self):
        """Test Container.dependency_graph() method."""
        container = Container()
        SERVICE_TOKEN = Token[str]("service")
        container.register(SERVICE_TOKEN, lambda: "test")

        graph = container.dependency_graph()

        assert "service" in graph
        assert isinstance(graph["service"], list)
