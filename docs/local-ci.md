# Local CI Pipeline - Running Quality Gates Locally

One of the biggest pain points in development is discovering CI failures only after pushing to GitHub. This guide explains how to run the same quality gates locally, catching issues before they reach GitHub Actions.

## The Problem

Previously, documentation build failures were only caught by GitHub Actions CI. This creates a feedback loop gap:

1. Developer makes changes
2. Pushes to GitHub
3. GitHub Actions reveals failure
4. Developer fixes locally
5. Pushes again

This wastes time and blocks PRs. The solution: **Run quality gates locally before pushing.**

## Quick Start

### Option 1: Full Local CI (Recommended)

Run all quality gates in one command:

```bash
# Using Bash script
./scripts/ci-local.sh

# OR using Python (more detailed output)
uv run python scripts/ci-local.py
```

Both scripts:
- Run all 5 quality gates (format, lint, type check, docs build, tests)
- Match the GitHub Actions CI pipeline exactly
- Fail fast on first error (use `--no-fail-fast` to see all errors)
- Take ~30 seconds to run
- Show clear pass/fail status

### Option 2: Smart Targeted Validation

Only run checks relevant to what you changed:

```bash
./.claude/sub-agents/ci/ci.sh
```

This intelligent agent:
- Detects which files you modified
- Runs only relevant quality gates
- Provides smart remediation suggestions
- Much faster for small changes

### Option 3: Individual Commands

Run specific quality gates:

```bash
# Format check
uv run ruff format --check src

# Lint
uv run ruff check src

# Type checking (strict mode)
uv run basedpyright src

# Documentation build (THE CRITICAL ONE)
uv run mkdocs build --strict

# Tests
uv run pytest
```

## Comparison of Options

| Approach | Speed | Scope | Best For |
|----------|-------|-------|----------|
| `./scripts/ci-local.sh` | ~30s | All gates | Before pushing, final check |
| `./.claude/sub-agents/ci/ci.sh` | ~15s | Targeted | During development, quick feedback |
| Individual commands | Variable | One gate | Debugging specific issues |
| Pre-commit hooks | ~20s | Staged files | On every commit |

## Pre-Commit Integration

The project includes an enhanced pre-commit hook that validates documentation:

```bash
# Install pre-commit hooks (one-time setup)
pre-commit install

# This now automatically checks on commit:
# - Source code formatting (Ruff)
# - Linting (Ruff)
# - Type safety (BasedPyright)
# - Documentation build (MkDocs --strict) ← NEW
# - GitHub Actions syntax (actionlint)
```

### What Happens on Commit

```bash
$ git commit -m "docs: update API guide"

Running pre-commit hooks...
✓ Format check
✓ Lint check
✓ Type check
✓ Documentation build          ← Catches broken docs links
✓ GitHub Actions validation
✓ YAML linting

[your-branch abc1234] docs: update API guide
```

## Development Workflow

### Recommended Workflow

1. **During Development**: Run targeted validation as needed
   ```bash
   ./.claude/sub-agents/ci/ci.sh
   ```

2. **Before Committing**: Pre-commit hooks automatically validate
   ```bash
   git add src/container.py
   git commit -m "fix(container): resolve memory leak"
   # Pre-commit hooks run automatically
   ```

3. **Before Pushing**: Run full CI pipeline
   ```bash
   ./scripts/ci-local.sh
   # All gates must pass before pushing
   ```

4. **Push with Confidence**
   ```bash
   git push origin your-branch
   ```

### Quick Check During Development

When you want fast feedback on specific changes:

```bash
# Check only what changed
./.claude/sub-agents/ci/ci.sh

# Example output:
# 📊 Change Detection
#   Source code:     ✓ Modified
#   Documentation:   Not modified
#   Configuration:   Not modified
#   Workflows:       Not modified
#
# → Type Check (BasedPyright)
#   ✅ PASSED
```

## Understanding the Quality Gates

### 1. Format Check (Ruff)
**What it does**: Ensures code follows consistent formatting (88-char lines, etc.)
**Fix**: `uv run ruff format src`

### 2. Lint (Ruff)
**What it does**: Catches code quality issues (unused imports, undefined names, etc.)
**Fix**: `uv run ruff check src --fix` (most issues auto-fixable)

### 3. Type Check (BasedPyright)
**What it does**: Strict mode type checking ensures type safety
**Fix**: Add type hints or resolve type mismatches manually
**Configuration**: See `pyproject.toml` `[tool.basedpyright]`

### 4. Documentation Build
**What it does**: Ensures documentation builds without errors in strict mode
**Common issue**: Missing files referenced in `mkdocs.yml`
**Fix**: Either create the file or remove the reference from `mkdocs.yml`
**Why it matters**: Broken docs prevent doc site deployment

### 5. Test Suite
**What it does**: Ensures all 297 tests pass
**Fix**: Debug the failing test or adjust the implementation

## Troubleshooting

### Issue: "Cannot access attribute 'base_container'"

This is a type checking error. Use `isinstance()` instead of `hasattr()`:

```python
# ❌ Wrong - duck typing, fails type check
if hasattr(container, 'base_container'):
    pass

# ✅ Correct - proper type narrowing
if isinstance(container, TestContainer):
    pass
```

### Issue: "A reference to 'X.md' is included in nav but not found"

Documentation references non-existent files. Fix by:

1. **Create the file**: Create `docs/X.md`
2. **Remove the reference**: Edit `mkdocs.yml` nav and remove the reference

### Issue: Pre-commit hook takes too long

The documentation build hook only runs if docs changed:
```yaml
files: ^(docs/|mkdocs\.yml)$  # Only triggers on these changes
```

To skip pre-commit hooks (emergency only):
```bash
git commit --no-verify -m "your message"
```

### Issue: Tests hang or timeout

Run with timeout and verbose output:
```bash
uv run pytest -xvs --timeout=10
```

## Advanced Usage

### Run Full CI Without Failing

See all errors without stopping on first failure:

```bash
./scripts/ci-local.sh --no-fail-fast

# OR

uv run python scripts/ci-local.py --no-fail-fast

# OR

./.claude/sub-agents/ci/ci.sh --full
```

### JSON Output (for CI/CD integration)

```bash
uv run python scripts/ci-local.py --json
```

Returns structured data:
```json
{
  "timestamp": "2025-10-27T12:34:56",
  "passed": true,
  "summary": {
    "total": 5,
    "passed": 5,
    "failed": 0
  },
  "results": [...]
}
```

### Quiet Mode (minimal output)

```bash
./scripts/ci-local.sh --quiet
uv run python scripts/ci-local.py --quiet
```

## CI Pipeline Architecture

### GitHub Actions (`.github/workflows/ci.yml`)

| Step | Command | What |
|------|---------|------|
| 1 | `ruff format --check` | Code formatting |
| 2 | `ruff check` | Linting |
| 3 | `basedpyright` | Type checking |
| 4 | `mkdocs build --strict` | **Documentation** |
| 5 | `pytest` | Tests |

### Local Mirror Scripts

These scripts replicate the exact same steps:

- **Bash**: `./scripts/ci-local.sh` - Fast, no dependencies
- **Python**: `uv run scripts/ci-local.py` - Structured output, better UX
- **Smart Agent**: `./.claude/sub-agents/ci/ci.sh` - Intelligent, targeted validation

## Performance Metrics

Typical execution times on MacBook Pro M1:

```
Format check:        2.5s
Lint:               4.2s
Type check:        12.1s
Docs build:         0.99s (NEW)
Tests:             10.2s (with 297 tests)
─────────────────────────
Total:            ~30 seconds
```

Targeted validation (just changed files):
- Source only: ~20s
- Docs only: ~1s
- Config only: ~0.5s

## Integration with IDE

### VSCode Settings

Add to `.vscode/settings.json`:

```json
{
  "terminal.integrated.defaultProfile.osx": "zsh",
  "tasks.runTasks": ["ci-check"],
  "keybindings": [
    {
      "key": "cmd+shift+t",
      "command": "workbench.action.tasks.runTask",
      "args": "Local CI Check"
    }
  ]
}
```

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Local CI Check",
      "type": "shell",
      "command": "./scripts/ci-local.sh",
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "shared"
      }
    }
  ]
}
```

### Pre-push Hook (Git)

Create `.git/hooks/pre-push`:

```bash
#!/bin/bash
echo "Running local CI pipeline before push..."
./scripts/ci-local.sh || exit 1
```

Make it executable:
```bash
chmod +x .git/hooks/pre-push
```

## Summary

| When | What to Run |
|------|-------------|
| **During development** | `./.claude/sub-agents/ci/ci.sh` |
| **Before committing** | Pre-commit hooks (automatic) |
| **Before pushing** | `./scripts/ci-local.sh` |
| **On every push** | GitHub Actions (automatic) |

This multi-layer approach ensures:
- ✅ Fast feedback during development (seconds)
- ✅ Quality assurance before commits (automatic)
- ✅ Confidence before pushing (complete validation)
- ✅ Zero surprises from GitHub Actions (already validated)

---

**Key Takeaway**: The documentation build failure we fixed was only caught by GitHub Actions because `mkdocs build --strict` wasn't in the local workflow. Now it is—in pre-commit hooks and local CI scripts—preventing future surprises.
