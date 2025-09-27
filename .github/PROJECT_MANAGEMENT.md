# 🚀 injx GitHub Project Management System

## Overview

This project uses a **minimal, practical** GitHub project management system that requires **less than 5 minutes daily** to maintain. Based on what actually works in successful projects like uv, ruff, and FastAPI - not over-engineered enterprise solutions.

## 🏗️ System Architecture

### Core Components

1. **Minimal Labels (7)** - Just enough for organization
2. **Issue Templates (4)** - Structured reporting with auto-labeling
3. **Smart Automation** - Auto-labeling and duplicate detection
4. **GitHub Built-ins** - Milestones, Projects, and standard features

## 🏷️ Label System (7 Labels)

| Label | Purpose | Auto-Applied |
|-------|---------|--------------|
| `bug` | Something broken | ✅ via template |
| `enhancement` | New feature/improvement | ✅ via template |
| `question` | Discussion/help needed | ✅ via template |
| `roadmap` | Major milestone tracking | ✅ via template |
| `needs-triage` | Requires maintainer review | ✅ on all new issues |
| `python-3.14` | Python 3.14 compatibility | ❌ manual |
| `python-3.15` | Python 3.15 compatibility | ❌ manual |

**Supplementary labels** (keep but don't actively use):
- `documentation`, `good first issue`, `help wanted` - For community
- `duplicate`, `invalid`, `wontfix`, `stale` - Administrative

## 📝 Issue Templates

All templates automatically apply appropriate labels + `needs-triage`:

1. **Bug Report** (`bug_report.yaml`) - For bugs
2. **Feature Request** (`feature_request.yaml`) - For enhancements
3. **Question** (`question.yaml`) - For help/discussion
4. **Roadmap Tracker** (`roadmap.yaml`) - For major milestones

## 🤖 Automation Workflows

### Issue Management (`issue-management.yml`)
**Triggers:** Issues opened, edited, reopened

**Features:**
- **Auto-labeling**: Using github/issue-labeler with regex patterns
- **Duplicate Detection**: AI-powered similarity analysis (70% threshold)
- **First-time Welcome**: Automated greeting for new contributors
- **Project Board**: Auto-adds new issues to project board

### AI Triage Bot (`triage-bot.yml`)
**Triggers:** New issues, manual dispatch

**KISS Principle Features:**
- **Simple Categorization**: Bug, enhancement, question, docs, or invalid
- **Two-Step Verification**: Both agents must agree with >90% confidence
- **Monthly Batch PR**: High-confidence triages batched for review
- **Security Safeguards**: Ignores manipulation attempts
- **Chain-of-Thought**: Step-by-step reasoning for transparency

**🔐 OAuth Authentication**: Uses Claude Max/Pro subscription via OAuth token
- No API key required - uses your existing Claude Code subscription
- Single token setup: `CLAUDE_CODE_OAUTH_TOKEN`
- Generate with: `claude setup-token` (for Pro/Max users)

### Label Configuration (`labeler.yml`)
**Pattern-based auto-labeling for:**
- Bug reports (error, crash, exception keywords)
- Feature requests (enhancement, proposal keywords)
- Questions (how to, help keywords)
- Documentation (docs, readme, typo keywords)
- Performance issues (slow, optimize keywords)
- Python version specific (3.14, 3.15 mentions)

#### Issue Triage (`issue-triage.yml`)
**Triggers:** New issues opened
**Actions:**
- Welcomes first-time contributors
- Provides type-specific guidance
- Flags high-priority issues
- Applies `needs-triage` label

#### Stale Management (`stale.yml`)
**Triggers:** Daily at 12:00 UTC
**Actions:**
- Marks issues stale after 14 days
- Closes stale issues after 7 more days
- Exempts: `roadmap`, `python-3.14`, `python-3.15`, `enhancement`

#### Sprint Planning (`sprint-plan.yml`)
**Triggers:** Manual (workflow_dispatch)
**Actions:**
- Creates sprint milestone
- Analyzes triage queue
- Generates prioritized issue list

#### Roadmap Tracker (`roadmap-tracker.yml`)
**Triggers:** Issue/PR closed, manual
**Actions:**
- Updates roadmap checkboxes when issues close
- Tracks PR merges against roadmap items


## 📅 Daily Workflow (< 5 minutes)

### Morning Routine (2-3 minutes)

```bash
# 1. Check triage queue (GitHub web or CLI)
gh issue list --label "needs-triage"

# 2. For each needs-triage issue:
#    - Review and remove needs-triage label
#    - Add appropriate additional labels if needed
#    - Close obvious duplicates/invalid issues

# 3. Quick check for high-priority notifications
gh issue list --search "HIGH PRIORITY" --limit 5
```

### Quick Triage Commands

```bash
# Remove triage label and add python-3.14
gh issue edit [number] --remove-label "needs-triage" --add-label "python-3.14"

# Close with comment
gh issue close [number] --comment "Duplicate of #123"

# Assign to milestone
gh issue edit [number] --milestone "Sprint 2025-Q1-1"
```

## 📆 Weekly Workflow (15 minutes)

### Sprint Planning (Every 2 weeks)

1. **Trigger sprint planning:**
```bash
gh workflow run sprint-plan.yml \
  -f sprint_name="Sprint 2025-Q1-1" \
  -f target_issues=5 \
  -f days_duration=14
```

2. **Review generated sprint plan** (auto-created issue)

3. **Assign issues to sprint milestone:**
```bash
# Batch assign high-priority issues
gh issue edit 1 2 3 --milestone "Sprint 2025-Q1-1"
```

### Roadmap Review (Weekly)

1. **Generate progress report:**
```bash
gh workflow run roadmap-tracker.yml
```

2. **Review roadmap issues:**
```bash
gh issue list --label "roadmap"
```

## 🚀 Release Process

### Manual Release Control

As the core maintainer, you have full control over releases through the existing `release.yml` workflow.

### Release Workflow

```bash
# Test release to TestPyPI
gh workflow run release.yml \
  -f target_environment=testpypi \
  -f dry_run=false

# Production release to PyPI
gh workflow run release.yml \
  -f target_environment=pypi \
  -f dry_run=false

# Dry run to preview changes
gh workflow run release.yml \
  -f target_environment=pypi \
  -f dry_run=true
```

### Conventional Commits (Recommended)

While releases are manual, using conventional commits helps with changelog generation:

```bash
feat: New feature       # Minor version candidate
fix: Bug fix           # Patch version candidate
feat!: Breaking change # Major version candidate
docs:, test:, refactor:, chore:, ci:, perf:, style:  # Non-release commits
```

## 📊 GitHub Project Board Setup

Create a project with 4 views:

### View 1: Triage Queue
- **Filter:** `label:needs-triage`
- **Sort:** Created (oldest first)
- **Purpose:** Daily triage workflow

### View 2: Current Sprint
- **Filter:** Current milestone
- **Group by:** Status
- **Purpose:** Sprint progress tracking

### View 3: Roadmap Overview
- **Filter:** `label:roadmap`
- **Sort:** Priority
- **Purpose:** Long-term planning

### View 4: Release Pipeline
- **Filter:** `milestone:next-release`
- **Group by:** Type (bug/feature)
- **Purpose:** Release planning

## 🎯 Milestone Strategy

### Milestone Structure

The project uses GitHub Milestones to organize work with a **stability-first** approach:

| Milestone | Purpose | Version Target | Priority |
|-----------|---------|---------------|----------|
| **v1.0.0 Stable** | Bug fixes & stability | v1.0.0 | 🔴 **PRIMARY FOCUS** |
| **Python 3.13 Stable** | Maintenance fixes | v0.2.x - v1.0.x | High |
| **Enhancements (Future)** | Nice-to-have features | Post-1.0 | Low |
| **Python 3.14 Compatibility** | Python 3.14 features | TBD (Post-1.0) | Future |
| **Python 3.15 Planning** | Python 3.15 tracking | TBD (Post-1.0) | Future |

### Automatic Issue Assignment

Issues are automatically assigned to milestones based on labels:

- `bug` → v1.0.0 Stable milestone (priority)
- `python-3.14` → Python 3.14 Compatibility milestone (future)
- `python-3.15` → Python 3.15 Planning milestone (future)
- `enhancement` → Enhancements (Future) milestone (low priority)

### Managing Milestones

Use the milestone management script:

```bash
# List all milestones
./.github/scripts/manage-milestones.sh list

# Auto-assign issues based on labels
./.github/scripts/manage-milestones.sh assign

# Show milestone progress
./.github/scripts/manage-milestones.sh progress

# Run all operations
./.github/scripts/manage-milestones.sh all
```

## 🎯 Creating a Master Roadmap Issue

Use the roadmap template to create tracking issues that reference milestones:

```markdown
# Python 3.14 Support Roadmap (Milestone #2)

## Objective
Enable injx to work with Python 3.14's new features

## Success Criteria
- [ ] #101 - Free-threading support (PEP 703)
- [ ] #102 - Sub-interpreter support (PEP 734)
- [ ] #103 - Lazy annotations (PEP 649)
- [ ] #104 - Performance benchmarking
- [ ] #105 - Documentation updates

## Target: v0.4.0 - Q2 2025
## Milestone: Python 3.14 Compatibility (#2)
```

## 🔧 Advanced Commands

### Bulk Operations

```bash
# Label all bugs as high-priority
gh issue list --label bug --json number --jq '.[].number' | \
  xargs gh issue edit --add-label "high-priority"

# Close all questions older than 30 days
gh issue list --label question --json number,createdAt --jq \
  '.[] | select(.createdAt | fromdate < (now - 2592000)) | .number' | \
  xargs gh issue close --comment "Auto-closed due to inactivity"
```

### Analytics

```bash
# Issues closed this week
gh issue list --state closed --json closedAt --jq \
  '[.[] | select(.closedAt | fromdate > (now - 604800))] | length'

# Average time to close (last 10 issues)
gh issue list --state closed --limit 10 --json createdAt,closedAt --jq \
  '[.[] | ((.closedAt | fromdate) - (.createdAt | fromdate)) / 86400] | add/length'
```

## 🤝 Community Contribution Flow

When the project grows:

1. **Good first issues:** Label simple bugs/features
2. **Help wanted:** Label complex issues needing expertise
3. **Documentation:** Always welcome, auto-merged if correct
4. **Triage assistance:** Community can help remove `needs-triage`

## 🚨 Troubleshooting

### Common Issues

**Too many triage issues:**
- Run stale workflow manually: `gh workflow run stale.yml`
- Bulk close old questions
- Consider increasing stale timeout

**Sprint planning not working:**
- Check workflow permissions
- Ensure milestones are enabled in repo settings
- Verify sprint names don't conflict

**Release Please not creating PRs:**
- Check conventional commit format
- Verify `.release-please-config.json` is valid
- Ensure workflow has write permissions

## 📈 Success Metrics

Track these monthly:

- **Triage response time:** Target < 48 hours
- **Issue resolution rate:** Target > 70%
- **Release frequency:** Target 1-2 per month
- **Community PRs:** Growth indicator
- **Stale issue %:** Target < 10%

## 🎬 Getting Started Checklist

- [ ] Labels created (6 core labels)
- [ ] Issue templates configured (4 templates)
- [ ] Workflows deployed (5 workflows)
- [ ] Release Please configured
- [ ] First roadmap issue created
- [ ] GitHub Project board set up
- [ ] Similar Issues AI app installed
- [ ] First sprint planned

## 💡 Tips for Success

1. **Be ruthless with triage** - Close unclear issues quickly
2. **Use templates** - Enforce structure for better automation
3. **Trust automation** - Let bots handle repetitive work
4. **Focus on code** - Spend time coding, not managing
5. **Iterate quickly** - Adjust thresholds based on volume

---

*This system is designed to scale from 1 to 100+ contributors without adding complexity. The automations handle growth, while the simple label system keeps things manageable.*

**Questions?** Create an issue with the `question` label!