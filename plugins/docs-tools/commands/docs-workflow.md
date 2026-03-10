---
description: Run the multi-stage documentation workflow for a JIRA ticket. Orchestrates agents sequentially — requirements analysis, planning, writing, technical review, and style review
argument-hint: [action] <ticket> [--pr <url>] [--create-jira <PROJECT>] [--mkdocs]
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Task, WebSearch, WebFetch
---

# Documentation Workflow

Run the multi-stage documentation workflow for a JIRA ticket. This command orchestrates five specialized agents sequentially — requirements analysis, planning, writing, technical review, and style review — to produce complete documentation in AsciiDoc (default) or Material for MkDocs Markdown format.

## Agents

| Stage | Agent | Description |
|-------|-------|-------------|
| 1. Requirements | requirements-analyst | Parses JIRA issues, PRs, and specs to extract documentation requirements |
| 2. Planning | docs-planner | Creates documentation plans with JTBD framework and gap analysis |
| 3. Writing | docs-writer | Writes complete documentation — AsciiDoc modules or MkDocs Markdown pages |
| 4. Technical review | technical-reviewer | Reviews for technical accuracy — code examples, prerequisites, commands, failure paths |
| 5. Style review | docs-reviewer | Reviews with Vale linting and style guide checks, edits files in place |
| 6. Create JIRA | *(direct bash/curl)* | Optional: creates a docs JIRA ticket linked to the parent ticket |

## Output Structure

**AsciiDoc (default):**

```
.claude/docs/
├── workflow/           # Workflow state files (JSON)
├── requirements/       # Stage 1 outputs
├── plans/              # Stage 2 outputs
└── drafts/             # Stage 3–5 outputs (per-ticket folders)
    └── <ticket>/
        ├── _index.md
        ├── _review_report.md   # Stage 5 review report
        ├── assembly_*.adoc
        └── modules/
            ├── <concept>.adoc
            ├── <procedure>.adoc
            └── <reference>.adoc
```

**MkDocs Markdown (`--mkdocs`):**

```
.claude/docs/
├── workflow/           # Workflow state files (JSON)
├── requirements/       # Stage 1 outputs
├── plans/              # Stage 2 outputs
└── drafts/             # Stage 3–5 outputs (per-ticket folders)
    └── <ticket>/
        ├── _index.md
        ├── _review_report.md   # Stage 5 review report
        ├── mkdocs-nav.yml      # Suggested nav tree fragment
        └── docs/
            ├── <concept>.md
            ├── <procedure>.md
            └── <reference>.md
```

## Arguments

- **action**: $1 (default: `start`) — Action to perform: `start`, `resume`, or `status`
- **ticket**: $2 (required) — JIRA ticket identifier (e.g., `RHAISTRAT-123`)

**IMPORTANT**: This command requires a ticket identifier. If no ticket is provided, stop and ask the user to provide one.

## Options

- **--pr \<url\>**: GitHub PR or GitLab MR URL to include in requirements analysis. Can be specified multiple times across start/resume invocations.
- **--mkdocs**: Output Material for MkDocs Markdown instead of AsciiDoc. Produces `.md` files with YAML frontmatter in a `docs/` subfolder, plus a `mkdocs-nav.yml` navigation fragment.
- **--create-jira \<PROJECT\>**: Create a documentation JIRA ticket in the specified project (e.g., `INFERENG`) after the review stage completes. The project key is mandatory — there is no default. The created ticket is linked to the parent ticket with a "Document" relationship. Can be passed on `start` or `resume`.

## Step-by-Step Instructions

### Step 1: Parse Arguments

Parse the action, ticket, and options from the command arguments.

```bash
ACTION="${1:-start}"
TICKET="${2:-}"

# Parse --pr, --mkdocs, and --create-jira flags from remaining arguments
PR_URLS=()
CREATE_JIRA_PROJECT=""
OUTPUT_FORMAT="adoc"
shift 2 2>/dev/null
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pr) PR_URLS+=("$2"); shift 2 ;;
        --mkdocs) OUTPUT_FORMAT="mkdocs"; shift ;;
        --create-jira) CREATE_JIRA_PROJECT="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Validate ticket is provided
if [[ -z "$TICKET" ]]; then
    echo "ERROR: Ticket identifier is required."
    echo "Usage: /docs-tools:docs-workflow [start|resume|status] <TICKET> [--pr <url>] [--mkdocs] [--create-jira <PROJECT>]"
    exit 1
fi

echo "Action: ${ACTION}"
echo "Ticket: ${TICKET}"
echo "Format: ${OUTPUT_FORMAT}"
if [[ ${#PR_URLS[@]} -gt 0 ]]; then
    echo "PR URLs: ${PR_URLS[*]}"
fi
if [[ -n "$CREATE_JIRA_PROJECT" ]]; then
    echo "Create JIRA in project: ${CREATE_JIRA_PROJECT}"
fi
```

If no ticket is provided, STOP and ask the user to provide one.

### Step 2: Pre-flight Validation

Validate that required access tokens are available before proceeding.

```bash
echo ""
echo "Validating access tokens..."

HAS_ERRORS=false

# JIRA token is REQUIRED
if [[ -z "${JIRA_AUTH_TOKEN:-}" ]]; then
    echo "ERROR: JIRA_AUTH_TOKEN is not set."
    echo "  The workflow requires JIRA access to fetch ticket details."
    echo "  Add JIRA_AUTH_TOKEN to ~/.env and source it."
    HAS_ERRORS=true
else
    echo "  JIRA_AUTH_TOKEN: configured"
fi

# GitHub token — warning only
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    echo "  GITHUB_TOKEN: configured"
else
    echo "  GITHUB_TOKEN: not set (required if using GitHub PRs)"
fi

# GitLab token — warning only
if [[ -n "${GITLAB_TOKEN:-}" ]]; then
    echo "  GITLAB_TOKEN: configured"
else
    echo "  GITLAB_TOKEN: not set (required if using GitLab MRs)"
fi

if [[ "$HAS_ERRORS" == "true" ]]; then
    echo ""
    echo "CRITICAL: Required access tokens are missing."
    echo "The workflow WILL NOT proceed without JIRA_AUTH_TOKEN."
    echo ""
    echo "Available env files:"
    ls -la ~/.env* 2>/dev/null || echo "  No ~/.env* files found"
    echo ""
    echo "To fix: add JIRA_AUTH_TOKEN to ~/.env and run: source ~/.env"
    exit 1
fi

echo ""
```

**If JIRA_AUTH_TOKEN is missing, STOP IMMEDIATELY.** Do not proceed without it. Display the error and available env files.

#### JIRA Environment File Fallback

If JIRA access fails later during requirements analysis, try alternate env files:

1. Search for `~/.env*` files containing "jira"
2. Source each alternate file and retry
3. If all fail, reset to `~/.env` and retry
4. If still failing, STOP and report the error

```bash
# List alternate JIRA env files
ls -la ~/.env*jira* ~/.env*.jira* 2>/dev/null

# Source an alternate env file
set -a && source ~/.env.jira_internal && set +a
```

### Step 3: Initialize or Load State

Create the workflow state file or load existing state.

```bash
CLAUDE_DOCS_DIR="${PWD}/.claude/docs"
SAFE_TICKET=$(echo "$TICKET" | tr '[:upper:]' '[:lower:]' | tr '-' '_')
STATE_FILE="${CLAUDE_DOCS_DIR}/workflow/workflow_${SAFE_TICKET}.json"

# Resolve the plugin root directory (where this command file lives)
# This is used to locate agent files in the agents/ directory
CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Ensure directories exist
mkdir -p "${CLAUDE_DOCS_DIR}/workflow" "${CLAUDE_DOCS_DIR}/requirements" "${CLAUDE_DOCS_DIR}/plans" "${CLAUDE_DOCS_DIR}/drafts"
```

#### For `start` action

If a state file already exists, treat it as a resume. Otherwise, create a new state file:

```bash
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Build PR URLs JSON array
PR_URLS_JSON="[]"
if [[ ${#PR_URLS[@]} -gt 0 ]]; then
    PR_URLS_JSON=$(printf '%s\n' "${PR_URLS[@]}" | jq -R . | jq -s .)
fi

cat > "$STATE_FILE" << EOF
{
  "ticket": "${TICKET}",
  "created_at": "${NOW}",
  "updated_at": "${NOW}",
  "current_stage": "requirements",
  "status": "pending",
  "options": {
    "pr_urls": ${PR_URLS_JSON},
    "format": "${OUTPUT_FORMAT}",
    "create_jira_project": ${CREATE_JIRA_PROJECT:+\"$CREATE_JIRA_PROJECT\"}${CREATE_JIRA_PROJECT:-null}
  },
  "data": {
    "jira_summary": null,
    "related_prs": []
  },
  "stages": {
    "requirements": {"status": "pending", "output_file": null, "started_at": null, "completed_at": null},
    "planning": {"status": "pending", "output_file": null, "started_at": null, "completed_at": null},
    "writing": {"status": "pending", "output_file": null, "started_at": null, "completed_at": null},
    "technical_review": {"status": "pending", "output_file": null, "started_at": null, "completed_at": null, "iterations": 0},
    "review": {"status": "pending", "output_file": null, "started_at": null, "completed_at": null},
    "create_jira": {"status": "pending", "output_file": null, "started_at": null, "completed_at": null}
  }
}
EOF

echo "Initialized workflow for ${TICKET}"
```

#### For `resume` action

Load the existing state file and add any new `--pr` URLs:

```bash
test -f "$STATE_FILE" || {
    echo "No workflow found for ${TICKET}."
    echo "Use: /docs-tools:docs-workflow start ${TICKET}"
    exit 1
}

# Add new PR URLs if provided
for url in "${PR_URLS[@]}"; do
    TMP=$(mktemp)
    jq --arg url "$url" '.options.pr_urls += [$url] | .options.pr_urls |= unique' "$STATE_FILE" > "$TMP"
    mv "$TMP" "$STATE_FILE"
    echo "Added PR/MR URL: ${url}"
done

# Set create_jira_project if provided on resume
if [[ -n "$CREATE_JIRA_PROJECT" ]]; then
    TMP=$(mktemp)
    jq --arg proj "$CREATE_JIRA_PROJECT" '.options.create_jira_project = $proj' "$STATE_FILE" > "$TMP"
    mv "$TMP" "$STATE_FILE"
    echo "Set create-jira project: ${CREATE_JIRA_PROJECT}"
fi
```

#### For `status` action

Display the current workflow state and exit:

```bash
test -f "$STATE_FILE" || {
    echo "No workflow found for ${TICKET}."
    exit 1
}

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Documentation Workflow Status: ${TICKET}"
echo "════════════════════════════════════════════════════════════"
echo ""

STATUS=$(jq -r '.status' "$STATE_FILE")
CURRENT=$(jq -r '.current_stage' "$STATE_FILE")
PR_LIST=$(jq -r '.options.pr_urls // [] | join(", ")' "$STATE_FILE")

echo "Overall Status: ${STATUS}"
echo "Current Stage:  ${CURRENT}"
if [[ -n "$PR_LIST" ]]; then
    echo "PR/MR URLs:     ${PR_LIST}"
fi
echo ""
echo "Stages:"

CREATE_JIRA_PROJ=$(jq -r '.options.create_jira_project // ""' "$STATE_FILE")
STAGES="requirements planning writing technical_review review"
case "$CREATE_JIRA_PROJ" in
    ""|"null") ;;
    *) STAGES="$STAGES create_jira" ;;
esac

for STAGE in $STAGES; do
    STAGE_STATUS=$(jq -r ".stages.${STAGE}.status" "$STATE_FILE")
    OUTPUT=$(jq -r ".stages.${STAGE}.output_file // \"\"" "$STATE_FILE")
    case "$STAGE_STATUS" in
        "completed") ICON="[x]" ;;
        "in_progress") ICON="[>]" ;;
        "failed") ICON="[!]" ;;
        *) ICON="[ ]" ;;
    esac
    DISPLAY_NAME="${STAGE}"
    if [[ "$STAGE" == "create_jira" ]]; then
        DISPLAY_NAME="create_jira (${CREATE_JIRA_PROJ})"
    fi
    case "$OUTPUT" in
        ""|"null") echo "  ${ICON} ${DISPLAY_NAME}" ;;
        *) echo "  ${ICON} ${DISPLAY_NAME} -> ${OUTPUT}" ;;
    esac
done

echo ""
```

**If the action is `status`, display the state and STOP. Do not run any stages.**

### Step 4: Determine Next Stage

Find the first stage that is not completed. If all stages are completed, report that the workflow is done.

```bash
CREATE_JIRA_PROJ=$(jq -r '.options.create_jira_project // ""' "$STATE_FILE")
STAGES="requirements planning writing technical_review review"
case "$CREATE_JIRA_PROJ" in
    ""|"null") ;;
    *) STAGES="$STAGES create_jira" ;;
esac

NEXT_STAGE=""
for STAGE in $STAGES; do
    STAGE_STATUS=$(jq -r ".stages.${STAGE}.status" "$STATE_FILE")
    case "$STAGE_STATUS" in
        "completed") ;;
        *) NEXT_STAGE="$STAGE"; break ;;
    esac
done

if [[ -z "$NEXT_STAGE" ]]; then
    echo "Workflow for ${TICKET} is already complete."
    # Show status and stop
fi
```

If all stages are completed, show the status summary and STOP.

### Step 5: Run Stages Sequentially

Run each remaining stage in order: `requirements` → `planning` → `writing` → `technical_review` → `review` → `create_jira` (if `--create-jira` was specified).

For each stage:

1. Update the state to `in_progress`
2. Invoke the Agent tool with the prompt from the corresponding stage section below
3. After the agent completes, use the "Mark stage as completed" command below (it verifies the output file and updates state)
4. Proceed to the next stage

**IMPORTANT**: Run stages sequentially, not in parallel. Each stage depends on the previous stage's output.

#### State update commands

Use these bash/jq commands to update the state file before and after each stage:

**Mark stage as in_progress:**

```bash
TMP=$(mktemp)
jq --arg stage "<STAGE>" --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
   '.stages[$stage].status = "in_progress" | .stages[$stage].started_at = $now | .updated_at = $now | .status = "in_progress" | .current_stage = $stage' \
   "$STATE_FILE" > "$TMP"
mv "$TMP" "$STATE_FILE"
```

**Mark stage as completed (with output file verification):**

```bash
if [[ ! -f "$OUTPUT_FILE" ]]; then
    OUTPUT_FILE=$(ls -t "${CLAUDE_DOCS_DIR}/<SUBDIR>/"*"${SAFE_TICKET}"*.md 2>/dev/null | head -1)
fi
if [[ ! -f "$OUTPUT_FILE" ]]; then
    echo "ERROR: Output file not found for stage <STAGE>"
    exit 1
fi
TMP=$(mktemp)
jq --arg stage "<STAGE>" --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg output "$OUTPUT_FILE" \
   '.stages[$stage].status = "completed" | .stages[$stage].completed_at = $now | .stages[$stage].output_file = $output | .updated_at = $now' \
   "$STATE_FILE" > "$TMP"
mv "$TMP" "$STATE_FILE"
echo "Stage <STAGE> completed. Output: $OUTPUT_FILE"
```

Replace `<SUBDIR>` with the output directory for the stage (`requirements`, `plans`, or `drafts/<TICKET>`).

**Mark stage as failed:**

```bash
TMP=$(mktemp)
jq --arg stage "<STAGE>" --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
   '.stages[$stage].status = "failed" | .updated_at = $now | .status = "failed"' \
   "$STATE_FILE" > "$TMP"
mv "$TMP" "$STATE_FILE"
```

Replace `<STAGE>` and `<OUTPUT_FILE>` with actual values for each invocation.

## Stage Prompts

The following sections define the exact prompt to pass to the Agent tool for each stage. Each prompt explicitly tells the agent which agent file to read and follow — this is how custom agents are invoked. All agents use the default `general-purpose` subagent type.

**IMPORTANT — variable expansion**: All `<VARIABLE>` placeholders (e.g., `<TICKET>`, `<PREV_OUTPUT>`, `<DRAFTS_DIR>`, `<OUTPUT_FILE>`) must be expanded to their actual values **before** passing the prompt string to the Agent tool. Subagents start with a fresh context — they cannot access the orchestrator's shell variables. Build each prompt string with the resolved values substituted in.

### Stage 1: Requirements (requirements-analyst)

**Agent tool parameters:**
- `description`: `Analyze requirements for <TICKET>`

**Output file path:**

```bash
NOW=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="${CLAUDE_DOCS_DIR}/requirements/requirements_${SAFE_TICKET}_${NOW}.md"
```

**Prompt:**

> Use the requirements-analyst agent. Read and follow the agent instructions at `${CLAUDE_PLUGIN_ROOT}/agents/requirements-analyst.md`.
>
> Analyze documentation requirements for JIRA ticket `<TICKET>`.
>
> Manually-provided PR/MR URLs to include in analysis (merge with any auto-discovered URLs, dedup):
> - `<PR_URL_1>`
> - `<PR_URL_2>`
>
> Save your complete analysis to: `<OUTPUT_FILE>`
>
> Follow your standard analysis methodology (JIRA fetch, ticket graph traversal, PR/MR analysis, web search expansion). Format the output as structured markdown for the next stage.

**Note:** The PR URL bullet list is conditional — include those bullets only if PR URLs exist in the state file. Read them with:

```bash
jq -r '.options.pr_urls // [] | .[]' "$STATE_FILE"
```

If no `--pr` URLs were provided, omit the bullet list but keep the rest of the prompt.

After the agent completes, verify the output file exists. If not, search for the most recent file in the requirements directory:

```bash
ls -t "${CLAUDE_DOCS_DIR}/requirements/"*.md 2>/dev/null | head -1
```

### Stage 2: Planning (docs-planner)

**Agent tool parameters:**
- `description`: `Create documentation plan for <TICKET>`

**Output file path:**

```bash
NOW=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="${CLAUDE_DOCS_DIR}/plans/plan_${SAFE_TICKET}_${NOW}.md"
```

**Previous output:** Read from the requirements stage output file in the state:

```bash
PREV_OUTPUT=$(jq -r '.stages.requirements.output_file // ""' "$STATE_FILE")
```

**Prompt:**

> Use the docs-planner agent. Read and follow the agent instructions at `${CLAUDE_PLUGIN_ROOT}/agents/docs-planner.md`.
>
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

After the agent completes, verify the output file exists.

### Stage 3: Writing (docs-writer)

The writing stage output structure depends on the `--mkdocs` option.

**Agent tool parameters:**

Read the format from the state file:
```bash
OUTPUT_FORMAT=$(jq -r '.options.format // "adoc"' "$STATE_FILE")
```

- **If `OUTPUT_FORMAT` is `adoc`** (default):
  - `description`: `Write AsciiDoc documentation for <TICKET>`

- **If `OUTPUT_FORMAT` is `mkdocs`**:
  - `description`: `Write MkDocs documentation for <TICKET>`

**Output paths:**

```bash
TICKET_LOWERCASE=$(echo "$TICKET" | tr '[:upper:]' '[:lower:]')
DRAFTS_DIR="${CLAUDE_DOCS_DIR}/drafts/${TICKET_LOWERCASE}"

if [[ "$OUTPUT_FORMAT" == "mkdocs" ]]; then
    DOCS_DIR="${DRAFTS_DIR}/docs"
    mkdir -p "${DOCS_DIR}"
else
    MODULES_DIR="${DRAFTS_DIR}/modules"
    mkdir -p "${MODULES_DIR}"
fi
OUTPUT_FILE="${DRAFTS_DIR}/_index.md"
```

**Previous output:** Read from the planning stage output file in the state:

```bash
PREV_OUTPUT=$(jq -r '.stages.planning.output_file // ""' "$STATE_FILE")
```

**Prompt (AsciiDoc — default):**

> Use the docs-writer agent. Read and follow the agent instructions at `${CLAUDE_PLUGIN_ROOT}/agents/docs-writer.md`.
>
> Write complete AsciiDoc documentation based on the documentation plan for ticket `<TICKET>`.
>
> Read the plan from: `<PREV_OUTPUT>`
>
> **IMPORTANT**: Write COMPLETE .adoc files, not summaries or outlines.
>
> Output folder structure:
> ```
> <DRAFTS_DIR>/
> ├── _index.md                     # Index of all modules
> ├── assembly_<name>.adoc          # Assembly files at root
> └── modules/                      # All module files
>     ├── <concept-name>.adoc
>     ├── <procedure-name>.adoc
>     └── <reference-name>.adoc
> ```
>
> Save modules to: `<MODULES_DIR>/`
> Save assemblies to: `<DRAFTS_DIR>/`
> Create index at: `<DRAFTS_DIR>/_index.md`

**Prompt (MkDocs — `--mkdocs`):**

> Use the docs-writer agent. Read and follow the agent instructions at `${CLAUDE_PLUGIN_ROOT}/agents/docs-writer.md`.
>
> Write complete Material for MkDocs Markdown documentation based on the documentation plan for ticket `<TICKET>`.
>
> Read the plan from: `<PREV_OUTPUT>`
>
> **IMPORTANT**: Write COMPLETE .md files with YAML frontmatter (title, description), not summaries or outlines. Use Material for MkDocs conventions: admonitions (`!!! note`, `!!! warning`), content tabs, code blocks with titles, and proper heading hierarchy starting at `# h1`.
>
> Output folder structure:
> ```
> <DRAFTS_DIR>/
> ├── _index.md                     # Index of all pages
> ├── mkdocs-nav.yml                # Suggested nav tree fragment
> └── docs/                         # All page files
>     ├── <concept-name>.md
>     ├── <procedure-name>.md
>     └── <reference-name>.md
> ```
>
> Save pages to: `<DOCS_DIR>/`
> Create nav fragment at: `<DRAFTS_DIR>/mkdocs-nav.yml`
> Create index at: `<DRAFTS_DIR>/_index.md`

After the agent completes, verify the index file exists at `<DRAFTS_DIR>/_index.md`.

### Stage 4: Technical Review (technical-reviewer) — iterative with writer

The technical reviewer checks documentation for technical accuracy: code examples, prerequisites, commands, failure paths, and architectural coherence. The writer and technical reviewer iterate until the technical review passes.

**Agent tool parameters:**
- `description`: `Technical review of documentation for <TICKET>`

**Output path:**

```bash
TICKET_LOWERCASE=$(echo "$TICKET" | tr '[:upper:]' '[:lower:]')
DRAFTS_DIR="${CLAUDE_DOCS_DIR}/drafts/${TICKET_LOWERCASE}"
TECH_REVIEW_FILE="${DRAFTS_DIR}/_technical_review.md"
```

**Prompt:**

> Use the technical-reviewer agent. Read and follow the agent instructions at `${CLAUDE_PLUGIN_ROOT}/agents/technical-reviewer.md`.
>
> Perform a technical review of the documentation drafts for ticket `<TICKET>`.
>
> Source drafts location: `<DRAFTS_DIR>/`
>
> Review all .adoc and .md files in the drafts directory. Follow your standard review methodology — apply the developer lens for procedures and the architect lens for concepts. Check code example integrity, prerequisite completeness, command accuracy, failure path coverage, and architectural coherence.
>
> Save your review report to: `<TECH_REVIEW_FILE>`

**Iteration loop:**

After the technical reviewer completes, increment the iteration counter in state and check the review report:

```bash
TMP=$(mktemp)
jq '.stages.technical_review.iterations += 1' "$STATE_FILE" > "$TMP"
mv "$TMP" "$STATE_FILE"
ITERATIONS=$(jq '.stages.technical_review.iterations' "$STATE_FILE")
```

1. Read `<TECH_REVIEW_FILE>` and check the **Overall technical confidence** rating
2. If confidence is **HIGH**: mark `technical_review` as completed and proceed to the style review stage
3. If confidence is **MEDIUM** or **LOW** and `ITERATIONS < 3`: launch the writer agent to fix issues, then re-run the technical reviewer
4. If confidence is **MEDIUM** or **LOW** and `ITERATIONS >= 3`: mark the stage as completed with a note that manual technical review is recommended

**Writer fix prompt (for iteration):**

> Use the docs-writer agent. Read and follow the agent instructions at `${CLAUDE_PLUGIN_ROOT}/agents/docs-writer.md`.
>
> The technical reviewer found issues in the documentation for ticket `<TICKET>`.
>
> Read the technical review report at: `<TECH_REVIEW_FILE>`
>
> Address all **Critical issues** and **Significant issues** listed in the report. Edit the draft files in place at `<DRAFTS_DIR>/`.
>
> Do NOT address minor issues or style concerns — those are handled by the style review stage.

**Iteration rules:**

- Maximum 3 iterations (initial review + 2 fix cycles), tracked in `stages.technical_review.iterations`
- Each iteration overwrites `<TECH_REVIEW_FILE>` with the latest review
- On resume, the iteration count is preserved — the workflow continues from where it left off rather than restarting the review cycle

### Stage 5: Style Review (docs-reviewer)

**Agent tool parameters:**
- `description`: `Review documentation for <TICKET>`

**Output path:**

```bash
TICKET_LOWERCASE=$(echo "$TICKET" | tr '[:upper:]' '[:lower:]')
DRAFTS_DIR="${CLAUDE_DOCS_DIR}/drafts/${TICKET_LOWERCASE}"
OUTPUT_FILE="${DRAFTS_DIR}/_review_report.md"
```

**Prompt:**

Read the format from the state file:
```bash
OUTPUT_FORMAT=$(jq -r '.options.format // "adoc"' "$STATE_FILE")
```

**If `OUTPUT_FORMAT` is `adoc` (default):**

> Use the docs-reviewer agent. Read and follow the agent instructions at `${CLAUDE_PLUGIN_ROOT}/agents/docs-reviewer.md`.
>
> Review the AsciiDoc documentation drafts for ticket `<TICKET>`.
>
> Source drafts location: `<DRAFTS_DIR>/`
> - Modules in: `<DRAFTS_DIR>/modules/`
> - Assemblies in: `<DRAFTS_DIR>/`
>
> **Edit files in place** in the drafts folder. Do NOT create copies in a separate folder.
>
> For each .adoc file:
> 1. Run Vale linting once (use the `vale` skill)
> 2. Fix obvious errors where the fix is clear and unambiguous
> 3. Run documentation review skills:
>    - Red Hat docs: modular-docs, content-quality
>    - IBM Style Guide: audience-and-medium, language-and-grammar, punctuation, numbers-and-measurement, structure-and-format, references, technical-elements, legal-information
>    - Red Hat SSG: grammar-and-language, formatting, structure, technical-examples, gui-and-links, legal-and-support, accessibility, release-notes (if applicable)
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

**If `OUTPUT_FORMAT` is `mkdocs`:**

> Use the docs-reviewer agent. Read and follow the agent instructions at `${CLAUDE_PLUGIN_ROOT}/agents/docs-reviewer.md`.
>
> Review the Material for MkDocs Markdown documentation drafts for ticket `<TICKET>`.
>
> Source drafts location: `<DRAFTS_DIR>/`
> - Pages in: `<DRAFTS_DIR>/docs/`
>
> **Edit files in place** in the drafts folder. Do NOT create copies in a separate folder.
>
> For each .md file:
> 1. Run Vale linting once (use the `vale` skill)
> 2. Fix obvious errors where the fix is clear and unambiguous
> 3. Run documentation review skills:
>    - Content quality: content-quality
>    - IBM Style Guide: audience-and-medium, language-and-grammar, punctuation, numbers-and-measurement, structure-and-format, references, technical-elements, legal-information
>    - Red Hat SSG: grammar-and-language, formatting, structure, technical-examples, gui-and-links, legal-and-support, accessibility
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

After the agent completes, verify the review report exists.

### Stage 6: Create JIRA (optional — direct bash/curl)

This stage only runs when `--create-jira <PROJECT>` was provided. It does NOT use a Task agent — it uses direct Bash commands with the JIRA REST API.

**Check if stage should run:**

```bash
CREATE_JIRA_PROJ=$(jq -r '.options.create_jira_project // ""' "$STATE_FILE")
if [[ -z "$CREATE_JIRA_PROJ" || "$CREATE_JIRA_PROJ" == "null" ]]; then
    echo "Skipping create_jira stage (--create-jira not specified)"
    # Skip this stage entirely — do NOT mark it in state
fi
```

If `create_jira_project` is not set in the state, skip this stage entirely and proceed to workflow completion.

**Step 6a: Check for existing "is documented by" link on parent ticket**

Before creating a new ticket, check if another ticket already "documents" this parent. If it does, skip ticket creation.

```bash
JIRA_URL="https://issues.redhat.com"

# Fetch parent ticket's issue links
LINKS_JSON=$(curl -s \
  -H "Authorization: Bearer ${JIRA_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  "${JIRA_URL}/rest/api/2/issue/${TICKET}?fields=issuelinks")

# Check for existing "Is documented by" link.
# In Step 6d we create the link with:
#   outwardIssue = TICKET          (the parent — source, shows "Is documented by")
#   inwardIssue  = NEW_ISSUE_KEY   (the docs ticket — destination)
# When querying TICKET's links, the docs ticket appears as inwardIssue.
HAS_DOC_LINK=$(echo "$LINKS_JSON" | jq -r '
  .fields.issuelinks[]? |
  select(
    .type.name == "Document" and
    .inwardIssue != null
  ) | .type.name' | head -1)

if [[ -n "$HAS_DOC_LINK" ]]; then
    LINKED_KEY=$(echo "$LINKS_JSON" | jq -r '
      .fields.issuelinks[] |
      select(.type.name == "Document" and .inwardIssue != null) |
      .inwardIssue.key' | head -1)
    echo "Parent ticket ${TICKET} already documents ${LINKED_KEY}."
    echo "Skipping JIRA creation."
fi
```

If a "Document" link already exists, mark the stage as completed with a note and STOP. Do not create a duplicate.

**Step 6a-2: Check if the JIRA project is public**

Before attaching the detailed docs plan, determine whether the target project allows anonymous (public) access. Make an unauthenticated curl request to the project endpoint and check the HTTP status code:

```bash
JIRA_URL="https://issues.redhat.com"

# Check project visibility with an unauthenticated request
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Content-Type: application/json" \
  "${JIRA_URL}/rest/api/2/project/${CREATE_JIRA_PROJ}")

if [[ "$HTTP_STATUS" == "200" ]]; then
    PROJECT_IS_PUBLIC=true
    echo "Project ${CREATE_JIRA_PROJ} is PUBLIC (anonymous access returned HTTP ${HTTP_STATUS})."
    echo "The detailed docs plan will NOT be attached to the JIRA ticket."
else
    PROJECT_IS_PUBLIC=false
    echo "Project ${CREATE_JIRA_PROJ} is PRIVATE (anonymous access returned HTTP ${HTTP_STATUS})."
    echo "The detailed docs plan will be attached to the JIRA ticket."
fi
```

If the unauthenticated request returns HTTP 200, the project is public and the detailed documentation plan must NOT be attached (Step 6e will be skipped). If it returns 401, 403, or any other non-200 status, the project is private and the plan will be attached as usual.

**Step 6b: Extract description content from the documentation plan**

Read the documentation plan output file (Stage 2) and extract the three JIRA description sections defined by the docs-planner agent.

```bash
PLAN_FILE=$(jq -r '.stages.planning.output_file // ""' "$STATE_FILE")
```

Use the Read tool to read `<PLAN_FILE>`. Then extract these three sections (including their headings):

1. `## What is the main JTBD? What user goal is being accomplished? What pain point is being avoided?`
2. `## How does the JTBD(s) relate to the overall real-world workflow for the user?`
3. `## Who can provide information and answer questions?`

For each section, extract everything from the `##` heading through to the next `##` heading (or end of file). Include the headings in the output.

**Do NOT include** the `## New Docs` or `## Updated Docs` sections in the JIRA description. Those sections are only in the full documentation plan, which is attached to the ticket as a file.

Combine them into a single description string in the order listed above. Append a footer at the end, choosing the appropriate version based on whether the project is public or private (determined in Step 6a-2):

**If the project is PRIVATE** (`PROJECT_IS_PUBLIC=false`):

```
----
(i) Doc requirements generated by Claude <YYYY-MM-DD>.
See the attached markdown file for the preliminary generated doc plans and proposed updated docs topics.
*Review and validate AI generated doc plans for accuracy with an SME before implementation.*
```

**If the project is PUBLIC** (`PROJECT_IS_PUBLIC=true`):

```
----
(i) Doc requirements generated by Claude <YYYY-MM-DD>.
*Review and validate AI generated doc plans for accuracy with an SME before implementation.*
```

Where `<YYYY-MM-DD>` is today's date from `date +%Y-%m-%d`.

**Note:** The "attached markdown file" reference is omitted for public projects because the detailed docs plan is not attached to public JIRA tickets.

**Step 6b-2: Convert description from markdown to JIRA wiki markup**

The JIRA REST API v2 description field expects JIRA wiki markup, not markdown. After extracting and combining the three sections, convert the description to JIRA wiki markup before creating the ticket.

Use Python to perform the conversion and write the description to a temp file:

```bash
python3 << 'PYEOF'
import re

with open("/tmp/jira_description_raw.txt", "r") as f:
    content = f.read()

lines = content.split('\n')
result = []
in_table = False

for line in lines:
    # Convert ## headings to h2.
    if line.startswith('## '):
        result.append('h2. ' + line[3:])
        continue
    # Convert ### headings to h3.
    if line.startswith('### '):
        result.append('h3. ' + line[4:])
        continue
    # Convert --- horizontal rules to ----
    if line.strip() == '---':
        result.append('----')
        continue
    # Convert **bold** to *bold*
    line = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', line)
    # Convert `code` to {{code}}
    line = re.sub(r'`([^`]+)`', r'{{\1}}', line)
    # Convert markdown links [text](url) to [text|url]
    line = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'[\1|\2]', line)
    # Convert numbered list items (1. 2. 3.) to # items
    numbered = re.match(r'^(\d+)\.\s+(.*)', line)
    if numbered:
        result.append('# ' + numbered.group(2))
        continue
    # Convert markdown table rows
    if '|' in line and line.strip().startswith('|'):
        cells = [c.strip() for c in line.strip().split('|')]
        cells = [c for c in cells if c]
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue
        if not in_table:
            result.append('||' + '||'.join(cells) + '||')
            in_table = True
        else:
            result.append('|' + '|'.join(cells) + '|')
        continue
    else:
        in_table = False
    result.append(line)

with open("/tmp/jira_description_wiki.txt", "w") as f:
    f.write('\n'.join(result))
PYEOF
```

The converted JIRA wiki markup is written to `/tmp/jira_description_wiki.txt` for use in Step 6c.

**Step 6c: Create the JIRA ticket**

Use the JIRA REST API to create a new ticket. The `JIRA_AUTH_TOKEN` environment variable is used for authentication (from `~/.env`, already validated in pre-flight).

```bash
JIRA_URL="https://issues.redhat.com"
TODAY=$(date +%Y-%m-%d)

# Build the summary from the parent ticket's summary
PARENT_SUMMARY=$(curl -s \
  -H "Authorization: Bearer ${JIRA_AUTH_TOKEN}" \
  "${JIRA_URL}/rest/api/2/issue/${TICKET}?fields=summary" | jq -r '.fields.summary')

# Build the complete JSON payload using Python to ensure proper escaping.
# IMPORTANT: Do NOT use shell interpolation with inline --data for large
# multi-line descriptions. Shell interpolation silently truncates or corrupts
# the content, resulting in a null description on the created ticket.
# Instead, use Python to build the JSON payload file and pass it with --data @file.
python3 << PYEOF
import json

with open("/tmp/jira_description_wiki.txt", "r") as f:
    description = f.read()

payload = {
    "fields": {
        "project": {"key": "${CREATE_JIRA_PROJ}"},
        "summary": "[ccs] Docs - ${PARENT_SUMMARY}",
        "description": description,
        "issuetype": {"name": "Story"},
        "components": [{"name": "Documentation"}]
    }
}

with open("/tmp/jira_create_payload.json", "w") as f:
    json.dump(payload, f)
PYEOF

RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer ${JIRA_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  --data @/tmp/jira_create_payload.json \
  "${JIRA_URL}/rest/api/2/issue")

NEW_ISSUE_KEY=$(echo "$RESPONSE" | jq -r '.key')

if [[ -z "$NEW_ISSUE_KEY" || "$NEW_ISSUE_KEY" == "null" ]]; then
    echo "ERROR: Failed to create JIRA ticket."
    echo "Response: $RESPONSE"
    # Mark stage as failed
    exit 1
fi

echo "Created JIRA ticket: ${NEW_ISSUE_KEY}"
echo "URL: ${JIRA_URL}/browse/${NEW_ISSUE_KEY}"
```

**Step 6d: Link the new ticket to the parent ticket**

Create a "Document" link so that the parent ticket "documents" the new docs ticket.

**IMPORTANT**: The link type name is `"Document"` (singular), not `"Documents"` (plural). Using the wrong name returns a 404 error.

```bash
# outwardIssue = TICKET (the parent — source, shows "documents")
# inwardIssue  = NEW_ISSUE_KEY (the docs ticket — destination, shows "is documented by")
curl -s -X POST \
  -H "Authorization: Bearer ${JIRA_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "{
    \"type\": { \"name\": \"Document\" },
    \"outwardIssue\": { \"key\": \"${TICKET}\" },
    \"inwardIssue\": { \"key\": \"${NEW_ISSUE_KEY}\" }
  }" \
  "${JIRA_URL}/rest/api/2/issueLink"

echo "Linked ${TICKET} documents ${NEW_ISSUE_KEY}"
```

If the "Document" link type name does not match, query available link types to find the correct one:

```bash
curl -s -H "Authorization: Bearer ${JIRA_AUTH_TOKEN}" \
  "${JIRA_URL}/rest/api/2/issueLinkType" | jq '.issueLinkTypes[] | {name, inward, outward}'
```

**Step 6e: Attach the docs plan (private projects only)**

Attach the full documentation plan file (Stage 2 output) to the new JIRA ticket. **Skip this step if the project is public** (determined in Step 6a-2), because the detailed docs plan should not be attached to public JIRA tickets.

```bash
if [[ "$PROJECT_IS_PUBLIC" == "true" ]]; then
    echo "Skipping docs plan attachment — project ${CREATE_JIRA_PROJ} is public."
else
    PLAN_FILE=$(jq -r '.stages.planning.output_file // ""' "$STATE_FILE")

    if [[ -n "$PLAN_FILE" && -f "$PLAN_FILE" ]]; then
        curl -s -X POST \
          -H "Authorization: Bearer ${JIRA_AUTH_TOKEN}" \
          -H "X-Atlassian-Token: no-check" \
          -F "file=@${PLAN_FILE}" \
          "${JIRA_URL}/rest/api/2/issue/${NEW_ISSUE_KEY}/attachments"
        echo "Attached docs plan: ${PLAN_FILE}"
    fi
fi
```

**Step 6f: Update state**

After the ticket is created and linked, mark the stage as completed with the new ticket URL as the output file.

```bash
TMP=$(mktemp)
jq --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg output "${JIRA_URL}/browse/${NEW_ISSUE_KEY}" \
   '.stages.create_jira.status = "completed" | .stages.create_jira.completed_at = $now | .stages.create_jira.output_file = $output | .updated_at = $now' \
   "$STATE_FILE" > "$TMP"
mv "$TMP" "$STATE_FILE"
```

## Workflow Completion

After all stages complete successfully (five core stages, plus the optional create_jira stage if `--create-jira` was specified), update the overall workflow status:

```bash
TMP=$(mktemp)
jq --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
   '.status = "completed" | .updated_at = $now' \
   "$STATE_FILE" > "$TMP"
mv "$TMP" "$STATE_FILE"
```

Then display the final status summary showing all stages as completed, and inform the user where the output files are located.

If the `create_jira` stage completed, display the created JIRA ticket URL as a clickable link:

```bash
CREATED_JIRA_URL=$(jq -r '.stages.create_jira.output_file // ""' "$STATE_FILE")
case "$CREATED_JIRA_URL" in
    ""|"null") ;;
    *) echo ""; echo "Created JIRA ticket: ${CREATED_JIRA_URL}" ;;
esac
```

**IMPORTANT**: Always display the JIRA URL at the end of the workflow output so the user can click directly to the created ticket.

## Access Failure Handling

If any stage fails due to access issues (JIRA, GitHub, GitLab):

1. **STOP IMMEDIATELY** — Do not proceed to the next stage
2. **Report the exact error** — Display the full error message
3. **List available env files** — Run `ls -la ~/.env* 2>/dev/null`
4. **Mark the stage as failed** in the state file
5. **Await user action** — User must fix credentials and resume with:
   ```
   /docs-tools:docs-workflow resume <TICKET>
   ```
6. **NEVER guess or infer** — No assumptions about ticket or PR content

### Why this matters

If JIRA access fails and the workflow proceeded anyway, it would make assumptions about what a ticket is about based on the ticket ID, generate documentation for the wrong topic entirely, and waste effort that must be completely redone.

## Usage Examples

Start a new workflow:
```bash
/docs-tools:docs-workflow start RHAISTRAT-123
```

Start with a related PR/MR:
```bash
/docs-tools:docs-workflow start RHAISTRAT-123 --pr https://github.com/org/repo/pull/456
```

Start with a GitLab MR:
```bash
/docs-tools:docs-workflow start RHAISTRAT-123 --pr https://gitlab.com/org/repo/-/merge_requests/789
```

Check workflow status:
```bash
/docs-tools:docs-workflow status RHAISTRAT-123
```

Resume and add a PR URL:
```bash
/docs-tools:docs-workflow resume RHAISTRAT-123 --pr https://github.com/org/repo/pull/456
```

Start with MkDocs Markdown output:
```bash
/docs-tools:docs-workflow start RHAISTRAT-123 --mkdocs
```

Start with MkDocs format and a related PR:
```bash
/docs-tools:docs-workflow start RHAISTRAT-123 --mkdocs --pr https://github.com/org/repo/pull/456
```

Start with JIRA creation in INFERENG project:
```bash
/docs-tools:docs-workflow start RHAISTRAT-123 --create-jira INFERENG
```

Add JIRA creation on resume (after review completes):
```bash
/docs-tools:docs-workflow resume RHAISTRAT-123 --create-jira INFERENG
```

## Prerequisites

- `jq` — JSON processor (install with: `sudo dnf install jq`)
- `python3` — Python 3 for git_review_api.py
- `jira-reader` skill installed (from pr-plugins marketplace)
- `JIRA_AUTH_TOKEN` in `~/.env` (required)
- `GITHUB_TOKEN` and/or `GITLAB_TOKEN` in `~/.env` (for PR/MR access)

## Notes

- If no action is specified, the command defaults to `start`
- The ticket parameter is required for all actions
- Workflow state is maintained between runs for resume functionality
- All outputs are organized by ticket ID for easy tracking
- Multiple --pr URLs can be added across start/resume commands
- **Access failures stop the workflow** — the workflow never guesses or infers content
- The review stage edits files in place in the drafts folder rather than creating copies
- The `--create-jira` stage is optional — it only runs when the flag is provided with a project key
- The `--create-jira` stage checks for existing "is documented by" links on the parent ticket before creating a duplicate ticket. If the "is documented by" link exists, a new ticket is not created. The link type name is `"Document"` (singular)
- The created JIRA description contains three sections from the documentation plan (JTBD, workflow context, contacts), with the full docs plan attached for private projects only
- For **public projects**, the detailed docs plan is NOT attached to the JIRA ticket. Project visibility is determined by making an unauthenticated curl request to the JIRA project endpoint — HTTP 200 means public, any other status means private
- The JIRA description is converted from markdown to JIRA wiki markup before submission, and the JSON payload is built using Python and passed via `--data @file` to avoid shell interpolation issues with large descriptions
- The `--mkdocs` flag switches output from AsciiDoc to Material for MkDocs Markdown. The same agents are used — the writing and review prompts adapt to produce `.md` files with MkDocs conventions. The review stage omits `modular-docs` checks (AsciiDoc-specific) and uses content-quality plus IBM/Red Hat style guide skills
