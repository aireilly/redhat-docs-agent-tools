---
name: docs-workflow-planning
description: Create a documentation plan from requirements analysis output. Dispatches the docs-planner agent. Invoked by the orchestrator.
argument-hint: <ticket> --base-path <path>
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent
---

# Documentation Planning Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `artifacts/proj-123`)

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

Extract the ticket ID and `--base-path` from the args string.

Set the paths:

```bash
INPUT_FILE="${BASE_PATH}/requirements/requirements.md"
OUTPUT_DIR="${BASE_PATH}/planning"
OUTPUT_FILE="${OUTPUT_DIR}/plan.md"
mkdir -p "$OUTPUT_DIR"
```

### 2. Dispatch agent

**You MUST use the Agent tool** to invoke the `docs-planner` subagent. Do NOT read the agent's markdown file or attempt to perform the agent's work yourself — the agent has a specialized system prompt and must run as an isolated subagent.

**Agent tool parameters:**
- `subagent_type`: `docs-planner`
- `description`: `Create documentation plan for <TICKET>`

**Prompt** (pass this as the `prompt` parameter to the Agent tool):

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
