#!/usr/bin/env bash
# Prepare a clean git branch from the latest upstream default branch.
# Used by the docs-workflow-prepare-branch skill.
#
# Usage: prepare_branch.sh <ticket-id> --base-path <path> [--draft] [--repo-path <path>]
#
# Outputs: <base-path>/prepare-branch/branch-info.md

set -euo pipefail

# --- Argument parsing ---
TICKET=""
BASE_PATH=""
DRAFT=false
REPO_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-path)
      BASE_PATH="$2"
      shift 2
      ;;
    --draft)
      DRAFT=true
      shift
      ;;
    --repo-path)
      REPO_PATH="$2"
      shift 2
      ;;
    -*)
      echo "ERROR: Unknown option: $1" >&2
      exit 1
      ;;
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
  echo "ERROR: Ticket ID is required as the first positional argument." >&2
  exit 1
fi

if [[ -z "$BASE_PATH" ]]; then
  echo "ERROR: --base-path is required." >&2
  exit 1
fi

OUTPUT_DIR="${BASE_PATH}/prepare-branch"
OUTPUT_FILE="${OUTPUT_DIR}/branch-info.md"
mkdir -p "$OUTPUT_DIR"

# --- Skip mode: draft or repo-path ---
if [[ "$DRAFT" == true ]]; then
  cat > "$OUTPUT_FILE" <<'EOF'
# Branch Preparation — Skipped
Draft mode: no branch created.
EOF
  echo "Draft mode — skipped branch creation."
  exit 0
fi

if [[ -n "$REPO_PATH" ]]; then
  cat > "$OUTPUT_FILE" <<'EOF'
# Branch Preparation — Skipped
Repo-path mode: branch managed externally by repo-setup.sh.
EOF
  echo "Repo-path mode — skipped branch creation (managed externally)."
  exit 0
fi

# --- Detect default upstream branch ---
DEFAULT_REMOTE=$(git remote | grep -m1 upstream || git remote | head -1)
if [[ -z "$DEFAULT_REMOTE" ]]; then
  echo "ERROR: No git remotes found." >&2
  exit 1
fi

DEFAULT_BRANCH=$(git remote show "$DEFAULT_REMOTE" 2>/dev/null | sed -n 's/.*HEAD branch: //p')
if [[ -z "$DEFAULT_BRANCH" ]]; then
  # Fall back to main, then master
  for candidate in main master; do
    if git rev-parse --verify "${DEFAULT_REMOTE}/${candidate}" >/dev/null 2>&1; then
      DEFAULT_BRANCH="$candidate"
      break
    fi
  done
fi

if [[ -z "$DEFAULT_BRANCH" ]]; then
  echo "ERROR: Could not detect default branch for remote '${DEFAULT_REMOTE}'." >&2
  exit 1
fi

# --- Check for uncommitted changes ---
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
  echo "ERROR: Working tree has uncommitted changes. Stash or commit them before running this script." >&2
  exit 1
fi

# --- Fetch latest from remote ---
if ! git fetch "$DEFAULT_REMOTE" "$DEFAULT_BRANCH" 2>/dev/null; then
  echo "WARNING: git fetch failed (network/auth issue). Continuing with local copy." >&2
fi

# --- Create or switch to branch ---
TICKET_LOWER=$(echo "$TICKET" | tr '[:upper:]' '[:lower:]')
BRANCH_NAME="${TICKET_LOWER}"

if git rev-parse --verify "$BRANCH_NAME" >/dev/null 2>&1; then
  echo "Branch '${BRANCH_NAME}' already exists — switching to it."
  git checkout "$BRANCH_NAME"
else
  echo "Creating branch '${BRANCH_NAME}' from '${DEFAULT_REMOTE}/${DEFAULT_BRANCH}'."
  git checkout -b "$BRANCH_NAME" "${DEFAULT_REMOTE}/${DEFAULT_BRANCH}"
fi

# --- Write output ---
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "$OUTPUT_FILE" <<EOF
# Branch Preparation

- **Branch**: \`${BRANCH_NAME}\`
- **Based on**: \`${DEFAULT_REMOTE}/${DEFAULT_BRANCH}\`
- **Created at**: ${TIMESTAMP}
EOF

echo "Branch prepared. Output written to ${OUTPUT_FILE}"
