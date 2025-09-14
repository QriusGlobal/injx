# Changelog

All notable changes to Injx will be documented in this file.

## [Unreleased]

### Notes
- Injx is a complete rewrite and rename of the pyinj package
- Starting fresh with proper semantic versioning from 0.1.0-alpha.1
- Previous pyinj versions (0.0.2, 1.0.0-1.2.0) are deprecated

## 0.1.0-alpha.1 (Not Released Yet)

### Initial Alpha Release

This is the first alpha release of Injx, a type-safe dependency injection container for Python 3.13+. 

**Status**: Alpha - APIs will change. Not recommended for production use.

### Features (Inherited from pyinj)
- Type-safe dependency injection with full static type checking
- Thread-safe and async-safe resolution using ContextVars
- O(1) performance for type lookups with pre-computed hash tokens
- Zero external dependencies
- Protocol-based type safety
- Metaclass auto-registration for declarative DI patterns
- PEP 561 compliant with py.typed support
- Memory efficient with proper cleanup

### Why the Rename?
The original pyinj package was released prematurely with version 1.0.0 after only 2 days of development, violating semantic versioning principles. Injx represents a fresh start with:
- Proper version progression (0.1.0 → 0.x → 1.0.0)
- Alpha/Beta/RC release channels
- Commitment to semantic versioning
- Clear communication about stability

### Migration from pyinj
If you were using pyinj, update your imports:
```python
# Old
from pyinj import Container, Token, inject

# New  
from injx import Container, Token, inject
```

The API remains compatible, but the package name has changed.

### Known Issues
- This is an alpha release - expect breaking changes
- Documentation is being updated
- Performance optimizations are ongoing

### Contributors
- Qrius Global team

---

For historical changes from the pyinj package, see the [archived repository](https://github.com/qriusglobal/pyinj).