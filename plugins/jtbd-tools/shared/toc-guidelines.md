# JTBD TOC Generation Guidelines

## Purpose

Generate standalone, high-quality Jobs-To-Be-Done Table of Contents from JTBD analysis data.

---

## Input

You'll receive:
1. Document name (e.g., "deploying-models.md")
2. JTBD records (detailed or rolled-up main jobs)
3. Optional: Guide purpose, primary personas

---

## Output Structure

### Required Sections (In Order)

#### 1. Title & Overview

```markdown
# [Guide Name]
**Jobs-To-Be-Done Oriented Table of Contents**

*Organized by user goals and workflow stages*

---

## Guide Overview

**Purpose:** [One sentence - what this guide helps users accomplish]
**Personas:** [List all personas from the data]
**Main Jobs:** [Number] core jobs across [Number] workflow stages
```

#### 2. Quick Navigation Section

**Purpose:** Let users jump directly to their goal

```markdown
## Quick Navigation

**I want to:**
- [Common goal 1] -> Job X (Stage)
- [Common goal 2] -> Job Y (Stage)
- [Common goal 3] -> Job Z (Stage)
...
```

#### 3. Table of Contents (Main Content)

**Organize by workflow stages (ordered internally, but use descriptive headings):**

```markdown
# Table of Contents

## Choose Your Approach

### Job 1: [Clean Main Job Title]
*When [situation from job statement]*

**Personas:** [Who does this job]

#### [Section heading describing options/paths]

[Organized content with:]
- Option A/B/C (for choice-based jobs)
- For [Persona]: [Approach] (for persona-based jobs)
- Step-by-step paths with line references

[Continue for jobs in same workflow phase]

## Find Resources
[Jobs for locating/discovering resources]

## Set Up for Deployment
[Jobs for setup and configuration]

## Deploy & Use
[Jobs for core execution tasks]

## Track Performance
[Jobs for monitoring and observability]

## Update & Optimize
[Jobs for modification and troubleshooting]

## Clean Up
[Jobs for decommissioning and cleanup]
```

**IMPORTANT:** Do NOT use "DEFINE:", "EXECUTE:", "MONITOR:" etc. in headings.

#### 4. Appendices (Required when applicable)

```markdown
## Appendices

### A. [Platform/Option] Comparison Matrix
[Table showing trade-offs]

### B. [Tool/Approach] Selection Guide
[Decision matrix for choosing between methods]

### C. Workflow Coverage Analysis
[Stage coverage with ✅/❌ indicators]

### D. Quick Reference
[Shortcuts, common patterns]
```

**Include appendices when:**
- Document has multiple installation/deployment methods → Decision Matrix
- Multiple platforms or approaches exist → Comparison Matrix
- Need to show workflow completeness → Coverage Analysis

#### 5. Navigation Guide

```markdown
## Navigation Guide

### By User Journey

**[Persona type] [doing common task]:**
1. Job X: [Step]
2. Job Y: [Step]
3. Job Z: [Step]

**[Another persona] [doing different task]:**
1. Job A: [Step]
...
```

#### 6. Document Statistics

```markdown
## Document Statistics

**Workflow Coverage:**
- Get Started: X jobs
- Configure: Y jobs
- Deploy: Z jobs
- Monitor: A jobs
...
- [Missing stage]: Gap identified

**Main Jobs:** [Number]
**User Stories/Paths:** [Number]
**Source Sections:** [Number]
**Platform/Tool Variations:** [Number]
```

---

## Main Job Formatting

### Sequential Job Numbering (CRITICAL)

**Jobs MUST be numbered sequentially (1, 2, 3, 4, 5...) based on the order they appear in the TOC output.**

- Do NOT preserve job numbers from the input analysis records
- Do NOT skip numbers (no "Job 1, Job 2, Job 9")
- Do NOT go backwards (no "Job 5" after "Job 9")
- Number jobs 1 through N in the exact order they appear

**Example (CORRECT):**
```
## Plan Your Deployment
### Job 1: Understand Architecture
### Job 2: Choose Update Channel

## Configure Prerequisites
### Job 3: Verify Requirements
### Job 4: Configure Namespaces
### Job 5: Configure Certificates  <- Sequential, not "Job 9"

## Deploy
### Job 6: Install Operator  <- Continues sequentially
```

### Clean Job Titles (CRITICAL)

**Formula:** [Verb] + [Object/Outcome]

**Good Examples:**
- "Choose Model Serving Platform"
- "Deploy a Model"
- "Monitor Model Performance"
- "Store Your Model"
- "Configure Serving Runtime"
- "Make Inference Requests"

**Bad Examples:**
- "Use the multi-model" <- Fragment
- "View metrics in dashboard" <- Too specific (user story)
- "Deploy via UI wizard" <- Implementation (user story)

**How to create good titles:**
1. Look at job_statement field
2. Extract the main goal (not the implementation)
3. Make it outcome-focused
4. Make it stable (would exist even if tech changes)

---

## Job vs Task Validation (The "Why vs. How" Ladder)

**CRITICAL:** Before finalizing Level 1 headings, validate each is a true Job, not a Task.

### The Ladder Technique

| Direction | Question | Result |
|-----------|----------|--------|
| UP (Why?) | "Why would someone do this?" | Moves toward Job/Outcome |
| DOWN (How?) | "How would someone do this?" | Moves toward Task/Implementation |

### Validation Process

For each proposed Level 1 Job, ask: **"Why would someone do this?"**

- If the answer is **another user goal** -> Current item is a TASK, ladder up
- If the answer is **business value/outcome** -> Current item is a JOB, keep it

### Examples

**Task Detection:**
```
Proposed: "Configure vLLM server arguments"
 Why? -> "To optimize inference performance"
 Why? -> "To reduce latency and costs" (business value)

Result: "Configure vLLM server arguments" is a TASK
Promote to: "Optimize Model Inference Performance"
```

**Job Confirmation:**
```
Proposed: "Deploy a Model"
 Why? -> "To make predictions available to applications" (business value)

Result: "Deploy a Model" is a JOB
```

### Red Flags (Likely Tasks, Not Jobs)

- Mentions specific tools: "Configure Prometheus", "Use vLLM"
- Mentions specific UI elements: "Click Deploy button"
- Very narrow scope: "Set memory limits"
- Implementation verbs: "Configure", "Install", "Set up"

### Green Flags (Likely Jobs)

- Outcome-focused: "Monitor Performance", "Deploy Model"
- Tool-agnostic: Would exist even if technology changes
- Business value: "Reduce inference latency"
- Stable verbs: "Choose", "Deploy", "Monitor", "Update"

### Auto-Correction Rules

When you identify a Task at Level 1:

1. Ask "Why?" to find the parent Job
2. Make the Job the Level 1 heading
3. Nest the Task as a user story or procedure under that Job

**Before:**
```
### Job 5: Configure vLLM Server Arguments
```

**After:**
```
### Job 5: Optimize Model Inference Performance
*When inference latency or throughput needs tuning*

- Configure vLLM server arguments
  -> Lines 100-200: Server configuration reference
  - Memory allocation
  - Batch sizing
  - GPU optimization
```

---

## Job Entry Format

```markdown
### Job [Number]: [Clean Title]
*When [situation]*

**Personas:** [Who does this]
**Timing:** [ONLY if critical] BEFORE Job X - [consequence if missed]
**Requires:** [ONLY if non-obvious] [Brief prerequisite list]
**Why:** [ONLY if risk context matters] [One sentence motivation]

#### [Descriptive heading for options/paths]

**[If choice-based]:**

- **Option A: [Name]** ([When to use])
  *Persona: [If specific]*
  -> Lines X-Y (Chapter/Section Name): Description
  - [Benefit/feature]
  - [Benefit/feature]

- **Option B: [Name]** ([When to use])
  -> Lines A-B (Chapter/Section Name): Description

**[If persona-based]:**

- **For [Persona]: [Approach]**
  -> Lines X-Y (Chapter/Section Name): Description
  [Optional procedure summary]

- **For [Other Persona]: [Different Approach]**
  -> Lines A-B (Chapter/Section Name): Description
```

**IMPORTANT:** The `Timing:`, `Requires:`, and `Why:` lines are OPTIONAL. Only include them when the data warrants it.

---

## Prerequisite & Timing Surfacing (Lightweight Enrichment)

**Goal:** Surface critical sequencing and prerequisites without bloating the TOC. Add these lines ONLY when the data warrants it - most jobs will NOT have them.

### When to Include Each Element

| Element | Include When... | Extract From |
|---------|-----------------|--------------|
| **Timing:** | Job MUST happen before/after another, OR action is irreversible | `prerequisites` field |
| **Requires:** | Prerequisites are non-obvious (not just "admin access") | `prerequisites` field |
| **Why:** | Risk/motivation changes how users approach the job | `desired_outcomes` field |

### Examples

**Job WITH critical timing:**
```markdown
### Job 4: Configure Custom Namespaces
*When your organization has namespace naming policies*

**Personas:** Cluster administrator
**Timing:** BEFORE Job 5 (Install Operator) - cannot change after
**Requires:** OpenShift CLI installed, custom namespace names determined
```

**Job WITH risk motivation:**
```markdown
### Job 2: Choose Update Channel
*When installing or managing OpenShift AI*

**Personas:** Platform administrator
**Why:** Wrong channel selection can disrupt production with unexpected updates
```

**Job WITHOUT enrichment (default - most jobs):**
```markdown
### Job 1: Understand Platform Architecture
*When evaluating or planning OpenShift AI deployment*

**Personas:** Platform administrator, Cluster administrator
```

---

## The 3-Tier Hierarchy (CRITICAL)

**Structure every job using this hierarchy:**

```
Job (Outcome)
 -> User Story / Themed Goal (Approach)
     -> Task (Implementation step)
```

**Example:**
```markdown
### Job 3: Provision Workbench Environment
*When I need to instantiate a reproducible development environment*

#### 3.1 Define Core Workbench Profile (The "Standard" Setup)
**Goal:** Establish the baseline compute and software environment.

- **Task:** Define Metadata (Name, Namespace, Labels)
  -> Lines X-Y: Section reference
- **Task:** Specify Notebook Image
  -> Lines A-B: Section reference
- **Task:** Set Resource Limits & Requests
  -> Lines C-D: Section reference

#### 3.2 Implement Security Hardening (The "Secure" Setup) - Strategic Priority
**Goal:** Secure access and communications.

- **Task:** Configure OAuth Authentication
  -> Lines E-F: Enable inject-oauth annotation
- **Task:** Configure SSL/TLS Certificates
  -> Lines G-H: Set PIP_CERT, GIT_SSL env vars

#### 3.3 Verify Provisioning (Confirmation Step)
**Goal:** Confirm the environment is ready for handoff.

- **Task:** Run `oc describe notebook`
- **Validation:** Check for Ready status and presence of sidecars
```

---

## Thematic Consolidation (Group Related Items)

**CRITICAL:** Don't list tasks flatly. Group them under themed user stories:

| Instead of... | Use... |
|---------------|--------|
| Flat list of 10 configuration tasks | 3-4 themed groups |
| "Configure X", "Configure Y", "Configure Z" | "Security Hardening", "Core Profile", "Integrations" |
| Individual verification jobs | Final "Verify" step within execution job |

**Thematic Grouping Examples:**

| Theme | Contains |
|-------|----------|
| **Core Profile** ("Standard" Setup) | Metadata, Image, Resources |
| **Security Hardening** ("Secure" Setup) | OAuth, TLS, RBAC |
| **Workflow Integrations** ("Integrated" Setup) | Data connections, Scheduling |
| **Verification** (Confirmation Step) | Status checks, Validation commands |

---

## Section Headings (Use Descriptive Names, NOT Stage Labels)

| Internal Stage | Use This Heading (NOT stage name) |
|----------------|-----------------------------------|
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

**Why:** Stage names are internal taxonomy for ordering - use descriptive headings that make sense to documentation users.

---

## Line Reference Format (CRITICAL)

Use consistent arrow notation with line numbers first, section title, and source reference on the next line.

**Format:**
```
→ Lines X-Y: Section Title
  Source: Chapter X, Section X.X
```

**Examples:**
```
→ Lines 19-22: Preface
  Source: Front matter

→ Lines 35-42: Storage requirements
  Source: Chapter 1, Section 1.2

→ Lines 488-683: Installing by using the CLI
  Source: Chapter 3, Section 3.1
```

**Rules:**
- Place line reference at start of each content block
- Include descriptive section title after colon
- Add `Source:` line with chapter/section reference for writer navigation
- Use arrow character (→) not dash (->)
- Extract section info from `section` field in JTBD records

**Good examples:**
```
→ Lines 36-45: Creating a custom image
  Source: Chapter 2, Section 2.1
  - ImageStream CRD configuration
  - Base image selection

→ Lines 365-370: OAuth configuration
  Source: Chapter 3, Section 3.2
  - inject-oauth annotation
  - Authentication setup
```

**Bad examples:**
```
-> Lines 36-45 (Chapter 2): ImageStream CRD  <- Old format, missing Source line
-> Lines 365-370                             <- No section title or source
Lines 80-150: Dashboard visibility labels    <- Missing arrow
```

---

## Decision Matrices (When Applicable)

Include decision matrices when the document presents multiple approaches to achieve the same goal.

### Method Comparison Matrix

Use when document has multiple installation, deployment, or configuration methods:

```markdown
### Installation Method Decision Guide

| Method | Best For | Complexity | Repeatability | Prerequisites |
|--------|----------|------------|---------------|---------------|
| GUI installer | Interactive setups, beginners | Low | Manual | UI access |
| CLI (`jtbd run`) | Scripted workflows, CI/CD | Medium | High | CLI installed |
| Kickstart/automated | Mass deployments | High | Very High | Automation infra |

**Choose based on:**
- **GUI installer:** First-time users, one-off installations
- **CLI:** Developers, pipeline integration, consistent environments
- **Kickstart:** Enterprise rollouts, air-gapped environments
```

### Tools Reference Matrix

Use when different options require different CLI tools or utilities:

```markdown
### CLI Tools by Platform/Option

| Option | Primary CLI | Additional Tools | Package |
|--------|-------------|------------------|---------|
| Bare metal | `bootc` | `mkksiso`, `lorax` | bootc-image-builder |
| Container | `podman` | `buildah` | podman, buildah |
| Cloud | `aws`, `gcloud` | cloud-init | cloud-provider-cli |
```

### Storage/Resource Requirements Matrix

Use when documenting resource requirements:

```markdown
### Storage Requirements Quick Reference

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| Model weights | 10 GB | 50 GB | Varies by model size |
| Container images | 5 GB | 15 GB | Multiple versions |
| Logs/telemetry | 1 GB | 10 GB | Retention policy dependent |
```

---

## Workflow Coverage Analysis (Required)

Include a coverage section showing which job map stages are represented by the document.

### Coverage Table Format

```markdown
## Workflow Coverage

| Stage | Coverage | Jobs | Notes |
|-------|----------|------|-------|
| Get Started | ✅ | Job 1 | Initial setup, onboarding |
| Plan | ✅ | Job 2 | Platform selection, evaluation |
| Configure | ✅ | Jobs 3, 4, 5 | Prerequisites and configuration |
| Deploy | ✅ | Jobs 6, 7, 8 | Core deployment procedures |
| Monitor | ❌ | - | No observability content |
| Troubleshoot | ⚠️ Limited | Job 9 (partial) | Only basic troubleshooting |
| Upgrade | ❌ | - | No upgrade content |
| Reference | ✅ | Job 10 | API and CLI reference |
```

### Gap Identification

Always include a "Gaps Identified" subsection:

```markdown
### Gaps Identified

| Stage | Gap | Recommendation |
|-------|-----|----------------|
| Monitor | No observability | Link to monitoring guide or add basic checks |
| Upgrade | No upgrade procedures | Add version upgrade section |
| Migrate | No migration content | Add "Migrating from/to" section if applicable |
```

### Coverage Indicators

| Symbol | Meaning |
|--------|---------|
| ✅ | Stage fully covered with dedicated jobs |
| ⚠️ Limited | Partial coverage, some content exists |
| ❌ | Stage not covered, gap identified |

---

## Quality Checklist

### Structure
- [ ] Main jobs are ~10-15 (not 30+)
- [ ] Job numbers are SEQUENTIAL (1, 2, 3, 4...) - no skips, no backwards jumps
- [ ] Jobs organized by workflow stage order (Get Started first, Reference last)
- [ ] NO "DEFINE:", "EXECUTE:", "MONITOR:" in section headings

### 3-Tier Hierarchy
- [ ] Jobs contain themed user stories/goals (not flat task lists)
- [ ] Each user story has a **Goal:** statement
- [ ] Tasks are labeled with **Task:** prefix
- [ ] Verification is a final step within execution jobs, NOT a sibling job

### Job Titles
- [ ] Clean, professional (not fragments)
- [ ] Outcome-focused (Deploy a Model, not Deployment Features)
- [ ] Stable/timeless (would exist if tech changes)
- [ ] Consistent format ([Verb] + [Object])

### Content
- [ ] Prerequisites shown for jobs that need them
- [ ] Related jobs linked (next steps)
- [ ] Platform/persona variations clear
- [ ] Line references use `→ Lines X-Y: Section Title` format
- [ ] Decision matrices included (when multiple methods exist)
- [ ] Workflow coverage section with ✅/❌ indicators

### Navigation
- [ ] Quick navigation section included
- [ ] User journeys shown
- [ ] Cross-references between jobs work
- [ ] Can find content in 2-3 clicks

### Job vs Task Validation
- [ ] Each Level 1 heading passes "Why?" test
- [ ] No tool-specific headings at Level 1
- [ ] Tasks are nested under Jobs, not promoted to Level 1

### Sequencing & Prerequisites
- [ ] Jobs with temporal constraints have **Timing:** line
- [ ] Irreversible actions are flagged with consequence
- [ ] Day 2 operations are marked as such
- [ ] **Most jobs have NO enrichment** - only add where data explicitly supports it

---

## Consolidation Rules

**Multiple sections with similar verbs/stages = ONE main job**

**Example:**
- "View performance metrics" (2.5.1)
- "View runtime metrics" (2.5.2)
- "View NIM metrics" (3.2)
- "View server metrics" (4.9)

**All Monitor stage, all viewing metrics -> ONE job:**
"Job 6: Monitor Model Performance" with 4 user stories

---

## Common Mistakes to Avoid

- **Too many main jobs** (>20) - Most are probably user stories
- **Job title fragments** - "Use the multi-model" instead of "Choose Platform"
- **Feature-based titles** - "Single-model platform features" instead of "Deploy with dedicated servers"
- **Wrong granularity** - Treating user stories as main jobs
- **Poor ordering** - Not following workflow sequence
- **No consolidation** - Same job appearing multiple times
- **Stage labels in headings** - Using "DEFINE:", "EXECUTE:", etc.
