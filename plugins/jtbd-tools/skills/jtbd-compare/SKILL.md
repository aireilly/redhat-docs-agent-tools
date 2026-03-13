---
name: jtbd-compare
description: Compare current feature-based documentation structure with proposed JTBD structure. Use to show stakeholders the benefits of restructuring and quantify navigation improvements.
argument-hint: [source-doc] [jsonl-file]
allowed-tools: Read, Glob, Write
---

# JTBD TOC Comparison Skill

Generate a side-by-side comparison of current (feature-based) vs. proposed (JTBD-based) documentation structures.

## Usage

```bash
# Compare using source doc and existing records
/jtbd-compare docs_raw/rhoai/creating-a-workbench.md

# Explicit paths
/jtbd-compare docs_raw/rhoai/creating-a-workbench.md analysis/rhoai/creating-a-workbench/creating-a-workbench-jtbd.jsonl
```

## Arguments

- **source-doc** (required): Path to original markdown document
- **jsonl-file** (optional): Path to JTBD records. If omitted, will look in `analysis/<project>/<doc>/`

## What This Skill Does

1. **Reads source markdown** to extract current TOC structure
2. **Reads JTBD records** for proposed structure
3. **Generates side-by-side comparison** with metrics
4. **Writes output** to `<doc>-comparison.md`

## Output Location

Comparison is saved to:
```
analysis/<project>/<doc>/<doc>-comparison.md
```

## Comparison Structure

The generated comparison follows this structure (see `comparison-guide.md` for details):

```markdown
# [Document Name] - TOC Comparison

**Current Feature-Based vs. Proposed JTBD-Based Structure**

**Analysis Date:** [Date]
**JTBD Records:** X
**Main Jobs:** Y (rolled up from records)

---

## Current Structure (Feature-Based)

[Document Name]
 - Chapter 1: [Feature/Platform Name]
   - Section 1.1: [Feature Detail]
   - Section 1.2: [Feature Detail]
 - Chapter 2: [Another Feature/Platform]
   ...

---

## Proposed JTBD-Based Structure

## Choose Your Approach

Job 1: [Clean Main Job Title]
  When: [Situation from job statements]
  Personas: [All personas who do this job]

  - Option A: [Approach Name]
    Persona: [Specific persona]
    → Lines X-Y: Section description
    Source: Chapter X, Section X.X

  - Option B: [Alternative Approach]
    → Lines A-B: Section description
    Source: Chapter X, Section X.X

## Set Up & Configure

Job 2: [Next Main Job]
  ...

[Continue through all workflow phases]

---

## Key Differences

### Current Structure (Feature-Based)
**Organized By:** Features, platforms, technical components
**Navigation:** X sections/chapters
**User Journey:** Linear reading, chapter by chapter

### Proposed Structure (JTBD-Based)
**Organized By:** Job map stages, user goals
**Navigation:** Y main jobs with persona paths
**User Journey:** Goal-directed, choose your path

---

## Navigation Improvement

**Current:** Browse X sections to find content
**Proposed:** Navigate Y main jobs -> choose persona path
**Reduction:** Z% fewer top-level items
**Benefit:** Find content in 2-3 clicks vs 5-10

---

## Workflow Coverage Comparison

| Stage | Current | Proposed | Gap Status |
|-------|---------|----------|------------|
| Get Started | ⚠️ Scattered | ✅ Job 1 | Improved |
| Plan | ❌ Missing | ✅ Job 2 | Added |
| Configure | ✅ Chapter 2 | ✅ Jobs 3, 4, 5 | Reorganized |
| Deploy | ✅ Chapters 3-5 | ✅ Jobs 6, 7, 8 | Consolidated |
| Monitor | ❌ Missing | ❌ Missing | Gap remains |
| Troubleshoot | ⚠️ Appendix | ✅ Job 9 | Elevated |
| Reference | ✅ Appendix | ✅ Job 10 | Reorganized |

### Gaps Identified
- Monitor: No observability content
- Upgrade: No upgrade procedures
- Migrate: No migration content (if applicable)

---

## Example: Content Consolidation

**Current (Fragmented):**
- Section 2.5.1: Viewing metrics (single-model)
- Section 3.2: Viewing metrics (NIM)
- Section 4.8: Viewing metrics (multi-model)

**Proposed (Consolidated):**
Job 6: Monitor Model Performance
  - Platform variation: Single-model (2.5.1)
  - Platform variation: NIM (3.2)
  - Platform variation: Multi-model (4.8)

**Benefit:** One place to learn monitoring!
```

## Key Design Principles

### Job-Based, NOT Persona-Based

**Modern AI teams have fluid roles** - the same person completes jobs across multiple personas.

**DO:**
- Job titles describe WHAT needs to be done
- Prerequisites specify permissions needed
- Use "Context:" to explain scenarios
- Include both UI and CLI paths where applicable

**DON'T:**
- Use "For [Persona]:" prefixes on tasks
- Organize sections by persona/role
- Prerequisites as job titles
- Hide content behind persona labels

### Granularity Levels

| Level | Description | Purpose |
|-------|-------------|---------|
| **Main Jobs** (~10-15) | Stable, outcome-focused goals | Level 1 headings |
| **User Stories** (2-7 per job) | Persona-specific approaches | Nested under jobs |
| **Procedures** | Step-by-step instructions | Referenced with line numbers |

### Workflow Order

Order jobs by when users need them (but use descriptive headings):

| Internal Stage | Use This Heading |
|----------------|------------------|
| Get Started | "Getting Started" |
| Plan | "Choose Your Approach" |
| Architecture | "Understand Architecture" |
| Configure | "Set Up & Configure" |
| Deploy | "Deploy & Use" |
| Develop | "Develop & Experiment" |
| Training | "Train Models" |
| Operate | "Operate & Manage" |
| Monitor | "Track Performance" |
| Troubleshoot | "Troubleshoot Issues" |
| Administer | "Administer Platform" |
| Secure | "Secure Your Environment" |
| Migrate | "Migrate & Move" |
| Upgrade | "Upgrade & Update" |
| Extend | "Extend & Customize" |
| Reference | "Reference" |
| What's New | "What's New" |

## Research Insights Section

If JTBD records include research extension fields (`pain_points`, `strategic_priority`, `teams_involved`), add this section:

```markdown
## UX Research Alignment

### Pain Points Addressed by Restructure

| Pain Point (from analysis) | How New Structure Helps |
|---------------------------|------------------------|
| "Complex YAML configuration" | Task 3.1-3.6 breaks into discrete sections |
| "Multiple environment variables" | Task 3.4 consolidates all SSL/TLS variables |

### Strategic Priorities Elevated

| Strategic Job | Current Location | Proposed Location | Improvement |
|--------------|-----------------|-------------------|-------------|
| OAuth Configuration | Buried at line 380 | Job 3.2: Dedicated section | Direct navigation |

### Cross-Team Collaboration Visibility

| Job | Teams Involved | Benefit |
|-----|---------------|---------|
| Create Custom Image | Platform Team, DS Team | Clear handoff visible |
```

**Note:** Only include this section if research fields are populated.

## Quality Checklist

### Main Jobs
- [ ] 10-15 main jobs total (not 30+)
- [ ] Clean, professional titles (not fragments)
- [ ] Outcome-focused (not feature-focused)
- [ ] Organized by domain taxonomy stages

### User Stories/Tasks
- [ ] 2-7 per main job (not standalone jobs)
- [ ] Scenario-specific or approach-based
- [ ] NO "For [Persona]:" prefixes
- [ ] Properly nested under main jobs

### Structure
- [ ] Follows domain taxonomy stage progression
- [ ] Line references use `→ Lines X-Y: Title` format with `Source:` line
- [ ] Prerequisites stated as permissions
- [ ] Both UI and CLI paths documented

### Comparison
- [ ] Current structure shown accurately
- [ ] Proposed structure is logical
- [ ] Key differences explained
- [ ] Navigation improvements quantified
- [ ] Workflow coverage comparison with ✅/⚠️/❌ indicators
- [ ] Gaps identified with recommendations

## Common Mistakes to Avoid

- **Too many main jobs** (>20) - Most are probably user stories
- **Persona gates** - "For Administrators:" prefixes
- **No consolidation** - Same job appearing multiple times
- **Stage labels in headings** - Using "DEFINE:", "EXECUTE:"
- **Missing metrics** - No quantified improvement

## Example Workflow

```bash
# Step 1: Ensure JTBD records exist
/jtbd-analyze docs_raw/rhoai/creating-a-workbench.md

# Step 2: Generate comparison
/jtbd-compare docs_raw/rhoai/creating-a-workbench.md

# Output:
# - Displays comparison preview
# - Writes to analysis/rhoai/creating-a-workbench/creating-a-workbench-comparison.md

# Step 3: Share with stakeholders
cat analysis/rhoai/creating-a-workbench/creating-a-workbench-comparison.md
```

## Reference Guidelines

For complete comparison guidelines, see `comparison-guide.md` in this skill directory.
