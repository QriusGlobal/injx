# Injx Development Roadmap

> **Strategic Focus**: Python 3.13+ greenfield projects, SDK development, and async-first applications

## Executive Summary

Injx positions itself as the next-generation dependency injection library for modern Python applications. Unlike existing solutions that prioritize backward compatibility and broad adoption, Injx focuses on delivering exceptional developer experience for teams building new applications with Python 3.13+.

## Market Analysis & Positioning

### Ecosystem Landscape

| Library | Strength | Weakness | Target Use Case |
|---------|----------|----------|-----------------|
| **python-inject** | Simplicity, maturity | Limited type safety, global state | Small to medium applications |
| **dependency-injector** | Enterprise features, performance | Complex configuration, learning curve | Large enterprise applications |
| **injx** | Type safety, modern Python, DX | New/unproven, Python 3.13+ only | Greenfield projects, SDKs, async APIs |

### Key Differentiators

1. **Python 3.13+ Native**: Leverage latest language features for superior type safety
2. **Async-First Design**: Built for modern web applications and real-time systems
3. **SDK-Friendly**: Optimized for building libraries and reusable components
4. **Testing Excellence**: Testing should be easier than production code
5. **Zero-Compromise Type Safety**: Compile-time dependency verification

## Performance vs. Stability Analysis

### Lessons from python-dependency-injector's Cython Implementation

Analysis of issues #812, #791, and #827 reveals critical flaws in optimization-first approaches.

#### The Cython Performance Fallacy

**Claimed Benefits:**
- High performance through C extension optimization
- Faster runtime dependency resolution
- Enterprise-grade performance characteristics

**Observed Reality:**
- Segmentation faults in production environments (Issue #812)
- 24-month compatibility crisis with Python 3.12+ (Cython 0.29 → 3.0 migration)
- Install failures on stable Python 3.13 releases
- Single maintainer overwhelmed by C API compatibility requirements
- Performance gains negated by system instability

**Fundamental Lesson:**
Performance optimizations that compromise system reliability violate basic software engineering principles. A library that occasionally fails delivers infinite latency for failed operations.

### Architectural Principles for Stability

#### Principle 1: Correctness Before Performance

**Rationale:** Donald Knuth's observation on premature optimization applies directly to dependency injection library design. python-dependency-injector optimized before establishing:
- Stable API surface
- Comprehensive test coverage across Python versions  
- Maintenance capacity for C extension complexity

**Implementation:** Pure Python implementation using Python 3.13+ performance improvements without C extension complexity.

#### Principle 2: Maintainability Enables Reliability

**Rationale:** C extensions require specialized expertise, creating maintenance bottlenecks that compromise long-term stability.

**Implementation:**
- Zero C dependencies in core library
- Standard Python debugging tools remain functional
- Contributing requires only Python knowledge
- Bus factor > 1 through accessible codebase

#### Principle 3: Algorithmic Over Implementation Optimization

**Rationale:** O(n) algorithm in C is slower than O(1) algorithm in Python for practical input sizes.

**Implementation:**
- Pre-computed token hashes for O(1) lookups
- Lazy evaluation patterns
- Memory layout optimization through `__slots__`
- Python 3.13 performance improvements (11% function call improvement)

### Performance Strategy

#### Benchmark Methodology

**Rejected Metrics:** Microbenchmarks of isolated operations
**Adopted Metrics:** End-to-end application performance including failure scenarios

**Key Performance Indicators:**
- Install success rate: Target 100% on supported platforms
- Runtime failure rate: Target 0% (no segmentation faults)
- Median lookup latency: Target <1μs
- 99th percentile lookup latency: Target <5μs
- Memory overhead per dependency: Target <500 bytes

#### Implementation Targets

**Phase 1:** Stability establishment
- Zero segmentation faults through pure Python implementation
- Comprehensive type checking with basedpyright
- Thread safety through standard library primitives

**Phase 2:** Performance optimization
- Profile-guided optimization based on real application usage
- Benchmark against pure Python baseline, not unstable C implementations
- Optimize only demonstrated bottlenecks

### Common DI Library Problems

Analysis of python-dependency-injector issue patterns:

#### 1. Configuration Complexity
- **Problem**: Declarative containers become unwieldy with complex dependency graphs
- **Our Solution**: Hybrid approach with simple registration + optional config files

#### 2. Testing Difficulties  
- **Problem**: Mocking and dependency override patterns are error-prone
- **Our Solution**: Built-in testing utilities with clear override patterns

#### 3. Performance Bottlenecks
- **Problem**: Runtime dependency resolution overhead in hot paths
- **Our Solution**: Pre-computed token hashes + O(1) lookups

#### 4. Type Safety Gaps
- **Problem**: `__getattr__` patterns silence legitimate type checking issues
- **Our Solution**: Protocol-based design with full static analysis support

#### 5. Framework Integration Friction
- **Problem**: Complex setup required for FastAPI, Django integration
- **Our Solution**: Native async support + framework-specific helpers

#### 6. Resource Management Issues
- **Problem**: Inconsistent cleanup, memory leaks in long-running applications
- **Our Solution**: LIFO cleanup with proper async resource handling

### Anti-Patterns to Avoid

1. **Global State Dependencies**: Avoid inject.configure() patterns
2. **Magic Registration**: Explicit is better than implicit
3. **Complex Container Hierarchies**: Favor composition over inheritance
4. **Runtime Discovery**: Prefer compile-time dependency verification
5. **Framework Lock-in**: Maintain framework-agnostic core

## Technical Architecture

### Core Design Principles

1. **Immutability**: Tokens are immutable with pre-computed hashes
2. **Explicitness**: No magic, clear dependency graphs
3. **Composability**: Container as a value, not global state
4. **Type Safety**: Protocol-based interfaces with generic preservation
5. **Performance**: O(1) lookups, minimal runtime overhead

### Configuration Strategy

#### Primary: Pydantic Settings Integration
```python
from pydantic_settings import BaseSettings
from injx import Container, configure_from_settings

class APISettings(BaseSettings):
    database_url: str
    redis_url: str
    log_level: str = "INFO"

settings = APISettings()
container = configure_from_settings(settings)
```

#### Fallback: Pure TOML Configuration
```toml
[database]
url = "postgresql://localhost/myapp"
pool_size = 10

[redis]
url = "redis://localhost:6379"
max_connections = 100
```

```python
from injx import Container, configure_from_toml

container = configure_from_toml("config.toml")
```

### Testing Philosophy

**Core Principle**: Testing should be simpler than production code.

#### Request-Scoped Testing
```python
@pytest.fixture
def test_container():
    with container.test_scope() as test_container:
        test_container.override(DATABASE, MockDatabase())
        yield test_container

def test_user_service(test_container):
    service = test_container.get(USER_SERVICE)
    # Test logic here
```

#### SDK Testing Patterns
```python
class MySDK:
    def __init__(self, container: Container | None = None):
        self.container = container or get_default_container()
    
    @inject
    def create_user(self, http_client: HTTPClient) -> User:
        # Implementation using injected dependencies

# Easy to test
def test_sdk():
    mock_client = MockHTTPClient()
    container = Container()
    container.register(HTTP_CLIENT, lambda: mock_client)
    
    sdk = MySDK(container)
    user = sdk.create_user()
    assert user.id is not None
```

## Development Phases

### Phase 1: Foundation (v0.1.0 - v0.2.0) 🚧 Current
**Timeline**: Q1 2025
**Status**: In Progress

**Core Features**:
- ✅ Type-safe container implementation
- ✅ Token-based dependency registration
- ✅ Basic injection decorator
- ✅ Scope management (Singleton, Transient, Request, Session)
- ✅ Circular dependency detection
- 🚧 Performance optimization (O(1) lookups)
- ⏳ Basic configuration support

**Deliverables**:
- Core container functionality
- Basic documentation
- Performance benchmarks
- Alpha release for early adopters

### Phase 2: Developer Experience (v0.3.0 - v0.5.0)
**Timeline**: Q2 2025

**Enhanced Testing**:
- Advanced testing utilities
- Mock and override patterns
- Request/session scoped testing
- Performance testing helpers

**Configuration Management**:
- Pydantic-settings integration
- TOML configuration support  
- Environment variable binding
- Configuration validation

**Developer Tools**:
- Enhanced error messages with resolution chains
- IDE integration improvements
- Debugging utilities
- Documentation improvements

**Deliverables**:
- Comprehensive testing framework
- Configuration management system
- Developer tool integrations
- Beta release

### Phase 3: Framework Integration (v0.6.0 - v1.0.0)
**Timeline**: Q3-Q4 2025

**FastAPI Integration**:
- Native FastAPI dependency provider
- Async context management
- Request lifecycle integration
- Middleware patterns

**SDK Development Tools**:
- SDK construction patterns
- Package distribution helpers
- Version compatibility utilities
- Plugin architecture

**Enterprise Features**:
- Monitoring and observability hooks
- Production deployment patterns
- Multi-tenancy support
- Security patterns

**Deliverables**:
- Production-ready framework integrations
- SDK development toolkit
- Enterprise feature set
- 1.0 stable release

### Phase 4: Ecosystem & Adoption (v1.1.0+)
**Timeline**: 2026

**Community Building**:
- Plugin ecosystem
- Community patterns and recipes
- Third-party integrations
- Educational content

**Advanced Features**:
- Distributed dependency injection
- Multi-container patterns
- Advanced async patterns
- Performance optimizations

## Target Use Cases

### 1. SDK Development
```python
# Clean, testable SDK design
class PaymentSDK:
    def __init__(self, container: Container | None = None):
        self.container = container or create_default_container()
    
    @inject
    async def process_payment(
        self, 
        http_client: HTTPClient,
        rate_limiter: RateLimiter,
        amount: Decimal
    ) -> PaymentResult:
        # Implementation with clean dependency injection
```

### 2. API Services
```python
# FastAPI with clean dependency management
from fastapi import FastAPI
from injx import Container, Token
from injx.fastapi import InjxDepends

app = FastAPI()
container = Container()

@app.post("/users")
async def create_user(
    request: UserCreateRequest,
    user_service: UserService = InjxDepends(USER_SERVICE),
    db: Database = InjxDepends(DATABASE)
) -> UserResponse:
    user = await user_service.create(request, db)
    return UserResponse.from_user(user)
```

### 3. Monolith Service Wiring
```python
# Complex service dependency management
class ServiceRegistry:
    def __init__(self):
        self.container = Container()
        self._register_infrastructure()
        self._register_domain_services()
        self._register_application_services()
    
    def _register_infrastructure(self):
        self.container.register(DATABASE, create_database_connection)
        self.container.register(CACHE, create_redis_connection)
        self.container.register(QUEUE, create_message_queue)
    
    # Clean separation of concerns
```

## Performance Targets

### Benchmark Goals (vs. Alternatives)

| Metric | Target | Current | python-inject | dependency-injector |
|--------|---------|---------|---------------|-------------------|
| Cold lookup | <1μs | ~0.8μs | ~2μs | ~0.5μs |
| Warm lookup | <0.1μs | ~0.1μs | ~1μs | ~0.3μs |
| Memory overhead | <500B/service | ~400B | ~200B | ~300B |
| Import time | <50ms | ~40ms | ~20ms | ~30ms |

### Scalability Targets
- Support 10,000+ registered dependencies
- O(1) lookup complexity regardless of container size
- Memory-efficient resource cleanup
- Minimal GIL contention in multi-threaded scenarios

## Quality Gates

### Definition of Done
Each phase must meet these criteria before progression:

1. **Type Safety**: 100% mypy/basedpyright compatibility
2. **Test Coverage**: >95% with comprehensive edge case testing
3. **Performance**: Meet or exceed benchmark targets
4. **Documentation**: Complete API documentation with examples
5. **Real-world Validation**: At least 3 production deployments

### Success Metrics

**Phase 1**: 
- 100 GitHub stars
- 5 early adopter projects
- Performance benchmarks published

**Phase 2**:
- 500 GitHub stars  
- 50 production deployments
- Framework integration examples

**Phase 3**:
- 1000 GitHub stars
- 200 production deployments
- Community contributions

## Risk Assessment

### Technical Risks
1. **Python 3.13+ Adoption**: Limited initial market
   - *Mitigation*: Target early adopters, greenfield projects
2. **Performance Claims**: Unproven against mature alternatives
   - *Mitigation*: Rigorous benchmarking, transparent metrics
3. **Ecosystem Integration**: Framework compatibility challenges
   - *Mitigation*: Early partnership with framework maintainers

### Market Risks
1. **Adoption Inertia**: Teams stick with working solutions
   - *Mitigation*: Focus on new projects, compelling DX improvements
2. **Feature Parity**: Catching up to mature libraries
   - *Mitigation*: Focus on specific use cases, not broad compatibility
3. **Maintenance Burden**: Sustaining development momentum
   - *Mitigation*: Community building, clear governance model

## Contributing Guidelines

### Core Team Responsibilities
- Architecture decisions
- Performance optimization
- Framework integrations
- Community management

### Community Contributions
- Use case examples
- Framework-specific helpers
- Documentation improvements
- Bug reports and testing

### Decision Making
- RFCs for major features
- Community input on breaking changes
- Transparent roadmap updates
- Regular community calls

## Conclusion

Injx aims to be the dependency injection library for Python's future, not its past. By focusing on Python 3.13+ and modern development patterns, we can deliver unprecedented type safety, performance, and developer experience.

The path to 1.0 is ambitious but achievable with focused execution on our core differentiators: exceptional testing support, async-first design, and uncompromising type safety.

---

**Last Updated**: January 2025  
**Next Review**: Q2 2025  
**Version**: 1.0  