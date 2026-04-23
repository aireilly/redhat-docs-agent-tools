#!/usr/bin/env bash
# Create or find an existing MR/PR for the published docs branch.
# Usage: bash create_mr.sh <ticket-id> --base-path <path> [--repo-path <path>] [--draft]
# Dependencies: python3, glab CLI (for GitLab), gh CLI (for GitHub)
set -euo pipefail

# --- Argument parsing ---
TICKET=""
BASE_PATH=""
DRAFT=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-path) BASE_PATH="$2"; shift 2 ;;
    --repo-path) shift 2 ;;  # Accepted but unused — context comes from commit-info.json
    --draft) DRAFT=true; shift ;;
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

[[ -z "$TICKET" ]] && { echo "ERROR: Ticket ID is required." >&2; exit 1; }
[[ -z "$BASE_PATH" ]] && { echo "ERROR: --base-path is required." >&2; exit 1; }

TICKET_UPPER="$(echo "$TICKET" | tr '[:lower:]' '[:upper:]')"
OUTPUT_DIR="${BASE_PATH}/create-mr"
mkdir -p "$OUTPUT_DIR"
PLATFORM="unknown"

# --- Helper: write mr-info.json ---
write_mr_info() {
  local url="$1" action="$2" title="${3:-}"
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
    # SCP-style SSH: git@github.com:owner/repo.git
    m = re.match(r'git@([^:]+):(.+?)(?:\.git)?$', url)
    if m:
        print(f'https://{m.group(1)}/{m.group(2)}')
    else:
        print(re.sub(r'\.git$', '', url))
"
}

# --- Helper: ensure required CLI tool is available ---
ensure_cli() {
  local tool="$1"
  if command -v "$tool" >/dev/null 2>&1; then
    return 0
  fi

  echo "${tool} CLI not found. Attempting to install..." >&2

  # Try common package managers
  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y "$tool" 2>/dev/null && return 0
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -qq && sudo apt-get install -y "$tool" 2>/dev/null && return 0
  elif command -v brew >/dev/null 2>&1; then
    brew install "$tool" 2>/dev/null && return 0
  fi

  echo "ERROR: ${tool} CLI is required but could not be installed. Install it manually:" >&2
  if [[ "$tool" == "gh" ]]; then
    echo "  https://cli.github.com/manual/installation" >&2
  else
    echo "  https://gitlab.com/gitlab-org/cli#installation" >&2
  fi
  exit 1
}

# --- Draft mode: skip ---
if [[ "$DRAFT" == true ]]; then
  write_mr_info "null" "skipped" ""
  echo "Draft mode — skipped MR/PR creation."
  exit 0
fi

# --- Read commit-info.json ---
COMMIT_INFO="${BASE_PATH}/commit/commit-info.json"

if [[ ! -f "$COMMIT_INFO" ]]; then
  echo "No commit-info.json found at ${COMMIT_INFO}. Nothing to do."
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
# Trust commit-info.json — branch/platform/repo_url guaranteed when pushed=true
BRANCH="$PUB_BRANCH"
PLATFORM="$PUB_PLATFORM"
REPO_URL="$PUB_REPO_URL"
DEFAULT_BRANCH="main"

# Get default_branch from repo-info.json if available
REPO_INFO="${BASE_PATH}/repo-info.json"
if [[ -f "$REPO_INFO" ]]; then
  DEFAULT_BRANCH="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('default_branch','main'))" "$REPO_INFO" 2>/dev/null || echo main)"
fi

if [[ -z "$REPO_URL" || -z "$BRANCH" ]]; then
  echo "ERROR: commit-info.json has pushed=true but is missing branch or repo_url." >&2
  exit 1
fi

echo "Platform: ${PLATFORM}"
echo "Repo URL: ${REPO_URL}"
echo "Branch:   ${BRANCH} → ${DEFAULT_BRANCH}"

# --- Pre-flight: ensure CLI tool is available ---
if [[ "$PLATFORM" == "github" ]]; then
  ensure_cli gh
elif [[ "$PLATFORM" == "gitlab" ]]; then
  ensure_cli glab
fi

# --- Build MR/PR title (sidecar-first, fallback to heading regex) ---
REQ_SIDECAR="${BASE_PATH}/requirements/step-result.json"
REQUIREMENTS_FILE="${BASE_PATH}/requirements/requirements.md"
SUMMARY=""

if [[ -f "$REQ_SIDECAR" ]]; then
  SUMMARY="$(python3 -c "
import json, sys
sidecar = json.load(open(sys.argv[1]))
title = sidecar.get('title', '')
if title:
    print(title[:80])
" "$REQ_SIDECAR" 2>/dev/null || true)"
fi

if [[ -z "$SUMMARY" && -f "$REQUIREMENTS_FILE" ]]; then
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

TITLE="docs(${TICKET_UPPER}): ${SUMMARY:-generated documentation}"

# --- Build MR/PR description ---
DESCRIPTION="Documentation generated by the docs pipeline.

**JIRA ticket:** ${TICKET_UPPER}
**Branch:** ${BRANCH}
**Target:** ${DEFAULT_BRANCH}"

FILES_LIST="$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
for f in d.get('files_committed', []):
    print(f'- \`{f}\`')
" "$COMMIT_INFO" 2>/dev/null || true)"

if [[ -n "$FILES_LIST" ]]; then
  DESCRIPTION="${DESCRIPTION}

**Files:**
${FILES_LIST}"
fi

# --- Source credentials ---
source ~/.env 2>/dev/null || true

# --- Normalize URL to HTTPS for project path extraction ---
REPO_URL="$(normalize_url "$REPO_URL")"

# --- Platform-specific MR/PR creation ---
if [[ "$PLATFORM" == "gitlab" ]]; then
  PROJECT_PATH="$(echo "$REPO_URL" | sed -E 's|https?://[^/]+/||')"
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
    exit 0
  fi

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

  MR_URL="$(echo "$MR_OUTPUT" | grep -oE 'https?://[^ ]+' | tail -1)"
  if [[ -n "$MR_URL" ]]; then
    echo "Created MR: ${MR_URL}"
    write_mr_info "$MR_URL" "created" "$TITLE"
  else
    echo "ERROR: Failed to create MR. Output: ${MR_OUTPUT}" >&2
    write_mr_info "null" "skipped" "$TITLE"
    exit 1
  fi

elif [[ "$PLATFORM" == "github" ]]; then
  OWNER_REPO="$(echo "$REPO_URL" | sed -E 's|https?://github\.com/||')"

  EXISTING_PR="$(gh pr list --head "$BRANCH" --repo "$OWNER_REPO" --json url --jq '.[0].url' 2>/dev/null || echo "")"
  if [[ -n "$EXISTING_PR" ]]; then
    echo "Found existing PR: ${EXISTING_PR}"
    write_mr_info "$EXISTING_PR" "found_existing" "$TITLE"
    exit 0
  fi

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

else
  echo "ERROR: Unknown platform '${PLATFORM}'. Cannot create MR/PR." >&2
  write_mr_info "null" "skipped" "$TITLE"
  exit 1
fi
