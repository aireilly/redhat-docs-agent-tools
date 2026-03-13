---
name: jtbd-analyze-adoc
description: Extract Jobs-To-Be-Done records from AsciiDoc documentation repos. Use when analyzing modular AsciiDoc docs (assemblies, includes, conditionals) for user goals and JTBD-oriented restructuring. Handles reduction, source mapping, and chunked analysis.
argument-hint: <path-to-assembly-or-master.adoc> [--variant self-managed|cloud-service] [--research config-name] [--output path]
context: fork
allowed-tools: Read, Glob, Grep, Write, Task, Bash
---

# JTBD AsciiDoc Analysis Skill

Extract Jobs-To-Be-Done records from AsciiDoc documentation repositories, specifically Red Hat modular docs that use assemblies, modules, includes, attributes, and conditionals.

## Usage

```bash
# Analyze a book (master.adoc)
/jtbd-analyze-adoc ~/Documents/RHAI_DOCUMENTATION/openshift-ai-documentation/deploying-models/master.adoc --variant self-managed

# Analyze an assembly
/jtbd-analyze-adoc ~/Documents/RHAI_DOCUMENTATION/openshift-ai-documentation/assemblies/deploying-models.adoc --variant self-managed

# With research config
/jtbd-analyze-adoc path/to/master.adoc --variant self-managed --research redhat-ai

# With custom output
/jtbd-analyze-adoc path/to/master.adoc --variant self-managed --output analysis/rhoai-adoc/deploying-models/
```

## Arguments

- **path** (required): Path to an AsciiDoc assembly file or book `master.adoc`
- **--variant** (recommended): `self-managed` or `cloud-service` to resolve conditionals
- **--research** (optional): Research config name for domain-specific personas and extensions
- **--output** (optional): Custom output directory. Defaults to `analysis/<book-name>-adoc/<doc>/`
- **--skip-validation** (optional): Skip the grounding validation step (Step 9). Validation runs by default.

## Prerequisites

1. **asciidoctor-reducer** must be installed:
   ```bash
   gem install asciidoctor-reducer
   ```
   If Ruby/gem is not available:
   ```bash
   brew install ruby   # macOS
   ```

2. **jtbd CLI** must be installed:
   ```bash
   pip install -e .
   ```

## What This Skill Does

### Phase 1: Reduce (Flatten)

1. **Checks prerequisites**: Verifies `asciidoctor-reducer` is available
2. **Runs reducer**: Calls `asciidoctor-reducer` to flatten the assembly/book into a single file, resolving all `include::` directives
3. **Applies variant**: If `--variant` is specified, sets the conditional attribute so `ifdef::self-managed[]` / `ifdef::cloud-service[]` blocks are resolved
4. **Saves reduced file**: Writes to output directory as `<book>-<variant>-reduced.adoc`

### Phase 2: Source Map

5. **Parses include graph**: Reads the *unreduced* assembly/master.adoc to build the full include tree
6. **Maps sections to modules**: Correlates section titles in the reduced output back to their original module files
7. **Saves include graph**: Writes `<doc>-include-graph.json` for Phase 2 refactoring use

### Phase 3: JTBD Analysis

8. **Parses sections**: Parses reduced AsciiDoc into Section objects using AsciiDoc heading syntax (`=`, `==`, `===`, etc.)
9. **Assesses document size**: Determines single-pass vs chunked processing strategy
10. **Extracts JTBD records**: Applies the methodology from `@plugins/jtbd-tools/reference/methodology.md`
11. **Enriches with module info**: Annotates evidence and notes with source module paths and types
12. **Validates against source**: Re-reads cited source lines and runs grounding checks on each record (unless `--skip-validation`)
13. **Writes output**: Saves JSONL + CSV + include graph

## Processing Strategy

### Document Size Assessment

| Reduced File Size | Strategy |
|-------------------|----------|
| < 500 lines | Single pass processing |
| >= 500 lines | Chunked subagent processing |

### Single Pass Processing

For small reduced files:
1. Read the entire reduced AsciiDoc
2. Apply JTBD extraction methodology (from `@plugins/jtbd-tools/reference/methodology.md`)
3. Generate all records in one pass
4. Write to JSONL file

### Chunked Processing

For large reduced files:
1. Parse into sections by AsciiDoc headings
2. Skip boilerplate: Legal Notice, Providing feedback, Making open source more inclusive, Preface
3. Group sections into chunks of 3-5 sections
4. For each chunk, launch a Task subagent:
   ```
   Task(subagent_type="general-purpose", prompt=chunk_analysis_prompt)
   ```
5. Aggregate results from all chunks
6. Write merged records to JSONL

### Phase 4: Grounding Validation

Unless `--skip-validation` is passed, run the grounding validation described in `@plugins/jtbd-tools/reference/methodology.md` Step 9:

1. For each JTBD record, parse the `evidence` field to extract the source file, section heading, and line range
2. Re-read the cited lines from the reduced file (±20 lines context window)
3. Verify the `section` field matches an actual heading in the reduced file (mechanical check)
4. Run the grounding check prompt to verify job statement, persona, and desired outcomes are supported by the source
5. Set `validation_status` and `validation_flags` on each record
6. Print a validation summary to the user

Processing strategy:
- ≤ 20 records: single validation prompt with all records and their source excerpts
- \> 20 records: chunked validation with 5-10 records per subagent

## AsciiDoc-Specific Considerations

### Module Types

Red Hat modular docs follow naming conventions:
- `con-*.adoc` = CONCEPT modules (explanatory content)
- `proc-*.adoc` = PROCEDURE modules (step-by-step instructions)
- `ref-*.adoc` = REFERENCE modules (tables, lists, specifications)
- `snip-*.adoc` = SNIPPET modules (reusable fragments)
- `assembly-*.adoc` or `assembly_*.adoc` = ASSEMBLY files (collections of modules)

### Heading Syntax

AsciiDoc uses `=` for headings (unlike markdown's `#`):
```
= Level 1 (Document Title)
== Level 2 (Chapter)
=== Level 3 (Section)
==== Level 4 (Subsection)
```

### Record Enrichment

Each JTBD record's evidence and notes fields are enriched with AsciiDoc-specific provenance:

```json
{
  "evidence": "deploying-models-reduced.adoc -> Section 'Deploying models...', lines 45-120 [module: upstream-modules/proc-deploying-models.adoc, type: PROCEDURE]",
  "notes": "Source module: upstream-modules/proc-deploying-models.adoc (PROCEDURE). Assembly: assemblies/deploying-models.adoc"
}
```

### Conditional Content

When `--variant` is specified:
- `ifdef::self-managed[]` blocks are included (or excluded for cloud-service)
- `ifdef::cloud-service[]` blocks are included (or excluded for self-managed)
- Shared content (outside conditionals) is always included

## CLI Integration

This skill wraps two CLI commands:

```bash
# Step 1: Reduce only
jtbd reduce path/to/master.adoc --variant self-managed --output analysis/rhoai-adoc/deploying-models/

# Step 2: Full pipeline (reduce + analyze)
jtbd run-adoc path/to/master.adoc --variant self-managed --project rhoai-adoc --doc deploying-models
```

The skill prefers using the CLI commands when available, falling back to direct Python calls if needed.

## Workflow

```bash
# Step 1: Reduce and analyze
/jtbd-analyze-adoc path/to/deploying-models/master.adoc --variant self-managed

# Step 2: Review results
cat analysis/rhoai-adoc/deploying-models/deploying-models-jtbd.jsonl

# Step 3: Check include graph
cat analysis/rhoai-adoc/deploying-models/deploying-models-include-graph.json

# Step 4: Generate TOC from records
/jtbd-toc analysis/rhoai-adoc/deploying-models/

# Step 5: Compare with current structure
/jtbd-compare --project rhoai-adoc --doc deploying-models
```

## Output Location

Default:
```
analysis/<book-name>-adoc/<doc>/<doc>-jtbd.jsonl
analysis/<book-name>-adoc/<doc>/<doc>-jtbd.csv
analysis/<book-name>-adoc/<doc>/<doc>-toc-new_taxonomy.md
analysis/<book-name>-adoc/<doc>/<doc>-include-graph.json
analysis/<book-name>-adoc/<doc>/<doc>-<variant>-reduced.adoc
```

## Quality Checklist

Same as `/jtbd-analyze`, plus:

- [ ] Reduced file has all includes resolved (no remaining `include::` directives)
- [ ] Include graph JSON has correct module types
- [ ] Evidence fields include module file references
- [ ] Conditional content matches the specified variant
- [ ] Section titles from reduced file map correctly to original modules
- [ ] Grounding validation passed (or flagged records reviewed and accepted)
- [ ] No `no_evidence` records (evidence citations resolve to real content)

## Methodology Reference

The complete JTBD extraction methodology is shared with `/jtbd-analyze`:
- See `@plugins/jtbd-tools/reference/methodology.md` for extraction rules
- See `@plugins/jtbd-tools/reference/schema.md` for record schema
