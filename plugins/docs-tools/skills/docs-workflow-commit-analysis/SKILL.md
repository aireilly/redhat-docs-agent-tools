---
name: docs-workflow-commit-analysis
description: Analyze code commits for documentation impact. Dispatches the commit-analyst agent. Invoked by the orchestrator in commit-driven workflows.
argument-hint: <identifier> --base-path <path> --repo <url> --commits <sha1,sha2,...>
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Commit Analysis Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

## Arguments

- `$1` — Workflow identifier (e.g., `my-service/a1b2c3d-e4f5g6h`)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/my-service/a1b2c3d-e4f5g6h`)
- `--repo <url>` — Code repository URL (required)
- `--commits <sha1,sha2,...>` — Comma-separated commit SHAs to analyze (required)

## Output

```
<base-path>/commit-analysis/analysis.md
```

## Execution

### 1. Parse arguments

Extract the identifier, `--base-path`, `--repo`, and `--commits` from the args string.

Set the output path:

```bash
OUTPUT_DIR="${BASE_PATH}/commit-analysis"
OUTPUT_FILE="${OUTPUT_DIR}/analysis.md"
mkdir -p "$OUTPUT_DIR"
```

### 2. Dispatch agent

Dispatch the `docs-tools:commit-analyst` agent with the following prompt.

**Agent tool parameters:**
- `subagent_type`: `docs-tools:commit-analyst`
- `description`: `Analyze commits for documentation impact`

**Prompt:**

> Analyze the following commits for documentation impact.
>
> **Repository**: `<REPO_URL>`
> **Commits**: `<SHA1>`, `<SHA2>`, ...
>
> Save your complete analysis to: `<OUTPUT_FILE>`
>
> Follow your standard analysis methodology (fetch commit data, parse messages, analyze diffs for change signals, grade doc impact). Format the output as structured markdown for the requirements-analyst.

### 3. Verify output

After the agent completes, verify the output file exists at `<OUTPUT_FILE>`.

If no output file is found, report an error.
