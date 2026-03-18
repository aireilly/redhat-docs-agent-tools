---
name: jtbd-workflow-adoc
description: End-to-end JTBD workflow for AsciiDoc repos using master.adoc. Runs all 4 steps (analyze, TOC, comparison, consolidation) in one command. Supports batch processing of multiple documents.
argument-hint: <path-to-master.adoc> [--variant self-managed|cloud-service] [--research-file path] [--docs-file file] [--batch] [--batch-size N] [--output path]
context: fork
allowed-tools: Read, Glob, Grep, Write, Task, Bash
---

# JTBD Workflow — AsciiDoc Repos

End-to-end JTBD analysis workflow for AsciiDoc documentation repositories that use `master.adoc` entry points (e.g., RHOAI, RHEL AI, Satellite). Runs all 4 steps in sequence:

1. **Analyze** — Reduce master.adoc, build source map, extract JTBD records
2. **TOC** — Generate JTBD-oriented Table of Contents
3. **Compare** — Compare current vs proposed structure
4. **Consolidate** — Generate stakeholder-facing consolidation report

## Usage

```bash
# Single book
/jtbd-workflow-adoc path/to/master.adoc --variant self-managed

# With domain-specific research personas
/jtbd-workflow-adoc path/to/master.adoc --variant self-managed --research-file ~/my-project/research.yaml

# Custom output
/jtbd-workflow-adoc path/to/master.adoc --variant self-managed --output analysis/my-project/my-book/

# Batch
/jtbd-workflow-adoc --docs-file docs.txt --batch --batch-size 5
```

## Arguments

- **path** (required for single-doc mode): Path to assembly or `master.adoc`
- **--variant** (optional): Conditional variant for `ifdef` resolution (e.g., `self-managed`, `cloud-service`)
- **--research-file** (optional): Path to a research config YAML file with domain-specific personas, schema extensions, and canonical jobs. See [Research Config](#research-config) for the YAML format.
- **--docs-file** (optional): Text file with paths to master.adoc files, one per line
- **--batch** (optional): Enable batch mode (requires `--docs-file`)
- **--batch-size** (optional): Items per invocation, default 5, max 10
- **--output** (optional): Output directory

## Prerequisites

1. **asciidoctor-reducer** must be installed:
   ```bash
   gem install asciidoctor-reducer
   ```
   If Ruby/gem is not available:
   ```bash
   brew install ruby   # macOS
   ```

---

## Step 1: Analysis (AsciiDoc)

This step is identical to the `/jtbd-analyze-adoc` skill. Full details are in that skill; the key steps are summarized here.

### 1.1 Reduce (Flatten)

1. Verify `asciidoctor-reducer` is available:
   ```bash
   which asciidoctor-reducer
   ```
   If not found, tell the user to install it and stop.

2. Determine the document name from the path:
   - If path ends with `master.adoc`, use the parent directory name
   - Otherwise, use the filename without extension

3. Run reducer to flatten the assembly/book:
   ```bash
   asciidoctor-reducer <path-to-master.adoc> -o <output-dir>/<doc>-reduced.adoc
   ```
   If `--variant` is specified, set the attribute:
   ```bash
   asciidoctor-reducer -a <variant> <path-to-master.adoc> -o <output-dir>/<doc>-<variant>-reduced.adoc
   ```

4. Verify reduction: check output has no remaining `include::` directives (except in code blocks)

### 1.2 Source Map (Include Graph)

1. Read the *unreduced* assembly/master.adoc
2. Parse `include::` directives to build the full include tree
3. For each include, record: assembly, module path, module type, leveloffset
4. Map section titles from reduced output to original module files
5. Save as `<output-dir>/<doc>-include-graph.json`

#### Module Type Detection

Red Hat modular docs naming conventions:
- `con-*.adoc` = CONCEPT (explanatory content)
- `proc-*.adoc` = PROCEDURE (step-by-step instructions)
- `ref-*.adoc` = REFERENCE (tables, lists, specifications)
- `snip-*.adoc` = SNIPPET (reusable fragments)
- `assembly-*.adoc` = ASSEMBLY (collection of modules)
- Otherwise = UNKNOWN

### 1.3 JTBD Extraction

1. Read the reduced file
2. Parse into sections using AsciiDoc heading syntax:
   ```
   = Level 1 (Document/Book Title)
   == Level 2 (Chapter)
   === Level 3 (Section)
   ==== Level 4 (Subsection)
   ```
3. Skip boilerplate: Legal Notice, Providing feedback, Making open source more inclusive, Preface
4. Assess size for processing strategy:

| Reduced File Size | Strategy |
|-------------------|----------|
| < 500 lines | Single pass |
| >= 500 lines | Chunked subagent processing |

#### Research Config Integration

If `--research-file` is provided:
1. Read the YAML file at the specified path
2. Extract the personas, schema extensions, canonical jobs, strategic priorities, and pain point patterns
3. Generate a research overlay prompt section from the YAML content (see [Research Config](#research-config) for format)
4. Append this overlay to the methodology when constructing analysis prompts
5. When writing CSV output, include additional columns for any schema extension fields defined in the research config

If `--research-file` is NOT provided, use generic persona detection from `@plugins/jtbd-tools/reference/methodology.md`.

#### Single Pass Processing

Read entire reduced file, apply methodology from `@plugins/jtbd-tools/reference/methodology.md` (plus research overlay if provided), generate all records, write JSONL.

#### Chunked Processing

1. Group sections into chunks of 3-5 top-level sections (`==` headings)
2. Never split a chapter across chunks
3. For each chunk, launch a Task subagent:
   ```
   Task(subagent_type="general-purpose", prompt=chunk_analysis_prompt)
   ```
4. The chunk prompt must include:
   - The chunk content
   - The full methodology from `@plugins/jtbd-tools/reference/methodology.md` (read the reference file)
   - The schema from `@plugins/jtbd-tools/reference/schema.md` (read the reference file)
   - The research overlay (if `--research-file` was provided)
   - The document name and identifier
   - Instructions to output ONLY valid JSONL records
5. Collect results, merge, deduplicate, ensure parent_job consistency

### 1.4 Enrich Records

Match each record's `section` to the include graph, update `evidence` and `notes` with source module paths and types.

Example enriched record:
```json
{
  "evidence": "deploying-models-reduced.adoc -> Section 'Deploying models...', lines 45-120 [module: upstream-modules/proc-deploying-models.adoc, type: PROCEDURE]",
  "notes": "Source module: upstream-modules/proc-deploying-models.adoc (PROCEDURE). Assembly: assemblies/deploying-models.adoc"
}
```

### 1.5 Write Output

Save to `<output-dir>/`:
- `<doc>-jtbd.jsonl` — JTBD records (one JSON per line)
- `<doc>-jtbd.csv` — CSV version (array fields joined with `; `)
- `<doc>-include-graph.json` — Include graph with module types
- `<doc>-<variant>-reduced.adoc` (or `<doc>-reduced.adoc` if no variant)

#### Default Output Directory

If `--output` is not specified:
- `analysis/<book-name>-adoc/<doc>/`
- Where `<book-name>` is derived from the repository or parent directory name

---

## Step 2: TOC Generation

Read `@plugins/jtbd-tools/reference/toc-guidelines.md` and `@plugins/jtbd-tools/reference/example-toc.md` for the complete formatting rules.

### Process

1. Read `<doc>-jtbd.jsonl` from the output directory
2. Group records by main jobs and their user stories
3. Organize by workflow stages (Get Started -> Reference order)
4. Generate formatted markdown TOC following `@plugins/jtbd-tools/reference/toc-guidelines.md`
5. Write to `<output-dir>/<doc>-toc-new_taxonomy.md`

### Key Rules

- Jobs numbered sequentially (1, 2, 3...) in output order
- Clean titles: [Verb] + [Object/Outcome]
- Descriptive section headings (NOT stage labels like "DEFINE:", "EXECUTE:")
- 3-tier hierarchy: Job -> User Story -> Task
- Line references use `-> Lines X-Y: Section Title` format
- **AsciiDoc adaptation**: Source headings use `=`/`==`/`===` not `#`/`##`/`###`. Map `= Title` to document title, `== Chapter` to chapters.
- Include Quick Navigation, Workflow Coverage, and Document Statistics sections

---

## Step 3: Comparison

Read `@plugins/jtbd-tools/reference/comparison-guide.md` for the complete formatting rules.

### Process

1. Read the reduced `.adoc` file as the "source document"
2. Extract current structure from AsciiDoc headings (`=`, `==`, `===`)
3. Read `<doc>-jtbd.jsonl` for proposed structure
4. Generate side-by-side comparison per `@plugins/jtbd-tools/reference/comparison-guide.md`
5. Write to `<output-dir>/<doc>-comparison.md`

### AsciiDoc Adaptation

- `= Title` headings map to document/book title
- `== Chapter` headings map to chapters
- `=== Section` headings map to sections
- Extract the current TOC from these AsciiDoc headings, not markdown `#` headings

### Required Sections

1. Header & Metadata
2. Current Structure (Feature-Based)
3. Proposed JTBD-Based Structure
4. Key Differences
5. Hierarchy Levels
6. Example Consolidation (1-2 concrete examples)
7. Navigation Improvement Metrics
8. Workflow Coverage Comparison with gap recommendations
9. UX Research Alignment (when research fields present)

---

## Step 4: Consolidation Report

Read `@plugins/jtbd-tools/reference/consolidation-guide.md` for the complete formatting rules.

### Process

1. Read all inputs:
   - `<doc>-jtbd.jsonl` — JTBD records
   - `<doc>-toc-new_taxonomy.md` — TOC (for proposed structure)
   - `<doc>-comparison.md` — Comparison (for current structure context)
   - `<doc>-*-reduced.adoc` — Source document (reduced)
2. Generate consolidation report per `@plugins/jtbd-tools/reference/consolidation-guide.md`
3. Write to `<output-dir>/<doc>-consolidation-report.md`

### Required Sections (10 total, in order)

1. Header & Metadata
2. Executive Summary (What's Changing + Key Improvements)
3. Current Structure (Feature-Based) — extracted from reduced `.adoc` headings
4. Proposed JTBD-Based Structure (Quick Overview + Detailed Job Descriptions)
5. Key Differences (table + Job List Adjustments)
6. Consolidation Examples (2-3 before/after)
7. Content Gaps Identified (table with High/Medium/Low impact)
8. Navigation Improvement Summary (quantified metrics)
9. UX Research Alignment (only if research fields populated)
10. Document Statistics

---

## Batch Mode

### Usage

```bash
/jtbd-workflow-adoc --docs-file docs.txt --batch --batch-size 5
```

`docs.txt` lists paths to master.adoc files, one per line:
```
~/Documents/RHAI_DOCS/deploying-models/master.adoc
~/Documents/RHAI_DOCS/creating-a-workbench/master.adoc
~/Documents/RHAI_DOCS/working-on-projects/master.adoc
```

You can also include `--variant` and `--research` flags which apply to all documents:

```bash
/jtbd-workflow-adoc --docs-file docs.txt --variant self-managed --research redhat-ai --batch --batch-size 5
```

### Behavior

1. Read the docs file and count items
2. `--batch-size N` controls how many to process (default 5, max 10)
3. If file has more items than batch-size, process only the first N and report remaining
4. Display the batch list and confirm with user before proceeding
5. Process each document sequentially (full 4-step workflow)
6. Report progress between documents (e.g., "Completed 2/5: deploying-models")
7. Produce summary table at end:

```markdown
| # | Document | Records | Main Jobs | Status |
|---|----------|---------|-----------|--------|
| 1 | deploying-models | 52 | 14 | Done |
| 2 | creating-a-workbench | 28 | 8 | Done |
| 3 | working-on-projects | 35 | 11 | Done |
```

### Large Batches (>10 items)

For processing more than 10 documents, use the Python batch-runner script:

```bash
python3 plugins/jtbd-workflow-adoc/scripts/batch-runner.py \
  --docs-file docs.txt \
  --variant self-managed \
  --research redhat-ai \
  --batch-size 5
```

This splits items into groups and invokes `claude` for each group, handling failures and providing resume capability.

---

## Output Summary

For each document processed, the following files are produced:

| File | Step | Description |
|------|------|-------------|
| `<doc>-jtbd.jsonl` | 1 | JTBD records |
| `<doc>-jtbd.csv` | 1 | CSV version of records |
| `<doc>-*-reduced.adoc` | 1 | Reduced (flattened) AsciiDoc |
| `<doc>-include-graph.json` | 1 | Include graph with module types |
| `<doc>-toc-new_taxonomy.md` | 2 | JTBD-oriented TOC |
| `<doc>-comparison.md` | 3 | Current vs proposed comparison |
| `<doc>-consolidation-report.md` | 4 | Stakeholder consolidation report |

---

## Quality Checklist

### Step 1: Analysis
- [ ] Reduced file has all includes resolved (no remaining `include::` directives)
- [ ] Include graph JSON has correct module types (CONCEPT, PROCEDURE, REFERENCE, SNIPPET)
- [ ] Evidence fields include module file references and line numbers
- [ ] Conditional content matches the specified variant
- [ ] Records follow "When X, I want Y, so I can Z" format
- [ ] ~10-15 main_jobs per document
- [ ] All user_story records have parent_job set
- [ ] JSONL is valid (one JSON object per line)

### Step 2: TOC
- [ ] Job numbers are sequential (1, 2, 3...)
- [ ] Clean job titles: [Verb] + [Object]
- [ ] Descriptive section headings (NOT stage labels)
- [ ] 3-tier hierarchy: Job -> User Story -> Task
- [ ] Quick Navigation section included
- [ ] Workflow Coverage with gap indicators

### Step 3: Comparison
- [ ] Current structure extracted from reduced `.adoc` headings
- [ ] Proposed structure uses proper granularity levels
- [ ] Navigation improvements quantified
- [ ] Workflow coverage comparison with indicators

### Step 4: Consolidation
- [ ] All 10 required sections present in order
- [ ] Job list adjustments explain any merges
- [ ] 2-3 consolidation examples with before/after
- [ ] Gap table with impact ratings (High/Medium/Low)
- [ ] Navigation metrics quantified with percentages
- [ ] Topic type tags on all approaches

### Cross-Step
- [ ] Job counts consistent across TOC, comparison, and consolidation
- [ ] Source references match between artifacts
- [ ] All files written to the correct output directory

## Research Config

The `--research-file` flag lets you provide a YAML file with domain-specific personas, schema extensions, and canonical jobs. Without it, the skill uses generic persona detection from the documentation content.

### YAML Format

```yaml
name: "My Project"
version: "1.0"
description: "Research overlay for My Project documentation"

# Domain-specific personas (override generic role detection)
personas:
  - id: sysadmin
    name: "Sam the Systems Administrator"
    role: "Manages hosts, patching, and content lifecycle"
    archetype: "THE OPERATOR"          # optional
    loop: "outer"                       # inner | outer | cross-cutting (optional)
    key_skills:                         # optional
      - "Host management"
      - "Content views"
      - "Patching"
    pain_points:                        # optional
      - "Complex content management workflows"
      - "Slow patching cycles across large fleets"
    key_quote: "I need to patch 500 hosts and I can't afford downtime."  # optional

  - id: deveng
    name: "Dana the Developer"
    role: "Builds and deploys applications on the platform"
    archetype: "THE BUILDER"
    loop: "inner"
    key_skills:
      - "Application development"
      - "CI/CD pipelines"
    pain_points:
      - "Disconnected from operational environment constraints"

# Additional fields added to every JTBD record
schema_extensions:
  - field: "compliance_framework"
    type: "enum"
    values: ["STIG", "CIS", "PCI-DSS", "HIPAA", "none"]
    description: "Applicable compliance framework for this job"

  - field: "operational_impact"
    type: "enum"
    values: ["high", "medium", "low"]
    description: "Impact on production operations if this job fails"

  - field: "teams_involved"
    type: "array"
    description: "Teams that collaborate on this job"

# Canonical jobs from research for matching/validation
canonical_jobs:
  setup:
    - "Register and provision hosts"
    - "Configure content sources"
  operations:
    - "Patch hosts across environments"
    - "Monitor compliance status"
  lifecycle:
    - "Promote content across environments"

# Jobs flagged as strategic priorities
strategic_priorities:
  - "Patch hosts across environments"
  - "Monitor compliance status"

# Pain point patterns to detect in documentation
pain_point_patterns:
  - pattern: "manual"
    maps_to: "Automation opportunity"
  - pattern: "drift"
    maps_to: "Compliance monitoring gap"
  - pattern: "complex"
    maps_to: "Simplification opportunity"
```

### How It Works

When `--research-file` is provided, the skill:

1. **Reads the YAML** and extracts all sections
2. **Replaces generic persona detection** with the named personas from the config. The LLM uses these personas (with their archetypes, pain points, key quotes) instead of inferring roles from the documentation.
3. **Adds schema extension fields** to every JTBD record. These appear as additional columns in the CSV output.
4. **References canonical jobs** during extraction to align extracted jobs with known research-backed jobs.
5. **Flags strategic priorities** with `strategic_priority: true` on matching records.
6. **Detects pain point patterns** in the documentation text and captures them in the `pain_points` field.

### Sections Reference

| Section | Required | Purpose |
|---------|----------|---------|
| `name`, `version` | Yes | Config identity |
| `description` | No | Human-readable description |
| `personas` | No | Domain-specific persona definitions |
| `schema_extensions` | No | Additional fields for JTBD records |
| `canonical_jobs` | No | Reference jobs from research for alignment |
| `strategic_priorities` | No | Jobs to flag as high-priority |
| `pain_point_patterns` | No | Text patterns to detect and capture |

All sections except `name` and `version` are optional. You can provide just personas, just schema extensions, or any combination.

---

## Methodology Reference

This skill references shared methodology and guideline files in the reference/ directory:
- `@plugins/jtbd-tools/reference/methodology.md` — JTBD extraction rules (from `/jtbd-analyze-adoc`)
- `@plugins/jtbd-tools/reference/schema.md` — Record schema (from `/jtbd-analyze-adoc`)
- `@plugins/jtbd-tools/reference/toc-guidelines.md` — TOC formatting rules (from `/jtbd-toc`)
- `@plugins/jtbd-tools/reference/example-toc.md` — Example TOC output (from `/jtbd-toc`)
- `@plugins/jtbd-tools/reference/comparison-guide.md` — Comparison rules (from `/jtbd-compare`)
- `@plugins/jtbd-tools/reference/consolidation-guide.md` — Consolidation rules (from `/jtbd-consolidate`)
