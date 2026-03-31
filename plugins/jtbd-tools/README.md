# JTBD tools for Claude Code

!!! tip

    **These skills are designed for local AsciiDoc documentation repositories** — they read `master.adoc` files, `_topic_map.yml` structures, and modular doc assemblies directly from disk. They do not crawl or scrape websites. If you need to harvest and analyze documentation from HTML websites, use the [JTBD Agentic Orchestration](https://gitlab.cee.redhat.com/dobrenna/jtbd_agentic_orchestration) pipeline instead.

## Prerequisites

- Install [software dependencies](https://redhat-documentation.github.io/redhat-docs-agent-tools/install/#software-dependencies) (Ruby gems for AsciiDoc skills)

- The batch-runner scripts use only the Python standard library and need the `claude` CLI on `$PATH`

- All other skills work directly in Claude Code without additional dependencies

## Usage

```bash
# Analyze a markdown document
/jtbd-tools:jtbd-analyze docs_raw/rhoai/deploying-models.md

# Analyze an AsciiDoc book
/jtbd-tools:jtbd-analyze-adoc path/to/master.adoc --variant self-managed

# Analyze a topic map-based book (OpenShift docs)
/jtbd-tools:jtbd-analyze-topicmap path/to/repo --book installing_gitops --distro openshift-gitops

# Generate TOC from analysis results
/jtbd-tools:jtbd-toc analysis/rhoai/deploying-models/

# Compare current vs proposed structure
/jtbd-tools:jtbd-compare docs_raw/rhoai/deploying-models.md

# Generate consolidation report
/jtbd-tools:jtbd-consolidate analysis/rhoai/deploying-models/

# End-to-end workflow (all 4 steps in one command)
/jtbd-tools:jtbd-workflow-topicmap path/to/repo --book installing_gitops --distro openshift-gitops

/jtbd-tools:jtbd-workflow-adoc path/to/master.adoc --variant self-managed

# Batch processing
/jtbd-tools:jtbd-workflow-topicmap path/to/repo --books-file books.txt --distro openshift-enterprise --batch

/jtbd-tools:jtbd-workflow-adoc --docs-file docs.txt --variant self-managed --batch
```

## Typical workflow

**Individual steps:**

```bash
# extract JTBD records from markdown or AsciiDoc
/jtbd-tools:jtbd-analyze

# generate proposed TOC
/jtbd-tools:jtbd-toc

# side-by-side comparison
/jtbd-tools:jtbd-compare

# stakeholder report
/jtbd-tools:jtbd-consolidate
```

**One-command workflow (recommended for AsciiDoc repos):**
```bash
/jtbd-tools:jtbd-workflow-topicmap path/to/repo --book book_name --distro distro-name

/jtbd-tools:jtbd-workflow-adoc path/to/master.adoc --variant self-managed
```

These workflow skills run all 4 steps (analyze, TOC, compare, consolidate) automatically and produce all output artifacts in one invocation.

## Workflow skills

The workflow skills (`jtbd-workflow-topicmap` and `jtbd-workflow-adoc`) combine all 4 analysis steps into a single command. Instead of invoking analyze, TOC, compare, and consolidate separately, one workflow invocation runs all steps in sequence and produces every output artifact.

Two separate workflow skills exist because the analysis entry points differ:

- **`jtbd-workflow-topicmap`** — For repos structured with `_topic_maps/_topic_map.yml` (e.g., openshift-docs, openshift-gitops). You specify a book directory name from the topic map.
- **`jtbd-workflow-adoc`** — For repos using `master.adoc` entry points (e.g., RHOAI, RHEL AI, Satellite). You point directly to a `master.adoc` file.

### jtbd-workflow-topicmap

```bash
# List available books in the topic map (filtered by distro)
/jtbd-tools:jtbd-workflow-topicmap ~/Documents/openshift-docs --list-books --distro openshift-gitops

# Analyze a single book (all 4 steps)
/jtbd-tools:jtbd-workflow-topicmap ~/Documents/openshift-docs --book installing_gitops --distro openshift-gitops

# With domain-specific research personas
/jtbd-tools:jtbd-workflow-topicmap ~/Documents/openshift-docs --book installing_gitops --distro openshift-gitops --research-file ~/my-project/research.yaml

# Custom output directory
/jtbd-tools:jtbd-workflow-topicmap ~/Documents/openshift-docs --book installing_gitops --distro openshift-gitops --output analysis/gitops/installing/
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `path` | Yes | Repo root containing `_topic_maps/_topic_map.yml` |
| `--book` | Yes (unless `--list-books` or `--batch`) | Book directory name (e.g., `installing_gitops`) |
| `--distro` | No | Filter books by distro (e.g., `openshift-gitops`, `openshift-enterprise`) |
| `--list-books` | No | Display available books in a table and exit |
| `--research-file` | No | Path to research config YAML (see [Custom research configs](#custom-research-configs)) |
| `--books-file` | No | Text file listing book directory names, one per line |
| `--batch` | No | Enable batch mode (requires `--books-file`) |
| `--batch-size` | No | Number of books per invocation (default 5, max 10) |
| `--output` | No | Output base directory. Default: `analysis/<distro>/<book>/` |
| `--skip-validation` | No | Skip grounding validation step |

### jtbd-workflow-adoc

```bash
# Analyze a single book (all 4 steps)
/jtbd-tools:jtbd-workflow-adoc ~/Documents/RHAI_DOCS/deploying-models/master.adoc --variant self-managed

# With domain-specific research personas
/jtbd-tools:jtbd-workflow-adoc ~/Documents/RHAI_DOCS/deploying-models/master.adoc --variant self-managed --research-file ~/research/redhat-ai.yaml

# Custom output directory
/jtbd-tools:jtbd-workflow-adoc ~/Documents/RHAI_DOCS/deploying-models/master.adoc --variant self-managed --output analysis/rhoai/deploying-models/
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `path` | Yes (single-doc mode) | Path to assembly or `master.adoc` file |
| `--variant` | No | Conditional variant for `ifdef` resolution (`self-managed`, `cloud-service`) |
| `--research-file` | No | Path to research config YAML (see [Custom research configs](#custom-research-configs)) |
| `--docs-file` | No | Text file listing paths to `master.adoc` files, one per line |
| `--batch` | No | Enable batch mode (requires `--docs-file`) |
| `--batch-size` | No | Number of docs per invocation (default 5, max 10) |
| `--output` | No | Output directory |
| `--skip-validation` | No | Skip grounding validation step |

### What each step produces

A single workflow invocation generates these files in the output directory:

| File | Step | Description |
|------|------|-------------|
| `<name>-jtbd.jsonl` | 1. Analyze | JTBD records (one JSON object per line) |
| `<name>-jtbd.csv` | 1. Analyze | Same records in CSV format |
| `<name>-*-reduced.adoc` | 1. Analyze | Flattened AsciiDoc with all includes resolved |
| `<name>-include-graph.json` | 1. Analyze | Module provenance map (assembly -> module -> type) |
| `<name>-combined.adoc` | 1. Analyze | Concatenated reduced content (topicmap workflow only) |
| `<name>-topicmap.json` | 1. Analyze | Extracted topic map structure (topicmap workflow only) |
| `<name>-toc-new_taxonomy.md` | 2. TOC | JTBD-oriented Table of Contents |
| `<name>-comparison.md` | 3. Compare | Side-by-side current vs proposed structure |
| `<name>-consolidation-report.md` | 4. Consolidate | Stakeholder-facing report with gap analysis |

### Batch processing

Both workflow skills can process multiple books or documents in a single invocation. This is useful when you need to analyze an entire documentation set rather than one book at a time.

**How it works:**

1. Create a text file listing the items to process (one per line)
2. Pass it with `--books-file` (topicmap) or `--docs-file` (adoc) plus the `--batch` flag
3. The skill processes each item sequentially through all 4 steps
4. Progress is reported between items (e.g., "Completed 3/5")
5. A summary table is displayed at the end with record counts

**Topicmap batch example:**

```bash
# books.txt (one book directory name per line):
# installing_gitops
# configuring_gitops
# monitoring_gitops

/jtbd-tools:jtbd-workflow-topicmap ~/Documents/openshift-docs --books-file books.txt --distro openshift-gitops --batch --batch-size 5"
```

**adoc batch example:**

```bash
# docs.txt (one master.adoc path per line):
# ~/Documents/RHAI_DOCS/deploying-models/master.adoc
# ~/Documents/RHAI_DOCS/creating-a-workbench/master.adoc
# ~/Documents/RHAI_DOCS/working-on-projects/master.adoc

/jtbd-tools:jtbd-workflow-adoc --docs-file docs.txt --variant self-managed --batch -batch-size 5"
```

**Batch size limits:** Each invocation processes up to `--batch-size` items (default 5, max 10). If the file lists more items than the batch size, only the first N are processed and the remaining count is reported.

**Large batches (>10 items):** The plugin includes Python batch-runner scripts that split large lists into groups and invoke the Claude Code CLI for each group. They track progress in a state file and support `--resume` to continue after interruption. These scripts use only the Python standard library (no pip dependencies).

```bash
# Process 30 books in groups of 5
python3 plugins/jtbd-tools/scripts/batch-runner-topicmap.py \
  --repo ~/Documents/openshift-docs \
  --books-file all-books.txt \
  --distro openshift-enterprise \
  --batch-size 5

# Process multiple AsciiDoc docs
python3 plugins/jtbd-tools/scripts/batch-runner-adoc.py \
  --docs-file docs.txt \
  --variant self-managed \
  --batch-size 5

# Resume after interruption
python3 plugins/jtbd-tools/scripts/batch-runner-topicmap.py \
  --repo ~/Documents/openshift-docs \
  --books-file all-books.txt \
  --distro openshift-enterprise \
  --batch-size 5 \
  --resume
```

## Custom research configs

By default, the workflow skills use generic persona detection — they infer roles from the documentation content (e.g., "cluster admin" language maps to a platform/admin role). To use domain-specific personas from UX research, provide a YAML config file with `--research-file`.

### Creating a research config

Create a YAML file with your project's personas, schema extensions, and canonical jobs:

```yaml
# satellite-research.yaml
name: "Red Hat Satellite"
version: "1.0"
description: "Research overlay for Satellite documentation"

personas:
  - id: sysadmin
    name: "Sam the Systems Administrator"
    role: "Manages RHEL hosts, patching, and content lifecycle"
    archetype: "THE OPERATOR"
    loop: "outer"
    key_skills:
      - "Host management"
      - "Content views"
      - "Patching"
    pain_points:
      - "Complex content management workflows"
      - "Slow patching cycles across large fleets"
    key_quote: "I need to patch 500 hosts and I can't afford downtime."

  - id: contentmgr
    name: "Cora the Content Manager"
    role: "Curates and promotes content across lifecycle environments"
    archetype: "THE CURATOR"
    loop: "outer"
    key_skills:
      - "Content views"
      - "Lifecycle environments"
      - "Repository management"

# Additional fields added to every JTBD record (appear as CSV columns)
schema_extensions:
  - field: "compliance_framework"
    type: "enum"
    values: ["STIG", "CIS", "PCI-DSS", "HIPAA", "none"]
    description: "Applicable compliance framework"

  - field: "operational_impact"
    type: "enum"
    values: ["high", "medium", "low"]
    description: "Impact on production if this job fails"

# Reference jobs from research for alignment
canonical_jobs:
  setup:
    - "Register and provision hosts"
    - "Configure content sources"
  operations:
    - "Patch hosts across environments"
    - "Monitor compliance status"

# Jobs to flag with strategic_priority: true
strategic_priorities:
  - "Patch hosts across environments"
  - "Monitor compliance status"

# Text patterns to detect and capture as pain_points
pain_point_patterns:
  - pattern: "manual"
    maps_to: "Automation opportunity"
  - pattern: "drift"
    maps_to: "Compliance monitoring gap"
```

### Using it

```bash
# Topic map repo
/jtbd-tools:jtbd-workflow-topicmap ~/Documents/satellite-docs --book managing_hosts -research-file ~/research/satellite-research.yaml

# AsciiDoc repo
/jtbd-tools:jtbd-workflow-adoc ~/Documents/satellite-docs/managing-hosts/master.adoc--research-file ~/research/satellite-research.yaml
```

### What it does

When `--research-file` is provided:

1. **Personas** replace generic role detection. The LLM uses your named personas (with archetypes, pain points, key quotes) instead of inferring roles.
2. **Schema extensions** add extra fields to every JTBD record and CSV column.
3. **Canonical jobs** guide the LLM to align extracted jobs with your research-backed job list.
4. **Strategic priorities** flag matching jobs with `strategic_priority: true`.
5. **Pain point patterns** detect text patterns in documentation and capture them in the `pain_points` field.
6. **UX Research sections** appear in comparison and consolidation reports when research fields are populated.

### YAML sections reference

| Section | Required | Description |
|---------|----------|-------------|
| `name`, `version` | Yes | Config identity |
| `description` | No | Human-readable description |
| `personas` | No | Domain-specific persona definitions with optional archetype, loop, skills, pain points, and key quote |
| `schema_extensions` | No | Additional fields for JTBD records (type: `enum`, `boolean`, `array`, or `string`) |
| `canonical_jobs` | No | Reference jobs grouped by phase/category |
| `strategic_priorities` | No | Job statements to flag as high-priority |
| `pain_point_patterns` | No | Text pattern -> category mappings |

All sections except `name` and `version` are optional. A minimal config with just personas works fine.

## Plugin structure

```bash
jtbd-tools/
├── .claude-plugin/
│   └── plugin.json                    # plugin manifest (v1.1.0)
├── reference/                         # shared reference files (read via @-references)
│   ├── methodology.md                 # JTBD extraction methodology
│   ├── schema.md                      # JTBD record schema
│   ├── comparison-guide.md            # structure comparison guidelines
│   ├── consolidation-guide.md         # consolidation report guidelines
│   ├── toc-guidelines.md              # TOC generation guidelines
│   └── example-toc.md                 # example TOC output
├── skills/
│   ├── jtbd-analyze/                  # markdown analysis
│   ├── jtbd-analyze-adoc/             # AsciiDoc analysis (reduce + extract)
│   ├── jtbd-analyze-topicmap/         # topic map analysis (parse + reduce + extract)
│   ├── jtbd-toc/                      # TOC generation from JSONL records
│   ├── jtbd-compare/                  # current vs proposed comparison
│   ├── jtbd-consolidate/              # stakeholder consolidation report
│   ├── jtbd-workflow-adoc/            # end-to-end: analyze + TOC + compare + consolidate
│   └── jtbd-workflow-topicmap/        # end-to-end: analyze + TOC + compare + consolidate
├── scripts/
│   ├── batch-runner-adoc.py           # large batch helper for AsciiDoc workflows
│   └── batch-runner-topicmap.py       # large batch helper for topic map workflows
└── README.md
```

Shared files are maintained once in `reference/` and referenced from SKILL.md files using relative markdown links (e.g., `[methodology.md](../../reference/methodology.md)`).

## JTBD framework

These skills implement the Outcome-Driven Innovation (ODI) variant of JTBD:

- **Job statement format:** "When [situation], I want to [motivation], so I can [outcome]"
- **Granularity levels:** main_job (10-15 per guide) > user_story (2-7 per job) > procedure
- **Job map stages:** Get Started, Plan, Configure, Deploy, Monitor, Troubleshoot, Reference, etc.
- **Grounding validation:** Each extracted record is verified against source content to prevent hallucination (can be skipped with `--skip-validation`)
