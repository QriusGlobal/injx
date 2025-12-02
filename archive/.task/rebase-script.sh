#!/bin/bash
# Interactive Rebase Script for Semantic Versioning Correction

echo "Starting interactive rebase to fix semantic versioning..."
echo "This will change 20 commits from fix: to chore:"
echo ""

# The commits that need to be changed from fix: to chore:
COMMITS_TO_FIX=(
    "827ff1f"  # fix: correct UV publish syntax for TestPyPI
    "8b05def"  # fix: remove redundant GitHub release creation step
    "28f61f8"  # fix: resolve remaining semantic-release syntax bugs found by Gemini review
    "1805031"  # fix: improve dry-run logic and remove redundant flags in release workflow
    "cd158ba"  # fix: correct semantic-release command syntax in release workflow
    "cc41de2"  # fix: use proper dependency management and add release environment selection
    "e327182"  # fix: secure GitHub Actions and optimize UV caching
    "77c0cce"  # fix: resolve GitHub Actions workflow issues and enable local testing
    "e1fd0ee"  # fix: enable pre-1.0 development with allow_zero_version = true
    "8f16629"  # fix: break long line in release workflow to meet yamllint standards
    "f037426"  # fix: move TestPyPI to release workflow to test release process
    "7d38cf9"  # fix: align version and changelog with PyPI reality
    "90399f3"  # fix: update Release Please action to working SHA hash and fix YAML formatting
    "d042455"  # fix: correct Release Please manifest to reflect actual version 0.2.1
    "89f2414"  # fix: set reportImportCycles and reportAny as warnings not suppressions
    "1f3a021"  # fix: use uvx for tools that don't need to be installed
    "882f26b"  # fix: use uv run for all commands to ensure tools are available
    "eb43de7"  # fix: add pytest-cov and pytest-xdist to CI dependencies
    "b7585c2"  # fix: consolidate CI workflow and fix venv issues
    "7479bd8"  # fix: resolve CI/CD issues and add AI development attribution
)

echo "The following commits will be changed from fix: to chore:"
for commit in "${COMMITS_TO_FIX[@]}"; do
    echo "  - $commit"
done
echo ""
echo "Starting rebase..."
echo ""

# Start the interactive rebase
git rebase -i v0.1.0