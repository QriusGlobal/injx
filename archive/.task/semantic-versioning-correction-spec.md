# Semantic Versioning Correction Specification
**Date**: 2025-09-18
**Author**: Claude (with Gemini architectural review)
**Status**: Approved for Implementation
**Impact**: High - Will rewrite Git history for 51 commits

## Executive Summary

This specification outlines the professional correction of semantic versioning commit prefixes in the injx repository. The correction involves an interactive rebase of 51 commits to change 20 incorrectly prefixed infrastructure commits from `fix:` to `chore:`, ensuring accurate automated version calculation by semantic-release.

## Problem Statement

### Current Issues
- **20 commits** incorrectly use `fix:` prefix for infrastructure/CI changes
- These should use `chore:` prefix (no version bump) instead of `fix:` (patch bump)
- Semantic-release miscalculates versions based on incorrect prefixes
- Production PyPI shows v0.1.0, but Git history suggests v0.2.x releases
- Misleading version history creates professional credibility issues

### Impact Analysis
- Automated versioning produces incorrect version numbers
- Version v0.2.x tags were created but don't exist on production PyPI
- Developer confusion about actual release status
- Unprofessional semantic versioning compliance

## Architectural Review

### Gemini's Assessment
> "For a single-developer project, this is an acceptable and standard procedure... Interactive rebase is the most direct and fitting tool for this specific, one-time cleanup."

### Key Endorsements
- **Standard procedure** for single-developer projects
- **Most direct tool** for systematic commit message correction
- **Professional solution** that establishes proper standards
- **Acceptable risk** with proper safety measures

## Solution Specification

### Approach: Interactive Rebase
- **Method**: `git rebase -i v0.1.0`
- **Scope**: 51 commits since last legitimate release
- **Changes**: 20 commits from `fix:` → `chore:` prefix
- **Impact**: All commit hashes will change from rebase point
- **Requirement**: Force push with `--force-with-lease`

### Commits Requiring Correction

The following 20 commits need their prefix changed from `fix:` to `chore:`:

```
827ff1f fix: correct UV publish syntax for TestPyPI
8b05def fix: remove redundant GitHub release creation step
28f61f8 fix: resolve remaining semantic-release syntax bugs found by Gemini review
1805031 fix: improve dry-run logic and remove redundant flags in release workflow
cd158ba fix: correct semantic-release command syntax in release workflow
cc41de2 fix: use proper dependency management and add release environment selection
e327182 fix: secure GitHub Actions and optimize UV caching
77c0cce fix: resolve GitHub Actions workflow issues and enable local testing
e1fd0ee fix: enable pre-1.0 development with allow_zero_version = true
8f16629 fix: break long line in release workflow to meet yamllint standards
f037426 fix: move TestPyPI to release workflow to test release process
7d38cf9 fix: align version and changelog with PyPI reality
90399f3 fix: update Release Please action to working SHA hash and fix YAML formatting
d042455 fix: correct Release Please manifest to reflect actual version 0.2.1
89f2414 fix: set reportImportCycles and reportAny as warnings not suppressions
1f3a021 fix: use uvx for tools that don't need to be installed
882f26b fix: use uv run for all commands to ensure tools are available
eb43de7 fix: add pytest-cov and pytest-xdist to CI dependencies
b7585c2 fix: consolidate CI workflow and fix venv issues
7479bd8 fix: resolve CI/CD issues and add AI development attribution
```

### Legitimate fix: Commits (Keep As-Is)

The following 8 commits are correctly categorized and should remain unchanged:

```
b44056c fix: resolve parameter resolution conflicts in injection wrapper
65287f2 fix: remove invalid asyncio package from dev dependencies
002ce00 fix: resolve type errors in injection and registry modules
ef9871f fix: resolve circular import between container and injection modules
e37564f fix: resolve memory leaks in Container lock management
8c8a772 fix(types): add minimal ContainerProtocol and fix type delegation
da2ada3 fix: resolve circular import by refactoring Container to use composition
5a803a5 fix: add metadata exports to __all__ to resolve linting issues
```

## Implementation Phases

### Phase 1: Safety Setup (15 minutes)

#### 1.1 Disable CI/Automation
- [ ] Navigate to GitHub repository settings
- [ ] Temporarily disable GitHub Actions on main branch
- [ ] Document original settings for restoration

#### 1.2 Create Backup
```bash
# Create timestamped backup branch
git branch main-backup-$(date +%F)

# Push backup to remote for safety
git push origin main-backup-$(date +%F)
```

#### 1.3 Documentation
- [ ] Create this specification in .task/ directory
- [ ] Generate commit correction list
- [ ] Prepare rollback procedures

### Phase 2: Interactive Rebase (30-45 minutes)

#### 2.1 Start Interactive Rebase
```bash
git rebase -i v0.1.0
```

#### 2.2 Mark Commits for Rewording
In the interactive editor:
- Change `pick` to `reword` (or `r`) for the 20 identified commits
- Keep `pick` for all other commits
- Save and exit

#### 2.3 Systematic Message Correction
For each marked commit, change:
```
fix: [description]
```
to:
```
chore: [description]
```

### Phase 3: Validation (15 minutes)

#### 3.1 Code Integrity Check (CRITICAL)
```bash
# This MUST produce NO output (empty diff)
git diff main-backup-$(date +%F) main
```
**Expected**: Empty output (only messages changed, not code)

#### 3.2 Semantic-Release Validation
```bash
# Test version calculation with corrected commits
uv run semantic-release version --print --dry-run
```
**Expected**: v0.1.1 or v0.1.2 (NOT v0.2.x)

#### 3.3 History Integrity Verification
```bash
# Verify commit count unchanged
git rev-list v0.1.0..HEAD --count
# Expected: 51

# Check corrected prefixes
git log --oneline v0.1.0..HEAD | grep "^[a-f0-9]* fix:" | wc -l
# Expected: ~8 (legitimate fixes only)

git log --oneline v0.1.0..HEAD | grep "^[a-f0-9]* chore:" | wc -l
# Expected: ~28 (including corrected commits)
```

### Phase 4: Force Push (5 minutes)

#### 4.1 Push Corrected History
```bash
# Safe force push with lease protection
git push --force-with-lease origin main
```

#### 4.2 Verify Remote State
```bash
# Confirm push succeeded
git log --oneline origin/main -5
```

### Phase 5: Cleanup & Documentation (15 minutes)

#### 5.1 Re-enable CI/Automation
- [ ] Return to GitHub repository settings
- [ ] Re-enable GitHub Actions on main branch
- [ ] Verify workflows trigger correctly

#### 5.2 Update Documentation
- [ ] Update CLAUDE.md with semantic versioning standards
- [ ] Document the correction rationale
- [ ] Add commit message guidelines

#### 5.3 Cleanup (After Stability Confirmed)
Wait 24 hours to ensure stability, then:
```bash
# Delete local backup
git branch -d main-backup-$(date +%F)

# Delete remote backup
git push origin --delete main-backup-$(date +%F)
```

## Safety Measures

### Pre-Rebase Checklist
- [ ] CI/Automation disabled
- [ ] Backup branch created locally
- [ ] Backup branch pushed to remote
- [ ] Clean working directory (no uncommitted changes)
- [ ] Documentation prepared

### Validation Checklist
- [ ] Code diff shows NO changes (empty output)
- [ ] Semantic-release shows correct version calculation
- [ ] Commit count unchanged (51)
- [ ] Legitimate fix: commits preserved (~8)
- [ ] Infrastructure commits corrected to chore: (~20)

### Rollback Procedures

#### Local Rollback (Before Push)
```bash
# If rebase in progress
git rebase --abort

# If rebase complete but wrong
git reset --hard main-backup-$(date +%F)
```

#### Remote Rollback (After Push)
```bash
# Emergency restore from backup
git push --force origin main-backup-$(date +%F):main
```

## Success Criteria

### Immediate Success Metrics
- [ ] All 20 infrastructure commits use `chore:` prefix
- [ ] All 8 legitimate fix commits remain unchanged
- [ ] Semantic-release calculates v0.1.1/v0.1.2 (not v0.2.x)
- [ ] No code changes (only commit messages modified)
- [ ] CI/CD workflows continue functioning

### Long-term Success Metrics
- [ ] Future releases follow correct semantic versioning
- [ ] No confusion about version history
- [ ] Professional Git history maintained
- [ ] Team follows commit message standards

## Risk Assessment

### Identified Risks
1. **Commit hash changes** - Acceptable for semantic correctness
2. **Force push to main** - Mitigated by backup and --force-with-lease
3. **Large rebase scope (51 commits)** - Manageable with systematic approach
4. **CI disruption** - Mitigated by temporary disable/re-enable

### Risk Mitigation
- Complete backup before starting
- Code integrity validation after rebase
- Semantic-release dry run validation
- Emergency rollback procedures documented
- Single-developer context reduces coordination risk

## Communication Plan

### Commit Message for Documentation
```
chore: correct semantic versioning prefixes via interactive rebase

- Fixed 20 commits incorrectly marked as fix: → chore:
- Infrastructure/CI changes now properly categorized
- Preserves 8 legitimate fix: commits for library functionality
- Enables accurate automated version calculation
- See .task/ directory for complete audit trail

BREAKING: Commit hashes changed from v0.1.0 forward
Note: This was a one-time correction to establish professional
      semantic versioning standards. Future commits will follow
      proper conventions from the start.
```

## Appendix: Commit Message Standards

### For Future Reference
- `feat:` - New features (minor version bump)
- `fix:` - Bug fixes in library code (patch version bump)
- `chore:` - Infrastructure, CI/CD, dependencies (no version bump)
- `docs:` - Documentation changes (no version bump)
- `refactor:` - Code restructuring (no version bump)
- `test:` - Test additions/changes (no version bump)
- `style:` - Formatting changes (no version bump)

## Approval

This specification has been:
- **Architecturally reviewed** by Gemini
- **Approved** by the user
- **Ready for implementation**

---

*End of Specification - Proceed with Phase 1: Safety Setup*