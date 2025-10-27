#!/usr/bin/env python3
"""
Local CI Pipeline Mirror - Replicates GitHub Actions quality gates locally.

Usage:
    python scripts/ci-local.py [--quiet] [--no-fail-fast] [--json]

This script runs all quality gates in sequence, matching the GitHub Actions CI pipeline.
Developers can run this before pushing to catch issues locally.
"""

import subprocess
import sys
import json
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path
from datetime import datetime

# ANSI color codes
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color


@dataclass
class CheckResult:
    """Result of a single quality gate check."""
    name: str
    passed: bool
    command: str
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class CIPipeline:
    """Orchestrates local CI quality gates."""

    def __init__(self, quiet: bool = False, fail_fast: bool = True, json_output: bool = False):
        self.quiet = quiet
        self.fail_fast = fail_fast
        self.json_output = json_output
        self.results: list[CheckResult] = []
        self.start_time = datetime.now()

    def _print(self, message: str, color: str = Colors.NC):
        """Print colored output if not quiet mode."""
        if not self.quiet:
            print(f"{color}{message}{Colors.NC}")

    def _run_command(self, name: str, command: str) -> CheckResult:
        """Run a single quality gate check."""
        import time
        start = time.time()

        self._print(f"\n{Colors.BLUE}→ {name}{Colors.NC}")
        self._print(f"  Command: {command}", Colors.YELLOW)
        self._print("")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )

            duration = (time.time() - start) * 1000

            if result.returncode == 0:
                self._print(f"✅ PASSED", Colors.GREEN)
                return CheckResult(
                    name=name,
                    passed=True,
                    command=command,
                    output=result.stdout,
                    duration_ms=duration
                )
            else:
                self._print(f"❌ FAILED", Colors.RED)
                if result.stderr:
                    self._print(f"\n{result.stderr}", Colors.RED)
                if result.stdout:
                    self._print(f"\n{result.stdout}", Colors.RED)

                return CheckResult(
                    name=name,
                    passed=False,
                    command=command,
                    error=result.stderr or result.stdout,
                    duration_ms=duration
                )

        except Exception as e:
            self._print(f"❌ EXCEPTION: {str(e)}", Colors.RED)
            return CheckResult(
                name=name,
                passed=False,
                command=command,
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    def run_all_gates(self) -> bool:
        """Run all quality gates in sequence."""
        self._print("╔════════════════════════════════════════════════════════════════╗", Colors.BLUE)
        self._print("║         Local CI Pipeline - Quality Gate Validation         ║", Colors.BLUE)
        self._print("║        Mirrors GitHub Actions workflow locally             ║", Colors.BLUE)
        self._print("╚════════════════════════════════════════════════════════════════╝", Colors.BLUE)

        # Define all quality gates matching GitHub Actions CI
        gates = [
            ("Format Check (Ruff)", "uv run ruff format --check src"),
            ("Lint Check (Ruff)", "uv run ruff check src"),
            ("Type Check (BasedPyright)", "uv run basedpyright src"),
            ("Documentation Build (MkDocs --strict)", "uv run mkdocs build --strict"),
            ("Test Suite (Pytest)", "uv run pytest --tb=short -q"),
        ]

        for name, command in gates:
            result = self._run_command(name, command)
            self.results.append(result)

            if not result.passed and self.fail_fast:
                break

        # Print summary
        self._print_summary()

        return all(r.passed for r in self.results)

    def _print_summary(self):
        """Print summary of all results."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        self._print("\n════════════════════════════════════════════════════════════════", Colors.NC)
        self._print("CI Pipeline Summary", Colors.BLUE)
        self._print("════════════════════════════════════════════════════════════════", Colors.NC)

        self._print(f"Total Checks: {total}")
        self._print(f"Passed: {passed}", Colors.GREEN)
        self._print(f"Failed: {failed}", Colors.RED)

        total_time = (datetime.now() - self.start_time).total_seconds()
        self._print(f"Total Duration: {total_time:.2f}s")

        if failed > 0:
            self._print(f"\n{Colors.RED}❌ CI Pipeline Failed{Colors.NC}")
            self._print("\nFailed gates:")
            for result in self.results:
                if not result.passed:
                    self._print(f"  {Colors.RED}✗{Colors.NC} {result.name} ({result.duration_ms:.0f}ms)")
            self._print("\nFix the above issues and run this script again.\n")
        else:
            self._print(f"\n{Colors.GREEN}✅ All Quality Gates Passed!{Colors.NC}")
            self._print("\nYour code is ready to push! 🚀\n")

    def output_json(self):
        """Output results as JSON."""
        output = {
            "timestamp": datetime.now().isoformat(),
            "passed": all(r.passed for r in self.results),
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
            },
            "results": [asdict(r) for r in self.results],
        }
        print(json.dumps(output, indent=2))


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Local CI Pipeline - Run all quality gates locally"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed output"
    )
    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Continue running all gates even if one fails"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    pipeline = CIPipeline(
        quiet=args.quiet,
        fail_fast=not args.no_fail_fast,
        json_output=args.json
    )

    success = pipeline.run_all_gates()

    if args.json:
        pipeline.output_json()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
