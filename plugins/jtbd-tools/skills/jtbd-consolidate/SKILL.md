---
name: jtbd-consolidate
description: Generate a consolidation report showing how JTBD restructuring improves documentation navigation. Use after running jtbd-analyze, jtbd-toc, and jtbd-compare to produce a stakeholder-facing summary with consolidation examples, gap analysis, and navigation improvements.
argument-hint: [analysis-directory]
context: fork
allowed-tools: Read, Glob, Write, Bash
---

# JTBD Consolidation Report Skill

Generate a stakeholder-facing consolidation report that explains what's changing in a documentation restructure and why, with concrete consolidation examples, gap analysis, and quantified navigation improvements.

## Usage

```bash
# From analysis directory (must contain JSONL, TOC, and comparison files)
/jtbd-consolidate analysis/rhoai/deploying-models-v3/

# From specific JSONL file
/jtbd-consolidate analysis/rhoai/deploying-models-v3/deploying-models-jtbd.jsonl
```

## Arguments

- **analysis-directory** (required): Path to analysis directory or JSONL file. The directory must contain:
  - `<doc>-jtbd.jsonl` — JTBD records
  - `<doc>-toc-new_taxonomy.md` — TOC (for proposed structure)
  - `<doc>-comparison.md` — Comparison (for current structure context)

## What This Skill Does

1. **Locates input files** in the analysis directory (JSONL, TOC, comparison)
2. **Reads JTBD records** and groups by granularity (main_job, user_story, procedure)
3. **Determines source document path** from the `doc` field in JSONL records
4. **Reads source markdown** to extract current chapter/section structure
5. **Reads comparison and TOC** for proposed structure context
6. **Generates consolidation report** following `@plugins/jtbd-tools/reference/consolidation-guide.md`
7. **Writes output** to `<doc>-consolidation-report.md`

## Output Location

Report is saved to:
```
analysis/<project>/<doc>/<doc>-consolidation-report.md
```

## Consolidation Report Structure

The generated report follows this structure (see `@plugins/jtbd-tools/reference/consolidation-guide.md` for details):

```markdown
# [Document Name] — Consolidation Report

**Document:** [filename].md
**JTBD Records:** [N] pre-consolidated main jobs → [M] final jobs (after merging)

---

## Executive Summary

### What's Changing
[2-3 paragraphs explaining the organizing principle shift]

### Key Improvements
[Bulleted list of 5-8 major improvements]

---

## Current Structure (Feature-Based)
[Hierarchical bullet list of actual document chapters/sections]

---

## Proposed JTBD-Based Structure

### Quick Overview
[Jobs grouped by lifecycle stage]

### Detailed Job Descriptions
[For each job: statement, prerequisites, approaches with topic types, context]

---

## Key Differences
[Comparison table: Dimension | Current | Proposed]

### Job List Adjustments
[Numbered list explaining consolidation decisions]

---

## Consolidation Examples
[2-3 before/after examples with benefit statements]

---

## Content Gaps Identified
[Table: Gap | JTBD Reference | Current Coverage | Impact]

---

## Navigation Improvement Summary
[Table: Metric | Current | Proposed | Improvement]

---

## UX Research Alignment
[Pain points, strategic priorities, cross-team collaboration, loop distribution]
```

## Topic Type Classification

Each source section reference in the Detailed Job Descriptions includes a topic type tag:

| Tag | Meaning | Indicators |
|-----|---------|------------|
| `[concept]` | Explanatory content | Architecture overviews, how-it-works, decision guidance, comparisons, benefits |
| `[procedure]` | Step-by-step instructions | Prerequisites, numbered steps, verification, CLI commands |
| `[reference]` | Lookup material | API endpoints, parameter tables, configuration examples, CLI flags, glossaries |

**Example:**
```markdown
- **1.1. Understand OCI container storage benefits** `[concept]`
  - 1.1. Using OCI containers for model storage (Chapter 1)
- **2.1. Package model as an OCI image** `[procedure]`
  - 1.2. Storing a model in an OCI image (Chapter 1)
- **6.3. Runtime-specific endpoint reference** `[reference]`
  - 4.4.1-4.4.9. Inference endpoints (Chapter 4)
```

## Job Description Format

Each job in the Detailed Job Descriptions section follows this format:

```markdown
**Job [N]: [Clean Title]**

*[Job statement in "When X, I want Y, so I can Z" format]*

Prerequisites: [List of required access/knowledge]

- **[N.1]. [Approach title]** `[topic-type]`
  - [Source section] ([Chapter]): [Description]
  - Context: [When/why to use this approach]
- **[N.2]. [Next approach]** `[topic-type]`
  - [Source section] ([Chapter]): [Description]
```

## Key Design Principles

### Consolidation Report vs Comparison

| Aspect | Comparison (`/jtbd-compare`) | Consolidation Report (`/jtbd-consolidate`) |
|--------|------------------------------|-------------------------------------------|
| **Audience** | Technical reviewers | Stakeholders, writers, managers |
| **Focus** | Side-by-side structure diff | What's changing and WHY |
| **Job adjustments** | None — shows raw proposed structure | Explains merges, absorptions, reassignments |
| **Examples** | Brief consolidation mention | 2-3 detailed before/after examples |
| **Gaps** | Coverage table with indicators | Gap table with impact ratings |
| **Navigation** | Quantified improvement metrics | Detailed metric-by-metric comparison |
| **Research** | Optional section if fields exist | Full alignment section with pain points |

### Job List Adjustments

The consolidation report explicitly explains how the raw JTBD records were refined:
- **Merges**: Two duplicate jobs combined (e.g., deploy jobs split by persona → one job)
- **Absorptions**: Narrow jobs folded into parent jobs (e.g., "see examples" → reference under deploy)
- **Reassignments**: User stories moved from wrong parent to correct parent
- **Promotions**: User stories elevated to main jobs when warranted

### Impact Rating Criteria

| Rating | Criteria |
|--------|----------|
| **High** | Users have no guidance for a common/critical task; likely causes support tickets |
| **Medium** | Content exists but is insufficient, buried, or incomplete |
| **Low** | Nice-to-have content; users can work around the gap |

## Processing Steps

### Step 1: Locate Input Files

```
Given: analysis/rhoai/deploying-models-v3/
Find:  deploying-models-jtbd.jsonl
       deploying-models-toc-new_taxonomy.md
       deploying-models-comparison.md
```

### Step 2: Read and Parse JSONL Records

- Count main_jobs, user_stories, procedures
- Group user_stories by parent_job
- Extract doc field to find source document path
- Note research extension fields (pain_points, strategic_priority, loop, etc.)

### Step 3: Read Source Document

- Extract chapter/section hierarchy from markdown headings
- Count total sections and chapters
- Note the organizing principle (by feature, by platform, by component, etc.)

### Step 4: Read Comparison and TOC

- Use comparison for current vs proposed context
- Use TOC for the proposed structure with line references

### Step 5: Generate Report

Follow `@plugins/jtbd-tools/reference/consolidation-guide.md` section by section. Key generation logic:

**Executive Summary:**
- Describe current organizing principle (from source doc headings)
- Describe proposed organizing principle (from JTBD stages)
- List 5-8 key improvements based on consolidation patterns found

**Current Structure:**
- Extract from source document headings (not from comparison doc)
- Show full hierarchy with brief annotations

**Proposed Structure:**
- Quick overview: group jobs by lifecycle stage
- Detailed descriptions: for each main_job, list its user_stories as approaches
- Tag each approach with `[concept]`, `[procedure]`, or `[reference]`

**Job List Adjustments:**
- Compare the raw main_job count from JSONL against the final proposed count
- Explain each merge, absorption, or reassignment

**Consolidation Examples:**
- Pick 2-3 cases where scattered content is unified
- Show current (fragmented) sections and proposed (consolidated) job
- State the benefit

**Gaps:**
- Check which domain taxonomy stages have no coverage
- Rate impact based on user need

**Navigation:**
- Compare section counts, click paths, and findability

**UX Research:**
- Only include if JSONL records have research extension fields
- Map pain_points to structural improvements
- Show strategic_priority elevation
- Map teams_involved to collaboration patterns

### Step 6: Write Output

Write to `<doc>-consolidation-report.md` in the same analysis directory.

## Quality Checklist

### Structure
- [ ] All 10 required sections present (header through UX research)
- [ ] Sections in correct order
- [ ] Executive summary is 2-3 paragraphs (not a wall of text)

### Jobs
- [ ] Job count matches between Quick Overview and Detailed Descriptions
- [ ] Every main_job from JSONL appears in the report
- [ ] Job list adjustments explain any merges or changes from raw records
- [ ] Each approach has a `[concept]`, `[procedure]`, or `[reference]` tag

### Content
- [ ] Current structure extracted from actual source document (not invented)
- [ ] Line references and chapter/section citations present
- [ ] 2-3 consolidation examples with before/after format
- [ ] Gap table includes impact ratings (High/Medium/Low)
- [ ] Navigation metrics are quantified (percentages, counts)

### Research
- [ ] UX research section included only when research fields are populated
- [ ] Pain points mapped to specific structural improvements
- [ ] Strategic priorities show current vs proposed location
- [ ] Loop distribution (inner/outer/shared) covers all jobs

## Common Mistakes to Avoid

- **Inventing content**: The report describes restructuring, not new content. Don't add sections that don't exist in the source
- **Missing adjustments**: If the final job count differs from the JSONL main_job count, you MUST explain why in Job List Adjustments
- **Generic benefits**: "Better navigation" is not enough. Quantify: "75% reduction in sections to browse"
- **Flat job lists**: Group approaches under jobs, don't list everything at the same level
- **Missing topic types**: Every approach entry needs a `[concept]`, `[procedure]`, or `[reference]` tag
- **Skipping UX research**: If JSONL records have pain_points or strategic_priority fields, include the UX Research section
- **Copy-pasting comparison**: The consolidation report is NOT the comparison doc with extra sections. It has a different structure, audience, and purpose

## Example Workflow

```bash
# Step 1: Ensure prerequisites exist
ls analysis/rhoai/deploying-models-v3/
# Should show: deploying-models-jtbd.jsonl, deploying-models-toc-new_taxonomy.md, deploying-models-comparison.md

# Step 2: Generate consolidation report
/jtbd-consolidate analysis/rhoai/deploying-models-v3/

# Step 3: Review output
cat analysis/rhoai/deploying-models-v3/deploying-models-consolidation-report.md
```

## Reference Guidelines

For complete consolidation report guidelines, see `@plugins/jtbd-tools/reference/consolidation-guide.md` in this skill directory.
