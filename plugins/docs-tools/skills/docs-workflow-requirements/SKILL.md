---
name: docs-workflow-requirements
description: Analyze documentation requirements from JIRA tickets, local files, Google Drive, and web sources. Dispatches the requirements-analyst agent. Invoked by the orchestrator.
argument-hint: <id> --base-path <path> [--pr <url>]... [--jql <query>] [--tickets <list>] [--inputs <path-or-url>]...
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Requirements Analysis Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

## Arguments

- `$1` — Workflow ID (required). A JIRA ticket ID for single-ticket workflows, or a doc set name for multi-source workflows.
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--pr <url>` — PR/MR URL to include in analysis (repeatable)
- `--jql <query>` — JQL query for bulk JIRA ticket fetch (optional)
- `--tickets <list>` — Comma-separated list of JIRA ticket IDs (optional)
- `--inputs <path-or-url>` — Additional input sources (repeatable). Each value is auto-detected as a local file path, Google Drive URL, or web URL.

## Output

```
<base-path>/requirements/requirements.md
```

## Execution

### 1. Parse arguments

Extract the workflow ID, `--base-path`, and any optional flags from the args string.

Set the output path:

```bash
OUTPUT_DIR="${BASE_PATH}/requirements"
OUTPUT_FILE="${OUTPUT_DIR}/requirements.md"
mkdir -p "$OUTPUT_DIR"
```

Determine the mode:
- **Multi-source mode**: If any of `--jql`, `--tickets`, or `--inputs` are present. `$1` is a workflow ID only.
- **Single-ticket mode**: If none of those flags are present. `$1` is a JIRA ticket ID.

### 2. Dispatch agent

Dispatch the `docs-tools:requirements-analyst` agent with the following prompt.

**Agent tool parameters:**
- `subagent_type`: `docs-tools:requirements-analyst`
- `description`: `Analyze requirements for <ID>`

**Prompt (single-ticket mode):**

> Analyze documentation requirements for JIRA ticket `<ID>`.
>
> Manually-provided PR/MR URLs to include in analysis (merge with any auto-discovered URLs, dedup):
> - `<PR_URL_1>`
> - `<PR_URL_2>`
>
> Save your complete analysis to: `<OUTPUT_FILE>`
>
> Follow your standard analysis methodology (JIRA fetch, ticket graph traversal, PR/MR analysis, web search expansion). Format the output as structured markdown for the next stage.

**Prompt (multi-source mode):**

> Analyze documentation requirements from multiple sources for workflow `<ID>`.
>
> **JIRA sources** (fetch all, run --graph on each):
> - JQL query: `<JQL>` (use --fetch-details)
> - Explicit tickets: `<TICKETS>`
>
> **Additional input sources** (auto-detect type for each):
> - `<INPUT_1>`
> - `<INPUT_2>`
>
> **PR/MR URLs** (merge with any auto-discovered URLs, dedup):
> - `<PR_URL_1>`
> - `<PR_URL_2>`
>
> Save your complete analysis to: `<OUTPUT_FILE>`
>
> Gather ALL sources before analysis. Process each --inputs value by auto-detecting its type (Google Drive URL → gdoc2md.py, web URL → article_extractor.py, local path → Read tool). Then follow your standard analysis methodology. Produce a single unified requirements.md covering all sources.

Each section in the prompt is conditional — include only if the corresponding flags were provided. If no `--jql` was passed, omit the JQL line. If no `--inputs` were passed, omit the inputs section. Etc.

### 3. Verify output

After the agent completes, verify the output file exists at `<OUTPUT_FILE>`.

If no output file is found, report an error.
