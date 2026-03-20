# Design Spec: Docs Orchestrator (Hooks + structured workflow)

**Date**: 2026-03-20
**Status**: Draft
**Scope**: `plugins/docs-tools/`
**Supersedes**: `2026-03-19-docs-orchestrator-design.md`, `2026-03-19-docs-orchestrator-hooks-design.md`
**Prerequisites**: None (no external dependencies required)

## Problem

The `docs-workflow` command is a ~1300-line monolithic orchestrator that inlines all stage prompts, state management, JIRA API logic, and control flow into a single markdown file. This causes:

* **Every team gets the same pipeline** — no way to add, remove, or reorder stages without forking the orchestrator
* **New workflows require new orchestrator skills** — a review-only workflow or simplified onboarding workflow each need their own hardcoded orchestrator
* **No reusability** — individual stages cannot be invoked independently
* **Maintenance burden** — changes to one stage risk breaking others

## Solution

Three components, each doing exactly one thing:

1. **Step skills** — independent, reusable skills that each own one stage of the pipeline
2. **A `docs-orchestrator` skill** — teaches Claude the pipeline and conventions; reads step list from YAML if present
3. **A Stop hook** — validates workflow completion by checking one thing: is `status == "completed"` in the progress file?

Claude is the orchestrator. The skill is a checklist. The YAML is a user-editable step list. The hook is a safety net.

**What this is not**: a workflow engine. There is no YAML interpreter, no template resolver, no Python state machine. Claude reads instructions and executes them; `workflow_state.py` is replaced by Claude writing JSON directly.

## Architecture

```
User: "Write docs for PROJ-123 --pr https://..."
     |
     v
docs-orchestrator skill          ← Reads step list from YAML (or uses built-in default)
     |                           ← Teaches Claude the pipeline conventions
     |
     +-- Claude decides what's needed
     |
     +-- Skill: step-1-skill     ← Independent step skills
     +-- Skill: step-2-skill
     +-- ...
     |
     v
Stop hook                        ← One check: status == "completed"?
     |
     +-- exit 0                 → Claude stops
     +-- exit 2 + stderr        → Claude continues
```

## Component Inventory

### New files

```
plugins/docs-tools/skills/
  docs-orchestrator/
    docs-orchestrator.md                  # Orchestrator skill
    hooks/
      workflow-completion-check.sh        # Stop hook script
    scripts/
      setup-hooks.sh                      # Hook installation helper
    defaults/
      docs-orchestrator.yaml              # Default step list (shipped with plugin)
```

### Step skills (new)

```
plugins/docs-tools/skills/
  docs-workflow-requirements/
    docs-workflow-requirements.md
  docs-workflow-planning/
    docs-workflow-planning.md
  docs-workflow-writing/
    docs-workflow-writing.md
  docs-workflow-tech-review/
    docs-workflow-tech-review.md
  docs-workflow-style-review/
    docs-workflow-style-review.md
  docs-workflow-integrate/
    docs-workflow-integrate.md
  docs-workflow-create-jira/
    docs-workflow-create-jira.md
```

### User-created files (per team/repo)

```
.claude/
  docs-orchestrator.yaml          # Optional — override the default step list
  settings.json                   # Stop hook registration (written by setup-hooks.sh)
  hooks/
    workflow-completion-check.sh  # Copied here by setup-hooks.sh
  docs/
    workflow/
      docs-workflow_<ticket>.json # Progress files (written by Claude)
```

### Existing files (unchanged)

* `commands/docs-workflow.md` — continues to work as-is
* `agents/*.md` — all agent definitions unchanged

---

## The YAML Step List

The YAML is **not** a workflow engine definition. It is a step list: an ordered set of step names, skill references, and conditions. All orchestration logic (iteration, confirmation gates, progress tracking) lives in the `docs-orchestrator.md` skill, not in the YAML.

### Location

1. `.claude/docs-orchestrator.yaml` — user's repo (takes precedence)
2. `plugins/docs-tools/skills/docs-orchestrator/defaults/docs-orchestrator.yaml` — plugin default (used when no user YAML exists)

The orchestrator reads the user's YAML if present, otherwise falls back to the plugin default. Users never have to create a YAML file to use the orchestrator.

### Schema

```yaml
workflow:
  name: <string>           # Workflow type name (used in progress file naming)
  description: <string>    # Optional

  steps:
    - name: <string>       # Step identifier (used in progress file)
      skill: <string>      # Fully qualified skill name (plugin:skill)
      description: <string>  # Optional — shown in status output
      when: <string>       # Optional — param name to check (truthy = run this step)
```

That's it. No template syntax. No filter expressions. No condition operators. No iteration config. No confirm gates. All of that lives in the orchestrator skill's natural-language instructions, where Claude can reason about it.

### What the YAML controls

| Controlled by YAML | Controlled by orchestrator skill |
|---|---|
| Step names | Output path conventions |
| Step order | Argument construction |
| Skill references | Iteration logic (tech review) |
| Which param gates a step | Confirmation gates |
| Step descriptions | Progress file schema |
| | Error handling |
| | Preflight checks |
| | Resume behavior |

### Default `docs-orchestrator.yaml`

```yaml
workflow:
  name: docs-workflow
  description: >
    Multi-stage documentation workflow for a JIRA ticket.
    Requirements analysis, planning, writing, technical review,
    style review, and optionally integration and JIRA creation.

  steps:
    - name: requirements
      skill: docs-tools:docs-workflow-requirements
      description: Analyze documentation requirements

    - name: planning
      skill: docs-tools:docs-workflow-planning
      description: Create documentation plan

    - name: writing
      skill: docs-tools:docs-workflow-writing
      description: Write documentation drafts

    - name: technical-review
      skill: docs-tools:docs-workflow-tech-review
      description: Technical accuracy review

    - name: style-review
      skill: docs-tools:docs-workflow-style-review
      description: Style guide compliance review

    - name: integrate-plan
      skill: docs-tools:docs-workflow-integrate
      description: Plan integration into build framework
      when: integrate

    - name: integrate-execute
      skill: docs-tools:docs-workflow-integrate
      description: Execute integration
      when: integrate

    - name: create-jira
      skill: docs-tools:docs-workflow-create-jira
      description: Create linked JIRA ticket
      when: create_jira_project
```

### Example: Team-specific customization

A team that doesn't use JIRA and wants a tighter review loop:

```yaml
workflow:
  name: docs-workflow
  description: Streamlined docs workflow (no JIRA)

  steps:
    - name: requirements
      skill: docs-tools:docs-workflow-requirements
      description: Analyze documentation requirements

    - name: planning
      skill: docs-tools:docs-workflow-planning
      description: Create documentation plan

    - name: writing
      skill: docs-tools:docs-workflow-writing
      description: Write documentation drafts

    - name: peer-review
      skill: acme-tools:peer-review-request
      description: Open peer review PR

    - name: technical-review
      skill: docs-tools:docs-workflow-tech-review
      description: Technical accuracy review

    - name: style-review
      skill: docs-tools:docs-workflow-style-review
      description: Style guide compliance review

    - name: integrate-plan
      skill: docs-tools:docs-workflow-integrate
      description: Plan integration
      when: integrate

    - name: integrate-execute
      skill: docs-tools:docs-workflow-integrate
      description: Execute integration
      when: integrate
```

No skill changes needed. No orchestrator fork. Edit the YAML, add the step.

### Example: Review-only workflow

A second YAML file for review-only runs (`.claude/docs-review-only.yaml`):

```yaml
workflow:
  name: review-only
  description: Run technical and style review on existing drafts

  steps:
    - name: technical-review
      skill: docs-tools:docs-workflow-tech-review
      description: Technical accuracy review

    - name: style-review
      skill: docs-tools:docs-workflow-style-review
      description: Style guide compliance review
```

Invoke with: `Skill: docs-tools:docs-orchestrator, args: "PROJ-123 --workflow review-only"`

The Stop hook reads the progress file's `workflow_type` field to find the correct YAML and validate completion.

---

## Orchestrator Skill: `docs-orchestrator.md`

### Frontmatter

```
---
name: docs-orchestrator
description: >
  Documentation workflow orchestrator. Reads the step list from
  .claude/docs-orchestrator.yaml (or the plugin default). Runs steps
  sequentially, manages progress state, handles iteration and confirmation
  gates. Claude is the orchestrator — the YAML is a step list, not a
  workflow engine.
argument-hint: <ticket> [--workflow <name>] [--pr <url>] [--mkdocs] [--integrate] [--create-jira <PROJECT>]
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, AskUserQuestion, WebSearch, WebFetch
---
```

### Pre-flight

Before starting, verify the environment:

1. Source `~/.env` if `JIRA_AUTH_TOKEN` is not set
2. If `JIRA_AUTH_TOKEN` is still unset → STOP and ask the user
3. Warn (don't stop) if `GITHUB_TOKEN` or `GITLAB_TOKEN` are unset

### Parse arguments

* `$1` — JIRA ticket ID (required)
* `--workflow <name>` — use `.claude/docs-<name>.yaml` instead of `docs-orchestrator.yaml`
* `--pr <url>` — PR/MR URLs (repeatable, accumulated into a list)
* `--mkdocs` — use Material for MkDocs format instead of AsciiDoc
* `--integrate` — run integration steps after review
* `--create-jira <PROJECT>` — create a linked JIRA ticket in the specified project

### Load the step list

1. Determine the YAML file to use:
   - If `--workflow <name>` was specified → `.claude/docs-<name>.yaml`
   - Otherwise → `.claude/docs-orchestrator.yaml`
   - If neither exists → use the plugin default at `skills/docs-orchestrator/defaults/docs-orchestrator.yaml`

2. Read the YAML and extract the ordered step list with names, skills, descriptions, and `when` conditions.

3. Evaluate `when` conditions against parsed params:
   - `when: integrate` → run this step only if `--integrate` was passed
   - `when: create_jira_project` → run this step only if `--create-jira` was passed
   - Steps with no `when` always run

4. Validate the step list:
   - All step names must be unique
   - All `skill` references must be fully qualified (`plugin:skill`)
   - For each step, check its input dependencies (from the [Input dependencies](#input-dependencies) table). If a required upstream step is not present in the step list and has no `when` condition that would skip it, fail with an error (e.g., "Step 'writing' requires 'planning', but 'planning' is not in the step list")

5. The evaluated step list (with skipped steps identified) drives everything that follows.

### Output conventions

All outputs go under `.claude/docs/`:

```
.claude/docs/
  requirements/requirements_<ticket>_<timestamp>.md
  plans/plan_<ticket>_<timestamp>.md
  drafts/<ticket>/
    _index.md
    [modules and assemblies]
    _technical_review.md
    _review_report.md
    _integration_plan.md    (if --integrate)
    _integration_report.md  (if --integrate)
  workflow/
    <workflow-type>_<ticket>.json
```

Convert the ticket ID to lowercase for directory names (e.g., `PROJ-123` → `proj-123`).
Use lowercase with underscores for filenames (e.g., `PROJ-123` → `proj_123`).

### Check for existing work

Before starting, check for a progress file at `.claude/docs/workflow/<workflow-type>_<ticket>.json`.

If a progress file exists:
- Read it and identify which steps have status `"completed"` or `"skipped"`
- For each `"completed"` step that has a non-null `output` path, verify the output file still exists on disk. If it has been deleted, reset that step to `"pending"` and reset all downstream dependent steps to `"pending"` as well
- Resume from the first step with status `"pending"` or `"failed"`
- Before running the resume step, validate its input dependencies are satisfied (see [Input dependencies](#input-dependencies))
- Tell the user: "Found existing work for `<ticket>`. Resuming from `<step>`."

If no progress file exists, start from step 1 and create a new progress file.

### Progress file

Claude writes the progress file directly using the Write tool. Create it after parsing arguments, before step 1. Update it after each step.

**Location**: `.claude/docs/workflow/<workflow-type>_<ticket>.json`

The `workflow_type` field and filename prefix match the YAML's `workflow.name`. This allows multiple workflow types to run against the same ticket without conflict (e.g., `docs-workflow_proj_123.json` and `review-only_proj_123.json`).

```json
{
  "workflow_type": "docs-workflow",
  "ticket": "PROJ-123",
  "status": "in_progress",
  "created_at": "2026-03-20T10:00:00Z",
  "updated_at": "2026-03-20T12:34:56Z",
  "options": {
    "format": "adoc",
    "integrate": false,
    "create_jira_project": null,
    "pr_urls": []
  },
  "step_order": [
    "requirements", "planning", "writing",
    "technical-review", "style-review",
    "integrate-plan", "integrate-execute", "create-jira"
  ],
  "steps": {
    "requirements": {
      "status": "completed",
      "output": ".claude/docs/requirements/requirements_proj_123_20260320_100100.md"
    },
    "planning": {
      "status": "completed",
      "output": ".claude/docs/plans/plan_proj_123_20260320_100500.md"
    },
    "writing": {
      "status": "in_progress",
      "output": null
    },
    "technical-review": {
      "status": "pending",
      "output": null
    },
    "style-review": {
      "status": "pending",
      "output": null
    },
    "integrate-plan": {
      "status": "skipped",
      "output": null
    },
    "integrate-execute": {
      "status": "skipped",
      "output": null
    },
    "create-jira": {
      "status": "skipped",
      "output": null
    }
  }
}
```

**`step_order`** is a top-level array listing steps in canonical order. This field exists so the Stop hook can determine step ordering without a hardcoded bash array. It must always be written by the orchestrator and kept in sync with the YAML step list.

#### Status values

| Value | Meaning |
|---|---|
| `pending` | Not yet started |
| `in_progress` | Currently running |
| `completed` | Finished successfully |
| `failed` | Failed — needs retry |
| `skipped` | Conditional step not applicable |

### Workflow steps

Run steps in the order defined by the YAML. Before each step, validate its input dependencies (see [Input dependencies](#input-dependencies)). After each step, verify the output file exists before proceeding — if the expected output file is missing, mark the step as `failed` in the progress file and stop. Update the progress file after each step completes.

The orchestrator skill owns all orchestration logic. Step skills only parse args, do work, and write output.

#### Argument construction

The orchestrator constructs args for each step skill using the conventions below. These are built from parsed params and previously completed step outputs read from the progress file.

| Step | Args passed to skill |
|---|---|
| requirements | `<ticket> [--pr <url>]... --output <output_path>` |
| planning | `<ticket> --input <requirements_output> --output <output_path>` |
| writing | `<ticket> --input <planning_output> --output <output_path> --format <adoc\|mkdocs>` |
| technical-review | `<ticket> --drafts-dir <drafts_dir> --output <output_path>` |
| style-review | `<ticket> --drafts-dir <drafts_dir> --output <output_path> --format <adoc\|mkdocs>` |
| integrate-plan | `<ticket> --phase plan --drafts-dir <drafts_dir> --output <output_path>` |
| integrate-execute | `<ticket> --phase execute --drafts-dir <drafts_dir> --plan <integration_plan_output> --output <output_path>` |
| create-jira | `<ticket> --project <PROJECT> --plan <planning_output>` |

#### Input dependencies

Each step declares which previous steps' outputs it requires. Before constructing arguments for a step, the orchestrator **must** read the progress file and verify that every required input step has `status: "completed"` and a non-null `output` path. If any required input is missing or its step did not complete, the orchestrator **must** fail the current step immediately with a clear error (e.g., "Step 'writing' requires output from 'planning', but planning has status 'failed' and output null").

| Step | Required inputs (step → arg) |
|---|---|
| requirements | *(none — entry point)* |
| planning | `requirements` → `<requirements_output>` |
| writing | `planning` → `<planning_output>` |
| technical-review | `writing` → `<drafts_dir>` (derived from writing output directory) |
| style-review | `writing` → `<drafts_dir>` |
| integrate-plan | `writing` → `<drafts_dir>` |
| integrate-execute | `integrate-plan` → `<integration_plan_output>` ; `writing` → `<drafts_dir>` |
| create-jira | `planning` → `<planning_output>` |

**Placeholder disambiguation**: `<planning_output>` always refers to the planning step's output file. `<integration_plan_output>` refers to the integrate-plan step's output file. These are distinct values read from different entries in the progress file's `steps` object.

**Custom workflow validation**: If a step's required input references a step that does not exist in the current YAML step list, the orchestrator must fail at load time with an error (e.g., "Step 'create-jira' requires 'planning', but 'planning' is not in the step list"). This prevents users from creating broken workflows by removing upstream steps without removing downstream dependents.

#### Technical review iteration

The technical review step runs in a loop until confidence is acceptable or three iterations are exhausted:

1. Run `docs-tools:docs-workflow-tech-review`
2. Read the output file and check for `Overall technical confidence: (HIGH|MEDIUM|LOW)`. If the confidence line is missing from the output, treat it as a step failure — mark the step `failed` and stop iteration.
3. If `HIGH` → mark completed, proceed
4. If `MEDIUM` or `LOW` and fewer than 3 iterations completed → run the fix skill:
   ```
   Skill: docs-tools:docs-workflow-writing, args: "<ticket> --fix-from <tech_review_output> --drafts-dir <drafts_dir>"
   ```
   Then re-run the reviewer (go to step 1)
5. After 3 iterations without reaching `HIGH` → proceed with a warning that manual review is recommended. `MEDIUM` is acceptable after max iterations; `LOW` after max iterations should ask the user whether to proceed or stop.

#### Integration confirmation gate

Before running `integrate-execute`:
1. Validate that `integrate-plan` completed successfully with a non-null output path. If `integrate-plan` has status `failed` or output is null, fail `integrate-execute` immediately — do not present the confirmation gate
2. Read the integration plan from `integrate-plan`'s output file. If the file does not exist on disk (e.g., deleted between sessions), mark `integrate-plan` as `pending` and re-run it before proceeding
3. Present a summary to the user
4. Ask: "The integration plan proposes the changes listed above. Shall I proceed?"
5. If yes → run `integrate-execute`
6. If no → mark `integrate-execute` as completed with a note that the plan is saved for manual reference; do not run the skill

This gate is defined in the orchestrator skill, not in the YAML.

### Completion

Update the progress file: `status → "completed"`.

Display a summary:
* List all output files with paths
* Note any warnings (tech review didn't reach `HIGH`, etc.)
* Show JIRA URL if a ticket was created

---

## Step Skills

Step skills follow a three-part contract: **parse args → do work → write output**. They do not manage workflow state, know about other steps, handle iteration, or handle confirmation gates.

Each step skill can be invoked directly outside the orchestrator:

```
Skill: docs-tools:docs-workflow-requirements, args: "PROJ-123 --output /tmp/reqs.md --pr https://..."
```

The skill doesn't know or care whether it's being called by the orchestrator or directly.

The agent definitions in `agents/*.md` remain unchanged throughout.

### `docs-workflow-requirements`

**Agent**: `docs-tools:requirements-analyst`

**Output**: `requirements/requirements_<ticket>_<timestamp>.md`

**Prompt**:

> Analyze documentation requirements for JIRA ticket `<TICKET>`.
>
> Manually-provided PR/MR URLs to include in analysis (merge with any auto-discovered URLs, dedup):
> - `<PR_URL_1>`
> - `<PR_URL_2>`
>
> Save your complete analysis to: `<OUTPUT_FILE>`
>
> Follow your standard analysis methodology (JIRA fetch, ticket graph traversal, PR/MR analysis, web search expansion). Format the output as structured markdown for the next stage.

The PR URL list is conditional — included only if PR URLs are provided.

**Output verification fallback**: Search `.claude/docs/requirements/*<ticket>*.md` for most recent match.

### `docs-workflow-planning`

**Agent**: `docs-tools:docs-planner`

**Input dependency**: `requirements` step output (passed as `--input`)

**Output**: `plans/plan_<ticket>_<timestamp>.md`

**Prompt**:

> Create a comprehensive documentation plan based on the requirements analysis.
>
> Read the requirements from: `<REQUIREMENTS_OUTPUT>`
>
> The plan must include:
> 1. Gap analysis (existing vs needed documentation)
> 2. Module specifications (type, title, audience, content points, prerequisites, dependencies)
> 3. Implementation order based on dependencies
> 4. Assembly structure (how modules group together)
> 5. Content sources from JIRA and PR/MR analysis
>
> Save the complete plan to: `<OUTPUT_FILE>`

**Output verification fallback**: Search `.claude/docs/plans/*<ticket>*.md` for most recent match.

### `docs-workflow-writing`

**Agent**: `docs-tools:docs-writer`

**Input dependency**: `planning` step output (passed as `--input`)

**Output**: `drafts/<ticket>/_index.md`

**Output directory structure (AsciiDoc)**:

```
.claude/docs/drafts/<ticket>/
  _index.md
  assembly_<n>.adoc
  modules/
    <concept>.adoc
    <procedure>.adoc
    <reference>.adoc
```

**Output directory structure (MkDocs, `--mkdocs`)**:

```
.claude/docs/drafts/<ticket>/
  _index.md
  mkdocs-nav.yml
  docs/
    <concept>.md
    <procedure>.md
    <reference>.md
```

**Prompt (AsciiDoc)**:

> Write complete AsciiDoc documentation based on the documentation plan for ticket `<TICKET>`.
>
> Read the plan from: `<PLANNING_OUTPUT>`
>
> **IMPORTANT**: Write COMPLETE .adoc files, not summaries or outlines.
>
> Save modules to: `<MODULES_DIR>/`
> Save assemblies to: `<DRAFTS_DIR>/`
> Create index at: `<DRAFTS_DIR>/_index.md`

**Prompt (MkDocs)**:

> Write complete Material for MkDocs Markdown documentation based on the documentation plan for ticket `<TICKET>`.
>
> Read the plan from: `<PLANNING_OUTPUT>`
>
> **IMPORTANT**: Write COMPLETE .md files with YAML frontmatter (title, description). Use Material for MkDocs conventions: admonitions, content tabs, code blocks with titles, heading hierarchy starting at `# h1`.
>
> Save pages to: `<DOCS_DIR>/`
> Create nav fragment at: `<DRAFTS_DIR>/mkdocs-nav.yml`
> Create index at: `<DRAFTS_DIR>/_index.md`

**Output verification**: Check that `_index.md` exists. It is the manifest for the entire drafts directory.

**Fix mode** (`--fix-from`):

When invoked with `--fix-from <review_output> --drafts-dir <drafts_dir>`, the writing skill operates in fix mode:

> Apply fixes to documentation drafts based on technical review feedback for ticket `<TICKET>`.
>
> Read the review report from: `<REVIEW_OUTPUT>`
> Drafts location: `<DRAFTS_DIR>/`
>
> For each issue flagged in the review:
> 1. If the fix is clear and unambiguous, apply it directly
> 2. If the issue requires broader context or judgment, skip it
> 3. Do NOT rewrite content that was not flagged
>
> Edit files in place. Do NOT create copies or new files.

In fix mode, the skill does not create new modules or restructure content. It reads the review output and applies targeted corrections to the existing drafts. The `--input` and `--output` args are not used in fix mode.

### `docs-workflow-tech-review`

**Agent**: `docs-tools:technical-reviewer`

**Input dependency**: `writing` step output (drafts directory derived from writing output path)

**Output**: `drafts/<ticket>/_technical_review.md`

**Prompt**:

> Perform a technical review of the documentation drafts for ticket `<TICKET>`.
> Source drafts location: `<DRAFTS_DIR>/`
> Review all .adoc and .md files. Follow your standard review methodology.
> Save your review report to: `<TECH_REVIEW_FILE>`
>
> The report must include an `Overall technical confidence: HIGH|MEDIUM|LOW` line.

The iteration loop (re-running with fixes between passes) is driven by the orchestrator skill, not this step skill.

### `docs-workflow-style-review`

**Agent**: `docs-tools:docs-reviewer`

**Input dependency**: `writing` step output (drafts directory derived from writing output path)

**Output**: `drafts/<ticket>/_review_report.md`

**AsciiDoc review skills**:

- Vale linting: `vale-tools:lint-with-vale`
- Red Hat docs: `docs-tools:docs-review-modular-docs`, `docs-tools:docs-review-content-quality`
- IBM Style Guide: `docs-tools:ibm-sg-audience-and-medium`, `docs-tools:ibm-sg-language-and-grammar`, `docs-tools:ibm-sg-punctuation`, `docs-tools:ibm-sg-numbers-and-measurement`, `docs-tools:ibm-sg-structure-and-format`, `docs-tools:ibm-sg-references`, `docs-tools:ibm-sg-technical-elements`, `docs-tools:ibm-sg-legal-information`
- Red Hat SSG: `docs-tools:rh-ssg-grammar-and-language`, `docs-tools:rh-ssg-formatting`, `docs-tools:rh-ssg-structure`, `docs-tools:rh-ssg-technical-examples`, `docs-tools:rh-ssg-gui-and-links`, `docs-tools:rh-ssg-legal-and-support`, `docs-tools:rh-ssg-accessibility`, `docs-tools:rh-ssg-release-notes` (if applicable)

**MkDocs review skills**: Same as AsciiDoc but omits `docs-review-modular-docs` (AsciiDoc-specific) and `rh-ssg-release-notes`.

**Prompt**:

> Review the [AsciiDoc|MkDocs Markdown] documentation drafts for ticket `<TICKET>`.
> Source drafts location: `<DRAFTS_DIR>/`
>
> **Edit files in place**. Do NOT create copies.
>
> For each file:
> 1. Run Vale linting once
> 2. Fix obvious errors where the fix is clear and unambiguous
> 3. Run documentation review skills: [skill list based on format]
> 4. Skip ambiguous issues requiring broader context
>
> Save the review report to: `<DRAFTS_DIR>/_review_report.md`

### `docs-workflow-integrate`

**Agent**: `docs-tools:docs-integrator`

**Input dependency (plan phase)**: `writing` step output (drafts directory)
**Input dependency (execute phase)**: `integrate-plan` step output (integration plan file) ; `writing` step output (drafts directory)

**Output (plan)**: `drafts/<ticket>/_integration_plan.md`
**Output (execute)**: `drafts/<ticket>/_integration_report.md`

Under `docs-orchestrator`, integration is expressed as two separate steps in the YAML (`integrate-plan` and `integrate-execute`). The confirmation gate between them lives in the orchestrator skill.

**Plan prompt**:

> Phase: PLAN
> Plan the integration of documentation drafts for ticket `<TICKET>`.
> Drafts location: `<DRAFTS_DIR>/`
> Save the integration plan to: `<INTEGRATION_PLAN_FILE>`

**Execute prompt**:

> Phase: EXECUTE
> Execute the integration plan for ticket `<TICKET>`.
> Drafts location: `<DRAFTS_DIR>/`
> Integration plan: `<INTEGRATION_PLAN_OUTPUT>`
> Save the integration report to: `<INTEGRATION_REPORT_FILE>`

### `docs-workflow-create-jira`

**No agent dispatch** — uses direct Bash/curl/Python for JIRA REST API calls.

**Input dependency**: `planning` step output (documentation plan, passed as `--plan`)

**Output**: `null` (produces a JIRA URL, not a file)

**Step-by-step logic**:

1. **Check for existing link** — Fetch parent ticket's issuelinks. If a "Document" link already exists, return immediately (no duplicate).
2. **Check project visibility** — Unauthenticated curl to `/rest/api/2/project/<PROJECT>`. HTTP 200 = public (do NOT attach detailed plan). Other = private (attach plan).
3. **Extract description** — Read the planning step output and extract 3 sections: main JTBD, JTBD relation, and information sources. Append footer with date and AI attribution.
4. **Convert to JIRA wiki markup** — Python inline script handles headings, bold, code, links, tables, numbered lists, horizontal rules.
5. **Create JIRA ticket** — POST to `/rest/api/2/issue`. Summary: `[ccs] Docs - <parent_summary>`. Issue type: Story. Component: Documentation.
6. **Link to parent ticket** — POST to `/rest/api/2/issueLink`. Type: "Document". outwardIssue: parent, inwardIssue: new ticket.
7. **Attach docs plan** — Private projects only.
8. **Return** — JIRA URL reported to user; not written to a file.

---

## Stop Hook: Workflow Completion Check

### Purpose

The Stop hook fires every time Claude finishes responding. When a documentation workflow is in progress, the hook checks one thing: is `status == "completed"` in the progress file? If not, it feeds the next incomplete step back to Claude as an instruction.

The hook does not verify tech review confidence. It does not check output file existence. Those are the orchestrator skill's job. The hook is a safety net for the case where Claude stops mid-workflow — after compaction, timeout, or misinterpreting a step result as the final output.

### Hook script: `workflow-completion-check.sh`

**Location**: `plugins/docs-tools/skills/docs-orchestrator/hooks/workflow-completion-check.sh`

```bash
#!/bin/bash
# workflow-completion-check.sh
#
# Stop hook: verify all documentation workflows are complete before
# letting Claude stop. Only activates when a progress JSON file exists.
#
# Checks only: is status == "completed" for every in-progress workflow?
# Step-level verification (output files, review confidence) is the
# orchestrator skill's responsibility.
#
# Exit codes:
#   0 = allow Claude to stop
#   2 = block stop; reason written to stderr (fed back to Claude as instruction)
#
# Requires: jq

INPUT=$(cat)

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null

# Prevent infinite loops — if the hook already triggered a continuation, allow stop
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
  exit 0
fi

# Find progress files
PROGRESS_FILES=$(ls .claude/docs/workflow/*.json 2>/dev/null)
if [ -z "$PROGRESS_FILES" ]; then
  exit 0
fi

for pfile in $PROGRESS_FILES; do
  WORKFLOW_STATUS=$(jq -r '.status' "$pfile" 2>/dev/null)

  if [ "$WORKFLOW_STATUS" != "in_progress" ]; then
    continue
  fi

  TICKET=$(jq -r '.ticket' "$pfile")
  WORKFLOW_TYPE=$(jq -r '.workflow_type' "$pfile")

  # Read step order from the progress file (written by the orchestrator)
  # This avoids hardcoding step names in the hook.
  mapfile -t STEP_ORDER < <(jq -r '.step_order[]' "$pfile" 2>/dev/null)

  if [ ${#STEP_ORDER[@]} -eq 0 ]; then
    # Fallback: jq key iteration order (adequate for unrecognized workflow types)
    mapfile -t STEP_ORDER < <(jq -r '.steps | keys[]' "$pfile" 2>/dev/null)
  fi

  # Find the first non-complete, non-skipped step
  NEXT_STEP=""
  for step in "${STEP_ORDER[@]}"; do
    STEP_STATUS=$(jq -r ".steps[\"$step\"].status // \"missing\"" "$pfile")
    case "$STEP_STATUS" in
      completed|skipped|missing) continue ;;
      *) NEXT_STEP="$step"; break ;;
    esac
  done

  if [ -n "$NEXT_STEP" ]; then
    echo "Documentation workflow '$WORKFLOW_TYPE' for $TICKET is not complete. Next step: $NEXT_STEP. Continue the workflow." >&2
    exit 2
  fi

  # All steps done but top-level status not updated — allow stop
  # (orchestrator will update it on the next iteration)
done

exit 0
```

### Exit code semantics

| Scenario | Exit code | Effect |
|---|---|---|
| No progress file exists | 0 | Claude stops normally |
| All workflows `status: completed` | 0 | Claude stops normally |
| `stop_hook_active` is true | 0 | Loop prevention — Claude stops |
| Workflow `status: in_progress`, steps remain | 2 | Claude continues; stderr fed back as instruction |

### Why the hook is this simple

The hook's job is to catch one case: Claude stopped before the workflow finished. It doesn't need to know why — it just needs to tell Claude which step is next. The orchestrator skill handles everything else:

* Output file existence verification happens inside the orchestrator (after each step)
* Tech review confidence is checked and iterated inside the orchestrator
* The hook reads `step_order` from the progress file rather than maintaining its own hardcoded array

### Infinite loop prevention

When the Stop hook returns exit 2, Claude continues. When Claude finishes and tries to stop again, the next Stop event includes `stop_hook_active: true`. The hook checks this field and exits 0, allowing Claude to stop. This gives the hook **one chance** per stop attempt to redirect Claude.

In practice, Claude typically completes all remaining steps in a single continuation because the skill instructs it to run all steps sequentially. The hook is a safety net, not a workflow driver.

---

## Hook Installation

### Setup script: `setup-hooks.sh`

**Location**: `plugins/docs-tools/skills/docs-orchestrator/scripts/setup-hooks.sh`

```bash
#!/bin/bash
# setup-hooks.sh
#
# Install docs-orchestrator hooks into .claude/settings.json.
# Safe to run multiple times.

set -e

SETTINGS_FILE=".claude/settings.json"
HOOK_SCRIPT_SRC="${CLAUDE_PLUGIN_ROOT}/skills/docs-orchestrator/hooks/workflow-completion-check.sh"
HOOK_SCRIPT_DST=".claude/hooks/workflow-completion-check.sh"

mkdir -p .claude/hooks

cp "$HOOK_SCRIPT_SRC" "$HOOK_SCRIPT_DST"
chmod +x "$HOOK_SCRIPT_DST"

if [ ! -f "$SETTINGS_FILE" ]; then
  echo '{}' > "$SETTINGS_FILE"
fi

# Add Stop hook (idempotent)
HAS_WORKFLOW_HOOK=$(jq '[(.hooks.Stop // []) | .[].hooks[]? | select(.command | contains("workflow-completion-check"))] | length' "$SETTINGS_FILE" 2>/dev/null || echo 0)

if [ "$HAS_WORKFLOW_HOOK" -gt 0 ]; then
  echo "Workflow completion hook already installed."
else
  jq '.hooks.Stop = (.hooks.Stop // []) + [{
    "hooks": [{
      "type": "command",
      "command": "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/workflow-completion-check.sh",
      "timeout": 10
    }]
  }]' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
  echo "Installed workflow completion Stop hook."
fi

# Add compaction re-injection hook (idempotent)
HAS_COMPACT_HOOK=$(jq '[(.hooks.SessionStart // []) | .[].hooks[]? | select(.command | contains("workflow"))] | length' "$SETTINGS_FILE" 2>/dev/null || echo 0)

if [ "$HAS_COMPACT_HOOK" -gt 0 ]; then
  echo "Compaction re-injection hook already installed."
else
  jq '.hooks.SessionStart = (.hooks.SessionStart // []) + [{
    "matcher": "compact",
    "hooks": [{
      "type": "command",
      "command": "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/reinject-workflow-state.sh"
    }]
  }]' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
  echo "Installed compaction re-injection hook."
fi

# Install compaction re-injection script
cat > .claude/hooks/reinject-workflow-state.sh << 'EOF'
#!/bin/bash
# Re-inject active workflow state after context compaction.
# Prints any in-progress progress files to stdout so Claude
# knows where to resume.
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null
for f in .claude/docs/workflow/*.json; do
  [ -f "$f" ] || continue
  STATUS=$(jq -r .status "$f" 2>/dev/null)
  if [ "$STATUS" = "in_progress" ]; then
    echo "=== Active workflow (re-injected after compaction) ==="
    cat "$f"
    echo ""
  fi
done
EOF
chmod +x .claude/hooks/reinject-workflow-state.sh

echo ""
echo "Setup complete. Hooks installed in $SETTINGS_FILE"
echo "Run /hooks in Claude Code to verify."
```

### What gets installed

| Hook | Event | Purpose |
|---|---|---|
| `workflow-completion-check.sh` | `Stop` | Validates workflow completion |
| `reinject-workflow-state.sh` | `SessionStart (compact)` | Re-injects active progress files after compaction |

---

## Context Re-injection After Compaction

Long workflows may trigger context compaction. The `SessionStart` hook with a `compact` matcher re-injects active progress files into context. Claude then knows which workflow is active, what steps are done, and where to resume.

The re-injection script is a standalone file (`.claude/hooks/reinject-workflow-state.sh`) rather than an inline command, making it readable and easy to extend.

---

## Resume Behavior

### Same session

Claude reads the progress file and skips completed steps. The Stop hook ensures Claude doesn't stop prematurely.

### New session

User says: `"Resume docs workflow for PROJ-123"`

1. Claude invokes `docs-tools:docs-orchestrator` with the ticket
2. The skill checks for an existing progress file
3. Claude finds `docs-workflow_proj_123.json` → reads it
4. Claude skips completed steps, resumes from first `pending` or `failed` step
5. Before running the resume step, **validate its input dependencies** — every required upstream step must have `status: "completed"` and a non-null `output` path in the progress file. If a dependency is `failed` or `pending`, the orchestrator must re-run that dependency first (or fail with an error if re-running is not possible)
6. For each upstream dependency with a non-null `output` path, verify the output file still exists on disk. If an output file was deleted between sessions, mark that step as `pending` and re-run it before proceeding
7. User can provide additional flags on resume (e.g., add `--integrate`) — Claude updates the progress file options accordingly

### After failure

Same as new session. The progress file shows which steps completed and which failed. The orchestrator identifies the failed step, validates its upstream dependencies are satisfied, and re-attempts it. If the failed step's upstream outputs are also missing (e.g., a cascading failure), the orchestrator walks back to the earliest incomplete dependency and resumes from there.

---

## Workflow Type Namespacing

Progress files are namespaced by workflow type:

```
.claude/docs/workflow/<workflow-type>_<ticket>.json
```

A user can run the full docs pipeline (`docs-workflow_proj_123.json`) and a separate review-only pass (`review-only_proj_123.json`) against the same ticket without the progress files conflicting.

---

## Design Principles

### Claude is the orchestrator

The YAML defines *what* steps exist. The orchestrator skill defines *how* to run them. Claude's intelligence handles sequencing, error recovery, and judgment calls. There is no interpreter loop written in natural language asking Claude to parse expressions and resolve filters.

### One source of truth per concern

| Concern | Owned by |
|---|---|
| Step list, order, conditions | YAML |
| Output path conventions | Orchestrator skill |
| Iteration logic | Orchestrator skill |
| Confirmation gates | Orchestrator skill |
| Progress state | Progress JSON (written by Claude) |
| Completion enforcement | Stop hook |
| Step implementation | Step skills |

### The hook does one thing

The Stop hook checks whether the workflow is complete. It does not verify output file contents, validate review confidence, or implement any business logic. Keeping it simple means it stays correct as the system evolves.

### Step skills are standalone

Every step skill works identically whether invoked by the orchestrator or directly by the user. The step skill contract (parse args → do work → write output) has no dependency on the orchestrator.

### Customization is a file edit

A team that wants a different pipeline edits `.claude/docs-orchestrator.yaml`. They do not fork any skill files, modify any plugin code, or understand Claude Code's skill system. Add a step, remove a step, swap a skill reference, reorder — all from a short YAML file they own.

---

## Example Workflows

### Full documentation workflow

```
User: Write docs for PROJ-123 --pr https://github.com/org/repo/pull/456 --integrate

Claude: [reads docs-orchestrator skill]
        [loads .claude/docs-orchestrator.yaml — or plugin default]
        [no existing progress file — creates docs-workflow_proj_123.json]
        [runs requirements → updates progress]
        [runs planning → updates progress]
        [runs writing → updates progress]
        [runs tech review → confidence MEDIUM → runs fix → re-reviews → HIGH]
        [updates progress: technical-review completed, iterations 2]
        [runs style review → updates progress]
        [reads integration plan → asks user to confirm → runs execute]
        [updates progress: status completed]
        [displays summary]

Stop hook: reads docs-workflow_proj_123.json — status: completed → exit 0
```

### Stop hook catches incomplete workflow

```
Claude: [runs requirements, planning, writing]
        [tries to stop — misinterprets writing output as final]

Stop hook: reads progress — technical-review status: pending
           → exit 2, stderr: "Workflow not complete. Next step: technical-review."

Claude: [continues with tech review, style review]
        [updates progress: status completed]

Stop hook: status: completed → exit 0
```

### Review-only (direct skill invocation)

```
User: Run a technical and style review on the docs in ./modules/

Claude: [invokes docs-workflow-tech-review directly]
        [invokes docs-workflow-style-review directly]
        [displays results]
```

For simple tasks, Claude invokes step skills directly without the orchestrator.

### Custom team workflow

```
User: Write docs for PROJ-123

# .claude/docs-orchestrator.yaml adds a peer-review step:
# steps: [requirements, planning, writing, peer-review, technical-review, style-review]

Claude: [loads .claude/docs-orchestrator.yaml]
        [runs requirements, planning, writing]
        [runs peer-review-request (custom skill)]
        [runs technical-review, style-review]
        [completes]
```

---

## Migration Path

Teams can adopt `docs-orchestrator` incrementally:

1. Run `setup-hooks.sh` to install Stop and compaction hooks (one time per project)
2. Invoke `docs-tools:docs-orchestrator` — it works out of the box with the plugin's default YAML
3. Optionally copy the default YAML to `.claude/docs-orchestrator.yaml` and customize it
4. Create step skills for any team-specific stages following the step skill contract

The existing `docs-workflow` command continues to work unchanged throughout.

### Implementation steps

1. Create step skills (can reuse agent definitions from `docs-workflow`)
2. Create `docs-orchestrator.md` skill
3. Create `defaults/docs-orchestrator.yaml` (the default step list)
4. Create `workflow-completion-check.sh` Stop hook
5. Create `setup-hooks.sh` installation helper
6. Update plugin README with setup instructions
7. Update `marketplace.json` to register `docs-orchestrator`

---

## Testing

### YAML loading

* Plugin default is used when no `.claude/docs-orchestrator.yaml` exists
* User YAML takes precedence over plugin default
* `--workflow <name>` loads `.claude/docs-<name>.yaml`
* Non-fully-qualified skill references in YAML fail at load time
* Step list with unsatisfied input dependencies fails at load time
* Duplicate step names in YAML fail at load time

### Orchestrator skill

* Full pipeline executes all steps in order
* Conditional steps (`when: integrate`) are skipped when flag absent
* Conditional steps run when flag present
* Skipped steps appear in progress file with `status: "skipped"`
* `step_order` array in progress file matches YAML step order
* Tech review iteration stops at `HIGH` confidence
* Tech review iterates on `MEDIUM`/`LOW` up to 3 attempts
* After 3 iterations, `MEDIUM` is accepted with warning; `LOW` prompts user confirmation
* Tech review output missing confidence line marks step as `failed`
* Integration confirmation gate asks before running `integrate-execute`
* Declining confirmation marks `integrate-execute` completed without running it
* Resume detects existing progress file and skips completed steps
* Resume validates output files still exist on disk; resets steps with missing outputs to `pending`
* Resume validates input dependencies before re-running a failed step
* New flags on resume update progress file options

### Input dependency validation

* Step with missing upstream output fails immediately with a clear error message
* Step with upstream step in `failed` status fails immediately
* Custom YAML missing a required upstream step fails at load time (e.g., workflow has `writing` but no `planning`)
* Custom YAML with all dependencies satisfied loads successfully
* `create-jira` without `planning` in step list fails at load time

### Stop hook

* Exit 0 when no progress file exists
* Exit 0 when all workflows `status: completed`
* Exit 0 when `stop_hook_active: true`
* Exit 2 with correct next step when workflow `status: in_progress`
* Reads `step_order` from progress file (not hardcoded)
* Falls back to `jq` key iteration if `step_order` is missing
* Handles multiple concurrent progress files (different tickets or workflow types)

### Step skills

* Each skill works when invoked directly (no orchestrator)
* Each skill works when invoked by the orchestrator
* Output files are written to the path specified in args
* Tech review report includes `Overall technical confidence: HIGH|MEDIUM|LOW` line

### Hook installation

* `setup-hooks.sh` is idempotent — safe to run multiple times
* Both hooks appear in `/hooks` after installation
* Compaction re-injection script prints active progress files to stdout

---

## Open Questions

1. ~~**YAML validation**~~ — **Resolved**: The orchestrator validates the YAML at load time (step 4 of "Load the step list"): unique step names, fully qualified skill references, and input dependency satisfaction. This catches broken custom workflows early rather than mid-pipeline.

2. **Multiple YAML files** — Should `.claude/docs-orchestrator/` subdirectory support be added for teams with many workflow types, or is flat files (`docs-review-only.yaml`, `docs-onboarding.yaml`) sufficient?

3. **Step output for create-jira** — The JIRA step produces a URL, not a file. Currently the progress file records `output: null` for this step. A future improvement could add an `output_url` field for richer status display, but this is YAGNI until teams need it.
