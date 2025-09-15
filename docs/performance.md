# Performance

Injx delivers production-grade performance with predictable overhead and efficient memory usage.

## Core Performance Metrics

### Resolution Performance
- **Token Lookups**: O(1) with pre-computed hashes
  - < 1 microsecond per lookup
  - Constant time regardless of container size
  - No performance degradation with 1000+ services

### Cycle Detection
- **Algorithm**: O(1) using set-based tracking
  - Improved from O(n²) in v1.1
  - < 100ms even for 1000-depth dependency chains
  - Immediate detection of circular dependencies

### Memory Efficiency
- **Per-Service Overhead**: ~500 bytes
- **Singleton Locks**: Automatically cleaned up after initialization
- **Transient Scope**: Zero caching - no memory retention
- **Token Objects**: ~200 bytes each with `__slots__` optimization

## Benchmarks

### Token Resolution (1000 services)
```python
# Setup: 1000 registered services
# Operation: Resolve service #500
# Result: ~0.4 microseconds (same as service #1)
```

### Singleton Access Performance
```python
# First access (includes creation): ~6 microseconds
# Subsequent accesses: ~4 microseconds
# Thread-safe with minimal lock contention
```

### Injection Decorator Performance
```python
# Function signature analysis: Cached after first call
# Dependency resolution: O(n) where n = number of parameters
# Typical 3-parameter function: < 10 microseconds total
```

## Optimizations

### Pre-computed Hash Values
Tokens compute their hash once at creation, enabling O(1) dictionary lookups without repeated hash calculations.

### Cached Injection Metadata
Function signatures are analyzed once and cached using `functools.lru_cache`, avoiding repeated introspection.

### Memory-Safe Transients
Transient dependencies are never cached, preventing memory leaks and ensuring garbage collection works properly.

### Lock Cleanup
Singleton initialization locks are automatically removed after successful creation, preventing memory accumulation in long-running applications.

