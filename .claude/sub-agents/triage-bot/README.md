# 🤖 Claude Code Triage Bot

An intelligent issue triage system using Claude Code GitHub Actions with confidence-based automation.

## Overview

This triage bot automatically analyzes new GitHub issues, categorizes them with high confidence, and batches decisions into monthly PRs for review. Only triages with >90% confidence are applied automatically.

## Architecture

### Two-Step Verification Process

1. **Initial Analysis** - Claude analyzes the issue and provides triage recommendations
2. **Verification** - A second Claude agent reviews the triage for accuracy
3. **Application** - If both agree with >90% confidence, adds to monthly batch

### Monthly Batch System

- Maintains an open PR for each month (e.g., "Triage-2025-01")
- High-confidence triages are committed to this PR
- You review the batch at your convenience
- Approve the PR to apply all triages at once

## Components

### 1. GitHub Action Workflow (`triage-bot.yml`)

Triggered on:
- New issues opened
- Issue edits
- Manual workflow dispatch

Jobs:
- `triage-analysis`: Initial Claude analysis with confidence scoring
- `verify-triage`: Second opinion verification
- `apply-triage`: Adds to monthly PR if confidence >90%
- `manual-review-needed`: Flags low-confidence issues

### 2. Claude Code Sub-Agent (`triage.sh`)

Local triage logic with:
- Pattern-based categorization
- Priority assessment
- Duplicate detection
- Label recommendations
- Milestone assignment
- Confidence scoring algorithm

## Confidence Scoring

The bot calculates confidence based on:
- **Clarity** (0-30 points): How clear the issue description is
- **Pattern Match** (0-30 points): How well it matches known patterns
- **Duplicate Detection** (0-20 points): Similarity to existing issues
- **Context Understanding** (0-20 points): Overall comprehension

Total score determines action:
- **90-100%**: Automatic triage to monthly PR
- **75-89%**: Suggested triage, needs review
- **<75%**: Flagged for manual triage

## Categories

Issues are categorized as:
- **bug**: Something broken, errors, crashes
- **enhancement**: Feature requests, improvements
- **question**: How-to, discussions
- **documentation**: Docs improvements, typos
- **invalid**: Not actionable, spam

## Priority Levels

- **critical**: Data loss, security, crashes
- **high**: Major functionality broken
- **medium**: Workaround exists
- **low**: Minor issues, nice-to-haves

## Labels Applied

Automatic labels based on content:
- Category labels (bug, enhancement, etc.)
- Priority labels (for critical bugs)
- Python version labels (python-3.14, python-3.15)
- good-first-issue (for simple tasks)
- performance (for speed issues)
- duplicate (if similar issues found)

## Milestone Assignment

Automatic milestone routing:
- Bugs → v1.0.0 Stable
- Python 3.14 features → Python 3.14 Compatibility
- Python 3.15 features → Python 3.15 Planning
- Enhancements → Enhancements (Future)

## Setup

### 1. Prerequisites

- GitHub repository with admin access
- Anthropic API key for Claude
- GitHub token with appropriate permissions

### 2. Configuration

Add to repository secrets:
```
ANTHROPIC_API_KEY=<your-api-key>
```

### 3. Installation

The workflow is automatically active once added to `.github/workflows/`.

### 4. Manual Testing

Test the triage bot locally:
```bash
# Triage a specific issue
./.claude/sub-agents/triage-bot/triage.sh triage 123

# Batch triage all needs-triage issues
./.claude/sub-agents/triage-bot/triage.sh batch
```

## Usage

### Automatic Mode

1. New issue is opened
2. Bot analyzes with Claude
3. If confidence >90%, adds to monthly PR
4. Otherwise, adds `needs-triage` label

### Manual Mode

Trigger workflow manually:
```bash
gh workflow run triage-bot.yml \
  -f issue_number=123 \
  -f batch_triage=false
```

### Batch Mode

Triage all pending issues:
```bash
gh workflow run triage-bot.yml \
  -f batch_triage=true
```

## Monthly Review Process

1. Bot creates/updates monthly PR (e.g., PR #45 for January 2025)
2. Each triage is a separate commit with description
3. Triage logs saved in `.github/triage-log/YYYY-MM/`
4. Review the PR to see all triages
5. Request changes for any incorrect triages
6. Approve and merge to apply all triages

## Monitoring

### Success Metrics

- **Accuracy**: % of correct triages
- **Confidence**: Average confidence score
- **Coverage**: % of issues auto-triaged
- **Time Saved**: Manual triage time reduced

### Logs

Check workflow runs:
```bash
gh run list --workflow=triage-bot.yml
gh run view <run-id>
```

### Triage History

All decisions logged in:
```
.github/triage-log/
├── 2025-01/
│   ├── issue-123.json
│   ├── issue-124.json
│   └── issue-125.json
└── 2025-02/
    └── ...
```

## Troubleshooting

### Low Confidence Issues

If many issues have low confidence:
1. Review issue templates - ensure structured input
2. Check categorization patterns in `triage.sh`
3. Adjust confidence thresholds if needed

### API Rate Limits

The bot respects GitHub API limits. For high-volume repos:
1. Use batch mode during off-hours
2. Adjust workflow triggers
3. Consider caching strategies

### False Positives

If incorrect triages occur:
1. Review the triage log for that issue
2. Adjust patterns in `triage.sh`
3. Provide feedback by editing the monthly PR

## Future Enhancements

- [ ] Learning from feedback (track accuracy)
- [ ] Custom categorization rules
- [ ] Integration with project boards
- [ ] Slack/Discord notifications
- [ ] Multi-repo support
- [ ] Triage performance dashboard

## Contributing

To improve the triage bot:
1. Edit patterns in `triage.sh`
2. Adjust confidence thresholds
3. Add new categorization rules
4. Submit PR with test cases

## License

Part of the injx project. See main LICENSE file.