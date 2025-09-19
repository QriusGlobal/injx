# Technical Specification: Injx Python 3.14 Adaptation
## PEP-Style Implementation Roadmap

### Abstract

This document specifies the architectural adaptations required for injx to leverage Python 3.14's free-threading (PEP 703), sub-interpreters (PEP 734), lazy annotations (PEP 649/749), and enhanced type system features (PEP 747/742). Each specification includes formal correctness criteria, performance benchmarks, and risk quantification.

### Specification Status

- **Version**: 1.0.0
- **Python Target**: 3.14.0
- **Implementation Timeline**: 6 months (2025 Q1-Q2)
- **Backward Compatibility**: Python 3.13+ maintained

---

## 1. Free-Threading Support Specification (PEP 703)

### 1.1 Technical Requirements

#### Memory Model Adoption
```c
// Required memory ordering semantics per PEP 703
typedef enum {
    _Py_memory_order_relaxed,   // Atomicity only, no ordering
    _Py_memory_order_acquire,   // Synchronizes with release stores
    _Py_memory_order_release,   // Makes prior writes visible
    _Py_memory_order_seq_cst    // Total ordering (default)
} _Py_memory_order;
```

#### Synchronization Primitive Requirements
- **Registry Operations**: Use `threading.RLock` (maps to `_Py_Mutex` internally)
- **Singleton Instantiation**: Per-token `threading.Lock` with double-checked locking
- **Atomic Operations**: Leverage `_Py_atomic_*` for lock-free fast paths where available

### 1.2 Implementation Specification

#### Phase 1: Core Thread-Safety Architecture
```python
class FreeThreadingContainer:
    """Container with explicit free-threading support per PEP 703."""

    def __init__(self):
        # Detect runtime GIL status
        self._is_free_threaded = not sys._is_gil_enabled() if hasattr(sys, '_is_gil_enabled') else False

        # Hybrid locking strategy
        self._registry_lock = threading.RLock()  # Coarse-grained
        self._singleton_locks: dict[Token, threading.Lock] = {}
        self._lock_factory_mutex = threading.Lock()

        # Atomic-friendly data structures
        self._registry: dict[Token, ProviderSpec] = {}
        self._singletons: dict[Token, Any] = {}

    def _get_singleton_lock(self, token: Token) -> threading.Lock:
        """Get or create a lock for a specific token (thread-safe)."""
        if token not in self._singleton_locks:
            with self._lock_factory_mutex:
                # Double-check pattern
                if token not in self._singleton_locks:
                    self._singleton_locks[token] = threading.Lock()
        return self._singleton_locks[token]

    def _resolve_singleton(self, token: Token[T]) -> T:
        """Implements correct double-checked locking for free-threading."""
        # Fast path: lock-free read (acquire semantics)
        if token in self._singletons:
            return self._singletons[token]

        # Slow path: acquire per-token lock
        lock = self._get_singleton_lock(token)
        with lock:
            # Second check inside critical section
            if token in self._singletons:
                return self._singletons[token]

            # Create instance
            instance = self._create_instance(token)

            # Store with release semantics (implicit in dict.__setitem__)
            self._singletons[token] = instance
            return instance
```

### 1.3 Correctness Criteria

#### Memory Safety Invariants
1. **No data races**: All shared state access synchronized
2. **Memory ordering**: Acquire-release semantics for singleton cache
3. **ABA prevention**: Immutable tokens prevent ABA problems

#### Testing Requirements
```python
def test_concurrent_singleton_instantiation():
    """Verify exactly one instance created under concurrent access."""
    container = FreeThreadingContainer()
    token = Token[Service]()
    instances = []
    barrier = threading.Barrier(100)

    def worker():
        barrier.wait()  # Synchronize start
        instances.append(container.get(token))

    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify singleton invariant
    assert len(set(id(inst) for inst in instances)) == 1
```

### 1.4 Performance Targets

| Operation | GIL Build (Baseline) | Free-Threading Target | Measurement Method |
|-----------|---------------------|----------------------|-------------------|
| Singleton Resolution (cached) | 250ns | 150ns | `timeit` with pre-warmed cache |
| Singleton Resolution (first) | 5μs | 6μs | Single-threaded first access |
| Parallel Resolution (8 threads) | 2μs/thread | 400ns/thread | Concurrent `threading.Barrier` test |
| Registry Mutation | 1μs | 2μs | `register()` with 1000 providers |

### 1.5 Risk Matrix

| Risk | Probability | Impact | Mitigation | Detection |
|------|-------------|---------|------------|-----------|
| Data race in singleton cache | Low (10%) | Critical | Double-checked locking + tests | TSAN, stress tests |
| Performance regression (GIL builds) | Medium (30%) | Medium | Conditional locking strategy | CI benchmarks |
| Memory ordering violation | Low (5%) | Critical | Use standard `threading` primitives | Memory model validator |
| Lock contention hotspot | Medium (40%) | High | Fine-grained locking | Lock profiling |

---

## 2. Sub-Interpreter Support Specification (PEP 734)

### 2.1 Technical Requirements

#### Interpreter Isolation Model
```python
# Per PEP 734, each interpreter has:
# - Independent GIL (if enabled)
# - Separate sys.modules
# - Isolated global state
# - No shared Python objects (except immortals)
```

### 2.2 Implementation Specification

```python
from concurrent.interpreters import create, Interpreter
from typing import Protocol

class ContainerBlueprint(Protocol):
    """Serializable container configuration for cross-interpreter use."""

    def serialize(self) -> bytes:
        """Serialize to cross-interpreter format."""
        ...

    @classmethod
    def deserialize(cls, data: bytes) -> 'ContainerBlueprint':
        """Reconstruct from serialized data."""
        ...

class InterpreterAwareContainer:
    """Container with sub-interpreter support per PEP 734."""

    @classmethod
    def create_blueprint(cls, container: Container) -> ContainerBlueprint:
        """Extract portable configuration from container."""
        return ContainerBlueprint(
            providers=[
                (token.serialize(), spec.to_portable())
                for token, spec in container._registry.items()
            ]
        )

    @classmethod
    def from_blueprint(cls, blueprint: ContainerBlueprint) -> Container:
        """Instantiate container in any interpreter."""
        container = cls()
        for token_data, spec_data in blueprint.providers:
            token = Token.deserialize(token_data)
            spec = ProviderSpec.from_portable(spec_data)
            container._registry[token] = spec
        return container

    def spawn_worker(self, blueprint: ContainerBlueprint) -> Interpreter:
        """Create worker interpreter with container."""
        interp = create()
        interp.run("""
            import pickle
            blueprint = pickle.loads(blueprint_bytes)
            container = Container.from_blueprint(blueprint)
            # Worker ready
        """, blueprint_bytes=blueprint.serialize())
        return interp
```

### 2.3 Correctness Criteria

1. **Isolation invariant**: No Python object sharing between interpreters
2. **Blueprint fidelity**: Reconstructed container semantically equivalent
3. **Scope semantics**: "Interpreter-singleton" clearly documented

### 2.4 Performance Targets

| Operation | Target | Measurement |
|-----------|---------|------------|
| Blueprint serialization | < 10ms for 100 providers | Pickle benchmark |
| Interpreter spawn + container | < 50ms | End-to-end timing |
| Cross-interpreter queue | 10K msg/sec | Queue throughput test |

---

## 3. Type System Enhancement Specification

### 3.1 Lazy Annotations Support (PEP 649/749)

#### Implementation Requirements
```python
from annotationlib import get_annotations, Format

class LazyAnnotationContainer:
    """Container leveraging PEP 649 lazy annotations."""

    @staticmethod
    def extract_dependencies(func: Callable) -> list[type]:
        """Extract type hints using lazy evaluation."""
        # Use VALUE format for runtime type objects
        annotations = get_annotations(func, format=Format.VALUE)
        return [
            ann for ann in annotations.values()
            if isinstance(ann, type) or hasattr(ann, '__origin__')
        ]

    def inject(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator with lazy annotation resolution."""
        # Annotations evaluated only when needed
        deps = None  # Lazy initialization

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal deps
            if deps is None:
                # First call: resolve annotations
                deps = self.extract_dependencies(func)

            # Inject dependencies
            injected = {
                name: self.get(typ)
                for name, typ in zip(func.__code__.co_varnames, deps)
            }
            return func(*args, **injected, **kwargs)

        return wrapper
```

### 3.2 TypeForm Support (PEP 747)

```python
from typing import TypeForm

class TypeAwareContainer:
    """Container with TypeForm support for type expressions."""

    def register_type_form(self, form: TypeForm[T], provider: Callable[[], T]) -> None:
        """Register provider for a type form (e.g., int | str)."""
        token = self._type_form_to_token(form)
        self.register(token, provider)

    def get_by_type_form(self, form: TypeForm[T]) -> T:
        """Resolve dependency by type form."""
        token = self._type_form_to_token(form)
        return self.get(token)

    @staticmethod
    def _type_form_to_token(form: TypeForm) -> Token:
        """Convert type form to token."""
        # Implementation handles Union, Generic, etc.
        if hasattr(form, '__origin__'):
            # Handle generics like list[int]
            return Token[form.__origin__](qualifier=str(form))
        return Token[form]()
```

### 3.3 TypeIs for Type Narrowing (PEP 742)

```python
from typing import TypeIs

class NarrowingContainer:
    """Container with type narrowing support."""

    def has_provider(self, token: Token[T]) -> TypeIs[Token[T]]:
        """Type guard for token availability."""
        return token in self._registry

    def get_optional(self, token: Token[T]) -> T | None:
        """Get with type narrowing."""
        if self.has_provider(token):
            # Type checker knows token exists
            return self.get(token)
        return None
```

### 3.4 Success Criteria

1. **Zero-overhead annotations**: No evaluation unless accessed
2. **Type form fidelity**: Correct handling of complex type expressions
3. **Static type safety**: Full mypy/pyright strict mode compliance

---

## 4. Performance Benchmarking Specification

### 4.1 Benchmark Suite Design

```python
class InjxBenchmark:
    """Standardized benchmark suite per Python PEP 8 § Performance."""

    OPERATIONS = [
        "register_provider",
        "resolve_transient",
        "resolve_singleton_cold",
        "resolve_singleton_hot",
        "resolve_scoped",
        "parallel_resolution"
    ]

    def run_benchmark(self, container: Container, iterations: int = 10000) -> dict:
        """Run complete benchmark suite."""
        results = {}

        for operation in self.OPERATIONS:
            method = getattr(self, f"bench_{operation}")

            # Warmup
            for _ in range(100):
                method(container)

            # Measure
            times = []
            for _ in range(iterations):
                start = time.perf_counter_ns()
                method(container)
                times.append(time.perf_counter_ns() - start)

            # Statistical analysis
            results[operation] = {
                "p50": statistics.quantiles(times, n=100)[49],
                "p95": statistics.quantiles(times, n=100)[94],
                "p99": statistics.quantiles(times, n=100)[98],
                "mean": statistics.mean(times),
                "stdev": statistics.stdev(times)
            }

        return results
```

### 4.2 Regression Detection

```python
def detect_regression(baseline: dict, current: dict, threshold: float = 0.1) -> list[str]:
    """Detect statistically significant regressions."""
    regressions = []

    for operation in baseline:
        base_mean = baseline[operation]["mean"]
        curr_mean = current[operation]["mean"]
        base_stdev = baseline[operation]["stdev"]

        # T-test for significance
        t_stat = abs(curr_mean - base_mean) / base_stdev

        # Check if regression exceeds threshold
        if curr_mean > base_mean * (1 + threshold) and t_stat > 2.0:
            regressions.append(f"{operation}: {curr_mean/base_mean:.2f}x slower")

    return regressions
```

---

## 5. Migration Strategy

### 5.1 Compatibility Layer

```python
class CompatibleContainer(Container):
    """Container with Python 3.13+ compatibility."""

    def __init__(self):
        super().__init__()

        # Runtime feature detection
        self._features = {
            "free_threading": hasattr(sys, "_is_gil_enabled"),
            "subinterpreters": "concurrent.interpreters" in sys.modules,
            "lazy_annotations": "annotationlib" in sys.modules,
            "typeis": hasattr(typing, "TypeIs")
        }

    def _select_strategy(self) -> ResolutionStrategy:
        """Select optimal strategy for runtime."""
        if self._features["free_threading"] and not sys._is_gil_enabled():
            return FreeThreadingStrategy()
        return StandardStrategy()
```

### 5.2 Deprecation Timeline

| Feature | Deprecated | Removed | Alternative |
|---------|------------|---------|-------------|
| String tokens | v1.1.0 | v2.0.0 | `Token[T]` instances |
| Eager annotations | v2.0.0 | v3.0.0 | Lazy evaluation |
| GIL-only optimizations | v2.1.0 | v3.0.0 | Free-threading aware |

---

## 6. Risk Assessment Matrix

### 6.1 Technical Risks

| Risk Category | Specific Risk | Probability | Impact | RPN* | Mitigation |
|---------------|--------------|-------------|---------|------|------------|
| Concurrency | Data race in cache | 0.1 | 10 | 1.0 | DCLP + TSAN |
| Concurrency | Deadlock | 0.05 | 10 | 0.5 | Lock ordering |
| Performance | 2x slower resolution | 0.3 | 5 | 1.5 | Profiling + optimization |
| Compatibility | Breaking change | 0.2 | 8 | 1.6 | Compatibility layer |
| Type Safety | Runtime type error | 0.1 | 7 | 0.7 | Static analysis |

*RPN = Risk Priority Number (Probability × Impact)

### 6.2 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|---------|------------|
| Slow Python 3.14 adoption | 0.7 | 3 | Maintain 3.13 support |
| Ecosystem incompatibility | 0.4 | 6 | Document compatible libraries |
| Complex migration | 0.5 | 4 | Migration guide + tooling |

---

## 7. Validation Criteria

### 7.1 Functional Requirements

- [ ] All existing tests pass on Python 3.14
- [ ] Free-threading tests pass with `PYTHON_GIL=0`
- [ ] Sub-interpreter tests validate isolation
- [ ] Type checker validation in strict mode

### 7.2 Performance Requirements

- [ ] No regression > 10% for GIL-enabled builds
- [ ] 3-5x speedup for parallel workloads (free-threading)
- [ ] Memory overhead < 5% increase
- [ ] Startup time < 10ms for 1000 providers

### 7.3 Quality Gates

```yaml
# CI/CD Quality Gates
quality_gates:
  coverage:
    threshold: 95%
    free_threading_specific: 90%

  benchmarks:
    regression_threshold: 10%
    statistical_significance: 0.05

  static_analysis:
    mypy: "--strict"
    pyright: "strict"
    ruff: "ALL"

  thread_safety:
    tsan: enabled
    helgrind: enabled
    stress_test_duration: 3600s
```

---

## 8. Conclusion

This specification provides a comprehensive technical roadmap for adapting injx to Python 3.14's paradigm-shifting features. The implementation prioritizes:

1. **Correctness**: Formal verification of thread-safety invariants
2. **Performance**: Quantified targets with statistical validation
3. **Compatibility**: Graceful degradation for older Python versions
4. **Type Safety**: Leveraging cutting-edge type system features

Success is measured through rigorous benchmarking, comprehensive testing including thread sanitizers, and maintaining backward compatibility while delivering substantial performance improvements in free-threaded environments.

The 6-month implementation timeline allows for iterative development with continuous validation against the specified criteria, ensuring injx becomes the reference implementation for modern Python dependency injection.

---

*Document Version: 1.0.0 | Last Updated: 2024*
*Target Python Version: 3.14.0 | Compatibility: 3.13+*
*Review Schedule: Monthly during implementation phase*