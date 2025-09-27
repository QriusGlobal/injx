# Sub-Interpreter Support (PEP 734)

**Labels:** `enhancement`, `python-3.14`

## Description
Enable injx containers to work across Python sub-interpreters for better isolation and parallelism.

## Current State
- No support for `concurrent.interpreters` module
- Containers cannot be shared across interpreters
- No serialization mechanism for cross-interpreter communication

## Requirements
- [ ] Implement ContainerBlueprint for cross-interpreter serialization
- [ ] Support interpreter-local singletons
- [ ] Handle scope semantics per interpreter
- [ ] Document multi-interpreter patterns

## Implementation Approach
```python
from concurrent.interpreters import create, Interpreter

class ContainerBlueprint:
    """Serializable container configuration."""
    def serialize(self) -> bytes:
        """Serialize to cross-interpreter format."""
        ...

    @classmethod
    def deserialize(cls, data: bytes) -> 'ContainerBlueprint':
        """Reconstruct from serialized data."""
        ...

class InterpreterAwareContainer:
    def spawn_worker(self, blueprint: ContainerBlueprint) -> Interpreter:
        """Create worker interpreter with container."""
        interp = create()
        interp.run(setup_code, blueprint_bytes=blueprint.serialize())
        return interp
```

## Use Cases
- CPU-bound parallel processing without GIL contention
- Isolated plugin systems with security boundaries
- Multi-tenant applications with strong isolation
- Parallel test execution in separate interpreters

## Success Criteria
- Container configuration can be serialized/deserialized
- Sub-interpreters can create containers from blueprints
- No Python object sharing violations
- Performance improvement for CPU-bound workloads

## References
- [PEP 734 - Multiple Interpreters in the Stdlib](https://peps.python.org/pep-0734/)
- ROADMAP_PYTHON_3.14.md Section 2