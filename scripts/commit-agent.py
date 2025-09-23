#!/usr/bin/env python3
"""
Injx Commit Agent - Ensures proper commit conventions for the project.

This agent analyzes changes and generates properly formatted conventional commits
according to the project's semantic-release standards (Angular Convention).
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import re


class CommitAgent:
    """Intelligent commit agent for Injx project."""

    # Commit types that trigger releases
    RELEASE_TYPES = {"feat", "fix"}

    # All valid commit types
    COMMIT_TYPES = {
        "feat": ("New features", "Minor version"),
        "fix": ("Bug fixes", "Patch version"),
        "docs": ("Documentation changes", "No release"),
        "style": ("Code formatting", "No release"),
        "refactor": ("Code restructuring", "No release"),
        "perf": ("Performance improvements", "No release"),
        "test": ("Test changes", "No release"),
        "chore": ("Maintenance tasks", "No release"),
        "ci": ("CI/CD changes", "No release"),
        "build": ("Build system changes", "No release"),
    }

    # Scope mapping based on file paths
    SCOPE_MAPPING = {
        "src/injx/container.py": "container",
        "src/injx/tokens.py": "tokens",
        "src/injx/injection.py": "injection",
        "src/injx/dependencies.py": "dependencies",
        "src/injx/contextual.py": "contextual",
        "src/injx/analyzer.py": "analyzer",
        "src/injx/scope_manager.py": "scope_manager",
        "src/injx/protocols/": "protocols",
        "tests/": "tests",
        "docs/": "docs",
        ".github/workflows/": "ci",
    }

    def __init__(self):
        """Initialize the commit agent."""
        self.staged_files = self._get_staged_files()
        self.diff = self._get_staged_diff()

    def _run_command(self, cmd: List[str]) -> str:
        """Run a command and return output."""
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout.strip()

    def _get_staged_files(self) -> List[str]:
        """Get list of staged files."""
        output = self._run_command(["git", "diff", "--cached", "--name-only"])
        return output.split("\n") if output else []

    def _get_staged_diff(self) -> str:
        """Get the staged diff."""
        return self._run_command(["git", "diff", "--cached"])

    def _determine_scope(self) -> Optional[str]:
        """Determine the scope based on changed files."""
        scopes = set()
        for file in self.staged_files:
            for pattern, scope in self.SCOPE_MAPPING.items():
                if pattern in file:
                    scopes.add(scope)
                    break

        # Return the most specific scope
        if len(scopes) == 1:
            return scopes.pop()
        elif "container" in scopes or "injection" in scopes or "tokens" in scopes:
            # Core module changes
            return "core"
        elif len(scopes) > 1:
            return None  # Multiple scopes, let user decide
        return None

    def _analyze_changes(self) -> Dict[str, any]:
        """Analyze staged changes to determine commit type and message."""
        analysis = {
            "is_breaking": False,
            "suggested_type": None,
            "suggested_scope": self._determine_scope(),
            "key_changes": [],
        }

        # Check for breaking changes
        if "BREAKING" in self.diff or "!" in self.diff:
            analysis["is_breaking"] = True

        # Analyze diff for type determination
        if any("def test_" in self.diff for _ in [1]):
            analysis["suggested_type"] = "test"
            analysis["key_changes"].append("Added or modified tests")
        elif any(pattern in self.diff for pattern in ["async def", "__await__", "await "]):
            if "async" in self.diff and "def __await__" in self.diff:
                analysis["suggested_type"] = "feat"
                analysis["key_changes"].append("Added async/await support")
        elif "raise " in self.diff or "except " in self.diff:
            analysis["suggested_type"] = "fix"
            analysis["key_changes"].append("Error handling improvements")
        elif "# type: ignore" in self.diff or "-> " in self.diff:
            analysis["suggested_type"] = "fix"
            analysis["key_changes"].append("Type safety improvements")
        elif any(f"src/injx/{module}" in " ".join(self.staged_files)
                for module in ["container.py", "injection.py", "tokens.py"]):
            analysis["suggested_type"] = "feat" if "def " in self.diff else "refactor"

        return analysis

    def _format_commit_message(self, type_: str, scope: Optional[str],
                              description: str, body: Optional[str] = None,
                              breaking: bool = False) -> str:
        """Format a proper conventional commit message."""
        # Build the subject line
        subject = f"{type_}"
        if scope:
            subject += f"({scope})"
        if breaking:
            subject += "!"
        subject += f": {description}"

        # Build the full message
        message = subject
        if body:
            message += f"\n\n{body}"
        if breaking:
            message += "\n\nBREAKING CHANGE: This changes the public API."

        return message

    def suggest_commit(self) -> str:
        """Suggest a commit message based on analysis."""
        if not self.staged_files:
            return "No staged changes to commit."

        analysis = self._analyze_changes()

        # Determine commit type
        if analysis["suggested_type"]:
            type_ = analysis["suggested_type"]
        else:
            # Default based on file location
            if any("src/" in f for f in self.staged_files):
                type_ = "feat"
            else:
                type_ = "chore"

        # Generate description based on changes
        if "dependencies.py" in " ".join(self.staged_files):
            if "__await__" in self.diff:
                description = "make Dependencies awaitable for async resolution"
            elif "type" in self.diff.lower():
                description = "improve type safety with explicit annotations"
            else:
                description = "update Dependencies implementation"
        else:
            description = "update " + (analysis["suggested_scope"] or "implementation")

        # Generate body
        body_lines = []
        if analysis["key_changes"]:
            for change in analysis["key_changes"]:
                body_lines.append(f"- {change}")

        return self._format_commit_message(
            type_,
            analysis["suggested_scope"],
            description,
            "\n".join(body_lines) if body_lines else None,
            analysis["is_breaking"]
        )

    def interactive_commit(self):
        """Interactive commit process."""
        print("🤖 Injx Commit Agent")
        print("=" * 50)
        print(f"📁 Staged files: {len(self.staged_files)}")
        for file in self.staged_files[:5]:  # Show first 5 files
            print(f"  - {file}")
        if len(self.staged_files) > 5:
            print(f"  ... and {len(self.staged_files) - 5} more")
        print()

        # Get suggestion
        suggested = self.suggest_commit()
        print("📝 Suggested commit message:")
        print("-" * 40)
        print(suggested)
        print("-" * 40)
        print()

        # Ask for confirmation or edit
        choice = input("Use this message? [Y]es / [E]dit / [C]ancel: ").lower()

        if choice == "c":
            print("❌ Commit cancelled.")
            sys.exit(0)
        elif choice == "e":
            print("\n📝 Enter your commit message (type END on a new line when done):")
            lines = []
            while True:
                line = input()
                if line == "END":
                    break
                lines.append(line)
            message = "\n".join(lines)
        else:
            message = suggested

        # Execute commit
        print("\n✅ Creating commit...")
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ Commit created successfully!")
            print(result.stdout)
        else:
            print("❌ Commit failed:")
            print(result.stderr)
            sys.exit(1)


def main():
    """Main entry point."""
    agent = CommitAgent()

    if "--suggest" in sys.argv:
        # Just print suggestion and exit
        print(agent.suggest_commit())
    else:
        # Interactive mode
        agent.interactive_commit()


if __name__ == "__main__":
    main()