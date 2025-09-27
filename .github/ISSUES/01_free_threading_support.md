# Free-Threading Support (PEP 703)

**Labels:** `enhancement`, `python-3.14`

## Description
Implement support for Python 3.14's free-threading mode (PEP 703) to enable true parallel execution without the GIL.

## Current State
- Container uses basic `threading.RLock` for synchronization
- No detection of `sys._is_gil_enabled()`
- No optimized paths for free-threaded builds
- Potential contention points in singleton instantiation

## Requirements
- [ ] Detect runtime GIL status using `sys._is_gil_enabled()`
- [ ] Implement double-checked locking pattern for singleton instantiation
- [ ] Use per-token locks instead of global container lock
- [ ] Add memory ordering semantics for cache coherency
- [ ] Support atomic operations where available

## Implementation Hints
```python
class FreeThreadingContainer:
    def __init__(self):
        self._is_free_threaded = not sys._is_gil_enabled() if hasattr(sys, '_is_gil_enabled') else False
        self._singleton_locks: dict[Token, threading.Lock] = {}

    def _resolve_singleton(self, token: Token[T]) -> T:
        # Fast path: lock-free read
        if token in self._singletons:
            return self._singletons[token]

        # Slow path: per-token lock
        lock = self._get_singleton_lock(token)
        with lock:
            # Double-check inside critical section
            if token in self._singletons:
                return self._singletons[token]
            # Create instance...
```

## Success Criteria
- All tests pass with `PYTHON_GIL=0`
- 3-5x speedup for parallel workloads
- No data races detected by thread sanitizers
- Benchmark shows improved multi-threaded performance

## References
- [PEP 703 - Making the Global Interpreter Lock Optional](https://peps.python.org/pep-0703/)
- ROADMAP_PYTHON_3.14.md Section 1