---
name: docs-workflow-tech-review
description: >
  Technical accuracy review of documentation drafts. Dispatches the
  technical-reviewer agent. Output includes confidence rating (HIGH/MEDIUM/LOW).
  Iteration logic is owned by the orchestrator, not this skill.
argument-hint: <ticket> --base-path <path>
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Technical Review Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

This skill performs a single review pass. The iteration loop (re-running with fixes between passes) is driven by the orchestrator skill, not this step skill.

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)

## Input

```
<base-path>/writing/
```

## Output

```
<base-path>/technical-review/review.md
```

## Execution

### 1. Parse arguments

Extract the ticket ID and `--base-path` from the args string.

Set the paths:

```bash
DRAFTS_DIR="${BASE_PATH}/writing"
OUTPUT_DIR="${BASE_PATH}/technical-review"
OUTPUT_FILE="${OUTPUT_DIR}/review.md"
mkdir -p "$OUTPUT_DIR"
```

### 2. Dispatch agent

Dispatch the `docs-tools:technical-reviewer` agent with the following prompt.

**Agent tool parameters:**
- `subagent_type`: `docs-tools:technical-reviewer`
- `description`: `Technical review of documentation for <TICKET>`

**Prompt:**

> Perform a technical review of the documentation drafts for ticket `<TICKET>`.
> Source drafts location: `<DRAFTS_DIR>/`
> Review all .adoc and .md files. Follow your standard review methodology.
> Save your review report to: `<OUTPUT_FILE>`
>
> The report must include an `Overall technical confidence: HIGH|MEDIUM|LOW` line.

### 3. Verify output

After the agent completes, verify the review report exists at `<OUTPUT_FILE>`.

The review report **must** include an `Overall technical confidence: HIGH|MEDIUM|LOW` line. If this line is missing from the output, the orchestrator will treat it as a step failure.
