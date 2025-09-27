#!/usr/bin/env bash

# Script to manage GitHub milestones and auto-assign issues based on labels

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Function to list all milestones
list_milestones() {
    echo "📊 Current Milestones:"
    echo "─────────────────────"

    gh api repos/QriusGlobal/injx/milestones --jq '.[] | "\(.number). \(.title) - \(.state) (Issues: \(.open_issues)/\(.open_issues + .closed_issues))"'
}

# Function to auto-assign issues to milestones based on labels
auto_assign_issues() {
    print_info "Auto-assigning issues to milestones based on labels..."

    # Get milestone numbers
    V100_MILESTONE=$(gh api repos/QriusGlobal/injx/milestones --jq '.[] | select(.title == "v1.0.0 Stable") | .number')
    PYTHON_313_MILESTONE=$(gh api repos/QriusGlobal/injx/milestones --jq '.[] | select(.title == "Python 3.13 Stable") | .number')
    PYTHON_314_MILESTONE=$(gh api repos/QriusGlobal/injx/milestones --jq '.[] | select(.title == "Python 3.14 Compatibility") | .number')
    PYTHON_315_MILESTONE=$(gh api repos/QriusGlobal/injx/milestones --jq '.[] | select(.title == "Python 3.15 Planning") | .number')
    ENHANCEMENTS_MILESTONE=$(gh api repos/QriusGlobal/injx/milestones --jq '.[] | select(.title == "Enhancements (Future)") | .number')

    # Process Python 3.14 labeled issues
    if [ -n "$PYTHON_314_MILESTONE" ]; then
        print_info "Processing Python 3.14 issues..."
        gh issue list --label "python-3.14" --json number --jq '.[].number' | while read -r issue_num; do
            gh issue edit "$issue_num" --milestone "$PYTHON_314_MILESTONE" 2>/dev/null && \
                print_status "Issue #$issue_num assigned to Python 3.14 milestone" || \
                print_warning "Issue #$issue_num already has a milestone"
        done
    fi

    # Process Python 3.15 labeled issues
    if [ -n "$PYTHON_315_MILESTONE" ]; then
        print_info "Processing Python 3.15 issues..."
        gh issue list --label "python-3.15" --json number --jq '.[].number' | while read -r issue_num; do
            gh issue edit "$issue_num" --milestone "$PYTHON_315_MILESTONE" 2>/dev/null && \
                print_status "Issue #$issue_num assigned to Python 3.15 milestone" || \
                print_warning "Issue #$issue_num already has a milestone"
        done
    fi

    # Process ALL bug issues for v1.0.0 (primary focus)
    if [ -n "$V100_MILESTONE" ]; then
        print_info "Processing bugs for v1.0.0 Stable (PRIMARY FOCUS)..."
        gh issue list --label "bug" --json number --jq '.[].number' | while read -r issue_num; do
            # Check if issue already has a milestone
            current_milestone=$(gh issue view "$issue_num" --json milestone --jq '.milestone.number // empty')
            if [ -z "$current_milestone" ]; then
                gh issue edit "$issue_num" --milestone "$V100_MILESTONE" && \
                    print_status "Bug #$issue_num assigned to v1.0.0 Stable milestone (PRIORITY)"
            fi
        done
    fi

    # Process enhancement issues for Future milestone (low priority)
    if [ -n "$ENHANCEMENTS_MILESTONE" ]; then
        print_info "Processing enhancements for Future milestone..."
        gh issue list --label "enhancement" --json number,labels --jq '.[] | select([.labels[].name] | contains(["python-3.14"]) | not) | select([.labels[].name] | contains(["python-3.15"]) | not) | .number' | while read -r issue_num; do
            current_milestone=$(gh issue view "$issue_num" --json milestone --jq '.milestone.number // empty')
            if [ -z "$current_milestone" ]; then
                gh issue edit "$issue_num" --milestone "$ENHANCEMENTS_MILESTONE" && \
                    print_status "Enhancement #$issue_num assigned to Future Enhancements (low priority)"
            fi
        done
    fi

    print_status "Auto-assignment complete!"
}

# Function to show milestone progress
show_progress() {
    print_info "Milestone Progress Report"
    echo "═══════════════════════════════════"

    gh api repos/QriusGlobal/injx/milestones --jq '.[] |
        . as $m |
        if (.open_issues + .closed_issues) > 0 then
            ((.closed_issues / (.open_issues + .closed_issues)) * 100) as $percent |
            "\n📌 \(.title)\n   Progress: \($percent | floor)% (\(.closed_issues)/\(.open_issues + .closed_issues) completed)\n   Due: \(.due_on // "No due date")\n   Open Issues: \(.open_issues)"
        else
            "\n📌 \(.title)\n   No issues assigned yet\n   Due: \(.due_on // "No due date")"
        end'
}

# Function to update milestone descriptions with current PEPs and features
update_python_milestones() {
    print_info "Updating Python milestone descriptions with latest PEPs..."

    # Update Python 3.14 milestone (post-v1.0.0)
    PYTHON_314_MILESTONE=$(gh api repos/QriusGlobal/injx/milestones --jq '.[] | select(.title == "Python 3.14 Compatibility") | .number')
    if [ -n "$PYTHON_314_MILESTONE" ]; then
        gh api repos/QriusGlobal/injx/milestones/"$PYTHON_314_MILESTONE" --method PATCH \
            -f description="Python 3.14 support including:
• Free-threading support (PEP 703) - Optional GIL removal
• Sub-interpreters (PEP 734) - True parallelism
• Lazy annotations (PEP 649) - Zero-overhead type hints
• Enhanced error messages
• Performance improvements
Target: Q2 2026 (Post-v1.0.0)" \
            -f due_on="2026-06-30T23:59:59Z"
        print_status "Updated Python 3.14 milestone description"
    fi

    # Update Python 3.15 milestone (post-v1.0.0)
    PYTHON_315_MILESTONE=$(gh api repos/QriusGlobal/injx/milestones --jq '.[] | select(.title == "Python 3.15 Planning") | .number')
    if [ -n "$PYTHON_315_MILESTONE" ]; then
        gh api repos/QriusGlobal/injx/milestones/"$PYTHON_315_MILESTONE" --method PATCH \
            -f description="Python 3.15 compatibility tracking. Features TBD as Python development progresses.
Will be updated as PEPs are accepted for Python 3.15.
Target: Q2 2026 (Post-v1.0.0)" \
            -f due_on="2026-06-30T23:59:59Z"
        print_status "Updated Python 3.15 milestone description"
    fi

    # Update v1.0.0 Stable milestone (PRIMARY FOCUS)
    V100_MILESTONE=$(gh api repos/QriusGlobal/injx/milestones --jq '.[] | select(.title == "v1.0.0 Stable") | .number')
    if [ -n "$V100_MILESTONE" ]; then
        gh api repos/QriusGlobal/injx/milestones/"$V100_MILESTONE" --method PATCH \
            -f description="🎯 PRIMARY FOCUS: Achieve production-ready stability
• Fix ALL known bugs
• Comprehensive test coverage
• Performance optimization
• Documentation completeness
• Zero regression policy
Target Release: v1.0.0"
        print_status "Updated v1.0.0 Stable milestone description (PRIMARY FOCUS)"
    fi
}

# Main menu
case "${1:-help}" in
    list)
        list_milestones
        ;;
    assign)
        auto_assign_issues
        ;;
    progress)
        show_progress
        ;;
    update)
        update_python_milestones
        ;;
    all)
        list_milestones
        echo ""
        auto_assign_issues
        echo ""
        show_progress
        ;;
    help|--help|-h)
        echo "🎯 Milestone Management Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  list      - List all milestones and their status"
        echo "  assign    - Auto-assign issues to milestones based on labels"
        echo "  progress  - Show detailed progress for each milestone"
        echo "  update    - Update milestone descriptions with latest info"
        echo "  all       - Run all commands (list, assign, progress)"
        echo "  help      - Show this help message"
        echo ""
        echo "Label → Milestone Mapping:"
        echo "  python-3.14 → Python 3.14 Compatibility"
        echo "  python-3.15 → Python 3.15 Planning"
        echo "  bug (without Python labels) → Python 3.13 Stable"
        echo "  enhancement (without Python labels) → v0.3.0"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac