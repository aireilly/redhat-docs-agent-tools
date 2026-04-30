---
name: docs-orchestrator
description: Documentation workflow orchestrator. Reads the step list from .claude/docs-workflow.yaml (or the plugin default). Runs steps sequentially, manages progress state, handles iteration and confirmation gates. Claude is the orchestrator — the YAML is a step list, not a workflow engine.

argument-hint: <ticket> [--workflow <name>] [--pr <url>...] [--source-code-repo <url-or-path>...] [--mkdocs] [--draft] [--docs-repo-path <path>] [--create-jira <PROJECT>] [--create-merge-request]

allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, AskUserQuestion
---

# Docs Orchestrator

**When the user invokes `/docs-orchestrator` or `/docs-tools:docs-orchestrator`, run THIS skill directly. Do NOT redirect to `docs-workflow-start` or any other skill.**

Claude is the orchestrator. The YAML is a step list. The hook is a safety net.

This skill teaches you how to run a documentation workflow pipeline. You read the step list from YAML, run each step skill sequentially, manage progress state via a JSON file, and handle iteration loops and confirmation gates.

## Pre-flight

Install the workflow completion Stop hook (safe to re-run, skips if already installed):

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/setup-hooks.sh
```

**Do not** source `~/.env` or check for tokens/CLIs here — Python scripts (`jira_reader.py`, `resolve_source.py`, etc.) load `~/.env` and validate prerequisites themselves, producing clear errors on failure.

## Parse arguments

When displaying available options to the user (e.g., on skill load or when asking for flags), reproduce the descriptions below **verbatim** — do not summarize or paraphrase them.

- `$1` — JIRA ticket ID (required). If missing, STOP and ask the user.
- `--workflow <name>` — Use `.claude/docs-<name>.yaml` instead of `docs-workflow.yaml`. Allows running alternative pipelines (e.g., writing-only, review-only). Falls back to the plugin default at `skills/docs-orchestrator/defaults/docs-workflow.yaml` if no project-level YAML exists
- `--pr <url>...` — PR/MR URLs (space-delimited, one or more). Accepts GitHub PRs (`gh` CLI) and GitLab MRs (`glab` CLI). Used both as requirements input (agent reads diffs/descriptions) and for source repo resolution (repo URL and branch derived from the first PR/MR). When multiple PRs from different repos are provided, all repos are resolved and treated equally as source material
- `--mkdocs` — Use Material for MkDocs format instead of AsciiDoc. Propagates to the writing step (generates `.md` with MkDocs front matter) and style-review step (applies Markdown-appropriate rules). Sets `options.format` to `"mkdocs"` in the progress file
- `--draft` — Write documentation to the staging area (`.claude/docs/<ticket>/writing/`) instead of directly into the repo. Uses DRAFT placement mode: no framework detection, no file placement into the target repo. Without this flag, UPDATE-IN-PLACE is the default
- `--docs-repo-path <path>` — Target documentation repository for UPDATE-IN-PLACE mode. The docs-writer explores this directory for framework detection (Antora, MkDocs, Docusaurus, etc.) and writes files there instead of the current working directory. Propagates to `writing` and `create-merge-request` steps (mapped to their internal `--repo-path` flag). **Precedence**: if both `--docs-repo-path` and `--draft` are passed, `--docs-repo-path` wins — log a warning and ignore `--draft`
- `--source-code-repo <url-or-path>...` — Source code repository/repositories for code evidence and requirements enrichment (space-delimited, one or more). Accepts remote URLs (https://, git@, ssh:// — each shallow-cloned to `.claude/docs/<ticket>/code-repo/<repo_name>/`) or local paths (used directly). The first repo is treated as primary; additional repos are returned as `additional_repos` in the result. Passed to requirements, code-evidence, and writing steps (mapped to their internal `--repo` flag). Without `--pr`, the entire repo is the subject matter; with `--pr`, the PR branch is checked out on the primary repo so code-evidence reflects the PR's state. Takes highest priority in source resolution, overriding `source.yaml` and PR-derived URLs
- `--create-jira <PROJECT>` — Create a linked JIRA ticket in the specified project after the planning step completes. Runs the standalone `docs-workflow-create-jira` workflow (use `--workflow workflow-create-jira`). Requires `JIRA_API_TOKEN` to be set
- `--create-merge-request` — Create a branch, commit, push, and open a merge request or pull request after reviews complete. Activates the `create-merge-request` workflow step (guarded by `when: create_merge_request`). Off by default

### Examples

```bash
# Minimal — just a ticket
/docs-orchestrator PROJ-123

# PR-driven with MkDocs output
/docs-orchestrator PROJ-123 --pr https://github.com/org/repo/pull/42 --mkdocs

# Multiple PRs from different repos, written to a separate docs repo
/docs-orchestrator PROJ-123 \
  --pr https://github.com/org/backend/pull/10 https://gitlab.example.com/org/frontend/-/merge_requests/5 \
  --docs-repo-path /home/user/docs-repo

# Source repo without PRs, draft mode, with merge request creation
/docs-orchestrator PROJ-123 \
  --source-code-repo https://github.com/org/operator \
  --draft \
  --create-merge-request

# Local source repo + PR (checks out PR branch within repo)
/docs-orchestrator PROJ-123 \
  --source-code-repo /home/user/local-checkout \
  --pr https://github.com/org/repo/pull/99

# Custom workflow YAML
/docs-orchestrator PROJ-123 --workflow quick

# Code-evidence workflow — requires a source repo
/docs-orchestrator PROJ-123 \
  --workflow workflow-code-evidence \
  --source-code-repo https://github.com/org/operator
```

## Resolve source repository

After parsing arguments and before running steps, resolve the source code repository if one is configured. This makes the repo available to all downstream steps that need it (requirements, code-evidence, writing).

All clone, verify, PR-resolution, and source.yaml logic is handled by the `resolve_source.py` script. The orchestrator calls the script and acts on the JSON result.

### Pre-flight resolution

Run the script with whatever source information is available from CLI args. Always pass `--ticket` and `--plugin-root` so the script can attempt JIRA-based discovery if explicit sources are absent:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/resolve_source.py \
  --base-path <base_path> \
  --ticket <TICKET> \
  --plugin-root ${CLAUDE_PLUGIN_ROOT} \
  [--repo <url-or-path>...] \
  [--pr <url>...]
```

The script checks sources in priority order:

1. **CLI `--source-code-repo` flag** — clone or verify the path
2. **Per-ticket `source.yaml`** — read and apply existing config
3. **PR-derived** — resolve repo URL and branch from `--pr` via `gh pr view` or `glab mr view`
4. **JIRA ticket discovery** — query the ticket's `git_links` and auto-discovered PR URLs, extract repo URLs, and select the primary repo by reference count. If multiple repos tie, return an error listing candidates
5. **No source** — exit code 2, defer resolution until after requirements

The script outputs JSON to stdout:

```json
{
  "status": "resolved",
  "repo_path": ".claude/docs/proj-123/code-repo/operator",
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

If `discovered_repos` is present in the result (multiple repos found), log all resolved repos. If `additional_repos` is present, record them in the progress file alongside the primary source. If `warnings` is present, log each warning.

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
- If the project-level file doesn't exist → fall back to the plugin default at `skills/docs-orchestrator/defaults/docs-workflow.yaml`

### 2. Read the YAML

Read the YAML file and extract the ordered step list. Each step has: `name`, `skill`, `description`, optional `when`, and optional `inputs`.

### 3. Validate `requires` conditions

If the YAML includes a top-level `workflow.requires` list, check each condition **before evaluating steps or running anything**:

- `has_source_repo` → a source repo must be resolvable. The pre-flight resolution script tries CLI args, `source.yaml`, PR-derived, and JIRA ticket discovery (git links and auto-discovered PRs) in priority order. If **none** of these yield a source repo, **STOP** immediately with: `"This workflow requires a source code repository. No repo could be discovered from the JIRA ticket. Pass --source-code-repo <url-or-path> or --pr <url>."`

Unlike `when` (which makes individual steps conditional), `requires` is a workflow-level precondition — the entire workflow fails if a required condition is not met. This prevents users from running a code-evidence-heavy workflow without a repo and only discovering the problem after requirements and planning have already completed.

### 4. Evaluate `when` conditions

- `when: create_merge_request` → run this step only if `--create-merge-request` was passed
- `when: has_source_repo` → evaluation depends on timing:
  - If a source repo was already resolved pre-flight (via `--source-code-repo`, `--pr`, or `source.yaml`) → step runs normally (`pending`)
  - If no source is resolved yet but post-requirements discovery is possible (case 4 above) → mark the step `deferred` (not `skipped`). The orchestrator re-evaluates after requirements completes
  - After post-requirements resolution: `deferred` steps become `pending` (source found) or `skipped` (no source found)
- Steps with no `when` always run
- Steps that don't meet their `when` condition and cannot be deferred are marked `skipped` in the progress file

### 5. Validate the step list

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

- name: create-merge-request
  skill: docs-tools:docs-workflow-create-merge-request
  when: create_merge_request
  inputs: [writing, style-review, technical-review]
```

The orchestrator validates at load time that every step name in `inputs` exists in the step list. Step skills read their input data from the upstream step's output folder by convention (see below).

**Conditional input dependencies**: If an upstream step in `inputs` has a `when` condition and was `skipped`, that dependency is considered satisfied. The downstream step is responsible for checking whether the optional input data actually exists (e.g., the writing step checks for `evidence.json` and uses it if present, but proceeds without it). Only upstream steps that ran and `failed` block downstream execution.

**Custom workflow validation**: If a step's `inputs` references a step that does not exist in the current YAML step list, fail at load time with an error (e.g., "Step 'writing' requires 'planning', but 'planning' is not in the step list").

## Output conventions

Every step writes to a predictable folder based on the ticket ID and step name:

```
.claude/docs/<ticket>/<step-name>/
```

The ticket ID is converted to **lowercase** for directory names (e.g., `PROJ-123` → `proj-123`).

### Resolve base path

Resolve the base path to an absolute path so agents (which may run in a different working directory) can locate files correctly:

```bash
BASE_PATH="$(cd "$(git rev-parse --show-toplevel)" && pwd)/.claude/docs/${TICKET_LOWER}"
```

Use this absolute `BASE_PATH` for the progress file's `base_path` field and for all `--base-path` arguments passed to step skills.

### Folder structure

```
.claude/docs/proj-123/
  source.yaml                        (per-ticket source config, if applicable)
  code-repo/
    <repo-name>/                     (each repo gets its own subdirectory)
  requirements/
    requirements.md
    step-result.json                 (sidecar: title)
  scope-req-audit/                     (if source repo is available)
    evidence-status.json
    summary.md
    step-result.json                 (sidecar: recommendation, grounded, partial, absent, total, discovered_repos_count)
  planning/
    plan.md
    step-result.json                 (sidecar: module_count)
  code-evidence/                     (if source repo is available)
    evidence.json
    summary.md
    step-result.json                 (sidecar: topic_count, snippet_count, repo_path)
  writing/
    _index.md
    step-result.json                 (sidecar: files, mode, format)
    assembly_*.adoc (or docs/*.md for mkdocs)
    modules/
  technical-review/
    review.md
    step-result.json                 (sidecar: confidence, severity_counts)
  style-review/
    review.md
    step-result.json                 (sidecar: common fields only)
  create-merge-request/
    step-result.json                 (sidecar: commit_sha, branch, pushed, url, action, platform, skipped)
  workflow/
    docs-workflow_proj-123.json
```

Each step skill knows its own output folder and writes there. Each step reads input from upstream step folders referenced in its `inputs` list. The orchestrator passes the base path `.claude/docs/<ticket>/` — step skills derive everything else by convention.

### Step result sidecars

Every step that produces markdown output also writes a `step-result.json` sidecar with structured metadata. See [schema/step-result-schema.md](schema/step-result-schema.md) for the full schema. Downstream scripts and the orchestrator prefer sidecar data when present, falling back to parsing the markdown output for backward compatibility.

## Progress file

Claude writes the progress file directly using the Write tool. Create it after parsing arguments, before step 1. Update it after each step.

**Location**: `.claude/docs/<ticket>/workflow/<workflow-type>_<ticket>.json`

The `workflow_type` field and filename prefix match the YAML's `workflow.name`. This allows multiple workflow types to run against the same ticket without conflict.

### Schema

```json
{
  "workflow_type": "<workflow.name from YAML>",
  "ticket": "<TICKET>",
  "base_path": "/absolute/path/to/.claude/docs/<ticket>",
  "status": "in_progress",
  "created_at": "<ISO 8601>",
  "updated_at": "<ISO 8601>",
  "options": {
    "format": "adoc",
    "draft": false,
    "create_merge_request": false,
    "pr_urls": [],
    "source": null,
    "additional_sources": []
  },
  "step_order": ["requirements", "scope-req-audit", "planning", "writing", ...],
  "steps": {
    "<step-name>": {
      "status": "pending",
      "output": null,
      "result": null
    }
  }
}
```

The `output` field records the step's output folder path (e.g., `.claude/docs/proj-123/writing/`) once completed.

The `result` field stores selected sidecar data after each step completes. This lets the orchestrator make downstream decisions and display summaries without re-reading sidecar files from disk — especially important on resume. Set to `null` until the step completes; then populated from `step-result.json` (see [Step-specific post-processing](#step-specific-post-processing)).

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

- If the step's status is `deferred`, skip it for now — it will be re-evaluated after post-requirements source resolution
- If the step's status is `skipped`, skip it permanently

### Before the step

1. Validate input dependencies — for each step name in the step's YAML `inputs`, check the upstream step's status:
   - `"completed"` — must also have a non-null `output` folder in the progress file
   - `"skipped"` (upstream step has a `when` condition) — treated as satisfied even though `output` is `null`. The downstream step is responsible for checking whether the optional input data actually exists
   - `"failed"` — **fail the current step immediately** with a clear error (e.g., "Step 'writing' requires 'planning', but planning has status 'failed'")
2. Update the step's status to `"in_progress"` in the progress file

### Construct arguments

Build the args string for the step skill. The orchestrator maps its user-facing flags to the internal flags that step skills expect: `--source-code-repo` → `--repo`, `--docs-repo-path` → `--repo-path`.

1. **Always**: `<ticket> --base-path <base_path>` — the ticket ID and the **absolute** base output path
2. **If source repo is resolved**: `--repo <repo_path>` — passed to steps that can use it
3. **From orchestrator context**: Step-specific args from parsed CLI flags:
   - `requirements`: `[--pr <url>]... [--repo <repo_path>]`
   - `scope-req-audit`: `--repo <repo_path> [--grounded-threshold <float>] [--absent-threshold <float>]`
   - `code-evidence`: `--repo <repo_path> [--scope-include <globs>] [--scope-exclude <globs>] [--reindex]` — scope globs come from `source.yaml` or `options.source.scope` in the progress file
   - `writing`: `--format <adoc|mkdocs> [--draft] [--repo <repo_path>] [--repo-path <path>]`
   - `style-review`: `--format <adoc|mkdocs>`
   - `create-merge-request`: `[--draft] [--repo-path <path>]`

Step skills derive their own output folder and input folders from `--base-path` and step name conventions. No per-input flag wiring needed.

### Invoke the step skill

```
Skill: <step.skill>, args: "<constructed args>"
```

### After the step

1. Verify the output folder exists (for steps that produce files). If the expected output folder is missing, mark the step as `failed` in the progress file and **STOP**
2. Read the step's `step-result.json` sidecar if it exists in the output folder. If present, store the step-specific fields in `steps.<step-name>.result` in the progress file (see [Step-specific post-processing](#step-specific-post-processing) for which fields to record per step). Log a warning if the sidecar is missing (the step still counts as completed — sidecars are expected but not required for backward compatibility)
3. Update the step's status to `"completed"` with the output folder path in the progress file
4. Update the progress file's `updated_at` timestamp
5. Run [step-specific post-processing](#step-specific-post-processing) for the just-completed step

### Step-specific post-processing

After each step completes, apply the rules below. When rules reference sidecar fields, read from `steps.<step-name>.result` in the progress file (already recorded in the after-step logic above). If the sidecar was missing, fall back to parsing the step's primary output file where noted.

**requirements**
- Log the `title` field: `"Requirements extracted: <title>"`
- If `options.source` is `null` → run [Post-requirements source resolution](#post-requirements-source-resolution). This may change `deferred` steps to `pending` or `skipped`

**scope-req-audit**
- Log: `"scope-req-audit completed: N grounded, N partial, N absent — recommendation: <recommendation>"`
- If `discovered_repos_count` > 0, also log: `"(N discovered repos not indexed)"`
- Fall back to reading `evidence-status.json` if sidecar result is missing

**planning**
- Log: `"Planning completed: N modules"`
- If `module_count` is 0, **warn**: `"Planning produced 0 modules — the plan may be empty. Review plan.md before continuing."` Ask the user whether to proceed or stop. If the user chooses to stop: mark the planning step as `failed` in the progress file, set the workflow status to `"failed"`, log `"Planning stopped by user after 0 modules — workflow cancelled."`, and halt without running subsequent steps

**code-evidence**
- Log: `"Code evidence retrieved: N topics, N snippets"`
- If `snippet_count` is 0, **warn**: `"No code snippets found — the writing step will have no code evidence to ground documentation in."`

**writing**
- If `result.files` is empty or missing, **warn**: `"Writing step produced no files."` Mark the `create-merge-request` step as `skipped` with `skip_reason: "no_files"` and record `result.commit_sha: null`, `result.branch: null`, `result.pushed: false`, `result.url: null`, `result.action: "skipped"`, `result.platform: "unknown"`, `result.skipped: true`. Log: `"Skipping create-merge-request: no files to commit."`

**create-merge-request**
- Record `result.url`, `result.pushed`, and `result.branch`. If `result.pushed` is false and `result.skipped` is false, log warning: `"create-merge-request: branch was not pushed."` If `result.url` is present, record it for the [Completion](#completion) summary

**create-jira**
- Record `result.jira_url` and `result.jira_key` for the [Completion](#completion) summary

## Post-requirements source resolution

This section triggers **only** when the `requirements` step completes AND `options.source` is still `null` (i.e., no source was resolved pre-flight).

### 1. Run the script with `--scan-requirements`

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/resolve_source.py \
  --base-path <base_path> \
  --ticket <TICKET> \
  --plugin-root ${CLAUDE_PLUGIN_ROOT} \
  --scan-requirements
```

The script first attempts JIRA ticket discovery (git links and auto-discovered PRs from the ticket graph), then scans `requirements.md` for GitHub/GitLab PR/MR URLs as a fallback. It groups discovered repos, resolves all repos equally (via `gh pr view` or `glab mr view`), clones each into `code-repo/<name>/`, and writes `source.yaml` for the primary repo.

### 2. Handle the result

| Exit code | `status` | Action |
|---|---|---|
| 0 | `resolved` | Record `options.source` in the progress file (primary repo + any `additional_repos`). Update all `deferred` steps to `pending`. Log all resolved repos |
| 1 | `error` / `clone_failed` | Log a warning: "Could not clone `<repo_url>`. Code-evidence will be skipped. To retry, run with `--source-code-repo <url-or-local-path>`." Update all `deferred` steps to `skipped` |
| 2 | `no_source` | Skip code-evidence (see below) |

### 3. No source found

When the script returns `no_source`, skip code-evidence without prompting.

Update all `deferred` steps to `skipped` and continue without code-evidence. Log: "No source code repository or PR discovered. Skipping code-evidence. To enable it, re-run with `--source-code-repo <url-or-path>` or `--pr <url>`."

## Technical review iteration

The technical review step runs in a loop until confidence is acceptable or three iterations are exhausted:

1. Invoke `docs-workflow-tech-review` with the standard args
2. Read the review metadata. **Prefer the sidecar** (`<base_path>/technical-review/step-result.json`) when present — read `confidence` and `severity_counts` directly. **Fall back** to parsing `review.md` for the `Overall technical confidence: (HIGH|MEDIUM|LOW)` and `Severity counts:` lines if no sidecar exists
   - If neither the sidecar nor the confidence line is found, treat it as a step failure — mark the step `failed` and stop iteration
3. If `HIGH` → mark completed, proceed to next step
4. If `MEDIUM`, check the severity counts (from sidecar `severity_counts` object or from the `Severity counts:` line):
   - If both `critical=0` AND `significant=0` → treat as acceptable. Log: "MEDIUM confidence with zero critical/significant issues — proceeding (remaining items require SME review)." Mark completed and proceed to next step.
   - If severity counts are unavailable, or either `critical > 0` or `significant > 0` → continue to step 5 for iteration
5. If `MEDIUM` (with fixable issues) or `LOW` and fewer than 3 iterations completed → run the fix skill:
   ```
   Skill: docs-tools:docs-workflow-writing, args: "<ticket> --base-path <base_path> --fix-from <base_path>/technical-review/review.md"
   ```
   Then re-run the reviewer (go to step 1)
6. After 3 iterations without reaching `HIGH`:
   - `MEDIUM` is acceptable — proceed with a warning that manual review is recommended
   - `LOW` after max iterations — ask the user whether to proceed or stop

## Commit confirmation gate

Before running the `create-merge-request` step, **ask the user to confirm** before committing. Show:
  - The target branch name — derived from the ticket ID (lowercase). If the repo is already on a feature branch, show the current branch name (from `git branch --show-current`)
  - The repository being committed to (current directory or `--docs-repo-path`)
  - The number of files — from `steps.writing.result.files` array length in the progress file. If unavailable, count files in the writing output folder

If the user declines, mark the `create-merge-request` step as `skipped` (with `skip_reason: "user_declined"`). Record `result.commit_sha: null`, `result.branch: null`, `result.pushed: false`, `result.url: null`, `result.action: "skipped"`, `result.platform: "unknown"`, `result.skipped: true`.

## Completion

After all steps complete (or are skipped):

1. Update the progress file: `status → "completed"`
2. Display a summary:
   - List all output folders with paths
   - Note any warnings (tech review didn't reach `HIGH`, planning had 0 modules, code-evidence had 0 snippets, etc.)
   - Show MR/PR URL from `steps.create-merge-request.result.url` if present
   - Show JIRA URL from `steps.create-jira.result.jira_url` (with key `result.jira_key`) if present
   - Show module count from `steps.planning.result.module_count` and file count from `steps.writing.result.files` length

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

When `--source-code-repo` is passed to the requirements step, the `requirements-analyst` agent should use the repo to enrich its analysis. This is **not yet implemented** — the requirements step currently accepts `--source-code-repo` but the agent does not act on it. Future work:

- Scan the repo's `README.md`, `CHANGELOG.md`, and `docs/` directory for existing documentation
- Note what documentation already exists and what gaps remain (feeds directly into the planning step's gap analysis)
- Extract project metadata: language, build system, major dependencies, directory structure
- Identify existing code examples, tutorials, or quickstart guides that the writer could reference or update rather than recreate
- If no `--pr` was provided, use the repo structure itself to identify the key components and features that need documentation

This work requires changes to the `requirements-analyst` agent definition (`agents/requirements-analyst.md`), not just the step skill.

