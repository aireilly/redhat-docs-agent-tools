#!/bin/bash
# cherry_pick.sh - Deterministic cherry-pick backport operations
#
# Handles: PR info fetching, branch audit, cherry-pick execution, push, PR description.
# Conflict RESOLUTION is delegated back to Claude (the caller) — this script only
# identifies conflicts and reports them.
#
# Usage:
#   cherry_pick.sh --pr <url> --target <branches> [options]
#   cherry_pick.sh --commit <sha> --target <branches> [options]
#
# Phases:
#   validate   - Check inputs, fetch PR info, resolve commit SHA
#   audit      - Run branch audit, detect path differences
#   apply      - Create branch, cherry-pick, report conflicts
#   push       - Push branch, generate PR description
#
# Exit codes:
#   0  - Success (or dry-run completed)
#   1  - Error (missing inputs, bad state)
#   2  - Cherry-pick has conflicts (caller should resolve, then re-run with --phase push)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$(dirname "$(dirname "$SKILL_DIR")")"
BRANCH_AUDIT="${PLUGIN_DIR}/skills/docs-branch-audit/scripts/branch_audit.sh"
GIT_PR_READER="${PLUGIN_DIR}/skills/git-pr-reader/scripts/git_pr_reader.py"

# State directory for intermediate files
STATE_DIR="/tmp/cherry-pick-state"

# Defaults
PR_URL=""
COMMIT_SHA=""
TARGET_BRANCHES=""
DRY_RUN=false
DEEP=false
NO_PUSH=false
TICKET=""
PHASE=""  # empty = full run, or: validate, audit, apply, push

usage() {
    cat <<'USAGE'
Usage:
  cherry_pick.sh --pr <url> --target <branches> [options]
  cherry_pick.sh --commit <sha> --target <branches> [options]

Options:
  --pr <url>            GitHub PR or GitLab MR URL
  --commit <sha>        Git commit SHA
  --target <branches>   Comma-separated target branches (required)
  --dry-run             Audit only, no changes
  --deep                Deep content comparison
  --no-push             Don't push, just create local branch
  --ticket <id>         JIRA ticket ID (auto-detected from PR title if omitted)
  --phase <phase>       Run a single phase: validate, audit, apply, push

Output:
  Writes structured JSON/text to /tmp/cherry-pick-state/ for each phase.
  The caller reads these files to drive the workflow.
USAGE
    exit 1
}

# --- Argument parsing ---

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr)       PR_URL="$2"; shift 2 ;;
        --commit)   COMMIT_SHA="$2"; shift 2 ;;
        --target)   TARGET_BRANCHES="$2"; shift 2 ;;
        --dry-run)  DRY_RUN=true; shift ;;
        --deep)     DEEP=true; shift ;;
        --no-push)  NO_PUSH=true; shift ;;
        --ticket)   TICKET="$2"; shift 2 ;;
        --phase)    PHASE="$2"; shift 2 ;;
        -h|--help)  usage ;;
        *)
            # Treat bare URL-like args as PR URL
            if [[ "$1" == http* && -z "$PR_URL" ]]; then
                PR_URL="$1"; shift
            else
                echo "ERROR: Unknown option: $1" >&2; usage
            fi
            ;;
    esac
done

if [[ -z "$TARGET_BRANCHES" ]]; then
    echo "ERROR: --target is required" >&2
    usage
fi

if [[ -z "$PR_URL" && -z "$COMMIT_SHA" ]]; then
    echo "ERROR: --pr or --commit is required" >&2
    usage
fi

# Ensure state directory exists
mkdir -p "$STATE_DIR"

# --- Helper functions ---

detect_platform() {
    if echo "$PR_URL" | grep -q "github.com"; then
        echo "github"
    elif echo "$PR_URL" | grep -q "gitlab"; then
        echo "gitlab"
    else
        echo "unknown"
    fi
}

fetch_pr_info_gh() {
    local pr_url="$1"
    local pr_number owner_repo

    pr_number=$(echo "$pr_url" | grep -oP '/pull/\K[0-9]+' || echo "")
    owner_repo=$(echo "$pr_url" | grep -oP 'github\.com/\K[^/]+/[^/]+' || echo "")

    if [[ -z "$pr_number" || -z "$owner_repo" ]]; then
        echo "ERROR: Could not parse PR URL: $pr_url" >&2
        return 1
    fi

    # Try gh CLI (unset tokens to use keyring auth)
    if command -v gh >/dev/null 2>&1; then
        GITHUB_TOKEN= GH_TOKEN= gh api "repos/${owner_repo}/pulls/${pr_number}" 2>/dev/null && return 0
    fi

    # Fallback to git_pr_reader.py
    if [[ -f "$GIT_PR_READER" ]]; then
        python3 "$GIT_PR_READER" info "$pr_url" --json 2>/dev/null && return 0
    fi

    echo "ERROR: Could not fetch PR info. Check gh auth or GITHUB_TOKEN." >&2
    return 1
}

fetch_pr_files_gh() {
    local pr_url="$1"
    local pr_number owner_repo

    pr_number=$(echo "$pr_url" | grep -oP '/pull/\K[0-9]+' || echo "")
    owner_repo=$(echo "$pr_url" | grep -oP 'github\.com/\K[^/]+/[^/]+' || echo "")

    # Try gh CLI first
    if command -v gh >/dev/null 2>&1; then
        if GITHUB_TOKEN= GH_TOKEN= gh api "repos/${owner_repo}/pulls/${pr_number}/files" --paginate --jq '.[].filename' 2>/dev/null; then
            return 0
        fi
    fi

    # Fallback to git_pr_reader.py
    if [[ -f "$GIT_PR_READER" ]]; then
        if python3 "$GIT_PR_READER" files "$pr_url" 2>/dev/null; then
            return 0
        fi
    fi

    echo "ERROR: Could not fetch PR files." >&2
    return 1
}

# --- Phase: Validate ---

phase_validate() {
    echo "=== Phase: Validate ===" >&2

    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
        echo "ERROR: Not in a git repo" >&2; exit 1
    }

    if [[ -n "$PR_URL" ]]; then
        local platform
        platform=$(detect_platform)
        echo "Platform: $platform" >&2
        echo "PR URL: $PR_URL" >&2

        # Fetch PR info
        echo "Fetching PR info..." >&2
        fetch_pr_info_gh "$PR_URL" > "$STATE_DIR/pr-info.json"

        # Extract ticket from title if not provided
        if [[ -z "$TICKET" ]]; then
            TICKET=$(python3 -c "import json,re,sys; d=json.load(open('$STATE_DIR/pr-info.json')); m=re.match(r'^([A-Z]+-[0-9]+)', d.get('title','')); print(m.group(1) if m else '')" 2>/dev/null || echo "")
        fi

        # Determine PR state and commit SHA
        local pr_state pr_merged merge_sha head_sha
        pr_state=$(python3 -c "import json; print(json.load(open('$STATE_DIR/pr-info.json')).get('state',''))" 2>/dev/null || echo "")
        pr_merged=$(python3 -c "import json; d=json.load(open('$STATE_DIR/pr-info.json')); print('true' if d.get('merged') or d.get('merged_at') or d.get('mergedAt') else 'false')" 2>/dev/null || echo "false")
        merge_sha=$(python3 -c "import json; d=json.load(open('$STATE_DIR/pr-info.json')); print(d.get('merge_commit_sha') or d.get('mergeCommit',{}).get('oid','') if isinstance(d.get('mergeCommit'),dict) else d.get('merge_commit_sha',''))" 2>/dev/null || echo "")
        head_sha=$(python3 -c "import json; d=json.load(open('$STATE_DIR/pr-info.json')); h=d.get('head',{}); print(h.get('sha','') or h.get('oid',''))" 2>/dev/null || echo "")

        if [[ "$pr_merged" == "true" ]]; then
            COMMIT_SHA="$merge_sha"
            echo "PR merged. Using merge commit: $COMMIT_SHA" >&2
        elif [[ "$pr_state" == "open" || "$pr_state" == "OPEN" ]]; then
            local pr_number
            pr_number=$(echo "$PR_URL" | grep -oP '\d+$')
            if [[ "$platform" == "github" ]]; then
                echo "PR is open. Fetching PR head ref..." >&2
                git fetch upstream "pull/${pr_number}/head:pr-${pr_number}" 2>&1 >&2 || true
                COMMIT_SHA=$(git rev-parse "pr-${pr_number}" 2>/dev/null || echo "$head_sha")
            elif [[ "$platform" == "gitlab" ]]; then
                git fetch upstream "merge-requests/${pr_number}/head:mr-${pr_number}" 2>&1 >&2 || true
                COMMIT_SHA=$(git rev-parse "mr-${pr_number}" 2>/dev/null || echo "$head_sha")
            fi
            echo "WARNING: PR is not merged. Using head commit: $COMMIT_SHA" >&2
        else
            echo "ERROR: PR is closed without being merged. Cannot cherry-pick." >&2
            exit 1
        fi

        # Fetch file list
        echo "Fetching changed files..." >&2
        fetch_pr_files_gh "$PR_URL" > "$STATE_DIR/source-files.txt"

    else
        # Commit mode
        if ! git cat-file -e "$COMMIT_SHA" 2>/dev/null; then
            echo "ERROR: Commit $COMMIT_SHA not found. Try 'git fetch upstream' first." >&2
            exit 1
        fi
        git diff-tree --no-commit-id --name-only -r "$COMMIT_SHA" > "$STATE_DIR/source-files.txt"
    fi

    # Save state
    echo "$COMMIT_SHA" > "$STATE_DIR/commit-sha.txt"
    echo "$TICKET" > "$STATE_DIR/ticket.txt"
    echo "$TARGET_BRANCHES" > "$STATE_DIR/target-branches.txt"

    local file_count
    file_count=$(wc -l < "$STATE_DIR/source-files.txt")
    echo "Found $file_count changed file(s)" >&2
    echo "Ticket: ${TICKET:-<none>}" >&2
    echo "Commit SHA: $COMMIT_SHA" >&2

    # Write validate summary as JSON
    python3 -c "
import json
info = {}
try:
    info = json.load(open('$STATE_DIR/pr-info.json'))
except: pass
summary = {
    'commit_sha': '$COMMIT_SHA',
    'ticket': '$TICKET',
    'pr_title': info.get('title', ''),
    'pr_state': info.get('state', ''),
    'file_count': $file_count,
    'target_branches': '$TARGET_BRANCHES'.split(','),
    'source': '${PR_URL:-commit:$COMMIT_SHA}'
}
json.dump(summary, open('$STATE_DIR/validate-summary.json', 'w'), indent=2)
print(json.dumps(summary, indent=2))
"
}

# --- Phase: Audit ---

phase_audit() {
    echo "=== Phase: Audit ===" >&2

    local commit_sha target_branches
    commit_sha=$(cat "$STATE_DIR/commit-sha.txt" 2>/dev/null || echo "$COMMIT_SHA")
    target_branches=$(cat "$STATE_DIR/target-branches.txt" 2>/dev/null || echo "$TARGET_BRANCHES")

    # Determine audit source flag
    local audit_source_flag=""
    if [[ -n "$PR_URL" ]]; then
        audit_source_flag="--pr $PR_URL"
    elif [[ -n "$commit_sha" ]]; then
        audit_source_flag="--commit $commit_sha"
    else
        audit_source_flag="--files $STATE_DIR/source-files.txt"
    fi

    # Run branch audit (text output)
    echo "" >&2
    bash "$BRANCH_AUDIT" $audit_source_flag --branches "$target_branches" \
        2>&1 | tee "$STATE_DIR/audit-text.txt"

    # Run branch audit (JSON output)
    bash "$BRANCH_AUDIT" $audit_source_flag --branches "$target_branches" \
        --json > "$STATE_DIR/audit.json" 2>/dev/null || true

    # Detect assembly path differences
    echo "" >&2
    echo "=== Assembly Path Analysis ===" >&2

    local path_diffs_found=false
    IFS=',' read -ra BRANCH_ARRAY <<< "$target_branches"
    > "$STATE_DIR/path-diffs.txt"  # clear

    for branch in "${BRANCH_ARRAY[@]}"; do
        branch=$(echo "$branch" | xargs)
        local ref=""
        if git rev-parse --verify "remotes/upstream/$branch" >/dev/null 2>&1; then
            ref="remotes/upstream/$branch"
        elif git rev-parse --verify "remotes/origin/$branch" >/dev/null 2>&1; then
            ref="remotes/origin/$branch"
        else
            continue
        fi

        while IFS= read -r filepath; do
            [[ -z "$filepath" ]] && continue
            filepath=$(echo "$filepath" | xargs)
            # Skip modules (they don't move) and non-assembly files
            [[ "$filepath" == modules/* ]] && continue

            if ! git cat-file -e "${ref}:${filepath}" 2>/dev/null; then
                local basename alt_path
                basename=$(basename "$filepath")
                alt_path=$(git ls-tree -r --name-only "$ref" | grep "/${basename}$" | head -1 || echo "")
                if [[ -n "$alt_path" ]]; then
                    echo "PATH DIFFERENCE: $filepath -> $alt_path on $branch" | tee -a "$STATE_DIR/path-diffs.txt"
                    path_diffs_found=true
                fi
            fi
        done < "$STATE_DIR/source-files.txt"
    done

    if [[ "$path_diffs_found" = false ]]; then
        echo "No path differences detected" >&2
    fi

    # Deep audit if requested
    if [[ "$DEEP" = true ]]; then
        echo "" >&2
        echo "Running deep content comparison..." >&2
        if [[ -n "$PR_URL" ]]; then
            bash "$BRANCH_AUDIT" --pr "$PR_URL" --branches "$target_branches" --deep \
                2>&1 | tee "$STATE_DIR/deep-audit.txt"
        else
            bash "$BRANCH_AUDIT" --commit "$commit_sha" --branches "$target_branches" --deep \
                2>&1 | tee "$STATE_DIR/deep-audit.txt"
        fi
    fi

    # If dry-run, print summary and exit
    if [[ "$DRY_RUN" = true ]]; then
        echo "" >&2
        echo "=== DRY RUN COMPLETE ===" >&2
        echo "No changes made. Review the audit output above." >&2
        exit 0
    fi
}

# --- Phase: Apply ---

phase_apply() {
    local target_branch="$1"
    echo "=== Phase: Apply ($target_branch) ===" >&2

    local commit_sha ticket
    commit_sha=$(cat "$STATE_DIR/commit-sha.txt")
    ticket=$(cat "$STATE_DIR/ticket.txt" 2>/dev/null || echo "")

    local branch_name="${ticket:-cherry-pick}-${target_branch##*-}-CP"

    # Fetch target branch
    git fetch upstream "$target_branch" 2>&1 >&2

    # Save original branch to return to later
    git rev-parse --abbrev-ref HEAD > "$STATE_DIR/original-branch.txt" 2>/dev/null || echo "main" > "$STATE_DIR/original-branch.txt"

    # Create backport branch
    git checkout -b "$branch_name" "upstream/$target_branch" 2>&1 >&2
    echo "Created branch: $branch_name from upstream/$target_branch" >&2

    # Get excluded files from audit JSON
    local exclude_files=()
    if [[ -f "$STATE_DIR/audit.json" ]]; then
        mapfile -t exclude_files < <(python3 -c "
import json
d = json.load(open('$STATE_DIR/audit.json'))
branch_data = d.get('branches', {}).get('$target_branch', {})
for f in branch_data.get('exclude', []):
    print(f)
" 2>/dev/null || true)
    fi

    # Attempt cherry-pick
    echo "Cherry-picking commit $commit_sha..." >&2
    local cp_exit=0
    git cherry-pick --no-commit "$commit_sha" 2>"$STATE_DIR/cherry-pick-stderr.txt" || cp_exit=$?

    # Remove excluded files regardless of cherry-pick result
    for excluded_file in "${exclude_files[@]}"; do
        git checkout HEAD -- "$excluded_file" 2>/dev/null || git rm --cached "$excluded_file" 2>/dev/null || true
    done

    # Save branch info
    echo "$branch_name" > "$STATE_DIR/branch-name.txt"
    echo "$target_branch" > "$STATE_DIR/current-target.txt"
    echo "${#exclude_files[@]}" > "$STATE_DIR/exclude-count.txt"
    printf '%s\n' "${exclude_files[@]}" > "$STATE_DIR/exclude-files.txt" 2>/dev/null || true

    if [[ $cp_exit -eq 0 ]]; then
        echo "Cherry-pick applied cleanly" >&2
        echo "clean" > "$STATE_DIR/cherry-pick-status.txt"
        echo "" > "$STATE_DIR/conflicted-files.txt"

        # Get included file count
        local include_count
        if [[ -f "$STATE_DIR/audit.json" ]]; then
            include_count=$(python3 -c "
import json
d = json.load(open('$STATE_DIR/audit.json'))
print(d.get('branches', {}).get('$target_branch', {}).get('include_count', 0))
" 2>/dev/null || echo "0")
        else
            include_count=$(wc -l < "$STATE_DIR/source-files.txt")
        fi

        # Auto-commit for clean cherry-picks
        local source
        source=$(cat "$STATE_DIR/validate-summary.json" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('source',''))" 2>/dev/null || echo "")

        git add -A
        git commit -m "$(cat <<EOF
${ticket}: Backport to ${target_branch}

Backport of ${source} to ${target_branch}.

${include_count} files included, ${#exclude_files[@]} files excluded.

$(if [[ ${#exclude_files[@]} -gt 0 ]]; then
echo "Excluded (not present on ${target_branch}):"
for f in "${exclude_files[@]}"; do echo "- $(basename "$f" .adoc)"; done
fi)

Co-Authored-By: Claude <model> <noreply@anthropic.com>
EOF
)" 2>&1 >&2

        echo "Committed changes" >&2
    else
        echo "conflicts" > "$STATE_DIR/cherry-pick-status.txt"

        # List conflicted files
        git diff --name-only --diff-filter=U > "$STATE_DIR/conflicted-files.txt" 2>/dev/null || true

        local conflict_count
        conflict_count=$(wc -l < "$STATE_DIR/conflicted-files.txt")
        echo "Cherry-pick has $conflict_count conflicted file(s):" >&2
        cat "$STATE_DIR/conflicted-files.txt" >&2
        echo "" >&2
        echo "ACTION REQUIRED: Resolve conflicts, then re-run with --phase push" >&2
        exit 2
    fi
}

# --- Phase: Push ---

phase_push() {
    echo "=== Phase: Push ===" >&2

    local branch_name target_branch ticket source
    branch_name=$(cat "$STATE_DIR/branch-name.txt")
    target_branch=$(cat "$STATE_DIR/current-target.txt")
    ticket=$(cat "$STATE_DIR/ticket.txt" 2>/dev/null || echo "")
    source=$(python3 -c "import json,sys; print(json.load(open('$STATE_DIR/validate-summary.json')).get('source',''))" 2>/dev/null || echo "")

    local exclude_count include_count source_file_count
    exclude_count=$(cat "$STATE_DIR/exclude-count.txt" 2>/dev/null || echo "0")

    if [[ -f "$STATE_DIR/audit.json" ]]; then
        include_count=$(python3 -c "
import json
d = json.load(open('$STATE_DIR/audit.json'))
print(d.get('branches', {}).get('$target_branch', {}).get('include_count', 0))
" 2>/dev/null || echo "0")
    else
        include_count=$(wc -l < "$STATE_DIR/source-files.txt")
    fi
    source_file_count=$(wc -l < "$STATE_DIR/source-files.txt")

    # Diff stats comparison
    local backport_stats
    backport_stats=$(git diff --stat "upstream/${target_branch}...HEAD" 2>/dev/null || echo "")
    local backport_file_count backport_insertions backport_deletions
    backport_file_count=$(git diff --numstat "upstream/${target_branch}...HEAD" 2>/dev/null | wc -l || echo "0")
    backport_insertions=$(git diff --numstat "upstream/${target_branch}...HEAD" 2>/dev/null | awk '{s+=$1} END {print s+0}' || echo "0")
    backport_deletions=$(git diff --numstat "upstream/${target_branch}...HEAD" 2>/dev/null | awk '{s+=$2} END {print s+0}' || echo "0")

    # Read path diffs
    local path_notes=""
    if [[ -s "$STATE_DIR/path-diffs.txt" ]]; then
        path_notes=$(cat "$STATE_DIR/path-diffs.txt")
    fi

    # Read exclude files
    local exclude_list=""
    if [[ -s "$STATE_DIR/exclude-files.txt" ]]; then
        exclude_list=$(while IFS= read -r f; do
            [[ -z "$f" ]] && continue
            echo "| \`$(basename "$f" .adoc)\` | Not present on $target_branch |"
        done < "$STATE_DIR/exclude-files.txt")
    fi

    # Read included files from audit
    local include_list=""
    if [[ -f "$STATE_DIR/audit.json" ]]; then
        include_list=$(python3 -c "
import json
d = json.load(open('$STATE_DIR/audit.json'))
for f in d.get('branches', {}).get('$target_branch', {}).get('include', []):
    print(f'- \`{f}\`')
" 2>/dev/null || echo "")
    fi

    # PR title from source
    local pr_title=""
    if [[ -f "$STATE_DIR/pr-info.json" ]]; then
        pr_title=$(python3 -c "import json; print(json.load(open('$STATE_DIR/pr-info.json')).get('title',''))" 2>/dev/null || echo "")
    fi

    # Generate PR description
    cat > "$STATE_DIR/pr-description.md" <<PRDESC
## Summary

Backport of ${source} to ${target_branch}.

${pr_title}

## Files

${include_count} files included, ${exclude_count} files excluded.

### Excluded files (not present on ${target_branch})

| Module | Reason |
|--------|--------|
${exclude_list:-| _(none)_ | |
}

### Included files

${include_list:-_(all files included)_}

## Stats comparison

| Metric | Backport |
|--------|----------|
| Files changed | ${backport_file_count} |
| Insertions (+) | ${backport_insertions} |
| Deletions (-) | ${backport_deletions} |

${path_notes:+## Assembly notes

$path_notes
}
## Verification

- [ ] Preview renders correctly
- [ ] No broken includes or cross-references
- [ ] Content is appropriate for this release version
PRDESC

    # Push unless --no-push
    if [[ "$NO_PUSH" = false ]]; then
        echo "Pushing branch $branch_name..." >&2
        git push -u origin "$branch_name" 2>&1
        echo "" >&2
        echo "Branch pushed: $branch_name" >&2
    else
        echo "Branch created locally: $branch_name (--no-push)" >&2
    fi

    echo "PR description written to: $STATE_DIR/pr-description.md" >&2
    echo "" >&2

    # Print summary
    cat <<SUMMARY
=== Cherry-Pick Complete ===

Branch: $branch_name
Target: $target_branch
Files: $include_count included, $exclude_count excluded

PR description: $STATE_DIR/pr-description.md

Copy to clipboard:
  cat $STATE_DIR/pr-description.md | xclip -selection clipboard
SUMMARY
}

# --- Main ---

run_phase() {
    local phase="$1"
    case "$phase" in
        validate)   phase_validate ;;
        audit)      phase_audit ;;
        apply)
            IFS=',' read -ra BRANCH_ARRAY <<< "$TARGET_BRANCHES"
            for branch in "${BRANCH_ARRAY[@]}"; do
                phase_apply "$(echo "$branch" | xargs)"
            done
            ;;
        push)       phase_push ;;
        *)          echo "ERROR: Unknown phase: $phase" >&2; exit 1 ;;
    esac
}

if [[ -n "$PHASE" ]]; then
    # Run single phase
    run_phase "$PHASE"
else
    # Full run: validate -> audit -> apply -> push
    phase_validate
    phase_audit

    if [[ "$DRY_RUN" = true ]]; then
        exit 0
    fi

    # Process each target branch
    IFS=',' read -ra BRANCH_ARRAY <<< "$TARGET_BRANCHES"
    for branch in "${BRANCH_ARRAY[@]}"; do
        branch=$(echo "$branch" | xargs)
        phase_apply "$branch"
        phase_push

        # Return to original branch before processing next
        if [[ ${#BRANCH_ARRAY[@]} -gt 1 ]]; then
            orig_branch=$(cat "$STATE_DIR/original-branch.txt" 2>/dev/null || echo "main")
            git checkout "$orig_branch" 2>&1 >&2 || true
        fi
    done
fi
