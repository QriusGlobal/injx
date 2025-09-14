# PRD-004: Phase 2 Container Optimizations

## Document Information
- **PRD Number**: PRD-004
- **Title**: Phase 2 Container Optimizations
- **Author**: Claude (with Gemini architectural review)
- **Date**: 2025-09-14
- **Status**: Approved
- **Dependencies**: PRD-003 (Functional-First Cleanup Architecture)

## Executive Summary

Following the successful implementation of PRD-003's functional-first cleanup architecture which achieved a 51% memory reduction, this PRD proposes Phase 2 optimizations focusing on container consolidation, strategic logging infrastructure, and maintaining architectural simplicity. These changes will improve maintainability, reduce memory overhead by an additional 10-15%, and provide crucial observability into the container's operations.

## Problem Statement

### Current Issues

1. **Data Structure Redundancy**
   - Three separate dictionaries store related provider information:
     - `_providers: dict[Token[object], ProviderLike[object]]`
     - `_registrations: dict[Token[object], _Registration[object]]`
     - `_token_scopes: dict[Token[object], Scope]`
   - This separation creates synchronization risks and memory overhead

2. **Duplicate Cleanup Infrastructure**
   - `CleanupMode` enum in container.py duplicates `CleanupStrategy` functionality
   - `_Registration` dataclass duplicates `ProviderRecord` purpose
   - Two parallel cleanup systems increase complexity

3. **Silent Failure Points**
   - 11 instances of exception swallowing without logging
   - Makes debugging production issues extremely difficult
   - No visibility into container lifecycle or performance

4. **Memory Inefficiencies**
   - Missing `__slots__` on frequently instantiated classes
   - Multiple dictionary headers for related data
   - Redundant storage of computed values

## Proposed Solution

### 1. Container Dictionary Consolidation

#### Design Decision
Consolidate three dictionaries into a single registry using an enhanced `ProviderRecord`:

```python
@dataclass(frozen=True, slots=True)
class ProviderRecord(Generic[T]):
    provider: Callable[..., T]
    cleanup: CleanupStrategy
    scope: Scope
    is_async: bool  # Pre-computed at registration
    dependencies: tuple[Token, ...]  # For circular detection
```

#### Benefits
- **Memory Reduction**: 3 dict headers → 1 (saves ~232 bytes per container)
- **Atomic Operations**: No synchronization issues between dictionaries
- **Simpler Code Paths**: Single source of truth for provider data
- **Faster Circular Detection**: Pre-computed dependency list

#### Concurrency Strategy
Per Gemini's recommendation:
- Single `threading.RLock` protects `_registry` during registration/removal
- Per-token `threading.Lock` dictionary for singleton instantiation
- Maintains performance while ensuring thread safety

### 2. Strategic Logging Infrastructure

#### Logging Architecture
```python
# Main logger for operational events
logger = logging.getLogger("pyinj")

# Separate performance logger
perf_logger = logging.getLogger("pyinj.perf")
```

#### Log Levels and Usage
- **ERROR**: Registration conflicts, circular dependencies, critical failures
- **WARNING** (default): Cleanup failures, override conflicts, potential issues
- **INFO** (opt-in): Container lifecycle, scope transitions, registration events
- **DEBUG** (opt-in): Resolution paths, cache statistics, detailed traces

#### Key Logging Points
1. Container initialization/shutdown
2. Scope entry/exit with timing
3. Registration conflicts with details
4. Resolution failures with full stack
5. Cleanup exceptions (currently swallowed)
6. Performance metrics (separate logger)

#### Performance Considerations
- Default WARNING level prevents log spam
- Separate `pyinj.perf` logger for metrics
- Lazy message formatting for efficiency
- Rate limiting for high-frequency events

### 3. Cleanup Infrastructure Unification

#### Actions
1. Remove `CleanupMode` enum from container.py
2. Remove `_Registration` dataclass from container.py
3. Use existing `CleanupStrategy` and `ProviderRecord` throughout

#### Benefits
- Eliminates conceptual duplication
- Reduces code complexity
- Single cleanup strategy implementation

### 4. Selective `__slots__` Application

#### Apply To
- `ScopeData`: Created per request/session (high frequency)
- Keep existing: `Token`, `ProviderRecord` (already optimized)

#### Skip For
- `Container`: Singleton per application
- `TokenFactory`: Typically one instance
- Classes with dynamic attributes

## Implementation Plan

### Phase A: Foundation (Low Risk)
**Timeline**: Day 1-2

1. Create `period_tasks/` directory structure
2. Implement logging infrastructure:
   ```python
   # src/pyinj/logging.py
   import logging
   
   logger = logging.getLogger("pyinj")
   perf_logger = logging.getLogger("pyinj.perf")
   
   def configure_logging(level=logging.WARNING):
       """Configure PyInj logging."""
       logger.setLevel(level)
   ```
3. Add initial lifecycle logging to container
4. Document logging configuration

### Phase B: Core Consolidation (Medium Risk)
**Timeline**: Day 3-5

1. Create enhanced `ProviderRecord` with new fields
2. Implement migration function:
   ```python
   def _migrate_to_registry(self):
       """Migrate from multiple dicts to single registry."""
       for token, provider in self._providers.items():
           registration = self._registrations.get(token)
           scope = self._token_scopes.get(token, Scope.TRANSIENT)
           is_async = asyncio.iscoroutinefunction(provider)
           deps = self._analyze_dependencies(provider)
           
           self._registry[token] = ProviderRecord(
               provider=provider,
               cleanup=registration.cleanup if registration else CleanupStrategy.NONE,
               scope=scope,
               is_async=is_async,
               dependencies=deps
           )
   ```
3. Update all access patterns to use `_registry`
4. Remove `CleanupMode` and `_Registration`
5. Add comprehensive logging at key points

### Phase C: Optimization (Low Risk)
**Timeline**: Day 6-7

1. Add `__slots__` to `ScopeData`
2. Implement performance metrics collection
3. Add benchmarking suite
4. Run comprehensive test suite
5. Profile memory usage

## Risk Analysis

### Identified Risks

#### High Risk: Concurrency Defects
- **Description**: Dictionary consolidation touches critical shared resources
- **Impact**: Race conditions, data corruption
- **Mitigation**:
  1. Formal concurrency review by experienced developer
  2. Stress testing with high contention scenarios
  3. Thread sanitizer tools during testing
  4. Incremental rollout with canary testing

#### Medium Risk: Performance Regression
- **Description**: Data structure changes may impact specific access patterns
- **Impact**: Slower resolution, increased latency
- **Mitigation**:
  1. Baseline benchmarks before changes
  2. Automated performance regression detection
  3. Statistical significance testing (t-tests)
  4. Percentile tracking (p50, p95, p99)

#### Low Risk: API Compatibility
- **Description**: Internal changes may affect introspection
- **Impact**: Breaking changes for advanced users
- **Mitigation**:
  1. Maintain public API compatibility
  2. Add introspection API if needed
  3. Comprehensive integration tests

### Risk Matrix

| Risk | Probability | Impact | Mitigation Priority |
|------|------------|--------|-------------------|
| Concurrency Defects | Medium | High | Critical |
| Performance Regression | Low | Medium | High |
| API Compatibility | Low | Low | Medium |
| Logging Overhead | Low | Low | Low |

## Change Management

### Affected Components

1. **container.py** (Major Changes)
   - Dictionary consolidation
   - Remove duplicate classes
   - Add logging throughout
   - Update locking strategy

2. **contextual.py** (Minor Changes)
   - Add logging for scope transitions
   - Update to use new `ProviderRecord`

3. **scope_data.py** (Minor Changes)
   - Add `__slots__` for memory optimization
   - Add performance metrics

4. **Tests** (Moderate Changes)
   - Update mocks for new structure
   - Add concurrency tests
   - Add performance benchmarks

### Backward Compatibility

- **Public API**: Unchanged, all changes internal
- **Type Signatures**: Preserved
- **Behavior**: Identical from user perspective
- **Performance**: Expected improvement

### Migration Path

1. Feature branch development
2. Comprehensive testing
3. Performance validation
4. Code review with concurrency focus
5. Merge to main

## Success Criteria

### Functional Requirements
- [ ] All existing tests pass
- [ ] No public API changes
- [ ] Type checking passes (BasedPyright strict)
- [ ] Code coverage maintained or improved

### Performance Requirements
- [ ] Memory usage reduced by 10-15%
- [ ] No statistically significant performance regression
- [ ] p99 latency maintained or improved
- [ ] Logging overhead < 2% in production mode

### Quality Requirements
- [ ] All 11 silent exceptions now logged
- [ ] Comprehensive docstrings for MkDocs
- [ ] Concurrency review completed
- [ ] Stress tests pass without race conditions

### Observability Requirements
- [ ] Container lifecycle visible via logs
- [ ] Performance metrics available
- [ ] Error messages equally or more informative
- [ ] Debug mode provides full resolution traces

## Performance Benchmarking Strategy

### Key Metrics
1. **Provider Registration Time**
   - Measure time to register 1000 providers
   - Track memory allocation

2. **Resolution Time by Scope**
   - Transient: First and subsequent
   - Singleton: First (with lock) and cached
   - Request/Session: With context overhead

3. **Container Operations**
   - Creation time
   - Teardown time with cleanup
   - Memory per provider

### Methodology
- Use `pytest-benchmark` for consistent measurements
- Statistical analysis with t-tests for significance
- Track percentiles (p50, p95, p99) not just means
- Compare against baseline from main branch

### Regression Detection
- Automated CI checks on performance
- Alert on statistically significant regressions
- Generate performance reports for PRs

## Alternative Approaches Considered

### ChainMap Replacement
- **Considered**: Custom lookup implementation
- **Rejected**: Built-in ChainMap is well-tested and optimized
- **Rationale**: No clear performance benefit, adds complexity

### TokenFactory Conversion
- **Considered**: Convert to module-level functions
- **Retained**: Keep as class
- **Rationale**: Provides clear abstraction, caching benefits

### ScopeManager Conversion
- **Considered**: Convert to module functions
- **Retained**: Keep as class with class methods
- **Rationale**: Namespace benefits, logical grouping

### Parallel Implementation
- **Considered**: Gradual migration with dual state
- **Rejected**: Direct refactoring
- **Rationale**: Added complexity not justified for library context

## Testing Strategy

### Unit Tests
- Test each component of consolidated container
- Verify ProviderRecord immutability
- Test logging output at different levels

### Integration Tests
- End-to-end scope management
- Override functionality with new structure
- Auto-registration with consolidated registry

### Concurrency Tests
- High contention scenarios
- Race condition detection
- Deadlock prevention validation

### Performance Tests
- Benchmarks for all key operations
- Memory profiling
- Regression detection

## Documentation Updates

### CLAUDE.md Updates
- Document dictionary consolidation
- Add performance benchmarking section
- Document logging strategy
- Update concurrency model

### User Documentation
- Logging configuration guide
- Performance tuning recommendations
- Debugging with PyInj logs

### API Documentation
- Update docstrings for MkDocs
- Add examples with logging
- Document introspection if added

## Implementation Checklist

### Pre-Implementation
- [ ] Create period_tasks directory
- [ ] Baseline performance benchmarks
- [ ] Set up stress testing environment

### Phase A: Foundation
- [ ] Implement logging infrastructure
- [ ] Add lifecycle logging
- [ ] Document configuration
- [ ] Test logging overhead

### Phase B: Consolidation
- [ ] Create enhanced ProviderRecord
- [ ] Implement registry migration
- [ ] Update access patterns
- [ ] Remove duplicate classes
- [ ] Add comprehensive logging
- [ ] Concurrency review

### Phase C: Optimization
- [ ] Add __slots__ to ScopeData
- [ ] Implement metrics collection
- [ ] Run benchmarks
- [ ] Memory profiling

### Post-Implementation
- [ ] Run full test suite
- [ ] Performance validation
- [ ] Update documentation
- [ ] Create commit with changelog

## Appendix

### A. Current vs Proposed Memory Layout

#### Current (3 dictionaries)
```
Container Instance:
  _providers: dict header (232 bytes) + entries
  _registrations: dict header (232 bytes) + entries  
  _token_scopes: dict header (232 bytes) + entries
  Total overhead: 696 bytes + 3x entry overhead
```

#### Proposed (1 dictionary)
```
Container Instance:
  _registry: dict header (232 bytes) + entries
  Total overhead: 232 bytes + 1x entry overhead
  Savings: 464 bytes + 2x entry overhead
```

### B. Logging Configuration Example

```python
import logging
from pyinj import configure_logging

# Production (default)
configure_logging()  # WARNING level

# Development
configure_logging(logging.INFO)

# Debugging
configure_logging(logging.DEBUG)

# Performance monitoring
perf_handler = logging.StreamHandler()
logging.getLogger("pyinj.perf").addHandler(perf_handler)
logging.getLogger("pyinj.perf").setLevel(logging.INFO)
```

### C. Concurrency Test Example

```python
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor

def stress_test_container(container, iterations=1000):
    """Stress test for race conditions."""
    def register_and_resolve():
        for i in range(iterations):
            token = Token(f"service_{i}", Service)
            container.register(token, lambda: Service())
            instance = container.get(token)
            assert instance is not None
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(register_and_resolve) for _ in range(10)]
        for future in futures:
            future.result()
```

## References

- PRD-003: Functional-First Cleanup Architecture
- Python Enhancement Proposals (PEPs): 561 (Type Checking), 544 (Protocols)
- Threading Best Practices: https://docs.python.org/3/library/threading.html
- Logging Best Practices: https://docs.python.org/3/howto/logging.html

---

*This PRD represents the collaborative output of Claude's implementation expertise and Gemini's architectural review, ensuring both practical implementation details and long-term architectural sustainability.*