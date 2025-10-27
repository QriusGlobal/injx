# Emergency Rollback Procedures

## Quick Reference

### If Something Goes Wrong During Rebase
```bash
# Abort the rebase immediately
git rebase --abort
```

### If Rebase Complete But Wrong (Before Push)
```bash
# Reset to backup
git reset --hard main-backup-$(date +%F)
```

### If Bad History Already Pushed
```bash
# Force restore from backup
git push --force origin main-backup-$(date +%F):main
```

## Detailed Rollback Scenarios

### Scenario 1: Rebase Conflicts or Errors

**Symptoms**:
- Git shows merge conflicts during rebase
- Accidentally changed code instead of just messages
- Confused about which commits to change

**Solution**:
```bash
# Stop the rebase immediately
git rebase --abort

# Verify you're back to original state
git status
git log --oneline -5

# Start over with better preparation
```

### Scenario 2: Rebase Complete But Validation Failed

**Symptoms**:
- `git diff main-backup-$(date +%F) main` shows code changes (NOT empty)
- Semantic-release still shows wrong version
- Wrong number of fix:/chore: commits

**Solution**:
```bash
# Reset main to the backup
git reset --hard main-backup-$(date +%F)

# Verify restoration
git log --oneline -5

# Review what went wrong before trying again
```

### Scenario 3: Already Pushed Bad History to Remote

**Symptoms**:
- Force pushed to main but tests failing
- Realized mistakes after push
- CI/CD broken after push

**Solution**:
```bash
# This is the ONLY time raw --force is acceptable (emergency)
git push --force origin main-backup-$(date +%F):main

# Verify remote is restored
git fetch origin
git log --oneline origin/main -5

# Communicate to any team members about the restoration
```

### Scenario 4: Backup Branch Accidentally Deleted

**Symptoms**:
- Deleted backup branch before confirming stability
- Need to restore but backup is gone

**Solution**:
```bash
# Check reflog for the backup branch
git reflog show main-backup-$(date +%F)

# If found, recreate it
git branch main-backup-$(date +%F) <commit-hash-from-reflog>

# If remote backup exists
git fetch origin main-backup-$(date +%F):main-backup-$(date +%F)
```

### Scenario 5: Complete Disaster Recovery

**Symptoms**:
- Multiple things went wrong
- Unsure of current state
- Need clean slate

**Solution**:
```bash
# Start fresh from remote
cd ..
mv injx injx-broken
git clone git@github.com:QriusGlobal/injx.git
cd injx

# If backup branch exists on remote
git fetch origin main-backup-$(date +%F):main-backup-$(date +%F)
git checkout main-backup-$(date +%F)
git branch -f main HEAD
git checkout main
git push --force-with-lease origin main
```

## Prevention Checklist

Before starting rebase:
- [ ] Backup branch created: `git branch main-backup-$(date +%F)`
- [ ] Backup pushed to remote: `git push origin main-backup-$(date +%F)`
- [ ] Working directory clean: `git status`
- [ ] Commit list documented in .task/
- [ ] CI/CD disabled on GitHub

During rebase:
- [ ] Only changing commit messages, not code
- [ ] Following the documented list exactly
- [ ] Double-checking each commit message change

After rebase (before push):
- [ ] Code diff is empty: `git diff main-backup-$(date +%F) main`
- [ ] Correct number of fix: commits (~8)
- [ ] Correct number of chore: commits (~28)
- [ ] Semantic-release shows correct version

## Recovery Verification

After any rollback:
```bash
# Verify branch state
git log --oneline -10
git status

# Verify remote state
git fetch origin
git log --oneline origin/main -5

# Verify semantic-release
uv run semantic-release version --print --dry-run

# Re-enable CI/CD if it was disabled
```

## Important Notes

1. **Keep backup for 24 hours minimum** after successful rebase
2. **Document any issues encountered** for future reference
3. **Test CI/CD thoroughly** after any restoration
4. **Communicate clearly** if this is a team repository
5. **Learn from mistakes** - update procedures if needed

## Contact for Help

If completely stuck:
1. Keep the backup branch intact
2. Document the exact error messages
3. Check git reflog for recovery options
4. Consider restoring from GitHub directly

Remember: The backup branch is your safety net. Don't delete it until you're 100% certain everything is working correctly.