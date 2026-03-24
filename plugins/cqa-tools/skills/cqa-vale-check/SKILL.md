---
name: cqa-vale-check
description: Use when assessing CQA parameter P1 (Vale DITA check). Runs Vale with AsciiDocDITA rules (direct for repo scope, dita-tools:dita-validate-asciidoc for assembly/topic scope) and fixes violations to achieve 0 errors and 0 warnings.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Skill
---

# CQA P1: Vale DITA Check

## Parameter

**P1: Content passes Vale dita-tools:dita-validate-asciidoc check with no errors or warnings.**
Level: Required. Target: Score 4 (0 errors, 0 warnings).

## Step 1: Identify the docs repo

Ask the user for the path to their Red Hat modular documentation repository. This is the directory that contains `assemblies/`, `topics/` (or `modules/`), and `titles/` directories.

Store this as `DOCS_REPO` for all subsequent steps.

Vale must be installed (v3.x+). For assembly/topic scope, the `dita-tools:dita-validate-asciidoc` skill checks this automatically. For repo-wide scope, verify manually:

```bash
vale --version
```

If not installed, stop and tell the user to install Vale v3.x+. Do not install it for them.

## Step 2: Run Vale

Choose the approach based on scope.

### For repo-wide scope — direct Vale invocation

Run Vale directly against all AsciiDoc files in the repo. This catches every `.adoc` file, including orphan files not referenced by any assembly.

First, ensure a `.vale.ini` exists in the docs repo root with AsciiDocDITA rules. If missing, create one:

```ini
StylesPath = .vale/styles

MinAlertLevel = warning

Packages = https://github.com/jhradilek/asciidoctor-dita-vale/releases/latest/download/AsciiDocDITA.zip

[*.adoc]
BasedOnStyles = AsciiDocDITA
```

Then sync and run:

```bash
cd "$DOCS_REPO"
vale sync
find . -name '*.adoc' -not -type l | xargs vale
```

### For assembly scope — dita-validate-asciidoc

Invoke the `dita-tools:dita-validate-asciidoc` skill, which discovers all included files and runs Vale with content-type-aware ShortDescription filtering:

```
Skill: dita-tools:dita-validate-asciidoc, args: "$DOCS_REPO/assemblies/admin/assembly_installing.adoc"
```

### For single-topic scope — dita-validate-asciidoc

```
Skill: dita-tools:dita-validate-asciidoc, args: "$DOCS_REPO/topics/con-overview.adoc"
```

If the result is `0 errors, 0 warnings` (or no output for dita-validate-asciidoc) — score **4** and skip to Step 6.

## Step 3: Categorize warnings

Group the output by rule name. Common rules and their fixes:

| Rule | Meaning | Fix |
|------|---------|-----|
| `ContentType` | Missing `:_mod-docs-content-type:` | Add attribute as first line |
| `ShortDescription` | Missing `[role="_abstract"]` | Add abstract paragraph after title |
| `ConceptLink` | Link/xref in body of CONCEPT or ASSEMBLY | Move link to `.Additional resources` section. Rewrite surrounding text. |
| `TaskInclude` | `include::` inside `.Procedure` | Inline the included content directly into procedure steps |
| `RelatedLinks` | Non-link content inside `.Additional resources` | Ensure only links appear. Use proper `==` headings (not bold pseudo-headings) after `.Additional resources` to close the section. |
| `TaskStep` | Content after `.Procedure` is not ordered list | Convert `*` to `. ` |
| `TaskSection` | `==` subsections in a PROCEDURE | Remove subsection headings or split into multiple procedures |
| `TaskTitle` | Procedure title not gerund | Rename to gerund phrase |
| `BlockTitle` | Unsupported block title in wrong module type | Remove `.Procedure` from concepts, etc. |
| `ExampleBlock` | Nested `====` delimiters | Restructure to avoid nesting example blocks |

## Step 4: Fix by priority

Process fixes in this order to avoid cascading issues:

1. **ContentType + ShortDescription** — structural metadata (quick fixes)
2. **TaskStep + TaskSection + TaskTitle + BlockTitle** — structural violations
3. **ConceptLink** — move links to Additional resources (most labor-intensive)
4. **TaskInclude** — inline snippets into procedure steps
5. **RelatedLinks** — fix Additional resources sections

### ConceptLink fix pattern

For each flagged link/xref in a CONCEPT or ASSEMBLY file:

1. Read the file and locate the inline link
2. Move the link to an `[role="_additional-resources"]` `.Additional resources` section (create one at end of file if none exists)
3. Rewrite the surrounding sentence to make sense without the inline link
4. If the file has bold pseudo-headings (`**text**`), convert to `==` headings (CONCEPT files allow subsections)

### TaskInclude fix pattern

For each `include::` inside a `.Procedure`:

1. Read the included snippet file
2. Copy the snippet content directly into the procedure step
3. Remove the `include::` directive
4. Verify the inlined content renders correctly in context

### RelatedLinks fix pattern

The `.Additional resources` section ends only when Vale encounters a recognized heading (a line matching `== Title` or `.Title` format). Bold pseudo-headings (`**text**`) are NOT recognized as headings.

For each RelatedLinks warning:

1. Check if there is a bold pseudo-heading after `.Additional resources` — convert it to a `==` subsection heading
2. Ensure only links (`link:`, `xref:`, `<<...>>`, bare URLs) appear inside the `.Additional resources` section
3. If the `.Additional resources` is mid-file, ensure a proper `==` heading follows it to close the section

## Step 5: Verify

Re-run the same method used in Step 2. The result MUST be clean before scoring.

### For repo-wide scope — direct Vale invocation

```bash
cd "$DOCS_REPO"
find . -name '*.adoc' -not -type l | xargs vale
```

### For assembly or topic scope — dita-validate-asciidoc

```
Skill: dita-tools:dita-validate-asciidoc, args: "$ASSEMBLY_OR_TOPIC"
```

If warnings remain, return to Step 3. Do not score until the output is clean.

## Step 6: Score

| Score | Criteria |
|-------|----------|
| **4** | 0 errors, 0 warnings |
| **3** | 0 errors, fewer than 10 warnings |
| **2** | Errors present or 10+ warnings |
| **1** | Vale not configured or not run |

Record the score, the exact Vale output (file count, error count, warning count), and the Vale version used.

## Common mistakes

- Suppressing warnings in Vale config instead of fixing content
- Moving links to Additional resources but leaving a bold pseudo-heading after it (causes RelatedLinks warnings)
- Forgetting to convert bold pseudo-headings to `==` headings in concept files
- Running Vale on symlinked directories and getting inflated counts
