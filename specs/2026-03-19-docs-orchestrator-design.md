# Design Spec: Generic Docs Orchestrator Skill

**Date**: 2026-03-19
**Status**: Draft
**Scope**: `plugins/docs-tools/`
**Related**: `specs/2026-03-18-docs-workflow-decomposition-design.md` (step skill decomposition)

## Problem

The `docs-workflow` command works but its orchestration logic is hardcoded — the dispatch table, stage ordering, conditional logic, and iteration rules are all embedded in markdown instructions. This means:

- **Every team gets the same pipeline** — no way to add, remove, or reorder stages without forking the orchestrator
- **New workflows require new orchestrator skills** — a review-only workflow or a simplified onboarding workflow each need their own hardcoded orchestrator
- **Orchestration logic is not testable** — it lives in natural-language instructions, not structured data

## Solution

Create a **new `docs-orchestrator` skill** that reads workflow definitions from a user-defined YAML file. The YAML declares params, steps, conditions, iteration rules, and confirmation gates. Claude interprets the YAML at runtime — there is no Python workflow engine. The orchestrator skill provides the rules for how to interpret the YAML; `workflow_state.py` handles state persistence.

The existing `docs-workflow` command continues to work unchanged. `docs-orchestrator` is a **new, parallel capability** — teams adopt it when they want composable, YAML-driven workflows. Over time, `docs-workflow` may be re-expressed as a `docs-orchestrator.yaml` definition, but that migration is not part of this spec.

Teams define their own `.claude/docs-orchestrator.yaml` (or multiple files in `.claude/docs-orchestrator/`) and compose workflows from any available skills.

## Architecture

```
.claude/docs-orchestrator.yaml          ← Team-defined workflow
     |
     v
docs-orchestrator skill                 ← Generic orchestrator (reads YAML, dispatches skills)
     |
     +-- workflow_state.py              ← State CRUD (init, next-step, complete, resume)
     |
     +-- Skill: step-1-skill            ← Step skills (existing, independent)
     +-- Skill: step-2-skill
     +-- ...
```

The orchestrator is **workflow-agnostic** — it knows how to read YAML, resolve templates, manage state, handle iteration/confirmation, and invoke skills. It does not know anything about JIRA, AsciiDoc, Vale, or any domain.

## YAML Schema

### Workflow definition file

**Location**: `.claude/docs-orchestrator.yaml` (single workflow) or `.claude/docs-orchestrator/<name>.yaml` (multiple workflows).

The workflow YAML is the single source of truth for all orchestration metadata — params, preflight, step definitions, and wiring. No sidecar files or custom frontmatter. Claude Code does not support custom frontmatter fields, so all orchestration config lives in the YAML.

The YAML supports shorthand syntax for common patterns, keeping simple workflows concise while allowing full control when needed.

```yaml
workflow:
  name: <string>                        # Optional — inferred from filename
  description: <string>                 # Optional

  params:                               # Declared parameters
    <param_name>:
      type: string | bool | list | choice
      required: <bool>                  # Default: false
      default: <value>                  # Default value (required if required is false)
      flag: <string>                    # CLI flag (e.g., --pr, --mkdocs, --integrate)
      flag_value: <string>              # For choice params: what value the flag sets
                                        # Only one flag maps to one value. Unmatched
                                        # choices use the default.
      choices: [<values>]              # For type: choice — allowed values
      accumulate: <bool>               # For list params: repeated flags append
      description: <string>

  preflight:                            # Optional pre-execution checks
    - check: env
      var: <string>                     # Environment variable name
      source: <string>                  # File to source if var is unset (e.g., ~/.env)
      required: <bool>                  # true = fail if missing, false = warn

  output_base: <string>                # Base directory for all outputs
                                        # Default: .claude/docs
                                        # Supports {param} templates

  steps:                                # Ordered list of step definitions
    - <step definition>                 # See Step Schema below
```

### Step schema

```yaml
- skill: <string>                       # REQUIRED — fully qualified skill name (plugin:skill)
  name: <string>                        # Optional — defaults to last segment of skill name
  description: <string>                 # Optional — defaults to skill's frontmatter description

  args: <string>                        # Template string passed as skill args
                                        # Resolved by orchestrator before invocation

  output: <string>                      # Output file path pattern, relative to output_base
                                        # null for steps with no file output (e.g., JIRA creation)

  when: <string>                        # Shorthand condition — just a param name (truthy check)
  condition: <string>                   # Full condition — expression with == or !=

  iterate:                              # Optional — step runs in a loop (longhand)
    max: <int>                          # Maximum iterations (required)
    check:
      file: <string>                    # Template — file to read after each iteration
      pattern: <string>                 # Regex with one capture group to extract a value
      done_when: <string>               # Value that means "stop iterating"
    fix:
      skill: <string>                   # Skill to invoke between iterations
      args: <string>                    # Template string for fix skill args

  # Shorthand: iterate: <int>          # Just max — check/fix must be in longhand

  confirm:                              # Optional — ask user before running this step (longhand)
    prompt: <string>                    # Question to present (supports {templates})
    show_file: <string>                 # Template — file to read and display before asking
    on_decline: complete | skip         # complete = mark step done, skip = skip entirely

  # Shorthand: confirm: "<string>"     # Just prompt — show_file defaults to previous step output,
                                        # on_decline defaults to complete
```

### Shorthand expansions

| Shorthand | Expands to |
|---|---|
| `when: integrate` | `condition: "{integrate} == true"` (bool params) |
| `when: create_jira_project` | `condition: "{create_jira_project} != null"` (string/list params) |
| `iterate: 3` | `iterate: { max: 3 }` — runs unconditionally N times (no convergence check). If `check` and `fix` are needed, use the longhand object form |
| `confirm: "Proceed?"` | `confirm: { prompt: "Proceed?", show_file: <previous step's output>, on_decline: complete }` |

The `when` shorthand infers the comparison operator from the param type: `== true` for bool params, `!= null` for string/list params.

### Conventions (fields inferred when omitted)

| Field | Convention when omitted |
|---|---|
| `workflow.name` | Inferred from filename (`docs-orchestrator.yaml` → `docs-orchestrator`) |
| `step.name` | Last segment of skill name (`docs-tools:docs-workflow-requirements` → `docs-workflow-requirements`) |
| `step.description` | Read from the skill's frontmatter `description` (a standard Claude Code field) |
| `output_base` | `.claude/docs` |
| `confirm.on_decline` | `complete` |
| `confirm.show_file` | Previous step's output path |

### Template resolution

Template strings use `{...}` delimiters. The orchestrator resolves them before passing args to skills or evaluating conditions.

| Reference | Resolves to | Example |
|---|---|---|
| `{param_name}` | Value of a declared param | `{ticket}` → `PROJ-123` |
| `{param_name\|lower}` | Value with filter applied | `{ticket\|lower}` → `proj-123` |
| `{steps.<name>.output}` | Absolute path to a completed step's output file | `{steps.requirements.output}` → `/abs/path/to/requirements.md` |
| `{output}` | This step's resolved output path (absolute) | `{output}` → `/abs/path/to/drafts/proj-123/_index.md` |
| `{output_base}` | The resolved `output_base` directory (absolute) | `{output_base}` → `/abs/path/to/.claude/docs` |
| `{timestamp}` | Current timestamp (`YYYYMMDD_HHMMSS`), resolved once at step start (not re-resolved on iteration re-dispatch) | `{timestamp}` → `20260319_143022` |

**Filters** (applied with `|`):

| Filter | Effect | Example |
|---|---|---|
| `lower` | Lowercase | `{ticket\|lower}` → `proj-123` |
| `upper` | Uppercase | `{ticket\|upper}` → `PROJ-123` |
| `safe` | Lowercase + replace hyphens with underscores | `{ticket\|safe}` → `proj_123` |
| `join:,` | Join list values with delimiter | `{pr_urls\|join:,}` → `url1,url2` |
| `repeat:--pr` | Expand list as repeated flags | `{pr_urls\|repeat:--pr}` → `--pr url1 --pr url2` |

**Condition expressions:**

Conditions are simple comparisons evaluated by the orchestrator:

```yaml
condition: "{integrate} == true"              # Bool param check
condition: "{create_jira_project} != null"    # Null check
condition: "{format} == mkdocs"               # Choice param check
```

Supported operators: `==`, `!=`. Values are compared as strings after template resolution. `null` is a special literal meaning "the param's value is null/unset."

### List param handling in args

For list params (like `pr_urls`), the args template determines how the list is serialized:

```yaml
# Repeated flags (most common):
args: "{ticket} {pr_urls|repeat:--pr} --output {output}"
# Resolves to: "PROJ-123 --pr https://url1 --pr https://url2 --output /path/out.md"

# Comma-separated:
args: "{ticket} --urls {pr_urls|join:,} --output {output}"
# Resolves to: "PROJ-123 --urls https://url1,https://url2 --output /path/out.md"
```

If a list param is empty, the template segment resolves to an empty string (the flag is omitted entirely).

## Default Workflow Definition

When no `.claude/docs-orchestrator.yaml` exists in the user's repo, the orchestrator writes the following default on first run. This default mirrors the existing `docs-workflow` command pipeline — same stages, same order, same options — so that `docs-orchestrator` works out of the box with identical behavior.

The user can then customize this file: reorder steps, remove stages they don't need, add team-specific stages, or change iteration/confirmation behavior.

### Default YAML (written to `.claude/docs-orchestrator.yaml`)

```yaml
workflow:
  name: docs-workflow
  description: >
    Multi-stage documentation workflow for a JIRA ticket.
    Orchestrates skills sequentially: requirements analysis, planning,
    writing, technical review, style review, and optionally integration
    and JIRA creation.

  params:
    ticket:
      type: string
      required: true
      description: JIRA ticket ID (e.g., PROJ-123)

    pr_urls:
      type: list
      default: []
      flag: --pr
      accumulate: true
      description: PR/MR URLs to include in analysis

    format:
      type: choice
      choices: [adoc, mkdocs]
      default: adoc
      flag: --mkdocs
      flag_value: mkdocs
      description: Output format (AsciiDoc or Material for MkDocs)

    integrate:
      type: bool
      default: false
      flag: --integrate
      description: Integrate drafts into the repo build framework

    create_jira_project:
      type: string
      default: null
      flag: --create-jira
      description: JIRA project key for docs ticket creation

  preflight:
    - check: env
      var: JIRA_AUTH_TOKEN
      source: ~/.env
      required: true
    - check: env
      var: GITHUB_TOKEN
      source: ~/.env
      required: false
    - check: env
      var: GITLAB_TOKEN
      source: ~/.env
      required: false

  output_base: .claude/docs

  steps:
    - name: requirements
      skill: docs-tools:docs-workflow-requirements
      description: Analyze documentation requirements
      output: requirements/requirements_{ticket|safe}_{timestamp}.md
      args: "{ticket} {pr_urls|repeat:--pr} --output {output}"

    - name: planning
      skill: docs-tools:docs-workflow-planning
      description: Create documentation plan
      output: plans/plan_{ticket|safe}_{timestamp}.md
      args: "{ticket} --input {steps.requirements.output} --output {output}"

    - name: writing
      skill: docs-tools:docs-workflow-writing
      description: Write documentation drafts
      output: drafts/{ticket|lower}/_index.md
      args: "{ticket} --input {steps.planning.output} --output {output} --format {format}"

    - name: technical-review
      skill: docs-tools:docs-workflow-tech-review
      description: Technical accuracy review
      output: drafts/{ticket|lower}/_technical_review.md
      args: "{ticket} --drafts-dir {output_base}/drafts/{ticket|lower} --output {output}"
      iterate:
        max: 3
        check:
          file: "{output}"
          pattern: "Overall technical confidence:\\s*(HIGH|MEDIUM|LOW)"
          done_when: HIGH
        fix:
          skill: docs-tools:docs-workflow-writing
          args: "{ticket} --fix-from {output} --drafts-dir {output_base}/drafts/{ticket|lower}"

    - name: style-review
      skill: docs-tools:docs-workflow-style-review
      description: Style guide compliance review
      output: drafts/{ticket|lower}/_review_report.md
      args: "{ticket} --drafts-dir {output_base}/drafts/{ticket|lower} --output {output} --format {format}"

    - name: integrate-plan
      skill: docs-tools:docs-workflow-integrate
      description: Plan integration into build framework
      condition: "{integrate} == true"
      output: drafts/{ticket|lower}/_integration_plan.md
      args: "{ticket} --phase plan --drafts-dir {output_base}/drafts/{ticket|lower} --output {output}"

    - name: integrate-execute
      skill: docs-tools:docs-workflow-integrate
      description: Execute integration
      condition: "{integrate} == true"
      output: drafts/{ticket|lower}/_integration_report.md
      args: "{ticket} --phase execute --drafts-dir {output_base}/drafts/{ticket|lower} --plan {steps.integrate-plan.output} --output {output}"
      confirm:
        prompt: "The integration plan proposes the changes listed above. Shall I proceed with the integration?"
        show_file: "{steps.integrate-plan.output}"
        on_decline: complete

    - name: create-jira
      skill: docs-tools:docs-workflow-create-jira
      description: Create linked JIRA ticket
      condition: "{create_jira_project} != null"
      output: null
      args: "{ticket} --project {create_jira_project} --plan {steps.planning.output}"
```

### Design notes on the default workflow

1. **Integration is two steps, not one.** The old monolith used a phase state machine inside a single stage. The YAML expresses this as two steps (`integrate-plan`, `integrate-execute`) with a `confirm` gate on the second. This is cleaner — no phase concept needed in the orchestrator.

2. **Tech review iteration is declarative.** The `iterate` block tells the orchestrator to loop: run the step, check output, optionally run a fix skill, repeat. The orchestrator handles the loop counter and convergence check.

3. **Null output for create-jira.** The JIRA step produces a URL, not a file. Setting `output: null` tells the orchestrator to skip output verification. The step skill is responsible for updating state with whatever result it produces.

4. **Filters handle ticket casing.** `{ticket|safe}` produces `proj_123` for file paths, `{ticket|lower}` produces `proj-123` for directory names.

## Component Inventory

### New files

```
plugins/docs-tools/skills/
  docs-orchestrator/
    docs-orchestrator.md                      # Generic orchestrator skill (~300 lines)
    defaults/
      docs-orchestrator.yaml                  # Default workflow definition (docs-workflow pipeline)
    scripts/
      workflow_state.py                       # State management (~150 lines)
```

The `defaults/docs-orchestrator.yaml` file is the source of truth for the default workflow. On first run, if no `.claude/docs-orchestrator.yaml` exists in the user's repo, the orchestrator copies this file to `.claude/docs-orchestrator.yaml`.

### Step skills

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

Each step skill follows the step skill contract (see "Step Skill Contract" section): parse args, do work, write output. Under `docs-orchestrator`, step skills do **not** manage state — the orchestrator handles all state transitions. The agent definitions in `agents/*.md` remain unchanged.

#### `docs-workflow-requirements`

**Agent**: `docs-tools:requirements-analyst`

**Output**: `requirements/requirements_{ticket|safe}_{timestamp}.md`

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

The PR URL bullet list is conditional — included only if PR URLs are provided.

**Output verification fallback**: Search `.claude/docs/requirements/*<safe_ticket>*.md` for most recent match.

#### `docs-workflow-planning`

**Agent**: `docs-tools:docs-planner`

**Output**: `plans/plan_{ticket|safe}_{timestamp}.md`

**Inputs**: Previous step output (`{steps.requirements.output}`)

**Prompt**:

> Create a comprehensive documentation plan based on the requirements analysis.
>
> Read the requirements from: `<PREV_OUTPUT>`
>
> The plan must include:
> 1. Gap analysis (existing vs needed documentation)
> 2. Module specifications (type, title, audience, content points, prerequisites, dependencies)
> 3. Implementation order based on dependencies
> 4. Assembly structure (how modules group together)
> 5. Content sources from JIRA and PR/MR analysis
>
> Save the complete plan to: `<OUTPUT_FILE>`
>
> Use structured markdown with clear sections for each module.

#### `docs-workflow-writing`

**Agent**: `docs-tools:docs-writer`

**Output**: `drafts/{ticket|lower}/_index.md`

**Inputs**: Previous step output (`{steps.planning.output}`), format param

**Output directory structure (AsciiDoc, default)**:

```
.claude/docs/drafts/<ticket>/
  _index.md
  assembly_<name>.adoc
  modules/
    <concept>.adoc
    <procedure>.adoc
    <reference>.adoc
```

**Output directory structure (MkDocs, `format == mkdocs`)**:

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
> Read the plan from: `<PREV_OUTPUT>`
>
> **IMPORTANT**: Write COMPLETE .adoc files, not summaries or outlines.
>
> Output folder structure:
> ```
> <DRAFTS_DIR>/
> +-- _index.md
> +-- assembly_<name>.adoc
> +-- modules/
>     +-- <concept-name>.adoc
>     +-- <procedure-name>.adoc
>     +-- <reference-name>.adoc
> ```
>
> Save modules to: `<MODULES_DIR>/`
> Save assemblies to: `<DRAFTS_DIR>/`
> Create index at: `<DRAFTS_DIR>/_index.md`

**Prompt (MkDocs)**:

> Write complete Material for MkDocs Markdown documentation based on the documentation plan for ticket `<TICKET>`.
>
> Read the plan from: `<PREV_OUTPUT>`
>
> **IMPORTANT**: Write COMPLETE .md files with YAML frontmatter (title, description), not summaries or outlines. Use Material for MkDocs conventions: admonitions, content tabs, code blocks with titles, and proper heading hierarchy starting at `# h1`.
>
> Output folder structure:
> ```
> <DRAFTS_DIR>/
> +-- _index.md
> +-- mkdocs-nav.yml
> +-- docs/
>     +-- <concept-name>.md
>     +-- <procedure-name>.md
>     +-- <reference-name>.md
> ```
>
> Save pages to: `<DOCS_DIR>/`
> Create nav fragment at: `<DRAFTS_DIR>/mkdocs-nav.yml`
> Create index at: `<DRAFTS_DIR>/_index.md`

**Output verification**: Check that `_index.md` exists at the output path. The `_index.md` serves as the manifest for the entire drafts directory.

#### `docs-workflow-tech-review`

**Agent (reviewer)**: `docs-tools:technical-reviewer`
**Agent (fix)**: `docs-tools:docs-writer`

**Output**: `drafts/{ticket|lower}/_technical_review.md`

This is the most complex step skill because the orchestrator drives its review-fix iteration loop via the `iterate` block in the YAML.

**Reviewer prompt**:

> Perform a technical review of the documentation drafts for ticket `<TICKET>`.
> Source drafts location: `<DRAFTS_DIR>/`
> Review all .adoc and .md files. Follow your standard review methodology.
> Save your review report to: `<TECH_REVIEW_FILE>`

**Fix prompt** (dispatched by the orchestrator between iterations):

> The technical reviewer found issues in the documentation for ticket `<TICKET>`.
> Read the technical review report at: `<TECH_REVIEW_FILE>`
> Address all Critical issues and Significant issues.
> Edit draft files in place at `<DRAFTS_DIR>/`.
> Do NOT address minor issues or style concerns.

**Iteration**: The orchestrator checks the output file for `Overall technical confidence: (HIGH|MEDIUM|LOW)`. Iteration stops on `HIGH` or after 3 attempts.

**Note on `subagent_type`**: Throughout this spec, agent references (e.g., `docs-tools:technical-reviewer`) refer to agent definitions in `agents/*.md`, not skills. This matches the Claude Code Agent tool convention where `subagent_type` loads agent markdown files as the subagent's system instructions.

#### `docs-workflow-style-review`

**Agent**: `docs-tools:docs-reviewer`

**Output**: `drafts/{ticket|lower}/_review_report.md`

**Inputs**: Format param determines which review skills to include

**AsciiDoc review skills**:

- Vale linting: `vale-tools:lint-with-vale`
- Red Hat docs: `docs-tools:docs-review-modular-docs`, `docs-tools:docs-review-content-quality`
- IBM Style Guide: `docs-tools:ibm-sg-audience-and-medium`, `docs-tools:ibm-sg-language-and-grammar`, `docs-tools:ibm-sg-punctuation`, `docs-tools:ibm-sg-numbers-and-measurement`, `docs-tools:ibm-sg-structure-and-format`, `docs-tools:ibm-sg-references`, `docs-tools:ibm-sg-technical-elements`, `docs-tools:ibm-sg-legal-information`
- Red Hat SSG: `docs-tools:rh-ssg-grammar-and-language`, `docs-tools:rh-ssg-formatting`, `docs-tools:rh-ssg-structure`, `docs-tools:rh-ssg-technical-examples`, `docs-tools:rh-ssg-gui-and-links`, `docs-tools:rh-ssg-legal-and-support`, `docs-tools:rh-ssg-accessibility`, `docs-tools:rh-ssg-release-notes` (if applicable)

**MkDocs review skills**: Same as AsciiDoc but omits `docs-review-modular-docs` (AsciiDoc-specific) and `rh-ssg-release-notes`.

**Prompt**:

> Review the [AsciiDoc|MkDocs Markdown] documentation drafts for ticket `<TICKET>`.
>
> Source drafts location: `<DRAFTS_DIR>/`
>
> **Edit files in place** in the drafts folder. Do NOT create copies.
>
> For each file:
> 1. Run Vale linting once
> 2. Fix obvious errors where the fix is clear and unambiguous
> 3. Run documentation review skills: [skill list based on format]
> 4. Skip ambiguous issues that require broader context
>
> Save the review report to: `<DRAFTS_DIR>/_review_report.md`
>
> The report must include:
> - Summary of files reviewed
> - Vale linting results (errors, warnings, suggestions)
> - Issues found by each review skill (with file:line references)
> - Fixes applied
> - Remaining issues requiring manual review

#### `docs-workflow-integrate`

**Agent**: `docs-tools:docs-integrator`

**Output (plan)**: `drafts/{ticket|lower}/_integration_plan.md`
**Output (execute)**: `drafts/{ticket|lower}/_integration_report.md`

Under `docs-orchestrator`, integration is expressed as **two separate steps** in the YAML (`integrate-plan` and `integrate-execute`) rather than a single skill with a phase state machine. The orchestrator handles the confirm gate between them. Each step is a single agent dispatch:

**Plan prompt**:

> Phase: PLAN
> Plan the integration of documentation drafts for ticket `<TICKET>`.
> Drafts location: `<DRAFTS_DIR>/`
> Save the integration plan to: `<INTEGRATION_PLAN_FILE>`

**Execute prompt**:

> Phase: EXECUTE
> Execute the integration plan for ticket `<TICKET>`.
> Drafts location: `<DRAFTS_DIR>/`
> Integration plan: `<INTEGRATION_PLAN_FILE>`
> Save the integration report to: `<INTEGRATION_REPORT_FILE>`

The `confirm` gate on `integrate-execute` (defined in the YAML) reads the plan file and asks the user before proceeding. If declined, the step is marked complete with the plan saved for manual reference.

#### `docs-workflow-create-jira`

**No agent dispatch** — uses direct Bash/curl/Python for JIRA REST API calls.

**Output**: `null` (produces a JIRA URL, not a file)

**Inputs**: `create_jira_project` param (target JIRA project key), planning step output (documentation plan to extract description)

**Step-by-step logic**:

1. **Check for existing link** — Fetch parent ticket's issuelinks via JIRA REST API. If a "Document" link with inwardIssue already exists, return immediately (no duplicate — the orchestrator marks the step completed).
2. **Check project visibility** — Unauthenticated curl to `/rest/api/2/project/<PROJECT>`. HTTP 200 = public (do NOT attach detailed plan). Other = private (attach plan).
3. **Extract description** — Read the planning step output and extract 3 sections: main JTBD, JTBD relation, and information sources. Append footer with date and AI attribution.
4. **Convert to JIRA wiki markup** — Python inline script handles headings, bold, code, links, tables, numbered lists, horizontal rules.
5. **Create JIRA ticket** — POST to `/rest/api/2/issue`. Summary: `[ccs] Docs - <parent_summary>`. Issue type: Story. Component: Documentation.
6. **Link to parent ticket** — POST to `/rest/api/2/issueLink`. Type: "Document" (singular). outwardIssue: parent (shows "documents"), inwardIssue: new ticket (shows "is documented by").
7. **Attach docs plan** — Private projects only. POST to `/rest/api/2/issue/<NEW_KEY>/attachments` with plan file.
8. **Return** — The orchestrator records completion. The JIRA URL is reported to the user but not written to a file (`output: null`).

### User-created files (per team/repo)

```
.claude/
  docs-orchestrator.yaml                      # Single workflow
  # OR
  docs-orchestrator/
    docs-workflow.yaml                        # Multiple workflows
    review-only.yaml
```

### Existing files (unchanged)

- `commands/docs-workflow.md` — continues to work as-is; `docs-orchestrator` is a new parallel capability, not a replacement

## Orchestrator Skill: `docs-orchestrator.md`

**Location**: `plugins/docs-tools/skills/docs-orchestrator/docs-orchestrator.md`

### Frontmatter

```yaml
---
name: docs-orchestrator
description: >
  Generic workflow orchestrator. Reads workflow definitions from
  .claude/docs-orchestrator.yaml and executes steps sequentially,
  handling iteration, confirmation gates, and conditional execution.
  Workflow-agnostic — all domain logic lives in step skills.
argument-hint: <action> [workflow-name] <params...>
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, AskUserQuestion, WebSearch, WebFetch
---
```

### Actions

| Action | Usage | Description |
|---|---|---|
| `start` | `start [workflow] <params...>` | Begin a new workflow run |
| `resume` | `resume [workflow] <identifier>` | Resume a paused/failed workflow |
| `status` | `status [workflow] <identifier>` | Show workflow progress |
| `list` | `list` | List available workflows from YAML files |

When only one workflow YAML exists, the workflow name can be omitted.

### Orchestrator pseudocode

```
## Step 1: Locate workflow definition

Search for YAML files:
  1. .claude/docs-orchestrator.yaml (single workflow)
  2. .claude/docs-orchestrator/<name>.yaml (named workflow)

If NO YAML file exists:
  Write the default workflow definition to .claude/docs-orchestrator.yaml.
  The default is the docs-workflow reference implementation (see
  "Default workflow definition" section below).
  Inform the user: "No workflow definition found. Created default
  docs-workflow definition at .claude/docs-orchestrator.yaml.
  You can customize this file to change the workflow pipeline."

If multiple workflows exist and no name was provided, list them and ask.
Parse the YAML and validate against the schema.

## Step 2: Parse params

Map CLI args to declared params:
  - Positional args fill required params in declaration order
  - Flags (--pr, --mkdocs, etc.) set their declared params
  - Accumulate flags (--pr url1 --pr url2) build list params
  - Flag-value mappings (--mkdocs → format: mkdocs) are applied
  - Missing required params → STOP, ask user
  - Missing optional params → use declared defaults

## Step 3: Run preflight checks

For each preflight entry:
  - check: env → verify environment variable is set
    If unset and source is specified, attempt to source the file
    If required and still unset → STOP with error
    If not required and unset → WARN and continue

## Step 4: Initialize or load state

Compute state file path:
  STATE_DIR = <output_base>/workflow/
  IDENTIFIER = first required param value (e.g., ticket)
  STATE_FILE = STATE_DIR/<workflow-name>_<identifier|safe>.json

For "start" action:
  python3 scripts/workflow_state.py init \
    --workflow <name> --identifier <id> --steps <step-names-json> --params <params-json>

For "resume" action:
  python3 scripts/workflow_state.py load --workflow <name> --identifier <id>
  Apply any new flag values (e.g., additional --pr URLs on resume)

For "status" action:
  python3 scripts/workflow_state.py status --workflow <name> --identifier <id>
  Display and STOP.

## Step 5: Dispatch loop

Loop:
  NEXT = python3 scripts/workflow_state.py next-step \
    --workflow <name> --identifier <id> --conditions <resolved-conditions-json>

  If NEXT is "done", break.

  Resolve the step definition from the YAML.

  ### 5a: Confirm gate (if step has `confirm`)
  If the step has a `confirm` block:
    1. Read the file at confirm.show_file (resolved template)
    2. Present a summary of the file contents to the user
    3. Ask the user: confirm.prompt (resolved template, via AskUserQuestion)
    4. If user declines:
       - on_decline == "complete" →
           complete-step (mark done without running), continue to next
       - on_decline == "skip" →
           skip-step (mark skipped), continue to next
    5. If user confirms → proceed to 5b

  ### 5b: Mark step in progress
  python3 scripts/workflow_state.py start-step \
    --workflow <name> --identifier <id> --step <step-name>

  ### 5c: Resolve templates
  Resolve all {templates} in the step's `args` and `output`:
    - {param} → param value
    - {param|filter} → filtered param value
    - {steps.<name>.output} → completed step's output path from state
    - {output} → this step's resolved output path (output_base + output pattern)
    - {output_base} → resolved output base directory
    - {timestamp} → current timestamp

  Ensure output directory exists (mkdir -p).

  ### 5d: Dispatch skill
  Invoke the step skill:
    Skill: <step.skill>, args: "<resolved args>"

  ### 5e: Handle iteration (if step has `iterate`)
  After skill returns:
    1. Increment iteration counter in state

    If iterate has `check` and `fix` (longhand with convergence):
      2. Read iterate.check.file (resolved)
      3. Extract value using iterate.check.pattern (regex)
      4. If extracted value == iterate.check.done_when →
         proceed to 5f (verify output and mark completed)
      5. If iterations < iterate.max:
         - Invoke iterate.fix.skill with resolved iterate.fix.args
         - Go back to 5d (re-dispatch the main skill)
      6. If iterations >= iterate.max →
         proceed to 5f with warning that manual review is recommended

    If iterate is shorthand (max only, no check/fix):
      2. If iterations < iterate.max → go back to 5d (re-dispatch)
      3. If iterations >= iterate.max → proceed to 5f

  ### 5f: Verify output (if step has `output`)
  If step.output is not null:
    - Verify the resolved output file exists
    - If not found, search the output directory for recent matching files
    - If still not found → fail-step, STOP

  ### 5g: Mark step completed
  python3 scripts/workflow_state.py complete-step \
    --workflow <name> --identifier <id> --step <step-name> --output <output-path>

  Loop back to next-step.

  NOTE: Steps 5f and 5g always run after 5e completes (whether via
  done_when match or max iterations). The iteration loop at 5e only
  loops back to 5d — it never skips 5f/5g.

## Step 6: Completion

python3 scripts/workflow_state.py complete-workflow \
  --workflow <name> --identifier <id>

Display final status summary.
```

## State Management

### State file schema

```json
{
  "workflow": "docs-workflow",
  "identifier": "proj-123",
  "created_at": "2026-03-19T10:00:00Z",
  "updated_at": "2026-03-19T12:34:56Z",
  "status": "in_progress",
  "current_step": "writing",
  "params": {
    "ticket": "PROJ-123",
    "pr_urls": ["https://github.com/org/repo/pull/456"],
    "format": "adoc",
    "integrate": false,
    "create_jira_project": null
  },
  "steps": {
    "requirements": {
      "status": "completed",
      "output": "/abs/path/to/requirements_proj_123_20260319.md",
      "started_at": "2026-03-19T10:01:00Z",
      "completed_at": "2026-03-19T10:05:00Z",
      "iterations": 0
    },
    "planning": {
      "status": "completed",
      "output": "/abs/path/to/plan_proj_123_20260319.md",
      "started_at": "2026-03-19T10:05:00Z",
      "completed_at": "2026-03-19T10:12:00Z",
      "iterations": 0
    },
    "writing": {
      "status": "in_progress",
      "output": null,
      "started_at": "2026-03-19T10:12:00Z",
      "completed_at": null,
      "iterations": 0
    },
    "integrate-execute": {
      "status": "skipped",
      "output": null,
      "started_at": null,
      "completed_at": "2026-03-19T12:00:00Z",
      "iterations": 0
    }
  }
}
```

### State file location

```
<output_base>/workflow/<workflow-name>_<identifier|safe>.json
```

Example: `.claude/docs/workflow/docs-workflow_proj_123.json`

### `workflow_state.py` commands

```
init --workflow <name> --identifier <id> --steps <json-array> --params <json-object>
    Create a new state file. Initialize all steps as pending.
    Print the state file path.

load --workflow <name> --identifier <id>
    Print the state file path. Exit 1 if not found.

status --workflow <name> --identifier <id>
    Print formatted status display with step checkmarks.

next-step --workflow <name> --identifier <id> --conditions <json-object>
    Print the name of the next incomplete step.
    The conditions object maps step names to their resolved condition
    expressions. Steps whose condition evaluates to false are skipped.
    Print "done" if all applicable steps are completed.

start-step --workflow <name> --identifier <id> --step <step-name>
    Mark step as in_progress, set started_at, update current_step.

complete-step --workflow <name> --identifier <id> --step <step-name> [--output <path>]
    Mark step as completed. Optionally record output path.

fail-step --workflow <name> --identifier <id> --step <step-name>
    Mark step and workflow as failed.

skip-step --workflow <name> --identifier <id> --step <step-name>
    Mark step as skipped. Used when a confirmation gate is declined with
    on_decline=skip, or when a conditional step is skipped in standalone mode.
    next-step treats skipped the same as completed (advances past it).

get --workflow <name> --identifier <id> <dotpath>
    Read a value from state. e.g., get ... .params.format

set --workflow <name> --identifier <id> <expression>
    Update state. e.g., set ... '.steps.technical-review.iterations += 1'

update-params --workflow <name> --identifier <id> --params <json-object>
    Merge new param values into existing state (for resume with new flags).

complete-workflow --workflow <name> --identifier <id>
    Mark overall workflow as completed.
```

### Implementation notes

- Pure Python, no `jq` dependency
- Atomic writes (`tempfile` + `os.replace`)
- `next-step` receives pre-resolved conditions as a JSON object so it can skip conditional steps without needing to parse YAML or resolve templates itself
- The `--conditions` object format: `{"integrate-plan": true, "integrate-execute": true, "create-jira": false}` — the orchestrator resolves all condition templates and passes the boolean results. Unconditional steps are omitted from the object (treated as always-true by `next-step`)
- State files from the old `docs-workflow` command are not compatible — the orchestrator creates new state files with a different schema
- `output_base` templates can only reference params (not step outputs), since it is resolved before any steps run
- `next-step` treats both `completed` and `skipped` statuses as "done" — it advances past both

## Step Skill Contract

Step skills invoked by the orchestrator follow a lightweight contract.

### What step skills receive

A single `args` string, resolved by the orchestrator. The args contain everything the skill needs — ticket ID, input file paths, output file path, format options, etc.

### What step skills must do

1. Parse their args (the skill defines its own arg format)
2. Do their work (dispatch agents, run scripts, call APIs)
3. Write their output to the path specified in args (if applicable)
4. Return — the orchestrator handles state updates

### What step skills must NOT do

- Manage workflow state (no calls to `workflow_state.py`)
- Know about other steps (no reading from state file)
- Handle iteration (the orchestrator loops, not the skill)
- Handle confirmation gates (the orchestrator asks, not the skill)

### Standalone invocation

Step skills can still be invoked directly, outside the orchestrator:

```
Skill: docs-tools:docs-workflow-requirements, args: "PROJ-123 --output /tmp/reqs.md --pr https://..."
```

The skill doesn't know or care whether it's being called by the orchestrator or directly. It just receives args and does its work.

### Relationship to docs-workflow step skills

If step skills are created following the previous decomposition spec (2026-03-18), they may call `workflow_state.py` directly (start-stage, complete-stage, etc.). Under `docs-orchestrator`, step skills are simpler — they don't touch state. The orchestrator handles all state transitions. Step skills designed for `docs-orchestrator` follow a 3-step contract: parse args → do work → write output.

Step skills can be designed to work with both systems by making state calls conditional (only if a state file is passed as an arg).

## Example: Team-Specific Workflows

### Review-only workflow (no writing)

```yaml
workflow:
  name: review-only
  description: Run style and technical review on existing drafts

  params:
    drafts_dir:
      type: string
      required: true
      description: Path to drafts directory

    format:
      type: choice
      choices: [adoc, mkdocs]
      default: adoc
      flag: --mkdocs
      flag_value: mkdocs

  output_base: .claude/docs

  steps:
    - name: technical-review
      skill: docs-tools:docs-workflow-tech-review
      description: Technical accuracy review
      output: reviews/_technical_review_{timestamp}.md
      args: "--drafts-dir {drafts_dir} --output {output}"
      iterate:
        max: 2
        check:
          file: "{output}"
          pattern: "Overall technical confidence:\\s*(HIGH|MEDIUM|LOW)"
          done_when: HIGH
        fix:
          skill: docs-tools:docs-workflow-writing
          args: "--fix-from {output} --drafts-dir {drafts_dir}"

    - name: style-review
      skill: docs-tools:docs-workflow-style-review
      description: Style guide compliance review
      output: reviews/_review_report_{timestamp}.md
      args: "--drafts-dir {drafts_dir} --output {output} --format {format}"
```

**Invocation:**

```
Skill: docs-tools:docs-orchestrator, args: "start review-only ./modules --mkdocs"
```

## YAML Validation

The orchestrator validates the YAML before execution:

### Required fields

| Field | Required | Level |
|---|---|---|
| `workflow.name` | Yes (inferred from filename if omitted) | Workflow |
| `workflow.description` | No | Workflow |
| `workflow.steps` | Yes (non-empty) | Workflow |
| `step.name` | Yes (inferred from skill name if omitted) | Step |
| `step.skill` | Yes | Step |
| `step.description` | Yes (inferred from skill frontmatter if omitted) | Step |
| `step.args` | Yes | Step |

### Validation rules

1. **Step names must be unique** — no duplicate names within a workflow
2. **Step references must be valid** — `{steps.<name>.output}` must reference a step that appears earlier in the list
3. **Required params must not have defaults** — if `required: true`, `default` is ignored
4. **Iterate longhand requires check and fix** — if `iterate` is specified as an object (longhand), both `check` and `fix` must be present. The shorthand `iterate: <int>` runs the step unconditionally N times without convergence checking
5. **Confirm show_file must be resolvable** — if `confirm.show_file` references a step output, that step must appear earlier
6. **Condition expressions must be valid** — only `==` and `!=` operators, right-hand side must be a literal

### Validation timing

Validation runs at YAML load time, before any steps execute. Template references to `{steps.<name>.output}` are validated structurally (the referenced step exists and appears earlier) but not resolved (the output file may not exist yet).

## Error Handling

### Step failure

When a step skill fails (returns an error, or output verification fails):

1. Mark the step as `failed` in state
2. Mark the overall workflow as `failed`
3. Display the error and the step that failed
4. Tell the user to fix the issue and resume:
   `Skill: docs-tools:docs-orchestrator, args: "resume <workflow> <identifier>"`

### Preflight failure

If a required preflight check fails:

1. Display the specific check that failed
2. List available env files
3. STOP — do not initialize state or run any steps

### YAML validation failure

If the YAML is invalid:

1. Display the specific validation error with line reference
2. STOP

### Resume after failure

On resume, the orchestrator:

1. Loads existing state
2. Re-reads the YAML and re-resolves all conditions against current params (params may have changed via `update-params` on resume — e.g., user removes `--integrate`)
3. Resets the failed step to `pending`
4. Calls `next-step` with the freshly resolved conditions
5. Continues from the next incomplete/non-skipped step

## Access Failure Handling

If any step fails due to access issues (JIRA auth, GitHub token, GitLab token):

1. **STOP IMMEDIATELY** — do not proceed to the next step
2. **Report the exact error** — display the full error message
3. **Mark the step as failed** in state
4. **Await user action** — user must fix credentials and resume

This behavior is inherited from step skills — the orchestrator does not catch or mask access errors.

## Migration Path

### Relationship to existing docs-workflow

`docs-orchestrator` is a **new skill** that coexists with the existing `docs-workflow` command. The existing command continues to work unchanged. Teams can adopt `docs-orchestrator` at their own pace by:

1. Writing a `.claude/docs-orchestrator.yaml` that expresses their desired workflow
2. Creating step skills that follow the step skill contract
3. Invoking `docs-tools:docs-orchestrator` instead of `docs-tools:docs-workflow`

A future migration could re-express `docs-workflow` as a YAML definition for `docs-orchestrator`, but that is **out of scope** for this spec.

### Implementation steps

1. Create `workflow_state.py` with the generic CLI
2. Create `docs-orchestrator.md` skill
3. Create step skills that follow the step skill contract (can reuse agent definitions from `docs-workflow`)
4. Write a reference `.claude/docs-orchestrator.yaml` as an example workflow
5. Update `marketplace.json` to register `docs-orchestrator`

## Testing

### YAML parsing and validation

- Valid YAML with all features parses correctly
- Missing required fields produce clear errors
- Invalid step references are caught at validation time
- Circular step references are detected
- Condition expressions with unsupported operators are rejected

### Template resolution

- Simple param references resolve correctly
- Filters (lower, upper, safe, join, repeat) produce correct output
- Step output references resolve to absolute paths
- Empty list params produce empty strings (no dangling flags)
- Nested filters are rejected (only one filter per reference)

### Orchestrator dispatch loop

- Sequential steps execute in order
- Conditional steps are skipped when condition is false
- Conditional steps run when condition is true
- Iteration stops when done_when is matched
- Iteration stops at max iterations with warning
- Confirm gates present the correct file and prompt
- Confirm decline with on_decline=complete marks step done
- Confirm decline with on_decline=skip skips the step
- Resume picks up at the correct step

### State management

- Init creates valid state with all declared steps
- Next-step respects conditions
- Complete-step records output path
- Resume after failure resets failed step to pending

## Design Note: Skill Composition is the Intended Pattern

The orchestrator invokes step skills via the `Skill` tool, and step skills dispatch agents via the `Agent` tool. This is not "3 levels of nesting" — it is standard skill composition:

1. Claude loads orchestrator instructions (context load, not a subprocess)
2. Claude invokes `Skill` tool → step skill markdown loads into context (context load)
3. Claude invokes `Agent` tool → subagent runs (actual subprocess)

Only the `Agent` dispatch creates a real subprocess. The skill-to-skill invocation is just Claude reading sequential instructions in the same context. This is the same pattern used by `docs-reviewer`, which loads 18 review skills through its agent definition. Skill composition is the orchestration mechanism — with commands deprecated, skills invoking skills is the intended architecture.

## Open Questions

1. **Multiple workflow files** — Should `.claude/docs-orchestrator/` support subdirectories for organization, or flat files only?

2. **Step parallelism** — The current design is strictly sequential. A future extension could add a `parallel` group construct for independent steps (e.g., tech review and style review). Deferred for now — keep it simple.

3. **Step skill discovery** — Should the orchestrator validate that all referenced skills exist before starting? This requires knowing how to check skill availability at runtime.

4. **Output as structured data** — Some steps produce structured output (JIRA URL, not a file). The current design uses `output: null` for these. A future extension could add `output_type: url | file | directory` for richer handling.

5. **Workflow composition** — Should one workflow YAML be able to include/extend another? e.g., `extends: docs-workflow` with overrides. Deferred — YAGNI until teams actually need it.
