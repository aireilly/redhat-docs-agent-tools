---
name: docs-workflow-create-jira
description: Create a linked JIRA ticket for documentation work. No agent dispatch. Uses direct JIRA REST API calls via a shell script. Checks for existing links, handles public/private project visibility, converts markdown to JIRA wiki markup.
model: claude-haiku-4-5@20251001
argument-hint: <ticket> --base-path <path> --project <PROJECT>
allowed-tools: Read, Write, Bash
---

# Create JIRA Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → do work → write output**.

Unlike other step skills, this skill does **not** dispatch an agent. It runs `scripts/create-jira-ticket.sh` directly.

**Output**: `null` (produces a JIRA URL, not a file)

## Arguments

- `$1` — Parent JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `artifacts/proj-123`)
- `--project <PROJECT>` — Target JIRA project key for the new ticket (required)

## Input

```
<base-path>/planning/plan.md
```

## Environment

Requires `JIRA_API_TOKEN` and `JIRA_EMAIL` in the environment (typically sourced from `~/.env`).

## Execution

Run the create-jira-ticket script:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/create-jira-ticket.sh "$TICKET" "$PROJECT" "${BASE_PATH}/planning/plan.md"
```

The script handles all steps:

1. **Check for existing link** — if a "Document" link already exists on the parent ticket, exits early
2. **Check project visibility** — unauthenticated probe to determine public vs private
3. **Extract description** — pulls JTBD sections from the plan, appends dated footer
4. **Convert to JIRA wiki markup** — calls `scripts/md2wiki.py` for markdown → wiki conversion
5. **Create JIRA ticket** — POST to JIRA REST API with `[ccs] Docs -` prefix
6. **Link to parent** — creates a "Document" issue link (singular, not "Documents")
7. **Attach plan** — attaches the full plan file (private projects only)

The script prints the JIRA URL on success (e.g., `https://redhat.atlassian.net/browse/DOCS-456`).

This step does not write an output file. The progress file records `output: null` for this step.
