#!/usr/bin/env bash
# Create or find an existing MR/PR for the published docs branch.
# Works in both local (current directory) and ACP (cloned repo) environments.
#
# Context resolution (ordered):
#   1. commit-info.json — always required (for pushed status)
#   2. repo-info.json (if exists) — ACP path for extra context
#   3. --repo-path or current directory git context — local fallback
#
# Usage: bash create_mr.sh <ticket-id> --base-path <path> [--repo-path <path>] [--draft] [--dry-run]
#
# Dependencies: python3, glab CLI (for GitLab), gh CLI (for GitHub)
set -euo pipefail

# --- Argument parsing ---
TICKET=""
BASE_PATH=""
REPO_PATH=""
DRAFT=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-path) BASE_PATH="$2"; shift 2 ;;
    --repo-path) REPO_PATH="$2"; shift 2 ;;
    --draft) DRAFT=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    -*) echo "ERROR: Unknown option: $1" >&2; exit 1 ;;
    *)
      if [[ -z "$TICKET" ]]; then
        TICKET="$1"
      else
        echo "ERROR: Unexpected argument: $1" >&2
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$TICKET" ]]; then
  echo "ERROR: Ticket ID is required." >&2
  exit 1
fi

if [[ -z "$BASE_PATH" ]]; then
  echo "ERROR: --base-path is required." >&2
  exit 1
fi

TICKET_LOWER="$(echo "$TICKET" | tr '[:upper:]' '[:lower:]')"
TICKET_UPPER="$(echo "$TICKET" | tr '[:lower:]' '[:upper:]')"
OUTPUT_DIR="${BASE_PATH}/create-mr"
mkdir -p "$OUTPUT_DIR"

# --- Helper: write mr-info.json ---
write_mr_info() {
  local url="$1"
  local action="$2"
  local title="${3:-}"
  python3 -c "
import json, sys
print(json.dumps({
    'platform': sys.argv[1],
    'url': sys.argv[2] if sys.argv[2] != 'null' else None,
    'action': sys.argv[3],
    'title': sys.argv[4] if sys.argv[4] else None
}, indent=2))
" "$PLATFORM" "$url" "$action" "$title" > "${OUTPUT_DIR}/mr-info.json"
  echo "Wrote ${OUTPUT_DIR}/mr-info.json"
}

# --- Helper: normalize git remote URL to HTTPS ---
# Handles SCP-style SSH, ssh:// URLs, and HTTPS URLs.
normalize_url() {
  local url="$1"
  echo "$url" | python3 -c "
import sys, re
url = sys.stdin.read().strip()
# ssh://git@host/owner/repo.git or ssh://git@host:port/owner/repo.git
m = re.match(r'ssh://(?:[^@]+@)?([^:/]+)(?::\d+)?/(.+?)(?:\.git)?$', url)
if m:
    print(f'https://{m.group(1)}/{m.group(2)}')
else:
    # SCP-style SSH: git@github.com:owner/repo.git -> https://github.com/owner/repo
    m = re.match(r'git@([^:]+):(.+?)(?:\.git)?$', url)
    if m:
        print(f'https://{m.group(1)}/{m.group(2)}')
    else:
        # Already HTTPS — strip trailing .git
        print(re.sub(r'\.git$', '', url))
"
}

# --- Draft mode: skip ---
if [[ "$DRAFT" == true ]]; then
  PLATFORM="unknown"
  write_mr_info "null" "skipped" ""
  echo "Draft mode — skipped MR/PR creation."
  exit 0
fi

# --- Read commit-info.json (from commit step's output directory) ---
COMMIT_INFO="${BASE_PATH}/commit/commit-info.json"

if [[ ! -f "$COMMIT_INFO" ]]; then
  echo "No commit-info.json found at ${COMMIT_INFO}. Nothing to do."
  PLATFORM="unknown"
  write_mr_info "null" "skipped" ""
  exit 0
fi

eval "$(python3 -c "
import json, sys, shlex
d = json.load(open(sys.argv[1]))
print(f'PUSHED={shlex.quote(str(d.get(\"pushed\", False)).lower())}')
print(f'PUB_BRANCH={shlex.quote(d.get(\"branch\") or \"\")}')
print(f'PUB_PLATFORM={shlex.quote(d.get(\"platform\") or \"\")}')
print(f'PUB_REPO_URL={shlex.quote(d.get(\"repo_url\") or \"\")}')
" "$COMMIT_INFO")"

if [[ "$PUSHED" != "true" ]]; then
  echo "commit-info.json has pushed=false. Skipping MR/PR creation."
  PLATFORM="${PUB_PLATFORM:-unknown}"
  write_mr_info "null" "skipped" ""
  exit 0
fi

# --- Resolve context ---
# Start with commit-info values
BRANCH="$PUB_BRANCH"
PLATFORM="$PUB_PLATFORM"
REPO_URL="$PUB_REPO_URL"
DEFAULT_BRANCH="main"

# Try repo-info.json for extra context (default branch, etc.)
REPO_INFO="${BASE_PATH}/repo-info.json"
if [[ -f "$REPO_INFO" ]]; then
  eval "$(python3 -c "
import json, sys, shlex
d = json.load(open(sys.argv[1]))
url = d.get('repo_url') or ''
db = d.get('default_branch', 'main')
plat = d.get('platform', '')
print(f'RI_REPO_URL={shlex.quote(url)}')
print(f'RI_DEFAULT_BRANCH={shlex.quote(db)}')
print(f'RI_PLATFORM={shlex.quote(plat)}')
" "$REPO_INFO")"
  DEFAULT_BRANCH="${RI_DEFAULT_BRANCH:-main}"
  [[ -z "$REPO_URL" ]] && REPO_URL="$RI_REPO_URL"
  [[ -z "$PLATFORM" || "$PLATFORM" == "unknown" ]] && PLATFORM="$RI_PLATFORM"
fi

# Fall back to git context if still missing values
if [[ -z "$REPO_URL" || -z "$BRANCH" ]]; then
  RESOLVE_DIR=""
  if [[ -n "$REPO_PATH" ]]; then
    RESOLVE_DIR="$REPO_PATH"
  else
    RESOLVE_DIR="$(pwd)"
  fi

  if git -C "$RESOLVE_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    [[ -z "$REPO_URL" ]] && REPO_URL="$(git -C "$RESOLVE_DIR" remote get-url origin 2>/dev/null || echo "")"
    [[ -z "$BRANCH" ]] && BRANCH="$(git -C "$RESOLVE_DIR" rev-parse --abbrev-ref HEAD)"

    if [[ -z "$PLATFORM" || "$PLATFORM" == "unknown" ]]; then
      if echo "$REPO_URL" | grep -q "github.com"; then
        PLATFORM="github"
      elif echo "$REPO_URL" | grep -q "gitlab"; then
        PLATFORM="gitlab"
      fi
    fi

    if [[ "$DEFAULT_BRANCH" == "main" ]]; then
      local_remote="$(git -C "$RESOLVE_DIR" remote | grep -m1 upstream || git -C "$RESOLVE_DIR" remote | head -1)"
      detected_default="$(git -C "$RESOLVE_DIR" remote show "$local_remote" 2>/dev/null | sed -n 's/.*HEAD branch: //p' || echo "")"
      [[ -n "$detected_default" ]] && DEFAULT_BRANCH="$detected_default"
    fi
  fi
fi

if [[ -z "$REPO_URL" ]]; then
  echo "ERROR: Could not determine repository URL from any source." >&2
  exit 1
fi

if [[ -z "$BRANCH" ]]; then
  echo "ERROR: Could not determine branch name from any source." >&2
  exit 1
fi

echo "Platform: ${PLATFORM}"
echo "Repo URL: ${REPO_URL}"
echo "Branch:   ${BRANCH} → ${DEFAULT_BRANCH}"

# --- Build MR/PR title ---
REQUIREMENTS_FILE="${BASE_PATH}/requirements/requirements.md"
SUMMARY=""
if [[ -f "$REQUIREMENTS_FILE" ]]; then
  SUMMARY="$(python3 -c "
import sys, re
with open(sys.argv[1]) as f:
    for line in f:
        line = line.strip()
        m = re.match(r'^#+\s+(.+)', line)
        if m:
            title = m.group(1)
            title = re.sub(r'^' + re.escape(sys.argv[2]) + r'\s*[-:]\s*', '', title, flags=re.IGNORECASE)
            if title:
                print(title[:80])
                break
" "$REQUIREMENTS_FILE" "$TICKET_UPPER" 2>/dev/null || true)"
fi

if [[ -z "$SUMMARY" ]]; then
  SUMMARY="generated documentation"
fi

TITLE="docs(${TICKET_UPPER}): ${SUMMARY}"

# --- Build MR/PR description ---
DESCRIPTION="Documentation generated by the docs pipeline.

**JIRA ticket:** ${TICKET_UPPER}
**Branch:** ${BRANCH}
**Target:** ${DEFAULT_BRANCH}"

# Append committed files if available
FILES_LIST="$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
files = d.get('files_committed', [])
if files:
    for f in files:
        print(f'- \`{f}\`')
" "$COMMIT_INFO" 2>/dev/null || true)"

if [[ -n "$FILES_LIST" ]]; then
  DESCRIPTION="${DESCRIPTION}

**Files:**
${FILES_LIST}"
fi

# --- Dry-run output ---
if [[ "$DRY_RUN" == "true" ]]; then
  echo "=== DRY RUN ==="
  echo "Platform: ${PLATFORM}"
  echo "Repo URL: ${REPO_URL}"
  echo "Branch: ${BRANCH}"
  echo "Target: ${DEFAULT_BRANCH}"
  echo "Title: ${TITLE}"
  echo "Description:"
  echo "$DESCRIPTION"
  echo "==============="
  exit 0
fi

# --- Source credentials ---
source ~/.env 2>/dev/null || true

# --- Normalize URL to HTTPS for project path extraction ---
REPO_URL="$(normalize_url "$REPO_URL")"

# --- Platform-specific MR/PR creation ---
if [[ "$PLATFORM" == "gitlab" ]]; then
  # Extract project path from GitLab URL (already normalized to HTTPS)
  PROJECT_PATH="$(echo "$REPO_URL" | sed -E 's|https?://[^/]+/||')"

  # Export GITLAB_HOST so glab knows which instance to use
  export GITLAB_HOST="$(echo "$REPO_URL" | sed -E 's|(https?://[^/]+).*|\1|')"

  # Check for existing MR
  EXISTING_URL="$(glab mr list --source-branch "$BRANCH" --repo "$PROJECT_PATH" -F json 2>/dev/null \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
if isinstance(data, list) and len(data) > 0:
    print(data[0].get('web_url', ''))
else:
    print('')
" 2>/dev/null || echo "")"

  if [[ -n "$EXISTING_URL" ]]; then
    echo "Found existing MR: ${EXISTING_URL}"
    write_mr_info "$EXISTING_URL" "found_existing" "$TITLE"
    echo "$EXISTING_URL"
    exit 0
  fi

  # Create new MR
  MR_OUTPUT="$(glab mr create \
    --source-branch "$BRANCH" \
    --target-branch "$DEFAULT_BRANCH" \
    --title "$TITLE" \
    --description "$DESCRIPTION" \
    --repo "$PROJECT_PATH" \
    --no-editor --yes 2>&1)" || {
    echo "ERROR: Failed to create MR: ${MR_OUTPUT}" >&2
    write_mr_info "null" "skipped" "$TITLE"
    exit 1
  }

  # Extract the MR URL from glab output
  MR_URL="$(echo "$MR_OUTPUT" | grep -oE 'https?://[^ ]+' | tail -1)"

  if [[ -n "$MR_URL" ]]; then
    echo "Created MR: ${MR_URL}"
    write_mr_info "$MR_URL" "created" "$TITLE"
    echo "$MR_URL"
  else
    echo "ERROR: Failed to create MR. Output: ${MR_OUTPUT}" >&2
    write_mr_info "null" "skipped" "$TITLE"
    exit 1
  fi

elif [[ "$PLATFORM" == "github" ]]; then
  # Extract owner/repo from GitHub URL (already normalized to HTTPS)
  OWNER_REPO="$(echo "$REPO_URL" | sed -E 's|https?://github\.com/||')"

  # Check for existing PR
  EXISTING_PR="$(gh pr list --head "$BRANCH" --repo "$OWNER_REPO" --json url --jq '.[0].url' 2>/dev/null || echo "")"

  if [[ -n "$EXISTING_PR" ]]; then
    echo "Found existing PR: ${EXISTING_PR}"
    write_mr_info "$EXISTING_PR" "found_existing" "$TITLE"
    echo "$EXISTING_PR"
    exit 0
  fi

  # Create new PR
  PR_URL="$(gh pr create \
    --repo "$OWNER_REPO" \
    --head "$BRANCH" \
    --base "$DEFAULT_BRANCH" \
    --title "$TITLE" \
    --body "$DESCRIPTION" 2>&1)" || {
    echo "ERROR: Failed to create PR: ${PR_URL}" >&2
    write_mr_info "null" "skipped" "$TITLE"
    exit 1
  }

  echo "Created PR: ${PR_URL}"
  write_mr_info "$PR_URL" "created" "$TITLE"
  echo "$PR_URL"

else
  echo "ERROR: Unknown platform '${PLATFORM}'. Cannot create MR/PR." >&2
  write_mr_info "null" "skipped" "$TITLE"
  exit 1
fi
