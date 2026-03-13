---
name: jtbd-analyze
description: Extract Jobs-To-Be-Done records from technical documentation. Use when analyzing docs for user goals, extracting job statements, or preparing content for JTBD-oriented restructuring. Handles large documents via chunked subagent processing.
argument-hint: [file-or-directory] [--research config-name] [--output path]
context: fork
allowed-tools: Read, Glob, Grep, Write, Task, Bash
---

# JTBD Analysis Skill

Extract Jobs-To-Be-Done records from technical documentation using the methodology defined in `methodology.md`.

## Usage

```bash
# Analyze a single document
/jtbd-analyze docs_raw/rhoai/creating-a-workbench.md

# With research config overlay
/jtbd-analyze docs_raw/rhoai/creating-a-workbench.md --research redhat-ai

# With custom output directory (for A/B testing)
/jtbd-analyze docs_raw/rhoai/creating-a-workbench.md --output analysis/rhoai/creating-a-workbench-skill/
```

## Arguments

- **file-or-directory** (required): Path to markdown file or directory to analyze
- **--research** (optional): Research config name for domain-specific personas and extensions
- **--output** (optional): Custom output directory. If not specified, defaults to `analysis/<project>/<doc>/`

## What This Skill Does

1. **Reads the markdown document** from the specified path
2. **Parses into sections** by markdown headers
3. **Assesses document size** to determine processing strategy
4. **Extracts JTBD records** following the methodology in `methodology.md`
5. **Writes JSONL output** to `--output` path or default `analysis/<project>/<doc>/<doc>-jtbd.jsonl`
6. **Converts to CSV** by calling `jtbd csv --input <jsonl-path>` for spreadsheet viewing

## Processing Strategy

### Document Size Assessment

| Document Size | Strategy |
|---------------|----------|
| < 500 lines | Single pass processing |
| >= 500 lines | Chunked subagent processing |

### Single Pass Processing (Small Documents)

For documents under 500 lines:
1. Read the entire document
2. Apply JTBD extraction methodology
3. Generate all records in one pass
4. Write to JSONL file

### Chunked Processing (Large Documents)

For documents 500+ lines:
1. Parse document into sections by markdown headers (# through ######)
2. Skip boilerplate sections (Legal Notice, Feedback, Additional Resources, etc.)
3. Group sections into chunks of 3-5 sections (~3000 tokens each)
4. For each chunk, launch a Task subagent:
   ```
   Task(subagent_type="general-purpose", prompt=chunk_analysis_prompt)
   ```
5. Aggregate results from all chunks
6. Write merged records to JSONL file

### Parallel vs Sequential

- **Default (Parallel)**: Launch multiple Task calls in a single message for faster processing
- **Sequential**: Use when debugging or when section order dependencies matter

## Methodology Reference

The complete JTBD extraction methodology is in `methodology.md`. Key points:

### Job Statement Format
```
When [situation], I want to [motivation], so I can [expected outcome]
```

### Granularity Levels

| Level | Description | Count per Guide |
|-------|-------------|-----------------|
| `main_job` | Stable, outcome-focused goals | ~10-15 |
| `user_story` | Persona-specific implementation paths | 2-7 per main job |
| `procedure` | Step-by-step instructions (reference only) | Skip or note in evidence |

### Job Map Stages (for internal ordering)

| Stage | Verbs | Examples |
|-------|-------|----------|
| Define | understand, choose, select | Choosing architecture approach |
| Locate | find, access, discover | Finding available resources |
| Prepare | set up, configure, install | Setting up environment |
| Confirm | verify, validate, check | Verifying deployment readiness |
| Execute | deploy, run, train, build | Deploying a model |
| Monitor | monitor, track, observe | Tracking performance metrics |
| Modify | optimize, adjust, tune | Tuning resource allocation |
| Conclude | clean up, remove, archive | Decommissioning resources |

### Job vs Task Validation

Before classifying as `main_job`, apply the "Why vs How" ladder:

1. Ask "Why would someone do this?"
2. If answer is another user goal -> This is a TASK, ladder up
3. If answer is business value/outcome -> This is a JOB, keep it

**Red flags (likely tasks, NOT main_jobs):**
- Mentions specific tools: "Configure vLLM"
- Mentions UI elements: "Click Deploy button"
- Narrow scope: "Set memory limits"

**Green flags (likely main_jobs):**
- Outcome-focused: "Deploy Model"
- Tool-agnostic: Would exist even if tech changes
- Business value: "Reduce inference latency"

## Output Schema

Each record follows the `JTBDRecord` schema (see `schema.md`):

```json
{
  "doc": "creating-a-workbench.md",
  "section": "Chapter 2: Configuring workbenches",
  "job_statement": "When setting up a development environment, I want to configure workbench resources, so I can ensure adequate compute for my experiments.",
  "job_type": "core",
  "persona": "Data scientist",
  "job_map_stage": "Configure",
  "granularity": "main_job",
  "parent_job": null,
  "prerequisites": ["Create a project", "Have cluster admin approval"],
  "related_jobs": ["Configure data connections", "Set up notebook images"],
  "desired_outcomes": [
    "Minimize time to get a working environment",
    "Reduce likelihood of resource contention"
  ],
  "evidence": "creating-a-workbench.md -> Chapter 2, lines 45-120",
  "notes": "Main job covering workbench configuration options"
}
```

## Output Location

By default, records are saved to:
```
analysis/<project>/<doc>/<doc>-jtbd.jsonl
analysis/<project>/<doc>/<doc>-jtbd.csv
```

Example:
```
analysis/rhoai/creating-a-workbench/creating-a-workbench-jtbd.jsonl
analysis/rhoai/creating-a-workbench/creating-a-workbench-jtbd.csv
```

When `--output` is specified, records are saved to:
```
<output-path>/<doc>-jtbd.jsonl
<output-path>/<doc>-jtbd.csv
```

Example with `--output analysis/rhoai/creating-a-workbench-skill/`:
```
analysis/rhoai/creating-a-workbench-skill/creating-a-workbench-jtbd.jsonl
analysis/rhoai/creating-a-workbench-skill/creating-a-workbench-jtbd.csv
```

### CSV Conversion

After writing the JSONL file, the skill calls the CLI to generate a CSV:

```bash
jtbd csv --input <output-path>/<doc>-jtbd.jsonl
```

**Prerequisite:** The `jtbd` CLI must be installed (`pip install -e .`). See the README for setup instructions.

## Chunk Processing Details

When spawning subagents for chunked processing, each chunk prompt includes:

1. **Chunk content**: The markdown sections in this chunk
2. **Document context**: Document name, section names
3. **Methodology**: Extraction guidelines from `methodology.md`
4. **Output format**: JSON array of JTBDRecord objects

### Chunk Size Guidelines

- Target: 3-5 sections per chunk
- Token estimate: ~3000 tokens per chunk
- Adjust based on section length (long sections = fewer per chunk)

### Aggregation

After all chunks complete:
1. Collect JSON arrays from each subagent
2. Merge into single records array
3. Deduplicate if any overlap
4. Write to JSONL (one record per line)

## Research Config

When `--research <config-name>` is specified:

1. Load config from `jtbd/research/<config-name>.yaml`
2. Apply domain-specific personas
3. Enable research extension fields:
   - `loop`: Inner/outer loop classification
   - `genai_phase`: Development vs production
   - `strategic_priority`: Is this a priority job from research?
   - `pain_points`: User-reported friction points
   - `teams_involved`: Cross-team collaboration

## Example Workflow

```bash
# Step 1: Analyze document
/jtbd-analyze docs_raw/rhoai/creating-a-workbench.md

# Output shows:
# - Document size and processing strategy
# - Progress as sections are analyzed
# - Summary of extracted records
# - Path to JSONL output

# Step 2: Review results
cat analysis/rhoai/creating-a-workbench/creating-a-workbench-jtbd.jsonl

# Step 3: Generate TOC from records
/jtbd-toc analysis/rhoai/creating-a-workbench/
```

## Error Handling

- **File not found**: Verify the path exists
- **Empty document**: No sections to analyze
- **Chunk failures**: Report which chunks failed, continue with others
- **Invalid output**: Validate JSON before writing

## Quality Checklist

Before completing analysis, verify:

- [ ] All significant sections have records
- [ ] Main jobs are ~10-15 (not 30+)
- [ ] Each main_job passes the "Why?" ladder test
- [ ] User stories have `parent_job` set
- [ ] Prerequisites are jobs, not section names
- [ ] Evidence includes line numbers
- [ ] No tool-specific main_jobs (vLLM, Prometheus, etc.)
