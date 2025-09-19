#!/usr/bin/env python3
"""
Tiered commit prefix validator implementing "Guidance over Gatekeeping" philosophy.

Validation Rules (in priority order):
1. Primary Rule: ANY src/ changes → allow feat, fix, perf, refactor
2. High-Impact Config: ONLY config files → allow broader range
3. Infrastructure Rule: ONLY docs/tests/other → require infrastructure prefixes

Escape Hatch: Use 'git commit --no-verify' for edge cases (audited by CI)
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def is_merge_commit() -> bool:
    """Check if this is a merge commit (should skip validation)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "MERGE_HEAD"],
            capture_output=True,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def get_staged_file_status() -> List[Tuple[str, str]]:
    """Get staged files with their status (for detecting renames)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-status"],
            capture_output=True,
            text=True,
            check=True
        )
        files = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    status = parts[0]
                    filename = parts[1]
                    files.append((status, filename))
        return files
    except subprocess.CalledProcessError:
        return []


def get_commit_message() -> str:
    """Get commit message from command line or editor."""
    if len(sys.argv) > 1:
        # Message passed via -m flag
        return sys.argv[1]

    # Read from commit message file (during git commit)
    commit_msg_file = Path(".git/COMMIT_EDITMSG")
    if commit_msg_file.exists():
        content = commit_msg_file.read_text().strip()
        # Get first line (subject)
        return content.split('\n')[0] if content else ""

    return ""


def extract_commit_prefix(message: str) -> str:
    """Extract the conventional commit prefix (e.g., 'feat', 'fix', 'chore')."""
    # Match conventional commit pattern: type(scope): subject
    match = re.match(r'^(\w+)(?:\([^)]+\))?:', message)
    return match.group(1) if match else ""


def has_bypass_token(message: str) -> bool:
    """Check if commit message contains bypass validation token."""
    full_message = ""

    # Try to get full commit message including body
    commit_msg_file = Path(".git/COMMIT_EDITMSG")
    if commit_msg_file.exists():
        full_message = commit_msg_file.read_text().strip()
    else:
        full_message = message

    # Look for bypass token in commit body
    return "Bypass-Validation:" in full_message


def classify_files(file_statuses: List[Tuple[str, str]]) -> dict:
    """Classify files into categories for validation rules."""
    categories = {
        'src': set(),
        'high_impact_config': set(),
        'infrastructure': set(),
        'renames': set()
    }

    # High-impact config files that can legitimately be feat/fix
    high_impact_patterns = {
        'pyproject.toml', 'uv.lock', 'package.json', 'package-lock.json',
        'Dockerfile', 'docker-compose.yml', 'requirements.txt'
    }

    # Infrastructure directories that require infrastructure prefixes
    infrastructure_dirs = {
        '.github/workflows/', 'tests/', 'docs/', 'scripts/'
    }

    for status, filename in file_statuses:
        # Handle renames specially
        if status.startswith('R'):
            categories['renames'].add(filename)
            continue

        # Categorize by path
        if filename.startswith('src/'):
            categories['src'].add(filename)
        elif filename in high_impact_patterns:
            categories['high_impact_config'].add(filename)
        elif any(filename.startswith(dir_) for dir_ in infrastructure_dirs):
            categories['infrastructure'].add(filename)
        elif filename.endswith(('.md', '.rst', '.txt')):
            categories['infrastructure'].add(filename)
        else:
            categories['infrastructure'].add(filename)

    return categories


def validate_commit_prefix(prefix: str, file_categories: dict) -> Tuple[bool, str]:
    """Validate commit prefix using strict priority hierarchy."""

    # All allowed prefixes
    library_prefixes = {'feat', 'fix', 'perf', 'refactor'}
    infrastructure_prefixes = {'chore', 'ci', 'docs', 'test', 'build', 'style'}
    all_prefixes = library_prefixes | infrastructure_prefixes

    if prefix not in all_prefixes:
        return False, f"Invalid commit prefix '{prefix}'. Allowed: {sorted(all_prefixes)}"

    # Special case: Only renames
    if file_categories['renames'] and not any(file_categories[cat] for cat in ['src', 'high_impact_config', 'infrastructure']):
        if prefix in {'refactor', 'chore'}:
            return True, ""
        return False, f"File renames should use 'refactor' or 'chore', got '{prefix}'"

    # STRICT PRIORITY HIERARCHY (highest priority wins)

    # Priority 1 (HIGHEST): ANY src/ changes - requires library prefix
    if file_categories['src']:
        if prefix in library_prefixes:
            return True, ""
        return False, (
            f"src/ changes require library prefix: {sorted(library_prefixes)}, got '{prefix}'"
        )

    # Priority 2: Infrastructure changes - requires infrastructure prefix
    if file_categories['infrastructure']:
        if prefix in infrastructure_prefixes:
            return True, ""
        return False, (
            f"Infrastructure changes require: {sorted(infrastructure_prefixes)}, got '{prefix}'"
        )

    # Priority 3 (LOWEST): ONLY high-impact config files - allows any prefix
    if file_categories['high_impact_config']:
        return True, ""

    return True, ""


def print_validation_guidance(prefix: str, file_categories: dict, files: List[str]):
    """Print helpful guidance for failed validation."""
    print(f"❌ Commit prefix validation failed:")
    print(f"   Prefix: '{prefix}'")
    print(f"   Files changed: {sorted(files)}")
    print()
    print("📋 Strict Priority Hierarchy (highest priority wins):")
    print("   1. src/ changes → feat, fix, perf, refactor (HIGHEST PRIORITY)")
    print("   2. Infrastructure → chore, ci, docs, test, build, style")
    print("   3. Config files → any prefix allowed (LOWEST PRIORITY)")
    print()
    print("🔧 Categories found:")
    for category, files_in_cat in file_categories.items():
        if files_in_cat:
            print(f"   • {category}: {sorted(files_in_cat)}")
    print()
    print("⚠️  Mixed commits: Highest priority category determines required prefix")
    print("🚪 Escape hatch: Use 'git commit --no-verify' for edge cases")
    print("   (Bypasses will be audited by CI)")


def main() -> int:
    """Main validation logic."""

    # Skip validation for merge commits
    if is_merge_commit():
        print("✅ Skipping validation for merge commit")
        return 0

    file_statuses = get_staged_file_status()
    if not file_statuses:
        print("✅ No staged files, allowing commit")
        return 0

    commit_message = get_commit_message()
    if not commit_message:
        print("❌ No commit message found")
        return 1

    # Check for bypass token
    if has_bypass_token(commit_message):
        print("🚪 Bypass token found, skipping validation")
        return 0

    prefix = extract_commit_prefix(commit_message)
    if not prefix:
        print(f"❌ Invalid conventional commit format: '{commit_message}'")
        print("   Expected: type(scope): description")
        return 1

    file_categories = classify_files(file_statuses)
    is_valid, error_msg = validate_commit_prefix(prefix, file_categories)

    if not is_valid:
        files = [filename for _, filename in file_statuses]
        print_validation_guidance(prefix, file_categories, files)
        if error_msg:
            print(f"   Specific issue: {error_msg}")
        return 1

    # Success message
    changed_categories = [cat for cat, files in file_categories.items() if files]
    print(f"✅ Commit prefix '{prefix}' valid for {changed_categories} changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())