---
name: docs-workflow-planning
description: Create a documentation plan from requirements analysis output. Dispatches the docs-planner agent with the specified content paradigm. Invoked by the orchestrator.
argument-hint: <id> --base-path <path> [--paradigm <jtbd|user-stories>]
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Documentation Planning Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

## Arguments

- `$1` — Workflow ID (JIRA ticket, doc set name, or any identifier) (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--paradigm <jtbd|user-stories>` — Content paradigm (default: `jtbd`)

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

Extract the workflow ID, `--base-path`, and `--paradigm` from the args string. Default paradigm to `jtbd` if not specified.

Set the paths:

```bash
INPUT_FILE="${BASE_PATH}/requirements/requirements.md"
OUTPUT_DIR="${BASE_PATH}/planning"
OUTPUT_FILE="${OUTPUT_DIR}/plan.md"
mkdir -p "$OUTPUT_DIR"
```

### 2. Dispatch agent

Always dispatch `docs-tools:docs-planner`. Pass the content paradigm in the prompt so the agent reads the correct paradigm reference file.

**Agent tool parameters:**
- `subagent_type`: `docs-tools:docs-planner`
- `description`: `Create documentation plan for <ID>`

**Prompt:**

> Create a comprehensive documentation plan based on the requirements analysis.
>
> **Content paradigm: <PARADIGM>**
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
