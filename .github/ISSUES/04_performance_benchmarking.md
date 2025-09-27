# Performance Benchmarking Suite

**Labels:** `enhancement`

## Description
Implement comprehensive benchmarking to prevent performance regressions and track improvements.

## Current State
- No standardized benchmarking suite
- No CI integration for performance tracking
- No regression detection mechanism
- Limited performance metrics collection

## Requirements
- [ ] Standardized benchmark operations
- [ ] Statistical significance testing
- [ ] CI integration with regression detection
- [ ] Comparison with baseline metrics
- [ ] Memory profiling integration

## Benchmark Operations
```python
class InjxBenchmark:
    OPERATIONS = [
        "register_provider",       # Provider registration time
        "resolve_transient",        # New instance creation
        "resolve_singleton_cold",   # First singleton access
        "resolve_singleton_hot",    # Cached singleton access
        "resolve_scoped",          # Scoped resolution
        "parallel_resolution",      # Multi-threaded access
        "memory_overhead"          # Memory per service
    ]

    def run_benchmark(self, container: Container, iterations: int = 10000):
        # Warmup phase
        # Measurement phase with statistical analysis
        # Return p50, p95, p99 metrics

    def detect_regression(self, baseline: dict, current: dict, threshold: float = 0.1):
        # T-test for statistical significance
        # Report if >10% regression detected
```

## Target Metrics
| Operation | Target | Current |
|-----------|--------|----------|
| Cold lookup | <1μs | ~0.8μs |
| Warm lookup | <0.1μs | ~0.1μs |
| Memory/service | <300B | ~400B |
| Registration | <0.5μs | Unknown |

## Success Criteria
- Automated regression detection in CI
- Performance reports on PRs
- Historical trend tracking
- Comparison with other DI libraries

## Implementation Notes
- Use `timeit` for accurate timing
- Use `tracemalloc` for memory profiling
- Generate JSON reports for CI consumption
- Create visualization dashboard