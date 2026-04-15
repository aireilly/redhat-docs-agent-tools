# Batch Controller

Autonomous batch processor for the Ambient Code Platform. Scrapes JIRA for labeled tickets and runs each through the documentation pipeline.

See [reference.md](reference.md) for JSON schemas, MR/PR creation details, config variables, and batch summary format.

## Path safety

Shell state does not persist between Bash tool calls. Every bash block that calls adapter scripts MUST resolve the repo root first:

```bash
AGENT_ROOT="$(cd "${CLAUDE_SKILL_DIR}" && git rev-parse --show-toplevel)"
```

Then use `"${AGENT_ROOT}/adapters/ambient/..."` for all script paths. This prevents "No such file or directory" errors when CWD has shifted (e.g., after the orchestrator runs in a cloned docs repo). Using `${CLAUDE_SKILL_DIR}` ensures resolution from the agent-tools repo, not whichever repo CWD happens to be in.

## Step 0: Environment setup

Read the ACP guidelines, then run setup:

```
Read adapters/ambient/CLAUDE.md
```

If the file cannot be read, STOP and report the error.

```bash
AGENT_ROOT="$(cd "${CLAUDE_SKILL_DIR}" && git rev-parse --show-toplevel)"
bash "${AGENT_ROOT}/adapters/ambient/setup.sh"
source ~/.env 2>/dev/null
```

If setup fails, run `batch-progress.sh abort` and stop the session.

## Step 1: Discover tickets

```bash
AGENT_ROOT="$(cd "${CLAUDE_SKILL_DIR}" && git rev-parse --show-toplevel)"
TICKETS_JSON="$(bash "${AGENT_ROOT}/adapters/ambient/scripts/batch-find-tickets.sh" \
  ${DOCS_JIRA_PROJECT:+--jira-project "$DOCS_JIRA_PROJECT"})"
```

This script queries JIRA for both `ambient-docs-ready` and `ambient-docs-processing` labels, then cross-references `batch-progress.json` to filter out already-completed tickets. It returns JSON with four lists: `ready`, `orphaned`, `skipped`, and `all`.

If `all` is empty, write a batch summary, run `batch-progress.sh finish`, and end the session.

## Step 1.5: Claim tickets

For tickets in the `ready` list, swap labels to prevent double-processing:

```bash
python3 ${CLAUDE_SKILL_DIR}/../jira-writer/scripts/jira_writer.py \
  --issue <TICKET> \
  --labels-remove ambient-docs-ready \
  --labels-add ambient-docs-processing
```

Skip the label swap for tickets in the `orphaned` list — they already have `ambient-docs-processing` from a previous session that crashed or was interrupted.

Run per-ticket for error isolation. If a claim fails, skip that ticket. This step must complete for all tickets before processing begins.

After claiming, register all tickets (from the `all` list) with the progress tracker:

```bash
AGENT_ROOT="$(cd "${CLAUDE_SKILL_DIR}" && git rev-parse --show-toplevel)"
bash "${AGENT_ROOT}/adapters/ambient/scripts/batch-progress.sh" init <TICKET-1> <TICKET-2> ...
```

## Batch progress tracking

`setup.sh` creates `artifacts/batch-progress.json` with `status: "in_progress"` at boot. The stop hook **blocks Claude from stopping** until the batch is explicitly finished. Call `batch-progress.sh` at each pipeline transition:

| Command | When |
|---------|------|
| `init <tickets...>` | After claiming tickets (Step 1.5) |
| `step <N>` | At each sub-step (2a–2e) |
| `ticket-done` | After a ticket succeeds |
| `ticket-failed` | After a ticket fails |
| `finish` | After writing batch summary (Step 3) |
| `abort` | Fatal error — end session early |

## Step 2: Process each ticket

For each claimed ticket, run steps 2a–2e sequentially.

### 2a. Resolve and clone target repo

```bash
AGENT_ROOT="$(cd "${CLAUDE_SKILL_DIR}" && git rev-parse --show-toplevel)"
bash "${AGENT_ROOT}/adapters/ambient/scripts/batch-progress.sh" step 2a
bash "${AGENT_ROOT}/adapters/ambient/scripts/repo-setup.sh" <TICKET-KEY>
```

Read `artifacts/<ticket>/repo-info.json` for `format`, `repo_url`, `clone_path`, and `platform`.

### 2b. Invoke the orchestrator

```bash
AGENT_ROOT="$(cd "${CLAUDE_SKILL_DIR}" && git rev-parse --show-toplevel)"
bash "${AGENT_ROOT}/adapters/ambient/scripts/batch-progress.sh" step 2b
```

Resolve orchestrator flags from `repo-info.json`:

```bash
AGENT_ROOT="$(cd "${CLAUDE_SKILL_DIR}" && git rev-parse --show-toplevel)"
REPO_FLAGS="$(bash "${AGENT_ROOT}/adapters/ambient/scripts/resolve-repo-context.sh" "<TICKET-KEY>")"
```

Then invoke the orchestrator with the resolved flags:

```
Skill: docs-tools:docs-orchestrator, args: "<TICKET-KEY> --workflow acp ${REPO_FLAGS}"
```

The orchestrator runs the full pipeline including commit and MR/PR creation (handled by the `commit` and `create-mr` workflow steps).

### 2c. Record the result

```bash
AGENT_ROOT="$(cd "${CLAUDE_SKILL_DIR}" && git rev-parse --show-toplevel)"
bash "${AGENT_ROOT}/adapters/ambient/scripts/batch-progress.sh" step 2c
```

Read `artifacts/<ticket>/create-mr/mr-info.json` for the MR/PR URL (if created by the orchestrator's `create-mr` step). Track ticket key, status, MR/PR URL, and any error messages.

### 2d. Update JIRA labels

```bash
AGENT_ROOT="$(cd "${CLAUDE_SKILL_DIR}" && git rev-parse --show-toplevel)"
bash "${AGENT_ROOT}/adapters/ambient/scripts/batch-progress.sh" step 2d
```

On success: `--labels-remove ambient-docs-processing --labels-add ambient-docs-generated`
On failure: `--labels-remove ambient-docs-processing --labels-add ambient-docs-failed`

```bash
python3 ${CLAUDE_SKILL_DIR}/../jira-writer/scripts/jira_writer.py \
  --issue <TICKET> --labels-remove ambient-docs-processing --labels-add <LABEL>
```

If the label update fails, log the error and continue.

### 2e. Continue to the next ticket

```bash
AGENT_ROOT="$(cd "${CLAUDE_SKILL_DIR}" && git rev-parse --show-toplevel)"
bash "${AGENT_ROOT}/adapters/ambient/scripts/batch-progress.sh" ticket-done   # or ticket-failed
```

Do not stop between tickets.

## Step 3: Write batch summary

Write `artifacts/batch-summary.md` (see [reference.md](reference.md) for format), then release the stop hook:

```bash
AGENT_ROOT="$(cd "${CLAUDE_SKILL_DIR}" && git rev-parse --show-toplevel)"
bash "${AGENT_ROOT}/adapters/ambient/scripts/batch-progress.sh" finish
```

## Error handling

- **JIRA access fails** (Step 1): Write error summary, run `batch-progress.sh abort`, stop.
- **Label claim fails** (Step 1.5): Skip that ticket — another session likely claimed it.
- **Single ticket fails** (Step 2): Log error, update label to failed, continue to next ticket.
- **Label update fails** (Step 2d): Log warning, continue.
- **Session dies mid-processing**: Tickets retain `ambient-docs-processing`. The next batch session will detect these as orphaned via `batch-find-tickets.sh` and resume processing automatically.
- **No tickets found**: Write summary noting zero tickets, run `batch-progress.sh finish`, end session.
