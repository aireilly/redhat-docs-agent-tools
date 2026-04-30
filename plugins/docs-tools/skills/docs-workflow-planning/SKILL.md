---
name: docs-workflow-planning
description: Create a documentation plan from requirements analysis output. Dispatches the docs-tools:docs-planner agent. Invoked by the orchestrator.
argument-hint: <ticket> --base-path <path>
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent
---

# Documentation Planning Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)

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

**You MUST use the Agent tool** to invoke the `docs-tools:docs-planner` subagent. Do NOT read the agent's markdown file or attempt to perform the agent's work yourself — the agent has a specialized system prompt and must run as an isolated subagent.

**Agent tool parameters:**
- `subagent_type`: `docs-tools:docs-planner`
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

**[Include only if `<BASE_PATH>/scope-req-audit/evidence-status.json` exists]** Append the following paragraph to the prompt:

> Code evidence status is available at `<BASE_PATH>/scope-req-audit/evidence-status.json`. Read it and use the evidence status when making scoping decisions:
>
> - **Grounded** requirements: create full module specifications as normal
> - **Partial** requirements: create module specifications but note what evidence was found and what is missing — flag for SME review
> - **Absent** requirements: do NOT create module specifications. Instead, list them in a "Deferred requirements (no code evidence)" section at the end of the plan, including the recommended action from the evidence status. These may be unimplemented features — documenting them risks fabrication
>
> If `discovered_repos` lists repos that weren't indexed, note them in the deferred section as potential sources for resolving absent requirements.

### 3. Verify output

After the agent completes, verify the output file exists at `<OUTPUT_FILE>`.

If no output file is found, report an error.

### 4. Write step-result.json

Read `<OUTPUT_FILE>` and count the number of module specifications. Count each occurrence of:

- Level-3 headings (`###`) whose text begins with `Module:`
- Numbered or bulleted list items within the "Module Specifications" section that start with `Module:`

Ignore headings or list items outside the "Module Specifications" section, and skip items inside code blocks or blockquotes. Treat duplicate module titles as separate modules (no deduplication). This count becomes the `module_count` field.

Write the sidecar to `<OUTPUT_DIR>/step-result.json`:

```json
{
  "schema_version": 1,
  "step": "planning",
  "ticket": "<TICKET>",
  "completed_at": "<current ISO 8601 timestamp>",
  "module_count": <number of modules in the plan>
}
```
