---
name: jtbd-analyze-topicmap
description: Extract Jobs-To-Be-Done records from OpenShift docs repos that use _topic_map.yml for structure instead of master.adoc. Parses the topic map to discover books and assemblies, reduces each assembly, and runs JTBD analysis.
argument-hint: <path-to-repo> --book <dir-name> [--distro <distro>] [--list-books] [--output path]
context: fork
allowed-tools: Read, Glob, Grep, Write, Task, Bash
---

# JTBD Topic Map Analysis Skill

Extract Jobs-To-Be-Done records from OpenShift documentation repositories that use `_topic_maps/_topic_map.yml` to define book structure, rather than a `master.adoc` entry point.

## Usage

```bash
# List available books for a distro
/jtbd-analyze-topicmap path/to/repo --list-books --distro openshift-gitops

# Analyze a specific book
/jtbd-analyze-topicmap path/to/repo --book installing_gitops

# Analyze with distro filter
/jtbd-analyze-topicmap path/to/repo --book installing_gitops --distro openshift-gitops

# Custom output location
/jtbd-analyze-topicmap path/to/repo --book installing_gitops --output analysis/gitops/installing_gitops/
```

## Arguments

- **path** (required): Path to the repo root containing `_topic_maps/_topic_map.yml`
- **--book** (required unless `--list-books`): Book directory name (e.g., `installing_gitops`)
- **--distro** (optional): Filter topic map entries by distro (e.g., `openshift-gitops`)
- **--list-books** (optional): List all books in the topic map and exit
- **--output** (optional): Custom output directory. Defaults to `analysis/<distro>/<book>/` (or `analysis/topicmap/<book>/` if no distro specified)
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

2. The target repo must have `_topic_maps/_topic_map.yml`

## What This Skill Does

### Step 1: Parse the Topic Map

1. Find `_topic_maps/_topic_map.yml` in the repo root
2. Read the file and split on `---` document separators (multi-document YAML)
3. Parse each YAML document as a book entry
4. Each book has: `Name`, `Dir`, `Distros`, `Topics`
5. If `--distro` is specified, filter to books whose `Distros` field contains that distro
6. If `--list-books`, display the book list in a table and stop

#### Topic Map YAML Format

The `_topic_map.yml` uses multi-document YAML (documents separated by `---`). Each document represents one book:

```yaml
---
Name: Installing GitOps          # Book display name
Dir: installing_gitops            # Directory containing assemblies
Distros: openshift-gitops         # Comma-separated distro list
Topics:                           # Ordered list of topics
- Name: Preparing to install      # Topic display name
  File: preparing-gitops-install  # Assembly filename (without .adoc)
- Name: Nested section            # Sub-topic group
  Dir: sub_directory              # Subdirectory within book dir
  Topics:                         # Nested topics
  - Name: Sub-topic
    File: sub-topic-file
```

#### Parsing Rules

- Each `---` document = one book
- `Distros` can be a single string or comma-separated (e.g., `openshift-enterprise,openshift-origin`)
- Topics can nest recursively with their own `Dir` and `Topics`
- A topic entry may have ONLY `Name` + `Topics` (section grouping, no file) or `Name` + `File` (leaf topic pointing to an assembly)
- File paths are resolved as: `<repo-root>/<book-Dir>/<File>.adoc` or `<repo-root>/<book-Dir>/<sub-Dir>/<File>.adoc` for nested topics

#### Parsing Implementation

Use the Bash tool to read the YAML file, then parse it in your response. Since Claude Code doesn't have a YAML library, follow this approach:

1. Read the file with the Read tool
2. Split content on lines that are exactly `---` (YAML document separator)
3. For each document block, extract:
   - `Name:` line -> book name
   - `Dir:` line -> book directory
   - `Distros:` line -> distro filter string
   - `Topics:` block -> list of topic entries
4. For each topic entry, extract `Name:`, `File:`, and optional nested `Dir:` + `Topics:`
5. Walk the topics tree recursively to collect all `File` references with their resolved paths

### Step 2: Resolve Assembly Files for the Book

1. Look up the book whose `Dir` field matches `--book`
2. Walk the `Topics` list recursively (topics can have nested sub-topics with their own `Dir`)
3. For each topic entry with a `File` field, resolve the full path:
   - Top-level topic: `<repo-root>/<book-Dir>/<File>.adoc`
   - Nested topic with `Dir`: `<repo-root>/<book-Dir>/<nested-Dir>/<File>.adoc`
4. Verify each assembly file exists using Glob or Read
5. Report the assemblies found (count, names) to the user

### Step 3: Reduce Each Assembly

**CRITICAL: Working Directory**

`asciidoctor-reducer` must run from the **book directory** (e.g., `installing_gitops/`), NOT the repo root. This is because each book directory contains symlinks that the reducer needs to resolve includes:

```
installing_gitops/
├── _attributes -> ../_attributes/
├── modules -> ../modules/
├── images -> ../images/
├── snippets -> ../snippets/
└── *.adoc
```

The reducer resolves `include::` paths relative to the file being processed. Since assemblies use `include::modules/...`, the `modules/` symlink in the book directory must be resolvable.

#### Reduction Process

1. Verify `asciidoctor-reducer` is available:
   ```bash
   which asciidoctor-reducer
   ```
   If not found, tell the user to install it and stop.

2. Create the output directory if it doesn't exist

3. For each assembly `.adoc` file:
   ```bash
   cd <repo-root>/<book-Dir> && asciidoctor-reducer <file>.adoc -o <output-dir>/<file>-reduced.adoc
   ```

   For nested topics with a subdirectory:
   ```bash
   cd <repo-root>/<book-Dir> && asciidoctor-reducer <sub-Dir>/<file>.adoc -o <output-dir>/<file>-reduced.adoc
   ```

4. Verify reduction succeeded by checking the output file exists and has no remaining `include::` directives:
   ```bash
   grep -c "^include::" <output-dir>/<file>-reduced.adoc
   ```
   (Should return 0 or only have false positives in code blocks)

### Step 4: Concatenate Reduced Files

1. Create a single concatenated document for analysis
2. For each reduced assembly (in topic map order):
   - Insert a level-1 heading: `= <Topic Name>` (using the `Name` from the topic map)
   - Append the reduced content
   - Insert a blank line separator
3. Save the concatenated file as `<output-dir>/<book>-combined.adoc`
4. Report the total line count to assess processing strategy

### Step 5: Build Source Map

1. For each assembly, parse `include::` directives from the ORIGINAL (unreduced) assembly to build the include graph
2. For each include, record:
   - `assembly`: the assembly filename
   - `module`: the included module path
   - `type`: module type based on naming convention (con-, proc-, ref-, snip-)
   - `leveloffset`: the level offset from the include directive
3. Map section titles from the reduced output back to original module files by matching heading text
4. Save the combined include graph as `<output-dir>/<book>-include-graph.json`

#### Include Graph JSON Format

```json
{
  "book": "installing_gitops",
  "book_name": "Installing GitOps",
  "assemblies": [
    {
      "file": "preparing-gitops-install.adoc",
      "topic_name": "Preparing to install OpenShift GitOps",
      "includes": [
        {
          "module": "modules/gitops-preparing-install.adoc",
          "type": "CONCEPT",
          "leveloffset": "+1"
        }
      ]
    }
  ]
}
```

#### Module Type Detection

Red Hat modular docs follow naming conventions for module files:
- `con-*.adoc` or filename contains `con-` = **CONCEPT** (explanatory content)
- `proc-*.adoc` or filename contains `proc-` = **PROCEDURE** (step-by-step instructions)
- `ref-*.adoc` or filename contains `ref-` = **REFERENCE** (tables, lists, specifications)
- `snip-*.adoc` or filename contains `snip-` = **SNIPPET** (reusable fragments)
- Anything else = **UNKNOWN**

### Step 6: JTBD Analysis

1. Read the concatenated combined file
2. Parse into Section objects using AsciiDoc heading syntax:
   ```
   = Level 1 (Document/Book Title)
   == Level 2 (Chapter)
   === Level 3 (Section)
   ==== Level 4 (Subsection)
   ```
3. Skip boilerplate sections:
   - Legal Notice
   - Providing feedback on Red Hat documentation
   - Making open source more inclusive
   - Preface
   - any section with "Additional resources" as the only content
4. Assess document size for processing strategy:

| Combined File Size | Strategy |
|-------------------|----------|
| < 500 lines | Single pass processing |
| >= 500 lines | Chunked subagent processing |

#### Single Pass Processing

For small combined files:
1. Read the entire combined AsciiDoc
2. Apply JTBD extraction methodology (from `@plugins/jtbd-tools/reference/methodology.md`)
3. Generate all records in one pass
4. Write to JSONL file

#### Chunked Processing

For large combined files:
1. Parse into sections by AsciiDoc headings
2. Group sections into chunks of 3-5 top-level sections (== headings)
3. For each chunk, launch a Task subagent:
   ```
   Task(subagent_type="general-purpose", prompt=chunk_analysis_prompt)
   ```
   The chunk prompt must include:
   - The chunk content
   - The full methodology from `@plugins/jtbd-tools/reference/methodology.md`
   - The schema from `@plugins/jtbd-tools/reference/schema.md`
   - The book name and doc identifier
   - Instructions to output ONLY valid JSONL records
   - Context about which part of the book this chunk covers
4. Collect results from all subagent chunks
5. Merge records, deduplicate, ensure parent_job references are consistent

### Step 7: Enrich Records with Module Provenance

After JTBD extraction, enrich each record:

1. Match each record's `section` field to a section in the combined file
2. Look up that section's source module from the include graph
3. Update the `evidence` field to include:
   - The reduced file reference
   - The section heading
   - Line numbers in the combined file
   - The source module path and type (if found)
4. Update the `notes` field to include:
   - Source module path and type
   - Assembly file this came from

Example enriched record:
```json
{
  "evidence": "installing_gitops-combined.adoc -> Section 'Installing OpenShift GitOps', lines 45-120 [module: modules/gitops-proc-installing.adoc, type: PROCEDURE]",
  "notes": "Source module: modules/gitops-proc-installing.adoc (PROCEDURE). Assembly: installing-openshift-gitops.adoc"
}
```

### Step 8: Validate Against Source

Unless `--skip-validation` is passed, run the grounding validation described in `@plugins/jtbd-tools/reference/methodology.md` Step 9:

1. For each JTBD record, parse the `evidence` field to extract the source file, section heading, and line range
2. Re-read the cited lines from the combined file (±20 lines context window)
3. Verify the `section` field matches an actual heading in the combined file (mechanical check)
4. Run the grounding check prompt to verify job statement, persona, and desired outcomes are supported by the source
5. Set `validation_status` and `validation_flags` on each record
6. Print a validation summary to the user

Processing strategy:
- ≤ 20 records: single validation prompt with all records and their source excerpts
- \> 20 records: chunked validation with 5-10 records per subagent

### Step 9: Write Output

Save all outputs to `<output-dir>/`:

1. **`<book>-jtbd.jsonl`** — JTBD records, one JSON object per line
2. **`<book>-jtbd.csv`** — CSV version with the same records (for spreadsheet use)
   - Use these columns: `doc,section,job_statement,job_type,persona,job_map_stage,granularity,parent_job,prerequisites,related_jobs,desired_outcomes,evidence,notes`
   - Array fields (prerequisites, related_jobs, desired_outcomes) should be joined with `; `
3. **`<book>-include-graph.json`** — Include graph for all assemblies
4. **`<book>-topicmap.json`** — Extracted topic map structure for this book:
   ```json
   {
     "name": "Installing GitOps",
     "dir": "installing_gitops",
     "distros": "openshift-gitops",
     "topics": [
       {"name": "Preparing to install", "file": "preparing-gitops-install"},
       {"name": "Installing OpenShift GitOps", "file": "installing-openshift-gitops"}
     ]
   }
   ```
5. **Individual `<file>-reduced.adoc` files** — Reduced assemblies
6. **`<book>-combined.adoc`** — Concatenated reduced content

#### Default Output Directory

If `--output` is not specified:
- With `--distro`: `analysis/<distro>/<book>/`
- Without `--distro`: `analysis/topicmap/<book>/`

The `doc` field in JTBD records should be set to `<book>-combined.adoc` (the concatenated file name).

## Processing Strategy Details

### Chunk Analysis Prompt Template

When using chunked processing, each subagent receives this prompt:

```
You are analyzing a section of the book "<Book Name>" from the <distro> documentation.

## Your Task
Extract Jobs-To-Be-Done (JTBD) records from the following AsciiDoc content.

## Methodology
<contents of @plugins/jtbd-tools/reference/methodology.md>

## Record Schema
<contents of @plugins/jtbd-tools/reference/schema.md>

## Document Info
- doc: <book>-combined.adoc
- Book: <Book Name>
- Sections covered: <list of section headings in this chunk>

## Content to Analyze

<chunk content>

## Output Format
Output ONLY valid JSONL — one JSON object per line, no markdown fencing, no commentary.
Each record must conform to the schema above.
Set the `doc` field to "<book>-combined.adoc" for all records.
```

### Section Grouping for Chunks

When grouping sections into chunks:
1. Each `= Title` (level 1) heading from the topic-map-inserted headings marks a new assembly boundary
2. Group 3-5 assemblies per chunk
3. Never split an assembly across chunks — keep all content between two `= Title` headings together
4. If a single assembly exceeds 300 lines, it gets its own chunk

## Workflow

```bash
# Step 1: List books to find what's available
/jtbd-analyze-topicmap ~/openshift-docs --list-books --distro openshift-gitops

# Step 2: Analyze a book
/jtbd-analyze-topicmap ~/openshift-docs --book installing_gitops --distro openshift-gitops

# Step 3: Review results
cat analysis/openshift-gitops/installing_gitops/installing_gitops-jtbd.jsonl

# Step 4: Check include graph
cat analysis/openshift-gitops/installing_gitops/installing_gitops-include-graph.json

# Step 5: Generate TOC from records
/jtbd-toc analysis/openshift-gitops/installing_gitops/

# Step 6: Compare with current structure
/jtbd-compare --source analysis/openshift-gitops/installing_gitops/
```

## Quality Checklist

- [ ] Topic map parsed correctly (all books listed, distro filter works)
- [ ] All assembly files resolved and found on disk
- [ ] Reduced files have all includes resolved (no remaining `include::` directives)
- [ ] Combined file has correct `= Topic Name` headings between assemblies
- [ ] Include graph JSON has correct module types (CONCEPT, PROCEDURE, REFERENCE, SNIPPET)
- [ ] Evidence fields include module file references and line numbers
- [ ] Section titles from reduced file map correctly to original modules
- [ ] Records follow "When X, I want Y, so I can Z" format
- [ ] ~10-15 main_jobs per book (not too many, not too few)
- [ ] All user_story records have parent_job set
- [ ] JSONL is valid (one JSON object per line, parseable)
- [ ] CSV columns match schema
- [ ] Grounding validation passed (or flagged records reviewed and accepted)
- [ ] No `no_evidence` records (evidence citations resolve to real content)

## Methodology Reference

The complete JTBD extraction methodology is shared with `/jtbd-analyze` and `/jtbd-analyze-adoc`:
- See `@plugins/jtbd-tools/reference/methodology.md` for extraction rules
- See `@plugins/jtbd-tools/reference/schema.md` for record schema
