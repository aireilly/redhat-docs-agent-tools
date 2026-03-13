---
name: jtbd-workflow-topicmap
description: End-to-end JTBD workflow for topic map-based repos. Runs all 4 steps (analyze, TOC, comparison, consolidation) in one command. Supports batch processing of multiple books.
argument-hint: <path-to-repo> --book <dir-name> [--distro <distro>] [--list-books] [--research-file path] [--books-file file] [--batch] [--batch-size N] [--output path]
context: fork
allowed-tools: Read, Glob, Grep, Write, Task, Bash
---

# JTBD Workflow — Topic Map Repos

End-to-end JTBD analysis workflow for OpenShift documentation repositories that use `_topic_maps/_topic_map.yml`. Runs all 4 steps in sequence:

1. **Analyze** — Parse topic map, reduce assemblies, extract JTBD records
2. **TOC** — Generate JTBD-oriented Table of Contents
3. **Compare** — Compare current vs proposed structure
4. **Consolidate** — Generate stakeholder-facing consolidation report

## Usage

```bash
# Single book
/jtbd-workflow-topicmap path/to/repo --book installing_gitops --distro openshift-gitops

# With domain-specific research personas
/jtbd-workflow-topicmap path/to/repo --book installing_gitops --distro openshift-gitops --research-file ~/my-project/research.yaml

# List books
/jtbd-workflow-topicmap path/to/repo --list-books --distro openshift-gitops

# Batch (max 10 per invocation)
/jtbd-workflow-topicmap path/to/repo --books-file books.txt --distro openshift-enterprise --batch --batch-size 5
```

## Arguments

- **path** (required): Repo root containing `_topic_maps/_topic_map.yml`
- **--book** (required unless `--list-books` or `--batch`): Book directory name (e.g., `installing_gitops`)
- **--distro** (optional): Filter books by distro (e.g., `openshift-gitops`, `openshift-enterprise`)
- **--list-books** (optional): List all books in the topic map and exit
- **--research-file** (optional): Path to a research config YAML file with domain-specific personas, schema extensions, and canonical jobs. See [Research Config](#research-config) for the YAML format.
- **--books-file** (optional): Text file with book dir names, one per line
- **--batch** (optional): Enable batch mode (requires `--books-file`)
- **--batch-size** (optional): Items per invocation, default 5, max 10
- **--output** (optional): Output base directory. Default: `analysis/<distro>/` or `analysis/topicmap/`

## Prerequisites

1. **asciidoctor-reducer** must be installed:
   ```bash
   gem install asciidoctor-reducer
   ```
   If Ruby/gem is not available:
   ```bash
   brew install ruby   # macOS
   ```

2. The target repo must have `_topic_maps/_topic_map.yml`

---

## Step 1: Analysis (Topic Map)

This step is identical to the `/jtbd-analyze-topicmap` skill. Full details are in that skill; the key steps are summarized here.

### 1.1 Parse the Topic Map

1. Find `_topic_maps/_topic_map.yml` in the repo root
2. Read the file and split on `---` document separators (multi-document YAML)
3. Parse each YAML document as a book entry with: `Name`, `Dir`, `Distros`, `Topics`
4. If `--distro` is specified, filter to books whose `Distros` field contains that distro
5. If `--list-books`, display a table of books and stop

#### Topic Map YAML Format

```yaml
---
Name: Installing GitOps          # Book display name
Dir: installing_gitops            # Directory containing assemblies
Distros: openshift-gitops         # Comma-separated distro list
Topics:                           # Ordered list of topics
- Name: Preparing to install      # Topic display name
  File: preparing-gitops-install  # Assembly filename (without .adoc)
- Name: Nested section
  Dir: sub_directory
  Topics:
  - Name: Sub-topic
    File: sub-topic-file
```

#### Parsing Rules

- Each `---` document = one book
- `Distros` can be a single string or comma-separated
- Topics nest recursively with their own `Dir` and `Topics`
- Topic entry with `Name` + `File` = leaf topic (assembly)
- Topic entry with `Name` + `Topics` = section grouping (no file)
- File paths resolve as: `<repo>/<book-Dir>/<File>.adoc` or `<repo>/<book-Dir>/<sub-Dir>/<File>.adoc`

#### Parsing Implementation

1. Read the file with the Read tool
2. Split content on lines that are exactly `---` (YAML document separator)
3. For each document block, extract `Name:`, `Dir:`, `Distros:`, `Topics:` fields
4. Walk topics tree recursively to collect all `File` references with resolved paths

### 1.2 Resolve Assembly Files

1. Look up the book whose `Dir` matches `--book`
2. Walk `Topics` recursively to collect all `File` entries
3. Resolve full paths: `<repo>/<book-Dir>/<File>.adoc`
4. Verify each assembly exists
5. Report assemblies found

### 1.3 Reduce Each Assembly

**CRITICAL: Working Directory** — `asciidoctor-reducer` must run from the **book directory**, not the repo root:

```bash
cd <repo>/<book-Dir> && asciidoctor-reducer <file>.adoc -o <output-dir>/<file>-reduced.adoc
```

For nested topics with a subdirectory:
```bash
cd <repo>/<book-Dir> && asciidoctor-reducer <sub-Dir>/<file>.adoc -o <output-dir>/<file>-reduced.adoc
```

Verify reduction: check output file has no remaining `include::` directives.

### 1.4 Concatenate Reduced Files

1. Create a single concatenated document
2. For each reduced assembly (in topic map order), insert `= <Topic Name>` heading and append content
3. Save as `<output-dir>/<book>-combined.adoc`
4. Report total line count

### 1.5 Build Source Map (Include Graph)

1. Parse `include::` directives from unreduced assemblies
2. Record assembly, module path, module type (con-, proc-, ref-, snip-), leveloffset
3. Map section titles from reduced output to original module files
4. Save as `<output-dir>/<book>-include-graph.json`

#### Module Type Detection

- `con-*.adoc` = CONCEPT
- `proc-*.adoc` = PROCEDURE
- `ref-*.adoc` = REFERENCE
- `snip-*.adoc` = SNIPPET
- Otherwise = UNKNOWN

### 1.6 JTBD Extraction

1. Read the combined file
2. Parse into sections using AsciiDoc headings (`=`, `==`, `===`, `====`)
3. Skip boilerplate: Legal Notice, Providing feedback, Making open source more inclusive, Preface
4. Assess size for processing strategy:

| Combined File Size | Strategy |
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

If `--research-file` is NOT provided, use generic persona detection from `methodology.md`.

#### Single Pass Processing

Read entire combined file, apply methodology from `methodology.md` (plus research overlay if provided), generate all records, write JSONL.

#### Chunked Processing

1. Group sections into chunks of 3-5 top-level sections (`==` headings)
2. Never split an assembly across chunks
3. For each chunk, launch a Task subagent:
   ```
   Task(subagent_type="general-purpose", prompt=chunk_analysis_prompt)
   ```
4. The chunk prompt must include:
   - The chunk content
   - The full methodology from `methodology.md` (read the file in this skill directory)
   - The schema from `schema.md` (read the file in this skill directory)
   - The research overlay (if `--research-file` was provided)
   - The book name and doc identifier
   - Instructions to output ONLY valid JSONL records
5. Collect results, merge, deduplicate, ensure parent_job consistency

### 1.7 Enrich Records with Module Provenance

Match each record's `section` to the include graph, update `evidence` and `notes` with module paths and types.

### 1.8 Write Output

Save to `<output-dir>/`:
- `<book>-jtbd.jsonl` — JTBD records (one JSON per line)
- `<book>-jtbd.csv` — CSV version (array fields joined with `; `)
- `<book>-include-graph.json` — Include graph
- `<book>-topicmap.json` — Extracted topic map structure
- Individual `<file>-reduced.adoc` files
- `<book>-combined.adoc` — Concatenated reduced content

#### Default Output Directory

- With `--distro`: `analysis/<distro>/<book>/`
- Without `--distro`: `analysis/topicmap/<book>/`

---

## Step 2: TOC Generation

Read `toc-guidelines.md` and `example-toc.md` from this skill directory for the complete formatting rules.

### Process

1. Read `<book>-jtbd.jsonl` from the output directory
2. Group records by main jobs and their user stories
3. Organize by workflow stages (Get Started -> Reference order)
4. Generate formatted markdown TOC following `toc-guidelines.md`
5. Write to `<output-dir>/<book>-toc-new_taxonomy.md`

### Key Rules

- Jobs numbered sequentially (1, 2, 3...) in output order
- Clean titles: [Verb] + [Object/Outcome]
- Descriptive section headings (NOT stage labels like "DEFINE:", "EXECUTE:")
- 3-tier hierarchy: Job -> User Story -> Task
- Line references use `-> Lines X-Y: Section Title` format
- **AsciiDoc adaptation**: Source headings use `=`/`==`/`===` not `#`/`##`/`###`. Map `= Title` to chapters.
- Include Quick Navigation, Workflow Coverage, and Document Statistics sections

---

## Step 3: Comparison

Read `comparison-guide.md` from this skill directory for the complete formatting rules.

### Process

1. Read the combined `.adoc` file (`<book>-combined.adoc`) as the "source document"
2. Extract current structure from AsciiDoc headings (`=`, `==`, `===`)
3. Read `<book>-jtbd.jsonl` for proposed structure
4. Generate side-by-side comparison per `comparison-guide.md`
5. Write to `<output-dir>/<book>-comparison.md`

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

Read `consolidation-guide.md` from this skill directory for the complete formatting rules.

### Process

1. Read all inputs:
   - `<book>-jtbd.jsonl` — JTBD records
   - `<book>-toc-new_taxonomy.md` — TOC (for proposed structure)
   - `<book>-comparison.md` — Comparison (for current structure context)
   - `<book>-combined.adoc` — Source document
2. Generate consolidation report per `consolidation-guide.md`
3. Write to `<output-dir>/<book>-consolidation-report.md`

### Required Sections (10 total, in order)

1. Header & Metadata
2. Executive Summary (What's Changing + Key Improvements)
3. Current Structure (Feature-Based) — extracted from combined `.adoc` headings
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
/jtbd-workflow-topicmap path/to/repo --books-file books.txt --distro openshift-enterprise --batch --batch-size 5
```

`books.txt` lists book directory names, one per line:
```
installing_gitops
configuring_gitops
monitoring_gitops
```

### Behavior

1. Read the books file and count items
2. `--batch-size N` controls how many to process (default 5, max 10)
3. If file has more items than batch-size, process only the first N and report remaining
4. Display the batch list and confirm with user before proceeding
5. Process each book sequentially (full 4-step workflow)
6. Report progress between books (e.g., "Completed 2/5: installing_gitops")
7. Produce summary table at end:

```markdown
| # | Book | Records | Main Jobs | Status |
|---|------|---------|-----------|--------|
| 1 | installing_gitops | 45 | 12 | Done |
| 2 | configuring_gitops | 38 | 10 | Done |
| 3 | monitoring_gitops | 22 | 8 | Done |
```

### Large Batches (>10 items)

For processing more than 10 books, use the Python batch-runner script:

```bash
python plugins/jtbd-workflow-topicmap/scripts/batch-runner.py \
  --repo ~/Documents/openshift-docs \
  --books-file books.txt \
  --distro openshift-enterprise \
  --batch-size 5
```

This splits items into groups and invokes `claude` for each group, handling failures and providing resume capability.

---

## Output Summary

For each book processed, the following files are produced:

| File | Step | Description |
|------|------|-------------|
| `<book>-jtbd.jsonl` | 1 | JTBD records |
| `<book>-jtbd.csv` | 1 | CSV version of records |
| `<book>-combined.adoc` | 1 | Concatenated reduced content |
| `<book>-include-graph.json` | 1 | Include graph with module types |
| `<book>-topicmap.json` | 1 | Topic map structure |
| `*-reduced.adoc` | 1 | Individual reduced assemblies |
| `<book>-toc-new_taxonomy.md` | 2 | JTBD-oriented TOC |
| `<book>-comparison.md` | 3 | Current vs proposed comparison |
| `<book>-consolidation-report.md` | 4 | Stakeholder consolidation report |

---

## Quality Checklist

### Step 1: Analysis
- [ ] Topic map parsed correctly (all books listed, distro filter works)
- [ ] All assembly files resolved and found on disk
- [ ] Reduced files have all includes resolved (no remaining `include::` directives)
- [ ] Combined file has correct `= Topic Name` headings between assemblies
- [ ] Include graph JSON has correct module types (CONCEPT, PROCEDURE, REFERENCE, SNIPPET)
- [ ] Records follow "When X, I want Y, so I can Z" format
- [ ] ~10-15 main_jobs per book
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
- [ ] Current structure extracted from combined `.adoc` headings
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

This skill embeds all methodology and guidelines as supporting files:
- `methodology.md` — JTBD extraction rules (from `/jtbd-analyze-adoc`)
- `schema.md` — Record schema (from `/jtbd-analyze-adoc`)
- `toc-guidelines.md` — TOC formatting rules (from `/jtbd-toc`)
- `example-toc.md` — Example TOC output (from `/jtbd-toc`)
- `comparison-guide.md` — Comparison rules (from `/jtbd-compare`)
- `consolidation-guide.md` — Consolidation rules (from `/jtbd-consolidate`)
