#!/bin/bash
# branch_audit.sh - Check which files from a source exist on target branches
#
# Usage:
#   branch_audit.sh --pr <pr-url> --branches <branch1,branch2,...> [--json] [--deep]
#   branch_audit.sh --commit <sha> --branches <branch1,branch2,...> [--json] [--deep]
#   branch_audit.sh --files <file-list.txt> --branches <branch1,branch2,...> [--json] [--deep]
#
# Requires: git, python3 (for PR mode with git_pr_reader.py)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$(dirname "$(dirname "$SKILL_DIR")")"
GIT_REVIEW_API="${PLUGIN_DIR}/skills/git-pr-reader/scripts/git_pr_reader.py"

# Defaults
PR_URL=""
COMMIT_SHA=""
FILE_LIST=""
BRANCHES=""
JSON_OUTPUT=false
DRY_RUN=false
DEEP=false

usage() {
    cat <<'USAGE'
Usage:
  branch_audit.sh --pr <pr-url> --branches <branch1,branch2,...> [--json]
  branch_audit.sh --commit <sha> --branches <branch1,branch2,...> [--json]
  branch_audit.sh --files <file-list.txt> --branches <branch1,branch2,...> [--json]

Options:
  --pr <url>            GitHub PR or GitLab MR URL
  --commit <sha>        Git commit SHA to get file list from
  --files <path>        Text file with one file path per line
  --branches <list>     Comma-separated list of target branches
  --json                Output results as JSON
  --deep                Run deep content comparison for included files
  --dry-run             Show what would be checked without fetching branches

Examples:
  branch_audit.sh --pr https://github.com/openshift/openshift-docs/pull/106280 \
    --branches enterprise-4.17,enterprise-4.16

  branch_audit.sh --commit abc123def --branches enterprise-4.17
USAGE
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr)       PR_URL="$2"; shift 2 ;;
        --commit)   COMMIT_SHA="$2"; shift 2 ;;
        --files)    FILE_LIST="$2"; shift 2 ;;
        --branches) BRANCHES="$2"; shift 2 ;;
        --json)     JSON_OUTPUT=true; shift ;;
        --deep)     DEEP=true; shift ;;
        --dry-run)  DRY_RUN=true; shift ;;
        -h|--help)  usage ;;
        *)          echo "ERROR: Unknown option: $1"; usage ;;
    esac
done

# Validate inputs
if [[ -z "$BRANCHES" ]]; then
    echo "ERROR: --branches is required"
    usage
fi

if [[ -z "$PR_URL" && -z "$COMMIT_SHA" && -z "$FILE_LIST" ]]; then
    echo "ERROR: One of --pr, --commit, or --files is required"
    usage
fi

# Temporary files
CANDIDATE_FILES=$(mktemp /tmp/branch-audit-candidates.XXXXXX)
REPORT_FILE=$(mktemp /tmp/branch-audit-report.XXXXXX)
trap 'rm -f "$CANDIDATE_FILES" "$REPORT_FILE"' EXIT

# Step 1: Build file list from source
echo "=== Building file list ===" >&2

if [[ -n "$PR_URL" ]]; then
    echo "Source: PR $PR_URL" >&2
    PR_FILES_OK=false

    # Try git_pr_reader.py first
    if [[ -f "$GIT_REVIEW_API" ]]; then
        if python3 "$GIT_REVIEW_API" files "$PR_URL" 2>/dev/null | grep '\.adoc$' > "$CANDIDATE_FILES" && [[ -s "$CANDIDATE_FILES" ]]; then
            PR_FILES_OK=true
        else
            echo "WARNING: git_pr_reader.py failed, trying gh CLI fallback..." >&2
        fi
    fi

    # Fallback to gh CLI
    # Unset GITHUB_TOKEN so gh uses keyring auth (an invalid GITHUB_TOKEN overrides valid keyring credentials)
    if [[ "$PR_FILES_OK" = false ]] && command -v gh >/dev/null 2>&1; then
        # Extract owner/repo and PR number from URL
        # Supports: https://github.com/owner/repo/pull/123
        PR_NUMBER=$(echo "$PR_URL" | grep -oP '/pull/\K[0-9]+')
        OWNER_REPO=$(echo "$PR_URL" | grep -oP 'github\.com/\K[^/]+/[^/]+')
        if [[ -n "$PR_NUMBER" && -n "$OWNER_REPO" ]]; then
            if GITHUB_TOKEN= GH_TOKEN= gh api "repos/${OWNER_REPO}/pulls/${PR_NUMBER}/files" --paginate --jq '.[].filename' 2>/dev/null | grep '\.adoc$' > "$CANDIDATE_FILES" && [[ -s "$CANDIDATE_FILES" ]]; then
                PR_FILES_OK=true
            else
                echo "WARNING: gh CLI also failed" >&2
            fi
        fi
    fi

    # Fallback to GitHub MCP tool file list extraction
    if [[ "$PR_FILES_OK" = false ]]; then
        echo "ERROR: Could not fetch PR file list. Check GITHUB_TOKEN or gh auth status." >&2
        exit 1
    fi

elif [[ -n "$COMMIT_SHA" ]]; then
    echo "Source: commit $COMMIT_SHA" >&2
    git diff-tree --no-commit-id --name-only -r "$COMMIT_SHA" | grep '\.adoc$' > "$CANDIDATE_FILES" || true

elif [[ -n "$FILE_LIST" ]]; then
    echo "Source: file list $FILE_LIST" >&2
    if [[ ! -f "$FILE_LIST" ]]; then
        echo "ERROR: File list not found: $FILE_LIST" >&2
        exit 1
    fi
    grep '\.adoc$' "$FILE_LIST" > "$CANDIDATE_FILES" || true
fi

TOTAL_FILES=$(wc -l < "$CANDIDATE_FILES")
if [[ "$TOTAL_FILES" -eq 0 ]]; then
    echo "ERROR: No .adoc files found from source" >&2
    exit 1
fi

echo "Found $TOTAL_FILES .adoc file(s) from source" >&2
echo "" >&2

# Step 2: Fetch remote branches if needed
if [[ "$DRY_RUN" = false ]]; then
    IFS=',' read -ra BRANCH_ARRAY <<< "$BRANCHES"
    for branch in "${BRANCH_ARRAY[@]}"; do
        branch=$(echo "$branch" | xargs)  # trim whitespace
        if ! git rev-parse --verify "remotes/upstream/$branch" >/dev/null 2>&1; then
            echo "Fetching upstream/$branch..." >&2
            git fetch upstream "$branch" 2>/dev/null || {
                echo "WARNING: Could not fetch upstream/$branch — trying origin/$branch" >&2
                git fetch origin "$branch" 2>/dev/null || {
                    echo "ERROR: Branch $branch not found on upstream or origin" >&2
                    continue
                }
            }
        fi
    done
fi

# Step 3: Check file existence on each branch
IFS=',' read -ra BRANCH_ARRAY <<< "$BRANCHES"

if [[ "$JSON_OUTPUT" = true ]]; then
    echo "{"
    echo "  \"source_files\": $TOTAL_FILES,"
    echo "  \"branches\": {"
fi

BRANCH_IDX=0
for branch in "${BRANCH_ARRAY[@]}"; do
    branch=$(echo "$branch" | xargs)  # trim whitespace
    BRANCH_IDX=$((BRANCH_IDX + 1))

    INCLUDE_FILES=()
    EXCLUDE_FILES=()

    # Determine the ref to check against
    REF=""
    if git rev-parse --verify "remotes/upstream/$branch" >/dev/null 2>&1; then
        REF="remotes/upstream/$branch"
    elif git rev-parse --verify "remotes/origin/$branch" >/dev/null 2>&1; then
        REF="remotes/origin/$branch"
    else
        echo "WARNING: Branch $branch not found, skipping" >&2
        continue
    fi

    while IFS= read -r filepath; do
        [[ -z "$filepath" ]] && continue
        filepath=$(echo "$filepath" | xargs)  # trim whitespace

        if git cat-file -e "${REF}:${filepath}" 2>/dev/null; then
            INCLUDE_FILES+=("$filepath")
        else
            EXCLUDE_FILES+=("$filepath")
        fi
    done < "$CANDIDATE_FILES"

    INCLUDE_COUNT=${#INCLUDE_FILES[@]}
    EXCLUDE_COUNT=${#EXCLUDE_FILES[@]}

    if [[ "$JSON_OUTPUT" = true ]]; then
        # JSON output
        [[ $BRANCH_IDX -gt 1 ]] && echo ","
        echo "    \"$branch\": {"
        echo "      \"include_count\": $INCLUDE_COUNT,"
        echo "      \"exclude_count\": $EXCLUDE_COUNT,"
        echo -n "      \"include\": ["
        for i in "${!INCLUDE_FILES[@]}"; do
            [[ $i -gt 0 ]] && echo -n ", "
            echo -n "\"${INCLUDE_FILES[$i]}\""
        done
        echo "],"
        echo -n "      \"exclude\": ["
        for i in "${!EXCLUDE_FILES[@]}"; do
            [[ $i -gt 0 ]] && echo -n ", "
            echo -n "\"${EXCLUDE_FILES[$i]}\""
        done
        echo "]"
        echo -n "    }"
    else
        # Text output
        echo "=== Branch Audit: $branch ==="
        echo ""
        echo "Include ($INCLUDE_COUNT files):"
        for f in "${INCLUDE_FILES[@]}"; do
            echo "  $f"
        done
        echo ""
        if [[ $EXCLUDE_COUNT -gt 0 ]]; then
            echo "Exclude ($EXCLUDE_COUNT files — not on branch):"
            for f in "${EXCLUDE_FILES[@]}"; do
                echo "  $f"
            done
        else
            echo "Exclude: none (all files exist on this branch)"
        fi
        echo ""
        echo "Summary: $INCLUDE_COUNT/$TOTAL_FILES files applicable to $branch"
        echo ""
    fi
done

if [[ "$JSON_OUTPUT" = true ]]; then
    echo ""
    echo "  }"
    echo "}"
fi

# Step 4: Deep content comparison (if --deep is set)
if [[ "$DEEP" = true && "$DRY_RUN" = false ]]; then
    echo "" >&2
    echo "Running deep content comparison..." >&2

    # Determine source ref (main or PR head)
    SOURCE_REF=""
    if git rev-parse --verify "remotes/upstream/main" >/dev/null 2>&1; then
        SOURCE_REF="remotes/upstream/main"
    elif git rev-parse --verify "remotes/origin/main" >/dev/null 2>&1; then
        SOURCE_REF="remotes/origin/main"
    fi

    if [[ -z "$SOURCE_REF" ]]; then
        echo "WARNING: Could not determine source ref for deep audit, skipping" >&2
    else
        IFS=',' read -ra BRANCH_ARRAY <<< "$BRANCHES"
        for branch in "${BRANCH_ARRAY[@]}"; do
            branch=$(echo "$branch" | xargs)

            # Determine target ref
            TARGET_REF=""
            if git rev-parse --verify "remotes/upstream/$branch" >/dev/null 2>&1; then
                TARGET_REF="remotes/upstream/$branch"
            elif git rev-parse --verify "remotes/origin/$branch" >/dev/null 2>&1; then
                TARGET_REF="remotes/origin/$branch"
            fi

            [[ -z "$TARGET_REF" ]] && continue

            # Build included files list for this branch
            INCLUDE_LIST=$(mktemp /tmp/deep-audit-include.XXXXXX)
            while IFS= read -r filepath; do
                [[ -z "$filepath" ]] && continue
                filepath=$(echo "$filepath" | xargs)
                if git cat-file -e "${TARGET_REF}:${filepath}" 2>/dev/null; then
                    echo "$filepath" >> "$INCLUDE_LIST"
                fi
            done < "$CANDIDATE_FILES"

            echo ""
            bash "${SCRIPT_DIR}/deep_audit.sh" \
                --source-ref "$SOURCE_REF" \
                --target-ref "$TARGET_REF" \
                --files "$INCLUDE_LIST" \
                --output-dir "/tmp/deep-audit-${branch}"

            rm -f "$INCLUDE_LIST"
        done
    fi
fi
