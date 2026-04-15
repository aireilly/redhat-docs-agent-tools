#!/usr/bin/env bash
# Commit manifest-listed files and push the feature branch.
# Works in both local (current directory) and ACP (cloned repo) environments.
#
# Context resolution (ordered):
#   1. repo-info.json (if exists) — ACP path
#   2. --repo-path argument — explicit target
#   3. Current working directory — local path
#
# Usage: bash commit.sh <ticket-id> --base-path <path> [--repo-path <path>] [--draft] [--dry-run]
#
# Dependencies: git, python3
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
OUTPUT_DIR="${BASE_PATH}/commit"
mkdir -p "$OUTPUT_DIR"

# --- Draft mode: skip ---
if [[ "$DRAFT" == true ]]; then
  python3 -c "
import json
print(json.dumps({
    'branch': None,
    'commit_sha': None,
    'files_committed': [],
    'platform': None,
    'repo_url': None,
    'pushed': False,
    'skip_reason': 'draft mode'
}, indent=2))
" > "${OUTPUT_DIR}/commit-info.json"
  echo "Draft mode — skipped committing."
  exit 0
fi

# --- Resolve repo context ---
# Try repo-info.json first (ACP path), then --repo-path or current directory
REPO_INFO="${BASE_PATH}/repo-info.json"
REPO_DIR=""
REPO_URL=""
PLATFORM=""
BRANCH=""
DEFAULT_BRANCH=""

# Normalize git remote URL to HTTPS (handles SCP-style SSH, ssh:// URLs, and HTTPS).
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
    # SCP-style SSH: git@host:owner/repo.git
    m = re.match(r'git@([^:]+):(.+?)(?:\.git)?$', url)
    if m:
        print(f'https://{m.group(1)}/{m.group(2)}')
    else:
        print(re.sub(r'\.git$', '', url))
"
}

# Populate REPO_DIR, BRANCH, REPO_URL, PLATFORM, and DEFAULT_BRANCH from a git directory.
resolve_from_git() {
  local dir="$1"

  if [[ ! -d "${dir}/.git" ]] && ! git -C "$dir" rev-parse --git-dir >/dev/null 2>&1; then
    echo "ERROR: ${dir} is not a git repository." >&2
    exit 1
  fi

  # Always resolve to repo root, not the passed directory
  REPO_DIR="$(git -C "$dir" rev-parse --show-toplevel)"
  BRANCH="$(git -C "$dir" rev-parse --abbrev-ref HEAD)"
  local raw_url
  raw_url="$(git -C "$dir" remote get-url origin 2>/dev/null || echo "")"
  REPO_URL="$(normalize_url "$raw_url")"

  # Detect platform from URL
  if echo "$REPO_URL" | grep -q "github.com"; then
    PLATFORM="github"
  elif echo "$REPO_URL" | grep -q "gitlab"; then
    PLATFORM="gitlab"
  else
    PLATFORM="unknown"
  fi

  # Detect default branch from remote HEAD
  local remote
  remote="$(git -C "$dir" remote | grep -m1 upstream || git -C "$dir" remote | head -1)"
  DEFAULT_BRANCH="$(git -C "$dir" remote show "$remote" 2>/dev/null | sed -n 's/.*HEAD branch: //p' || echo "")"
  if [[ -z "$DEFAULT_BRANCH" ]]; then
    for candidate in main master; do
      if git -C "$dir" rev-parse --verify "origin/${candidate}" >/dev/null 2>&1; then
        DEFAULT_BRANCH="$candidate"
        break
      fi
    done
  fi
  DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"
}

if [[ -f "$REPO_INFO" ]]; then
  # ACP path: read from repo-info.json
  eval "$(python3 -c "
import json, sys, shlex
d = json.load(open(sys.argv[1]))
print(f'REPO_URL={shlex.quote(d.get(\"repo_url\") or \"\")}')
print(f'REPO_DIR={shlex.quote(d.get(\"clone_path\") or \"\")}')
print(f'BRANCH={shlex.quote(d.get(\"branch\") or \"\")}')
print(f'PLATFORM={shlex.quote(d.get(\"platform\") or \"\")}')
print(f'DEFAULT_BRANCH={shlex.quote(d.get(\"default_branch\", \"main\"))}')
" "$REPO_INFO")"

  if [[ -z "$REPO_URL" ]]; then
    echo "repo_url is null in repo-info.json. Nothing to commit (draft mode)."
    python3 -c "
import json
print(json.dumps({
    'branch': None,
    'commit_sha': None,
    'files_committed': [],
    'platform': None,
    'repo_url': None,
    'pushed': False,
    'skip_reason': 'no repo URL in repo-info.json'
}, indent=2))
" > "${OUTPUT_DIR}/commit-info.json"
    exit 0
  fi

  if [[ ! -d "$REPO_DIR/.git" ]]; then
    echo "ERROR: Clone path does not exist: ${REPO_DIR}" >&2
    exit 1
  fi

elif [[ -n "$REPO_PATH" ]]; then
  # Explicit --repo-path
  resolve_from_git "$REPO_PATH"

else
  # Local mode: current working directory
  resolve_from_git "$(pwd)"
fi

echo "Repo:     ${REPO_DIR}"
echo "Branch:   ${BRANCH}"
echo "Platform: ${PLATFORM}"
echo "Remote:   ${REPO_URL}"

# --- Safety: refuse to push to main/master ---
if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
  echo "ERROR: Refusing to push to '${BRANCH}'. All pushes must go to feature branches." >&2
  exit 1
fi

# --- Safety: refuse to push if in the agent-tools repo ---
if [[ -d "${REPO_DIR}/adapters/ambient" ]]; then
  echo "ERROR: Refusing to commit from the agent-tools repository. Target a docs repository instead." >&2
  exit 1
fi

# --- Read manifest ---
MANIFEST="${BASE_PATH}/writing/_index.md"

if [[ ! -f "$MANIFEST" ]]; then
  echo "No manifest found at ${MANIFEST}. Orchestrator may not have completed the writing step."
  python3 -c "
import json, sys
print(json.dumps({
    'branch': sys.argv[1],
    'commit_sha': None,
    'files_committed': [],
    'platform': sys.argv[2],
    'repo_url': sys.argv[3],
    'pushed': False,
    'skip_reason': 'no manifest'
}, indent=2))
" "$BRANCH" "$PLATFORM" "$REPO_URL" > "${OUTPUT_DIR}/commit-info.json"
  exit 0
fi

# Extract file paths from the manifest table that are under the repo directory.
# Manifest table rows look like: | /absolute/path/to/file.md | TYPE | Description |
# Also handles backtick-wrapped paths: | `/absolute/path/to/file.md` | TYPE | Description |
REPO_DIR_ABS="$(cd "$REPO_DIR" && pwd)"
readarray -t MANIFEST_FILES < <(python3 -c "
import sys, re
clone = sys.argv[1]
with open(sys.argv[2]) as f:
    for line in f:
        for m in re.findall(r'\|\s*\x60?(' + re.escape(clone) + r'\S+?)\x60?\s*(?:\||$)', line):
            print(m)
" "$REPO_DIR_ABS" "$MANIFEST" 2>/dev/null)

if [[ ${#MANIFEST_FILES[@]} -eq 0 ]]; then
  echo "No files found in manifest under ${REPO_DIR_ABS}."
  python3 -c "
import json, sys
print(json.dumps({
    'branch': sys.argv[1],
    'commit_sha': None,
    'files_committed': [],
    'platform': sys.argv[2],
    'repo_url': sys.argv[3],
    'pushed': False,
    'skip_reason': 'no files in manifest'
}, indent=2))
" "$BRANCH" "$PLATFORM" "$REPO_URL" > "${OUTPUT_DIR}/commit-info.json"
  exit 0
fi

# --- Dry run ---
if [[ "$DRY_RUN" == true ]]; then
  echo "=== Dry Run ==="
  echo "Ticket:     $TICKET"
  echo "Repo:       $REPO_DIR_ABS"
  echo "Branch:     $BRANCH"
  echo "Platform:   $PLATFORM"
  echo ""
  echo "Files to commit (${#MANIFEST_FILES[@]}):"
  for f in "${MANIFEST_FILES[@]}"; do
    echo "  - ${f#${REPO_DIR_ABS}/}"
  done
  exit 0
fi

# --- Check for changes ---
cd "$REPO_DIR_ABS"

if git diff --quiet HEAD 2>/dev/null && \
   [[ -z "$(git ls-files --others --exclude-standard 2>/dev/null)" ]]; then
  echo "No changes detected in ${REPO_DIR_ABS}. Nothing to commit."
  python3 -c "
import json, sys
print(json.dumps({
    'branch': sys.argv[1],
    'commit_sha': None,
    'files_committed': [],
    'platform': sys.argv[2],
    'repo_url': sys.argv[3],
    'pushed': False,
    'skip_reason': 'no changes'
}, indent=2))
" "$BRANCH" "$PLATFORM" "$REPO_URL" > "${OUTPUT_DIR}/commit-info.json"
  exit 0
fi

# --- Stage manifest files ---
STAGED_FILES=()
for filepath in "${MANIFEST_FILES[@]}"; do
  if [[ -f "$filepath" ]]; then
    git add "$filepath" || { echo "WARNING: failed to stage ${filepath}" >&2; continue; }
    STAGED_FILES+=("${filepath#${REPO_DIR_ABS}/}")
  else
    echo "WARNING: Manifest lists ${filepath} but file does not exist. Skipping." >&2
  fi
done

if [[ ${#STAGED_FILES[@]} -eq 0 ]]; then
  echo "No manifest files exist on disk. Nothing to commit."
  python3 -c "
import json, sys
print(json.dumps({
    'branch': sys.argv[1],
    'commit_sha': None,
    'files_committed': [],
    'platform': sys.argv[2],
    'repo_url': sys.argv[3],
    'pushed': False,
    'skip_reason': 'no manifest files on disk'
}, indent=2))
" "$BRANCH" "$PLATFORM" "$REPO_URL" > "${OUTPUT_DIR}/commit-info.json"
  exit 0
fi

# --- Build commit message ---
COMMIT_MSG="docs(${TICKET_LOWER}): add generated documentation

Files:
$(printf '  - %s\n' "${STAGED_FILES[@]}")

Generated by docs-pipeline for ${TICKET}"

# --- Commit ---
git commit -m "$COMMIT_MSG" 2>&1

COMMIT_SHA=$(git rev-parse HEAD)
echo "Committed: ${COMMIT_SHA}"

# --- Push ---
# Fetch the remote branch ref so --force-with-lease has correct tracking info.
git fetch origin "$BRANCH" 2>/dev/null || true

# Use --force-with-lease: these are pipeline-generated branches, not collaborative
# work. Re-runs create a fresh branch from main, diverging from the remote.
if git push --force-with-lease -u origin "$BRANCH" 2>&1; then
  PUSH_STATUS="true"
  echo "Pushed branch '${BRANCH}' to origin"
else
  PUSH_STATUS="false"
  echo "ERROR: Push failed. Branch committed locally but not pushed." >&2
fi

# --- Write commit-info.json ---
python3 -c "
import json, sys
files = sys.argv[6:]
print(json.dumps({
    'branch': sys.argv[1],
    'commit_sha': sys.argv[2],
    'files_committed': files,
    'platform': sys.argv[3],
    'repo_url': sys.argv[4],
    'pushed': sys.argv[5] == 'true'
}, indent=2))
" "$BRANCH" "$COMMIT_SHA" "$PLATFORM" "$REPO_URL" "$PUSH_STATUS" "${STAGED_FILES[@]}" > "${OUTPUT_DIR}/commit-info.json"

echo "Wrote ${OUTPUT_DIR}/commit-info.json"
