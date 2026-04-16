#!/usr/bin/env bash
# Build resolved arguments for the docs-workflow-writing skill.
#
# Handles argument parsing, mode determination, input validation,
# directory creation, and path computation.  Emits a JSON object
# on stdout that the SKILL.md dispatcher uses to select the right
# prompt template and invoke the docs-writer subagent.
#
# Usage:
#   build_writing_args.sh <ticket> --base-path <path> \
#       [--format adoc|mkdocs] [--draft] [--repo-path <path>] \
#       [--fix-from <path>]
#
# Requires: jq

set -euo pipefail

# --- Argument parsing ---
TICKET=""
BASE_PATH=""
FORMAT="adoc"
DRAFT=false
REPO_PATH=""
FIX_FROM=""

require_arg() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" || "$val" == -* ]]; then
    echo "ERROR: ${opt} requires a value." >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-path)
      require_arg "$1" "${2:-}"
      BASE_PATH="$2"
      shift 2
      ;;
    --format)
      require_arg "$1" "${2:-}"
      FORMAT="$2"
      shift 2
      ;;
    --draft)
      DRAFT=true
      shift
      ;;
    --repo-path)
      require_arg "$1" "${2:-}"
      REPO_PATH="$2"
      shift 2
      ;;
    --fix-from)
      require_arg "$1" "${2:-}"
      FIX_FROM="$2"
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

# --- Validate required args ---
if [[ -z "$TICKET" ]]; then
  echo "ERROR: Ticket ID is required as the first positional argument." >&2
  exit 1
fi

if [[ -z "$BASE_PATH" ]]; then
  echo "ERROR: --base-path is required." >&2
  exit 1
fi

if [[ "$FORMAT" != "adoc" && "$FORMAT" != "mkdocs" ]]; then
  echo "ERROR: --format must be 'adoc' or 'mkdocs', got '${FORMAT}'." >&2
  exit 1
fi

# --- Compute paths ---
INPUT_FILE="${BASE_PATH}/planning/plan.md"
OUTPUT_DIR="${BASE_PATH}/writing"
OUTPUT_FILE="${OUTPUT_DIR}/_index.md"

# --- Determine mode ---
MODE=""
if [[ -n "$FIX_FROM" ]]; then
  MODE="fix"
elif [[ -n "$REPO_PATH" ]]; then
  MODE="update-in-place"
  if [[ "$DRAFT" == true ]]; then
    echo "WARNING: --draft ignored because --repo-path takes precedence." >&2
  fi
elif [[ "$DRAFT" == true ]]; then
  MODE="draft"
else
  MODE="update-in-place"
fi

# --- Validate inputs ---
if [[ "$MODE" != "fix" && ! -f "$INPUT_FILE" ]]; then
  echo "ERROR: Plan file not found: ${INPUT_FILE}" >&2
  exit 1
fi

if [[ "$MODE" == "fix" && ! -f "$FIX_FROM" ]]; then
  echo "ERROR: Review file not found: ${FIX_FROM}" >&2
  exit 1
fi

if [[ -n "$REPO_PATH" && ! -d "$REPO_PATH" ]]; then
  echo "ERROR: Repo path not found or not a directory: ${REPO_PATH}" >&2
  exit 1
fi

# --- Create output directory ---
mkdir -p "$OUTPUT_DIR"

# --- Determine verify_output ---
if [[ "$MODE" == "fix" ]]; then
  VERIFY=false
else
  VERIFY=true
fi

# --- Emit JSON ---
jq -n \
  --arg mode       "$MODE" \
  --arg ticket     "$TICKET" \
  --arg format     "$FORMAT" \
  --arg input_file "$INPUT_FILE" \
  --arg output_dir "$OUTPUT_DIR" \
  --arg output_file "$OUTPUT_FILE" \
  --arg repo_path  "$REPO_PATH" \
  --arg fix_from   "$FIX_FROM" \
  --argjson verify "$VERIFY" \
  '{
    mode:          $mode,
    ticket:        $ticket,
    format:        $format,
    input_file:    $input_file,
    output_dir:    $output_dir,
    output_file:   $output_file,
    repo_path:     (if $repo_path == "" then null else $repo_path end),
    fix_from:      (if $fix_from == "" then null else $fix_from end),
    verify_output: $verify
  }'
