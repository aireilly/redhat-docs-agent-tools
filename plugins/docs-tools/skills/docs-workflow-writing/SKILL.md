---
name: docs-workflow-writing
description: Write documentation from a documentation plan. Dispatches the docs-writer or docs-writer-jtbd agent based on --no-jtbd flag. Supports AsciiDoc (default) and MkDocs formats. Default placement is UPDATE-IN-PLACE; use --draft for staging area. Also supports fix mode for applying technical review corrections.
argument-hint: <ticket> --base-path <path> --format <adoc|mkdocs> [--draft] [--no-jtbd] [--fix-from <review_path>]
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Documentation Writing Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

Supports three modes:
- **Default mode (UPDATE-IN-PLACE)**: Detect the repo's build framework and write files directly to the correct repo locations. Create a manifest listing files written.
- **Draft mode (`--draft`)**: Write files to a staging area under `<base-path>/writing/`. No framework detection, no repo modifications.
- **Fix mode (`--fix-from`)**: Apply targeted corrections from a technical review.

## Arguments

### Normal mode

- `$1` — JIRA ticket ID or workflow ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--format <adoc|mkdocs>` — Output format (default: `adoc`)
- `--draft` — Use DRAFT placement mode (staging area) instead of UPDATE-IN-PLACE
- `--no-jtbd` — Use feature-based writing conventions instead of JTBD (optional)

### Fix mode

- `$1` — JIRA ticket ID or workflow ID (required)
- `--base-path <path>` — Base output path
- `--fix-from <path>` — Technical review output file (triggers fix mode)
- `--no-jtbd` — Use feature-based writing conventions instead of JTBD (optional)

## Input

```
<base-path>/planning/plan.md
```

## Output

**UPDATE-IN-PLACE mode (default):**

Files are written directly to their correct repo locations. A manifest is created at:

```
<base-path>/writing/_index.md
```

**Draft mode (`--draft`):**

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

Extract the ticket ID, `--base-path`, `--format`, `--draft`, and `--no-jtbd` from the args string.

If `--fix-from` is present, operate in **fix mode**. Otherwise, check for `--draft` to determine placement mode.

Set the paths:

```bash
INPUT_FILE="${BASE_PATH}/planning/plan.md"
OUTPUT_DIR="${BASE_PATH}/writing"
OUTPUT_FILE="${OUTPUT_DIR}/_index.md"
mkdir -p "$OUTPUT_DIR"
```

### 2a. UPDATE-IN-PLACE mode (default — no `--draft`)

Select the agent based on the `--no-jtbd` flag:

- **If `--no-jtbd` is present**: dispatch `docs-tools:docs-writer` (feature-based writing)
- **Otherwise (default)**: dispatch `docs-tools:docs-writer-jtbd` (JTBD writing)

**Agent tool parameters:**
- `subagent_type`: `docs-tools:docs-writer` or `docs-tools:docs-writer-jtbd`
- `description`: `Write <format> documentation for <TICKET>`

**Prompt (AsciiDoc):**

> Write complete AsciiDoc documentation based on the documentation plan for ticket `<TICKET>`.
>
> Read the plan from: `<INPUT_FILE>`
>
> **IMPORTANT**: Write COMPLETE .adoc files, not summaries or outlines.
>
> **Placement mode: UPDATE-IN-PLACE**
>
> Place files directly in the repository following existing conventions. Before writing any files:
> 1. Detect the repository's documentation build framework (Antora, ccutil, Sphinx, etc.)
> 2. Analyze existing file naming conventions, directory layout, include patterns, and nav/TOC structure
> 3. Determine the correct target path for each module based on the detected framework and conventions
>
> Write modules and assemblies directly to their correct repo locations. Update navigation/TOC files as needed, following existing patterns.
>
> Create a manifest at `<OUTPUT_FILE>` listing all files written and their repo locations.

**Prompt (MkDocs):**

> Write complete Material for MkDocs Markdown documentation based on the documentation plan for ticket `<TICKET>`.
>
> Read the plan from: `<INPUT_FILE>`
>
> **IMPORTANT**: Write COMPLETE .md files with YAML frontmatter (title, description). Use Material for MkDocs conventions: admonitions, content tabs, code blocks with titles, heading hierarchy starting at `# h1`.
>
> **Placement mode: UPDATE-IN-PLACE**
>
> Place files directly in the repository following existing conventions. Before writing any files:
> 1. Detect the repository's documentation build framework (MkDocs, Docusaurus, Hugo, etc.)
> 2. Analyze existing file naming conventions, directory layout, and nav structure
> 3. Determine the correct target path for each page based on the detected framework and conventions
>
> Write pages directly to their correct repo locations. Update `mkdocs.yml` nav section or equivalent as needed, following existing patterns.
>
> Create a manifest at `<OUTPUT_FILE>` listing all files written and their repo locations.

### 2b. DRAFT mode (`--draft`)

Select the agent based on the `--no-jtbd` flag (same logic as 2a).

**Agent tool parameters:**
- `subagent_type`: `docs-tools:docs-writer` or `docs-tools:docs-writer-jtbd`
- `description`: `Write <format> documentation for <TICKET>`

**Prompt (AsciiDoc, draft):**

> Write complete AsciiDoc documentation based on the documentation plan for ticket `<TICKET>`.
>
> Read the plan from: `<INPUT_FILE>`
>
> **IMPORTANT**: Write COMPLETE .adoc files, not summaries or outlines.
>
> **Placement mode: DRAFT (staging area)**
>
> Save files to the staging area. Do not modify any existing repository files.
>
> Output folder structure:
> ```
> <OUTPUT_DIR>/
> ├── _index.md                     # Index of all modules
> ├── assembly_<name>.adoc          # Assembly files at root
> └── modules/                      # All module files
>     ├── <concept-name>.adoc
>     ├── <procedure-name>.adoc
>     └── <reference-name>.adoc
> ```
>
> Save modules to: `<OUTPUT_DIR>/modules/`
> Save assemblies to: `<OUTPUT_DIR>/`
> Create index at: `<OUTPUT_FILE>`

**Prompt (MkDocs, draft):**

> Write complete Material for MkDocs Markdown documentation based on the documentation plan for ticket `<TICKET>`.
>
> Read the plan from: `<INPUT_FILE>`
>
> **IMPORTANT**: Write COMPLETE .md files with YAML frontmatter (title, description). Use Material for MkDocs conventions: admonitions, content tabs, code blocks with titles, heading hierarchy starting at `# h1`.
>
> **Placement mode: DRAFT (staging area)**
>
> Save files to the staging area. Do not modify any existing repository files.
>
> Output folder structure:
> ```
> <OUTPUT_DIR>/
> ├── _index.md                     # Index of all pages
> ├── mkdocs-nav.yml                # Suggested nav tree fragment
> └── docs/                         # All page files
>     ├── <concept-name>.md
>     ├── <procedure-name>.md
>     └── <reference-name>.md
> ```
>
> Save pages to: `<OUTPUT_DIR>/docs/`
> Create nav fragment at: `<OUTPUT_DIR>/mkdocs-nav.yml`
> Create index at: `<OUTPUT_FILE>`

### 2c. Fix mode — dispatch writer agent for corrections

When invoked with `--fix-from`, the skill applies targeted corrections to existing drafts.

Select the agent based on the `--no-jtbd` flag (same logic as 2a).

**Agent tool parameters:**
- `subagent_type`: `docs-tools:docs-writer` or `docs-tools:docs-writer-jtbd`
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

**Normal mode (both UPDATE-IN-PLACE and DRAFT)**: Check that `_index.md` exists at `<OUTPUT_FILE>`.

**Fix mode**: No output verification needed — files are edited in place.
