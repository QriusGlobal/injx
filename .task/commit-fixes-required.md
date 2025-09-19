# Commit Fixes Required - Interactive Rebase Instructions

## Summary
- **Total Commits Since v0.1.0**: 51
- **Commits Needing fix: → chore: Change**: 20
- **Commits to Keep As-Is**: 31

## Detailed Commit Fix List

### Infrastructure Commits to Change (fix: → chore:)

| Hash | Current Message | Change To |
|------|-----------------|-----------|
| 827ff1f | fix: correct UV publish syntax for TestPyPI | chore: correct UV publish syntax for TestPyPI |
| 8b05def | fix: remove redundant GitHub release creation step | chore: remove redundant GitHub release creation step |
| 28f61f8 | fix: resolve remaining semantic-release syntax bugs found by Gemini review | chore: resolve remaining semantic-release syntax bugs found by Gemini review |
| 1805031 | fix: improve dry-run logic and remove redundant flags in release workflow | chore: improve dry-run logic and remove redundant flags in release workflow |
| cd158ba | fix: correct semantic-release command syntax in release workflow | chore: correct semantic-release command syntax in release workflow |
| cc41de2 | fix: use proper dependency management and add release environment selection | chore: use proper dependency management and add release environment selection |
| e327182 | fix: secure GitHub Actions and optimize UV caching | chore: secure GitHub Actions and optimize UV caching |
| 77c0cce | fix: resolve GitHub Actions workflow issues and enable local testing | chore: resolve GitHub Actions workflow issues and enable local testing |
| e1fd0ee | fix: enable pre-1.0 development with allow_zero_version = true | chore: enable pre-1.0 development with allow_zero_version = true |
| 8f16629 | fix: break long line in release workflow to meet yamllint standards | chore: break long line in release workflow to meet yamllint standards |
| f037426 | fix: move TestPyPI to release workflow to test release process | chore: move TestPyPI to release workflow to test release process |
| 7d38cf9 | fix: align version and changelog with PyPI reality | chore: align version and changelog with PyPI reality |
| 90399f3 | fix: update Release Please action to working SHA hash and fix YAML formatting | chore: update Release Please action to working SHA hash and fix YAML formatting |
| d042455 | fix: correct Release Please manifest to reflect actual version 0.2.1 | chore: correct Release Please manifest to reflect actual version 0.2.1 |
| 89f2414 | fix: set reportImportCycles and reportAny as warnings not suppressions | chore: set reportImportCycles and reportAny as warnings not suppressions |
| 1f3a021 | fix: use uvx for tools that don't need to be installed | chore: use uvx for tools that don't need to be installed |
| 882f26b | fix: use uv run for all commands to ensure tools are available | chore: use uv run for all commands to ensure tools are available |
| eb43de7 | fix: add pytest-cov and pytest-xdist to CI dependencies | chore: add pytest-cov and pytest-xdist to CI dependencies |
| b7585c2 | fix: consolidate CI workflow and fix venv issues | chore: consolidate CI workflow and fix venv issues |
| 7479bd8 | fix: resolve CI/CD issues and add AI development attribution | chore: resolve CI/CD issues and add AI development attribution |

### Legitimate Library Fix Commits (Keep As-Is)

| Hash | Message | Reason |
|------|---------|--------|
| b44056c | fix: resolve parameter resolution conflicts in injection wrapper | Fixes bug in src/injx/injection.py |
| 65287f2 | fix: remove invalid asyncio package from dev dependencies | Dependency fix affecting library |
| 002ce00 | fix: resolve type errors in injection and registry modules | Fixes bugs in src/injx/ code |
| ef9871f | fix: resolve circular import between container and injection modules | Fixes library import issue |
| e37564f | fix: resolve memory leaks in Container lock management | Fixes memory leak in library |
| 8c8a772 | fix(types): add minimal ContainerProtocol and fix type delegation | Fixes type issues in library |
| da2ada3 | fix: resolve circular import by refactoring Container to use composition | Fixes library architecture |
| 5a803a5 | fix: add metadata exports to __all__ to resolve linting issues | Fixes library exports |

### Other Commits to Keep As-Is

All other commits with prefixes:
- `chore:` (8 commits) - Already correct
- `feat:` (3 commits) - Features, keep as-is
- `refactor:` (4 commits) - Refactoring, keep as-is
- `docs:` (4 commits) - Documentation, keep as-is
- `style:` (1 commit) - Formatting, keep as-is
- `security:` (1 commit) - Security, keep as-is
- `refactor!:` (1 commit) - Breaking change, keep as-is

## Interactive Rebase Instructions

1. When you run `git rebase -i v0.1.0`, you'll see all 51 commits
2. For the 20 commits listed above under "Infrastructure Commits to Change":
   - Change `pick` to `reword` (or just `r`)
3. Save and close the editor
4. Git will now walk through each marked commit
5. For each one, change only the prefix from `fix:` to `chore:`
6. Keep the rest of the message exactly the same

## Validation After Rebase

Run these checks to ensure the rebase was successful:

```bash
# Should show ~8 legitimate fix commits
git log --oneline v0.1.0..HEAD | grep "^[a-f0-9]* fix:" | wc -l

# Should show ~28 chore commits (8 original + 20 corrected)
git log --oneline v0.1.0..HEAD | grep "^[a-f0-9]* chore:" | wc -l

# Should show empty diff (no code changes)
git diff main-backup-$(date +%F) main
```

## Notes

- All 20 infrastructure commits touch only:
  - `.github/workflows/` files (CI/CD)
  - `pyproject.toml` configuration
  - Test/build scripts
  - Documentation files

- None of these commits touch the actual library code in `src/injx/`
- This is why they should be `chore:` not `fix:`