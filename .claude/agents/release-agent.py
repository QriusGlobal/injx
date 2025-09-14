#!/usr/bin/env python3
"""
Injx Release Agent - Automated release management
Following PEP 440 and Semantic Versioning 2.0.0
"""

from typing import Literal
import subprocess
import sys
from pathlib import Path
try:
    import toml
except ImportError:
    print("Please install toml: pip install toml")
    sys.exit(1)

class InjxReleaseAgent:
    """Manages releases for the injx project."""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.pyproject = self.project_root / "pyproject.toml"
        self.version_file = self.project_root / "src/injx/__init__.py"
        
    def get_current_version(self) -> str:
        """Get current version from pyproject.toml."""
        config = toml.load(self.pyproject)
        return config["project"]["version"]
    
    def determine_next_version(
        self, 
        bump_type: Literal["major", "minor", "patch", "alpha", "beta", "rc"],
        current: str
    ) -> str:
        """Determine next version based on bump type and current version."""
        # Parse current version
        if "-" in current:
            base, prerelease = current.split("-", 1)
        else:
            base = current
            prerelease = None
            
        major, minor, patch = map(int, base.split("."))
        
        # Apply versioning rules for 0.x.y
        if major == 0:
            if bump_type == "major":  # Breaking change in 0.x
                return f"0.{minor + 1}.0"
            elif bump_type in ["minor", "patch"]:
                return f"0.{minor}.{patch + 1}"
        
        # Handle pre-release versions
        if bump_type in ["alpha", "beta", "rc"]:
            if prerelease and bump_type in prerelease:
                # Increment pre-release number
                num = int(prerelease.split(".")[-1]) + 1
                return f"{base}-{bump_type}.{num}"
            else:
                return f"{base}-{bump_type}.1"
                
        # Standard semver after 1.0.0
        if bump_type == "major":
            return f"{major + 1}.0.0"
        elif bump_type == "minor":
            return f"{major}.{minor + 1}.0"
        elif bump_type == "patch":
            return f"{major}.{minor}.{patch + 1}"
            
    def validate_version(self, version: str) -> bool:
        """Validate version against PEP 440."""
        try:
            from packaging.version import Version
            Version(version)
            return True
        except Exception:
            return False
        
    def run_quality_gates(self) -> bool:
        """Run all quality checks before release."""
        checks = [
            ("Tests", "uv run pytest"),
            ("Type Check", "uv run basedpyright src"),
            ("Linting", "uv run ruff check src"),
            ("Docs Build", "uv run mkdocs build"),
        ]
        
        for name, command in checks:
            print(f"Running {name}...")
            result = subprocess.run(command, shell=True, capture_output=True)
            if result.returncode != 0:
                print(f"❌ {name} failed")
                print(result.stderr.decode())
                return False
            print(f"✅ {name} passed")
            
        return True
    
    def update_version_files(self, new_version: str):
        """Update version in all relevant files."""
        # Update pyproject.toml
        config = toml.load(self.pyproject)
        config["project"]["version"] = new_version
        with open(self.pyproject, "w") as f:
            toml.dump(config, f)
        
        # Update __init__.py
        init_content = self.version_file.read_text()
        lines = init_content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("__version__"):
                lines[i] = f'__version__ = "{new_version}"'
                break
        self.version_file.write_text("\n".join(lines))
        
        print(f"Updated version to {new_version}")
        
    def release(self, channel: str = "alpha"):
        """Execute a release to the specified channel."""
        current = self.get_current_version()
        print(f"Current version: {current}")
        
        # Determine bump type based on channel
        if channel == "alpha":
            bump = "alpha"
        elif channel == "beta":
            bump = "beta"
        elif channel == "rc":
            bump = "rc"
        else:
            bump = "patch"  # or determine from commits
            
        next_version = self.determine_next_version(bump, current)
        print(f"Next version: {next_version}")
        
        if not self.validate_version(next_version):
            print(f"❌ Invalid version: {next_version}")
            return False
            
        print("Running quality gates...")
        if not self.run_quality_gates():
            print("❌ Quality gates failed")
            return False
            
        self.update_version_files(next_version)
        
        # Build and publish would go here
        print(f"✅ Ready to release {next_version}")
        print("Note: Actual PyPI publishing not implemented yet")
        
        return True

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Injx Release Agent")
    parser.add_argument(
        "command",
        choices=["check", "release-alpha", "release-beta", "release-rc", "release-stable"],
        help="Command to execute"
    )
    
    args = parser.parse_args()
    agent = InjxReleaseAgent()
    
    if args.command == "check":
        version = agent.get_current_version()
        print(f"Current version: {version}")
        print(f"Valid: {agent.validate_version(version)}")
    elif args.command == "release-alpha":
        agent.release("alpha")
    elif args.command == "release-beta":
        agent.release("beta")
    elif args.command == "release-rc":
        agent.release("rc")
    elif args.command == "release-stable":
        agent.release("stable")

if __name__ == "__main__":
    main()