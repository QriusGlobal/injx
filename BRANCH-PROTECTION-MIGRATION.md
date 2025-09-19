# Branch Protection Migration Guide

## Overview

This guide covers the transition from direct pushes to protected main branch with PR-based releases.

## What Changed

### Before Branch Protection
- GitHub Actions could push directly to main
- Releases modified `pyproject.toml` and `CHANGELOG.md` on main
- Single workflow handled all release types

### After Branch Protection
- All changes to main require PR review
- GitHub Actions cannot push directly to main
- Separate workflows for direct vs PR-based releases

## Release Workflow Changes

### TestPyPI Releases
**✅ No changes required**
- TestPyPI releases never pushed to git (by design)
- Continue using the standard `release.yml` workflow
- Publishes packages without creating git tags

### Production Releases
**⚠️ New workflow required**
- Production releases need git tags and version commits
- Must use new PR-based workflow: `release-pr.yml`

## Migration Steps

### 1. Enable Branch Protection Rules

In repository settings, configure main branch protection:

```yaml
Protection Rules:
  - Require pull request reviews (1 approval minimum)
  - Require status checks:
    - "CI / ci"
    - "Quality Gates"
  - Include administrators: No (allows auto-merge)
  - Allow auto-merge: Yes
  - Restrict pushes: Yes
```

### 2. Update Release Process

#### For TestPyPI (No Change)
```bash
# Continue using existing workflow
Actions → Release → Run workflow
- Target: testpypi
- Dry run: optional
```

#### For Production (New Process)
```bash
# Use new PR-based workflow
Actions → Create Release PR → Run workflow
- Target: release
# Review and merge the created PR
# Release publishes automatically after merge
```

### 3. Handle First Release After Migration

The first production release after enabling branch protection will:

1. **Detect branch protection** - Workflow warns about protection
2. **Fail if using old workflow** - Direct push rejected
3. **Require PR workflow** - Must use `release-pr.yml`

## Workflow Comparison

| Aspect | Direct Release | PR-Based Release |
|--------|----------------|------------------|
| **Trigger** | Manual workflow | Manual → PR → Merge |
| **Review** | None | Required PR review |
| **Git Operations** | Direct push | Via PR merge |
| **Rollback** | Difficult | Easy (revert PR) |
| **Audit Trail** | Workflow logs only | Full PR history |
| **Security** | Lower | Higher |

## FAQ

### Q: Why can't we just disable branch protection for releases?
**A:** Branch protection is a critical security feature. Bypassing it defeats the purpose of supply chain security.

### Q: Can TestPyPI and production use the same workflow?
**A:** No. TestPyPI doesn't need git operations, production does. Different workflows prevent git pollution from test releases.

### Q: What happens to version overrides (patch/minor/major)?
**A:** Removed. Versions are always determined from commit messages to enforce good practices.

### Q: How do I fix a wrong version?
**A:** Fix the commit message using `git rebase -i` or `git commit --amend`, then create a new release.

### Q: Can I still do emergency releases?
**A:** Yes, using the PR workflow. The PR can be reviewed and merged quickly for urgent fixes.

## Best Practices

### Commit Messages
Write proper conventional commits:
```bash
# Good
git commit -m "fix: resolve memory leak in container cleanup"
git commit -m "feat: add support for async dependency injection"

# Bad
git commit -m "update stuff"
git commit -m "fixes"
```

### Release Planning
1. **Test first**: Always release to TestPyPI before production
2. **Review PRs**: Use the PR review process for quality control
3. **Document changes**: Ensure commit messages accurately describe changes

### Emergency Procedures
1. **Fix the issue** with proper commit message
2. **Create release PR** using `release-pr.yml`
3. **Fast-track review** - get quick approval
4. **Auto-merge** handles the rest

## Troubleshooting

### "Permission denied" errors
- Branch protection is active
- Use PR-based workflow instead
- Check that auto-merge is enabled

### Version conflicts
- Ensure commits follow conventional format
- Use `semantic-release version --print` to preview version
- Fix commit messages if version is wrong

### PR merge failures
- Ensure all CI checks pass
- Resolve any merge conflicts
- Verify PR has correct labels

## Support

For issues with the new workflow:
1. Check workflow logs in Actions tab
2. Verify branch protection settings
3. Ensure conventional commit format
4. Open an issue if problems persist

---

*This migration enhances security while maintaining release automation. The PR-based approach provides better audit trails and prevents accidental releases.*