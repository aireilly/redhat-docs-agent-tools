---
name: rhivos-workflow
description: >-
  Orchestrates the full RHIVOS content pipeline: map upstream sources, convert
  Markdown to AsciiDoc, restructure with JTBD principles, run quality review,
  and publish to the doc repo. Runs stages sequentially with interactive review
  gates between each. Supports resume from last completed gate. Use this skill
  to process a complete RHIVOS Doc Title end-to-end.
argument-hint: "<google-doc-url>" --title "Doc Title" [--sig-docs-path <path>] [--resume]
allowed-tools: Read, Write, Bash, Glob, Grep, Edit, Skill, Agent, AskUserQuestion
---

# RHIVOS Content Workflow

Orchestrates the 5-stage RHIVOS content pipeline with interactive review gates.

## When to use

- Processing a RHIVOS Doc Title end-to-end
- Resuming a previously interrupted workflow

## Inputs

Parse from `$ARGUMENTS`:

- **Google Doc URL** (required, positional) — the skeleton ToC document
- **`--title "Doc Title"`** (required) — one of the 8 RHIVOS Doc Titles
- **`--sig-docs-path <path>`** (optional) — path to local sig-docs clone. Default: `~/Documents/git-repos/sig-docs`
- **`--resume`** (optional) — resume from the last completed gate instead of starting fresh

If the URL or title is missing, ask the user with `AskUserQuestion`.

## Pipeline overview

```
Stage 1: MAP         -> rhivos-map-upstream       -> GATE 1: interactive mapping review
Stage 2: CONVERT     -> rhivos-fetch-convert      -> GATE 2: interactive module review
Stage 3: RESTRUCTURE -> rhivos-jtbd-restructure   -> GATE 3: interactive JTBD review
Stage 4: REVIEW      -> rhivos-quality-review     -> GATE 4: interactive issue triage
Stage 5: PUBLISH     -> copy to doc repo          -> GATE 5: final confirmation
```

Gates are mandatory and interactive. Each gate pauses execution, presents a structured summary, and accepts writer decisions via `AskUserQuestion`. No stage runs until the previous gate is approved.

## Setup

### 1. Compute the doc-title-slug

Convert the `--title` value to kebab-case lowercase:
- "RHIVOS Image Building" -> `rhivos-image-building`
- "Application development and integration" -> `application-development-and-integration`

### 2. Initialize artifacts directory

```bash
mkdir -p "artifacts/<doc-title-slug>"
```

### 3. Check for resume

If `--resume` is set, read `artifacts/<doc-title-slug>/workflow-state.json`:

```json
{
  "doc_title": "<Doc Title>",
  "slug": "<doc-title-slug>",
  "google_doc_url": "<url>",
  "sig_docs_path": "<path>",
  "stages": {
    "map": { "status": "approved", "completed_at": "<ISO 8601>" },
    "convert": { "status": "approved", "completed_at": "<ISO 8601>" },
    "restructure": { "status": "pending" },
    "review": { "status": "pending" },
    "publish": { "status": "pending" }
  }
}
```

Skip to the first stage with `status: "pending"`. If all stages are approved, inform the writer the workflow is already complete.

If `--resume` is not set but `workflow-state.json` exists, ask the writer:
- Resume the existing workflow?
- Start fresh (overwrites previous artifacts)?

### 4. Initialize state file

If starting fresh, write the initial `workflow-state.json` with all stages set to `"pending"`.

## Stage 1: MAP

Invoke the mapping skill:

```
Skill: rhivos-map-upstream, args: "<google-doc-url>" --title "<Doc Title>" --sig-docs-path "<path>"
```

The skill handles its own interactive gate (Gate 1). When the writer approves:

1. Update `workflow-state.json`: set `map` status to `"approved"` with timestamp
2. Proceed to Stage 2

## Stage 2: CONVERT

Invoke the conversion skill:

```
Skill: rhivos-fetch-convert, args: "artifacts/<slug>/upstream-mapping.yaml" --sig-docs-path "<path>"
```

The skill handles its own interactive gate (Gate 2). When the writer approves:

1. Update `workflow-state.json`: set `convert` status to `"approved"` with timestamp
2. Proceed to Stage 3

## Stage 3: RESTRUCTURE

Invoke the restructuring skill:

```
Skill: rhivos-jtbd-restructure, args: "<slug>"
```

The skill handles its own interactive gate (Gate 3). When the writer approves:

1. Update `workflow-state.json`: set `restructure` status to `"approved"` with timestamp
2. Proceed to Stage 4

## Stage 4: REVIEW

Invoke the quality review skill:

```
Skill: rhivos-quality-review, args: "<slug> --fix"
```

The `--fix` flag enables auto-fix for high-confidence issues. The skill handles its own interactive gate (Gate 4). When the writer approves:

1. Update `workflow-state.json`: set `review` status to `"approved"` with timestamp
2. Proceed to Stage 5

## Stage 5: PUBLISH

The publish stage copies final artifacts into the RHIVOS doc repo.

### 1. Determine target paths

Ask the writer for the target doc repo path if not obvious from the current working directory:

```
Ready to publish "<Doc Title>" modules.

Where should the files be copied?
  - modules/ directory (e.g., doc/modules/)
  - assemblies/ directory (e.g., doc/assemblies/)

If you're in the RHIVOS doc repo, I'll detect the paths automatically.
Otherwise, provide the base path.
```

### 2. Copy files

```bash
# Copy modules
cp artifacts/<slug>/modules/*.adoc <target>/modules/

# Copy assembly
cp artifacts/<slug>/assemblies/*.adoc <target>/assemblies/
```

### 3. Final confirmation (Gate 5)

Present the publish summary:

```
Published "<Doc Title>" to <target>:
  - <N> modules copied to <target>/modules/
  - <N> assemblies copied to <target>/assemblies/

Files are NOT committed. Review the changes and commit when satisfied:
  git add <target>/modules/ <target>/assemblies/
  git status

Workflow complete.
```

Update `workflow-state.json`: set `publish` status to `"approved"` with timestamp.

## Error handling

- If any skill invocation fails, capture the error and present it to the writer
- Do NOT automatically retry — let the writer decide:
  - Retry the stage
  - Abort and resume later
  - Skip the stage (not recommended, warn about downstream impact)
- Always save progress to `workflow-state.json` before stopping

## Progress display

At the start of each stage, display the pipeline status:

```
RHIVOS Content Pipeline: "<Doc Title>"
  [x] MAP         — approved (2026-04-15T10:30:00Z)
  [x] CONVERT     — approved (2026-04-15T11:15:00Z)
  [ ] RESTRUCTURE — in progress
  [ ] REVIEW      — pending
  [ ] PUBLISH     — pending
```

## Output

All artifacts are under `artifacts/<doc-title-slug>/`:

```
artifacts/<doc-title-slug>/
  workflow-state.json              # Pipeline progress
  upstream-mapping.yaml            # Stage 1 output
  modules/                         # Stage 2-3 output
    con_*.adoc
    proc_*.adoc
    ref_*.adoc
  assemblies/                      # Stage 3 output
    assembly_*.adoc
  conversion-report.md             # Stage 2 output
  jtbd/                            # Stage 3 output
    jtbd-records.jsonl
    jtbd-toc-proposed.md
    jtbd-comparison.md
    jtbd-consolidation-report.md
  quality-review/                  # Stage 4 output
    review-report.md
    issues.json
    auto-fixes-applied.md
```
