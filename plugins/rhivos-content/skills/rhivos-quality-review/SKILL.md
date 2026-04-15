---
name: rhivos-quality-review
description: >-
  Runs multi-pass quality review on RHIVOS AsciiDoc modules: Red Hat SSG style
  guide compliance, Vale linting, modular docs validation, and RHIVOS-specific
  checks (product attributes, ASIL B placement, safety references). Supports
  auto-fix mode. Use this skill after rhivos-jtbd-restructure or on any RHIVOS
  AsciiDoc modules.
argument-hint: "<doc-title-slug> [--threshold <N>] [--fix]"
allowed-tools: Read, Write, Bash, Glob, Grep, Edit, Skill, Agent, AskUserQuestion
---

# Quality Review

Runs parallel quality review passes on RHIVOS AsciiDoc modules and applies RHIVOS-specific validation rules.

## When to use

- After `rhivos-jtbd-restructure` has produced approved modules
- When reviewing any RHIVOS AsciiDoc content for style compliance
- Before publishing modules to the RHIVOS doc repo

## Inputs

Parse from `$ARGUMENTS`:

- **`<doc-title-slug>`** (required, positional) — the kebab-case slug identifying the Doc Title
- **`--threshold <N>`** (optional) — confidence threshold for reporting issues. Default: 80
- **`--fix`** (optional) — auto-apply fixes at confidence >= 65%, prompt for lower

Expects modules at `artifacts/<doc-title-slug>/modules/`.

## Process

### 1. Run three review passes in parallel

Launch three Agent instances concurrently:

#### Pass 1: Style guide compliance

```
Skill: docs-review-style, args: "artifacts/<doc-title-slug>/modules/ --local"
```

Checks against Red Hat Supplementary Style Guide and IBM Style Guide rules.

#### Pass 2: Vale linting

```
Skill: lint-with-vale, args: "artifacts/<doc-title-slug>/modules/"
```

Runs Vale with the project's `.vale.ini` configuration.

#### Pass 3: Modular docs compliance

```
Skill: docs-review-modular-docs, args: "artifacts/<doc-title-slug>/modules/"
```

Checks modular docs structure: anchors, content type attributes, abstract roles, file naming, assembly structure.

### 2. Apply RHIVOS-specific checks

After the three passes complete, run additional RHIVOS-specific validations on each module:

#### a. Product attribute usage

Scan for hardcoded product names that should use attributes:

| Find | Replace with |
|------|-------------|
| `RHIVOS` (standalone, not in attribute definition) | `{ProductShortName}` |
| `Red Hat In-Vehicle Operating System` | `{ProductName}` |
| `AutoSD` | `{ProductName}` |
| `Automotive Stream Distribution` | `{ProductName}` |

See [product-attributes.md](../../reference/product-attributes.md) for the full substitution map.

#### b. ASIL B content placement

Check that ASIL B and functional safety references appear only in:
- Admonition blocks (`[NOTE]`, `[WARNING]`, `[IMPORTANT]`, `[TIP]`, `[CAUTION]`)
- The module abstract (`[role="_abstract"]` paragraph)

Flag any ASIL B content found in regular body text.

#### c. Safety Guidance references

Check that references to the "RHIVOS Safety Guidance" document use italic formatting:
- Correct: `_RHIVOS Safety Guidance_`
- Incorrect: `RHIVOS Safety Guidance` (unformatted)

#### d. Reusable snippets

Check for content that should use a shared snippet:
- Functional safety disclaimer -> `include::snip_fusa-disclaimer.adoc[]`
- Standard ASIL B warning -> `include::snip_asil-b-warning.adoc[]`

Flag instances where the content is inlined rather than included.

### 3. Collect and deduplicate issues

Merge issues from all passes. Deduplicate by file + line number + rule. Assign each issue:

- **Severity**: error, warning, suggestion
- **Confidence**: 0-100 (how certain is the fix)
- **Source**: which pass detected it (style, vale, modular-docs, rhivos-specific)
- **Fix**: proposed fix text (if auto-fixable)

Filter by the `--threshold` value — only report issues at or above the threshold.

### 4. Write review artifacts

Write to `artifacts/<doc-title-slug>/quality-review/`:

#### `review-report.md`

```markdown
# Quality Review: <Doc Title>

Generated: <ISO 8601 timestamp>
Threshold: <N>
Mode: <report | fix>

## Summary

- Total issues: <N>
- Errors: <N>
- Warnings: <N>
- Suggestions: <N>
- Auto-fixable (>= 65% confidence): <N>

## Errors

### <filename>:<line>
- **Rule**: <rule name>
- **Source**: <pass name>
- **Issue**: <description>
- **Fix**: <proposed fix>
- **Confidence**: <N>%

## Warnings
...

## Suggestions
...
```

#### `issues.json`

Machine-readable issue list for tooling integration:

```json
[
  {
    "file": "<filename>",
    "line": <N>,
    "severity": "error",
    "rule": "<rule name>",
    "source": "<pass name>",
    "message": "<description>",
    "fix": "<proposed fix>",
    "confidence": <N>
  }
]
```

### 5. Apply auto-fixes (if --fix mode)

If `--fix` is set:

1. Sort issues by confidence (highest first)
2. Apply fixes with confidence >= 65% automatically
3. Write `auto-fixes-applied.md` listing what was changed
4. For issues with confidence < 65%, present each to the writer for interactive decision

### 6. Present results for review

Display the review summary:

```
Quality review of "<Doc Title>" (<N> modules):
  - <N> errors (must fix)
  - <N> warnings
  - <N> suggestions
  - <N> auto-fixable at >= 65% confidence

Errors:
  <file>:<line> — <description>
  ...

Top warnings:
  <file>:<line> — <description>
  ...

Full report: artifacts/<slug>/quality-review/review-report.md

Actions:
  approve — Accept review results, continue to next stage
  inspect <file> — Display a specific module
  fix-all — Apply all auto-fixes at or above confidence threshold
  fix <file> — Apply auto-fixes for a specific file only
  reject-fix <issue-id> — Exclude a specific issue from auto-fix
  set-threshold <N> — Change confidence threshold and re-filter
  abort — Stop and save progress

Your choice?
```

Repeat the review loop until the writer approves.

## Output

```
artifacts/<doc-title-slug>/
  quality-review/
    review-report.md
    issues.json
    auto-fixes-applied.md        # If --fix mode
```
