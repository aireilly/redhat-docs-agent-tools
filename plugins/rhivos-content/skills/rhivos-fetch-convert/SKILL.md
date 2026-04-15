---
name: rhivos-fetch-convert
description: >-
  Fetches upstream CentOS Automotive SIG Markdown files and converts them to
  Red Hat modular AsciiDoc. Handles Material for MkDocs extensions (tabs,
  admonitions, snippets, figure captions). Use this skill after rhivos-map-upstream
  has produced an approved upstream-mapping.yaml.
argument-hint: "<mapping-yaml> [--sig-docs-path <path>]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# Fetch and Convert Upstream Content

Converts upstream CentOS Automotive SIG Markdown files to Red Hat modular AsciiDoc using pandoc and a post-processing script.

## When to use

- After `rhivos-map-upstream` has produced an approved `upstream-mapping.yaml`
- When re-converting specific files after mapping changes
- When upstream content has been updated and modules need refreshing

## Inputs

Parse from `$ARGUMENTS`:

- **Mapping YAML path** (required, positional) — path to `upstream-mapping.yaml` from Skill A
- **`--sig-docs-path <path>`** (optional) — path to local sig-docs clone. Default: `~/Documents/git-repos/sig-docs`

## Prerequisites

Verify before proceeding (stop with clear error if missing):

```bash
command -v pandoc >/dev/null 2>&1 || echo "ERROR: pandoc not found. Install with: sudo dnf install pandoc"
pandoc --version | head -1
```

Pandoc 3.x is required. Warn if version is below 3.0.

## Process

### 1. Read the mapping

```bash
cat "<mapping-yaml-path>"
```

Parse the YAML. Filter to entries where `upstream_sources` is non-empty (skip `net_new: true` entries — those become stubs in the restructure stage).

Extract `doc_title` and compute the `<doc-title-slug>` (kebab-case lowercase).

### 2. Convert each upstream file

For each mapping entry with upstream sources marked `usage: adapt`:

#### a. Run pandoc base conversion

```bash
pandoc -f markdown -t asciidoc -o "<output-path>" "<sig-docs-path>/<upstream-path>"
```

#### b. Run md2adoc.py post-processor

The post-processing script handles Material for MkDocs extensions that pandoc does not convert correctly:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/md2adoc.py "<output-path>"
```

The script modifies the file in place. See [md2adoc.py conversions](#md2adoc-conversions) for what it handles.

#### c. Apply modular docs conventions

After post-processing, apply the semantic layer. Read the converted file and edit it to add:

1. **Module anchor** — Add `[id="<prefix>_<topic-name>_{context}"]` as the first line, where:
   - `<prefix>` is `con`, `proc`, or `ref` based on the mapping's `content_type`
   - `<topic-name>` is the downstream topic in kebab-case

2. **Content type attribute** — Add `:_mod-docs-content-type: <CONCEPT|PROCEDURE|REFERENCE>` after the title

3. **Abstract role** — Add `[role="_abstract"]` before the first body paragraph

4. **Product name substitution** — Replace upstream product references with attributes:
   - "AutoSD" -> `{ProductName}`
   - "Automotive Stream Distribution" -> `{ProductName}`
   - "CentOS Automotive SIG" -> Red Hat
   - "autosd" (case-sensitive, standalone word) -> `{ProductShortName}`

5. **File naming** — Rename the output file with the correct prefix:
   - CONCEPT -> `con_<topic-name>.adoc`
   - PROCEDURE -> `proc_<topic-name>.adoc`
   - REFERENCE -> `ref_<topic-name>.adoc`

See [product-attributes.md](../../reference/product-attributes.md) for the full substitution map.
See [modular-docs-rules.md](../../reference/modular-docs-rules.md) for structural conventions.

### 3. Handle multi-source merges

For mapping entries with multiple upstream sources (merge case):

1. Convert each source file individually (steps 2a-2b)
2. Concatenate relevant sections into a single output file
3. Mark each source's contribution with a comment:
   ```asciidoc
   // SOURCE: <upstream-path>
   ```
4. Apply modular docs conventions to the merged file (step 2c)
5. Flag the file for writer reconciliation in the conversion report

### 4. Generate conversion report

Write `artifacts/<doc-title-slug>/conversion-report.md`:

```markdown
# Conversion Report: <Doc Title>

Generated: <ISO 8601 timestamp>

## Summary

- Files converted: <N>
- Clean conversions: <N>
- Conversions with warnings: <N>
- Multi-source merges: <N>

## Warnings

### <filename>
- <warning description>

## Merges

### <filename>
- Merged from: <list of upstream paths>
- Reconciliation needed: <description>
```

### 5. Present results for review

Display the conversion summary and ask the writer to review:

```
Converted <N> modules for "<Doc Title>":
  - <X> clean conversions
  - <Y> with warnings (MkDocs extensions required manual handling)
  - <Z> multi-source merges (flagged for reconciliation)

<list warnings and merges>

Full report: artifacts/<slug>/conversion-report.md
Modules: artifacts/<slug>/modules/

Actions:
  approve — Accept conversions, continue to next stage
  inspect <file> — Display the full converted AsciiDoc file
  reconvert <file> — Re-run conversion for a specific file
  abort — Stop and save progress

Your choice?
```

## Output

```
artifacts/<doc-title-slug>/
  modules/
    con_<topic>.adoc
    proc_<topic>.adoc
    ref_<topic>.adoc
  conversion-report.md
```

## md2adoc conversions

The `md2adoc.py` script handles these Material for MkDocs extensions:

| MkDocs syntax | AsciiDoc output |
|---------------|-----------------|
| `=== "Tab title"` tabbed content | Labeled section: `.Tab title` followed by content |
| `!!! note "Title"` / `!!! warning` admonitions | `[NOTE]` / `[WARNING]` / `[TIP]` / `[IMPORTANT]` / `[CAUTION]` blocks |
| `--8<-- "path"` snippet inclusions | `include::<path>[]` directives |
| `/// figure-caption` | AsciiDoc image macro with `.Title` |
| Fenced code blocks with `title=` | AsciiDoc source blocks with `.Title` |
| Relative Markdown links `[text](file.md)` | AsciiDoc cross-references `xref:file.adoc[text]` |
| YAML frontmatter `title:` | AsciiDoc document title `= Title` |
| YAML frontmatter `description:` | `[role="_abstract"]` paragraph |
