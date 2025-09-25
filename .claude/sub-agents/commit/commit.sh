#!/usr/bin/env bash
#
# Semantic Commit Sub-Agent for Injx
# A lightweight shell script for creating conventional commits
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check for auto-accept flag
AUTO_ACCEPT=false
if [[ "$1" == "-y" ]]; then
	AUTO_ACCEPT=true
fi

# Direct commit message provided
if [[ $# -gt 0 && "$1" != "-y" ]]; then
	git commit -m "$*"
	echo -e "${GREEN}✅ Committed: $*${NC}"
	exit 0
fi

# Function to analyze staged changes
analyze_changes() {
	local has_src=false
	local has_test=false
	local has_docs=false
	local has_ci=false
	local has_config=false
	local scope=""

	# Analyze staged files
	while IFS=$'\t' read -r status file; do
		case "$file" in
		src/injx/*.py)
			has_src=true
			# Extract module name for scope
			basename="${file##*/}"
			module="${basename%.py}"
			if [[ -z "$scope" && "$module" != "__init__" ]]; then
				scope="$module"
			fi
			;;
		src/*)
			has_src=true
			;;
		tests/*)
			has_test=true
			;;
		*.md | docs/*)
			has_docs=true
			;;
		.github/*)
			has_ci=true
			;;
		pyproject.toml | uv.lock | requirements*.txt)
			has_config=true
			;;
		esac
	done < <(git diff --cached --name-status)

	# Determine commit type based on file changes
	local type="chore"
	local subject="update"

	if $has_src; then
		# Check if it's a bug fix by looking for fix patterns in the diff
		if git diff --cached | grep -qi '\(fix\|bug\|issue\|error\|crash\|leak\|race\)'; then
			type="fix"
			subject="resolve issue"
		else
			type="feat"
			subject="update implementation"
		fi
	elif $has_test; then
		type="test"
		subject="update tests"
	elif $has_docs; then
		type="docs"
		subject="update documentation"
	elif $has_ci; then
		type="ci"
		scope="workflows"
		subject="update CI configuration"
	elif $has_config; then
		type="chore"
		subject="update configuration"
	fi

	# Build commit message
	local message="$type"
	if [[ -n "$scope" ]]; then
		message="$message($scope)"
	fi
	message="$message: $subject"

	echo "$message"
}

# Function to get version impact
get_version_impact() {
	local type="$1"
	case "$type" in
	fix) echo "patch" ;;
	feat) echo "minor" ;;
	*) echo "none" ;;
	esac
}

# Main flow
echo -e "${BLUE}🔍 Analyzing changes...${NC}"
echo

# Check for staged changes
staged_count=$(git diff --cached --name-status | wc -l)
if [[ $staged_count -eq 0 ]]; then
	# Check for unstaged changes
	unstaged_count=$(git diff --name-status | wc -l)
	if [[ $unstaged_count -gt 0 ]]; then
		echo -e "${YELLOW}⚠️  No staged changes. You have unstaged changes:${NC}"
		git diff --name-status | head -5 | while IFS=$'\t' read -r status file; do
			echo "  $status $file"
		done
		if [[ $unstaged_count -gt 5 ]]; then
			echo "  ... and $((unstaged_count - 5)) more"
		fi
		echo
		echo "Stage changes with: git add <files>"
	else
		echo -e "${GREEN}✨ No changes to commit.${NC}"
	fi
	exit 0
fi

# Show staged changes
echo -e "${BLUE}📝 Staged changes ($staged_count files):${NC}"
git diff --cached --name-status | head -10 | while IFS=$'\t' read -r status file; do
	echo "  $status $file"
done
if [[ $staged_count -gt 10 ]]; then
	echo "  ... and $((staged_count - 10)) more"
fi
echo

# Analyze and propose commit
proposed_message=$(analyze_changes)
type="${proposed_message%%:*}"
type="${type%%(*}" # Remove scope if present
version_impact=$(get_version_impact "$type")

# Display proposal
echo -e "${BLUE}💡 Proposed commit:${NC}"
echo "──────────────────────────────────────────────────"
echo "$proposed_message"
echo "──────────────────────────────────────────────────"
echo
if [[ "$version_impact" == "none" ]]; then
	echo -e "📊 Version impact: none (no release)"
else
	echo -e "📊 Version impact: ${YELLOW}$version_impact${NC}"
fi
echo

# Handle user choice
if $AUTO_ACCEPT; then
	echo "Options:"
	echo "  [y] Accept and commit"
	echo "  [e] Edit message"
	echo "  [c] Cancel"
	echo
	echo -e "Your choice [y/e/c]: ${GREEN}y (auto-accept mode)${NC}"
	choice="y"
else
	echo "Options:"
	echo "  [y] Accept and commit"
	echo "  [e] Edit message"
	echo "  [c] Cancel"
	echo
	read -r -p "Your choice [y/e/c]: " choice
fi

case "$choice" in
y | Y)
	git commit -m "$proposed_message"
	echo -e "${GREEN}✅ Commit created successfully!${NC}"
	echo
	echo -e "📌 $(git log --oneline -1)"
	;;
e | E)
	echo
	echo "Enter your commit message (or press Ctrl+C to cancel):"
	read -r -p "> " custom_message
	if [[ -n "$custom_message" ]]; then
		git commit -m "$custom_message"
		echo -e "${GREEN}✅ Commit created with custom message!${NC}"
	else
		echo -e "${RED}❌ Empty message, commit cancelled.${NC}"
		exit 1
	fi
	;;
*)
	echo -e "${RED}❌ Commit cancelled.${NC}"
	exit 0
	;;
esac
