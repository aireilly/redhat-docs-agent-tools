---
name: docs-workflow-style-review
description: >
  Style guide compliance review of documentation drafts. Dispatches the
  docs-reviewer agent with Vale linting and 18+ style guide review skills.
argument-hint: <ticket> --base-path <path> --format <adoc|mkdocs>
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Style Review Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → dispatch agent → write output**.

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--format <adoc|mkdocs>` — Documentation format (default: `adoc`)

## Input

```
<base-path>/writing/
```

## Output

```
<base-path>/style-review/review.md
```

## Execution

### 1. Parse arguments

Extract the ticket ID, `--base-path`, and `--format` from the args string.

Set the paths:

```bash
DRAFTS_DIR="${BASE_PATH}/writing"
OUTPUT_DIR="${BASE_PATH}/style-review"
OUTPUT_FILE="${OUTPUT_DIR}/review.md"
mkdir -p "$OUTPUT_DIR"
```

### 2. Dispatch agent

Dispatch the `docs-tools:docs-reviewer` agent with a format-specific prompt.

**Agent tool parameters:**
- `subagent_type`: `docs-tools:docs-reviewer`
- `description`: `Review documentation for <TICKET>`

**Prompt (AsciiDoc — `--format adoc`):**

> Review the AsciiDoc documentation drafts for ticket `<TICKET>`.
> Source drafts location: `<DRAFTS_DIR>/`
>
> **Edit files in place**. Do NOT create copies.
>
> For each file:
> 1. Run Vale linting once (use the `vale-tools:lint-with-vale` skill)
> 2. Fix obvious errors where the fix is clear and unambiguous
> 3. Run documentation review skills:
>    - Red Hat docs: docs-tools:docs-review-modular-docs, docs-tools:docs-review-content-quality
>    - IBM Style Guide: docs-tools:ibm-sg-audience-and-medium, docs-tools:ibm-sg-language-and-grammar, docs-tools:ibm-sg-punctuation, docs-tools:ibm-sg-numbers-and-measurement, docs-tools:ibm-sg-structure-and-format, docs-tools:ibm-sg-references, docs-tools:ibm-sg-technical-elements, docs-tools:ibm-sg-legal-information
>    - Red Hat SSG: docs-tools:rh-ssg-grammar-and-language, docs-tools:rh-ssg-formatting, docs-tools:rh-ssg-structure, docs-tools:rh-ssg-technical-examples, docs-tools:rh-ssg-gui-and-links, docs-tools:rh-ssg-legal-and-support, docs-tools:rh-ssg-accessibility, docs-tools:rh-ssg-release-notes (if applicable)
> 4. Skip ambiguous issues requiring broader context
>
> Save the review report to: `<OUTPUT_FILE>`

**Prompt (MkDocs — `--format mkdocs`):**

> Review the Material for MkDocs Markdown documentation drafts for ticket `<TICKET>`.
> Source drafts location: `<DRAFTS_DIR>/`
>
> **Edit files in place**. Do NOT create copies.
>
> For each file:
> 1. Run Vale linting once (use the `vale-tools:lint-with-vale` skill)
> 2. Fix obvious errors where the fix is clear and unambiguous
> 3. Run documentation review skills:
>    - Content quality: docs-tools:docs-review-content-quality
>    - IBM Style Guide: docs-tools:ibm-sg-audience-and-medium, docs-tools:ibm-sg-language-and-grammar, docs-tools:ibm-sg-punctuation, docs-tools:ibm-sg-numbers-and-measurement, docs-tools:ibm-sg-structure-and-format, docs-tools:ibm-sg-references, docs-tools:ibm-sg-technical-elements, docs-tools:ibm-sg-legal-information
>    - Red Hat SSG: docs-tools:rh-ssg-grammar-and-language, docs-tools:rh-ssg-formatting, docs-tools:rh-ssg-structure, docs-tools:rh-ssg-technical-examples, docs-tools:rh-ssg-gui-and-links, docs-tools:rh-ssg-legal-and-support, docs-tools:rh-ssg-accessibility
> 4. Skip ambiguous issues requiring broader context
>
> Save the review report to: `<OUTPUT_FILE>`

Note: MkDocs review omits `docs-review-modular-docs` (AsciiDoc-specific) and `rh-ssg-release-notes`.

### 3. Verify output

After the agent completes, verify the review report exists at `<OUTPUT_FILE>`.
