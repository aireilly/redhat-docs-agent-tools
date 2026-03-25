#!/bin/bash
# commits-ready-check.sh
#
# Gate script for commit-driven docs-orchestrator runs.
# Checks a code repository for new commits since the last processed marker,
# applies file filtering to exclude irrelevant commits, and returns a JSON
# payload of actionable commit batches.
#
# Usage:
#   bash commits-ready-check.sh \
#     --repo https://github.com/org/repo \
#     [--branch main] \
#     [--base-path .claude/docs] \
#     [--since <sha>] \
#     [--max-commits 50] \
#     [--dry-run]
#
# Requires: jq, python3, git_commit_reader.py, GITHUB_TOKEN or GITLAB_TOKEN

set -euo pipefail

# --- Defaults ---
REPO=""
BRANCH="main"
BASE_PATH=".claude/docs"
SINCE_SHA=""
MAX_COMMITS=50
DRY_RUN=false

# Resolve git_commit_reader.py relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMIT_READER="${SCRIPT_DIR}/../../git-pr-reader/scripts/git_commit_reader.py"

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ -n "${2:-}" ]] || { echo '{"error": "--repo requires a URL"}'; exit 1; }
      REPO="$2"; shift 2 ;;
    --branch)
      [[ -n "${2:-}" ]] || { echo '{"error": "--branch requires a name"}'; exit 1; }
      BRANCH="$2"; shift 2 ;;
    --base-path)
      [[ -n "${2:-}" ]] || { echo '{"error": "--base-path requires a path"}'; exit 1; }
      BASE_PATH="$2"; shift 2 ;;
    --since)
      [[ -n "${2:-}" ]] || { echo '{"error": "--since requires a SHA"}'; exit 1; }
      SINCE_SHA="$2"; shift 2 ;;
    --max-commits)
      [[ -n "${2:-}" ]] || { echo '{"error": "--max-commits requires a number"}'; exit 1; }
      MAX_COMMITS="$2"; shift 2 ;;
    --dry-run)
      DRY_RUN=true; shift ;;
    *)
      echo "{\"error\": \"Unknown argument: $1\"}"; exit 1 ;;
  esac
done

if [[ -z "$REPO" ]]; then
  echo '{"error": "--repo is required"}'
  exit 1
fi

# --- Validate environment ---
if [[ -z "${GITHUB_TOKEN:-}${GITLAB_TOKEN:-}" ]]; then
  # Try sourcing ~/.env
  set -a; source ~/.env 2>/dev/null || true; set +a
fi

if [[ ! -f "$COMMIT_READER" ]]; then
  echo "{\"error\": \"git_commit_reader.py not found at $COMMIT_READER\"}"
  exit 1
fi

# --- Derive repo slug for marker file ---
REPO_SLUG=$(echo "$REPO" | sed 's|https\?://||' | sed 's|\.git$||' | sed 's|[^a-zA-Z0-9]|-|g' | tr '[:upper:]' '[:lower:]')
MARKER_DIR="${BASE_PATH}/.commit-markers"
MARKER_FILE="${MARKER_DIR}/${REPO_SLUG}.json"

# --- Read marker for last processed SHA ---
if [[ -z "$SINCE_SHA" ]]; then
  if [[ -f "$MARKER_FILE" ]]; then
    SINCE_SHA=$(jq -r '.last_processed_sha // empty' "$MARKER_FILE" 2>/dev/null || true)
  fi
fi

# --- Query commits ---
READER_ARGS="list $REPO --branch $BRANCH --max $MAX_COMMITS --no-merges --drop-empty --json"
if [[ -n "$SINCE_SHA" ]]; then
  READER_ARGS="$READER_ARGS --since $SINCE_SHA"
fi

COMMIT_OUTPUT=$(python3 "$COMMIT_READER" $READER_ARGS 2>&1) || {
  echo "{\"error\": \"git_commit_reader.py failed\", \"detail\": $(echo "$COMMIT_OUTPUT" | jq -Rs .)}"
  exit 1
}

# --- Extract commit count ---
TOTAL=$(echo "$COMMIT_OUTPUT" | jq -r '.total')

if [[ "$TOTAL" -eq 0 || "$TOTAL" == "null" ]]; then
  jq -n \
    --arg repo "$REPO" \
    --arg branch "$BRANCH" \
    --arg marker "$SINCE_SHA" \
    '{
      repository: $repo,
      branch: $branch,
      marker_sha: $marker,
      total_new_commits: 0,
      filtered_out: 0,
      ready: false,
      batch: null,
      filtered: {}
    }'
  exit 0
fi

# --- Extract commit SHAs ---
ALL_SHAS=$(echo "$COMMIT_OUTPUT" | jq -r '.commits[].sha')
FIRST_SHA=$(echo "$COMMIT_OUTPUT" | jq -r '.commits[0].sha')
LAST_SHA=$(echo "$COMMIT_OUTPUT" | jq -r '.commits[-1].sha')

# --- Derive repo short name ---
REPO_SHORT=$(echo "$REPO" | sed 's|.*/||' | sed 's|\.git$||')

# --- Build batch identifier ---
FIRST_SHORT="${FIRST_SHA:0:7}"
LAST_SHORT="${LAST_SHA:0:7}"
if [[ "$FIRST_SHA" == "$LAST_SHA" ]]; then
  IDENTIFIER="${REPO_SHORT}/${FIRST_SHORT}"
else
  IDENTIFIER="${REPO_SHORT}/${FIRST_SHORT}-${LAST_SHORT}"
fi

# --- Filter out already-processed batches ---
FILTERED_COUNT=0
declare -A FILTERED_MAP

# Check if a progress file already exists for this identifier
IDENTIFIER_LOWER=$(echo "$IDENTIFIER" | tr '[:upper:]' '[:lower:]')
if compgen -G "${BASE_PATH}/${IDENTIFIER_LOWER}/workflow/*.json" >/dev/null 2>&1; then
  # The entire batch has already been processed
  jq -n \
    --arg repo "$REPO" \
    --arg branch "$BRANCH" \
    --arg marker "$SINCE_SHA" \
    --arg id "$IDENTIFIER" \
    '{
      repository: $repo,
      branch: $branch,
      marker_sha: $marker,
      total_new_commits: 0,
      filtered_out: 1,
      ready: false,
      batch: null,
      filtered: {($id): "progress_file_exists"}
    }'
  exit 0
fi

# --- Build commit list as JSON array ---
COMMITS_JSON=$(echo "$COMMIT_OUTPUT" | jq '[.commits[].sha]')

# --- Build output ---
FILTERED_STATS=$(echo "$COMMIT_OUTPUT" | jq '.filtered_stats')

jq -n \
  --arg repo "$REPO" \
  --arg branch "$BRANCH" \
  --arg marker "${SINCE_SHA:-}" \
  --argjson total "$TOTAL" \
  --arg id "$IDENTIFIER" \
  --argjson commits "$COMMITS_JSON" \
  --arg first "$FIRST_SHA" \
  --arg last "$LAST_SHA" \
  --argjson filtered_stats "$FILTERED_STATS" \
  '{
    repository: $repo,
    branch: $branch,
    marker_sha: $marker,
    total_new_commits: $total,
    filtered_out: 0,
    ready: true,
    batch: {
      identifier: $id,
      commits: $commits,
      first_sha: $first,
      last_sha: $last,
      summary: (($total | tostring) + " commits")
    },
    filtered_stats: $filtered_stats,
    filtered: {}
  }'
