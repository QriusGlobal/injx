# Changelog

All notable changes to Injx will be documented in this file.

## [1.0.0](https://github.com/QriusGlobal/injx/compare/v0.2.1...v1.0.0) (2025-09-17)


### ⚠ BREAKING CHANGES

* Removed container.inject() method to improve architecture

### Bug Fixes

* add pytest-cov and pytest-xdist to CI dependencies ([eb43de7](https://github.com/QriusGlobal/injx/commit/eb43de72584ae25576a925a8812f14b939a13a02))
* consolidate CI workflow and fix venv issues ([b7585c2](https://github.com/QriusGlobal/injx/commit/b7585c2df205c9953e3bf4e3fd18fb36e3b142e7))
* correct Release Please manifest to reflect actual version 0.2.1 ([d042455](https://github.com/QriusGlobal/injx/commit/d042455c4b9d8a54890d0adbd66f57bd4f790622))
* remove invalid asyncio package from dev dependencies ([65287f2](https://github.com/QriusGlobal/injx/commit/65287f2a8dbf65eb4f22d2ceebed00f314a1eded))
* resolve circular import between container and injection modules ([ef9871f](https://github.com/QriusGlobal/injx/commit/ef9871f2eee3bc7ebad19e363144bc4b635c12d6))
* resolve parameter resolution conflicts in injection wrapper ([b44056c](https://github.com/QriusGlobal/injx/commit/b44056cc1f1d104e51162d34cd6ab099ec25dcae))
* resolve type errors in injection and registry modules ([002ce00](https://github.com/QriusGlobal/injx/commit/002ce0075d27f229826798c9b3553e99658bb498))
* set reportImportCycles and reportAny as warnings not suppressions ([89f2414](https://github.com/QriusGlobal/injx/commit/89f241431385c293b3f21eafe2bf373f27fd35cc))
* update Release Please action to working SHA hash and fix YAML formatting ([90399f3](https://github.com/QriusGlobal/injx/commit/90399f3c8a9a8093e092da65693c8718fb7e9e9f))
* use uv run for all commands to ensure tools are available ([882f26b](https://github.com/QriusGlobal/injx/commit/882f26b636a3b4e4307f4c4f0aaf15ce67871ab3))
* use uvx for tools that don't need to be installed ([1f3a021](https://github.com/QriusGlobal/injx/commit/1f3a021d91838797fc9bccd22d9a600b4ad014d3))


### Documentation

* document ChainMap/MappingProxyType live-view architecture ([28aa7fd](https://github.com/QriusGlobal/injx/commit/28aa7fd4d59f8b4d2efb3d66dded3fc85eb09b83))
* update CHANGELOG with recent fixes and improvements ([8a4cfb1](https://github.com/QriusGlobal/injx/commit/8a4cfb1810f6e39fd7b07ff5b8d4ca6da03873b3))


### Code Refactoring

* remove container.inject() anti-pattern ([3ffe736](https://github.com/QriusGlobal/injx/commit/3ffe73651bd341c5100345bc9f9ce172180ee555))

## [Unreleased]

### Fixed
- **Critical**: Parameter resolution conflicts in `@inject` decorator causing "multiple values for argument" errors
  - Fixed double parameter passing in sync and async injection wrappers
  - Resolved 5 failing tests while maintaining all existing functionality
  - No performance impact - minimal code changes required
- **Critical**: Memory leak where async locks were never cleaned up
- **High**: Memory leak in singleton lock cleanup for cached values
- **Low**: Memory leak where type index was never cleared
- **Low**: Test method name error calling non-existent `_clear_singletons()` method
- **Low**: Remove invalid asyncio package from dev dependencies
- Singleton locks now use fast path to check cache before acquiring lock
- Container `clear()` method now properly cleans all internal dictionaries
- Container `__aexit__` now clears async locks after cleanup

### Performance
- Optimized singleton resolution to avoid lock creation for cached values (99% of cases)
- Implemented double-check locking pattern with fast path for better performance
- Reduced lock contention in high-throughput scenarios

### Development
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

### Breaking Changes
- Removed `container.inject()` anti-pattern method (deprecated in favor of `@inject` decorator)

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
- `register_value` method now properly creates ProviderSpec

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
