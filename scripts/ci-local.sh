#!/bin/bash
# Local CI Pipeline Mirror - Replicates GitHub Actions quality gates locally
# Usage: ./scripts/ci-local.sh [--fail-fast] [--quiet]
#
# This script runs the exact same quality gates as the GitHub Actions CI pipeline,
# allowing developers to catch issues before pushing. All gates must pass.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Options parsing
FAIL_FAST=true
QUIET=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-fail-fast)
            FAIL_FAST=false
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Tracking
PASSED=0
FAILED=0
TOTAL=0
FAILED_GATES=()

# Helper function to run a check
run_check() {
    local name=$1
    local command=$2

    TOTAL=$((TOTAL + 1))

    if [[ "$QUIET" == "false" ]]; then
        echo ""
        printf "${BLUE}Step ${TOTAL}:${NC} ${name}\n"
        echo "  Command: $command"
        echo ""
    fi

    if eval "$command"; then
        PASSED=$((PASSED + 1))
        if [[ "$QUIET" == "false" ]]; then
            printf "${GREEN}✅ PASSED${NC}\n"
        fi
    else
        FAILED=$((FAILED + 1))
        FAILED_GATES+=("$name")
        if [[ "$QUIET" == "false" ]]; then
            printf "${RED}❌ FAILED${NC}\n"
        fi

        if [[ "$FAIL_FAST" == "true" ]]; then
            echo ""
            printf "${RED}Stopping on first failure (use --no-fail-fast to continue)${NC}\n"
            echo ""
            exit 1
        fi
    fi
}

# Banner
if [[ "$QUIET" == "false" ]]; then
    echo ""
    printf "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}\n"
    printf "${BLUE}║${NC}         Local CI Pipeline - Quality Gate Validation         ${BLUE}║${NC}\n"
    printf "${BLUE}║${NC}        Mirrors GitHub Actions workflow locally             ${BLUE}║${NC}\n"
    printf "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}\n"
fi

# Gate 1: Format Check (Ruff)
run_check \
    "Format Check (Ruff)" \
    "uv run ruff format --check src"

# Gate 2: Lint (Ruff)
run_check \
    "Lint Check (Ruff)" \
    "uv run ruff check src"

# Gate 3: Type Check (BasedPyright)
run_check \
    "Type Check (BasedPyright)" \
    "uv run basedpyright src"

# Gate 4: Documentation Build (MkDocs - THE CRITICAL GATE)
run_check \
    "Documentation Build (MkDocs --strict)" \
    "uv run mkdocs build --strict"

# Gate 5: Tests
run_check \
    "Test Suite (Pytest)" \
    "uv run pytest --tb=short -q"

# Summary
echo ""
echo "════════════════════════════════════════════════════════════════"
printf "${BLUE}CI Pipeline Summary${NC}\n"
echo "════════════════════════════════════════════════════════════════"
printf "Total Checks: ${TOTAL}\n"
printf "Passed: ${GREEN}${PASSED}${NC}\n"
printf "Failed: ${RED}${FAILED}${NC}\n"
echo ""

if [[ $FAILED -gt 0 ]]; then
    printf "${RED}❌ CI Pipeline Failed${NC}\n"
    echo ""
    echo "Failed gates:"
    for gate in "${FAILED_GATES[@]}"; do
        printf "  ${RED}✗${NC} $gate\n"
    done
    echo ""
    echo "Fix the above issues and run this script again."
    echo ""
    exit 1
else
    printf "${GREEN}✅ All Quality Gates Passed!${NC}\n"
    echo ""
    echo "Your code is ready to push! 🚀"
    echo ""
    exit 0
fi
