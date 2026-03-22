---
name: cqa-vale-check
description: Use when assessing CQA parameter P1 (Vale DITA check). Verifies prerequisites, sets up asciidoctor-dita-vale styles, runs Vale against all content, and fixes violations to achieve 0 errors and 0 warnings.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# CQA P1: Vale DITA Check

## Parameter

**P1: Content passes Vale asciidoctor-dita-vale check with no errors or warnings.**
Level: Required. Target: Score 4 (0 errors, 0 warnings).

## Step 1: Verify prerequisites

### 1a. Vale CLI

Check that `vale` is installed and is v3.x or later:

```bash
vale --version
```

If not installed, stop and tell the user to install Vale v3.x+. Do not install it for them.

### 1b. Identify the docs repo

Ask the user for the path to their Red Hat modular documentation repository. This is the directory that contains `assemblies/`, `topics/` (or `modules/`), and `titles/` directories.

Store this as `DOCS_REPO` for all subsequent steps.

### 1c. asciidoctor-dita-vale styles

Check if the styles directory exists as a sibling to the docs repo:

```bash
ls "$(dirname "$DOCS_REPO")/asciidoctor-dita-vale/styles"
```

If the directory does not exist, clone it automatically:

```bash
git clone https://github.com/jhradilek/asciidoctor-dita-vale "$(dirname "$DOCS_REPO")/asciidoctor-dita-vale"
```

Verify the clone succeeded:

```bash
ls "$(dirname "$DOCS_REPO")/asciidoctor-dita-vale/styles/AsciiDocDITA"
```

### 1d. `.vale.ini`

Check if `.vale.ini` exists in the docs repo root:

```bash
ls "$DOCS_REPO/.vale.ini"
```

If `.vale.ini` does not exist, generate one. The `StylesPath` must point to the sibling `asciidoctor-dita-vale/styles` directory. The config must exclude snippet, common, and symlinked directories to prevent double-counting:

```ini
StylesPath = ../asciidoctor-dita-vale/styles
MinAlertLevel = warning

[*.adoc]
BasedOnStyles = AsciiDocDITA

# Exclude snippet and common files (include fragments, not standalone modules)
[**/snippets/*.adoc]
BasedOnStyles =

[**/common/*.adoc]
BasedOnStyles =

[snippets/*.adoc]
BasedOnStyles =

[common/*.adoc]
BasedOnStyles =

# Exclude symlinked directories inside assemblies/ and titles/ to prevent
# double-counting when running vale on assemblies/ topics/ titles/ together.
# Each assembly and title directory symlinks to topics/, snippets/, common/, images/.
[assemblies/**/topics/**/*.adoc]
BasedOnStyles =

[assemblies/**/snippets/**/*.adoc]
BasedOnStyles =

[titles/**/topics/**/*.adoc]
BasedOnStyles =

[titles/**/assemblies/**/*.adoc]
BasedOnStyles =

[titles/**/snippets/**/*.adoc]
BasedOnStyles =

[titles/**/common/**/*.adoc]
BasedOnStyles =
```

If `.vale.ini` already exists, verify it has:
- `StylesPath` pointing to a valid directory containing `AsciiDocDITA/`
- `BasedOnStyles = AsciiDocDITA` under `[*.adoc]`
- Exclusion patterns for snippets, common, and symlinked directories

If any of these are missing, warn the user and offer to fix the config.

## Step 2: Run Vale

Run Vale from the docs repo root against assemblies, topics (or modules), and master files:

```bash
cd "$DOCS_REPO"
# Adjust directory names to match your repo structure (topics/ or modules/)
vale assemblies/ topics/ titles/administration_guide/master.adoc titles/user_guide/master.adoc
```

If the result is `0 errors, 0 warnings` — score **4** and skip to Step 6.

## Step 3: Categorize warnings

Group Vale output by rule name. Common rules and their fixes:

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

Run Vale again. The result MUST be `0 errors, 0 warnings` before scoring.

```bash
cd "$DOCS_REPO"
vale assemblies/ topics/ titles/administration_guide/master.adoc titles/user_guide/master.adoc
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

- Suppressing warnings in `.vale.ini` instead of fixing content
- Moving links to Additional resources but leaving a bold pseudo-heading after it (causes RelatedLinks warnings)
- Forgetting to convert bold pseudo-headings to `==` headings in concept files
- Running Vale on symlinked directories and getting inflated counts
- Not verifying `.vale.ini` exclusion patterns before running Vale
