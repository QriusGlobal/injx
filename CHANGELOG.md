# Changelog

All notable changes to Injx will be documented in this file.

## [Unreleased]

## 0.2.0 - 2025-01-16

### Added
- `Dependencies` pattern for grouping multiple dependencies (#PRD-003)
- `Container.get_active()` and `Container.set_active()` class methods (#PRD-001)
- `ContainerProtocol` for type-safe contracts (#PRD-002)
- `AsyncCleanupRequiredError` to exports

### Changed
- Container now uses composition instead of inheritance (#PRD-001)
- Simplified module structure and exports (#PRD-004)
- Strengthened deprecation warnings for v2.0.0

### Fixed
- Circular import between container.py and defaults.py (#PRD-001)
- Type checking errors in injection.py (#PRD-002)
- Thread-safety issues with global default container
- `register_value` method now properly creates ProviderRecord

### Deprecated
- `get_default_container()` - use `Container.get_active()` instead (will be removed in v2.0.0)
- `set_default_container()` - use `Container.set_active()` instead (will be removed in v2.0.0)

### Removed
- `defaults.py` module (functionality moved to Container)
- `InjectionAnalyzer` class (use `analyze_dependencies()` function directly)

### Security
- Improved context isolation with ContextVar

## 0.1.0 - 2025-01-15

### First Official Release

This is the first official release of Injx, following the alpha testing phase. Going forward, we adopt clean semantic versioning (0.x.y) without alpha/beta suffixes.

**Note:** This release supersedes 0.1.0a1 and establishes the baseline for the project.

### Features
- Type-safe dependency injection with full static type checking
- Thread-safe and async-safe resolution using ContextVars
- O(1) performance for type lookups with pre-computed hash tokens
- Zero external dependencies
- Protocol-based type safety
- Metaclass auto-registration for declarative DI patterns
- PEP 561 compliant with py.typed support
- Memory efficient with proper cleanup
- Comprehensive scope management (Singleton, Request, Session, Transient)
- Context manager support for automatic resource cleanup
- Full async/await support with proper cleanup ordering

### Installation
```bash
pip install injx==0.1.0
# or
uv pip install injx==0.1.0
```

## 0.1.0a1 - 2025-01-15 (Pre-release)

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