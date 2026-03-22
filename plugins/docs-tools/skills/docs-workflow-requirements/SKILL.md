---
name: docs-workflow-requirements
description: >
  Analyze documentation requirements for a JIRA ticket. Dispatches the
  requirements-analyst agent. Invoked by the orchestrator.
argument-hint: <ticket> --base-path <path> [--pr <url>]...
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Requirements Analysis Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--pr <url>` — PR/MR URL to include in analysis (repeatable)

## Output

```
<base-path>/requirements/requirements.md
```

## Execution

### 1. Parse arguments

Extract the ticket ID, `--base-path`, and any `--pr` URLs from the args string.

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
- `description`: `Analyze requirements for <TICKET>`

**Prompt:**

> Analyze documentation requirements for JIRA ticket `<TICKET>`.
>
> Manually-provided PR/MR URLs to include in analysis (merge with any auto-discovered URLs, dedup):
> - `<PR_URL_1>`
> - `<PR_URL_2>`
>
> Save your complete analysis to: `<OUTPUT_FILE>`
>
> Follow your standard analysis methodology (JIRA fetch, ticket graph traversal, PR/MR analysis, web search expansion). Format the output as structured markdown for the next stage.

The PR URL bullet list is conditional — include those bullets only if PR URLs were provided. If no `--pr` URLs exist, omit the bullet list but keep the rest of the prompt.

### 3. Verify output

After the agent completes, verify the output file exists at `<OUTPUT_FILE>`.

If no output file is found, report an error.
