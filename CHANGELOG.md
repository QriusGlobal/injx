# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and uses [Conventional Commits](https://conventionalcommits.org/) for automated changelog generation.

## [Unreleased]

### Features

- `Dependencies` pattern for grouping multiple dependencies (#PRD-003)
- `Container.get_active()` and `Container.set_active()` class methods (#PRD-001)
- `ContainerProtocol` for type-safe contracts (#PRD-002)
- `AsyncCleanupRequiredError` to exports
- **Enhanced Testing**: Integrated `unittest.mock.create_autospec` with MockFactory for signature validation
  - Added `use_autospec` parameter (default: True) for automatic signature checking
  - Smart fallback for primitive types (str, int, etc.) and custom classes
  - Full backward compatibility with existing test code
  - Implements hybrid approach from research_unittest_mock.md

### Bug Fixes

- **Critical**: Fixed deprecated `Token[T](name)` syntax across all tests - migrated to `Token(name, T)` per v1.1.0+ API
  - Updated 50+ test instances across test_testing.py, test_debug.py, test_cycle_detection.py
  - Improves code clarity and compliance with current API
  - Zero breaking changes - tests continue to function correctly

- **Critical**: Fixed undefined `TestScope` type errors via TYPE_CHECKING imports
  - Resolved circular import chains between container.py and testing.py
  - Added proper type imports in protocols/container.py
  - Linting errors reduced from 2 to 0

- **Critical**: Fixed scope reading bugs in debug module (src/injx/debug.py)
  - After dictionary consolidation refactoring, scope information moved from Token to ProviderSpec
  - Fixed 3 locations in debug.py that were reading `token.scope.name` instead of `spec.scope.name`
  - Fixed scope reading in container.py:1650 (get_debug_info method)
  - Tests: test_get_container_state, test_get_dependency_graph, test_container_debug_info_method now pass

- **High**: Fixed protocol compliance in threading test
  - Added missing `__enter__` and `__exit__` methods to CloseableResource test class
  - Now properly matches SupportsClose protocol requirements
  - test_resource_tracking_thread_safety now passes

- **Medium**: Fixed dependency graph API field name mismatch
  - Test was expecting `["name"]` field in graph nodes, but implementation uses `["id"]`
  - Updated test assertion to use correct field
  - Aligns test expectations with current implementation

- **Previous Critical Issues**:
  - Parameter resolution conflicts in `@inject` decorator causing "multiple values for argument" errors
    - Fixed double parameter passing in sync and async injection wrappers
    - Resolved 5 failing tests while maintaining all existing functionality
  - Memory leak where async locks were never cleaned up
  - Memory leak in singleton lock cleanup for cached values
  - Memory leak where type index was never cleared
  - Test method name error calling non-existent `_clear_singletons()` method
  - Remove invalid asyncio package from dev dependencies
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
