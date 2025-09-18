# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and uses [Conventional Commits](https://conventionalcommits.org/) for automated changelog generation.

## [Unreleased]

### Features

- `Dependencies` pattern for grouping multiple dependencies (#PRD-003)
- `Container.get_active()` and `Container.set_active()` class methods (#PRD-001)
- `ContainerProtocol` for type-safe contracts (#PRD-002)
- `AsyncCleanupRequiredError` to exports

### Bug Fixes

- **Critical**: Parameter resolution conflicts in `@inject` decorator causing "multiple values for argument" errors
  - Fixed double parameter passing in sync and async injection wrappers
  - Resolved 5 failing tests while maintaining all existing functionality
  - No performance impact - minimal code changes required
- **Critical**: Memory leak where async locks were never cleaned up
- **High**: Memory leak in singleton lock cleanup for cached values
- **Low**: Memory leak where type index was never cleared
- **Low**: Test method name error calling non-existent `_clear_singletons()` method
- **Low**: Remove invalid asyncio package from dev dependencies
- Circular import between container.py and defaults.py (#PRD-001)
- Type checking errors in injection.py (#PRD-002)
- Thread-safety issues with global default container
- `register_value` method now properly creates ProviderSpec
- Singleton locks now use fast path to check cache before acquiring values (99% of cases)
- Container `clear()` method now properly cleans all internal dictionaries
- Container `__aexit__` now clears async locks after cleanup

### Performance

- Optimized singleton resolution to avoid lock creation for cached values (99% of cases)
- Implemented double-check locking pattern with fast path for better performance
- Reduced lock contention in high-throughput scenarios

### Refactoring

- Container now uses composition instead of inheritance (#PRD-001)
- Simplified module structure and exports (#PRD-004)
- Strengthened deprecation warnings for v2.0.0
- Improved type safety following architectural guidance
- Consolidated type checker configuration in pyproject.toml
- Set reportImportCycles and reportAny as warnings instead of suppressions
- Added .codecontext dev tool directory to .gitignore

### Testing

- Added comprehensive memory leak detection tests
- Added async lock cleanup verification tests
- Added container cleanup tests for all lock types

### Documentation

- Documented ChainMap/MappingProxyType live-view architecture
- Created comprehensive PRD for injection parameter resolution analysis

### Deprecated

- `get_default_container()` - use `Container.get_active()` instead (will be removed in v2.0.0)
- `set_default_container()` - use `Container.set_active()` instead (will be removed in v2.0.0)

### Removed

- `defaults.py` module (functionality moved to Container)
- `InjectionAnalyzer` class (use `analyze_dependencies()` function directly)

### Breaking Changes

- Removed `container.inject()` anti-pattern method (deprecated in favor of `@inject` decorator)

## [0.1.0] - 2025-01-15

### Features

**First Official Release** - This is the first official release of Injx, following the alpha testing phase. Going forward, we adopt clean semantic versioning (0.x.y) without alpha/beta suffixes.

**Note:** This release supersedes 0.1.0a1 and establishes the baseline for the project.

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

## [0.1.0a1] - 2025-01-15

### Features

**Initial Alpha Release** - This is the first alpha release of Injx, a type-safe dependency injection container for Python 3.13+.

**Status**: Alpha - APIs will change. Not recommended for production use.

- Type-safe dependency injection with full static type checking
- Thread-safe and async-safe resolution using ContextVars
- O(1) performance for type lookups with pre-computed hash tokens
- Zero external dependencies
- Protocol-based type safety
- Metaclass auto-registration for declarative DI patterns
- PEP 561 compliant with py.typed support
- Memory efficient with proper cleanup

### Migration

**Why the Rename?** The original pyinj package was released prematurely with version 1.0.0 after only 2 days of development, violating semantic versioning principles. Injx represents a fresh start with:
- Proper version progression (0.1.0 → 0.x → 1.0.0)
- Alpha/Beta/RC release channels
- Commitment to semantic versioning
- Clear communication about stability

**Migration from pyinj:** If you were using pyinj, update your imports:
```python
# Old
from pyinj import Container, Token, inject

# New
from injx import Container, Token, inject
```

The API remains compatible, but the package name has changed.
