# CI Sub-Agent: Intelligent Local Quality Gate Validation

A smart Claude Code sub-agent that provides targeted, intelligent local CI validation with:

- 🎯 **Smart change detection**: Analyzes what files changed to run only relevant checks
- 💡 **Intelligent feedback**: Provides remediation suggestions for failures
- ⚡ **Fast feedback**: ~15 seconds for targeted checks vs ~30 seconds for full CI
- 🔍 **Strict validation**: Ensures quality matches GitHub Actions pipeline

## Quick Start

### Run Smart Validation

```bash
# Run only checks relevant to what you changed
./.claude/sub-agents/ci/ci.sh

# Run full CI pipeline (all checks)
./.claude/sub-agents/ci/ci.sh --full
```

### Understanding the Output

```
📊 Change Detection
  Source code:     ✓ Modified
  Documentation:   Not modified
  Configuration:   Not modified
  Workflows:       Not modified

📋 Mode: Targeted Validation
   Running checks based on detected changes

→ Format Check (Ruff)
  ✅ PASSED

→ Lint Check (Ruff)
  ✅ PASSED

→ Type Check (BasedPyright)
  ✅ PASSED

📊 Validation Summary
Passed: 3
Failed: 0

✅ All Validations Passed!
Your code is ready!
```

## Features

### 1. Smart Change Detection

The sub-agent automatically detects what changed:

```
- Source code (src/):      Triggers format, lint, type check
- Documentation (docs/):   Triggers documentation build
- Configuration:           Triggers all checks
- Workflows:               Triggers workflow validation
```

### 2. Targeted Validation

Only runs necessary checks:

```bash
# Only docs changed? Only checks docs build
./.claude/sub-agents/ci/ci.sh
# → Documentation Build
# Total time: ~1 second

# Only src changed? Checks format, lint, type
./.claude/sub-agents/ci/ci.sh
# → Format Check
# → Lint Check
# → Type Check
# Total time: ~15 seconds
```

### 3. Intelligent Error Feedback

When a check fails, the agent provides:
- Error message
- Remediation suggestion
- Example fix command

```
→ Type Check (BasedPyright)
  ❌ FAILED

  Error output:
    src/container.py:42 - error: Cannot access attribute

  💡 Fix suggestion:
    Review type annotations in changed files
```

### 4. Full CI Mode

Force all checks regardless of changes:

```bash
# Run complete validation
./.claude/sub-agents/ci/ci.sh --full
```

## Usage Patterns

### During Development

Run frequently for quick feedback:

```bash
./.claude/sub-agents/ci/ci.sh
```

### Before Committing

Pre-commit hooks run automatically (no action needed):

```bash
git commit -m "fix: resolve issue"
# Hooks validate automatically
```

### Before Pushing

Run full CI for final validation:

```bash
./.claude/sub-agents/ci/ci.sh --full
```

## Options

| Option | Effect |
|--------|--------|
| (none) | Run targeted checks based on changes |
| `--full` | Run all quality gates regardless of changes |
| `--quiet` | Suppress output, show only results |

## Integration

### With /ci-check Slash Command

In Claude Code, you can create a slash command:

```bash
# In .claude/commands/ci-check.md
/ci-check
→ Runs: ./.claude/sub-agents/ci/ci.sh
```

Then use anywhere in the project:
```
/ci-check
```

### With Git Hooks

Create `.git/hooks/pre-push`:

```bash
#!/bin/bash
./.claude/sub-agents/ci/ci.sh --full || exit 1
```

## Architecture

```
ci.sh
├── detect_changes()      # Analyze git changes
├── run_check()          # Execute single check with feedback
└── main()               # Orchestrate validation flow

Checks:
├── Format (Ruff)
├── Lint (Ruff)
├── Type (BasedPyright)
├── Docs (MkDocs --strict)
├── Workflows (actionlint)
└── Tests (Pytest) [--full only]
```

## Examples

### Example 1: Documentation Update

```bash
$ echo "New docs content" >> docs/advanced.md
$ ./.claude/sub-agents/ci/ci.sh

📊 Change Detection
  Documentation:   ✓ Modified

📋 Mode: Targeted Validation

→ Documentation Build (MkDocs)
  ✅ PASSED

✅ All Validations Passed!
```

### Example 2: Source Code Fix

```bash
$ # Fix in src/container.py
$ ./.claude/sub-agents/ci/ci.sh

📊 Change Detection
  Source code:     ✓ Modified

📋 Mode: Targeted Validation

→ Format Check (Ruff)
  ✅ PASSED

→ Lint Check (Ruff)
  ✅ FAILED

  Error output:
    src/container.py:42 - F401: unused import

  💡 Fix suggestion:
    Run: uv run ruff check src --fix

✅ Running suggested fix...
(Fixed 1 error)

Now run again to verify...
```

### Example 3: Full Pipeline Check

```bash
$ ./.claude/sub-agents/ci/ci.sh --full

📊 Change Detection
  [All files]

📋 Mode: Full CI Pipeline
   Running all quality gates (--full flag)

→ Format Check (Ruff)
  ✅ PASSED

→ Lint Check (Ruff)
  ✅ PASSED

→ Type Check (BasedPyright)
  ✅ PASSED

→ Documentation Build (MkDocs)
  ✅ PASSED

→ Workflow Validation (actionlint)
  ✅ PASSED

→ Test Suite (Pytest)
  ✅ PASSED (297 passed in 10.2s)

✅ All Validations Passed!
Your code is ready! 🚀
```

## Comparison: This Agent vs Others

| Tool | Speed | Scope | Intelligence |
|------|-------|-------|--------------|
| `./scripts/ci-local.sh` | ~30s | All gates | No - deterministic |
| **This agent** | ~15s | Targeted | **Yes - smart** |
| Individual commands | Variable | One gate | No |
| Pre-commit hooks | ~20s | Staged | No - file-based |

## When to Use

✅ **Use this agent when**:
- Developing a feature locally
- Need quick feedback
- Want to understand what CI will check
- Prefer intelligent validation over raw output

⚠️ **Use full CI when**:
- About to push/open PR
- Making cross-cutting changes
- Want 100% confidence

❌ **Don't use for**:
- Production CI/CD (use GitHub Actions)
- Automated checks (use pre-commit hooks)
- Continuous monitoring (use CI service)

## Troubleshooting

### Agent says "Not in git repo"

The agent needs to be in a git repository to detect changes:

```bash
cd /path/to/injx  # Make sure you're in the project root
./.claude/sub-agents/ci/ci.sh
```

### Wants to run all checks but you only changed docs

Either:

1. **Stage your changes**: `git add docs/`
2. **Force targeted**: `git diff` shows what changed

Or just run full CI:

```bash
./.claude/sub-agents/ci/ci.sh --full
```

### Hook fails but I need to push

For emergencies only:

```bash
./.claude/sub-agents/ci/ci.sh --full --quiet
# Returns exit code 0 for pass, 1 for fail
```

## Related Tools

- **`./scripts/ci-local.sh`**: Fast bash mirror of full CI
- **`./scripts/ci-local.py`**: Python version with better UX
- **`.pre-commit-config.yaml`**: Automatic hooks on commit
- **`.github/workflows/ci.yml`**: GitHub Actions pipeline

---

**Philosophy**: This agent embodies the principle of "fast feedback loops" - catching issues locally within seconds rather than waiting for GitHub Actions to run.
