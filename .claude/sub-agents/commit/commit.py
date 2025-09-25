#!/usr/bin/env python3
"""
Project-Specific Commit Sub-Agent for Injx

This sub-agent handles semantic versioning commits for the injx project.
It analyzes changes and creates properly formatted conventional commits
according to the project's commit standards.
"""

import subprocess
import sys
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class CommitType(Enum):
    """Valid commit types and their release impact."""
    FIX = ("fix", "Bug fixes", "patch")
    FEAT = ("feat", "New features", "minor")
    DOCS = ("docs", "Documentation", None)
    STYLE = ("style", "Formatting", None)
    REFACTOR = ("refactor", "Code restructuring", None)
    TEST = ("test", "Test changes", None)
    CHORE = ("chore", "Maintenance", None)
    CI = ("ci", "CI/CD changes", None)
    PERF = ("perf", "Performance improvements", None)
    BUILD = ("build", "Build system changes", None)

    def __init__(self, prefix: str, description: str, version_impact: Optional[str]):
        self.prefix = prefix
        self.description = description
        self.version_impact = version_impact


@dataclass
class FileChange:
    """Represents a changed file."""
    path: Path
    status: str  # A=added, M=modified, D=deleted
    is_staged: bool


@dataclass
class CommitProposal:
    """A proposed commit message."""
    type: CommitType
    scope: Optional[str]
    subject: str
    body: Optional[str] = None
    breaking: bool = False
    breaking_description: Optional[str] = None
    fixes: Optional[str] = None


class InjxCommitAgent:
    """Semantic versioning commit agent for the injx project."""

    def __init__(self):
        self.project_root = self._find_project_root()
        self.src_modules = {
            "container", "tokens", "injection", "analyzer",
            "contextual", "scope_manager", "protocols", "exceptions"
        }

    def _find_project_root(self) -> Path:
        """Find the project root by looking for pyproject.toml."""
        current = Path.cwd()
        while current != current.parent:
            if (current / "pyproject.toml").exists():
                return current
            current = current.parent
        raise RuntimeError("Could not find project root (no pyproject.toml)")

    def _run_git(self, *args) -> str:
        """Run a git command and return output."""
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        if result.returncode != 0:
            print(f"Git command failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        return result.stdout.strip()

    def get_changes(self) -> Tuple[List[FileChange], List[FileChange]]:
        """Get staged and unstaged changes."""
        staged = []
        unstaged = []

        # Get staged changes
        diff_cached = self._run_git("diff", "--cached", "--name-status")
        if diff_cached:
            for line in diff_cached.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    staged.append(FileChange(
                        path=Path(parts[1]),
                        status=parts[0][0],
                        is_staged=True
                    ))

        # Get unstaged changes
        diff = self._run_git("diff", "--name-status")
        if diff:
            for line in diff.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    unstaged.append(FileChange(
                        path=Path(parts[1]),
                        status=parts[0][0],
                        is_staged=False
                    ))

        # Get untracked files
        untracked = self._run_git("ls-files", "--others", "--exclude-standard")
        if untracked:
            for file in untracked.splitlines():
                unstaged.append(FileChange(
                    path=Path(file),
                    status="A",
                    is_staged=False
                ))

        return staged, unstaged

    def analyze_changes(self, changes: List[FileChange]) -> CommitProposal:
        """Analyze changes and propose a commit message."""
        # Categorize files
        src_files = []
        test_files = []
        doc_files = []
        ci_files = []
        config_files = []

        for change in changes:
            path_str = str(change.path)
            if path_str.startswith("src/"):
                src_files.append(change)
            elif path_str.startswith("tests/"):
                test_files.append(change)
            elif path_str.endswith(".md") or path_str.startswith("docs/"):
                doc_files.append(change)
            elif ".github/" in path_str:
                ci_files.append(change)
            elif path_str in ["pyproject.toml", "uv.lock", "requirements.txt"]:
                config_files.append(change)

        # Determine commit type based on file changes
        if src_files:
            # Source changes - determine if fix or feat
            scope = self._determine_scope(src_files)

            # Check if it's a bug fix (common patterns)
            fix_patterns = ["fix", "bug", "issue", "error", "crash", "leak"]
            diff_content = self._run_git("diff", "--cached")

            is_fix = any(pattern in diff_content.lower() for pattern in fix_patterns)

            if is_fix:
                return CommitProposal(
                    type=CommitType.FIX,
                    scope=scope,
                    subject=self._generate_subject(src_files, "fix")
                )
            else:
                return CommitProposal(
                    type=CommitType.FEAT,
                    scope=scope,
                    subject=self._generate_subject(src_files, "feat")
                )

        elif test_files:
            return CommitProposal(
                type=CommitType.TEST,
                scope=None,
                subject=self._generate_subject(test_files, "test")
            )

        elif doc_files:
            return CommitProposal(
                type=CommitType.DOCS,
                scope=None,
                subject=self._generate_subject(doc_files, "docs")
            )

        elif ci_files:
            return CommitProposal(
                type=CommitType.CI,
                scope="workflows" if any(".github/workflows" in str(f.path) for f in ci_files) else None,
                subject=self._generate_subject(ci_files, "ci")
            )

        else:
            # Default to chore for config/misc changes
            return CommitProposal(
                type=CommitType.CHORE,
                scope=None,
                subject=self._generate_subject(config_files or changes, "chore")
            )

    def _determine_scope(self, src_files: List[FileChange]) -> Optional[str]:
        """Determine scope from source files."""
        modules = set()
        for change in src_files:
            path_parts = change.path.parts
            if len(path_parts) > 2 and path_parts[0] == "src" and path_parts[1] == "injx":
                module = path_parts[2].replace(".py", "")
                if module in self.src_modules:
                    modules.add(module)

        if len(modules) == 1:
            return modules.pop()
        elif len(modules) > 1:
            # Multiple modules - use most significant
            priority = ["container", "tokens", "injection"]
            for module in priority:
                if module in modules:
                    return module
        return None

    def _generate_subject(self, changes: List[FileChange], commit_type: str) -> str:
        """Generate a commit subject based on changes."""
        if len(changes) == 1:
            change = changes[0]
            if change.status == "A":
                return f"add {change.path.name}"
            elif change.status == "D":
                return f"remove {change.path.name}"
            else:
                return f"update {change.path.name}"
        else:
            # Multiple files - generate based on type
            if commit_type == "test":
                return "improve test coverage"
            elif commit_type == "docs":
                return "update documentation"
            elif commit_type == "ci":
                return "update CI configuration"
            else:
                return "update implementation"

    def format_commit_message(self, proposal: CommitProposal) -> str:
        """Format the complete commit message."""
        # Build the subject line
        subject = f"{proposal.type.prefix}"
        if proposal.scope:
            subject += f"({proposal.scope})"
        if proposal.breaking:
            subject += "!"
        subject += f": {proposal.subject}"

        # Build complete message
        message = subject
        if proposal.body:
            message += f"\n\n{proposal.body}"

        footer_items = []
        if proposal.breaking_description:
            footer_items.append(f"BREAKING CHANGE: {proposal.breaking_description}")
        if proposal.fixes:
            footer_items.append(f"Fixes #{proposal.fixes}")

        if footer_items:
            message += "\n\n" + "\n".join(footer_items)

        return message

    def interactive_commit(self):
        """Interactive commit workflow."""
        print("🔍 Analyzing changes...")

        staged, unstaged = self.get_changes()

        if not staged:
            if unstaged:
                print("\n⚠️  No staged changes. You have unstaged changes:")
                for change in unstaged[:5]:  # Show first 5
                    print(f"  {change.status} {change.path}")
                if len(unstaged) > 5:
                    print(f"  ... and {len(unstaged) - 5} more")
                print("\nStage changes with: git add <files>")
            else:
                print("✨ No changes to commit.")
            return

        print(f"\n📝 Staged changes ({len(staged)} files):")
        for change in staged[:10]:  # Show first 10
            print(f"  {change.status} {change.path}")
        if len(staged) > 10:
            print(f"  ... and {len(staged) - 10} more")

        # Analyze and propose
        proposal = self.analyze_changes(staged)
        message = self.format_commit_message(proposal)

        print("\n💡 Proposed commit:")
        print("─" * 50)
        print(message)
        print("─" * 50)

        # Show version impact
        if proposal.type.version_impact:
            print(f"\n📊 Version impact: {proposal.type.version_impact}")
        else:
            print(f"\n📊 Version impact: none (no release)")

        # Ask for confirmation
        print("\nOptions:")
        print("  [y] Accept and commit")
        print("  [e] Edit message")
        print("  [c] Cancel")

        choice = input("\nYour choice [y/e/c]: ").lower().strip()

        if choice == 'y':
            # Commit with the message
            self._run_git("commit", "-m", message)
            print("✅ Commit created successfully!")

            # Show the commit
            log = self._run_git("log", "--oneline", "-1")
            print(f"\n📌 {log}")

        elif choice == 'e':
            # Edit the message
            print("\nEnter your commit message (Ctrl+D when done):")
            lines = []
            try:
                while True:
                    lines.append(input())
            except EOFError:
                pass

            custom_message = "\n".join(lines)
            if custom_message.strip():
                self._run_git("commit", "-m", custom_message)
                print("✅ Commit created with custom message!")
            else:
                print("❌ Empty message, commit cancelled.")

        else:
            print("❌ Commit cancelled.")


def main():
    """Main entry point."""
    agent = InjxCommitAgent()

    if len(sys.argv) > 1:
        # Direct commit message provided
        message = " ".join(sys.argv[1:])
        agent._run_git("commit", "-m", message)
        print(f"✅ Committed: {message}")
    else:
        # Interactive mode
        agent.interactive_commit()


if __name__ == "__main__":
    main()