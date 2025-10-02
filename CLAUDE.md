# PyInj - Project Context and Maintenance Guide

## Project Overview

PyInj is a type-safe dependency injection container for Python 3.13+, designed with production reliability and performance as primary goals. The library provides compile-time type safety, O(1) lookup performance, and zero external dependencies.

### Core Value Proposition
- **Minimal complexity**: ~200 lines of core implementation
- **Type safety**: Full static type checking with protocols and generics
- **Performance**: Constant-time lookups via pre-computed token hashes
- **Async-safe**: ContextVar-based isolation for concurrent execution
- **Zero dependencies**: No external packages required

### Target Use Cases
1. Modern Python applications requiring dependency injection
2. FastAPI/Django/Flask service layer organization
3. Testing with dependency overrides
4. Async-first architectures with proper resource cleanup
5. Multi-tenant applications with request/session scoping

## Architecture & Design Principles

### Type System Architecture
- **Token-based resolution**: Strongly typed tokens (`Token[T]`) as container keys
- **Protocol-driven design**: `Resolvable[T]` protocol for container abstraction
- **Generic type preservation**: Full type inference through decorator chains
- **No string fallbacks**: Explicit rejection of string-based tokens for type safety
- **PEP 561 compliant**: Inline type annotations + `py.typed` marker (no stub files)
- **Forward references**: Uses `from __future__ import annotations` for Python 3.13 compatibility

### Performance Architecture
- **O(1) lookups**: Pre-computed hash values on Token instances
- **Cached metadata**: Function signatures analyzed once at decoration time
- **Lock-free fast paths**: Double-checked locking for singleton initialization
- **Memory efficient**: ~500 bytes overhead per registered service

### Concurrency Model
- **ContextVar isolation**: Thread-safe and async-safe by default
- **Scope hierarchy**: Container → Session → Request with proper isolation
- **LIFO cleanup**: Resources cleaned up in reverse registration order
- **Circuit breaker**: Early failure for async resources in sync contexts

## Repository Structure

```
pyinj/
├── src/pyinj/              # Source code
│   ├── __init__.py         # Public API exports
│   ├── container.py        # Core container implementation
│   ├── contextual.py       # Scoped containers (Request/Session)
│   ├── tokens.py           # Token and Scope definitions
│   ├── injection.py        # Decorator and injection logic
│   ├── analyzer.py         # Dependency analysis
│   ├── scope_manager.py    # ContextVar-based scope orchestration
│   ├── protocols/          # Protocol definitions
│   └── py.typed            # PEP 561 type marker
├── tests/                  # Test suite
├── docs/                   # MkDocs documentation
├── .github/workflows/      # CI/CD pipelines
├── pyproject.toml          # Package configuration
└── CLAUDE.md              # This file
```

### Key Files
- `pyproject.toml`: Package metadata, dependencies, tool configuration
- `src/pyinj/__init__.py`: Version string and public API
- `.github/workflows/ci.yml`: Quality gates (format, lint, type, test)
- `.github/workflows/publish.yml`: PyPI publishing via OIDC
- `release-please-config.json`: Automated release configuration

## Development Workflow

### Trunk-Based Development
- **Single long-lived branch**: `main` is always deployable
- **Feature branches**: Short-lived, merged via squash PRs
- **No release branches**: Direct releases from `main` via tags
- **Linear history**: Squash merges maintain clean commit history

### CI Pipeline (Deterministic Order)
1. **Format check**: `ruff format --check src` (no auto-fix)
2. **Lint**: `ruff check src` (comprehensive rule set)
3. **Type check**: `basedpyright src` (strict mode)
4. **Tests**: `pytest` with coverage reporting
5. **Docs build**: `mkdocs build` (parallel job)

### Quality Requirements
- Type checking: BasedPyright strict mode must pass
- Code formatting: Ruff-formatted (88 char lines)
- Test coverage: Maintained but not strictly enforced
- Documentation: All public APIs documented

### Type Stub Architecture (October 2024 Decision)
**Status**: No `.pyi` stub files - Using inline types only

**Rationale**:
- Source code has comprehensive inline type annotations (Python 3.13+)
- `py.typed` marker provides PEP 561 compliance
- Stub files were 100% redundant with inline types
- Eliminates maintenance burden of keeping stubs synchronized

**Technical Details**:
- Type checkers prioritize `.pyi` over `.py` when both exist
- With inline types + `py.typed`, stub files provide zero additional value
- Modern libraries (Pydantic, httpx) use inline-only approach
- Removed 20 stub files in commit following architectural analysis

**Forward References**:
- **Current**: Requires `from __future__ import annotations` (Python 3.13)
- **Python 3.14+**: Can remove future import when PEP 649 lands (October 2025)
- **Reason**: Python 3.13 lacks native deferred annotation evaluation

## Release Strategy

### Release Automation
- **Release Please**: Google's automated release management
- **Conventional Commits**: Semantic versioning from commit messages
- **Automated changelog**: Generated from commit history
- **Direct from main**: No separate release branches needed

### Version Management
- **SemVer compliance**: MAJOR.MINOR.PATCH versioning
- **Pre-release tags**: `a` (alpha), `b` (beta), `rc` (release candidate)
- **Version locations**:
  - `pyproject.toml`: `[project].version`
  - `src/pyinj/__init__.py`: `__version__`
  - `.release-please-manifest.json`: Current version tracker

### Publishing Process
1. Conventional commits accumulate on `main`
2. Release Please creates PR with version bumps
3. Merging PR creates GitHub Release and tag
4. Tag triggers publish workflow (OIDC trusted publishing)
5. Package published to PyPI automatically

### PyPI Considerations
- **Immutable versions**: Cannot overwrite published versions
- **Yanking**: Use PyPI web UI to deprecate bad releases
- **Trusted Publishing**: OIDC-based, no token storage
- **Project URLs**: Sourced from `[project.urls]` in pyproject.toml

## Technical Constraints

### Runtime Requirements
- **Python 3.13+**: Required for latest typing features
- **No GIL support**: Designed for Python's no-GIL future
- **Zero dependencies**: No external packages in production

### Type Safety Invariants
- Tokens must be `Token[T]` instances or types
- No string-based token resolution
- All public APIs fully typed
- Protocol compliance enforced

### Performance Guarantees
- O(1) token lookup complexity
- Singleton initialization thread-safe
- No memory leaks in scoped resources
- Cleanup always LIFO ordered

## API Design Principles

### Token Design
- **Immutable**: Tokens are hashable and reusable
- **Generic**: `Token[T]` preserves type information
- **Explicit**: No implicit string-to-token conversion

### Scope Hierarchy
```
SINGLETON    # Container lifetime
SESSION      # Session context lifetime  
REQUEST      # Request context lifetime
TRANSIENT    # New instance each resolution
```

### Injection Patterns
- **Decorator-based**: `@inject` for automatic resolution
- **Type-driven**: Resolution based on type annotations
- **Override support**: Scoped overrides for testing
- **Protocol resolution**: Support for protocol-based dependencies

### Error Handling
- **Clear error messages**: Full resolution chain in errors
- **Early failure**: Type mismatches caught immediately
- **Circular detection**: Prevents infinite recursion
- **Async safety**: AsyncCleanupRequiredError for context mismatches

## Testing Patterns

### Override Mechanisms
- `container.override()`: Temporary replacements
- `container.use_overrides()`: Context-managed overrides
- Scoped overrides: Per-request test isolation

### Resource Management
- Context managers for cleanup testing
- Async cleanup verification
- Memory leak detection patterns
- Thread safety validation

## Migration Notes

### From Other DI Libraries
- **dependency-injector**: Use Token instead of providers
- **injector**: Replace decorators with `@inject`
- **No auto-wiring**: Explicit registration required

### Breaking Changes
- v1.1.0: Removed string token support
- v1.1.0: Immutable registrations (no re-registration)
- v1.1.0: Context-managed resources via `register_context`

## Operational Guidelines

### Best Practices
1. Use `TokenFactory` for consistent token creation
2. Prefer singleton scope for stateless services
3. Register async providers for async resolution only
4. Use context managers for resource cleanup
5. Test with scoped overrides, not global mutations

### Common Pitfalls
- Registering async providers for sync `get()` calls
- Missing cleanup for resources with lifecycle
- Circular dependencies in singleton providers
- Type mismatches in protocol implementations

### Performance Tips
- Pre-create tokens at module level
- Use singleton scope for expensive objects
- Avoid transient scope for frequently accessed services
- Cache injection metadata with `@inject` decorator

## Maintenance Notes

### Release Checklist
1. Ensure CI passes on main
2. Version already updated by Release Please
3. Tag created automatically on PR merge
4. PyPI publication automatic via OIDC

### Documentation Updates
- Public API changes require docstring updates
- Architectural changes update this file
- User-facing changes update README.md
- Breaking changes noted in CHANGELOG.md

### Quality Maintenance
- Keep core implementation under 300 lines
- Maintain zero production dependencies
- Ensure O(1) lookup performance
- Preserve full type safety

---

*This document serves as the authoritative reference for PyInj's architecture, design decisions, and maintenance procedures. It should be updated whenever significant architectural decisions are made or development processes change.*