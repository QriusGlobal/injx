# PyInj v1.2.0 Release Notes

## Release Date: 2025-09-14

## Overview

PyInj v1.2.0 brings significant performance improvements, critical bug fixes, and enhanced monitoring capabilities. This release focuses on production reliability with O(1) circular dependency detection, proper memory management, and correct transient scope semantics.

## 🚀 Performance Improvements

### O(1) Circular Dependency Detection
- **Before**: O(n²) complexity using tuple concatenation
- **After**: O(1) complexity using set-based tracking
- **Impact**: Detection time remains constant even with 1000+ dependency depth
- **Benchmark**: < 100ms for 1000-depth chains (previously would timeout)

### Memory Leak Fixes
- **Singleton Lock Cleanup**: Locks are now properly removed after initialization
- **Before**: Unbounded growth with `defaultdict(threading.Lock)`
- **After**: Locks cleaned up immediately after successful singleton creation
- **Impact**: Long-running applications no longer accumulate memory

### Transient Scope Correctness
- **Fixed**: Removed incorrect WeakValueDictionary caching
- **Before**: Transients were incorrectly cached, violating scope semantics
- **After**: Each resolution creates a new instance as expected
- **Impact**: Proper garbage collection and predictable behavior

## 🐛 Bug Fixes

1. **Transient Scope Violation** - Transients now correctly create new instances every time
2. **Singleton Lock Memory Leak** - Proper cleanup prevents memory accumulation
3. **Dead Code Removal** - Eliminated unused dependency tracking code

## ✨ New Features

### Batch Operations
```python
# Register multiple dependencies at once
container.batch_register([
    (TOKEN_A, provider_a),
    (TOKEN_B, provider_b),
    (TOKEN_C, provider_c),
])

# Resolve multiple dependencies efficiently
results = container.batch_resolve([TOKEN_A, TOKEN_B, TOKEN_C])

# Async batch resolution with parallel execution
results = await container.batch_resolve_async([TOKEN_A, TOKEN_B, TOKEN_C])
```

### Performance Monitoring
```python
# Get container statistics
stats = container.get_stats()
# Returns: {
#     'total_providers': 150,
#     'singletons': 45,
#     'cache_hits': 1200,
#     'cache_misses': 150,
#     'cache_hit_rate': 0.889,
#     'avg_resolution_time': 0.000004
# }

# Direct cache hit rate property
hit_rate = container.cache_hit_rate  # 0.0 to 1.0
```

### Contextual Overrides
```python
# Temporarily override dependencies in a context
with container.use_overrides({LOGGER: fake_logger, DB: test_db}):
    service = container.get(SERVICE)
    # service uses fake_logger and test_db within this context
# Original dependencies restored outside the context
```

## 📊 Testing Improvements

- **31 new tests** added for comprehensive coverage
- **7 memory profiling tests** using `tracemalloc`
- **10 cycle detection tests** validating O(1) performance
- **4 performance benchmark tests**
- **Total**: 156 tests, all passing

## 📚 Documentation

- **Cleaned up code comments**: Removed redundant inline comments, keeping only non-obvious explanations
- **Updated API documentation**: Added all v1.2.0 features with examples
- **Performance documentation**: Real benchmarks and complexity analysis
- **CHANGELOG**: Comprehensive change history

## 💥 Breaking Changes

None. This release maintains full backward compatibility with v1.1.x.

## 🔄 Migration Guide

No migration required. Simply update your dependency:

```bash
# Using pip
pip install --upgrade injx==1.2.0

# Using uv
uv pip install --upgrade injx==1.2.0

# Using poetry
poetry add injx@^1.2.0
```

## 🎯 Highlights for Production Use

1. **Predictable Performance**: O(1) operations ensure consistent response times
2. **Memory Safe**: No memory leaks in long-running applications
3. **Correct Semantics**: Transient scope behaves as documented
4. **Observable**: Built-in performance monitoring for production insights
5. **Thread-Safe**: Proper lock management without memory overhead

## 🙏 Acknowledgments

Thanks to all contributors and users who reported issues and provided feedback for this release.

## 📦 Installation

```bash
pip install injx==1.2.0
```

## 🔗 Links

- [GitHub Repository](https://github.com/QriusGlobal/injx)
- [PyPI Package](https://pypi.org/project/injx/1.2.0/)
- [Documentation](https://github.com/QriusGlobal/injx#readme)
- [Changelog](https://github.com/QriusGlobal/injx/blob/main/CHANGELOG.md)

---

**Full Changelog**: https://github.com/QriusGlobal/injx/compare/v1.1.1...v1.2.0