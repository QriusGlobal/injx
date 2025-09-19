#!/usr/bin/env python3
"""
Prepare commit message hook for automatic prefix suggestion.

This hook analyzes staged files and pre-fills the commit message with the
correct prefix based on the strict priority hierarchy. This provides
proactive guidance to prevent classification errors.

Usage:
    - Automatically called by git during commit preparation
    - Can be overridden with environment variables:
      INJX_COMMIT_TYPE=feat INJX_COMMIT_SCOPE=container git commit
    - Only fills blank commit messages (preserves user input)
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional


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


def classify_files(file_statuses: List[Tuple[str, str]]) -> dict:
    """Classify files into categories using the same logic as the validator."""
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

        # Categorize by path (same logic as validator)
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


def determine_commit_type_and_scope(file_categories: dict) -> Tuple[str, Optional[str]]:
    """Determine the recommended commit type and scope based on file categories."""

    # Handle renames
    if file_categories['renames'] and not any(file_categories[cat] for cat in ['src', 'high_impact_config', 'infrastructure']):
        return 'refactor', None

    # STRICT PRIORITY HIERARCHY (matches validator)

    # Priority 1 (HIGHEST): ANY src/ changes
    if file_categories['src']:
        # Try to determine scope from src/ files
        src_files = file_categories['src']
        if any('container' in f for f in src_files):
            return 'feat', 'container'
        elif any('token' in f for f in src_files):
            return 'feat', 'tokens'
        elif any('injection' in f for f in src_files):
            return 'feat', 'injection'
        elif any('scope' in f for f in src_files):
            return 'feat', 'scope'
        else:
            return 'feat', None

    # Priority 2: Infrastructure changes
    if file_categories['infrastructure']:
        infrastructure_files = file_categories['infrastructure']

        # Determine type based on infrastructure type
        if any('.github/workflows/' in f for f in infrastructure_files):
            return 'ci', 'workflows'
        elif any('tests/' in f for f in infrastructure_files):
            return 'test', None
        elif any('docs/' in f for f in infrastructure_files):
            return 'docs', None
        elif any('scripts/' in f for f in infrastructure_files):
            return 'chore', 'scripts'
        elif any(f.endswith('.md') for f in infrastructure_files):
            return 'docs', None
        else:
            return 'chore', None

    # Priority 3 (LOWEST): Config files - default to chore
    if file_categories['high_impact_config']:
        config_files = file_categories['high_impact_config']
        if 'pyproject.toml' in config_files:
            return 'chore', 'deps'
        elif 'Dockerfile' in config_files:
            return 'chore', 'docker'
        else:
            return 'chore', None

    # Fallback
    return 'chore', None


def get_env_overrides() -> Tuple[Optional[str], Optional[str]]:
    """Get environment variable overrides for commit type and scope."""
    commit_type = os.environ.get('INJX_COMMIT_TYPE')
    commit_scope = os.environ.get('INJX_COMMIT_SCOPE')
    return commit_type, commit_scope


def format_commit_message(commit_type: str, scope: Optional[str]) -> str:
    """Format the commit message with type and scope."""
    if scope:
        return f"{commit_type}({scope}): "
    else:
        return f"{commit_type}: "


def should_prepare_message(commit_msg_file: Path) -> bool:
    """Check if we should prepare the commit message (only if blank or default)."""
    if not commit_msg_file.exists():
        return True

    content = commit_msg_file.read_text().strip()

    # Don't override if user has already written something meaningful
    if content and not content.startswith('#'):
        # Check if it's already a conventional commit
        if re.match(r'^[a-z]+(\([^)]+\))?\s*:', content):
            return False
        # Check if it's substantial user content
        if len(content) > 20:
            return False

    return True


def main() -> int:
    """Main prepare commit message logic."""

    # Get commit message file from git
    if len(sys.argv) < 2:
        return 0  # No commit message file provided

    commit_msg_file = Path(sys.argv[1])

    # Check if we should prepare the message
    if not should_prepare_message(commit_msg_file):
        return 0

    # Get staged files
    file_statuses = get_staged_file_status()
    if not file_statuses:
        return 0  # No staged files

    # Classify files
    file_categories = classify_files(file_statuses)

    # Check for environment overrides
    env_type, env_scope = get_env_overrides()

    if env_type:
        # Use environment overrides
        commit_type = env_type
        scope = env_scope
    else:
        # Determine automatically
        commit_type, scope = determine_commit_type_and_scope(file_categories)

    # Format the message
    prepared_message = format_commit_message(commit_type, scope)

    # Preserve any existing content (like from -m flag)
    existing_content = ""
    if commit_msg_file.exists():
        existing_content = commit_msg_file.read_text().strip()
        # If there's already content, don't override
        if existing_content and not existing_content.startswith('#'):
            return 0

    # Write the prepared message
    try:
        commit_msg_file.write_text(prepared_message)
    except Exception:
        # If we can't write, don't fail the commit
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())