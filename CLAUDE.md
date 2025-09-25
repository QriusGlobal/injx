# Injx - Project Context and Maintenance Guide

## Project Overview

Injx is a type-safe dependency injection container for Python 3.13+, designed with production reliability and performance as primary goals. The library provides compile-time type safety, O(1) lookup performance, and zero external dependencies.

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

### Performance Architecture
- **O(1) lookups**: Pre-computed hash values on Token instances
- **Cached metadata**: Function signatures analyzed once at decoration time
- **Lock-free fast paths**: Double-checked locking for singleton initialization
- **Memory efficient**: ~500 bytes overhead per registered service

### Performance Benchmarking
To prevent regressions and validate optimizations, a consistent benchmarking strategy is required:
- **Key Metrics**: Benchmarks will focus on:
  - Provider registration time
  - Resolution time for each scope (transient, singleton, etc.), including first and subsequent lookups
  - Container creation and teardown time
  - Memory usage per provider and per container
- **Methodology**: Performance tests will use statistical analysis (e.g., t-tests) to determine the significance of any changes in performance.
- **Regression Thresholds**: Instead of hard-coded thresholds, regressions will be evaluated based on their statistical significance.
- **Percentile Tracking**: Key latency metrics will be tracked at the 50th, 95th, and 99th percentiles to monitor tail latency and ensure predictable performance under load.

### Concurrency Model
- **ContextVar isolation**: Thread-safe and async-safe by default
- **Scope hierarchy**: Container → Session → Request with proper isolation
- **LIFO cleanup**: Resources cleaned up in reverse registration order
- **Circuit breaker**: Early failure for async resources in sync contexts

## Architectural Evolution

This section outlines planned architectural improvements to enhance maintainability, performance, and clarity.

### Dictionary Consolidation

To simplify the internal state management, the various dictionaries (`_providers`, `_singletons`, etc.) will be consolidated into a single `_registry`.

- **Motivation**: Reduce complexity, create a single source of truth for provider information, and simplify logic for features like overrides and dependency analysis.

- **ProviderSpec Design**: The `_registry` will map tokens to a `ProviderSpec`. This will be a frozen dataclass to keep it lightweight, while caching key information computed at registration time to improve performance. A generic `metadata` field is rejected to maintain a minimal memory footprint and focused design.
  ```python
  @dataclass(frozen=True, slots=True)
  class ProviderSpec(Generic[T]):
      provider: Callable[..., T]
      cleanup: CleanupStrategy
      scope: Scope
      is_async: bool
      dependencies: tuple[Token, ...]
  ```

- **Concurrency Strategy**: The existing granular locking strategy will be adapted. A single `threading.RLock` will protect the `_registry` dictionary itself during provider registration and removal. For singleton instantiation, the per-token `threading.Lock` will be maintained in a separate dictionary (`dict[Token, threading.Lock]`), keyed by the token, to prevent contention during resolution. This balances simplicity with performance by avoiding a single global lock for all operations.

- **Migration Strategy**: The refactoring will be performed directly within a feature branch, accompanied by a comprehensive suite of tests to ensure no regressions. A gradual, parallel implementation is deemed to add unnecessary complexity and risk for a library context.

- **Impact Analysis**: This consolidation is expected to simplify features like overrides, "given" instances, and auto-registration by providing a unified view of providers. It will not negatively impact the type index and should make dependency-related features easier to implement and reason about.

## Repository Structure

```
injx/
├── src/injx/              # Source code
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
- `src/injx/__init__.py`: Version string and public API
- `.github/workflows/ci.yml`: Quality gates (format, lint, type, test)
- `.github/workflows/publish.yml`: PyPI publishing via OIDC
- `release-please-config.json`: Automated release configuration

## Development Workflow

### Package Management with UV
This project uses **UV** for fast, reliable Python package management.

#### Environment Setup
- **Virtual environment**: Located at `.venv/` in the project root
- **Python runtime**: Managed by UV within the virtual environment
- **Package installation**: All dependencies managed through UV

#### UV Commands for Development
```bash
# Running Python scripts
uv run python script.py

# Running pytest
uv run pytest
uv run pytest tests/test_performance.py -xvs

# Running linting and formatting
uv run ruff format src tests
uv run ruff check src tests

# Running type checking
uv run basedpyright src

# Installing dependencies
uv pip install -e .  # Install project in editable mode
uv pip install -r requirements-dev.txt  # Install dev dependencies

# Managing packages
uv pip list  # List installed packages
uv pip show injx  # Show package details
```

#### Important Notes
- **Always use `uv run`**: Ensures commands execute in the correct virtual environment
- **No global Python**: All Python commands should be prefixed with `uv run`
- **Fast installation**: UV provides 10-100x faster package installation than pip
- **Lockfile support**: UV can generate and use lockfiles for reproducible builds

### Trunk-Based Development
- **Single long-lived branch**: `main` is always deployable
- **Feature branches**: Short-lived, merged via squash PRs
- **No release branches**: Direct releases from `main` via tags
- **Linear history**: Squash merges maintain clean commit history

### CI Pipeline (Deterministic Order)
1. **Format check**: `uv run ruff format --check src` (no auto-fix)
2. **Lint**: `uv run ruff check src` (comprehensive rule set)
3. **Type check**: `uv run basedpyright src` (strict mode)
4. **Tests**: `uv run pytest` with coverage reporting
5. **Docs build**: `uv run mkdocs build` (parallel job)

### Quality Requirements
- Type checking: BasedPyright strict mode must pass
- Code formatting: Ruff-formatted (88 char lines)
- Test coverage: Maintained but not strictly enforced
- Documentation: All public APIs documented

## Commit Standards for AI Agents

### Overview
This project follows the **semantic-release standard** (Angular Convention) for commit messages to automate semantic versioning and releases. Every commit message directly controls version bumps and changelog generation. AI agents MUST use the `/commit` command to ensure commits follow standards.

**Note**: This project uses the semantic-release/Angular Convention where only `fix` and `feat` commits trigger releases. Performance improvements (`perf`) are treated as non-release commits.

### Using the Commit Agent
**ALWAYS use the `/commit` slash command for commits. Never use raw `git commit`.**

```bash
# After making changes:
/commit

# The agent will:
# 1. Analyze your changes
# 2. Propose conventional commit(s)
# 3. Wait for your approval
# 4. Execute the commit(s)
```

### Commit Types and Release Impact

| Type | Description | Version Impact | Example |
|------|-------------|----------------|---------|
| `fix` | Bug fixes | Patch (0.2.1 → 0.2.2) | `fix(container): resolve memory leak` |
| `feat` | New features | Minor (0.2.1 → 0.3.0) | `feat(tokens): add token validation` |
| `docs` | Documentation | None | `docs: update API guide` |
| `style` | Formatting | None | `style: apply ruff formatting` |
| `refactor` | Code restructuring | None | `refactor(core): simplify logic` |
| `test` | Test changes | None | `test: add edge case coverage` |
| `chore` | Maintenance | None | `chore: update dependencies` |
| `ci` | CI/CD changes | None | `ci: optimize workflow caching` |
| `perf` | Performance improvements | None | `perf: optimize hash computation` |
| `build` | Build system changes | None | `build: update package config` |

### Breaking Changes
Use `!` after type or `BREAKING CHANGE:` in footer for major version bumps:
```
feat(api)!: remove deprecated methods

BREAKING CHANGE: Removed string-based token support.
Use Token instances instead.
```

### Commit Message Format

#### Standard Format
```
type(scope): subject

[optional body]

[optional footer]
```

#### Rules
- **Subject**: Max 50 chars, imperative mood, no period
- **Body**: Wrap at 72 chars, explain what and why
- **Scope**: Module name (container, tokens, injection, etc.)
- **Footer**: Breaking changes, issue references

### Examples

#### Bug Fix
```
fix(container): prevent singleton initialization race condition

Thread-safe double-checked locking ensures singleton providers
initialize exactly once even under concurrent access.

Fixes #123
```

#### Feature Addition
```
feat(injection): support optional dependencies with Optional[T]

Optional dependencies return None when not registered instead
of raising ResolutionError. Enables graceful degradation.
```

#### Multiple Related Changes
```
refactor(tokens): consolidate token validation logic

- Move validation to tokens.py
- Add comprehensive error messages
- Improve performance with caching
```

### AI Agent Workflow

1. **Make changes**: Implement the required functionality
2. **Run `/commit`**: Triggers the conventional commit agent
3. **Review proposal**: Agent analyzes changes and proposes commit(s)
4. **Approve/Edit**: Confirm or modify the proposed commit
5. **Automatic execution**: Agent creates the commit with proper format

### Common Mistakes to Avoid

- **DON'T** mix unrelated changes in one commit
- **DON'T** use past tense ("fixed" vs "fix")
- **DON'T** exceed 50 characters in subject
- **DON'T** forget scope for module-specific changes
- **DON'T** commit without running tests
- **DON'T** use vague messages like "update files"

### Testing Commit Impact

Before committing, consider:
- Will this trigger the right version bump?
- Is the scope accurate?
- Are related tests included?
- Is the message clear for the changelog?

Remember: Your commits control the automated release pipeline. Accuracy matters.

### Modernized Commit Validation System

This project enforces semantic versioning through an industry-standard commit validation system using **commitizen + commitlint** with a custom Node.js validation script that maintains our strict file-based hierarchy rules.

#### System Architecture

**Industry-Standard Foundation:**
- **commitizen**: Enhanced commit authoring experience with `cz commit`
- **commitlint**: Robust validation engine via `@commitlint/lint` API
- **Custom router**: Smart file analysis and dynamic ruleset selection

#### Single Hook Installation

**REQUIRED for all developers and agents:**
```bash
# Install modernized validation hook
uv run pre-commit install --hook-type commit-msg
```

#### Validation Process

**Smart Validation (`scripts/validate-commit.js`)**
- Analyzes staged files to determine context (src/, infrastructure, config)
- Dynamically applies appropriate commitlint ruleset based on strict hierarchy
- Provides clear, standardized error messages from commitlint engine
- ~75 lines of custom logic vs. previous 500+ lines

#### Strict Priority Hierarchy (No Loopholes)

**Priority 1 (HIGHEST): src/ Changes**
- **Files**: Any file in `src/` directory
- **Required Prefixes**: `feat`, `fix`, `perf`, `refactor`
- **Beats Everything**: Even if mixed with infrastructure/config

**Priority 2: Infrastructure Changes**
- **Files**: `.github/workflows/`, `tests/`, `docs/`, `scripts/`, `*.md`
- **Required Prefixes**: `chore`, `ci`, `docs`, `test`, `build`, `style`
- **Beats Config**: Infrastructure rules override config rules

**Priority 3 (LOWEST): Config Files Only**
- **Files**: `pyproject.toml`, `uv.lock`, `Dockerfile`
- **Allowed Prefixes**: Any (both library and infrastructure)
- **Lowest Priority**: Only applies when no src/ or infrastructure files

#### Critical Mixed Commits Behavior

```bash
# ✅ src/ + anything = library prefix required
git add src/container.py .github/workflows/ci.yml pyproject.toml
git commit -m "feat(container): add feature"  # ← ALLOWED

# ❌ src/ + anything ≠ infrastructure prefix
git add src/container.py .github/workflows/ci.yml
git commit -m "ci(workflows): update"  # ← BLOCKED

# ✅ Infrastructure + config = infrastructure prefix required
git add .github/workflows/ci.yml pyproject.toml
git commit -m "ci(workflows): update workflow"  # ← ALLOWED

# ❌ Infrastructure + config ≠ library prefix (THE FIXED VULNERABILITY)
git add .github/workflows/ci.yml pyproject.toml
git commit -m "feat(workflows): add workflow"  # ← BLOCKED ✅
```

#### Automatic Prefix Suggestions

**The prepare hook suggests:**
- `feat(container): ` for src/container.py changes
- `ci(workflows): ` for .github/workflows/ changes
- `test: ` for tests/ changes
- `docs: ` for documentation changes
- `chore(deps): ` for pyproject.toml changes

#### Environment Overrides for Edge Cases

```bash
# Manual override for complex scenarios
INJX_COMMIT_TYPE=fix INJX_COMMIT_SCOPE=security git commit
```

#### Examples with Modern Validation

```bash
# ✅ Priority 1: src/ changes - library prefixes required
feat(container): add async support
# Files: src/container.py, tests/test_container.py, docs/api.md
# [injx-validator] Applying "Source Code" validation rules.

# ✅ Priority 2: Infrastructure changes - infrastructure prefixes required
ci(workflows): update release process
# Files: .github/workflows/release.yml, pyproject.toml
# [injx-validator] Applying "Infrastructure" validation rules.

# ✅ Priority 3: Config only - any prefix allowed
feat(deps): add new dependency
# Files: pyproject.toml (only)
# [injx-validator] Applying "Configuration" validation rules.

# ❌ BLOCKED: Infrastructure with library prefix
feat(workflows): add CI workflow  # Should be 'ci' or 'chore'
# [injx-validator] Applying "Infrastructure" validation rules.
# ❌ Commit message validation failed:
#   - type must be one of [chore, ci, docs, test, build, style, refactor]

# ❌ BLOCKED: src/ with infrastructure prefix
chore(container): add new feature  # Should be 'feat'
# [injx-validator] Applying "Source Code" validation rules.
# ❌ Commit message validation failed:
#   - type must be one of [feat, fix, perf, refactor]
```

#### Agent Integration Instructions

**For AI Agents using this codebase:**
1. **Use project sub-agent**: Run `./.claude/sub-agents/commit/commit.sh` for interactive commits
2. **Alternative**: Run `uv run cz commit` for interactive commit authoring
3. **Handle failures**: Review validation messages for specific guidance
4. **Emergency bypass**: Use `git commit --no-verify` only with documented reason
5. **Dependencies**: Node.js dependencies managed automatically by pre-commit

#### Project Sub-Agent for Commits

This project includes a Claude Code sub-agent for handling semantic commits:
- **Location**: `.claude/sub-agents/commit/commit.sh`
- **Usage**: `./.claude/sub-agents/commit/commit.sh` (native shell script)
- **Features**:
  - Analyzes staged changes and proposes conventional commits
  - Determines correct commit type based on file changes
  - Suggests appropriate scope from module names
  - Shows version impact (patch/minor/major/none)
  - Interactive mode with edit capability
  - Auto-accept mode with `-y` flag

#### Slash Command Integration

**Usage**: `/commit` - Analyzes staged changes and proposes a semantic commit

The `/commit` slash command provides an interactive interface to the commit sub-agent:
- **Default behavior**: Analyzes all staged files and proposes an appropriate commit
- **Auto-accept**: `/commit -y` to automatically accept the proposed commit
- **Smart detection**: Automatically determines commit type based on file changes
- **Version awareness**: Shows whether commit will trigger a release (patch/minor/major)

The command intelligently categorizes changes:
- src/ changes → feat or fix (triggers releases)
- tests/ changes → test commits
- docs/ changes → docs commits
- .github/ changes → ci commits
- Config files → chore commits

#### Escape Hatch (Audited)
- **Local bypass**: `git commit --no-verify` for exceptional cases
- **CI auditing**: Add `Bypass-Validation: [reason]` to commit body for review
- **Justification required**: All bypasses must explain why rules don't apply

#### Implementation Details
- **Two hooks**: prepare-commit-msg + commit-msg for complete coverage
- **No loopholes**: Strict priority hierarchy eliminates mixed commit vulnerabilities
- **Regression protection**: Comprehensive test suite prevents rule weakening
- **Clear guidance**: Detailed error messages with specific fix instructions
- **Performance**: Fast file classification using git diff analysis

## Release Strategy

### Release Automation
- **python-semantic-release**: Automated versioning from conventional commits
- **workflow_dispatch**: Manual trigger with human control over timing
- **Conventional Commits**: Determines version bumps automatically
- **Automated changelog**: Generated from commit history
- **Trunk-based development**: All work on `main`, no release branches

### Version Management
- **SemVer compliance**: MAJOR.MINOR.PATCH versioning
- **Pre-release tags**: `a` (alpha), `b` (beta), `rc` (release candidate)
- **Single source of truth**: Version in `pyproject.toml`
- **Runtime access**: Via `importlib.metadata.version("injx")`

### Publishing Process
1. Developers push conventional commits to `main`
2. Every push to `main` publishes to TestPyPI for validation
3. When ready, trigger release workflow via GitHub Actions
4. Workflow calculates version from commits since last release
5. Automated: version bump → changelog → tag → PyPI publish → docs deploy

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

## Architectural Stance

This section documents key architectural decisions, reinforcing the library's design philosophy in response to common patterns found in other dependency injection frameworks.

### 1. Token Design: Strict Typing over Flexibility

**Decision:** The current token design, based on frozen dataclasses with pre-computed hashes, is affirmed as the optimal approach. We will not introduce more flexible, string-based, or implicit token mechanisms.

- **Rationale:**
  - **Type Safety:** `Token[T]` is the cornerstone of our compile-time safety guarantee. Allowing string-based fallbacks or other non-typed keys would undermine this core value proposition and re-introduce the very class of runtime errors `injx` is designed to prevent.
  - **Performance:** Pre-computed hashes ensure O(1) lookup complexity, which is critical for production performance.
  - **Clarity:** Explicit `Token` instances make dependency requirements unambiguous and discoverable through static analysis.

This aligns with our philosophy of prioritizing correctness and leveraging the full power of Python's modern type system.

### 2. Public API Contract: Explicit and Minimal

**Decision:** The public API will continue to be explicitly defined in `src/injx/__init__.py` using `__all__`. We will not add separate `api.py` modules or facade patterns at this stage.

- **Rationale:**
  - **Simplicity:** For a library with a focused scope, a single `__init__.py` provides a clean and easily discoverable public contract.
  - **Explicitness:** Using `__all__` is a precise, standard Python mechanism for defining the public API. It prevents accidental exposure of internal components and provides a clear contract for users and static analysis tools.
  - **Avoids Over-Engineering:** Facades or separate API modules would add unnecessary complexity for the current scale of the library. The `Container` class already serves as a natural facade.

### 3. Injection Strategy: Explicit Registration over Auto-Wiring

**Decision:** `injx` will not implement auto-injection, module scanning, or "wiring" features found in other libraries. Registration will remain explicit.

- **Rationale:**
  - **Predictability:** Explicit registration makes the dependency graph deterministic and easy to reason about. Auto-wiring can create "magic" behavior that is difficult to debug, especially in large applications.
  - **Startup Performance:** Module scanning and import hooks can negatively impact application startup time.
  - **Adherence to Python's Zen:** "Explicit is better than implicit." Our target audience of developers building robust, greenfield applications values clarity and control over convenience that obscures behavior.

### 4. Async Provider Pattern: Explicit Context over Cascading Async

**Decision:** The explicit separation of `get()` (sync) and `aget()` (async) is a deliberate design choice that will be maintained. We will not adopt "cascading async" modes.

- **Rationale:**
  - **Correctness:** Mixing synchronous and asynchronous resolution paths implicitly can lead to deadlocks, event loop blocking, and other subtle concurrency bugs. The `AsyncCleanupRequiredError` is a critical safety feature that prevents such misuse.
  - **Performance Awareness:** Forcing developers to choose the resolution context (`get` vs. `aget`) makes them aware of the performance implications of their dependency graph.
  - **Simplicity of Implementation:** An explicit approach is simpler to implement, test, and maintain, reducing the surface area for bugs within the container itself.

### 5. Summary of Stance on Other Concerns

- **Module-Level Wiring:** Rejected. See "Explicit Registration over Auto-Wiring."
- **`Token[T]` Optimality:** Affirmed. It is the ideal pattern for leveraging Python 3.13+'s type system for this use case.
- **String-Based Fallbacks:** Rejected. This would violate our type safety invariants and was intentionally removed in v1.1.0.

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

### Logging Strategy
To balance observability with performance, the library will adopt the following logging strategy:
- **Default Log Level**: The `injx` logger will default to the `WARNING` level to avoid excessive log volume in production environments.
- **Opt-in Verbosity**: Users can enable more detailed `INFO` or `DEBUG` level logging for development or troubleshooting. `INFO` level logs will cover container lifecycle events and scope transitions.
- **Performance Logger**: A separate, dedicated logger, `injx.perf`, can be used for detailed performance metrics, allowing users to selectively enable performance tracing without enabling all debug logs.

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

*This document serves as the authoritative reference for Injx's architecture, design decisions, and maintenance procedures. It should be updated whenever significant architectural decisions are made or development processes change.*
