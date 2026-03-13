# JTBD Tools for Claude Code

## Dependencies

All skills work directly in Claude Code without additional dependencies — the LLM performs JTBD extraction using the methodology files included in the plugin.

**For AsciiDoc analysis (`jtbd-analyze-adoc`, `jtbd-analyze-topicmap`):**

The `asciidoctor-reducer` Ruby gem is required to flatten AsciiDoc includes before analysis:

```bash
gem install asciidoctor-reducer

# If Ruby/gem is not available:
brew install ruby   # macOS
```

**Optional: `jtbd` CLI tool**

The `jtbd` CLI is only needed if you want to run the pipeline programmatically outside Claude Code (e.g., `jtbd run-adoc`, `jtbd csv` for JSONL-to-CSV conversion). It is not required for interactive use with Claude Code.

```bash
# From the jtbd-pipeline repo (https://gitlab.cee.redhat.com/dobrenna/jtbd-pipeline)
python3 -m pip install -e .
```

## Usage

Once installed, invoke skills in Claude Code:

```bash
# Analyze a document
Skill: jtbd-tools:jtbd-analyze, args: "docs_raw/rhoai/deploying-models.md"

# Analyze an AsciiDoc book
Skill: jtbd-tools:jtbd-analyze-adoc, args: "path/to/master.adoc --variant self-managed"

# Analyze a topic map-based book (OpenShift docs)
Skill: jtbd-tools:jtbd-analyze-topicmap, args: "path/to/repo --book installing_gitops --distro openshift-gitops"

# Generate TOC from analysis results
Skill: jtbd-tools:jtbd-toc, args: "analysis/rhoai/deploying-models/"

# Compare current vs proposed structure
Skill: jtbd-tools:jtbd-compare, args: "docs_raw/rhoai/deploying-models.md"

# Generate consolidation report
Skill: jtbd-tools:jtbd-consolidate, args: "analysis/rhoai/deploying-models/"

# Harvest docs from a URL
Skill: jtbd-tools:jtbd-harvest, args: "https://docs.example.com/guide --project myproject"

# End-to-end workflow (all 4 steps in one command)
Skill: jtbd-tools:jtbd-workflow-topicmap, args: "path/to/repo --book installing_gitops --distro openshift-gitops"
Skill: jtbd-tools:jtbd-workflow-adoc, args: "path/to/master.adoc --variant self-managed"

# Batch processing
Skill: jtbd-tools:jtbd-workflow-topicmap, args: "path/to/repo --books-file books.txt --distro openshift-enterprise --batch"
Skill: jtbd-tools:jtbd-workflow-adoc, args: "--docs-file docs.txt --variant self-managed --batch"
```

## Typical Workflow

**Individual steps:**
```
1. jtbd-tools:jtbd-harvest       (or provide existing docs)
2. jtbd-tools:jtbd-analyze       (extract JTBD records)
3. jtbd-tools:jtbd-toc           (generate proposed TOC)
4. jtbd-tools:jtbd-compare       (side-by-side comparison)
5. jtbd-tools:jtbd-consolidate   (stakeholder report)
```

**One-command workflow (recommended for AsciiDoc repos):**
```
Skill: jtbd-tools:jtbd-workflow-topicmap, args: "path/to/repo --book book_name --distro distro-name"
Skill: jtbd-tools:jtbd-workflow-adoc, args: "path/to/master.adoc --variant self-managed"
```

These workflow skills run all 4 steps (analyze, TOC, compare, consolidate) automatically and produce all output artifacts in one invocation.

## Workflow Skills

The workflow skills (`jtbd-workflow-topicmap` and `jtbd-workflow-adoc`) combine all 4 analysis steps into a single command. Instead of invoking analyze, TOC, compare, and consolidate separately, one workflow invocation runs all steps in sequence and produces every output artifact.

Two separate workflow skills exist because the analysis entry points differ:

- **`jtbd-workflow-topicmap`** — For repos structured with `_topic_maps/_topic_map.yml` (e.g., openshift-docs, openshift-gitops). You specify a book directory name from the topic map.
- **`jtbd-workflow-adoc`** — For repos using `master.adoc` entry points (e.g., RHOAI, RHEL AI, Satellite). You point directly to a `master.adoc` file.

### `jtbd-workflow-topicmap`

```bash
# List available books in the topic map (filtered by distro)
Skill: jtbd-tools:jtbd-workflow-topicmap, args: "~/Documents/openshift-docs --list-books --distro openshift-gitops"

# Analyze a single book (all 4 steps)
Skill: jtbd-tools:jtbd-workflow-topicmap, args: "~/Documents/openshift-docs --book installing_gitops --distro openshift-gitops"

# With domain-specific research personas
Skill: jtbd-tools:jtbd-workflow-topicmap, args: "~/Documents/openshift-docs --book installing_gitops --distro openshift-gitops --research-file ~/my-project/research.yaml"

# Custom output directory
Skill: jtbd-tools:jtbd-workflow-topicmap, args: "~/Documents/openshift-docs --book installing_gitops --distro openshift-gitops --output analysis/gitops/installing/"
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `path` | Yes | Repo root containing `_topic_maps/_topic_map.yml` |
| `--book` | Yes (unless `--list-books` or `--batch`) | Book directory name (e.g., `installing_gitops`) |
| `--distro` | No | Filter books by distro (e.g., `openshift-gitops`, `openshift-enterprise`) |
| `--list-books` | No | Display available books in a table and exit |
| `--research-file` | No | Path to research config YAML (see [Custom Research Configs](#custom-research-configs)) |
| `--books-file` | No | Text file listing book directory names, one per line |
| `--batch` | No | Enable batch mode (requires `--books-file`) |
| `--batch-size` | No | Number of books per invocation (default 5, max 10) |
| `--output` | No | Output base directory. Default: `analysis/<distro>/<book>/` |
| `--skip-validation` | No | Skip grounding validation step |

### `jtbd-workflow-adoc`

```bash
# Analyze a single book (all 4 steps)
Skill: jtbd-tools:jtbd-workflow-adoc, args: "~/Documents/RHAI_DOCS/deploying-models/master.adoc --variant self-managed"

# With domain-specific research personas
Skill: jtbd-tools:jtbd-workflow-adoc, args: "~/Documents/RHAI_DOCS/deploying-models/master.adoc --variant self-managed --research-file ~/research/redhat-ai.yaml"

# Custom output directory
Skill: jtbd-tools:jtbd-workflow-adoc, args: "~/Documents/RHAI_DOCS/deploying-models/master.adoc --variant self-managed --output analysis/rhoai/deploying-models/"
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `path` | Yes (single-doc mode) | Path to assembly or `master.adoc` file |
| `--variant` | No | Conditional variant for `ifdef` resolution (`self-managed`, `cloud-service`) |
| `--research-file` | No | Path to research config YAML (see [Custom Research Configs](#custom-research-configs)) |
| `--docs-file` | No | Text file listing paths to `master.adoc` files, one per line |
| `--batch` | No | Enable batch mode (requires `--docs-file`) |
| `--batch-size` | No | Number of docs per invocation (default 5, max 10) |
| `--output` | No | Output directory |
| `--skip-validation` | No | Skip grounding validation step |

### What Each Step Produces

A single workflow invocation generates these files in the output directory:

| File | Step | Description |
|------|------|-------------|
| `<name>-jtbd.jsonl` | 1. Analyze | JTBD records (one JSON object per line) |
| `<name>-jtbd.csv` | 1. Analyze | Same records in CSV format |
| `<name>-*-reduced.adoc` | 1. Analyze | Flattened AsciiDoc with all includes resolved |
| `<name>-include-graph.json` | 1. Analyze | Module provenance map (assembly -> module -> type) |
| `<name>-toc-new_taxonomy.md` | 2. TOC | JTBD-oriented Table of Contents |
| `<name>-comparison.md` | 3. Compare | Side-by-side current vs proposed structure |
| `<name>-consolidation-report.md` | 4. Consolidate | Stakeholder-facing report with gap analysis |

### Batch Processing

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

Skill: jtbd-tools:jtbd-workflow-topicmap, args: "~/Documents/openshift-docs --books-file books.txt --distro openshift-gitops --batch --batch-size 5"
```

**Adoc batch example:**

```bash
# docs.txt (one master.adoc path per line):
# ~/Documents/RHAI_DOCS/deploying-models/master.adoc
# ~/Documents/RHAI_DOCS/creating-a-workbench/master.adoc
# ~/Documents/RHAI_DOCS/working-on-projects/master.adoc

Skill: jtbd-tools:jtbd-workflow-adoc, args: "--docs-file docs.txt --variant self-managed --batch --batch-size 5"
```

**Batch size limits:** Each invocation processes up to `--batch-size` items (default 5, max 10). If the file lists more items than the batch size, only the first N are processed and the remaining count is reported.

**Large batches (>10 items):** The plugin includes batch-runner scripts that split large lists into groups and invoke the Claude Code CLI for each group. They track progress in a state file and support `--resume` to continue after interruption.

```bash
# Process 30 books in groups of 5
python3 plugins/jtbd-tools/scripts/batch-runner-topicmap.py \
  --repo ~/Documents/openshift-docs \
  --books-file all-books.txt \
  --distro openshift-enterprise \
  --batch-size 5

# Resume after interruption
python3 plugins/jtbd-tools/scripts/batch-runner-topicmap.py \
  --repo ~/Documents/openshift-docs \
  --books-file all-books.txt \
  --distro openshift-enterprise \
  --batch-size 5 \
  --resume
```

## Custom Research Configs

By default, the workflow skills use generic persona detection — they infer roles from the documentation content (e.g., "cluster admin" language maps to a platform/admin role). To use domain-specific personas from UX research, provide a YAML config file with `--research-file`.

### Creating a Research Config

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

### Using It

```bash
# Topic map repo
Skill: jtbd-tools:jtbd-workflow-topicmap, args: "~/Documents/satellite-docs --book managing_hosts --research-file ~/research/satellite-research.yaml"

# AsciiDoc repo
Skill: jtbd-tools:jtbd-workflow-adoc, args: "~/Documents/satellite-docs/managing-hosts/master.adoc --research-file ~/research/satellite-research.yaml"
```

### What It Does

When `--research-file` is provided:

1. **Personas** replace generic role detection. The LLM uses your named personas (with archetypes, pain points, key quotes) instead of inferring roles.
2. **Schema extensions** add extra fields to every JTBD record and CSV column.
3. **Canonical jobs** guide the LLM to align extracted jobs with your research-backed job list.
4. **Strategic priorities** flag matching jobs with `strategic_priority: true`.
5. **Pain point patterns** detect text patterns in documentation and capture them in the `pain_points` field.
6. **UX Research sections** appear in comparison and consolidation reports when research fields are populated.

### YAML Sections Reference

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

## Plugin Structure

```
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
│   ├── jtbd-analyze/                  # each skill has only SKILL.md
│   ├── jtbd-analyze-adoc/
│   ├── jtbd-analyze-topicmap/
│   ├── jtbd-toc/
│   ├── jtbd-compare/
│   ├── jtbd-consolidate/
│   ├── jtbd-harvest/
│   ├── jtbd-workflow-adoc/
│   └── jtbd-workflow-topicmap/
├── scripts/
│   ├── batch-runner-adoc.py           # large batch helper for AsciiDoc workflows
│   └── batch-runner-topicmap.py       # large batch helper for topic map workflows
└── README.md
```

Shared files are maintained once in `reference/` and referenced from SKILL.md files using `Read @plugins/jtbd-tools/reference/<file>.md`.

## JTBD Framework

These skills implement the Outcome-Driven Innovation (ODI) variant of JTBD:

- **Job statement format:** "When [situation], I want to [motivation], so I can [outcome]"
- **Granularity levels:** main_job (10-15 per guide) > user_story (2-7 per job) > procedure
- **Job map stages:** Get Started, Plan, Configure, Deploy, Monitor, Troubleshoot, Reference, etc.
- **Grounding validation:** Each extracted record is verified against source content to prevent hallucination (can be skipped with `--skip-validation`)

## License

Internal use only.
