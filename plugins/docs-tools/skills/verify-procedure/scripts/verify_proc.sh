#!/usr/bin/env bash
# verify_proc.sh — Thin executor for procedure verification.
#
# Claude handles AsciiDoc parsing and intent classification.
# This script only does what requires a shell: execute commands,
# validate YAML against a live cluster, save files, and clean up.
#
# Usage:
#   verify_proc.sh init                          → create workdir, detect CLI tool
#   verify_proc.sh execute <label> <command>     → run a shell command in workdir
#   verify_proc.sh validate-yaml <label> [file]  → validate YAML from stdin (syntax + dry-run)
#   verify_proc.sh validate-json <label>         → validate JSON from stdin
#   verify_proc.sh save-file <label> <path>      → save stdin content to workdir/<path>
#   verify_proc.sh check-connection              → verify cluster connectivity
#   verify_proc.sh cleanup                       → delete tracked resources + workdir
#   verify_proc.sh summary                       → print pass/fail summary
#
# All output is structured for Claude to parse:
#   [PASS]    <label> <message>
#   [FAIL]    <label> <message>
#   [SKIP]    <label> <message>
#   [INFO]    <message>
#   [WORKDIR] <path>
#   [CLI]     <tool>
#
# Session isolation: init creates a unique session ID. All temp files
# include this ID so concurrent runs don't interfere.

set -o pipefail

TIMEOUT="${VERIFY_TIMEOUT:-120}"

# Session file stores the workdir path; its name is the session anchor.
# init writes it; all other commands read it.
SESSION_FILE="/tmp/verify-proc-session"

# --- Helpers ---

detect_cli() {
  if command -v oc &>/dev/null; then
    echo "oc"
  elif command -v kubectl &>/dev/null; then
    echo "kubectl"
  else
    echo ""
  fi
}

# Derive all temp file paths from the workdir path (set during init).
# This ensures concurrent sessions use separate files.
session_paths() {
  local workdir="$1"
  local sid="${workdir##*-}"  # extract suffix from /tmp/verify-proc-XXXXXX
  TRACKED_FILE="/tmp/verify-proc-tracked-${sid}"
  COUNTER_FILE="/tmp/verify-proc-counters-${sid}"
  STDERR_FILE="/tmp/verify-proc-stderr-${sid}"
}

load_session() {
  if [[ ! -f "$SESSION_FILE" ]]; then
    echo "[FAIL] session No active session — run init first"
    exit 1
  fi
  WORKDIR=$(cat "$SESSION_FILE")
  if [[ -z "$WORKDIR" || ! -d "$WORKDIR" ]]; then
    echo "[FAIL] session Working directory missing — run init first"
    exit 1
  fi
  session_paths "$WORKDIR"
}

read_counter() {
  local name="$1"
  local file="$2"
  if [[ -f "$file" ]]; then
    grep "^${name}=" "$file" 2>/dev/null | head -1 | cut -d= -f2 | grep -E '^[0-9]+$' || echo 0
  else
    echo 0
  fi
}

save_counters() {
  local pass_count="$1"
  local fail_count="$2"
  printf 'PASS_COUNT=%d\nFAIL_COUNT=%d\n' "$pass_count" "$fail_count" > "$COUNTER_FILE"
}

pass() {
  local label="$1"; shift
  echo "[PASS] $label $*"
  local p f
  p=$(read_counter PASS_COUNT "$COUNTER_FILE")
  f=$(read_counter FAIL_COUNT "$COUNTER_FILE")
  save_counters $((p + 1)) "$f"
}

fail() {
  local label="$1"; shift
  echo "[FAIL] $label $*"
  local p f
  p=$(read_counter PASS_COUNT "$COUNTER_FILE")
  f=$(read_counter FAIL_COUNT "$COUNTER_FILE")
  save_counters "$p" $((f + 1))
}

# --- Commands ---

cmd_init() {
  WORKDIR=$(mktemp -d /tmp/verify-proc-XXXXXX)
  echo "$WORKDIR" > "$SESSION_FILE"
  session_paths "$WORKDIR"
  : > "$TRACKED_FILE"
  save_counters 0 0
  echo "[WORKDIR] $WORKDIR"

  local cli
  cli=$(detect_cli)
  if [[ -n "$cli" ]]; then
    echo "[CLI] $cli"
  else
    echo "[INFO] No oc or kubectl found"
  fi
}

cmd_check_connection() {
  local cli
  cli=$(detect_cli)
  if [[ -z "$cli" ]]; then
    echo "[FAIL] connection No oc or kubectl found"
    return 1
  fi

  local out
  if out=$($cli whoami 2>&1); then
    echo "[PASS] connection Logged in as: $out"
    echo "[INFO] Cluster: $($cli cluster-info 2>/dev/null | head -1 || $cli whoami --show-server 2>/dev/null)"
  else
    echo "[FAIL] connection Not logged in: $out"
    return 1
  fi
}

cmd_execute() {
  local label="$1"
  local command="$2"
  load_session

  echo "[INFO] Executing: ${command:0:200}"

  local stdout stderr exit_code
  stdout=$(cd "$WORKDIR" && timeout "$TIMEOUT" bash -c "$command" 2>"$STDERR_FILE" <<< "" )
  exit_code=$?
  stderr=$(cat "$STDERR_FILE" 2>/dev/null)
  rm -f "$STDERR_FILE"

  if [[ $exit_code -eq 124 ]]; then
    fail "$label" "Command timed out after ${TIMEOUT}s"
    return 1
  fi

  if [[ $exit_code -eq 0 ]]; then
    pass "$label" "executed successfully"
    # Track created K8s resources from stdout
    while IFS= read -r line; do
      if [[ "$line" =~ ^([a-z]+/[^ ]+)\ created$ ]]; then
        echo "resource:${BASH_REMATCH[1]}" >> "$TRACKED_FILE"
      fi
    done <<< "$stdout"
    # Track oc/kubectl apply/create -f commands
    if [[ "$command" =~ (oc|kubectl)[[:space:]]+(create|apply)[[:space:]]+-f[[:space:]]+([^[:space:]]+) ]]; then
      local file="${BASH_REMATCH[3]}"
      local filepath
      if [[ "$file" = /* ]]; then
        filepath="$file"
      else
        filepath="$WORKDIR/$file"
      fi
      if [[ -f "$filepath" ]]; then
        echo "file:$(detect_cli):$filepath" >> "$TRACKED_FILE"
      fi
    fi
    if [[ -n "$stdout" ]]; then
      echo "[OUTPUT] $stdout"
    fi
  else
    fail "$label" "${stderr:-exit code $exit_code}"
    if [[ -n "$stdout" ]]; then
      echo "[OUTPUT] $stdout"
    fi
  fi
}

cmd_validate_yaml() {
  local label="$1"
  local save_as="$2"
  local content
  content=$(cat)
  load_session

  # Syntax check with python (more portable than ruby for YAML)
  if ! printf '%s' "$content" | python3 -c "
import sys, yaml
try:
    list(yaml.safe_load_all(sys.stdin))
except yaml.YAMLError as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
" 2>"$STDERR_FILE"; then
    local err
    err=$(cat "$STDERR_FILE")
    rm -f "$STDERR_FILE"
    fail "$label" "YAML syntax error: $err"
    return 1
  fi
  rm -f "$STDERR_FILE"

  pass "$label" "YAML syntax valid"

  # Save to workdir if requested
  if [[ -n "$save_as" && -n "$WORKDIR" ]]; then
    # Block absolute paths
    if [[ "$save_as" = /* ]]; then
      echo "[INFO] Path $save_as — validated but not written to filesystem"
    else
      local dest="$WORKDIR/$save_as"
      mkdir -p "$(dirname "$dest")"
      printf '%s\n' "$content" > "$dest"
      echo "[INFO] Saved to $dest"
    fi
  fi

  # K8s dry-run if it looks like a resource
  if printf '%s' "$content" | grep -q "apiVersion:"; then
    local cli
    cli=$(detect_cli)
    if [[ -z "$cli" ]]; then
      echo "[SKIP] $label No CLI tool — dry-run skipped"
      return 0
    fi

    local tmpfile
    tmpfile=$(mktemp /tmp/verify-yaml-XXXXXX.yaml)
    printf '%s\n' "$content" > "$tmpfile"

    local dr_stderr
    if dr_stderr=$($cli apply -f "$tmpfile" --dry-run=client 2>&1 >/dev/null); then
      pass "${label}-dryrun" "Resource dry-run passed"
    elif printf '%s' "$dr_stderr" | grep -qE "Unable to connect|no such host|connection refused"; then
      echo "[SKIP] ${label}-dryrun No cluster connection"
    else
      fail "${label}-dryrun" "Resource validation: $(printf '%s' "$dr_stderr" | head -1)"
    fi
    rm -f "$tmpfile"
  fi
}

cmd_validate_json() {
  local label="$1"
  local content
  content=$(cat)
  load_session

  if printf '%s' "$content" | python3 -c "import sys,json; json.load(sys.stdin)" 2>"$STDERR_FILE"; then
    rm -f "$STDERR_FILE"
    pass "$label" "JSON syntax valid"
  else
    local err
    err=$(cat "$STDERR_FILE")
    rm -f "$STDERR_FILE"
    fail "$label" "JSON syntax error: $err"
  fi
}

cmd_save_file() {
  local label="$1"
  local path="$2"
  local content
  content=$(cat)
  load_session

  if [[ "$path" = /* ]]; then
    echo "[INFO] Path $path — content recorded but not written to filesystem"
    pass "$label" "Content recorded (absolute path)"
    return 0
  fi

  local dest="$WORKDIR/$path"
  mkdir -p "$(dirname "$dest")"
  printf '%s\n' "$content" > "$dest"
  pass "$label" "Saved to $dest"
}

cmd_cleanup() {
  if [[ ! -f "$SESSION_FILE" ]]; then
    echo "[INFO] No active session to clean up"
    return 0
  fi

  WORKDIR=$(cat "$SESSION_FILE")
  session_paths "$WORKDIR"

  if [[ -f "$TRACKED_FILE" ]]; then
    local cli
    cli=$(detect_cli)

    # Process tracked resources in reverse order
    tac "$TRACKED_FILE" | while IFS= read -r entry; do
      case "$entry" in
        file:*:*)
          local tool file
          tool=$(echo "$entry" | cut -d: -f2)
          file=$(echo "$entry" | cut -d: -f3-)
          echo "[INFO] Deleting resources from: $file"
          if $tool delete -f "$file" --ignore-not-found 2>/dev/null; then
            echo "[CLEANED] $file"
          else
            echo "[WARN] Failed to clean: $file"
          fi
          ;;
        resource:*)
          local resource="${entry#resource:}"
          local tool="${cli:-oc}"
          echo "[INFO] Deleting: $resource"
          if $tool delete "$resource" --ignore-not-found 2>/dev/null; then
            echo "[CLEANED] $resource"
          else
            echo "[WARN] Failed to clean: $resource"
          fi
          ;;
      esac
    done
  else
    echo "[INFO] No tracked resources to clean up"
  fi

  # Clean up workdir and all session temp files
  if [[ -n "$WORKDIR" && -d "$WORKDIR" ]]; then
    rm -rf "$WORKDIR"
    echo "[CLEANED] Removed working directory: $WORKDIR"
  fi
  rm -f "$SESSION_FILE" "$TRACKED_FILE" "$COUNTER_FILE" "$STDERR_FILE"
}

cmd_summary() {
  if [[ ! -f "$SESSION_FILE" ]]; then
    echo "[INFO] No active session"
    return 0
  fi
  WORKDIR=$(cat "$SESSION_FILE")
  session_paths "$WORKDIR"

  local pass_count fail_count total
  pass_count=$(read_counter PASS_COUNT "$COUNTER_FILE")
  fail_count=$(read_counter FAIL_COUNT "$COUNTER_FILE")
  total=$((pass_count + fail_count))

  echo "============================================================"
  echo "FINAL SUMMARY"
  echo "============================================================"
  echo "Total executable steps: $total"
  echo "Passed: $pass_count"
  echo "Failed: $fail_count"
  echo "============================================================"
  if [[ $fail_count -eq 0 ]]; then
    echo "All steps PASSED"
  else
    echo "Some steps FAILED"
  fi
  echo "============================================================"
}

# --- Main dispatch ---

case "${1:-}" in
  init)             cmd_init ;;
  check-connection) cmd_check_connection ;;
  execute)          cmd_execute "$2" "$3" ;;
  validate-yaml)    cmd_validate_yaml "$2" "${3:-}" ;;
  validate-json)    cmd_validate_json "$2" ;;
  save-file)        cmd_save_file "$2" "$3" ;;
  cleanup)          cmd_cleanup ;;
  summary)          cmd_summary ;;
  *)
    echo "Usage: verify_proc.sh {init|check-connection|execute|validate-yaml|validate-json|save-file|cleanup|summary}"
    echo ""
    echo "Commands:"
    echo "  init                          Create workdir and detect CLI tool"
    echo "  check-connection              Verify cluster connectivity"
    echo "  execute <label> <command>     Run a shell command in workdir"
    echo "  validate-yaml <label> [file]  Validate YAML from stdin (+ dry-run)"
    echo "  validate-json <label>         Validate JSON from stdin"
    echo "  save-file <label> <path>      Save stdin to workdir/<path>"
    echo "  cleanup                       Delete tracked resources + workdir"
    echo "  summary                       Print pass/fail summary"
    exit 1
    ;;
esac
