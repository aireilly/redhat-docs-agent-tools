---
name: docs-workflow-planning
description: Create a documentation plan from requirements analysis output. Dispatches the docs-planner or docs-planner-jtbd agent based on --no-jtbd flag. Invoked by the orchestrator.
argument-hint: <ticket> --base-path <path> [--no-jtbd]
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Documentation Planning Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

## Arguments

- `$1` — JIRA ticket ID or workflow ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--no-jtbd` — Use feature-based information architecture instead of JTBD (optional)

## Input

```
<base-path>/requirements/requirements.md
```

## Output

```
<base-path>/planning/plan.md
```

## Execution

### 1. Parse arguments

Extract the ticket ID, `--base-path`, and `--no-jtbd` from the args string.

Set the paths:

```bash
INPUT_FILE="${BASE_PATH}/requirements/requirements.md"
OUTPUT_DIR="${BASE_PATH}/planning"
OUTPUT_FILE="${OUTPUT_DIR}/plan.md"
mkdir -p "$OUTPUT_DIR"
```

### 2. Dispatch agent

Select the agent based on the `--no-jtbd` flag:

- **If `--no-jtbd` is present**: dispatch `docs-tools:docs-planner` (feature-based planning)
- **Otherwise (default)**: dispatch `docs-tools:docs-planner-jtbd` (JTBD planning)

**Agent tool parameters:**
- `subagent_type`: `docs-tools:docs-planner` or `docs-tools:docs-planner-jtbd`
- `description`: `Create documentation plan for <TICKET>`

**Prompt:**

> Create a comprehensive documentation plan based on the requirements analysis.
>
> Read the requirements from: `<INPUT_FILE>`
>
> The plan must include:
> 1. Gap analysis (existing vs needed documentation)
> 2. Module specifications (type, title, audience, content points, prerequisites, dependencies)
> 3. Implementation order based on dependencies
> 4. Assembly structure (how modules group together)
> 5. Content sources from JIRA and PR/MR analysis
>
> Save the complete plan to: `<OUTPUT_FILE>`

### 3. Verify output

After the agent completes, verify the output file exists at `<OUTPUT_FILE>`.

If no output file is found, report an error.
