# Thread-Safety Audit

**Labels:** `enhancement`

## Description
Comprehensive audit and improvement of thread-safety guarantees across the library.

## Current State
- Basic thread safety with `threading.RLock`
- ContextVar usage for async isolation
- Some potential race conditions in edge cases
- No formal verification of thread safety

## Requirements
- [ ] Document all synchronization points
- [ ] Verify lock ordering to prevent deadlocks
- [ ] Test with thread sanitizers (TSAN)
- [ ] Stress test concurrent operations
- [ ] Create thread-safety documentation

## Areas to Audit

### 1. Singleton Instantiation
```python
# Current pattern - needs verification
with self._lock:
    if token not in self._singletons:
        self._singletons[token] = create_instance()
```

### 2. Registry Mutations
- Provider registration during resolution
- Override management
- Scope transitions

### 3. Context Variable Usage
- Proper isolation verification
- No leakage between tasks
- Cleanup in error cases

### 4. Resource Cleanup
- LIFO ordering enforcement
- Exception safety
- Async cleanup coordination

## Testing Approach

### Stress Test
```python
import threading
import random

def stress_test_concurrent_resolution():
    container = Container()
    barrier = threading.Barrier(100)
    results = []
    errors = []

    def worker():
        barrier.wait()  # Synchronize start
        try:
            for _ in range(1000):
                # Random operations
                op = random.choice(['get', 'register', 'override'])
                if op == 'get':
                    container.get(random_token())
                elif op == 'register':
                    container.register(new_token(), factory)
                else:
                    container.override(existing_token(), mock)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread safety violations: {errors}"
```

### Thread Sanitizer Integration
```bash
# Run with thread sanitizer
PYTHONMALLOC=malloc python -X dev -m pytest tests/test_thread_safety.py
```

## Documentation Requirements
- Thread-safety guarantees per operation
- Safe usage patterns
- Known limitations
- Performance implications

## Success Criteria
- No data races detected by TSAN
- No deadlocks under stress testing
- Clear thread-safety documentation
- Performance maintained or improved
- All existing tests pass with concurrent execution