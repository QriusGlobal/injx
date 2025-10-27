#!/bin/bash
# Claude Code Sub-Agent: Intelligent Local CI Pipeline
#
# Smart validation that understands what changed and provides
# targeted feedback with remediation suggestions.
#
# Usage: ./.claude/sub-agents/ci/ci.sh [--full] [--quiet]
#
# This sub-agent:
# 1. Analyzes changed files to determine validation scope
# 2. Runs targeted quality gates based on changes
# 3. Provides intelligent feedback with fix suggestions
# 4. Can be used standalone or via /ci-check slash command

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Options
FULL_CI=false
QUIET=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            FULL_CI=true
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

# State tracking
CHECKS_PASSED=0
CHECKS_FAILED=0
FAILED_CHECKS=()

# Utility functions
log() {
    if [[ "$QUIET" == "false" ]]; then
        echo -e "$1"
    fi
}

error() {
    echo -e "${RED}$1${NC}"
}

success() {
    echo -e "${GREEN}$1${NC}"
}

info() {
    echo -e "${BLUE}$1${NC}"
}

warn() {
    echo -e "${YELLOW}$1${NC}"
}

# Detect what files have changed
detect_changes() {
    local has_src=false
    local has_docs=false
    local has_config=false
    local has_workflows=false

    # Check if we're in a git repo
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        # Not in git, assume all changes
        FULL_CI=true
        return
    fi

    # Get changed files (staged + unstaged)
    local changed_files=$(git diff --name-only --cached 2>/dev/null || true)
    changed_files+=" $(git diff --name-only 2>/dev/null || true)"

    if echo "$changed_files" | grep -q "^src/"; then
        has_src=true
    fi
    if echo "$changed_files" | grep -q "^docs/\|mkdocs.yml"; then
        has_docs=true
    fi
    if echo "$changed_files" | grep -q "pyproject.toml\|uv.lock"; then
        has_config=true
    fi
    if echo "$changed_files" | grep -q "^.github/workflows/"; then
        has_workflows=true
    fi

    log "${CYAN}📊 Change Detection${NC}"
    log "  Source code:     $([ "$has_src" = true ] && echo '✓ Modified' || echo '  Not modified')"
    log "  Documentation:   $([ "$has_docs" = true ] && echo '✓ Modified' || echo '  Not modified')"
    log "  Configuration:   $([ "$has_config" = true ] && echo '✓ Modified' || echo '  Not modified')"
    log "  Workflows:       $([ "$has_workflows" = true ] && echo '✓ Modified' || echo '  Not modified')"
    log ""

    # Export for use in checks
    export HAS_SRC=$has_src
    export HAS_DOCS=$has_docs
    export HAS_CONFIG=$has_config
    export HAS_WORKFLOWS=$has_workflows
}

# Run a single check with smart feedback
run_check() {
    local check_name=$1
    local check_cmd=$2
    local remediation=$3

    log "${BLUE}→ $check_name${NC}"

    if eval "$check_cmd" > /tmp/ci_check_output.txt 2>&1; then
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        success "  ✅ PASSED"
        log ""
        return 0
    else
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        FAILED_CHECKS+=("$check_name")
        error "  ❌ FAILED"

        # Show error output
        if [ -s /tmp/ci_check_output.txt ]; then
            log ""
            log "  ${RED}Error output:${NC}"
            while IFS= read -r line; do
                log "    $line"
            done < /tmp/ci_check_output.txt
        fi

        # Show remediation advice
        if [ -n "$remediation" ]; then
            log ""
            warn "  💡 Fix suggestion:"
            while IFS= read -r line; do
                log "    $line"
            done <<< "$remediation"
        fi

        log ""
        return 1
    fi
}

# Main validation flow
main() {
    log ""
    log "${MAGENTA}╔═══════════════════════════════════════════════════════════════╗${NC}"
    log "${MAGENTA}║${NC}    Intelligent CI Validation - Smart Local Quality Gates   ${MAGENTA}║${NC}"
    log "${MAGENTA}╚═══════════════════════════════════════════════════════════════╝${NC}"
    log ""

    # Analyze what changed
    detect_changes

    # Determine if running full CI or targeted checks
    if [[ "$FULL_CI" == "true" ]]; then
        log "${CYAN}📋 Mode: Full CI Pipeline${NC}"
        log "   Running all quality gates (--full flag or outside git repo)"
        log ""
    else
        log "${CYAN}📋 Mode: Targeted Validation${NC}"
        log "   Running checks based on detected changes"
        log "   Use --full to run all gates regardless"
        log ""
    fi

    # Format check
    if [[ "$FULL_CI" == "true" ]] || [[ "$HAS_SRC" == "true" ]]; then
        run_check \
            "Format Check (Ruff)" \
            "uv run ruff format --check src" \
            "Run: uv run ruff format src"
    fi

    # Lint check
    if [[ "$FULL_CI" == "true" ]] || [[ "$HAS_SRC" == "true" ]]; then
        run_check \
            "Lint Check (Ruff)" \
            "uv run ruff check src" \
            "Run: uv run ruff check src --fix"
    fi

    # Type check
    if [[ "$FULL_CI" == "true" ]] || [[ "$HAS_SRC" == "true" ]]; then
        run_check \
            "Type Check (BasedPyright)" \
            "uv run basedpyright src" \
            "Review type annotations in changed files"
    fi

    # Documentation build - CRITICAL
    if [[ "$FULL_CI" == "true" ]] || [[ "$HAS_DOCS" == "true" ]]; then
        run_check \
            "Documentation Build (MkDocs)" \
            "uv run mkdocs build --strict" \
            "Check mkdocs.yml references all docs files in docs/ directory"
    fi

    # Workflow validation
    if [[ "$FULL_CI" == "true" ]] || [[ "$HAS_WORKFLOWS" == "true" ]]; then
        run_check \
            "Workflow Validation (actionlint)" \
            "uv run actionlint .github/workflows/" \
            "Review GitHub Actions workflow syntax"
    fi

    # Tests (always run for full CI)
    if [[ "$FULL_CI" == "true" ]]; then
        run_check \
            "Test Suite (Pytest)" \
            "uv run pytest --tb=short -q" \
            "Review test output or run: uv run pytest -xvs"
    fi

    # Summary
    log ""
    log "════════════════════════════════════════════════════════════════"
    log "${BLUE}📊 Validation Summary${NC}"
    log "════════════════════════════════════════════════════════════════"
    log "Passed: ${GREEN}${CHECKS_PASSED}${NC}"
    log "Failed: ${RED}${CHECKS_FAILED}${NC}"
    log ""

    if [[ $CHECKS_FAILED -gt 0 ]]; then
        error "❌ Validation Failed"
        log ""
        error "Failed checks:"
        for check in "${FAILED_CHECKS[@]}"; do
            log "  ${RED}✗${NC} $check"
        done
        log ""
        error "Fix the above issues and run this script again."
        log ""
        error "Need help? Try:"
        log "  • ${CYAN}Run full CI${NC}: ./.claude/sub-agents/ci/ci.sh --full"
        log "  • ${CYAN}Check specific area${NC}: uv run pytest -xvs (or similar)"
        log ""
        exit 1
    else
        success "✅ All Validations Passed!"
        log ""
        log "Your code is ready! $([ "$FULL_CI" != "true" ] && echo '(Note: Ran targeted checks only. Use --full for complete CI.)')"
        log ""
        exit 0
    fi
}

# Run main
main
