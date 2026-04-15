#!/usr/bin/env bash
# Discover tickets for batch processing.
# Queries JIRA for both ambient-docs-ready and ambient-docs-processing labels,
# cross-references batch-progress.json to filter out already-completed tickets.
#
# Usage: bash batch-find-tickets.sh [--jira-script <path>] [--jira-project <PROJECT>]
#
# Output (JSON to stdout):
#   {
#     "ready": ["PROJ-1", "PROJ-2"],
#     "orphaned": ["PROJ-3"],
#     "skipped": ["PROJ-4"],
#     "all": ["PROJ-1", "PROJ-2", "PROJ-3"]
#   }
#
# - ready: tickets with ambient-docs-ready (need label swap in step 1.5)
# - orphaned: tickets with ambient-docs-processing, not in completed/failed (skip label swap)
# - skipped: tickets with ambient-docs-processing, already in completed/failed (stale label)
# - all: ready + orphaned (the tickets to process)
#
# Dependencies: python3
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"

# --- Argument parsing ---
JIRA_SCRIPT=""
JIRA_PROJECT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --jira-script) JIRA_SCRIPT="$2"; shift 2 ;;
    --jira-project) JIRA_PROJECT="$2"; shift 2 ;;
    -*) echo "ERROR: Unknown option: $1" >&2; exit 1 ;;
    *) echo "ERROR: Unexpected argument: $1" >&2; exit 1 ;;
  esac
done

# Default jira_reader.py path: resolve from repo root via .claude/skills/ symlinks
if [[ -z "$JIRA_SCRIPT" ]]; then
  JIRA_SCRIPT="${REPO_ROOT}/.claude/skills/jira-reader/scripts/jira_reader.py"
fi

if [[ ! -f "$JIRA_SCRIPT" ]]; then
  echo "ERROR: JIRA script not found at ${JIRA_SCRIPT}" >&2
  echo "Searched default: \${REPO_ROOT}/.claude/skills/jira-reader/scripts/jira_reader.py" >&2
  echo "Override with: --jira-script <path>" >&2
  exit 1
fi

# --- Build JQL base ---
PROJECT_FILTER=""
if [[ -n "$JIRA_PROJECT" ]]; then
  PROJECT_FILTER="project = ${JIRA_PROJECT} AND "
fi

# --- Query for ready tickets ---
READY_LABEL="${DOCS_TRIGGER_LABEL:-ambient-docs-ready}"
PROCESSING_LABEL="${DOCS_PROCESSING_LABEL:-ambient-docs-processing}"

READY_JQL="${PROJECT_FILTER}labels = \"${READY_LABEL}\""
READY_JSON="$(python3 "$JIRA_SCRIPT" --jql "$READY_JQL")" || {
  echo "WARNING: JIRA query for '${READY_LABEL}' failed. Treating as empty result set." >&2
  READY_JSON="[]"
}

# --- Query for processing tickets (potential orphans) ---
PROCESSING_JQL="${PROJECT_FILTER}labels = \"${PROCESSING_LABEL}\""
PROCESSING_JSON="$(python3 "$JIRA_SCRIPT" --jql "$PROCESSING_JQL")" || {
  echo "WARNING: JIRA query for '${PROCESSING_LABEL}' failed. Treating as empty result set." >&2
  PROCESSING_JSON="[]"
}

# --- Cross-reference with batch-progress.json ---
PROGRESS_FILE="${REPO_ROOT}/artifacts/batch-progress.json"

python3 -c "
import json, sys

def extract_keys(raw_json):
    \"\"\"Extract issue keys from jira_reader.py output.
    Handles both single-object and array output formats.\"\"\"
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return []
    # jira_reader.py outputs a single dict when there's exactly 1 result
    if isinstance(data, dict):
        data = [data]
    if isinstance(data, list):
        return [t.get('issue_key', t.get('key', '')) for t in data
                if isinstance(t, dict) and not t.get('error')]
    return []

# Parse ready tickets
ready_tickets = extract_keys(sys.argv[1])

# Parse processing tickets
processing_tickets = extract_keys(sys.argv[2])

# Load progress file if it exists
completed = set()
failed = set()
progress_path = sys.argv[3]
try:
    with open(progress_path) as f:
        progress = json.load(f)
    completed = set(progress.get('completed_tickets', []))
    failed = set(progress.get('failed_tickets', []))
except (FileNotFoundError, json.JSONDecodeError):
    pass

already_done = completed | failed

# Classify processing tickets
orphaned = []
skipped = []
for ticket in processing_tickets:
    if ticket in already_done:
        skipped.append(ticket)
    else:
        orphaned.append(ticket)

# Remove any ready tickets that are already done (defensive)
ready = [t for t in ready_tickets if t not in already_done]

# Merge: all = ready + orphaned
all_tickets = ready + orphaned

print(json.dumps({
    'ready': ready,
    'orphaned': orphaned,
    'skipped': skipped,
    'all': all_tickets
}, indent=2))
" "$READY_JSON" "$PROCESSING_JSON" "$PROGRESS_FILE"
