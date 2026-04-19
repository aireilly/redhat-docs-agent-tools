---
name: docs-orchestrator
description: Documentation workflow orchestrator. Reads the step list from .claude/docs-workflow.yaml (or the plugin default). Runs steps sequentially, manages progress state, handles iteration and confirmation gates. Claude is the orchestrator — the YAML is a step list, not a workflow engine.

argument-hint: <ticket> [--workflow <name>] [--pr <url>]... [--repo <url-or-path>] [--mkdocs] [--draft] [--repo-path <path>] [--create-jira <PROJECT>]

allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, AskUserQuestion
---

# Docs Orchestrator

Claude is the orchestrator. The YAML is a step list. The hook is a safety net.

This skill teaches you how to run a documentation workflow pipeline. You read the step list from YAML, run each step skill sequentially, manage progress state via a JSON file, and handle iteration loops and confirmation gates.

## Pre-flight

Check if setup has already been completed by an upstream script (e.g., ACP's `setup.sh`):

```bash
if [[ -f "artifacts/.setup-complete" ]]; then
  echo "Setup already completed (sentinel found). Skipping pre-flight checks."
fi
```

If the sentinel file exists, skip directly to **Parse arguments**. Otherwise, run the full pre-flight:

```bash
# Source ~/.env if JIRA_API_TOKEN is not set
if [[ -z "${JIRA_API_TOKEN:-}" ]]; then
  set -a && source ~/.env 2>/dev/null && set +a
fi
```

1. If `JIRA_API_TOKEN` is still unset:
   - In interactive mode: **STOP** and ask the user to set it in `~/.env`
   - In headless mode (no user interaction available, e.g., ACP): log a warning and continue — agents will use `~/.env` credentials for JIRA access (populated by `setup.sh`)
2. Warn (don't stop) if `GITHUB_TOKEN` or `GITLAB_TOKEN` are unset
3. Check that `uv` is available (needed by the code-evidence step to manage the `code-finder` dependency):
   ```bash
   command -v uv >/dev/null 2>&1
   ```
   If not found, **warn**: "uv is not installed. Code evidence retrieval requires uv. Install with: brew install uv (macOS) or see https://docs.astral.sh/uv/getting-started/installation/"
   This is a warning, not a blocker — the code-evidence step is conditional and may be skipped if no source repo is provided.
4. Install hooks (safe to re-run):

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/setup-hooks.sh
```

## Parse arguments

- `$1` — JIRA ticket ID (required). If missing, STOP and ask the user.
- `--workflow <name>` — Use `.claude/docs-<name>.yaml` instead of `docs-workflow.yaml`
- `--pr <url>` — PR/MR URLs (repeatable, accumulated into a list)
- `--mkdocs` — Use Material for MkDocs format instead of AsciiDoc
- `--draft` — Write documentation to a staging area instead of directly into the repo. When set, the writing step uses DRAFT placement mode (no framework detection, no branch creation). Without this flag, UPDATE-IN-PLACE is the default

- `--repo-path <path>` — Target repository for UPDATE-IN-PLACE mode. The docs-writer agent explores this directory for framework detection and writes files there, instead of writing to the repository at the current working directory. **Precedence**: if both `--repo-path` and `--draft` are passed, `--repo-path` wins — log a warning and ignore `--draft`
- `--repo <url-or-path>` — Source code repository. Can be a local path or a remote URL (https://, git@, ssh://). When provided without `--pr`, enables repo-driven documentation mode where the entire repo (or scoped subdirectories) is the subject matter. When provided alongside `--pr`, the PR branch is checked out within the provided repo.
- `--create-jira <PROJECT>` — Create a linked JIRA ticket in the specified project

## Resolve source repository

After parsing arguments and before running steps, resolve the source code repository if one is configured. This makes the repo available to all downstream steps that need it (requirements, code-evidence, writing).

All clone, verify, PR-resolution, and source.yaml logic is handled by the `resolve_source.py` script. The orchestrator calls the script and acts on the JSON result.

### Pre-flight resolution

Run the script with whatever source information is available from CLI args:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/resolve_source.py \
  --base-path <base_path> \
  [--repo <url-or-path>] \
  [--pr <url>]...
```

The script checks sources in priority order:

1. **CLI `--repo` flag** — clone or verify the path
2. **Per-ticket `source.yaml`** — read and apply existing config
3. **PR-derived** — resolve repo URL and branch from `--pr` via `gh pr view`
4. **No source** — exit code 2, defer resolution until after requirements

The script outputs JSON to stdout:

```json
{
  "status": "resolved",
  "repo_path": ".claude/docs/proj-123/code-repo",
  "repo_url": "https://github.com/org/operator",
  "ref": "pr-branch-name",
  "scope": null
}
```

### Handle the result

| Exit code | `status` | Action |
|---|---|---|
| 0 | `resolved` | Set `has_source_repo = true`. Record `options.source` in the progress file from the JSON fields (`repo_path`, `repo_url`, `ref`, `scope`) |
| 1 | `error` | **STOP** with the error `message` from the JSON |
| 2 | `no_source` | Mark steps with `when: has_source_repo` as `deferred`. Source resolution will be retried after requirements (see [Post-requirements source resolution](#post-requirements-source-resolution)) |

If `discovered_repos` is present in the result (multiple repos found during scan), log which repo was auto-selected and list the others.

### Per-ticket source config schema

Writers can create `<base-path>/source.yaml` before starting a workflow to pre-configure the source repo and scope. The script also writes this file after a successful clone so that resume picks it up automatically.

```yaml
# .claude/docs/<ticket>/source.yaml
repo: https://github.com/org/operator   # URL or local path (required)
ref: main                                # branch, tag, or commit (default: HEAD)
scope:
  include:                               # glob patterns — what to index and search
    - "src/controllers/**"
    - "pkg/api/v1/**"
    - "README.md"
  exclude:                               # glob patterns — what to skip
    - "**/vendor/**"
    - "**/testdata/**"
    - "**/*_test.go"
```

All fields except `repo` are optional. If `scope` is omitted, the entire repository is in scope.

## Load the step list

### 1. Determine the YAML file

- If `--workflow <name>` was specified → `.claude/docs-<name>.yaml`
- Otherwise → `.claude/docs-workflow.yaml`
- If neither exists → use the plugin default at `skills/docs-orchestrator/defaults/docs-workflow.yaml`

### 2. Read the YAML

Read the YAML file and extract the ordered step list. Each step has: `name`, `skill`, `description`, optional `when`, and optional `inputs`.

### 3. Evaluate `when` conditions

- `when: create_jira_project` → run this step only if `--create-jira` was passed
- `when: has_source_repo` → evaluation depends on timing:
  - If a source repo was already resolved pre-flight (via `--repo`, `--pr`, or `source.yaml`) → step runs normally (`pending`)
  - If no source is resolved yet but post-requirements discovery is possible (case 4 above) → mark the step `deferred` (not `skipped`). The orchestrator re-evaluates after requirements completes
  - After post-requirements resolution: `deferred` steps become `pending` (source found) or `skipped` (no source found)
- Steps with no `when` always run
- Steps that don't meet their `when` condition and cannot be deferred are marked `skipped` in the progress file

### 4. Validate the step list

All of the following must be true. If any check fails, **STOP** with a clear error:

- All step names are unique
- All `skill` references resolve to a known skill (bare names like `docs-workflow-writing` are preferred; fully qualified `plugin:skill` format is also accepted)
- Input dependencies are satisfied — for each step with `inputs`, every referenced step name must be present in the step list (unless it has a `when` condition that would skip it)

### Input dependencies

Steps declare their inputs as a list of upstream step names in the YAML:

```yaml
- name: writing
  skill: docs-workflow-writing
  inputs: [planning]

- name: create-jira
  skill: docs-workflow-create-jira
  when: create_jira_project
  inputs: [planning]
```

The orchestrator validates at load time that every step name in `inputs` exists in the step list. Step skills read their input data from the upstream step's output folder by convention (see below).

**Conditional input dependencies**: If an upstream step in `inputs` has a `when` condition and was `skipped`, that dependency is considered satisfied. The downstream step is responsible for checking whether the optional input data actually exists (e.g., the writing step checks for `evidence.json` and uses it if present, but proceeds without it). Only upstream steps that ran and `failed` block downstream execution.

**Custom workflow validation**: If a step's `inputs` references a step that does not exist in the current YAML step list, fail at load time with an error (e.g., "Step 'writing' requires 'planning', but 'planning' is not in the step list").

## Output conventions

Every step writes to a predictable folder based on the ticket ID and step name:

```
artifacts/<ticket>/<step-name>/
```

The ticket ID is converted to **lowercase** for directory names (e.g., `PROJ-123` → `proj-123`).

### Resolve base path

Resolve the base path to an absolute path so agents (which may run in a different working directory) can locate files correctly:

```bash
BASE_PATH="$(cd "$(git rev-parse --show-toplevel)" && pwd)/artifacts/${TICKET_LOWER}"
```

Use this absolute `BASE_PATH` for the progress file's `base_path` field and for all `--base-path` arguments passed to step skills.

### Folder structure

```
artifacts/proj-123/
  source.yaml                        (per-ticket source config, if applicable)
  code-repo/                         (cloned source repo, if applicable)
  requirements/
    requirements.md
  planning/
    plan.md
  code-evidence/                     (if source repo is available)
    evidence.json
    summary.md
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
  commit/
    commit-info.json
  create-mr/
    mr-info.json
  workflow/
    docs-workflow_proj-123.json
```

Each step skill knows its own output folder and writes there. Each step reads input from upstream step folders referenced in its `inputs` list. The orchestrator passes the base path `artifacts/<ticket>/` — step skills derive everything else by convention.

## Progress file

Claude writes the progress file directly using the Write tool. Create it after parsing arguments, before step 1. Update it after each step.

**Location**: `artifacts/<ticket>/workflow/<workflow-type>_<ticket>.json`

The `workflow_type` field and filename prefix match the YAML's `workflow.name`. This allows multiple workflow types to run against the same ticket without conflict.

### Schema

```json
{
  "workflow_type": "<workflow.name from YAML>",
  "ticket": "<TICKET>",
  "base_path": "/absolute/path/to/artifacts/<ticket>",
  "status": "in_progress",
  "created_at": "<ISO 8601>",
  "updated_at": "<ISO 8601>",
  "options": {
    "format": "adoc",
    "draft": false,
    "create_jira_project": null,
    "pr_urls": [],
    "source": null
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

The `output` field records the step's output folder path (e.g., `artifacts/proj-123/writing/`) once completed.

### Status values

| Value | Meaning |
|---|---|
| `pending` | Not yet started |
| `in_progress` | Currently running |
| `completed` | Finished successfully |
| `failed` | Failed — needs retry |
| `skipped` | Conditional step not applicable |
| `deferred` | Waiting for upstream step to determine if condition is met |

### `step_order`

A top-level array listing steps in canonical order. This field exists so the Stop hook can determine step ordering without a hardcoded bash array. It **must** always be written by the orchestrator and kept in sync with the YAML step list.

## Check for existing work

Before starting, check for a progress file at `artifacts/<ticket>/workflow/<workflow-type>_<ticket>.json`.

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

- If the step's status is `deferred`, skip it for now — it will be re-evaluated after post-requirements source resolution
- If the step's status is `skipped`, skip it permanently

### Before the step

1. Validate input dependencies — for each step name in the step's YAML `inputs`, check the upstream step's status:
   - `"completed"` — must also have a non-null `output` folder in the progress file
   - `"skipped"` (upstream step has a `when` condition) — treated as satisfied even though `output` is `null`. The downstream step is responsible for checking whether the optional input data actually exists
   - `"failed"` — **fail the current step immediately** with a clear error (e.g., "Step 'writing' requires 'planning', but planning has status 'failed'")
2. Update the step's status to `"in_progress"` in the progress file

### Construct arguments

Build the args string for the step skill:

1. **Always**: `<ticket> --base-path <base_path>` — the ticket ID and the **absolute** base output path
2. **If source repo is resolved**: `--repo <repo_path>` — passed to steps that can use it
3. **From orchestrator context**: Step-specific args from parsed CLI flags:
   - `requirements`: `[--pr <url>]... [--repo <repo_path>]`
   - `prepare-branch`: `[--draft] [--repo-path <path>]`
   - `code-evidence`: `--repo <repo_path> [--scope-include <globs>] [--scope-exclude <globs>] [--reindex]` — scope globs come from `source.yaml` or `options.source.scope` in the progress file
   - `writing`: `--format <adoc|mkdocs> [--draft] [--repo <repo_path>] [--repo-path <path>]`
   - `style-review`: `--format <adoc|mkdocs>`
   - `commit`: `[--draft] [--repo-path <path>]`
   - `create-mr`: `[--draft] [--repo-path <path>]`
   - `create-jira`: `--project <PROJECT>`

Step skills derive their own output folder and input folders from `--base-path` and step name conventions. No per-input flag wiring needed.

### Invoke the step skill

```
Skill: <step.skill>, args: "<constructed args>"
```

### After the step

1. Verify the output folder exists (for steps that produce files). If the expected output folder is missing, mark the step as `failed` in the progress file and **STOP**
2. Update the step's status to `"completed"` with the output folder path in the progress file
3. Update the progress file's `updated_at` timestamp
4. **If the just-completed step is `requirements` AND `options.source` is `null`** → run [Post-requirements source resolution](#post-requirements-source-resolution) before continuing to the next step. This may change `deferred` steps to `pending` or `skipped`

## Post-requirements source resolution

This section triggers **only** when the `requirements` step completes AND `options.source` is still `null` (i.e., no source was resolved pre-flight).

### 1. Run the script with `--scan-requirements`

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/resolve_source.py \
  --base-path <base_path> \
  --scan-requirements
```

The script scans `requirements.md` for GitHub/GitLab PR/MR URLs, groups them by repo, selects the repo with the most PRs, resolves the branch via `gh pr view`, clones, and writes `source.yaml`.

### 2. Handle the result

| Exit code | `status` | Action |
|---|---|---|
| 0 | `resolved` | Record `options.source` in the progress file. Update all `deferred` steps to `pending`. If `discovered_repos` has multiple entries, log which was auto-selected |
| 1 | `error` / `clone_failed` | Log a warning: "Could not clone `<repo_url>`. Code-evidence will be skipped. To retry, run with `--repo <url-or-local-path>`." Update all `deferred` steps to `skipped` |
| 2 | `no_source` | Skip code-evidence (see below) |

### 3. No source found

When the script returns `no_source`, skip code-evidence without prompting.

Update all `deferred` steps to `skipped` and continue without code-evidence. Log: "No source code repository or PR discovered. Skipping code-evidence. To enable it, re-run with `--repo <url-or-path>` or `--pr <url>`."

## Technical review iteration

The technical review step runs in a loop until confidence is acceptable or three iterations are exhausted:

1. Invoke `docs-workflow-tech-review` with the standard args
2. Read the output file and check for `Overall technical confidence: (HIGH|MEDIUM|LOW)`
   - If the confidence line is **missing** from the output, treat it as a step failure — mark the step `failed` and stop iteration
3. If `HIGH` → mark completed, proceed to next step
4. If `MEDIUM`, check for the `Severity counts:` line in the review output:
   - If present and both `critical=0` AND `significant=0` → treat as acceptable. Log: "MEDIUM confidence with zero critical/significant issues — proceeding (remaining items require SME review)." Mark completed and proceed to next step.
   - If the severity line is missing, or either `critical > 0` or `significant > 0` → continue to step 5 for iteration
5. If `MEDIUM` (with fixable issues) or `LOW` and fewer than 3 iterations completed → run the fix skill:
   ```
   Skill: docs-tools:docs-workflow-writing, args: "<ticket> --base-path <base_path> --fix-from <base_path>/technical-review/review.md"
   ```
   Then re-run the reviewer (go to step 1)
6. After 3 iterations without reaching `HIGH`:
   - `MEDIUM` is acceptable — proceed with a warning that manual review is recommended
   - `LOW` after max iterations — ask the user whether to proceed or stop

## Commit confirmation gate

Before running the `commit` step, check whether this is an interactive session:

- If `artifacts/.setup-complete` exists (ACP/headless mode): proceed without confirmation
- Otherwise (interactive/local mode): **ask the user to confirm** before committing. Show:
  - The target branch name
  - The repository being committed to (current directory or `--repo-path`)
  - The number of files in the writing manifest

If the user declines, mark the `commit` step as `skipped` and also skip the `create-mr` step (its input dependency is unsatisfied).

## Completion

After all steps complete (or are skipped):

1. Update the progress file: `status → "completed"`
2. Display a summary:
   - List all output folders with paths
   - Note any warnings (tech review didn't reach `HIGH`, etc.)
   - Show MR/PR URL if one was created
   - Show JIRA URL if a ticket was created

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

## Follow-on work

### Requirements-analyst agent: repo-aware analysis

When `--repo` is passed to the requirements step, the `requirements-analyst` agent should use the repo to enrich its analysis. This is **not yet implemented** — the requirements step currently accepts `--repo` but the agent does not act on it. Future work:

- Scan the repo's `README.md`, `CHANGELOG.md`, and `docs/` directory for existing documentation
- Note what documentation already exists and what gaps remain (feeds directly into the planning step's gap analysis)
- Extract project metadata: language, build system, major dependencies, directory structure
- Identify existing code examples, tutorials, or quickstart guides that the writer could reference or update rather than recreate
- If no `--pr` was provided, use the repo structure itself to identify the key components and features that need documentation

This work requires changes to the `requirements-analyst` agent definition (`agents/requirements-analyst.md`), not just the step skill.

### GitLab MR resolution

`resolve_source.py` discovers GitLab MRs during requirements scanning but cannot resolve them automatically — `gh pr view` is GitHub-only. When only GitLab MRs are found, the script returns `no_source` with a message prompting the user to provide `--repo` manually. Future work: add `glab` CLI support or GitLab API integration for automatic MR resolution.
