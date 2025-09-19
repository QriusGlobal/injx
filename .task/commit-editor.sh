#!/bin/bash
# This script fixes commit messages during rebase

# Check if this is a commit we need to fix
COMMIT_FILE="$1"

# Read the first line
FIRST_LINE=$(head -n1 "$COMMIT_FILE")

# If it starts with "fix:" and matches our infrastructure patterns, change to "chore:"
if echo "$FIRST_LINE" | grep -E "^fix: .*(CI|workflow|GitHub Actions|UV|TestPyPI|semantic-release|Release Please|yamllint|pytest-cov|pytest-xdist|venv|uvx|uv run|reportImportCycles|reportAny)" > /dev/null; then
    # Replace fix: with chore: on the first line
    sed -i '' '1s/^fix:/chore:/' "$COMMIT_FILE"
fi
