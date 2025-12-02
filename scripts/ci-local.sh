#!/bin/bash
# Local CI - Mirrors GitHub Actions quality gates
# Usage: ./scripts/ci-local.sh

set -e

echo "Running local CI..."
echo ""

uv run ruff format --check src
uv run ruff check src
uv run basedpyright src
uv run mkdocs build --strict
uv run pytest --tb=short -q

echo ""
echo "✅ All quality gates passed!"
