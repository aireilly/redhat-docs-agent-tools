---
name: docs-workflow-writing
description: >
  Write documentation drafts from a documentation plan. Dispatches the
  docs-writer agent. Supports AsciiDoc (default) and MkDocs formats.
  Also supports fix mode for applying technical review corrections.
argument-hint: <ticket> --base-path <path> --format <adoc|mkdocs> [--fix-from <review_path>]
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Documentation Writing Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

Supports two modes:
- **Normal mode**: Write new documentation from a plan
- **Fix mode**: Apply targeted corrections from a technical review

## Arguments

### Normal mode

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--format <adoc|mkdocs>` — Output format (default: `adoc`)

### Fix mode

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path
- `--fix-from <path>` — Technical review output file (triggers fix mode)

## Input

```
<base-path>/planning/plan.md
```

## Output

```
<base-path>/writing/
  _index.md
  assembly_*.adoc        (AsciiDoc mode)
  modules/*.adoc         (AsciiDoc mode)
  mkdocs-nav.yml         (MkDocs mode)
  docs/*.md              (MkDocs mode)
```

## Execution

### 1. Parse arguments

Extract the ticket ID, `--base-path`, and `--format` from the args string.

If `--fix-from` is present, operate in **fix mode**. Otherwise, operate in **normal mode**.

Set the paths:

```bash
INPUT_FILE="${BASE_PATH}/planning/plan.md"
OUTPUT_DIR="${BASE_PATH}/writing"
OUTPUT_FILE="${OUTPUT_DIR}/_index.md"
mkdir -p "$OUTPUT_DIR"
```

### 2a. Normal mode — dispatch writer agent

**Agent tool parameters:**
- `subagent_type`: `docs-tools:docs-writer`
- `description`: `Write <format> documentation for <TICKET>`

**Prompt (AsciiDoc):**

> Write complete AsciiDoc documentation based on the documentation plan for ticket `<TICKET>`.
>
> Read the plan from: `<INPUT_FILE>`
>
> **IMPORTANT**: Write COMPLETE .adoc files, not summaries or outlines.
>
> Save modules to: `<OUTPUT_DIR>/modules/`
> Save assemblies to: `<OUTPUT_DIR>/`
> Create index at: `<OUTPUT_FILE>`

**Prompt (MkDocs):**

> Write complete Material for MkDocs Markdown documentation based on the documentation plan for ticket `<TICKET>`.
>
> Read the plan from: `<INPUT_FILE>`
>
> **IMPORTANT**: Write COMPLETE .md files with YAML frontmatter (title, description). Use Material for MkDocs conventions: admonitions, content tabs, code blocks with titles, heading hierarchy starting at `# h1`.
>
> Save pages to: `<OUTPUT_DIR>/docs/`
> Create nav fragment at: `<OUTPUT_DIR>/mkdocs-nav.yml`
> Create index at: `<OUTPUT_FILE>`

### 2b. Fix mode — dispatch writer agent for corrections

When invoked with `--fix-from`, the skill applies targeted corrections to existing drafts.

**Agent tool parameters:**
- `subagent_type`: `docs-tools:docs-writer`
- `description`: `Fix documentation for <TICKET>`

**Prompt:**

> Apply fixes to documentation drafts based on technical review feedback for ticket `<TICKET>`.
>
> Read the review report from: `<FIX_FROM_PATH>`
> Drafts location: `<OUTPUT_DIR>/`
>
> For each issue flagged in the review:
> 1. If the fix is clear and unambiguous, apply it directly
> 2. If the issue requires broader context or judgment, skip it
> 3. Do NOT rewrite content that was not flagged
>
> Edit files in place. Do NOT create copies or new files.

In fix mode, the skill does not create new modules or restructure content.

### 3. Verify output

**Normal mode**: Check that `_index.md` exists at `<OUTPUT_FILE>`.

**Fix mode**: No output verification needed — files are edited in place.
