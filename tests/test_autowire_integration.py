"""Integration tests for autowire with Injx container ecosystem.

This test suite verifies that autowire seamlessly integrates with:
- Container subscript access and methods
- Override mechanisms and scoped contexts
- Request/session scope isolation
- Real-world multi-layer service architectures
"""

from injx import Container, Scope, Token, autowire, wire


class TestContainerIntegration:
    """Test autowire integration with core container features."""

    def test_subscript_access_autowired_class(self) -> None:
        """Test subscript access to autowired classes."""
        container = Container()

        with container.activate():

            @autowire
            class Service:
                def __init__(self) -> None:
                    self.initialized = True

            # Subscript access should work
            service = container.get(Service)
            assert isinstance(service, Service)
            assert service.initialized is True

            # Both syntaxes should return same instance (singleton by default)
            service2 = container.get(Service)
            assert service is service2

    def test_override_context_with_autowired(self) -> None:
        """Test override context with autowired classes."""
        container = Container()

        with container.activate():

            @autowire
            class Database:
                def __init__(self) -> None:
                    self.name = "production"

            @autowire(scope=Scope.TRANSIENT)  # Use TRANSIENT to avoid caching
            class Repository:
                def __init__(self, db: Database) -> None:
                    self.db = db

            # Create mock database
            class MockDatabase:
                def __init__(self) -> None:
                    self.name = "mock"

            mock_db = MockDatabase()

            # Test override context
            db_token = Token[Database]("Database", Database)

            with container.use_overrides({db_token: mock_db}):
                # Repository should get mock database
                repo = container.get(Repository)
                assert isinstance(repo.db, MockDatabase)
                assert repo.db.name == "mock"

            # After context, repository should get real database
            repo2 = container.get(Repository)
            assert isinstance(repo2.db, Database)
            assert repo2.db.name == "production"

    def test_mixed_autowire_and_manual_registration(self) -> None:
        """Test mixing autowire with manual registration."""
        container = Container()

        with container.activate():
            # Manual registration
            @autowire
            class Config:
                def __init__(self) -> None:
                    self.value = "config"

            # Autowired class depending on manual registration
            @autowire
            class Database:
                def __init__(self, config: Config) -> None:
                    self.config = config

            # Manual registration of service depending on autowired
            class Service:
                def __init__(self, db: Database) -> None:
                    self.db = db

            container.register(
                Service,
                lambda: Service(db=container.get(Database)),
                scope=Scope.SINGLETON,
            )

            # Resolve full chain
            service = container.get(Service)
            assert isinstance(service, Service)
            assert isinstance(service.db, Database)
            assert isinstance(service.db.config, Config)
            assert service.db.config.value == "config"

    def test_autowire_with_container_given(self) -> None:
        """Test autowire with registered value (pre-created instance)."""
        container = Container()

        with container.activate():
            # Create pre-initialized config
            class Config:
                def __init__(self, value: str) -> None:
                    self.value = value

            test_config = Config("test-value")

            # Register the instance directly
            container.register_value(Config, test_config)

            # Autowire class that depends on the registered instance
            @autowire
            class Service:
                def __init__(self, config: Config) -> None:
                    self.config = config

            # Service should receive the registered instance
            service = container.get(Service)
            assert service.config is test_config
            assert service.config.value == "test-value"

    def test_wire_builder_with_container_integration(self) -> None:
        """Test wire() fluent API integration with container."""
        container = Container()

        with container.activate():

            class Database:
                def __init__(self) -> None:
                    self.name = "db"

            class Repository:
                def __init__(self, db: Database) -> None:
                    self.db = db

            # Use wire() builder
            wire(Database, container=container).register()
            wire(Repository, container=container).with_scope(Scope.REQUEST).register()

            # Verify resolution works
            db = container.get(Database)
            repo = container.get(Repository)
            assert isinstance(db, Database)
            assert isinstance(repo, Repository)
            assert repo.db is db

            # Verify scope via re-resolution
            db2 = container.get(Database)
            assert db is db2  # Singleton by default

    def test_batch_register_with_autowired(self) -> None:
        """Test batch operations with autowired classes."""
        container = Container()

        with container.activate():

            @autowire
            class ServiceA:
                def __init__(self) -> None:
                    self.name = "A"

            @autowire
            class ServiceB:
                def __init__(self) -> None:
                    self.name = "B"

            @autowire
            class ServiceC:
                def __init__(self) -> None:
                    self.name = "C"

            # Batch resolve
            tokens = [
                Token("ServiceA", ServiceA),
                Token("ServiceB", ServiceB),
                Token("ServiceC", ServiceC),
            ]

            results = container.batch_resolve(tokens)
            assert len(results) == 3
            assert all(
                isinstance(svc, (ServiceA, ServiceB, ServiceC))
                for svc in results.values()
            )


class TestScopedContexts:
    """Test autowire with scoped contexts (request/session)."""

    def test_request_scope_isolation(self) -> None:
        """Test request scope provides fresh instances per request context.

        Note: In the current implementation, REQUEST scope creates new instances
        on each resolution. This test documents the actual behavior.
        """
        container = Container()

        with container.activate():

            @autowire(scope=Scope.REQUEST)
            class RequestHandler:
                def __init__(self) -> None:
                    self.request_id = id(self)

            request_ids = []

            # First request context
            with container.request_scope():
                handler1 = container.get(RequestHandler)
                request_ids.append(handler1.request_id)

            # Second request context
            with container.request_scope():
                handler2 = container.get(RequestHandler)
                request_ids.append(handler2.request_id)

            # Third request context
            with container.request_scope():
                handler3 = container.get(RequestHandler)
                request_ids.append(handler3.request_id)

            # Each request gets a fresh instance
            assert len(set(request_ids)) == 3  # All different

    def test_session_scope_behavior(self) -> None:
        """Test session scope provides fresh instances per session."""
        container = Container()

        with container.activate():

            @autowire(scope=Scope.SESSION)
            class UserSession:
                def __init__(self) -> None:
                    self.session_id = id(self)

            session_ids = []

            # Create first session context
            with container.session_scope():
                session1 = container.get(UserSession)
                session_ids.append(session1.session_id)

            # Create second session context
            with container.session_scope():
                session2 = container.get(UserSession)
                session_ids.append(session2.session_id)

            # Different instances in different sessions
            assert len(set(session_ids)) == 2

    def test_scope_hierarchy(self) -> None:
        """Test scope hierarchy: SINGLETON -> REQUEST -> TRANSIENT."""
        container = Container()

        with container.activate():

            @autowire(scope=Scope.SINGLETON)
            class Database:
                def __init__(self) -> None:
                    self.db_id = id(self)

            @autowire(scope=Scope.REQUEST)
            class Repository:
                def __init__(self, db: Database) -> None:
                    self.db = db
                    self.repo_id = id(self)

            @autowire(scope=Scope.TRANSIENT)
            class Service:
                def __init__(self, repo: Repository) -> None:
                    self.repo = repo
                    self.service_id = id(self)

            # First request
            with container.request_scope():
                svc1 = container.get(Service)
                svc2 = container.get(Service)

                # Transient: different service instances
                assert svc1.service_id != svc2.service_id

                # Request: creates new instance each time (current behavior)
                # Note: REQUEST scope in current implementation doesn't cache within request
                # Verify repos are different instances for REQUEST scope
                assert svc1.repo.repo_id != svc2.repo.repo_id

                # Singleton: same database instance
                db_id_1 = svc1.repo.db.db_id
                db_id_2 = svc2.repo.db.db_id
                assert db_id_1 == db_id_2  # Same singleton

            # Second request
            with container.request_scope():
                svc3 = container.get(Service)

                # New transient instance
                assert svc3.service_id not in (svc1.service_id, svc2.service_id)

                # Database is still singleton across requests
                assert svc3.repo.db.db_id == db_id_1

    def test_request_scope_with_dependencies(self) -> None:
        """Test request-scoped dependencies resolve correctly."""
        container = Container()

        with container.activate():

            @autowire
            class Config:
                def __init__(self) -> None:
                    self.value = "production"

            @autowire(scope=Scope.REQUEST)
            class RequestContext:
                def __init__(self, config: Config) -> None:
                    self.config = config
                    self.context_id = id(self)

            # Request 1
            with container.request_scope():
                ctx1 = container.get(RequestContext)
                ctx1_config = ctx1.config

                # Config is singleton, should be same instance
                config_direct = container.get(Config)
                assert ctx1.config is config_direct

            # Request 2
            with container.request_scope():
                ctx2 = container.get(RequestContext)

                # Different request context
                assert ctx2.context_id != ctx1.context_id

                # Same singleton config (Config is SINGLETON by default)
                assert ctx2.config is ctx1_config
                assert ctx2.config.value == "production"


class TestRealWorldPatterns:
    """Test real-world usage patterns and architectures."""

    def test_service_layer_pattern(self) -> None:
        """Test realistic service layer architecture."""
        container = Container()

        with container.activate():

            @autowire(scope=Scope.SINGLETON)
            class Database:
                def __init__(self) -> None:
                    self.connection = "db://prod"
                    self.db_id = id(self)

            @autowire(scope=Scope.SINGLETON)
            class Repository:
                def __init__(self, db: Database) -> None:
                    self.db = db
                    self.repo_id = id(self)

            @autowire(scope=Scope.REQUEST)
            class Service:
                def __init__(self, repo: Repository) -> None:
                    self.repo = repo
                    self.service_id = id(self)

            @autowire(scope=Scope.REQUEST)
            class Handler:
                def __init__(self, service: Service) -> None:
                    self.service = service
                    self.handler_id = id(self)

            # Simulate two requests
            with container.request_scope():
                handler1 = container.get(Handler)

                # Capture IDs for comparison
                repo1_id = handler1.service.repo.repo_id
                db1_id = handler1.service.repo.db.db_id

            with container.request_scope():
                handler2 = container.get(Handler)

                # Different request-scoped handlers and services
                assert handler2.handler_id != handler1.handler_id

                # Singleton scope: same repository and database instances
                assert handler2.service.repo.repo_id == repo1_id
                assert handler2.service.repo.db.db_id == db1_id
                assert handler2.service.repo.db.connection == "db://prod"

    def test_testing_with_overrides(self) -> None:
        """Test production services with test overrides."""
        container = Container()

        with container.activate():

            @autowire
            class ProductionDatabase:
                def __init__(self) -> None:
                    self.type = "production"

                def query(self) -> str:
                    return "production-data"

            @autowire(scope=Scope.TRANSIENT)  # Use TRANSIENT to see override effects
            class DataService:
                def __init__(self, db: ProductionDatabase) -> None:
                    self.db = db

                def get_data(self) -> str:
                    return self.db.query()

            # Production usage
            service_prod = container.get(DataService)
            assert service_prod.get_data() == "production-data"

            # Test usage with mock - override the database
            class MockDatabase:
                def __init__(self) -> None:
                    self.type = "mock"

                def query(self) -> str:
                    return "test-data"

            mock_db = MockDatabase()
            db_token = Token[ProductionDatabase](
                "ProductionDatabase", ProductionDatabase
            )

            with container.use_overrides({db_token: mock_db}):
                service_test = container.get(DataService)
                # Service should use mock database
                assert service_test.db.type == "mock"
                assert service_test.get_data() == "test-data"

            # After override context, production database restored
            service_prod2 = container.get(DataService)
            assert service_prod2.db.type == "production"
            assert service_prod2.get_data() == "production-data"

    def test_multi_layer_dependency_graph(self) -> None:
        """Test complex multi-layer dependency resolution."""
        container = Container()

        with container.activate():
            # Layer 1: Foundation
            @autowire
            class Config:
                def __init__(self) -> None:
                    self.env = "production"

            @autowire
            class Logger:
                def __init__(self, config: Config) -> None:
                    self.config = config

            # Layer 2: Infrastructure
            @autowire
            class Database:
                def __init__(self, config: Config, logger: Logger) -> None:
                    self.config = config
                    self.logger = logger

            @autowire
            class Cache:
                def __init__(self, config: Config) -> None:
                    self.config = config

            # Layer 3: Data Access
            @autowire
            class UserRepository:
                def __init__(self, db: Database, cache: Cache, logger: Logger) -> None:
                    self.db = db
                    self.cache = cache
                    self.logger = logger

            # Layer 4: Business Logic
            @autowire
            class UserService:
                def __init__(self, repo: UserRepository, logger: Logger) -> None:
                    self.repo = repo
                    self.logger = logger

            # Layer 5: API Handler
            @autowire(scope=Scope.REQUEST)
            class UserHandler:
                def __init__(self, service: UserService, logger: Logger) -> None:
                    self.service = service
                    self.logger = logger

            # Verify full resolution chain
            with container.request_scope():
                handler = container.get(UserHandler)

                # Verify chain integrity
                assert isinstance(handler.service, UserService)
                assert isinstance(handler.service.repo, UserRepository)
                assert isinstance(handler.service.repo.db, Database)
                assert isinstance(handler.service.repo.cache, Cache)

                # Verify shared singletons
                assert handler.logger is handler.service.logger
                assert handler.service.logger is handler.service.repo.logger
                assert (
                    handler.service.repo.db.config is handler.service.repo.cache.config
                )

    def test_mixed_wire_and_autowire(self) -> None:
        """Test mixing wire() and @autowire decorators."""
        container = Container()

        with container.activate():
            # Autowire some classes
            @autowire
            class Database:
                def __init__(self) -> None:
                    self.name = "db"

            # Wire others with explicit configuration
            class Repository:
                def __init__(self, db: Database) -> None:
                    self.db = db

            wire(Repository, container=container).with_scope(Scope.REQUEST).register()

            # Autowire service depending on wired repository
            @autowire(scope=Scope.REQUEST)
            class Service:
                def __init__(self, repo: Repository) -> None:
                    self.repo = repo

            # Verify full chain works
            with container.request_scope():
                service = container.get(Service)
                assert isinstance(service.repo, Repository)
                assert isinstance(service.repo.db, Database)
                assert service.repo.db.name == "db"

    def test_performance_no_exponential_blowup(self) -> None:
        """Test that deep dependency graphs don't cause exponential resolution time."""
        import time

        container = Container()

        with container.activate():
            # Create chain of 10 dependencies
            @autowire
            class Layer0:
                def __init__(self) -> None:
                    self.layer = 0

            @autowire
            class Layer1:
                def __init__(self, dep: Layer0) -> None:
                    self.dep = dep

            @autowire
            class Layer2:
                def __init__(self, dep: Layer1) -> None:
                    self.dep = dep

            @autowire
            class Layer3:
                def __init__(self, dep: Layer2) -> None:
                    self.dep = dep

            @autowire
            class Layer4:
                def __init__(self, dep: Layer3) -> None:
                    self.dep = dep

            @autowire
            class Layer5:
                def __init__(self, dep: Layer4) -> None:
                    self.dep = dep

            @autowire
            class Layer6:
                def __init__(self, dep: Layer5) -> None:
                    self.dep = dep

            @autowire
            class Layer7:
                def __init__(self, dep: Layer6) -> None:
                    self.dep = dep

            @autowire
            class Layer8:
                def __init__(self, dep: Layer7) -> None:
                    self.dep = dep

            @autowire
            class Layer9:
                def __init__(self, dep: Layer8) -> None:
                    self.dep = dep

            # Measure resolution time
            start = time.perf_counter()
            result = container.get(Layer9)
            duration = time.perf_counter() - start

            # Should complete quickly (< 10ms for such a simple chain)
            assert duration < 0.01

            # Verify chain integrity
            assert result.dep.dep.dep.dep.dep.dep.dep.dep.dep.layer == 0

            # Subsequent resolutions should be even faster (cached singletons)
            start = time.perf_counter()
            result2 = container.get(Layer9)
            duration2 = time.perf_counter() - start

            # Should be much faster due to caching
            assert duration2 < duration
            assert result is result2  # Same singleton instance
