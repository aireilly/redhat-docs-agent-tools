# JTBD Extraction Methodology

## Purpose

Provide consistent guidance for extracting Jobs to be Done (JTBD) from technical documentation. Focus on Ulwick's Outcome-Driven Innovation (ODI) framing while acknowledging complementary JTBD literature.

## Canonical References

- Tony Ulwick, "Jobs-to-be-Done: A Framework for Customer Needs" (ODI)
- Anthony Ulwick & Lance Bettencourt, "The Customer-Centered Innovation Map" (job map)
- Clayton Christensen, Taddy Hall, Karen Dillon, David S. Duncan, "Competing Against Luck" (HBR Press, 2016)
- Bob Moesta & Chris Spiek, "Demand-Side Sales" / Re-Wired Group resources (JTBD interview technique)

---

## JTBD Definitions

| Term | Definition | Example |
|------|------------|---------|
| **Core functional job** | The primary process the actor wants to accomplish | "Stand up a governed model registry" |
| **Related jobs** | Adjacent tasks performed before/after the core job | "Configure storage classes" |
| **Consumption chain jobs** | Installation, maintenance, upgrade, decommission activities | "Install operator", "Upgrade cluster" |
| **Emotional/social jobs** | How users want to feel or be perceived | "Feel confident in compliance audits" |
| **Desired outcomes** | Measurable statements tied to each job step (direction + metric + qualifier) | "Minimize the time required to validate registry readiness" |

---

## Job Statement Format

Every job must be phrased as:

```
When [situation], I want to [motivation], so I can [expected outcome]
```

**Examples:**
- "When promoting a model to production, I want to register the new version with full lineage, so I can prove compliance and enable reuse."
- "When deploying large language models, I want dedicated model servers with independent scaling, so I can ensure adequate resources and monitor each deployment separately."

---

## Output Requirements

For each significant section of a document, extract:

| Field | Description | Required |
|-------|-------------|----------|
| `doc` | Source document filename | Yes |
| `section` | Section name/heading from source | Yes |
| `job_statement` | Job statement in When/Want/So format | Yes |
| `job_type` | core / related / consumption / emotional | Yes |
| `persona` | Primary persona/actor for this job | Yes |
| `job_map_stage` | One of the 8 stages (see below) | Yes |
| `granularity` | main_job / user_story / procedure | Yes |
| `parent_job` | Name of parent main job (for user stories) | If user_story |
| `prerequisites` | Jobs that must be completed first | Yes (can be empty) |
| `related_jobs` | Connected jobs (not prerequisites) | Yes (can be empty) |
| `desired_outcomes` | ODI-style outcome statements | Yes |
| `evidence` | Source reference with line numbers | Yes |
| `notes` | Gaps, assumptions, additional context | Optional |

---

## Extraction Process

### Step 1: Identify Actors

Identify the key personas/actors from the documentation content. Look for clues in:

- **Role-specific language**: "as an administrator", "cluster admin", "developer", "operator"
- **Permission levels**: Actions requiring elevated privileges vs end-user actions
- **Workflow context**: Who initiates vs who consumes the outcome
- **Skill indicators**: CLI-heavy sections (ops/platform roles) vs UI/notebook sections (end-user roles)

Extract persona names directly from the documentation. Common patterns include:

| Signal | Likely Persona Type | Example Indicators |
|--------|--------------------|--------------------|
| Infrastructure & security tasks | Platform/Admin role | "cluster admin", "configure", "install", "RBAC" |
| Development & experimentation | Developer/End-user role | "notebook", "experiment", "create", "build" |
| Automation & lifecycle management | Ops/Automation role | "pipeline", "automate", "deploy", "CI/CD" |
| Integration & application building | Application builder role | "application", "integrate", "API", "endpoint" |

> **Note:** If a `--research` config is provided, it supplies domain-specific persona definitions (names, archetypes, pain points) that override these generic patterns. Without `--research`, derive personas from the documentation itself.

### Step 2: Map Job Steps (Job Map)

Identify which stage of the job map each section represents:

| Stage | Purpose | Verbs to Look For |
|-------|---------|-------------------|
| **Define** | Determine what outcome is needed | understand, choose, select, decide, compare, evaluate |
| **Locate** | Find resources, identify components | find, access, identify, discover, search |
| **Prepare** | Set up, configure, install, enable | set up, configure, install, enable, create, upload, build |
| **Confirm** | Verify, validate, ensure readiness | verify, validate, check, ensure, test, confirm |
| **Execute** | The main action - deploy, train, build | deploy, run, train, serve, build, generate, perform |
| **Monitor** | Track, observe, measure performance | monitor, track, observe, view, measure, watch |
| **Modify** | Optimize, adjust, tune, troubleshoot | optimize, adjust, tune, customize, update, troubleshoot |
| **Conclude** | Clean up, remove, archive, decommission | clean up, remove, delete, decommission, archive |

### Step 3: Identify Prerequisites

Look for:
- "Prerequisites" sections in the documentation
- Phrases like "before you can", "first you must", "requires"
- List jobs that must be completed first (use job descriptions, not section names)
- If no prerequisites, use empty array: `"prerequisites": []`

### Step 4: Identify Related Jobs

Look for:
- Cross-references to other sections
- Jobs mentioned in the same workflow
- "See also" or "Additional resources" links
- List connected jobs (use job descriptions)
- If none, use empty array: `"related_jobs": []`

### Step 5: Parse Text Structure

- Use headings from Markdown (# through ######) to segment
- Skip boilerplate: Legal Notice, Feedback, Additional Resources, Copyright
- For fallback Markdown lacking headings, look for capitalized sentences or enumerations

### Step 6: Extract Job Statements

- Focus on **outcomes**, not implementation instructions
- Rephrase solution-centric sentences into job language:
  - BAD: "Configure ResourceQuota for GPU management"
  - GOOD: "Ensure GPU quotas prevent noisy neighbors"

### Step 7: Capture Desired Outcomes

Look for adverbs/adjectives indicating metrics:
- faster, reliable, minimize, reduce, ensure, prevent, avoid

Convert to ODI format:
- "Minimize time to ..."
- "Reduce likelihood of ..."
- "Ensure the promoted version is discoverable by ..."

### Step 8: Record Evidence

**ALWAYS include:**
- Document name
- Section heading
- Line numbers (e.g., "lines 133-156")
- Key quotes for context

---

## Granularity Levels (CRITICAL)

### Level 1: `main_job` (~10-15 per guide)

Main jobs are:
- **Stable over time** (won't change even as tech evolves)
- **Outcome-focused** (what user wants to accomplish)
- **Persona-agnostic** (different personas do it differently, but it's the same job)
- **High-level goal** (not implementation details)

**Examples of MAIN jobs:**
- "Deploy a model" (stable goal)
- "Monitor model performance" (stable goal)
- "Store a model" (stable goal)

**NOT main jobs:**
- "Deploy via UI wizard" <- This is a USER STORY
- "View dashboard metrics" <- This is a USER STORY
- "Upload to PVC" <- This is a USER STORY

### Level 2: `user_story` (2-7 per main job)

User stories are:
- **Implementation-specific** (UI vs CLI, Dashboard vs Prometheus)
- **Persona-specific** (Data Scientist approach vs Platform Engineer approach)
- **Technology/tool-specific** (uses specific UI, API, or tool)
- **A way to accomplish the main job**

**Examples of USER STORIES:**
- "As Data Scientist, deploy via UI wizard" (way to deploy)
- "As Platform Engineer, deploy via CLI" (way to deploy)
- "As SRE, query Prometheus metrics" (way to monitor)

**Required fields:**
```json
{
  "granularity": "user_story",
  "parent_job": "Deploy a model",
  "persona": "Data scientist"
}
```

### Level 3: `procedure` (reference only)

Procedures are:
- Pure instructions (no job, just steps)
- Reference material (endpoint lists, configuration examples)
- No standalone value (must be part of a user story)

**DON'T create JTBD records for:**
- Lists of endpoints
- Pure procedural steps with no context
- Configuration file examples

---

## Job vs Task Validation (CRITICAL)

Before marking any record as `main_job`, apply the "Why vs How" Ladder test.

### The Ladder Technique

| Direction | Question | Result |
|-----------|----------|--------|
| UP (Why?) | "Why would someone do this?" | Moves toward Job/Outcome |
| DOWN (How?) | "How would someone do this?" | Moves toward Task/Implementation |

### Validation Rule

For each proposed `main_job`, ask "Why would someone do this?"

- If answer is **another user goal** -> This is a TASK, ladder UP to find the real job
- If answer is **business value/outcome** -> This is a JOB, keep it as main_job

### Example: Task Detection

```
Proposed main_job: "Configure vLLM server arguments"
 Why? -> "To optimize inference performance"
 Why? -> "To reduce latency and costs" (business value)

Result: "Configure vLLM server arguments" is a TASK
Correct main_job: "Optimize Model Inference Performance"
The original becomes a user_story under this main_job.
```

### Example: Job Confirmation

```
Proposed main_job: "Deploy a Model"
 Why? -> "To make predictions available to applications" (business value)

Result: "Deploy a Model" is a JOB
```

### Red Flags (Likely Tasks, NOT main_jobs)

- Mentions specific tools: "Configure Prometheus", "Use vLLM", "Set up Grafana"
- Mentions specific UI elements: "Click Deploy button", "Use the wizard"
- Very narrow scope: "Set memory limits", "Configure TLS certificate"
- Implementation-focused verbs with specific objects: "Configure server arguments"

### Green Flags (Likely main_jobs)

- Outcome-focused: "Monitor Performance", "Deploy Model", "Store Model"
- Tool-agnostic: Would exist even if technology changes
- Business value: "Reduce inference latency", "Ensure model availability"
- Stable verbs with broad objects: "Choose", "Deploy", "Monitor", "Optimize"

---

## Verb Classification Guide

| Verb | Likely Level | Rationale |
|------|--------------|-----------|
| **Choose**, **Select**, **Decide** | main_job | Outcome-focused decision |
| **Deploy**, **Serve**, **Run** | main_job | Core execution goals |
| **Monitor**, **Track**, **Observe** | main_job | Ongoing operational goals |
| **Store**, **Save**, **Persist** | main_job | Data management goals |
| **Optimize**, **Improve**, **Tune** | main_job | Performance goals |
| **Understand**, **Learn** | main_job | Knowledge acquisition goals |
| **Configure**, **Set up** | user_story OR task | Apply "Why?" test |
| **Install**, **Enable** | user_story | Consumption chain activity |
| **Create**, **Build** | user_story OR task | Depends on what's created |
| **Click**, **Select (UI)**, **Enter** | procedure | UI interaction steps |
| **Copy**, **Paste**, **Run command** | procedure | Mechanical steps |

---

## Consolidation Indicators

**Signs that multiple sections are ONE main job with multiple user stories:**

1. Same verb/action across sections (deploy, monitor, store)
2. Same job map stage (all Monitor, all Execute)
3. Same high-level goal but different tools/interfaces
4. Persona variations (Data Scientist vs Admin doing same thing differently)
5. Platform variations (single-model vs multi-model doing same thing)

**Example:**
- Sections 2.5.1, 2.5.2, 3.2, 3.3, 4.8, 4.9, 4.10
- All are Monitor stage
- All have verb "view" or "monitor"
- All serve same goal: track model performance
- **ONE main job:** "Monitor model performance"
- **SEVEN user stories:** Different personas + platforms

---

## Quality Checklist

- [ ] Jobs phrased from actor's perspective, not product's features
- [ ] Each job linked to at least one measurable desired outcome
- [ ] Personas and job types are explicit
- [ ] job_map_stage is one of the 8 stages
- [ ] granularity is correctly identified
- [ ] parent_job is set for user stories
- [ ] prerequisites array is present (can be empty)
- [ ] related_jobs array is present (can be empty)
- [ ] evidence includes line numbers
- [ ] Notes call out gaps (e.g., "No emotional jobs stated")
- [ ] **~10-15 main_jobs maximum per guide** (if more, likely misclassified user_stories)

---

## Pre-Submission Validation

- [ ] Each `main_job` passes the "Why?" ladder test
- [ ] Ambiguous verbs (configure, set up, create, build) have been ladder-tested
- [ ] No tool-specific main_jobs (vLLM, Prometheus, Grafana, etc.)
- [ ] No UI-specific main_jobs (dashboard, wizard, button, etc.)
- [ ] Tasks are correctly classified as user_story with parent_job set

---

## Optional Enhancements

When applicable:
- Tag jobs with lifecycle stage (Plan / Build / Ship / Run)
- Indicate dependencies (e.g., "Requires enabling registry component first")
- Highlight consumption-chain jobs separately (install, upgrade, decommission)
- Include emotional/social jobs (e.g., "Feel confident in compliance audits")
