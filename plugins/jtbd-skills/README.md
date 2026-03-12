# JTBD Skills for Claude Code

A Claude Code plugin marketplace for Jobs-To-Be-Done (JTBD) documentation analysis. Extract user goals from technical documentation, generate JTBD-oriented TOCs, compare current vs proposed structures, and produce stakeholder-facing consolidation reports.

## Plugins

| Plugin | Description |
|--------|-------------|
| `jtbd-analyze` | Extract JTBD records from markdown documentation |
| `jtbd-analyze-adoc` | Extract JTBD records from AsciiDoc documentation repos (modular docs with assemblies, includes, conditionals) |
| `jtbd-analyze-topicmap` | Extract JTBD records from OpenShift docs repos that use `_topic_map.yml` for book structure |
| `jtbd-toc` | Generate a JTBD-oriented Table of Contents from JTBD records |
| `jtbd-compare` | Compare current feature-based structure with proposed JTBD structure |
| `jtbd-consolidate` | Generate stakeholder-facing consolidation reports with gap analysis and navigation improvements |
| `jtbd-harvest` | Harvest technical documentation from a URL for analysis |
| `jtbd-workflow-topicmap` | End-to-end workflow for topic map repos: analyze, TOC, compare, consolidate in one command. Supports batch processing. |
| `jtbd-workflow-adoc` | End-to-end workflow for AsciiDoc repos: analyze, TOC, compare, consolidate in one command. Supports batch processing. |

## Installation

### Option A: Plugin marketplace (recommended)

Add the marketplace and install plugins directly in Claude Code:

```
/plugin marketplace add git@gitlab.cee.redhat.com:dobrenna/jtbd-skills.git
/plugin install jtbd-analyze@jtbd-skills
/plugin install jtbd-toc@jtbd-skills
```

> **Note:** Use the SSH URL (`git@gitlab.cee.redhat.com:...`). The HTTPS URL may fail with SSL certificate errors on internal GitLab instances.

Or install all plugins:

```
/plugin install jtbd-analyze@jtbd-skills
/plugin install jtbd-analyze-adoc@jtbd-skills
/plugin install jtbd-analyze-topicmap@jtbd-skills
/plugin install jtbd-toc@jtbd-skills
/plugin install jtbd-compare@jtbd-skills
/plugin install jtbd-consolidate@jtbd-skills
/plugin install jtbd-harvest@jtbd-skills
/plugin install jtbd-workflow-topicmap@jtbd-skills
/plugin install jtbd-workflow-adoc@jtbd-skills
```

### Option B: Symlink into your project

Clone the repo and symlink plugin skills into your project's `.claude/skills/` directory:

```bash
git clone git@gitlab.cee.redhat.com:dobrenna/jtbd-skills.git ~/jtbd-skills

mkdir -p your-project/.claude/skills

# Symlink all plugins
for plugin in ~/jtbd-skills/plugins/jtbd-*; do
  name=$(basename "$plugin")
  ln -s "$plugin/skills/$name" "your-project/.claude/skills/$name"
done
```

### Option C: Copy into your project

```bash
git clone git@gitlab.cee.redhat.com:dobrenna/jtbd-skills.git

# Copy specific plugins
cp -r jtbd-skills/plugins/jtbd-analyze/skills/jtbd-analyze your-project/.claude/skills/
cp -r jtbd-skills/plugins/jtbd-toc/skills/jtbd-toc your-project/.claude/skills/
```

### Auto-install for your team

Add to your project's `.claude/settings.json` so team members are prompted to install the marketplace:

```json
{
  "extraKnownMarketplaces": {
    "jtbd-skills": {
      "source": {
        "source": "url",
        "url": "git@gitlab.cee.redhat.com:dobrenna/jtbd-skills.git"
      }
    }
  }
}
```

## Dependencies

All plugins work directly in Claude Code without additional dependencies — the LLM performs JTBD extraction using the methodology files included in each plugin.

**For AsciiDoc analysis (`jtbd-analyze-adoc`, `jtbd-analyze-topicmap`):**

The `asciidoctor-reducer` Ruby gem is required to flatten AsciiDoc includes before analysis:

```bash
gem install asciidoctor-reducer

# If Ruby/gem is not available:
brew install ruby   # macOS
```

**Optional: `jtbd` CLI tool**

The `jtbd` CLI is only needed if you want to run the pipeline programmatically outside Claude Code (e.g., `jtbd run-adoc`, `jtbd csv` for JSONL-to-CSV conversion). It is not required for interactive use with Claude Code plugins.

```bash
# From the jtbd-pipeline repo (https://gitlab.cee.redhat.com/dobrenna/jtbd-pipeline)
pip install -e .
```

## Usage

Once installed, invoke skills in Claude Code with `/skill-name`:

```bash
# Analyze a document
/jtbd-analyze docs_raw/rhoai/deploying-models.md

# Analyze an AsciiDoc book
/jtbd-analyze-adoc path/to/master.adoc --variant self-managed

# Analyze a topic map-based book (OpenShift docs)
/jtbd-analyze-topicmap path/to/repo --book installing_gitops --distro openshift-gitops

# Generate TOC from analysis results
/jtbd-toc analysis/rhoai/deploying-models/

# Compare current vs proposed structure
/jtbd-compare docs_raw/rhoai/deploying-models.md

# Generate consolidation report
/jtbd-consolidate analysis/rhoai/deploying-models/

# Harvest docs from a URL
/jtbd-harvest https://docs.example.com/guide --project myproject

# End-to-end workflow (all 4 steps in one command)
/jtbd-workflow-topicmap path/to/repo --book installing_gitops --distro openshift-gitops
/jtbd-workflow-adoc path/to/master.adoc --variant self-managed

# Batch processing
/jtbd-workflow-topicmap path/to/repo --books-file books.txt --distro openshift-enterprise --batch
/jtbd-workflow-adoc --docs-file docs.txt --variant self-managed --batch
```

## Typical Workflow

**Individual steps:**
```
1. /jtbd-harvest     (or provide existing docs)
2. /jtbd-analyze     (extract JTBD records)
3. /jtbd-toc         (generate proposed TOC)
4. /jtbd-compare     (side-by-side comparison)
5. /jtbd-consolidate (stakeholder report)
```

**One-command workflow (recommended for AsciiDoc repos):**
```
/jtbd-workflow-topicmap path/to/repo --book book_name --distro distro-name
/jtbd-workflow-adoc path/to/master.adoc --variant self-managed
```

These workflow skills run all 4 steps (analyze, TOC, compare, consolidate) automatically and produce all output artifacts in one invocation.

## Workflow Skills

The workflow plugins (`jtbd-workflow-topicmap` and `jtbd-workflow-adoc`) combine all 4 analysis steps into a single command. Instead of invoking `/jtbd-analyze`, `/jtbd-toc`, `/jtbd-compare`, and `/jtbd-consolidate` separately, one workflow invocation runs all steps in sequence and produces every output artifact.

Two separate workflow skills exist because the analysis entry points differ:

- **`jtbd-workflow-topicmap`** — For repos structured with `_topic_maps/_topic_map.yml` (e.g., openshift-docs, openshift-gitops). You specify a book directory name from the topic map.
- **`jtbd-workflow-adoc`** — For repos using `master.adoc` entry points (e.g., RHOAI, RHEL AI, Satellite). You point directly to a `master.adoc` file.

### `jtbd-workflow-topicmap`

```bash
# List available books in the topic map (filtered by distro)
/jtbd-workflow-topicmap ~/Documents/openshift-docs --list-books --distro openshift-gitops

# Analyze a single book (all 4 steps)
/jtbd-workflow-topicmap ~/Documents/openshift-docs --book installing_gitops --distro openshift-gitops

# With domain-specific research personas
/jtbd-workflow-topicmap ~/Documents/openshift-docs --book installing_gitops --distro openshift-gitops --research-file ~/my-project/research.yaml

# Custom output directory
/jtbd-workflow-topicmap ~/Documents/openshift-docs --book installing_gitops --distro openshift-gitops --output analysis/gitops/installing/
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

### `jtbd-workflow-adoc`

```bash
# Analyze a single book (all 4 steps)
/jtbd-workflow-adoc ~/Documents/RHAI_DOCS/deploying-models/master.adoc --variant self-managed

# With domain-specific research personas
/jtbd-workflow-adoc ~/Documents/RHAI_DOCS/deploying-models/master.adoc --variant self-managed --research-file ~/research/redhat-ai.yaml

# Custom output directory
/jtbd-workflow-adoc ~/Documents/RHAI_DOCS/deploying-models/master.adoc --variant self-managed --output analysis/rhoai/deploying-models/
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

/jtbd-workflow-topicmap ~/Documents/openshift-docs --books-file books.txt --distro openshift-gitops --batch --batch-size 5
```

**Adoc batch example:**

```bash
# docs.txt (one master.adoc path per line):
# ~/Documents/RHAI_DOCS/deploying-models/master.adoc
# ~/Documents/RHAI_DOCS/creating-a-workbench/master.adoc
# ~/Documents/RHAI_DOCS/working-on-projects/master.adoc

/jtbd-workflow-adoc --docs-file docs.txt --variant self-managed --batch --batch-size 5
```

**Batch size limits:** Each invocation processes up to `--batch-size` items (default 5, max 10). If the file lists more items than the batch size, only the first N are processed and the remaining count is reported.

**Large batches (>10 items):** Each workflow plugin includes a `scripts/batch-runner.py` Python script that splits large lists into groups and invokes the Claude Code CLI for each group. It tracks progress in a state file and supports `--resume` to continue after interruption.

```bash
# Process 30 books in groups of 5
python plugins/jtbd-workflow-topicmap/scripts/batch-runner.py \
  --repo ~/Documents/openshift-docs \
  --books-file all-books.txt \
  --distro openshift-enterprise \
  --batch-size 5

# Resume after interruption
python plugins/jtbd-workflow-topicmap/scripts/batch-runner.py \
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
/jtbd-workflow-topicmap ~/Documents/satellite-docs --book managing_hosts --research-file ~/research/satellite-research.yaml

# AsciiDoc repo
/jtbd-workflow-adoc ~/Documents/satellite-docs/managing-hosts/master.adoc --research-file ~/research/satellite-research.yaml
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

## Repository Structure

```
jtbd-skills/
├── .claude-plugin/
│   └── marketplace.json            # marketplace catalog
├── plugins/
│   ├── jtbd-analyze/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json         # plugin manifest
│   │   └── skills/
│   │       └── jtbd-analyze/
│   │           ├── SKILL.md
│   │           ├── methodology.md
│   │           └── schema.md
│   ├── jtbd-analyze-adoc/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       └── jtbd-analyze-adoc/
│   │           ├── SKILL.md
│   │           ├── methodology.md  # duplicated for independence
│   │           └── schema.md       # duplicated for independence
│   ├── jtbd-analyze-topicmap/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       └── jtbd-analyze-topicmap/
│   │           ├── SKILL.md
│   │           ├── methodology.md  # duplicated for independence
│   │           └── schema.md       # duplicated for independence
│   ├── jtbd-toc/
│   │   └── ...
│   ├── jtbd-compare/
│   │   └── ...
│   ├── jtbd-consolidate/
│   │   └── ...
│   ├── jtbd-harvest/
│   │   └── ...
│   ├── jtbd-workflow-topicmap/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── scripts/
│   │   │   └── batch-runner.py     # Python helper for large batches
│   │   └── skills/
│   │       └── jtbd-workflow-topicmap/
│   │           ├── SKILL.md
│   │           ├── methodology.md  # duplicated for independence
│   │           ├── schema.md
│   │           ├── toc-guidelines.md
│   │           ├── example-toc.md
│   │           ├── comparison-guide.md
│   │           └── consolidation-guide.md
│   └── jtbd-workflow-adoc/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── scripts/
│       │   └── batch-runner.py     # Python helper for large batches
│       └── skills/
│           └── jtbd-workflow-adoc/
│               ├── SKILL.md
│               ├── methodology.md  # duplicated for independence
│               ├── schema.md
│               ├── toc-guidelines.md
│               ├── example-toc.md
│               ├── comparison-guide.md
│               └── consolidation-guide.md
└── README.md
```

Each plugin is self-contained — no cross-plugin dependencies. Shared files (methodology.md, schema.md) are duplicated where needed so plugins can be installed independently.

## JTBD Framework

These skills implement the Outcome-Driven Innovation (ODI) variant of JTBD:

- **Job statement format:** "When [situation], I want to [motivation], so I can [outcome]"
- **Granularity levels:** main_job (10-15 per guide) > user_story (2-7 per job) > procedure
- **Job map stages:** Get Started, Plan, Configure, Deploy, Monitor, Troubleshoot, Reference, etc.
- **Personas:** Data Scientist, AI Engineer, ML Ops Engineer, Platform Engineer

## License

Internal use only.
