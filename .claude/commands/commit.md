---
description: Analyze changes and create semantic commits
argument-hint: [-y for auto-accept]
allowed-tools: Bash, Read, SlashCommand
---

# Create Semantic Commit for Injx

Analyze staged changes and propose an appropriate semantic versioning commit.

## Process

Check current git status and invoke the commit sub-agent:

```bash
# First, check if there are staged changes
!git status --short

# Run the commit sub-agent (native shell script)
!./.claude/sub-agents/commit/commit.sh $ARGUMENTS
```

The sub-agent will:
1. Analyze all staged changes
2. Determine the appropriate commit type (feat/fix/docs/test/chore/ci etc.)
3. Identify the scope from modified modules
4. Generate a semantic commit message
5. Show version impact (patch/minor/major/none)
6. Allow you to accept, edit, or cancel

## Arguments
- No arguments: Interactive mode (recommended)
- `-y`: Auto-accept the proposed commit

The sub-agent intelligently categorizes changes:
- src/ changes → feat or fix (triggers releases)
- tests/ changes → test commits
- docs/ changes → docs commits
- .github/ changes → ci commits
- Config files → chore commits