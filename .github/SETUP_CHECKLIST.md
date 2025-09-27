# ✅ GitHub Project Management Setup Checklist

## Automated Setup Completed

The following components have been automatically configured:

### ✅ Labels (7 core labels)
- `bug` - Something broken
- `enhancement` - New feature/improvement
- `question` - Discussion/help needed
- `roadmap` - Major milestone tracking
- `needs-triage` - Auto-applied to new issues
- `python-3.14` - Python 3.14 compatibility
- `python-3.15` - Python 3.15 compatibility

### ✅ Issue Templates (4 templates)
- Bug Report (`bug_report.yaml`)
- Feature Request (`feature_request.yaml`)
- Question (`question.yaml`)
- Roadmap Tracker (`roadmap.yaml`)

All templates auto-apply appropriate labels + `needs-triage`

### ✅ Automation Workflows (4 workflows)
- **issue-triage.yml** - Welcomes contributors, provides guidance
- **stale.yml** - Manages inactive issues (14 days → stale → 7 days → close)
- **sprint-plan.yml** - Manual trigger for sprint planning
- **roadmap-tracker.yml** - Updates roadmap issues automatically

### ✅ Release Workflow
- **release.yml** - Manual release control via workflow_dispatch
- Full control over TestPyPI and PyPI releases
- Dry run capability for testing

### ✅ Documentation
- **PROJECT_MANAGEMENT.md** - Complete system documentation
- **SETUP_CHECKLIST.md** - This file
- **create-roadmap-issue.sh** - Script to create master roadmap
- **manage-milestones.sh** - Script to manage milestones and auto-assign issues

### ✅ GitHub Milestones (4 created)
- **Python 3.13 Stable** - Maintenance releases (bug fixes only)
- **v0.3.0 - Enhanced Container API** - Current feature development
- **Python 3.14 Compatibility** - Python 3.14 features (Q2 2025)
- **Python 3.15 Planning** - Python 3.15 tracking (Q4 2025)

## Manual Setup Required

Complete these steps to fully activate the system:

### 1. 🤖 Install Similar Issues AI App

**Purpose:** Automatic duplicate issue detection

**Steps:**
1. Visit: https://github.com/apps/similar-issues-ai
2. Click "Install"
3. Select your repository (QriusGlobal/injx)
4. Grant required permissions
5. No configuration needed - works automatically

**Alternative (if app unavailable):**
- Consider Probot duplicate-issues: https://github.com/apps/duplicate-issues
- Or skip - manual duplicate detection still works

### 2. 📊 Create GitHub Project Board

**Purpose:** Visual tracking with 4 key views

**Steps:**
1. Go to repository → Projects tab → New project
2. Choose "Board" layout
3. Create 4 views:

**View 1: Triage Queue**
```
Filter: label:needs-triage
Sort: Created (oldest first)
Columns: To Do | In Review | Done
```

**View 2: Current Sprint**
```
Filter: milestone:"Sprint 2025-Q1-1"
Group by: Status
Columns: Backlog | In Progress | Review | Done
```

**View 3: Roadmap Overview**
```
Filter: label:roadmap
Sort: Priority (manual)
Columns: Not Started | In Progress | Complete
```

**View 4: Release Pipeline**
```
Filter: milestone:"v0.3.0"
Group by: Labels (bug/enhancement)
Columns: Ready | In Progress | Testing | Released
```

### 3. 📍 Create Master Roadmap Issue

**Purpose:** Central tracking for all development

**Steps:**
```bash
# Run the provided script
./.github/scripts/create-roadmap-issue.sh

# Or create manually using the roadmap template
gh issue create --template roadmap.yaml
```

**Then pin the issue:**
```bash
gh issue pin [issue-number]
```

### 4. 🔐 Verify Workflow Permissions

**Purpose:** Ensure automations can run

**Steps:**
1. Settings → Actions → General
2. Workflow permissions → Read and write permissions ✓
3. Allow GitHub Actions to create and approve pull requests ✓

### 5. 🎯 Run First Sprint Planning

**Purpose:** Test the system end-to-end

**Steps:**
```bash
# Create your first sprint
gh workflow run sprint-plan.yml \
  -f sprint_name="Sprint 2025-Q1-1" \
  -f target_issues=5 \
  -f days_duration=14

# Check the generated sprint planning issue
gh issue list --label roadmap
```

## Quick Test Commands

Verify everything is working:

```bash
# Check labels
gh label list

# Check workflows
gh workflow list

# Create test issue
echo "Test issue for triage" | gh issue create \
  --title "Test: Triage System" \
  --body -

# Check if needs-triage was applied
gh issue list --label needs-triage

# Manual trigger stale check
gh workflow run stale.yml

# Check release workflow
gh workflow view release.yml
```

## Daily Workflow Reminder

Your new daily routine (< 5 minutes):

```bash
# Morning check
gh issue list --label "needs-triage"

# Process each issue
gh issue view [number]
gh issue edit [number] --remove-label "needs-triage"

# That's it!
```

## Support & Troubleshooting

If you encounter issues:

1. Check workflow runs: `gh run list`
2. View workflow logs: `gh run view [run-id]`
3. Check permissions: Settings → Actions → General
4. Review docs: `.github/PROJECT_MANAGEMENT.md`

## Success Indicators

You'll know the system is working when:

- ✅ New issues automatically get `needs-triage` label
- ✅ First-time contributors receive welcome messages
- ✅ Stale issues close automatically after 21 days
- ✅ Roadmap issues update when related issues close
- ✅ Issues auto-assign to milestones based on labels
- ✅ Milestone progress is tracked automatically

---

**Total Setup Time:** ~15 minutes
**Daily Maintenance:** < 5 minutes
**Sprint Planning:** 15 minutes biweekly

Welcome to effortless project management! 🚀