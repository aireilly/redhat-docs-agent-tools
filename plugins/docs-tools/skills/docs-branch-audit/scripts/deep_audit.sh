#!/bin/bash
# deep_audit.sh - Deep content comparison for cherry-pick applicability
#
# For each included file, compares the source (main) and target branch versions
# to determine if the PR's changes will apply cleanly and flag version-specific content.
#
# Usage:
#   deep_audit.sh --source-ref <ref> --target-ref <ref> --files <file-list.txt> [--pr-diff <diff-file>]
#
# Output: Per-file report with confidence level (high/medium/needs-review)

set -euo pipefail

# Defaults
SOURCE_REF=""
TARGET_REF=""
FILE_LIST=""
PR_DIFF=""
OUTPUT_DIR=""

usage() {
    cat <<'USAGE'
Usage:
  deep_audit.sh --source-ref <ref> --target-ref <ref> --files <file-list.txt> [--pr-diff <diff-file>]

Options:
  --source-ref <ref>    Git ref for the source branch (e.g., upstream/main, PR head SHA)
  --target-ref <ref>    Git ref for the target branch (e.g., upstream/enterprise-4.17)
  --files <path>        Text file with one included file path per line
  --pr-diff <path>      Optional: unified diff file from the PR for patch dry-run testing
  --output-dir <dir>    Output directory for per-file diffs (default: /tmp/deep-audit)

USAGE
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --source-ref)  SOURCE_REF="$2"; shift 2 ;;
        --target-ref)  TARGET_REF="$2"; shift 2 ;;
        --files)       FILE_LIST="$2"; shift 2 ;;
        --pr-diff)     PR_DIFF="$2"; shift 2 ;;
        --output-dir)  OUTPUT_DIR="$2"; shift 2 ;;
        -h|--help)     usage ;;
        *)             echo "ERROR: Unknown option: $1"; usage ;;
    esac
done

# Validate
if [[ -z "$SOURCE_REF" || -z "$TARGET_REF" || -z "$FILE_LIST" ]]; then
    echo "ERROR: --source-ref, --target-ref, and --files are all required"
    usage
fi

if [[ ! -f "$FILE_LIST" ]]; then
    echo "ERROR: File list not found: $FILE_LIST" >&2
    exit 1
fi

OUTPUT_DIR="${OUTPUT_DIR:-/tmp/deep-audit}"
mkdir -p "$OUTPUT_DIR"

# Counters
COUNT_HIGH=0
COUNT_MEDIUM=0
COUNT_REVIEW=0
TOTAL=0

echo "=== Deep Audit: $(basename "$TARGET_REF") ==="
echo ""
echo "Source: $SOURCE_REF"
echo "Target: $TARGET_REF"
echo ""

while IFS= read -r filepath; do
    [[ -z "$filepath" ]] && continue
    filepath=$(echo "$filepath" | xargs)
    TOTAL=$((TOTAL + 1))

    BASENAME=$(basename "$filepath" .adoc)
    CONFIDENCE="high"
    ISSUES=()

    # --- Check 1: Content diff between source and target branch versions ---
    # This shows what's different in the file between branches (independent of the PR)
    BRANCH_DIFF_FILE="${OUTPUT_DIR}/${BASENAME}.branch-diff"
    if git diff "${TARGET_REF}" "${SOURCE_REF}" -- "$filepath" > "$BRANCH_DIFF_FILE" 2>/dev/null; then
        BRANCH_DIFF_LINES=$(wc -l < "$BRANCH_DIFF_FILE")
        if [[ "$BRANCH_DIFF_LINES" -eq 0 ]]; then
            # Files are identical between branches — PR changes will apply cleanly
            ISSUES+=("files-identical: File is identical on both branches")
        elif [[ "$BRANCH_DIFF_LINES" -gt 200 ]]; then
            CONFIDENCE="needs-review"
            ISSUES+=("large-divergence: ${BRANCH_DIFF_LINES} lines differ between branches")
        elif [[ "$BRANCH_DIFF_LINES" -gt 50 ]]; then
            CONFIDENCE="medium"
            ISSUES+=("moderate-divergence: ${BRANCH_DIFF_LINES} lines differ between branches")
        else
            ISSUES+=("minor-divergence: ${BRANCH_DIFF_LINES} lines differ between branches")
        fi
    else
        CONFIDENCE="needs-review"
        ISSUES+=("diff-error: Could not diff file between branches")
    fi

    # --- Check 2: Version-specific conditional attributes ---
    # Look for ifdef/ifndef blocks in the target branch version that gate content by version
    TARGET_CONTENT_FILE="${OUTPUT_DIR}/${BASENAME}.target"
    git show "${TARGET_REF}:${filepath}" > "$TARGET_CONTENT_FILE" 2>/dev/null || true
    if [[ -s "$TARGET_CONTENT_FILE" ]]; then
        # Check for version conditionals
        VERSION_CONDITIONALS=$(grep -cE 'ifdef::|ifndef::|ifeval::' "$TARGET_CONTENT_FILE" 2>/dev/null || true)
        VERSION_CONDITIONALS=${VERSION_CONDITIONALS:-0}
        if [[ "$VERSION_CONDITIONALS" -gt 0 ]]; then
            if [[ "$CONFIDENCE" != "needs-review" ]]; then
                CONFIDENCE="medium"
            fi
            ISSUES+=("conditionals: ${VERSION_CONDITIONALS} conditional directive(s) found")
        fi

        # Check for version-specific attribute references like {product-version}
        VERSION_ATTRS=$(grep -cE '\{product-version\}|\{ocp-version\}' "$TARGET_CONTENT_FILE" 2>/dev/null || true)
        VERSION_ATTRS=${VERSION_ATTRS:-0}
        if [[ "$VERSION_ATTRS" -gt 0 ]]; then
            ISSUES+=("version-attrs: ${VERSION_ATTRS} version attribute reference(s)")
        fi
    fi

    # --- Check 3: Patch applicability (if PR diff provided) ---
    if [[ -n "$PR_DIFF" && -f "$PR_DIFF" ]]; then
        # Extract just this file's diff from the full PR diff
        FILE_PATCH="${OUTPUT_DIR}/${BASENAME}.patch"
        # Use awk to extract the diff hunk for this specific file
        awk -v file="$filepath" '
            /^diff --git/ { found = ($0 ~ "b/" file "$"); if (found) print; next }
            found { print }
            /^diff --git/ && !($0 ~ "b/" file "$") { found = 0 }
        ' "$PR_DIFF" > "$FILE_PATCH" 2>/dev/null || true

        if [[ -s "$FILE_PATCH" ]]; then
            # Try applying the patch in check mode against the target branch version
            if git apply --check --3way "$FILE_PATCH" 2>/dev/null; then
                ISSUES+=("patch: applies cleanly")
            else
                PATCH_ERRORS=$(git apply --check --3way "$FILE_PATCH" 2>&1 || true)
                if echo "$PATCH_ERRORS" | grep -q "conflict"; then
                    CONFIDENCE="needs-review"
                    ISSUES+=("patch-conflict: patch has conflicts")
                else
                    if [[ "$CONFIDENCE" != "needs-review" ]]; then
                        CONFIDENCE="medium"
                    fi
                    ISSUES+=("patch-mismatch: patch context does not match target")
                fi
            fi
        fi
    fi

    # --- Check 4: Structural differences ---
    # Compare section headings between source and target to detect structural changes
    SOURCE_HEADINGS=$(git show "${SOURCE_REF}:${filepath}" 2>/dev/null | grep -cE '^=+ ' || true)
    SOURCE_HEADINGS=${SOURCE_HEADINGS:-0}
    TARGET_HEADINGS=0
    if [[ -s "$TARGET_CONTENT_FILE" ]]; then
        TARGET_HEADINGS=$(grep -cE '^=+ ' "$TARGET_CONTENT_FILE" 2>/dev/null || true)
        TARGET_HEADINGS=${TARGET_HEADINGS:-0}
    fi
    if [[ "$SOURCE_HEADINGS" != "$TARGET_HEADINGS" ]]; then
        if [[ "$CONFIDENCE" != "needs-review" ]]; then
            CONFIDENCE="medium"
        fi
        ISSUES+=("structure: heading count differs (source: ${SOURCE_HEADINGS}, target: ${TARGET_HEADINGS})")
    fi

    # --- Output ---
    case "$CONFIDENCE" in
        high)         COUNT_HIGH=$((COUNT_HIGH + 1));   SYMBOL="[HIGH]" ;;
        medium)       COUNT_MEDIUM=$((COUNT_MEDIUM + 1)); SYMBOL="[MEDIUM]" ;;
        needs-review) COUNT_REVIEW=$((COUNT_REVIEW + 1)); SYMBOL="[NEEDS-REVIEW]" ;;
    esac

    echo "$SYMBOL $filepath"
    for issue in "${ISSUES[@]}"; do
        echo "    $issue"
    done
    echo ""

done < "$FILE_LIST"

# --- Summary ---
echo "=== Deep Audit Summary ==="
echo ""
echo "  Total files:  $TOTAL"
echo "  High:         $COUNT_HIGH (changes will apply cleanly)"
echo "  Medium:       $COUNT_MEDIUM (likely applies, review recommended)"
echo "  Needs review: $COUNT_REVIEW (conflicts or large divergence expected)"
echo ""
echo "Per-file diffs saved to: $OUTPUT_DIR"
