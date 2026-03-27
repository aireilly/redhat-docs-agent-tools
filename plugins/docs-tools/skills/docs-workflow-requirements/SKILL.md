---
name: docs-workflow-requirements
description: Analyze documentation requirements from JIRA tickets, local files, Google Drive, and web sources. Dispatches the requirements-analyst agent. Invoked by the orchestrator.
argument-hint: <id> --base-path <path> [--pr <url>]... [--jql <query>] [--tickets <list>] [--inputs <path-or-url>]...
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Requirements Analysis Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

## Arguments

- `$1` — Workflow ID (required). If it matches a JIRA ticket pattern (`[A-Z]+-[0-9]+`), it is also fetched as a JIRA ticket source automatically.
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

### 2. Dispatch agent

Dispatch the `docs-tools:requirements-analyst` agent with the following prompt.

**Agent tool parameters:**
- `subagent_type`: `docs-tools:requirements-analyst`
- `description`: `Analyze requirements for <ID>`

**Prompt:**

> Analyze documentation requirements for workflow `<ID>`.
>
> **JIRA tickets** (fetch all, run --graph on each to discover linked docs and PRs):
> - `<TICKET_1>`
> - `<TICKET_2>`
>
> **JQL query** (use --fetch-details):
> - `<JQL>`
>
> **Additional input sources** (auto-detect type for each):
> - `<INPUT_1>`
>
> **PR/MR URLs** (merge with any auto-discovered URLs, dedup):
> - `<PR_URL_1>`
>
> Save your complete analysis to: `<OUTPUT_FILE>`
>
> Gather all sources before analysis. Follow your standard analysis methodology.
> Format the output as structured markdown for the next stage.

Each section is conditional — include only if sources of that type exist. If `$1` matched the JIRA pattern, it appears in the JIRA tickets list.

### 3. Verify output

After the agent completes, verify the output file exists at `<OUTPUT_FILE>`.

If no output file is found, report an error.
