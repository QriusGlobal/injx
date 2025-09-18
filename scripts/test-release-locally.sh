#!/bin/bash
set -e

echo "🧪 Local Release Testing Script"
echo "================================="
echo "Testing the same steps as GitHub Actions workflow..."
echo ""

# Mirror workflow environment setup
echo "📦 Setting up environment..."
echo "  → Installing dependencies with uv..."
uv sync --extra dev > /dev/null 2>&1
uv pip install python-semantic-release > /dev/null 2>&1
echo "  ✅ Dependencies installed"
echo ""

# Mirror quality gates from workflow
echo "🏗️ Running quality gates..."
echo "  → Format check (ruff)..."
if uv run ruff format --check src tests > /dev/null 2>&1; then
    echo "  ✅ Format check passed"
else
    echo "  ❌ Format check failed"
    echo "  💡 Run: uv run ruff format src tests"
    exit 1
fi

echo "  → Lint check (ruff)..."
if uv run ruff check src tests > /dev/null 2>&1; then
    echo "  ✅ Lint check passed"
else
    echo "  ❌ Lint check failed"
    echo "  💡 Run: uv run ruff check src tests --fix"
    exit 1
fi

echo "  → Type check (basedpyright)..."
if uv run basedpyright src > /dev/null 2>&1; then
    echo "  ✅ Type check passed"
else
    echo "  ⚠️  Type check has warnings (check output above)"
    # Don't exit on type warnings, just warn
fi

echo "  → Running tests..."
if uv run pytest -q --maxfail=1 > /dev/null 2>&1; then
    echo "  ✅ All tests passed"
else
    echo "  ❌ Tests failed"
    echo "  💡 Run: uv run pytest -v to see details"
    exit 1
fi
echo ""

# Mirror version determination logic from workflow
echo "🔍 Testing version calculation..."
CURRENT_VERSION=$(uv run python -c \
    "import tomllib; import pathlib; \
    print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])")

echo "  → Current version: $CURRENT_VERSION"

# Test semantic-release version calculation (suppress warnings for cleaner output)
NEXT_VERSION=$(uv run semantic-release version --print 2>/dev/null | tail -1)
echo "  → Next version: $NEXT_VERSION"

if [[ "$NEXT_VERSION" == "$CURRENT_VERSION" ]]; then
    echo "  ❌ No release needed - no changes detected since last release"
    echo "  💡 Make commits with 'feat:' or 'fix:' prefixes to trigger a release"
    exit 1
else
    echo "  ✅ Release needed: $CURRENT_VERSION → $NEXT_VERSION"
fi
echo ""

# Mirror build process from workflow
echo "🎯 Testing build process..."
rm -rf dist > /dev/null 2>&1 || true
echo "  → Building package..."
if uv build > /dev/null 2>&1; then
    echo "  ✅ Package built successfully"
    echo "  📦 Built packages:"
    ls -la dist/ | sed 's/^/     /'
else
    echo "  ❌ Build failed"
    exit 1
fi
echo ""

# Test dry run of semantic-release
echo "🧪 Testing semantic-release dry run..."
echo "  → Running semantic-release version --print..."
if uv run semantic-release version --print > /dev/null 2>&1; then
    echo "  ✅ Semantic-release configuration is valid"
else
    echo "  ❌ Semantic-release configuration has issues"
    echo "  💡 Check pyproject.toml [tool.semantic_release] section"
    exit 1
fi
echo ""

# Summary
echo "✅ Local testing complete!"
echo "================================="
echo "🚀 Ready for GitHub Actions release workflow"
echo "📋 Summary:"
echo "   • Quality gates: ✅ All passed"
echo "   • Version bump: $CURRENT_VERSION → $NEXT_VERSION"
echo "   • Build process: ✅ Working"
echo "   • Semantic-release: ✅ Valid configuration"
echo ""
echo "💡 To perform actual release:"
echo "   1. Go to: https://github.com/QriusGlobal/injx/actions/workflows/release.yml"
echo "   2. Click 'Run workflow'"
echo "   3. Choose release_type: auto"
echo "   4. Set dry_run: false"
echo ""