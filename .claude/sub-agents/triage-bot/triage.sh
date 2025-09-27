#!/usr/bin/env bash

# Claude Code Sub-Agent for Issue Triage
# This agent provides sophisticated triage logic with confidence scoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO="QriusGlobal/injx"
MIN_CONFIDENCE_FOR_AUTO=90
MIN_CONFIDENCE_FOR_SUGGEST=75

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to analyze issue content
analyze_issue() {
    local issue_number="$1"
    local issue_data=$(gh issue view "$issue_number" --repo "$REPO" --json title,body,labels,author,createdAt,comments)

    local title=$(echo "$issue_data" | jq -r '.title')
    local body=$(echo "$issue_data" | jq -r '.body // ""')
    local current_labels=$(echo "$issue_data" | jq -r '.labels[].name' | tr '\n' ',' | sed 's/,$//')
    local author=$(echo "$issue_data" | jq -r '.author.login')

    echo "{"
    echo "  \"number\": $issue_number,"
    echo "  \"title\": $(echo "$title" | jq -R .),"
    echo "  \"body\": $(echo "$body" | jq -R .),"
    echo "  \"current_labels\": \"$current_labels\","
    echo "  \"author\": \"$author\""
    echo "}"
}

# Function to categorize issue
categorize_issue() {
    local title="$1"
    local body="$2"
    local content=$(echo "$title $body" | tr '[:upper:]' '[:lower:]')

    local category=""
    local confidence=0

    # Bug detection patterns
    if [[ "$content" =~ (bug|error|crash|fail|broken|exception|traceback|segfault) ]]; then
        category="bug"
        confidence=85
        # Increase confidence for specific error patterns
        if [[ "$content" =~ (traceback|exception|error:|failed to) ]]; then
            confidence=95
        fi
    # Enhancement detection
    elif [[ "$content" =~ (feature|enhancement|request|add support|would be nice|suggestion) ]]; then
        category="enhancement"
        confidence=90
    # Question detection
    elif [[ "$content" =~ (how to|how do|what is|why does|can i|help|confused|\?) ]]; then
        category="question"
        confidence=85
    # Documentation detection
    elif [[ "$content" =~ (docs|documentation|readme|example|typo|clarify) ]]; then
        category="documentation"
        confidence=90
    else
        category="needs-triage"
        confidence=50
    fi

    echo "{\"category\": \"$category\", \"confidence\": $confidence}"
}

# Function to assess priority
assess_priority() {
    local title="$1"
    local body="$2"
    local category="$3"
    local content=$(echo "$title $body" | tr '[:upper:]' '[:lower:]')

    local priority="medium"
    local confidence=75

    # Critical indicators
    if [[ "$content" =~ (crash|segfault|data loss|security|memory leak|production down) ]]; then
        priority="critical"
        confidence=95
    # High priority indicators
    elif [[ "$content" =~ (broken|doesn't work|blocking|regression|performance degradation) ]]; then
        priority="high"
        confidence=85
    # Low priority indicators
    elif [[ "$content" =~ (nice to have|minor|trivial|cosmetic|typo) ]] || [[ "$category" == "enhancement" ]]; then
        priority="low"
        confidence=80
    fi

    # Bugs default to medium-high priority
    if [[ "$category" == "bug" ]] && [[ "$priority" == "medium" ]]; then
        priority="high"
        confidence=70
    fi

    echo "{\"priority\": \"$priority\", \"confidence\": $confidence}"
}

# Function to detect duplicates
detect_duplicates() {
    local title="$1"
    local issue_number="$2"

    # Extract key terms from title
    local search_terms=$(echo "$title" | sed 's/[^a-zA-Z0-9 ]//g' | tr '[:upper:]' '[:lower:]' | head -3)

    log_info "Searching for duplicates with terms: $search_terms"

    local similar_issues=$(gh search issues --repo "$REPO" "$search_terms" --limit 10 --json number,title,state 2>/dev/null || echo "[]")

    local duplicates="[]"
    if [ "$similar_issues" != "[]" ]; then
        duplicates=$(echo "$similar_issues" | jq "[.[] | select(.number != $issue_number)]")
    fi

    echo "$duplicates"
}

# Function to recommend labels
recommend_labels() {
    local title="$1"
    local body="$2"
    local category="$3"
    local priority="$4"
    local content=$(echo "$title $body" | tr '[:upper:]' '[:lower:]')

    local labels=("$category")

    # Add priority-based labels for bugs
    if [[ "$category" == "bug" ]] && [[ "$priority" == "critical" ]]; then
        labels+=("urgent")
    fi

    # Python version detection
    if [[ "$content" =~ python\ 3\.14|py3\.14|py314 ]]; then
        labels+=("python-3.14")
    fi
    if [[ "$content" =~ python\ 3\.15|py3\.15|py315 ]]; then
        labels+=("python-3.15")
    fi

    # Good first issue detection
    if [[ "$content" =~ (easy|simple|beginner|good first|straightforward|trivial) ]]; then
        labels+=("good-first-issue")
    fi

    # Performance related
    if [[ "$content" =~ (slow|performance|speed|optimize|benchmark) ]]; then
        labels+=("performance")
    fi

    # Output as JSON array
    echo -n "["
    local first=true
    for label in "${labels[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            echo -n ","
        fi
        echo -n "\"$label\""
    done
    echo "]"
}

# Function to assign milestone
assign_milestone() {
    local category="$1"
    local labels="$2"

    local milestone=""

    # Check for Python version labels first
    if [[ "$labels" =~ python-3.14 ]]; then
        milestone="Python 3.14 Compatibility"
    elif [[ "$labels" =~ python-3.15 ]]; then
        milestone="Python 3.15 Planning"
    elif [[ "$category" == "bug" ]]; then
        milestone="v1.0.0 Stable"
    elif [[ "$category" == "enhancement" ]]; then
        milestone="Enhancements (Future)"
    fi

    echo "$milestone"
}

# Function to calculate overall confidence
calculate_confidence() {
    local cat_confidence="$1"
    local priority_confidence="$2"
    local has_duplicates="$3"

    # Weight the different confidence scores
    local clarity_score=$((cat_confidence * 30 / 100))
    local priority_score=$((priority_confidence * 30 / 100))

    # Pattern matching bonus
    local pattern_score=20
    if [ "$cat_confidence" -lt 70 ]; then
        pattern_score=10
    fi

    # Duplicate detection score
    local duplicate_score=10
    if [ "$has_duplicates" = "true" ]; then
        duplicate_score=15
    fi

    # Context understanding
    local context_score=15
    if [ "$cat_confidence" -gt 85 ] && [ "$priority_confidence" -gt 80 ]; then
        context_score=20
    fi

    local total=$((clarity_score + priority_score + pattern_score + duplicate_score + context_score))

    echo "$total"
}

# Main triage function
triage_issue() {
    local issue_number="$1"

    log_info "Starting triage for issue #$issue_number"

    # Fetch issue data
    local issue_json=$(analyze_issue "$issue_number")
    local title=$(echo "$issue_json" | jq -r '.title')
    local body=$(echo "$issue_json" | jq -r '.body')
    local current_labels=$(echo "$issue_json" | jq -r '.current_labels')

    # Categorize issue
    local cat_result=$(categorize_issue "$title" "$body")
    local category=$(echo "$cat_result" | jq -r '.category')
    local cat_confidence=$(echo "$cat_result" | jq -r '.confidence')

    log_info "Category: $category (confidence: $cat_confidence%)"

    # Assess priority
    local priority_result=$(assess_priority "$title" "$body" "$category")
    local priority=$(echo "$priority_result" | jq -r '.priority')
    local priority_confidence=$(echo "$priority_result" | jq -r '.confidence')

    log_info "Priority: $priority (confidence: $priority_confidence%)"

    # Detect duplicates
    local duplicates=$(detect_duplicates "$title" "$issue_number")
    local has_duplicates="false"
    if [ "$(echo "$duplicates" | jq '. | length')" -gt 0 ]; then
        has_duplicates="true"
        log_warning "Found potential duplicates"
    fi

    # Recommend labels
    local recommended_labels=$(recommend_labels "$title" "$body" "$category" "$priority")
    log_info "Recommended labels: $recommended_labels"

    # Assign milestone
    local milestone=$(assign_milestone "$category" "$recommended_labels")
    if [ -n "$milestone" ]; then
        log_info "Suggested milestone: $milestone"
    fi

    # Calculate overall confidence
    local confidence=$(calculate_confidence "$cat_confidence" "$priority_confidence" "$has_duplicates")
    log_info "Overall confidence: $confidence%"

    # Build triage result
    cat <<EOF
{
  "issue_number": $issue_number,
  "category": "$category",
  "priority": "$priority",
  "labels_to_add": $recommended_labels,
  "labels_to_remove": [],
  "milestone": $([ -n "$milestone" ] && echo "\"$milestone\"" || echo "null"),
  "potential_duplicates": $duplicates,
  "confidence_score": $confidence,
  "confidence_breakdown": {
    "categorization": $cat_confidence,
    "priority": $priority_confidence,
    "has_duplicates": $has_duplicates
  },
  "reasoning": "Issue categorized as $category based on content analysis. Priority set to $priority based on severity indicators. Confidence: $confidence%",
  "needs_human_review": $([ "$confidence" -lt "$MIN_CONFIDENCE_FOR_AUTO" ] && echo "true" || echo "false")
}
EOF
}

# Function to apply triage
apply_triage() {
    local triage_json="$1"
    local dry_run="${2:-false}"

    local issue_number=$(echo "$triage_json" | jq -r '.issue_number')
    local labels_to_add=$(echo "$triage_json" | jq -r '.labels_to_add[]' | tr '\n' ',')
    local milestone=$(echo "$triage_json" | jq -r '.milestone // empty')
    local confidence=$(echo "$triage_json" | jq -r '.confidence_score')

    if [ "$confidence" -lt "$MIN_CONFIDENCE_FOR_AUTO" ]; then
        log_warning "Confidence too low ($confidence%) for automatic application"
        return 1
    fi

    if [ "$dry_run" = "true" ]; then
        log_info "DRY RUN - Would apply:"
        log_info "  Labels: $labels_to_add"
        [ -n "$milestone" ] && log_info "  Milestone: $milestone"
    else
        # Apply labels
        if [ -n "$labels_to_add" ]; then
            gh issue edit "$issue_number" --repo "$REPO" --add-label "$labels_to_add"
            log_success "Applied labels: $labels_to_add"
        fi

        # Apply milestone
        if [ -n "$milestone" ]; then
            gh issue edit "$issue_number" --repo "$REPO" --milestone "$milestone"
            log_success "Set milestone: $milestone"
        fi
    fi
}

# Main command handling
case "${1:-help}" in
    triage)
        if [ -z "$2" ]; then
            log_error "Issue number required"
            exit 1
        fi
        triage_issue "$2"
        ;;

    apply)
        if [ -z "$2" ]; then
            log_error "Triage JSON required"
            exit 1
        fi
        apply_triage "$2" "${3:-false}"
        ;;

    batch)
        # Triage all needs-triage issues
        log_info "Batch triaging all needs-triage issues..."
        issues=$(gh issue list --repo "$REPO" --label "needs-triage" --json number --jq '.[].number')
        for issue in $issues; do
            log_info "Processing issue #$issue"
            triage_json=$(triage_issue "$issue")
            confidence=$(echo "$triage_json" | jq -r '.confidence_score')
            if [ "$confidence" -ge "$MIN_CONFIDENCE_FOR_AUTO" ]; then
                log_success "High confidence triage for #$issue"
                echo "$triage_json"
            else
                log_warning "Low confidence for #$issue, skipping"
            fi
            echo "---"
        done
        ;;

    help|--help|-h)
        echo "Claude Code Triage Bot Sub-Agent"
        echo ""
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  triage <issue_number>    - Analyze and triage an issue"
        echo "  apply <json> [dry_run]   - Apply triage decisions"
        echo "  batch                    - Triage all needs-triage issues"
        echo "  help                     - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 triage 123"
        echo "  $0 apply '{...}' true    # Dry run"
        echo "  $0 batch"
        ;;

    *)
        log_error "Unknown command: $1"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac