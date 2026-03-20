---
name: docs-workflow-integrate
description: >
  Integrate documentation drafts into a repository's build framework.
  Supports two phases: PLAN (propose changes) and EXECUTE (apply changes).
  Confirmation gate between phases is owned by the orchestrator.
argument-hint: <ticket> --base-path <path> --phase <plan|execute>
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Integration Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

Under the `docs-orchestrator`, integration is expressed as two separate steps in the YAML (`integrate-plan` and `integrate-execute`). The confirmation gate between them lives in the orchestrator skill, not here.

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--phase <plan|execute>` — Integration phase (required)

## Input

```
<base-path>/writing/                         (both phases)
<base-path>/integrate-plan/plan.md           (execute phase only)
```

## Output

```
<base-path>/integrate-plan/plan.md           (plan phase)
<base-path>/integrate-execute/report.md      (execute phase)
```

## Execution

### 1. Parse arguments

Extract the ticket ID, `--base-path`, and `--phase` from the args string.

Set the paths based on phase:

```bash
DRAFTS_DIR="${BASE_PATH}/writing"

if [[ "$PHASE" == "plan" ]]; then
  OUTPUT_DIR="${BASE_PATH}/integrate-plan"
  OUTPUT_FILE="${OUTPUT_DIR}/plan.md"
elif [[ "$PHASE" == "execute" ]]; then
  PLAN_FILE="${BASE_PATH}/integrate-plan/plan.md"
  OUTPUT_DIR="${BASE_PATH}/integrate-execute"
  OUTPUT_FILE="${OUTPUT_DIR}/report.md"
fi

mkdir -p "$OUTPUT_DIR"
```

### 2. Dispatch agent

Dispatch the `docs-tools:docs-integrator` agent with a phase-specific prompt.

**Agent tool parameters:**
- `subagent_type`: `docs-tools:docs-integrator`

#### Plan phase

- `description`: `Plan integration of documentation for <TICKET>`

**Prompt:**

> Phase: PLAN
> Plan the integration of documentation drafts for ticket `<TICKET>`.
> Drafts location: `<DRAFTS_DIR>/`
> Save the integration plan to: `<OUTPUT_FILE>`

**Expected output**: `<base-path>/integrate-plan/plan.md`

#### Execute phase

- `description`: `Execute integration of documentation for <TICKET>`

**Prompt:**

> Phase: EXECUTE
> Execute the integration plan for ticket `<TICKET>`.
> Drafts location: `<DRAFTS_DIR>/`
> Integration plan: `<PLAN_FILE>`
> Save the integration report to: `<OUTPUT_FILE>`

**Expected output**: `<base-path>/integrate-execute/report.md`

### 3. Verify output

After the agent completes, verify the output file exists at `<OUTPUT_FILE>`.
