# Release Recovery Documentation

## Overview

This document provides comprehensive recovery procedures for failed Injx release workflows. The release system is designed with **manual recovery as an intentional safety feature**, not a bug. When releases fail, manual intervention ensures you understand what went wrong and can make informed decisions about how to proceed.

### Philosophy

- **Manual recovery prevents data loss**: Automated cleanup could remove important state
- **Failure investigation is crucial**: Understanding why a release failed prevents future issues
- **Safety over convenience**: Manual steps ensure you're in control of the recovery process

### Common Failure Points

1. **Branch conflicts** (exit code 128) - Most common failure
2. **Tag collisions** - Git tag already exists
3. **PyPI version conflicts** - Version already published
4. **PR creation failures** - GitHub API issues
5. **Partial releases** - Some steps succeeded, others failed

---

## Failure Scenarios & Recovery

### Scenario A: Branch Already Exists (Exit Code 128)

**Symptom:**
```
fatal: a branch named 'release/pypi-v0.2.0' already exists
Process completed with exit code 128
```

This is the most common failure, occurring when:
- Previous release workflow was interrupted
- Manual branch creation conflicted with workflow
- Concurrent release attempts

**Recovery Steps:**

1. **Identify the orphaned branch:**
   ```bash
   git fetch origin
   git branch -r | grep release/
   ```

2. **Check if branch contains important changes:**
   ```bash
   # Compare with main to see what's different
   git log main..origin/release/pypi-v0.2.0 --oneline

   # If you see commits you want to preserve, investigate further
   git show origin/release/pypi-v0.2.0
   ```

3. **Delete the orphaned branch:**
   ```bash
   # For PyPI releases
   git push origin --delete release/pypi-v0.2.0

   # For TestPyPI releases
   git push origin --delete release/testpypi-v0.2.0
   ```

4. **Verify cleanup:**
   ```bash
   git fetch origin --prune
   git branch -r | grep release/  # Should show no release branches
   ```

5. **Retry the release:**
   - Go to GitHub Actions → Release workflow
   - Re-run with same parameters

---

### Scenario B: Tag Already Exists

**Symptom:**
```
fatal: tag 'v0.2.0' already exists
```

**Recovery Steps:**

1. **Check if tag is valid:**
   ```bash
   git fetch origin --tags
   git show v0.2.0  # Examine the tagged commit
   ```

2. **Verify tag points to correct commit:**
   ```bash
   # Check if tag matches your intended release commit
   git log --oneline -10
   ```

3. **If tag is incorrect, delete and recreate:**
   ```bash
   # Delete local tag
   git tag -d v0.2.0

   # Delete remote tag
   git push origin --delete tag v0.2.0
   ```

4. **If tag is correct:**
   - The release may have partially succeeded
   - Check PyPI to see if version was published
   - Skip to "Scenario E: Partial Release" below

---

### Scenario C: PyPI Version Already Published

**Symptom:**
```
Version 0.2.0 already exists on PyPI, skipping publish
released=skipped
```

**Recovery Decision Tree:**

1. **Check if this is intentional:**
   ```bash
   # Verify the published version
   pip index injx | grep 0.2.0
   ```

2. **If version should not exist (accidental publish):**
   ```bash
   # Check what's actually published
   curl -s https://pypi.org/pypi/injx/json | jq '.releases | keys'
   ```

   **Note:** You cannot delete PyPI versions. Options:
   - **Yank the version** (via PyPI web interface)
   - **Publish next patch version** (recommended)

3. **If version is correct:**
   - Release may have succeeded
   - Verify all components: tag, GitHub release, PR
   - See "Post-Recovery Verification" section

---

### Scenario D: PR Creation Failed

**Symptom:**
```
Error: creating pull request failed
```

**Recovery Steps:**

1. **Check if PR already exists:**
   ```bash
   gh pr list --head release/pypi-v0.2.0 --base main
   ```

2. **Create PR manually if needed:**
   ```bash
   # Ensure you're on the release branch
   git checkout release/pypi-v0.2.0

   # Create PR with proper formatting
   gh pr create \
     --title "🚀 Release v0.2.0 to PyPI" \
     --body "## Production Release v0.2.0

   This release has been successfully published to PyPI.

   ### Changes
   - Version bumped to v0.2.0
   - CHANGELOG.md updated with release notes
   - Git tag created: \`v0.2.0\`

   ### Package Links
   - 📦 [PyPI](https://pypi.org/project/injx/0.2.0/)
   - 🏷️ [Git Tag](https://github.com/mishal/qrius-injx/releases/tag/v0.2.0)

   ### Verification
   \`\`\`bash
   pip install injx==0.2.0
   \`\`\`

   Merging this PR will update the main branch with the release version." \
     --base main \
     --head release/pypi-v0.2.0
   ```

---

### Scenario E: Partial Release

When some release steps succeeded but others failed, you need to identify what completed successfully.

**Investigation Steps:**

1. **Check Git state:**
   ```bash
   # Check if tag was created
   git fetch origin --tags
   git tag -l | grep v0.2.0

   # Check if release branch exists
   git fetch origin
   git branch -r | grep release/pypi-v0.2.0
   ```

2. **Check PyPI publication:**
   ```bash
   # For production releases
   pip index injx | grep 0.2.0

   # For test releases
   pip index --index-url https://test.pypi.org/simple/ injx | grep 0.2.0
   ```

3. **Check GitHub Release:**
   ```bash
   gh release list | grep v0.2.0
   ```

4. **Check PRs:**
   ```bash
   gh pr list --state all | grep "Release v0.2.0"
   ```

**Recovery Strategy Based on What Succeeded:**

| Git Tag | PyPI Published | GitHub Release | PR Created | Action Needed |
|---------|----------------|----------------|------------|---------------|
| ✅ | ✅ | ✅ | ❌ | Create PR manually (Scenario D) |
| ✅ | ✅ | ❌ | ❌ | Create GitHub release + PR |
| ✅ | ❌ | ❌ | ❌ | Re-run workflow or manual publish |
| ❌ | ❌ | ❌ | ❌ | Complete cleanup and retry |

---

## Recovery Commands Reference

### Branch Operations
```bash
# List all release branches
git branch -r | grep release/

# Delete specific release branch
git push origin --delete release/pypi-v0.2.0
git push origin --delete release/testpypi-v0.2.0

# Force delete local branch if needed
git branch -D release/pypi-v0.2.0
```

### Tag Management
```bash
# List all tags
git tag -l

# Delete tag locally and remotely
git tag -d v0.2.0
git push origin --delete tag v0.2.0

# Create tag manually if needed
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

### PyPI Verification
```bash
# Check PyPI for version
pip index injx | grep "0.2.0"

# Check TestPyPI for version
pip index --index-url https://test.pypi.org/simple/ injx | grep "0.2.0"

# Download and verify package
pip download injx==0.2.0
```

### GitHub Operations
```bash
# List PRs related to release
gh pr list --state all | grep "Release"

# List GitHub releases
gh release list

# Create GitHub release manually
gh release create v0.2.0 \
  --title "v0.2.0" \
  --generate-notes \
  --latest
```

---

## Pre-Release Checklist

Before triggering any release, verify clean state:

```bash
# 1. Check for orphaned release branches
git fetch origin --prune
git branch -r | grep release/
# Should return empty

# 2. Verify no conflicting tags
git fetch origin --tags
git tag -l | grep v0.2.0
# Should return empty for new version

# 3. Check PyPI status
pip index injx | tail -5
# Verify current version

# 4. Ensure main branch is clean
git status
# Should show "working tree clean"

# 5. Verify CI is passing
gh run list --branch main --limit 5
```

---

## Post-Recovery Verification

After successful recovery and re-run:

### For TestPyPI Releases
```bash
# 1. Verify package published
pip index --index-url https://test.pypi.org/simple/ injx | grep "0.2.0"

# 2. Test installation
pip install -i https://test.pypi.org/simple/ injx==0.2.0

# 3. Verify no orphaned branches
git branch -r | grep release/
# Should be empty (TestPyPI cleans up automatically)
```

### For PyPI Releases
```bash
# 1. Verify package published
pip index injx | grep "0.2.0"

# 2. Test installation
pip install injx==0.2.0

# 3. Verify tag created
git fetch origin --tags
git show v0.2.0

# 4. Verify GitHub release
gh release view v0.2.0

# 5. Verify PR created
gh pr list --head release/pypi-v0.2.0

# 6. Check release branch still exists (for PR)
git branch -r | grep release/pypi-v0.2.0
# Should exist until PR is merged
```

---

## Emergency Procedures

### Complete Release Rollback

If you need to completely undo a failed release:

```bash
# 1. Delete release branch
git push origin --delete release/pypi-v0.2.0

# 2. Delete tag if created
git push origin --delete tag v0.2.0
git tag -d v0.2.0

# 3. Close PR if created
gh pr close $(gh pr list --head release/pypi-v0.2.0 --json number -q '.[0].number')

# 4. Delete GitHub release if created
gh release delete v0.2.0 --yes

# 5. Verify clean state
git fetch origin --prune
git status
```

**Note:** Cannot rollback PyPI publications. If published to PyPI, consider yanking via web interface.

### Force Recovery (Use with Caution)

If normal recovery procedures fail:

```bash
# Nuclear option: delete all release artifacts
for branch in $(git branch -r | grep release/ | sed 's/origin\///'); do
  echo "Deleting branch: $branch"
  git push origin --delete "$branch"
done

# Verify everything is clean
git fetch origin --prune
git branch -r | grep release/  # Should be empty
```

---

## Troubleshooting Tips

### Permission Errors
- Ensure GitHub token has `contents: write` and `pull-requests: write`
- Check if repository has branch protection rules blocking force pushes

### Network/API Failures
- GitHub API rate limits: wait 10-15 minutes and retry
- PyPI upload timeouts: check PyPI status page

### Version Calculation Issues
- Ensure conventional commits are properly formatted
- Check that `semantic-release` can parse commit history

### Workflow Timeout
- Release workflow has 20-minute timeout
- Large packages may need timeout adjustment

---

## Getting Help

If recovery procedures don't resolve the issue:

1. **Check workflow logs**: GitHub Actions → Release workflow → Failed run
2. **Review error details**: Look for specific error messages
3. **Check system status**:
   - [GitHub Status](https://www.githubstatus.com/)
   - [PyPI Status](https://status.python.org/)
4. **Consult project history**: Look for similar issues in recent releases

---

## Best Practices

- **Always investigate before cleaning up**: Understand why the failure occurred
- **One release at a time**: Don't run concurrent release workflows
- **Verify pre-conditions**: Use the pre-release checklist
- **Test with TestPyPI first**: Validate the process before production
- **Keep recovery logs**: Document what went wrong for future reference

---

*This document should be updated whenever new failure patterns are discovered or recovery procedures change.*