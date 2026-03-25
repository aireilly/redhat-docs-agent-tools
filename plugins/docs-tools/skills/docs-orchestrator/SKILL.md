---
name: docs-orchestrator
description: Documentation workflow orchestrator. Reads the step list from .claude/docs-workflow.yaml (or the plugin default). Runs steps sequentially, manages progress state, handles iteration and confirmation gates. Claude is the orchestrator — the YAML is a step list, not a workflow engine. Supports both JIRA-driven and commit-driven workflows.
argument-hint: <ticket> [--workflow <name>] [--pr <url>]... [--mkdocs] [--draft] [--create-jira <PROJECT>] [--commits <repo-url> <sha1,sha2,...>] [--create-pr]
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, AskUserQuestion, WebSearch, WebFetch
---

# Docs Orchestrator

Claude is the orchestrator. The YAML is a step list. The hook is a safety net.

This skill teaches you how to run a documentation workflow pipeline. You read the step list from YAML, run each step skill sequentially, manage progress state via a JSON file, and handle iteration loops and confirmation gates.

## Pre-flight

Before starting, verify the environment:

```bash
# Source ~/.env if JIRA_AUTH_TOKEN is not set
if [[ -z "${JIRA_AUTH_TOKEN:-}" ]]; then
  set -a && source ~/.env 2>/dev/null && set +a
fi
```

1. If `JIRA_AUTH_TOKEN` is still unset → **STOP** and ask the user to set it in `~/.env` (skip this check in commit-driven mode — `JIRA_AUTH_TOKEN` is only needed when JIRA tickets are referenced)
2. Warn (don't stop) if `GITHUB_TOKEN` or `GITLAB_TOKEN` are unset (these are required in commit-driven mode)
3. Install hooks (safe to re-run):

```bash
bash scripts/setup-hooks.sh
```

## Parse arguments

- `$1` — Identifier (required). Either a JIRA ticket ID (e.g., `PROJ-123`) or a commit-derived identifier (e.g., `my-service/a1b2c3d-e4f5g6h`). If missing, STOP and ask the user.
- `--workflow <name>` — Use `.claude/docs-<name>.yaml` instead of `docs-workflow.yaml`
- `--pr <url>` — PR/MR URLs (repeatable, accumulated into a list)
- `--mkdocs` — Use Material for MkDocs format instead of AsciiDoc
- `--draft` — Write documentation to a staging area instead of directly into the repo. When set, the writing step uses DRAFT placement mode (no framework detection, no branch creation). Without this flag, UPDATE-IN-PLACE is the default
- `--create-jira <PROJECT>` — Create a linked JIRA ticket in the specified project
- `--commits <repo-url> <sha1,sha2,...>` — Commit-driven mode. The first value is the code repository URL, the second is a comma-separated list of commit SHAs. When present, uses `docs-commit-workflow.yaml` as default workflow (unless `--workflow` overrides). The identifier is auto-generated from the repo and SHAs if not provided as `$1`: `<repo-short-name>/<first-7chars>-<last-7chars>`
- `--create-pr` — Enable the PR/MR creation step. Maps to `when: create_pr` condition in the workflow YAML

## Load the step list

### 1. Determine the YAML file

- If `--workflow <name>` was specified → `.claude/docs-<name>.yaml`
- If `--commits` was specified (and no `--workflow`) → `.claude/docs-commit-workflow.yaml`
- Otherwise → `.claude/docs-workflow.yaml`
- If the selected file does not exist → use the plugin default at `skills/docs-orchestrator/defaults/docs-workflow.yaml` (JIRA mode) or `skills/docs-orchestrator/defaults/docs-commit-workflow.yaml` (commit mode)

### 2. Read the YAML

Read the YAML file and extract the ordered step list. Each step has: `name`, `skill`, `description`, optional `when`, and optional `inputs`.

### 3. Evaluate `when` conditions

- `when: create_jira_project` → run this step only if `--create-jira` was passed
- `when: create_pr` → run this step only if `--create-pr` was passed
- Steps with no `when` always run
- Steps that don't meet their `when` condition are marked `skipped` in the progress file

### 4. Validate the step list

All of the following must be true. If any check fails, **STOP** with a clear error:

- All step names are unique
- All `skill` references are fully qualified (`plugin:skill` format)
- Input dependencies are satisfied — for each step with `inputs`, every referenced step name must be present in the step list (unless it has a `when` condition that would skip it)

### Input dependencies

Steps declare their inputs as a list of upstream step names in the YAML:

```yaml
- name: writing
  skill: docs-tools:docs-workflow-writing
  inputs: [planning]

- name: create-jira
  skill: docs-tools:docs-workflow-create-jira
  when: create_jira_project
  inputs: [planning]
```

The orchestrator validates at load time that every step name in `inputs` exists in the step list. Step skills read their input data from the upstream step's output folder by convention (see below).

**Custom workflow validation**: If a step's `inputs` references a step that does not exist in the current YAML step list, fail at load time with an error (e.g., "Step 'writing' requires 'planning', but 'planning' is not in the step list").

## Output conventions

Every step writes to a predictable folder based on the ticket ID and step name:

```
.claude/docs/<ticket>/<step-name>/
```

The ticket ID is converted to **lowercase** for directory names (e.g., `PROJ-123` → `proj-123`).

### Folder structure

```
.claude/docs/proj-123/
  requirements/
    requirements.md
  planning/
    plan.md
  prepare-branch/
    branch-info.md
  writing/
    _index.md
    assembly_*.adoc (or docs/*.md for mkdocs)
    modules/
  technical-review/
    review.md
  style-review/
    review.md
  workflow/
    docs-workflow_proj-123.json
```

Each step skill knows its own output folder and writes there. Each step reads input from upstream step folders referenced in its `inputs` list. The orchestrator passes the base path `.claude/docs/<ticket>/` — step skills derive everything else by convention.

## Progress file

Claude writes the progress file directly using the Write tool. Create it after parsing arguments, before step 1. Update it after each step.

**Location**: `.claude/docs/<ticket>/workflow/<workflow-type>_<ticket>.json`

The `workflow_type` field and filename prefix match the YAML's `workflow.name`. This allows multiple workflow types to run against the same ticket without conflict.

### Schema

```json
{
  "workflow_type": "<workflow.name from YAML>",
  "ticket": "<IDENTIFIER>",
  "source_type": "jira",
  "base_path": ".claude/docs/<identifier>",
  "status": "in_progress",
  "created_at": "<ISO 8601>",
  "updated_at": "<ISO 8601>",
  "options": {
    "format": "adoc",
    "draft": false,
    "create_jira_project": null,
    "create_pr": false,
    "pr_urls": []
  },
  "step_order": ["requirements", "planning", "writing", ...],
  "steps": {
    "<step-name>": {
      "status": "pending",
      "output": null
    }
  }
}
```

For commit-driven workflows, include `source_type` and `source`:

```json
{
  "workflow_type": "docs-commit-workflow",
  "ticket": "my-service/a1b2c3d-e4f5g6h",
  "source_type": "commits",
  "source": {
    "repository": "https://github.com/org/repo",
    "commits": ["sha1", "sha2", "sha3"],
    "branch": "main"
  },
  "options": {
    "create_pr": true
  }
}
```

For JIRA-driven workflows, `source_type` defaults to `"jira"` (backward compatible — existing progress files without this field are treated as JIRA).

The `output` field records the step's output folder path (e.g., `.claude/docs/proj-123/writing/`) once completed.

### Status values

| Value | Meaning |
|---|---|
| `pending` | Not yet started |
| `in_progress` | Currently running |
| `completed` | Finished successfully |
| `failed` | Failed — needs retry |
| `skipped` | Conditional step not applicable |

### `step_order`

A top-level array listing steps in canonical order. This field exists so the Stop hook can determine step ordering without a hardcoded bash array. It **must** always be written by the orchestrator and kept in sync with the YAML step list.

## Check for existing work

Before starting, check for a progress file at `.claude/docs/<ticket>/workflow/<workflow-type>_<ticket>.json`.

**If a progress file exists:**

1. Read it and identify which steps have status `"completed"` or `"skipped"`
2. For each `"completed"` step, verify its output folder still exists on disk. If it has been deleted, reset that step to `"pending"` and reset all downstream dependent steps to `"pending"` as well
3. Resume from the first step with status `"pending"` or `"failed"`
4. Before running the resume step, validate its input dependencies are satisfied
5. Tell the user: "Found existing work for `<ticket>`. Resuming from `<step>`."
6. If the user provided additional flags on resume (e.g., `--create-jira`), update the progress file options accordingly

**If no progress file exists**, start from step 1 and create a new progress file.

## Running workflow steps

Run steps in the order defined by the YAML. For each step:

### Before the step

1. Validate input dependencies — for each step name in the step's YAML `inputs`, the referenced upstream step must have `status: "completed"` and a non-null `output` folder in the progress file. If any required input step did not complete, **fail the current step immediately** with a clear error (e.g., "Step 'writing' requires 'planning', but planning has status 'failed'")
2. Update the step's status to `"in_progress"` in the progress file

### Construct arguments

Build the args string for the step skill:

1. **Always**: `<identifier> --base-path <base_path>` — the identifier and the base output path
2. **From orchestrator context**: Step-specific args from parsed CLI flags:
   - `commit-analysis` (commit mode): `--repo <repo-url> --commits <sha1,sha2,...>`
   - `requirements` (JIRA mode): `[--pr <url>]...`
   - `requirements` (commit mode): `--commit-analysis <base_path>/commit-analysis/analysis.md`
   - `prepare-branch`: `[--draft]`
   - `writing`: `--format <adoc|mkdocs> [--draft]`
   - `style-review`: `--format <adoc|mkdocs>`
   - `create-jira`: `--project <PROJECT>`
   - `create-pr`: no additional args (reads branch info and plan from base path)

Step skills derive their own output folder and input folders from `--base-path` and step name conventions. No per-input flag wiring needed.

### Invoke the step skill

```
Skill: <step.skill>, args: "<constructed args>"
```

### After the step

1. Verify the output folder exists (for steps that produce files). If the expected output folder is missing, mark the step as `failed` in the progress file and **STOP**
2. Update the step's status to `"completed"` with the output folder path in the progress file
3. Update the progress file's `updated_at` timestamp

## Short-circuit on None impact (commit-driven only)

After the `commit-analysis` step completes, read the output file and check for `<!-- DOC_IMPACT: None -->`. If found:

1. Mark all remaining steps as `skipped` in the progress file
2. Set the workflow status to `completed`
3. Update the commit marker file (see "Commit marker update" below)
4. Report: "No documentation impact detected. Workflow complete."

This short-circuits before the heavier requirements step runs, saving time and cost when commits have no doc impact.

## Technical review iteration

The technical review step runs in a loop until confidence is acceptable or three iterations are exhausted:

1. Invoke `docs-tools:docs-workflow-tech-review` with the standard args
2. Read the output file and check for `Overall technical confidence: (HIGH|MEDIUM|LOW)`
   - If the confidence line is **missing** from the output, treat it as a step failure — mark the step `failed` and stop iteration
3. If `HIGH` → mark completed, proceed to next step
4. If `MEDIUM` or `LOW` and fewer than 3 iterations completed → run the fix skill:
   ```
   Skill: docs-tools:docs-workflow-writing, args: "<ticket> --base-path <base_path> --fix-from <base_path>/technical-review/review.md"
   ```
   Then re-run the reviewer (go to step 1)
5. After 3 iterations without reaching `HIGH`:
   - `MEDIUM` is acceptable — proceed with a warning that manual review is recommended
   - `LOW` after max iterations — ask the user whether to proceed or stop

## Completion

After all steps complete (or are skipped):

1. Update the progress file: `status → "completed"`
2. If commit-driven, update the commit marker (see "Commit marker update" below)
3. Display a summary:
   - List all output folders with paths
   - Note any warnings (tech review didn't reach `HIGH`, etc.)
   - Show JIRA URL if a ticket was created
   - Show PR/MR URL if a PR was created

## Commit marker update (commit-driven only)

On workflow completion (both None-impact short-circuit and full completion), update the commit marker file so the gate skill (`docs-workflow-commits-ready`) knows which commits have been processed.

**Marker file location**: `<base-path>/../.commit-markers/<repo-slug>.json`

The repo slug is derived from the repository URL: strip protocol, remove `.git` suffix, replace non-alphanumeric characters with hyphens, lowercase. For example: `https://github.com/org/repo` → `github-com-org-repo`.

**Marker content**:

```json
{
  "repository": "<repo-url>",
  "last_processed_sha": "<last-sha-from-batch>",
  "last_processed_at": "<ISO 8601>"
}
```

Create the `.commit-markers/` directory if it does not exist. Use the last SHA from the commit batch (the most recent commit) as the marker value.

## Resume behavior

### Same session

The progress file is already in context. Skip completed steps and continue from the first `pending` or `failed` step. The Stop hook ensures Claude doesn't stop prematurely.

### New session

User says: `"Resume docs workflow for PROJ-123"`

1. Invoke this skill with the ticket
2. Check for an existing progress file
3. Read it, skip completed steps, resume from first `pending` or `failed` step
4. Before running the resume step, **validate its input dependencies** — every required upstream step must have `status: "completed"` and a non-null `output` folder. If a dependency is `failed` or `pending`, re-run that dependency first
5. For each upstream dependency, verify the output folder still exists on disk. If an output folder was deleted, mark that step as `pending` and re-run it
6. The user can provide additional flags on resume (e.g., add `--create-jira`) — update the progress file options accordingly

### After failure

Same as new session. The progress file shows which steps completed and which failed. Walk back to the earliest incomplete dependency and resume from there.
