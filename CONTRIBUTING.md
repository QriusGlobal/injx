# Contributing to injx

Thank you for your interest in contributing to injx! This guide will help you get started with contributing to our type-safe, production-ready dependency injection library for Python 3.13+.

## 🚀 Quick Start

**TL;DR**: Use `make format` to fix formatting, `make test` to run tests and linting, and `make docs` to build documentation.

## 📋 Prerequisites

Before contributing, ensure you have:

- **Python 3.13+** (required)
- **UV** - Fast Python package manager ([installation guide](https://github.com/astral-sh/uv))
- **Git** - Version control
- **Make** - Build automation (optional, but recommended)

## 🛠 Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/injx.git
   cd injx
   ```

3. **Install dependencies**:
   ```bash
   # Install development dependencies
   uv sync --dev
   
   # Activate virtual environment
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

## 🔧 Development Workflow

### Making Changes

1. **Create a new branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes** following our coding standards

3. **Run quality checks**:
   ```bash
   # Format code automatically
   make format
   # or manually:
   ruff format .
   
   # Run linting and type checking
   make lint
   # or manually:
   ruff check . --fix
   basedpyright src/ tests/
   
   # Run tests with coverage
   make test
   # or manually:
   pytest --cov=src --cov-report=html
   ```

4. **Build documentation**:
   ```bash
   make docs
   # or manually:
   mkdocs build
   ```

### Available Make Commands

```bash
make install      # Install development dependencies
make format       # Auto-format code with Ruff
make lint         # Run linting and type checking
make test         # Run tests with coverage
make test-fast    # Run tests without coverage
make docs         # Build documentation
make docs-serve   # Serve docs locally at http://localhost:8000
make clean        # Clean build artifacts
make all          # Run format, lint, test, and docs
```

## 🔱 Branching & Releases

- `main`: protected and always deployable. No direct pushes; merge via PR.
- `feature/*`: all new work starts here; branch from latest `main`; open PR to `main`.
- `release/*`: stabilization only (version bumps, docs, fixes). Create from `main` when preparing a release; merge back to `main` and tag from `main`.
- `hotfix/*`: branch from a release tag for urgent fixes; merge back to `main` and active release branches; tag a patch release.

## 🧭 CI Pipeline (deterministic)

CI runs checks in this order (check-only, no auto-fix):

1. Format check: `uvx ruff format --check src`
2. Lint: `uvx ruff check src`
3. Type check: `uvx basedpyright src`
4. Tests: `PYTHONPATH=src uv run pytest -q`
5. Docs (separate job): `PYTHONPATH=src uv run mkdocs build`

Pre-commit can auto-format locally; CI only checks and never modifies files. Ensure you run `ruff format` locally before pushing.

## 📝 Coding Standards

### Code Style

- **Formatter**: [Ruff](https://docs.astral.sh/ruff/) (replaces Black + isort)
- **Linting**: Ruff with comprehensive rule set
- **Type Checking**: [BasedPyright](https://github.com/DetachHead/basedpyright) in strict mode
- **Line Length**: 88 characters
- **Import Sorting**: Automatic via Ruff

### Type Annotations

- **All functions must have type annotations**
- **Use generics for container types**: `list[str]` not `List[str]`
- **Protocol-based design** for dependency inversion
- **No `Any` types** without justification

### Documentation

- **Google-style docstrings** for all public APIs
- **Include type information** in docstring parameters
- **Provide runnable examples** in docstrings
- **Complete module-level documentation**

Example:
```python
def register(self, token: Token[T], provider: Provider[T], scope: Scope) -> None:
    """Register a provider for the given token.
    
    Args:
        token: The token to register the provider for
        provider: Factory function or callable that creates instances
        scope: Lifecycle scope (SINGLETON, TRANSIENT, etc.)
        
    Raises:
        ValueError: If token is already registered
        
    Example:
        >>> container = Container()
        >>> token = Token[str]("greeting")
        >>> container.register(token, lambda: "Hello", Scope.SINGLETON)
    """
```

## 🧪 Testing Requirements

### Test Coverage

- **Minimum 95% coverage** (enforced in CI)
- **Unit tests** for all public APIs
- **Integration tests** for real-world scenarios
- **Performance tests** for O(1) guarantees
- **Thread safety tests** for concurrent operations

### Test Organization

```python
# tests/test_container.py
class TestBasicRegistration:
    """Test basic dependency registration and resolution."""
    
    def test_register_and_get_transient(self):
        """Test registering and resolving transient dependencies."""
        # Arrange
        container = Container()
        token = Token[str]("test")
        
        # Act
        container.register(token, lambda: "value", Scope.TRANSIENT)
        result = container.get(token)
        
        # Assert
        assert result == "value"
```

### Test Markers

Use pytest markers for test organization:
- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.asyncio` - Async tests

## 📖 Documentation Guidelines

### Writing Style

- **Clear and concise** language
- **User-focused** - explain the "why" not just the "what"
- **Runnable examples** that users can copy-paste
- **Error scenarios** and how to handle them

### Documentation Structure

- **README.md** - Overview and quick start
- **docs/** - Detailed documentation
- **examples/** - Real-world usage patterns
- **Docstrings** - API reference

## 🚀 Submitting Changes

### Before Submitting

1. **Run the full test suite**: `make all`
2. **Update documentation** if needed
3. **Add tests** for new functionality
4. **Update CHANGELOG.md** if applicable

### Pull Request Process

1. **Create an issue** first for substantial changes
2. **Push your branch** to your fork
3. **Create a pull request** with:
   - Clear title and description
   - Reference to related issues
   - Test coverage information
   - Documentation updates

### PR Requirements

- ✅ All CI checks pass
- ✅ Code coverage ≥ 95%
- ✅ Type checking passes (BasedPyright strict mode)
- ✅ Documentation builds successfully
- ✅ Pre-commit hooks pass

## 🐛 Reporting Bugs

Use our [bug report template](https://github.com/qriusglobal/injx/issues/new?template=bug_report.yml) and include:

- **Python version** and operating system
- **injx version**
- **Minimal reproducible example**
- **Expected vs actual behavior**
- **Stack trace** if applicable

## 💡 Feature Requests

Use our [feature request template](https://github.com/qriusglobal/injx/issues/new?template=feature_request.yml) and include:

- **Use case** description
- **Proposed API** design
- **Alternative solutions** considered
- **Implementation** ideas (if any)

## 🔒 Security Issues

**Do not open public issues for security vulnerabilities.**

Please follow our [Security Policy](SECURITY.md) and report security issues privately to: security@qrius.global

## 📚 Additional Resources

- **Documentation**: https://github.com/qriusglobal/injx
- **Examples**: [examples/](examples/) directory
- **Issue Tracker**: https://github.com/qriusglobal/injx/issues
- **Discussions**: https://github.com/qriusglobal/injx/discussions

## 🤝 Code of Conduct

This project follows the [Python Community Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

## 📄 License

By contributing to injx, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

## 🌲 Trunk-Based Development

- `main` is the only long-lived branch.
- Create short-lived feature/fix branches; merge to `main` via PR.
- Squash merge PRs to keep a linear history.
- CI must pass (ruff, basedpyright, pytest) before merge.

## 📝 Conventional Commits

We use Conventional Commits for automation (releases + changelog).

Format: `type(scope)!: short summary`

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `perf`, `test`.

Breaking changes: add `!` or a `BREAKING CHANGE:` footer.

Examples:

- `feat(container): add async-safe singleton resolution`
- `fix(scope): prevent double-dispose in transient scope`
- `docs(readme): clarify beta stability caveats`

## 🚢 Release Process

- Automated via Release Please.
- Conventional commits on `main` accumulate in a release PR.
- Merging the release PR updates `CHANGELOG.md`, tags, and creates a GitHub Release.
- PyPI publish runs from `.github/workflows/publish.yml` on release publish.


**Questions?** Feel free to open a [discussion](https://github.com/qriusglobal/injx/discussions) or reach out to the maintainers!
