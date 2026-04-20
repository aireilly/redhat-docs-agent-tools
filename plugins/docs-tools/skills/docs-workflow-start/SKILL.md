---
name: docs-workflow-start
description: Interactive entry point for the docs workflow. When invoked with no CLI switches, uses AskUserQuestion to gather configuration. Supports full workflow, individual steps with auto-resolved prerequisites, and resuming previous runs. When switches are provided, passes through directly to docs-orchestrator.
argument-hint: "[<ticket>] [--workflow <name>] [--pr <url>]... [--repo <url-or-path>] [--mkdocs] [--draft] [--repo-path <path>] [--create-jira <PROJECT>]"
allowed-tools: Read, Write, Glob, Grep, Bash, Skill, AskUserQuestion
---

# Docs Workflow Start

Interactive entry point for the documentation workflow.

## Parse arguments

Same argument set as docs-orchestrator:

- `$1` — JIRA ticket ID (optional at this stage)
- `--workflow <name>` — custom workflow YAML
- `--pr <url>` — PR/MR URLs (repeatable)
- `--mkdocs` — Material for MkDocs format
- `--draft` — staging area mode
- `--repo-path <path>` — target docs repo for update-in-place
- `--repo <url-or-path>` — source code repository
- `--create-jira <PROJECT>` — create linked JIRA ticket

## Determine mode

**Pass-through mode**: If ANY `--` switches are present in the args string, invoke docs-orchestrator directly with all original arguments. Do NOT use AskUserQuestion.

```
Skill: docs-orchestrator, args: "<all original args>"
```

**Interactive mode**: If no `--` switches are present (bare invocation or just a ticket ID), go to the **Interactive mode — required steps** section below.

## Interactive mode — required steps

**STOP. You MUST follow steps 1–5 below IN ORDER. Do not skip any step. Do not invoke the orchestrator or any step skill until you reach step 5. Do not assume defaults — ask every question.**

### Step 1: Get ticket ID

If no ticket ID was provided in args, ask the user conversationally:

> What is the JIRA ticket ID? (e.g., PROJ-123)

The ticket ID is required. After obtaining it, proceed to step 2.

### Step 2: Action selection — call AskUserQuestion

You MUST call the AskUserQuestion tool now with 1 question. Do not skip this.

**What would you like to do?**

| Option | Description |
|--------|-------------|
| Run full workflow (Recommended) | Run the complete docs pipeline from requirements through to MR creation |
| Run specific step(s) | Run one or more individual workflow steps with prerequisites included automatically |
| Resume existing workflow | Continue a previously started workflow for this ticket |

Wait for the user's answer before proceeding.

- If **"Resume existing workflow"**: skip steps 3–4 and go directly to step 5 (resume path).
- If **"Run full workflow"**: proceed to step 3A.
- If **"Run specific step(s)"**: proceed to step 3B.

### Step 3A: Full workflow configuration — call AskUserQuestion

You MUST call the AskUserQuestion tool now with ALL 4 questions at once. Do not skip this.

**Q1: What output format should the documentation use?**

| Option | Description |
|--------|-------------|
| AsciiDoc (Recommended) | Standard Red Hat documentation format |
| Material for MkDocs | Markdown-based documentation format |

**Q2: Do you have source code related to this ticket?**

| Option | Description |
|--------|-------------|
| Yes — I have a PR URL | A pull request or merge request URL |
| Yes — I have a repo URL or path | A repository URL or local directory path |
| No source code | Proceed without code-evidence retrieval |

**Q3: Where should the documentation be written?**

| Option | Description |
|--------|-------------|
| Current repo — update in place (Recommended) | Detect framework and write directly to the current repository |
| A different repo | Write to a specified repository path |
| Draft — staging area only | Write to staging area without modifying any repository |

**Q4: Create a linked JIRA ticket in another project?**

| Option | Description |
|--------|-------------|
| No (Recommended) | Skip JIRA ticket creation |
| Yes | Create a linked ticket in another JIRA project |

Wait for all answers before proceeding to step 4.

### Step 3B: Specific steps selection — call AskUserQuestion

You MUST call the AskUserQuestion tool now with 1 question. Set `multiSelect: true` on this question so the user can select multiple steps. Do not skip this.

**Which step(s) do you want to run?** (`multiSelect: true`)

| Option | Description |
|--------|-------------|
| requirements | Analyze JIRA ticket and extract documentation requirements |
| code-evidence | Retrieve code evidence from source repository |
| writing | Write documentation from an existing plan |
| technical-review | Review existing documentation for technical accuracy |

For steps not listed (planning, style-review, prepare-branch, commit, create-mr, create-jira), the user can type the step name via the "Other" option.

**Invalid step names**: If the user enters a step name via "Other" that is not recognized, the dependency resolver will report the error with a list of valid step names. Surface this error to the user and ask them to correct their selection.

After receiving the answer, determine which configuration questions are relevant:

- **Format?** — include if any of these steps are selected: writing, style-review
- **Source code?** — include if code-evidence is selected
- **Placement?** — include if any of these steps are selected: writing, prepare-branch, commit, create-mr
- **Create JIRA?** — include if create-jira is selected

If any questions are relevant, call AskUserQuestion with those questions (same text and options as step 3A). If no questions are relevant, proceed to step 4.

### Step 4: Free-text follow-ups

Based on answers from step 3, collect any needed free-text inputs conversationally (not via AskUserQuestion). Only ask questions that apply:

**If "Yes — I have a PR URL" was selected**:
> Enter PR/MR URL(s), one per line (press Enter twice when done):

Multiple URLs are supported. Each becomes a `--pr <url>` flag.

**If "Yes — I have a repo URL or path" was selected**:
> Enter the source repo URL or local path:

Single value. Then follow up:
> Do you also have PR URL(s) for this repo? If so, enter them one per line (press Enter twice when done). Otherwise, press Enter to skip:

This is because `--repo` and `--pr` can coexist — the PR branch gets checked out within the repo.

**If "A different repo" was selected for placement**:
> Enter the target docs repository path:

Maps to `--repo-path <path>`.

**If "Yes" was selected for Create JIRA**:
> Enter the target JIRA project key (e.g., DOCS):

Maps to `--create-jira <PROJECT>`.

If no follow-ups are needed, proceed directly to step 5.

### Step 5: Build CLI flags and execute

Build the args string from collected answers:

| Answer | CLI flag |
|--------|----------|
| Material for MkDocs | `--mkdocs` |
| PR URL(s) | `--pr <url>` (repeat for each URL) |
| Repo URL or path | `--repo <url-or-path>` |
| Draft — staging area only | `--draft` |
| Target docs repo path | `--repo-path <path>` |
| Create JIRA = Yes | `--create-jira <PROJECT>` |

AsciiDoc format and current repo placement are defaults — no flags needed.

**Precedence**: If both `--repo-path` and `--draft` would be set, `--repo-path` wins — log a warning and omit `--draft` (matches orchestrator behavior).

**NOW invoke the orchestrator** (or run specific steps — see below).

#### Full workflow execution

Invoke the orchestrator with the ticket ID and all constructed flags:

```
Skill: docs-orchestrator, args: "<ticket> <constructed flags>"
```

Example:

```
Skill: docs-orchestrator, args: "PROJ-123 --mkdocs --pr https://github.com/org/repo/pull/42 --draft"
```

#### Resume execution

For the resume path (user selected "Resume existing workflow" in step 2):

```
Skill: docs-orchestrator, args: "<ticket>"
```

The orchestrator detects the existing progress file and resumes automatically.

#### Specific steps execution

When running individual steps, dependencies are resolved automatically and each step skill is invoked directly.

### 1. Resolve base path

```bash
TICKET_LOWER=$(echo "<ticket>" | tr '[:upper:]' '[:lower:]')
BASE_PATH="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)/.claude/docs/${TICKET_LOWER}"
mkdir -p "$BASE_PATH"
```

### 2. Resolve the YAML path

Determine which workflow YAML to use:

```bash
if [[ -f ".claude/docs-workflow.yaml" ]]; then
  YAML_PATH=".claude/docs-workflow.yaml"
else
  YAML_PATH="${CLAUDE_PLUGIN_ROOT}/skills/docs-orchestrator/defaults/docs-workflow.yaml"
fi
```

### 3. Compute execution plan

Run the dependency resolver:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/resolve_steps.py \
  --yaml "$YAML_PATH" \
  --steps <selected-step-names...> \
  --base-path "$BASE_PATH"
```

If the script exits with code 1, the user entered an invalid step name. Read the `error` field and `valid_steps` list from the JSON output and tell the user:

> Step name "\<name\>" is not recognized. Valid steps are: \<valid_steps list\>. Please try again.

Then re-ask the step selection question via AskUserQuestion.

### 4. Handle existing artifacts (smart hybrid confirmation)

Read the JSON output. If `steps_with_artifacts` is **non-empty**, use AskUserQuestion:

**Some prerequisite steps already have output from a previous run. Re-use existing artifacts or re-run?**

| Option | Description |
|--------|-------------|
| Re-use existing artifacts (Recommended) | Skip completed prerequisites and only run what's missing |
| Re-run all steps | Discard existing output and re-run everything from scratch |

If `steps_with_artifacts` is **empty**, skip this question and run all steps.

### 5. Evaluate `when` conditions

For each step in the execution plan with a `when` field:

- `when: has_source_repo` — skip this step if no source repo or PR URL was provided. Log: "Skipping \<step\>: no source repository configured."
- `when: create_jira_project` — skip this step if create-jira was not selected. Log: "Skipping \<step\>: JIRA creation not requested."

### 6. Run steps sequentially

For each step in `execution_plan` order:

1. If `has_artifacts: true` AND user chose "Re-use existing artifacts" → skip with message: "Skipping \<step\>: using existing artifacts at \<base-path\>/\<step\>/"
2. If `when` condition is not met → skip with message (see above)
3. Otherwise, construct the args and invoke:

```
Skill: <step.skill>, args: "<ticket> --base-path <BASE_PATH> <step-specific-flags>"
```

**Step-specific flags** — each step gets `<ticket> --base-path <BASE_PATH>` plus:

| Step | Additional flags from collected config |
|------|---------------------------------------|
| requirements | `[--pr <url>]... [--repo <repo_path>]` |
| planning | _(none)_ |
| code-evidence | `--repo <repo_path> [--scope-include <globs>] [--scope-exclude <globs>]` |
| prepare-branch | `[--draft] [--repo-path <path>]` |
| writing | `--format <adoc\|mkdocs> [--draft] [--repo <repo_path>] [--repo-path <path>]` |
| style-review | `--format <adoc\|mkdocs>` |
| technical-review | _(none)_ |
| commit | `[--draft] [--repo-path <path>]` |
| create-mr | `[--draft] [--repo-path <path>]` |
| create-jira | `--project <PROJECT>` |

The format flag defaults to `adoc` unless the user selected Material for MkDocs.

### 7. Verify and report

After each step completes:

1. Check the step's output directory exists at `<BASE_PATH>/<step-name>/`
2. If missing, report the failure: "Step \<step\> failed — expected output at \<path\> not found." **STOP** — do not continue to subsequent steps.
3. If present, report success: "Step \<step\> completed. Output: \<path\>"

After all steps complete, display a summary:

> **Completed steps:**
> - requirements: .claude/docs/proj-123/requirements/
> - planning: .claude/docs/proj-123/planning/
> - writing: .claude/docs/proj-123/writing/
>
> **Skipped steps:**
> - code-evidence: no source repository configured
