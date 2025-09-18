# Release Process

This document describes the release process for Injx, which uses a **progressive, automated release system** powered by [python-semantic-release](https://python-semantic-release.readthedocs.io/) and conventional commits.

## Branching Strategy: Trunk-Based Development

Injx uses **trunk-based development** where all work happens on the `main` branch. This approach:
- **Simplifies development**: Single branch to maintain
- **Enables fast iteration**: Changes integrate immediately
- **Follows industry standards**: Used by major Python libraries (numpy, requests, flask)
- **Provides continuous validation**: Every push to `main` publishes to TestPyPI

Release branches are not used because:
- The library does not maintain multiple major versions simultaneously
- TestPyPI serves as the staging environment
- Semantic versioning handles compatibility
- Complexity of branch management outweighs benefits for a library project

## Overview

- **Deterministic Versioning**: Version numbers are automatically calculated from commit messages
- **Controlled Timing**: Releases are triggered manually via GitHub Actions
- **Quality Assurance**: Every commit to `main` is automatically published to TestPyPI
- **Zero Manual Steps**: The release process is fully automated once triggered

## Release Types

### Patch Releases (0.x.Y)
- **Frequency**: Weekly or as needed for critical fixes
- **Triggers**: Commits with `fix:` prefix
- **Example**: `fix: resolve circular dependency detection bug`

### Minor Releases (0.X.0)
- **Frequency**: Quarterly for new features
- **Triggers**: Commits with `feat:` prefix
- **Example**: `feat: add session-scoped dependency management`

### Major Releases (X.0.0)
- **Frequency**: Rare, for breaking changes
- **Triggers**: Commits with `BREAKING CHANGE:` in body or `!` after type
- **Example**: `feat!: remove deprecated string token support`

## Development Workflow

### 1. Commit Standards (Enforced)

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Bug fixes (→ patch release)
git commit -m "fix: correct async cleanup ordering"

# New features (→ minor release)
git commit -m "feat: add protocol-based dependency resolution"

# Breaking changes (→ major release)
git commit -m "feat!: require Python 3.13+"

# Non-release commits (no version change)
git commit -m "docs: update API documentation"
git commit -m "test: add coverage for edge cases"
git commit -m "ci: optimize workflow caching"
```

**Pre-commit hooks** automatically validate commit messages. Install with:
```bash
uv sync --extra dev
pre-commit install
```

### 2. TestPyPI Validation

Every push to `main` automatically publishes to TestPyPI:
- View at: https://test.pypi.org/project/injx/
- Install test version: `pip install -i https://test.pypi.org/simple/ injx`
- Validates packaging before production release

### 3. Creating a Release

Releases are triggered manually through GitHub Actions:

1. Go to [Actions → Release workflow](../../actions/workflows/release.yml)
2. Click "Run workflow"
3. Select options:
   - **Release type**:
     - `auto` - Determine from commits (recommended)
     - `patch` - Force patch version bump
     - `minor` - Force minor version bump
     - `major` - Force major version bump
   - **Dry run**: Test the release without publishing

4. The workflow:
   - Runs all quality gates (format, lint, type check, tests)
   - Calculates the next version from commits since last release
   - Updates `pyproject.toml` with new version
   - Generates/updates `CHANGELOG.md`
   - Creates git tag
   - Builds and publishes to PyPI
   - Creates GitHub Release
   - Deploys documentation

## Release Cadence Guidelines

### Weekly (Patch Releases)
Review and release accumulated bug fixes:
```bash
# Typical weekly release for bug fixes
# Release type: auto (will detect fix: commits)
```

### Quarterly (Minor Releases)
Release new features:
```bash
# Quarterly feature release
# Release type: auto (will detect feat: commits)
```

### Immediate (Hotfixes)
Critical fixes that can't wait:
```bash
# Emergency hotfix release
# Release type: patch (or auto if only fix: commits)
```

## Version Management

### Single Source of Truth
- Version is stored in `pyproject.toml`
- Runtime access via `importlib.metadata.version("injx")`
- No separate `_version.py` file

### Version Calculation
The version is automatically determined from commit message analysis:

| Commit Type | Version Impact | Example |
|------------|---------------|---------|
| `fix:` | Patch (0.2.1 → 0.2.2) | Bug fixes |
| `feat:` | Minor (0.2.1 → 0.3.0) | New features |
| `BREAKING CHANGE:` or `!` | Major (0.2.1 → 1.0.0) | Breaking changes |
| `docs:`, `style:`, `refactor:` | None | No release |
| `test:`, `chore:`, `ci:` | None | No release |
| `perf:`, `build:` | None | No release |

## CHANGELOG Migration

This project transitioned from manual to automated changelog generation. Understanding this transition:

### Historical Content
- **CHANGELOG-LEGACY.md**: Contains manually curated releases (0.1.0 through 0.2.0)
- **CHANGELOG.md**: Automated generation via semantic-release starting with the next release
- **Rich Content**: Installation guides, migration notes, and detailed explanations remain in legacy file

### Transition Process
The transition involved:
1. **Content Preservation**: All manual changelog content backed up to CHANGELOG-LEGACY.md
2. **Format Reset**: Main CHANGELOG.md converted to semantic-release standard format
3. **Configuration Update**: Semantic-release configured for automated generation

## Troubleshooting

### No Release Needed
If the workflow reports "No release needed", this means:
- No `fix:` or `feat:` commits exist since last release
- Only non-release commits (docs, tests, CI) are present

### Version Conflicts
If you see version mismatch errors:
1. Ensure no manual edits to version in `pyproject.toml`
2. Let semantic-release manage versioning

### CHANGELOG Issues
If you need to add manual content:
1. Rich release notes go in GitHub Releases (created automatically)
2. Historical references go in CHANGELOG-LEGACY.md
3. Never manually edit the main CHANGELOG.md after semantic-release adoption

### TestPyPI Failures
TestPyPI publishes fail when:
- Version already exists (TestPyPI prohibits overwriting)
- OIDC trust is not configured (contact repository admin)

### Pre-commit Hook Issues
If commit fails validation:
```bash
# Check commit message format
commitizen check --commit-msg-file .git/COMMIT_EDITMSG

# Bypass hooks in emergency (use sparingly!)
git commit --no-verify -m "fix: emergency patch"
```

## Configuration Files

### pyproject.toml
Contains semantic-release configuration:
```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
branch = "main"
commit_parser = "conventional_commits"
# ... see pyproject.toml for full config
```

### .github/workflows/release.yml
The release workflow with `workflow_dispatch` trigger.

### .github/workflows/ci.yml
Includes TestPyPI publishing on every `main` push.

### .pre-commit-config.yaml
Enforces conventional commit standards.

## Security Notes

- **PyPI Publishing**: Uses OIDC trusted publishing (no tokens)
- **TestPyPI**: Separate OIDC configuration
- **GitHub Releases**: Created with artifacts for transparency
- **No Manual Credentials**: All authentication via GitHub OIDC

## Questions?

For issues or questions about the release process:
1. Check the [workflow runs](../../actions/workflows/release.yml)
2. Review the [semantic-release docs](https://python-semantic-release.readthedocs.io/)
3. Open an issue if you encounter problems