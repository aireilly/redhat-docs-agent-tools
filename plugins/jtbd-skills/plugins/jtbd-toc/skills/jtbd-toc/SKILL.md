---
name: jtbd-toc
description: Generate a JTBD-oriented Table of Contents from JTBD records. Use after running jtbd-analyze or with existing JSONL files. Organizes content by user goals and workflow stages.
argument-hint: [jsonl-file-or-directory]
allowed-tools: Read, Glob, Write
---

# JTBD TOC Generation Skill

Generate a standalone, high-quality Jobs-To-Be-Done Table of Contents from JTBD analysis records.

## Usage

```bash
# From analysis directory
/jtbd-toc analysis/rhoai/creating-a-workbench/

# From specific JSONL file
/jtbd-toc analysis/rhoai/creating-a-workbench/creating-a-workbench-jtbd.jsonl
```

## Arguments

- **jsonl-file-or-directory** (required): Path to JSONL file or analysis directory containing records

## What This Skill Does

1. **Reads JTBD records** from the specified JSONL file or finds them in the directory
2. **Groups records by main jobs** and their user stories
3. **Organizes by workflow stages** (Get Started -> Reference order)
4. **Generates formatted markdown TOC** following `toc-guidelines.md`
5. **Writes output** to `<doc>-toc-new_taxonomy.md`

## Output Location

TOC is saved to:
```
analysis/<project>/<doc>/<doc>-toc-new_taxonomy.md
```

## TOC Structure

The generated TOC follows this structure (see `toc-guidelines.md` for details):

```markdown
# [Guide Name]
**Jobs-To-Be-Done Oriented Table of Contents**

*Organized by user goals and workflow stages*

---

## Guide Overview
**Purpose:** [One sentence - what this guide helps users accomplish]
**Personas:** [List all personas from the data]
**Main Jobs:** [Number] core jobs across [Number] workflow stages

## Quick Navigation
**I want to:**
- [Common goal 1] -> Job X (Stage)
- [Common goal 2] -> Job Y (Stage)
...

# Table of Contents

## Choose Your Approach
### Job 1: [Clean Main Job Title]
*When [situation from job statement]*
**Personas:** [Who does this job]

[Organized content with options/paths]

## Set Up & Configure
### Job 2: [Next Main Job]
...

## Deploy & Use
...

## Track Performance
...

## Appendices

### A. Platform Comparison Matrix
[Trade-offs between options]

### B. Method Decision Guide
[Complexity, repeatability, prerequisites]

### C. Workflow Coverage Analysis
| Stage | Coverage | Jobs |
|-------|----------|------|
| Get Started | ✅ | Job 1 |
| Configure | ✅ | Jobs 2-4 |
| Deploy | ✅ | Jobs 5-7 |
| Monitor | ❌ | - |
...

## Navigation Guide
...

## Document Statistics
...
```

## Key Formatting Rules

### Sequential Job Numbering (CRITICAL)

Jobs MUST be numbered sequentially (1, 2, 3, 4...) based on the order they appear in the TOC output:

- Do NOT preserve job numbers from input records
- Do NOT skip numbers
- Do NOT go backwards

**Correct:**
```markdown
### Job 1: Understand Architecture
### Job 2: Choose Update Channel
### Job 3: Verify Requirements
### Job 4: Configure Namespaces
```

### Clean Job Titles

**Formula:** [Verb] + [Object/Outcome]

**Good examples:**
- "Choose Model Serving Platform"
- "Deploy a Model"
- "Monitor Model Performance"

**Bad examples:**
- "Use the multi-model" <- Fragment
- "View metrics in dashboard" <- Too specific (user story)
- "Deploy via UI wizard" <- Implementation detail

### Descriptive Section Headings (NOT Stage Labels)

**Use natural headings, NOT methodology jargon:**

| Internal Stage | Use This Heading |
|----------------|------------------|
| Get Started | "Getting Started" |
| Plan | "Choose Your Approach" or "Understand Options" |
| Architecture | "Understand Architecture" |
| Configure | "Set Up & Configure" |
| Deploy | "Deploy & Use" |
| Develop | "Develop & Experiment" |
| Training | "Train Models" |
| Operate | "Operate & Manage" |
| Monitor | "Track Performance" |
| Analyze | "Analyze Results" |
| Observe | "Observe System State" |
| Troubleshoot | "Troubleshoot Issues" |
| Administer | "Administer Platform" |
| Secure | "Secure Your Environment" |
| Migrate | "Migrate & Move" |
| Upgrade | "Upgrade & Update" |
| Extend | "Extend & Customize" |
| Reference | "Reference" |
| What's New | "What's New" |

### 3-Tier Hierarchy

Structure every job using:

```
Job (Outcome)
└── User Story / Themed Goal (Approach)
    └── Task (Implementation step)
```

### Prerequisite & Timing Surfacing

Only add enrichment when data warrants it:

| Element | Include When... |
|---------|-----------------|
| **Timing:** | Job MUST happen before/after another, OR action is irreversible |
| **Requires:** | Prerequisites are non-obvious (not just "admin access") |
| **Why:** | Risk/motivation changes how users approach the job |

**Most jobs will NOT have these lines - keep entries minimal by default.**

## Job Entry Format

```markdown
### Job [Number]: [Clean Title]
*When [situation]*

**Personas:** [Who does this]
**Timing:** [ONLY if critical] - BEFORE Job X - [consequence if missed]
**Requires:** [ONLY if non-obvious] [Brief prerequisite list]

#### [Descriptive heading for options/paths]

**[If choice-based]:**

- **Option A: [Name]** ([When to use])
  *Persona: [If specific]*
  → Lines X-Y: Section Name
  Source: Chapter X, Section X.X
  - [Benefit/feature]

- **Option B: [Name]** ([When to use])
  → Lines A-B: Section Name
  Source: Chapter X, Section X.X

**[If persona-based]:**

- **For [Persona]: [Approach]**
  → Lines X-Y: Section Name
  Source: Chapter X, Section X.X

- **For [Other Persona]: [Different Approach]**
  → Lines A-B: Section Name
  Source: Chapter X, Section X.X
```

### Line Reference Format (CRITICAL)

**Format:**
```
→ Lines X-Y: Section Title
  Source: Chapter X, Section X.X
```

**Examples:**
```markdown
→ Lines 19-22: Preface
  Source: Front matter

→ Lines 35-42: Storage requirements
  Source: Chapter 1, Section 1.2

→ Lines 488-683: Installing by using the CLI
  Source: Chapter 3, Section 3.1
```

**Rules:**
- Use arrow character (→) not dash (->)
- Place line reference at start of content block
- Include descriptive section title after colon
- Add `Source:` line with chapter/section for writer navigation

## Content Organization Principles

### Thematic Consolidation

Don't list tasks flatly. Group under themed user stories:

| Instead of... | Use... |
|---------------|--------|
| Flat list of 10 configuration tasks | 3-4 themed groups |
| "Configure X", "Configure Y", "Configure Z" | "Security Hardening", "Core Profile", "Integrations" |

### Demote Verification

Verification is a final step within execution jobs, NOT a sibling job:

**Wrong:**
```markdown
### Job 4: Deploy Workbench
### Job 5: Verify Deployment  <- WRONG: Sibling job
```

**Right:**
```markdown
### Job 4: Provision Workbench Environment

#### 4.1 Define Core Profile
[Tasks...]

#### 4.2 Verify Provisioning (Confirmation Step)  <- RIGHT: Final step
```

### Configuration Consolidation

When multiple "tasks" are fields in a single YAML, present as configuration inputs:

**Wrong:** Implies 5 separate operations
```markdown
#### 2.4 Configure OAuth
#### 2.5 Configure Resources
#### 2.6 Attach Data Connections
```

**Right:** One action with multiple inputs
```markdown
#### 2.2 Define Workbench Configuration
**Goal:** Author the Notebook CRD manifest.

- **Input:** OAuth authentication
- **Input:** Resource limits
- **Input:** Data connections

#### 2.3 Apply and Verify
- **Task:** `oc apply -f notebook.yaml`
```

## Quality Checklist

### Structure
- [ ] Main jobs are ~10-15 (not 30+)
- [ ] Job numbers are SEQUENTIAL (1, 2, 3, 4...)
- [ ] Jobs organized by workflow stage order
- [ ] NO "DEFINE:", "EXECUTE:" in section headings

### 3-Tier Hierarchy
- [ ] Jobs contain themed user stories/goals (not flat task lists)
- [ ] Each user story has a **Goal:** statement
- [ ] Tasks are labeled with **Task:** prefix
- [ ] Verification is a final step within execution jobs

### Job Titles
- [ ] Clean, professional (not fragments)
- [ ] Outcome-focused (Deploy a Model, not Deployment Features)
- [ ] Stable/timeless (would exist if tech changes)

### Content
- [ ] Prerequisites shown for jobs that need them
- [ ] Line references use `→ Lines X-Y: Section Title` format
- [ ] Platform/persona variations clear
- [ ] Decision matrices included (when multiple methods exist)
- [ ] Workflow coverage section with ✅/❌ indicators

### Job vs Task Validation
- [ ] Each Level 1 heading passes "Why?" test
- [ ] No tool-specific headings at Level 1
- [ ] Tasks are nested under Jobs, not promoted to Level 1

## Example Workflow

```bash
# Step 1: Ensure JTBD records exist
ls analysis/rhoai/creating-a-workbench/creating-a-workbench-jtbd.jsonl

# Step 2: Generate TOC
/jtbd-toc analysis/rhoai/creating-a-workbench/

# Output:
# - Displays TOC preview
# - Writes to analysis/rhoai/creating-a-workbench/creating-a-workbench-toc-new_taxonomy.md

# Step 3: Review and compare
cat analysis/rhoai/creating-a-workbench/creating-a-workbench-toc-new_taxonomy.md
/jtbd-compare docs_raw/rhoai/creating-a-workbench.md
```

## Reference Guidelines

For complete TOC generation guidelines, see `toc-guidelines.md` in this skill directory.
