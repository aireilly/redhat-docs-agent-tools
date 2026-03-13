# JTBD TOC Comparison Guidelines

## Purpose

Generate high-quality side-by-side comparisons of current (feature-based) vs. proposed (JTBD-based) documentation structures.

---

## CRITICAL: Job-Based Design Principles

**Modern AI teams have fluid roles.** The same person may complete jobs belonging to multiple personas (e.g., a developer doing platform engineering tasks).

### Core Principle

**Focus on the JOB to be done, NOT the job title or persona.**

### Key Rules

1. **Jobs describe WHAT needs to be done** (not WHO does it)
   - "Configure Gateway for llm-d"
   - NOT: "For Administrators: Configure Gateway"

2. **Personas are context, NOT gates**
   - "Context: Requires cluster admin permissions"
   - NOT: "For Cluster Administrators only"

3. **Prerequisites are permissions, NOT personas**
   - "Prerequisites: Cluster administrator permissions, oc CLI access"
   - NOT: "Prerequisites: Must be a Cluster Administrator"

4. **Organize by workflow stage internally, use descriptive headings externally**
   - Internal ordering: Get Started -> Plan -> Configure -> Deploy -> Monitor -> Troubleshoot -> Reference
   - Output headings: "Getting Started", "Choose Your Approach", "Set Up & Configure", "Deploy & Use"
   - NOT: "GET STARTED:", "DEPLOY:", "MONITOR:"

5. **No persona prefixes on tasks**
   - "Deploy Model via UI Wizard"
   - NOT: "For Data Scientists: Deploy Model via UI"

6. **Use "Context:" for scenario guidance**
   - "Context: UI method simpler for most users; CLI for automation"
   - NOT: "For UI users" / "For advanced users"

---

## Output Structure

### 1. Header & Metadata

```markdown
# [Document Name] - TOC Comparison

**Current Feature-Based vs. Proposed JTBD-Based Structure**

**Analysis Date:** [Date]
**JTBD Records:** X
**Main Jobs:** Y (rolled up from records)
**Coverage:** Z% enhanced schema
```

### 2. Current Structure

Extract and display the current feature-based TOC:

```markdown
## Current Structure (Feature-Based)

[Document Name]
 - Chapter 1: [Feature/Platform Name]
   - Section 1.1: [Feature Detail]
   - Section 1.2: [Feature Detail]
 - Chapter 2: [Another Feature/Platform]
    ...
```

### 3. Proposed JTBD Structure

**CRITICAL:** Use proper granularity (3 levels):

**Level 1: Main Jobs** (~10-15 total)
- Stable, outcome-focused goals
- Organize by domain taxonomy stages (Get Started, Configure, Deploy, Monitor, etc.)
- Clean, professional titles

**Level 2: User Stories** (nest under main jobs)
- Persona-specific implementation paths
- Platform/tool variations
- "For [Persona]: [Approach]" format OR "Option A/B/C" format

**Level 3: Procedures** (reference to source)
- Line numbers from evidence field
- Brief description of steps

**Template (use descriptive headings, NOT stage names):**

```markdown
## Proposed JTBD-Based Structure

## Choose Your Approach

Job 1: [Clean Main Job Title]
  When: [Situation from job statements]
  Personas: [All personas who do this job]

  [Organize user stories by persona or option]

  - Option A: [Approach Name]
    Persona: [Specific persona]
    → Lines X-Y: Section Name
    Source: Chapter X, Section X.X
    - [Key benefit]
    - [Key benefit]

  - Option B: [Alternative Approach]
    Persona: [Different persona]
    → Lines A-B: Section Name
    Source: Chapter X, Section X.X

## Set Up & Configure

Job 2: [Next Main Job]
  ...

[Continue through all workflow phases]
```

### 4. Key Differences Section

```markdown
## Key Differences

### Current Structure (Feature-Based)
**Organized By:** Features, platforms, technical components
**Navigation:** X sections/chapters
**User Journey:** Linear reading, chapter by chapter

### Proposed Structure (JTBD-Based)
**Organized By:** Job map stages, user goals
**Navigation:** Y main jobs with persona paths
**User Journey:** Goal-directed, choose your path
```

### 5. Hierarchy Levels Explanation

Explain the 3 levels:
- Main Jobs (stable goals)
- User Stories (persona approaches)
- Procedures (step-by-step)

### 6. Example Consolidation

Show one concrete example:

```markdown
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

### 7. Navigation Improvement Metrics

Quantify the improvement:

```markdown
## Navigation Improvement

**Current:** Browse X sections to find content
**Proposed:** Navigate Y main jobs -> choose persona path
**Reduction:** Z% fewer top-level items
**Benefit:** Find content in 2-3 clicks vs 5-10
```

### 8. Workflow Coverage Comparison (Required)

Compare workflow stage coverage between current and proposed structures:

```markdown
## Workflow Coverage Comparison

| Stage | Current | Proposed | Gap Status |
|-------|---------|----------|------------|
| Get Started | ⚠️ Scattered | ✅ Job 1 | Improved |
| Plan | ❌ Missing | ✅ Job 2 | Added |
| Configure | ✅ Chapter 2 | ✅ Jobs 3, 4, 5 | Reorganized |
| Deploy | ✅ Chapters 3-5 | ✅ Jobs 6, 7, 8 | Consolidated |
| Monitor | ❌ Missing | ❌ Missing | Gap remains |
| Troubleshoot | ⚠️ Appendix only | ✅ Job 9 | Elevated |
| Upgrade | ❌ Missing | ❌ Missing | Gap remains |
| Reference | ✅ Appendix | ✅ Job 10 | Reorganized |

### Coverage Summary

**Current structure gaps:** Plan, Monitor, Upgrade
**Proposed structure gaps:** Monitor, Upgrade
**Gaps addressed by restructure:** Plan (now covered)

### Recommendations for Gap Closure

| Gap | Recommendation | Priority |
|-----|----------------|----------|
| Monitor | Link to observability guide or add basic checks | High |
| Upgrade | Add version upgrade procedures | Medium |
| Migrate | Add migration content if applicable | Low |
```

### Coverage Indicators

| Symbol | Meaning |
|--------|---------|
| ✅ | Stage fully covered with dedicated content |
| ⚠️ | Partial coverage - content exists but scattered or limited |
| ❌ | Stage not covered - content gap identified |

### 9. Research Insights (when research fields available)

If JTBD records include research extension fields, add this section:

```markdown
## UX Research Alignment

### Pain Points Addressed by Restructure

| Pain Point (from analysis) | How New Structure Helps |
|---------------------------|------------------------|
| "Complex YAML configuration with many fields" | Task 3.1-3.6 breaks monolithic config into discrete, navigable sections |
| "Multiple environment variables for different tools" | Task 3.4 consolidates all SSL/TLS variables in one place |
| "Must coordinate multiple resources" | Prerequisites chain explicitly links Jobs 2 -> 3 -> 4 |

### Strategic Priorities Elevated

The following jobs are flagged as **strategic priorities** in UX research. The new structure gives them dedicated sections:

| Strategic Job | Current Location | Proposed Location | Visibility Improvement |
|--------------|-----------------|-------------------|----------------------|
| OAuth Configuration | Buried at line 380 in 1100-line procedure | Job 3.2: Dedicated section | Direct navigation |
| SSL/TLS Configuration | Buried at line 440 | Job 3.4: Dedicated section | Direct navigation |

### Cross-Team Collaboration Visibility

The new structure makes team collaboration patterns visible:

| Job | Teams Involved | Benefit |
|-----|---------------|---------|
| Create Custom Image | Platform Team, Data Science Team | Clear handoff: Platform creates, DS uses |
| Configure OAuth | Platform Team, Security Team | Security requirements visible in structure |
| Configure SSL/TLS | Platform Team, Security Team | Compliance requirements findable |

### Inner/Outer Loop Distribution (if applicable)

| Loop | Jobs | Implication |
|------|------|-------------|
| Outer (Production/Ops) | Jobs 1-4 (workbench provisioning) | Platform Engineer focus |
| Inner (Dev/Experimentation) | N/A in this guide | Data Scientist focus elsewhere |
```

**Note:** Only include this section if research extension fields are populated in the JTBD records.

---

## Main Job Title Guidelines

**Create clean, professional titles:**

### Good Main Job Titles

- "Choose Model Serving Platform"
- "Configure Serving Runtime"
- "Deploy a Model"
- "Monitor Model Performance"
- "Store Your Model"
- "Make Inference Requests"
- "Update Model Configuration"
- "Remove Deployed Models"

### Bad Titles (Auto-Generated)

- "Use the multi-model" <- Fragment
- "View metrics in dashboard" <- Too specific (user story, not main job)
- "Deploy via UI wizard" <- Implementation detail (user story)
- "Know the correct endpoint" <- Fragment
- "Using OCI containers for model storage" <- Uses initials that may be unknown

**Formula:** [Verb] + [Object/Outcome]

---

## User Story Guidelines

**Format:** "For [Persona]: [Approach]" or "Option [X]: [Method]"

### Good User Stories

- "For Data Scientist: Deploy via UI wizard"
- "For Platform Engineer: Deploy via CLI with YAML"
- "Option A: Store in OCI containers (for performance)"
- "Option B: Upload to PVC (for simplicity)"

### Persona-Based Grouping

When same job has multiple persona approaches:

```markdown
Job: Deploy a Model

  - For Data Scientists: UI Wizard
    → Lines 338-422: Deploy via dashboard
    Source: Chapter 2, Section 2.2

  - For Platform Engineers: CLI with YAML
    → Lines 423-586: CLI deployment procedure
    Source: Chapter 2, Section 2.3

  - For Advanced Users: Distributed Inference
    → Lines 587-720: Distributed inference setup
    Source: Chapter 2, Section 2.4
```

### Option-Based Grouping

When same job has multiple technical approaches:

```markdown
Job: Store Your Model

  - Option A: OCI Containers (scale & performance)
    → Lines 133-252: OCI container storage
    Source: Chapter 1, Sections 1.1-1.2

  - Option B: PVC Upload (simplicity)
    → Lines 252-320: PVC upload procedure
    Source: Chapter 1, Section 1.3

  - Option C: S3 Bucket (not detailed in this guide)
```

---

## Workflow Order Guidelines

**Order jobs by when users need them (but use descriptive headings):**

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

**Within each section:** Order by prerequisites
- Configure platform BEFORE deploy model
- Store model BEFORE deploy model
- Deploy model BEFORE monitor model

---

## UI and CLI Path Documentation

**When generating comparisons, document both UI and CLI methods where they exist:**

### Format

```markdown
**[Task Name]**
- **UI Path:** Navigation -> Path -> To -> Feature
  - Step-by-step instructions
  - (Screenshot reference if available)
- **CLI Path:** `command examples`
- **Context:** When to use UI vs CLI
```

### Examples

**Good (Both Paths):**
```markdown
**Annotate Authorino Service**
- **UI Path:** Networking -> Services -> Edit annotations
  - Key: service.beta.openshift.io/serving-cert-secret-name
  - Value: authorino-server-cert
  - (See Screenshot 4)
- **CLI Path:** `oc annotate svc/authorino...`
- **Context:** UI method essential for non-CLI administrators
```

**Good (CLI Only):**
```markdown
**Create Namespace**
- **CLI Path:** `oc create namespace kuadrant-system`
- **Context:** Command-line task, no UI alternative needed
```

---

## Gap Marking Conventions

**When content is missing from source documentation:**

### Mark with Warning Indicator

```markdown
### Job X: Configure Cluster Prerequisites [GAP]

**Note:** [GAP] This content is missing from current [document].md.
Source: [Other-document].md lines X-Y.

**Task Name** [GAP]
- **Gap:** Complete procedure missing from [document].md
- **Source:** [Other-document].md lines X-Y
```

### Gap Information to Include

- [GAP] visual indicator
- Note explaining what's missing
- Source document and line references
- Screenshot references if applicable

---

## Quality Checklist

### Main Jobs
- [ ] 10-15 main jobs total (not 30+)
- [ ] Clean, professional titles (not fragments)
- [ ] Outcome-focused (not feature-focused)
- [ ] Stable goals (would exist even if tech changed)
- [ ] Organized by domain taxonomy stages

### User Stories/Tasks
- [ ] 2-7 per main job (not standalone jobs)
- [ ] Scenario-specific or approach-based
- [ ] Implementation details, not goals
- [ ] Properly nested under main jobs
- [ ] NO "For [Persona]:" prefixes that gate content
- [ ] Use "Context:" to explain when/why to use each approach

### Structure
- [ ] Follows domain taxonomy stage progression
- [ ] Jobs ordered by workflow/prerequisites
- [ ] Line references use `→ Lines X-Y: Title` format with `Source:` line
- [ ] Prerequisites stated as permissions, not personas
- [ ] Both UI and CLI paths documented where applicable
- [ ] Gap markers for missing content

### Comparison
- [ ] Current structure shown accurately
- [ ] Proposed structure is logical
- [ ] Key differences explained
- [ ] Navigation improvements quantified
- [ ] Workflow coverage comparison with ✅/⚠️/❌ indicators
- [ ] Gap recommendations with priorities

### Research Alignment (when --research flag used)
- [ ] Pain points from records mapped to structural improvements
- [ ] Strategic priority jobs highlighted with elevated visibility
- [ ] Cross-team collaboration patterns surfaced
- [ ] Inner/outer loop distribution shown if relevant

---

## Common Mistakes to Avoid

- **Too many main jobs** (>20) - Most are probably user stories
- **Job title fragments** - "Use the multi-model" instead of "Choose Platform"
- **Feature-based titles** - "Single-model platform features" instead of "Deploy with dedicated servers"
- **Wrong granularity** - Treating user stories as main jobs
- **Poor ordering** - Not following workflow sequence
- **Persona gates** - "For Administrators:" prefixes that restrict perceived access
- **No consolidation** - Same job appearing multiple times
- **Prerequisites as personas** - "Must be admin" instead of "Cluster admin permissions required"
- **Missing UI paths** - Only showing CLI when UI alternative exists
- **Role-based organization** - Grouping by "Beginner/Advanced" or role hierarchy
- **Stage labels in headings** - Using "DEFINE:", "EXECUTE:", "MONITOR:"
- **Ignoring research fields** - When pain_points/strategic_priority available, not connecting to structure
- **Generic justifications** - Saying "better navigation" without citing specific pain points being addressed

---

## Success Criteria

**A good TOC comparison:**

- User can immediately see main goals (main jobs)
- User can find jobs by what they need to accomplish, not by their role
- User can see it's simpler than current structure
- Stakeholders understand the proposed improvement
- Content mappers know what to extract from where
- Structure follows natural workflow progression
- No persona gates - anyone can complete any job based on permissions
- Both UI and CLI paths documented where applicable
- Prerequisites stated as permissions, not job titles
- Gaps clearly marked with source references

**When research fields available:**

- Pain points explicitly connected to structural improvements
- Strategic priorities given visible, dedicated sections
- Cross-team collaboration patterns made visible in structure
- Research-backed justification for proposed changes
