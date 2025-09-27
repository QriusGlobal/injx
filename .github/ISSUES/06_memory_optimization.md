# Memory Optimization

**Labels:** `enhancement`

## Description
Reduce memory overhead per dependency registration and resolution.

## Current Metrics
- ~400 bytes per service
- ContextVar overhead
- Token hash caching
- Provider metadata storage

## Goals
- [ ] Reduce to <300 bytes per service
- [ ] Optimize token storage with interning
- [ ] Improve cache efficiency
- [ ] Profile memory hotspots
- [ ] Lazy load rarely-used metadata

## Optimization Opportunities

### 1. Extended `__slots__` Usage
```python
class ProviderSpec:
    __slots__ = ('provider', 'scope', 'is_async', 'cleanup', '_hash')

class Token:
    __slots__ = ('name', 'type_', 'scope', 'qualifier', 'tags', '_hash')
```

### 2. String Interning
```python
class TokenFactory:
    _interned_names: dict[str, str] = {}

    @classmethod
    def create(cls, name: str, ...) -> Token:
        # Intern common strings
        interned = cls._interned_names.setdefault(name, name)
        return Token(interned, ...)
```

### 3. Lazy Metadata Loading
```python
class LazyProviderSpec:
    __slots__ = ('_provider', '_metadata')

    @property
    def metadata(self):
        if self._metadata is None:
            self._metadata = self._load_metadata()
        return self._metadata
```

## Measurement Approach
```python
import tracemalloc

def measure_memory_per_service():
    tracemalloc.start()
    container = Container()

    snapshot1 = tracemalloc.take_snapshot()
    for i in range(1000):
        container.register(Token(f"service_{i}", Service), lambda: Service())
    snapshot2 = tracemalloc.take_snapshot()

    diff = snapshot2.compare_to(snapshot1, 'lineno')
    total_kb = sum(stat.size_diff for stat in diff) / 1024
    per_service = total_kb / 1000
    print(f"Memory per service: {per_service:.2f} KB")
```

## Success Criteria
- <300 bytes per service registration
- No performance regression
- Backward compatibility maintained
- Measurable improvement in large containers (10k+ services)

## Comparison Target
| Library | Memory/Service |
|---------|---------------|
| injx (current) | ~400B |
| injx (target) | <300B |
| python-inject | ~200B |
| dependency-injector | ~300B |