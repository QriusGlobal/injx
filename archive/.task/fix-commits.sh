#!/bin/bash
# Script to fix semantic versioning commit prefixes

echo "=== Semantic Versioning Correction ==="
echo "Fixing 20 infrastructure commits from fix: to chore:"
echo ""

# Define arrays of commit info
declare -A COMMITS_TO_FIX=(
    ["7479bd8"]="fix: resolve CI/CD issues and add AI development attribution"
    ["b7585c2"]="fix: consolidate CI workflow and fix venv issues"
    ["eb43de7"]="fix: add pytest-cov and pytest-xdist to CI dependencies"
    ["882f26b"]="fix: use uv run for all commands to ensure tools are available"
    ["1f3a021"]="fix: use uvx for tools that don't need to be installed"
    ["89f2414"]="fix: set reportImportCycles and reportAny as warnings not suppressions"
    ["d042455"]="fix: correct Release Please manifest to reflect actual version 0.2.1"
    ["90399f3"]="fix: update Release Please action to working SHA hash and fix YAML formatting"
    ["7d38cf9"]="fix: align version and changelog with PyPI reality"
    ["f037426"]="fix: move TestPyPI to release workflow to test release process"
    ["8f16629"]="fix: break long line in release workflow to meet yamllint standards"
    ["e1fd0ee"]="fix: enable pre-1.0 development with allow_zero_version = true"
    ["77c0cce"]="fix: resolve GitHub Actions workflow issues and enable local testing"
    ["e327182"]="fix: secure GitHub Actions and optimize UV caching"
    ["cc41de2"]="fix: use proper dependency management and add release environment selection"
    ["cd158ba"]="fix: correct semantic-release command syntax in release workflow"
    ["1805031"]="fix: improve dry-run logic and remove redundant flags in release workflow"
    ["28f61f8"]="fix: resolve remaining semantic-release syntax bugs found by Gemini review"
    ["8b05def"]="fix: remove redundant GitHub release creation step"
    ["827ff1f"]="fix: correct UV publish syntax for TestPyPI"
)

# Function to create the rebase sequence editor script
create_sequence_editor() {
    cat > .task/sequence-editor.sh << 'EOF'
#!/bin/bash
# This script modifies the rebase todo list

# Mark specific commits for rewording
sed -i '' -e 's/^pick \(7479bd8\)/reword \1/' \
          -e 's/^pick \(b7585c2\)/reword \1/' \
          -e 's/^pick \(eb43de7\)/reword \1/' \
          -e 's/^pick \(882f26b\)/reword \1/' \
          -e 's/^pick \(1f3a021\)/reword \1/' \
          -e 's/^pick \(89f2414\)/reword \1/' \
          -e 's/^pick \(d042455\)/reword \1/' \
          -e 's/^pick \(90399f3\)/reword \1/' \
          -e 's/^pick \(7d38cf9\)/reword \1/' \
          -e 's/^pick \(f037426\)/reword \1/' \
          -e 's/^pick \(8f16629\)/reword \1/' \
          -e 's/^pick \(e1fd0ee\)/reword \1/' \
          -e 's/^pick \(77c0cce\)/reword \1/' \
          -e 's/^pick \(e327182\)/reword \1/' \
          -e 's/^pick \(cc41de2\)/reword \1/' \
          -e 's/^pick \(cd158ba\)/reword \1/' \
          -e 's/^pick \(1805031\)/reword \1/' \
          -e 's/^pick \(28f61f8\)/reword \1/' \
          -e 's/^pick \(8b05def\)/reword \1/' \
          -e 's/^pick \(827ff1f\)/reword \1/' "$1"
EOF
    chmod +x .task/sequence-editor.sh
}

# Function to create the commit message editor script
create_commit_editor() {
    cat > .task/commit-editor.sh << 'EOF'
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
EOF
    chmod +x .task/commit-editor.sh
}

# Create the editor scripts
create_sequence_editor
create_commit_editor

echo "Editor scripts created."
echo ""
echo "To run the interactive rebase:"
echo "1. Set the sequence editor: export GIT_SEQUENCE_EDITOR=$PWD/.task/sequence-editor.sh"
echo "2. Set the commit editor: export GIT_EDITOR=$PWD/.task/commit-editor.sh"
echo "3. Run: git rebase -i v0.1.0"
echo ""
echo "Or run all at once:"
echo "GIT_SEQUENCE_EDITOR=$PWD/.task/sequence-editor.sh GIT_EDITOR=$PWD/.task/commit-editor.sh git rebase -i v0.1.0"