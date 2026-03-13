# JTBD Consolidation Report Guidelines

## Purpose

Generate stakeholder-facing consolidation reports that explain how JTBD restructuring improves documentation navigation. The consolidation report is the capstone artifact of the JTBD analysis workflow — it synthesizes JTBD records, TOC, and comparison into a single document that explains what's changing, why, and what impact it has.

**Audience:** Documentation writers, content strategists, product managers, engineering leads

**Key difference from comparison:** The comparison (`/jtbd-compare`) shows structure side-by-side. The consolidation report explains the *reasoning* behind changes, provides concrete consolidation examples, quantifies navigation improvements, and identifies content gaps with impact ratings.

---

## Output Structure

### Required Sections (In Order)

Every consolidation report must contain these 10 sections in this order:

1. Header & Metadata
2. Executive Summary (What's Changing + Key Improvements)
3. Current Structure (Feature-Based)
4. Proposed JTBD-Based Structure (Quick Overview + Detailed Job Descriptions)
5. Key Differences (table + Job List Adjustments)
6. Consolidation Examples (2-3 before/after)
7. Content Gaps Identified (table with impact ratings)
8. Navigation Improvement Summary (quantified metrics table)
9. UX Research Alignment (if research fields are populated)
10. Document Statistics (optional summary)

---

## Section Templates

### 1. Header & Metadata

```markdown
# [Document Name] — Consolidation Report

**Document:** [filename].md
**JTBD Records:** [N] pre-consolidated main jobs → [M] final jobs (after merging)

---
```

**Rules:**
- Use em dash (—) not hyphen in title
- Show pre-consolidated count (from JSONL) and final count (after adjustments)
- If no adjustments were made, show: "[N] main jobs (no adjustments needed)"

---

### 2. Executive Summary

```markdown
## Executive Summary

### What's Changing

[2-3 paragraphs explaining:]
- Current organizing principle (by platform, by feature, by component, etc.)
- Pain this causes (cross-chapter navigation, scattered procedures, buried content)
- Proposed organizing principle (by user goal and workflow stage)

### Key Improvements

- **[Improvement name]:** [One sentence explaining the consolidation]
- **[Improvement name]:** [One sentence]
- [5-8 bullets total]
```

**Rules:**
- Describe the organizing principle shift, not individual job changes
- Each improvement bullet names a specific consolidation pattern
- Use bold for improvement names
- Be concrete: "5 monitoring sections scattered across 2 chapters → 1 unified job" not "better monitoring"

---

### 3. Current Structure (Feature-Based)

```markdown
## Current Structure (Feature-Based)

- **Chapter 1: [Title]** — [Brief annotation]
  - 1.1. [Section] — [What it covers]
  - 1.2. [Section] — [What it covers]
- **Chapter 2: [Title]** — [Brief annotation]
  - 2.1. [Section]
    - 2.1.1. [Subsection]
  ...

**Total:** [N] chapters, [M]+ sections, organized by [organizing principle].
```

**Rules:**
- Extract from actual source document headings (do NOT copy from comparison doc)
- Show full hierarchy with brief annotations
- Bold chapter titles
- Include closing statement quantifying scope

---

### 4. Proposed JTBD-Based Structure

#### Quick Overview

```markdown
## Proposed JTBD-Based Structure

### Quick Overview

- **[Lifecycle Stage]**
  - Job 1: [Job Title]
- **[Next Stage]**
  - Job 2: [Job Title]
  - Job 3: [Job Title]
...
```

**Lifecycle stage names to use:**
- Understand & Plan
- Prepare
- Set Up & Configure
- Deploy & Serve
- Operate & Manage
- Track & Monitor
- Integrate
- Troubleshoot
- Reference

#### Detailed Job Descriptions

```markdown
### Detailed Job Descriptions

#### [Lifecycle Stage]

**Job [N]: [Clean Title]**

*[Job statement in "When X, I want Y, so I can Z" format]*

Prerequisites: [List]

- **[N.1]. [Approach title]** `[concept|procedure|reference]`
  - [Source section reference] ([Chapter]): [Description of what user learns/does]
  - Context: [When/why to use this approach]
- **[N.2]. [Next approach]** `[topic-type]`
  - [Source section] ([Chapter]): [Description]
  - [Optional sub-items for nested content]
```

**Rules:**
- Job titles follow [Verb] + [Object] formula
- Job statement in italic, full "When/want/so" format
- Prerequisites as a comma-separated list (not bulleted)
- Each approach numbered as [JobN.ApproachN]
- **Every approach MUST have a topic type tag**: `[concept]`, `[procedure]`, or `[reference]`
- Context line explains WHEN to use this approach (not what it does)

---

### 5. Key Differences

```markdown
## Key Differences

| Dimension | Current (Feature-Based) | Proposed (JTBD-Based) |
|-----------|------------------------|----------------------|
| **Organizing principle** | [Current approach] | [Proposed approach] |
| **Top-level items** | [N] chapters + [M] sections | [N] main jobs with nested approaches |
| **[Topic]-specific** | [Where it is now] | [Where it moves] |
...

### Job List Adjustments from Suggested Input

The suggested [N] jobs were consolidated to **[M] jobs** for the following reasons:

1. **Jobs [X] and [Y] ("[title]" x 2) merged** → [Explanation]
2. **Job [Z] ("[title]") absorbed into Job [W]** → [Explanation]
3. **Job [Q] ("[title]") dissolved** → [Explanation of where content went]
```

**Rules:**
- Key Differences table: 6-10 rows covering organizing principle, top-level items, and topic-specific dimensions
- Bold dimension names in the table
- Job List Adjustments: explain EVERY difference between raw JSONL main_job count and final count
- Use specific job numbers and titles in adjustment explanations
- Categorize adjustments as: merged, absorbed, dissolved, reassigned, or promoted

---

### 6. Consolidation Examples

```markdown
## Consolidation Examples

### Example 1: [Topic] ([N] scattered sections → [M] unified job)

**Current (Fragmented):**
- Section [X.Y]: [Title] ([where/what])
- Section [A.B]: [Title] ([where/what])
- Section [C.D]: [Title] ([where/what])

[1-2 sentences explaining the user pain point]

**Proposed (Consolidated):**
- **Job [N]: [Title]**
  - [N.1]. [Approach] ([source])
  - [N.2]. [Approach] ([source])
  - [N.3]. [Approach] ([source])

**Benefit:** [One sentence explaining the improvement]
```

**Rules:**
- 2-3 examples per report (not more, not fewer)
- Choose examples that show the biggest consolidation impact
- Current sections must reference real section numbers from the source document
- Each example must have a "Benefit" statement
- Good example topics: scattered monitoring, fragmented deployment paths, buried reference material

---

### 7. Content Gaps Identified

```markdown
## Content Gaps Identified

| Gap | JTBD Reference | Current Coverage | Impact |
|-----|---------------|-----------------|--------|
| [What's missing] | [Which job(s) affected] | [What exists now] | **[High/Medium/Low]** — [Brief reason] |
```

**Impact rating criteria:**

| Rating | Criteria | Examples |
|--------|----------|----------|
| **High** | Users have no guidance for a common/critical task; likely causes support tickets | No troubleshooting, no quickstart, no rollback procedures |
| **Medium** | Content exists but is insufficient, buried, or incomplete | Mentioned in passing, no step-by-step, fragmented across sections |
| **Low** | Nice-to-have content; users can work around the gap | Cost optimization tips, advanced configuration, edge cases |

**Rules:**
- 5-8 gaps per report
- Bold the impact rating
- Include brief reason after the rating
- Order by impact (High first)

---

### 8. Navigation Improvement Summary

```markdown
## Navigation Improvement Summary

| Metric | Current | Proposed | Improvement |
|--------|---------|----------|-------------|
| Top-level navigation items | [N] chapters | [M] jobs | [Comparison] |
| Sections to browse for "[common task]" | [N] sections across [M] chapters | [N] job, [M] approaches | ~[X]% reduction |
| [Next metric] | ... | ... | ... |

**Final job count: [N]** (reduced from suggested [M]). [1-2 sentences summarizing the consolidation rationale.]
```

**Rules:**
- 5-8 metrics per report
- Include at least 2 task-specific metrics ("sections to browse for X")
- Quantify improvements with percentages where possible
- Include "clicks to find" metrics for commonly sought content
- End with final job count and brief rationale

---

### 9. UX Research Alignment

**Include this section ONLY when JSONL records contain research extension fields** (pain_points, strategic_priority, teams_involved, loop).

```markdown
## UX Research Alignment

### Pain Points Addressed by Restructure

| Pain Point (from analysis) | How New Structure Helps |
|---------------------------|------------------------|
| [Pain point from records] | [How restructuring addresses it] |

### Strategic Priorities Elevated

| Strategic Job | Current Location | Proposed Location | Visibility Improvement |
|--------------|-----------------|-------------------|----------------------|
| [Job name] | [Where it is now] | [Where it moves] | [What improves] |

### Cross-Team Collaboration Visibility

| Job | Teams/Roles Involved | Collaboration Pattern |
|-----|---------------------|----------------------|
| Job [N]: [Title] | [Teams] | [How they collaborate on this job] |

### Loop Distribution

| Loop | Jobs | Implication |
|------|------|-------------|
| **Outer (Production/Ops)** | [Job numbers] | [Role focus] |
| **Inner (Dev/Experimentation)** | [Job numbers] | [Role focus] |
| **Shared** | [Job numbers] | [Why both loops need this] |
```

**Rules:**
- Pain points: 5-10 entries, extracted from `pain_points` field in JSONL records
- Strategic priorities: show jobs where `strategic_priority` is true
- Cross-team: map `teams_involved` field to collaboration patterns
- Loop distribution: map `loop` field to inner/outer/shared categories
- If research fields are empty/absent, SKIP this entire section

---

## Topic Type Classification

### Definitions

| Tag | Content Type | How to Identify |
|-----|-------------|-----------------|
| `[concept]` | Explanatory, decision-guidance | "Understanding X", "How X works", "Benefits of X", "Choosing between X and Y", overviews, architecture diagrams, comparison tables |
| `[procedure]` | Step-by-step instructions | "Creating X", "Configuring X", "Deploying X", numbered steps, prerequisites sections, verification steps, CLI commands with expected output |
| `[reference]` | Lookup material | "X endpoints", "X parameters", "X configuration options", tables of values, API paths, flag descriptions, example YAML/JSON |

### Classification Rules

1. **If the section teaches WHY or WHAT** → `[concept]`
2. **If the section tells HOW with steps** → `[procedure]`
3. **If the section lists VALUES or SPECS** → `[reference]`
4. **Mixed sections**: Use the dominant type. If a procedure section has a long reference table, tag it `[procedure]` but note the reference material
5. **Decision guidance** (choosing between approaches): `[concept]` even if it contains a comparison table

### Examples

```
"Using OCI containers for model storage"           → [concept]   (explains benefits)
"Storing a model in an OCI image"                   → [procedure] (step-by-step)
"Inference endpoints - Caikit TGIS"                 → [reference] (API paths)
"Automatic selection of serving runtimes"            → [concept]   (explains how selection works)
"Choosing a deployment strategy"                     → [concept]   (decision guidance)
"Deploying models on the model serving platform"     → [procedure] (wizard walkthrough)
"Viewing performance metrics for a deployed model"   → [procedure] (how to view metrics)
"Customizable model serving runtime parameters"      → [reference] (parameter table)
```

---

## Quality Checklist

### Structure
- [ ] All 10 required sections present
- [ ] Sections in correct order
- [ ] Executive summary is 2-3 paragraphs (not a wall of text)
- [ ] Quick Overview and Detailed Descriptions have matching job counts

### Jobs
- [ ] Every main_job from JSONL appears in the report
- [ ] Job titles follow [Verb] + [Object] formula
- [ ] Job statements in "When X, I want Y, so I can Z" format
- [ ] Job list adjustments explain all merges/changes from raw records
- [ ] Each approach has a topic type tag: `[concept]`, `[procedure]`, or `[reference]`

### Content
- [ ] Current structure extracted from actual source document headings
- [ ] Source references include chapter/section citations
- [ ] 2-3 consolidation examples with before/after format
- [ ] Gap table includes 5-8 gaps with impact ratings
- [ ] Navigation metrics are quantified with percentages

### Research (when applicable)
- [ ] UX research section included only when research fields are populated
- [ ] Pain points mapped to specific structural improvements
- [ ] Strategic priorities show current vs proposed location
- [ ] Loop distribution covers all jobs

---

## Common Mistakes to Avoid

- **Inventing content**: The report describes restructuring of existing content. Don't add sections that don't exist in the source document
- **Missing adjustments**: If final job count differs from JSONL main_job count, MUST explain in Job List Adjustments
- **Generic benefits**: "Better navigation" is insufficient. Quantify: "75% reduction in sections to browse for deployment"
- **Flat job lists**: Group approaches under jobs with numbered sub-items, don't list everything at the same level
- **Missing topic types**: Every approach entry MUST have `[concept]`, `[procedure]`, or `[reference]`
- **Skipping UX research**: If JSONL records have pain_points or strategic_priority fields, include the section
- **Copy-pasting comparison**: The consolidation report has different structure, audience, and purpose than the comparison doc
- **Wrong current structure**: Extract chapters/sections from the actual source markdown, not from the comparison doc
- **No consolidation rationale**: Each merge/absorption must explain WHY, not just WHAT changed
