# JTBDRecord Schema Reference

This document defines the complete schema for JTBD records. All extracted records must conform to this structure.

## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "JTBDRecord",
  "type": "object",
  "required": ["doc", "section", "job_statement", "job_type", "persona"],
  "properties": {
    "doc": {
      "type": "string",
      "description": "Source document filename"
    },
    "section": {
      "type": "string",
      "description": "Section name/heading from source"
    },
    "source_url": {
      "type": ["string", "null"],
      "description": "Full URL to source section (with anchor if available)"
    },
    "job_statement": {
      "type": "string",
      "description": "Job statement in format: When [situation], I want to [motivation], so I can [outcome]"
    },
    "job_type": {
      "type": "string",
      "enum": ["core", "related", "consumption", "emotional"],
      "description": "Type of job"
    },
    "persona": {
      "type": "string",
      "description": "Primary persona/actor for this job"
    },
    "job_map_stage": {
      "type": "string",
      "enum": [
        "Get Started", "Upgrade", "Develop", "Administer", "Observe",
        "Secure", "Reference", "Extend", "Migrate", "Configure",
        "Troubleshoot", "What's New", "Architecture", "Deploy",
        "Training", "Monitor", "Analyze", "Operate", "Plan", "Unknown"
      ],
      "description": "Internal category for ordering/grouping"
    },
    "granularity": {
      "type": "string",
      "enum": ["main_job", "user_story", "procedure"],
      "description": "Granularity level"
    },
    "parent_job": {
      "type": ["string", "null"],
      "description": "Name of parent main job (for user stories)"
    },
    "prerequisites": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Jobs that must be completed first"
    },
    "related_jobs": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Connected jobs (not prerequisites)"
    },
    "desired_outcomes": {
      "type": "array",
      "items": { "type": "string" },
      "description": "ODI-style outcome statements"
    },
    "evidence": {
      "type": "string",
      "description": "Source reference with line numbers"
    },
    "notes": {
      "type": "string",
      "description": "Additional notes, gaps, or assumptions"
    },
    "loop": {
      "type": ["string", "null"],
      "description": "Inner loop (dev) vs Outer loop (ops) - research extension"
    },
    "genai_phase": {
      "type": ["string", "null"],
      "description": "GenAI workflow phase: development or production - research extension"
    },
    "strategic_priority": {
      "type": ["boolean", "null"],
      "description": "Is this a strategic priority from research? - research extension"
    },
    "pain_points": {
      "type": "array",
      "items": { "type": "string" },
      "description": "User-reported friction points - research extension"
    },
    "teams_involved": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Teams involved in this job - research extension"
    }
  }
}
```

---

## Field Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `doc` | string | Source document filename (e.g., "creating-a-workbench.md") |
| `section` | string | Section name/heading from source (e.g., "Chapter 2: Configuring workbenches") |
| `job_statement` | string | Job statement in "When X, I want Y, so I can Z" format |
| `job_type` | enum | One of: `core`, `related`, `consumption`, `emotional` |
| `persona` | string | Primary persona/actor for this job |

### Classification Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `job_map_stage` | enum | "Unknown" | Internal category for ordering. See stage values below. |
| `granularity` | enum | "user_story" | One of: `main_job`, `user_story`, `procedure` |
| `parent_job` | string/null | null | For user_story: name of the parent main_job |

### Relationship Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prerequisites` | string[] | [] | Jobs that must be completed first |
| `related_jobs` | string[] | [] | Connected jobs (not prerequisites) |

### Outcome Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `desired_outcomes` | string[] | [] | ODI-style outcome statements |

### Evidence Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `evidence` | string | "" | Source reference with line numbers |
| `notes` | string | "" | Gaps, assumptions, additional context |
| `source_url` | string/null | null | Full URL to source section |

### Research Extension Fields

These fields are populated when using the `--research` flag:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `loop` | string/null | null | "inner" (dev/experimentation) or "outer" (production/ops) |
| `genai_phase` | string/null | null | "development" or "production" |
| `strategic_priority` | bool/null | null | Is this job a strategic priority from research? |
| `pain_points` | string[] | [] | User-reported friction points |
| `teams_involved` | string[] | [] | Teams involved in this job |

---

## Job Map Stage Values

The `job_map_stage` field uses a domain taxonomy:

| Stage | When to Use |
|-------|-------------|
| `Get Started` | Initial setup, onboarding, first steps |
| `Upgrade` | Version upgrades, migrations between versions |
| `Develop` | Development workflows, coding, experimentation |
| `Administer` | Administrative tasks, user management |
| `Observe` | Observability, logging, viewing state |
| `Secure` | Security configuration, authentication, authorization |
| `Reference` | Reference material, API docs, glossaries |
| `Extend` | Extensions, plugins, customizations |
| `Migrate` | Data migration, platform migration |
| `Configure` | Configuration, setup, enabling features |
| `Troubleshoot` | Debugging, fixing issues, error resolution |
| `What's New` | Release notes, new features |
| `Architecture` | Architecture decisions, design patterns |
| `Deploy` | Deployment, running, serving |
| `Training` | ML model training |
| `Monitor` | Performance monitoring, metrics, dashboards |
| `Analyze` | Data analysis, exploration |
| `Operate` | Day-2 operations, lifecycle management |
| `Plan` | Planning, evaluation, choosing approaches |
| `Unknown` | Cannot determine stage |

---

## Job Type Values

| Type | Description | Example |
|------|-------------|---------|
| `core` | Primary process the actor wants to accomplish | "Deploy a model" |
| `related` | Adjacent tasks before/after core job | "Configure storage" |
| `consumption` | Installation, maintenance, upgrade, decommission | "Install operator" |
| `emotional` | How users want to feel or be perceived | "Feel confident in audits" |

---

## Granularity Values

| Level | Description | parent_job Required? |
|-------|-------------|---------------------|
| `main_job` | Stable, high-level goal (~10-15 per guide) | No (null) |
| `user_story` | Persona-specific implementation path | Yes |
| `procedure` | Step-by-step instructions (skip or reference) | Yes |

---

## Example Records

### Main Job Example

```json
{
  "doc": "creating-a-workbench.md",
  "section": "Chapter 2: Creating a workbench",
  "job_statement": "When I need a development environment for ML experiments, I want to provision a workbench with appropriate resources, so I can start experimenting without infrastructure delays.",
  "job_type": "core",
  "persona": "Data scientist",
  "job_map_stage": "Configure",
  "granularity": "main_job",
  "parent_job": null,
  "prerequisites": ["Create a project", "Have cluster admin approval for resources"],
  "related_jobs": ["Configure data connections", "Select notebook image"],
  "desired_outcomes": [
    "Minimize time to get a working environment",
    "Reduce likelihood of resource contention",
    "Ensure environment has required libraries"
  ],
  "evidence": "creating-a-workbench.md -> Chapter 2, lines 45-200",
  "notes": "Main job covering workbench provisioning. Multiple user stories for UI vs CLI approaches."
}
```

### User Story Example

```json
{
  "doc": "creating-a-workbench.md",
  "section": "2.1: Creating a workbench using the UI",
  "job_statement": "As a Data Scientist, when I need to create a workbench quickly, I want to use the web interface wizard, so I can provision without CLI expertise.",
  "job_type": "core",
  "persona": "Data scientist",
  "job_map_stage": "Configure",
  "granularity": "user_story",
  "parent_job": "Provision a workbench with appropriate resources",
  "prerequisites": ["Have project access", "Know required resource sizes"],
  "related_jobs": [],
  "desired_outcomes": [
    "Complete workbench creation in under 5 minutes",
    "Avoid configuration errors from typos"
  ],
  "evidence": "creating-a-workbench.md -> Section 2.1, lines 85-150",
  "notes": "UI-based approach, alternative to CLI method in section 2.2"
}
```

### Record with Research Extensions

```json
{
  "doc": "creating-a-workbench.md",
  "section": "Chapter 3: Configuring OAuth",
  "job_statement": "When setting up secure access to workbenches, I want to configure OAuth authentication, so I can ensure only authorized users access my environment.",
  "job_type": "core",
  "persona": "Platform engineer",
  "job_map_stage": "Secure",
  "granularity": "user_story",
  "parent_job": "Provision a workbench with appropriate resources",
  "prerequisites": ["Create workbench", "Have OAuth provider configured"],
  "related_jobs": ["Configure TLS certificates"],
  "desired_outcomes": [
    "Ensure no unauthorized access to notebooks",
    "Minimize friction for legitimate users"
  ],
  "evidence": "creating-a-workbench.md -> Chapter 3, lines 320-380",
  "notes": "Security configuration, marked as strategic priority",
  "loop": "outer",
  "genai_phase": "production",
  "strategic_priority": true,
  "pain_points": ["OAuth configuration is complex", "Multiple annotation options confusing"],
  "teams_involved": ["Platform Team", "Security Team"]
}
```

---

## JSONL Output Format

Records are saved as JSON Lines (one record per line):

```jsonl
{"doc":"creating-a-workbench.md","section":"Chapter 2","job_statement":"When I need...","job_type":"core",...}
{"doc":"creating-a-workbench.md","section":"Section 2.1","job_statement":"As a Data Scientist...","job_type":"core",...}
{"doc":"creating-a-workbench.md","section":"Section 2.2","job_statement":"As a Platform Engineer...","job_type":"core",...}
```

---

## Validation Rules

1. **Required fields** must be present and non-empty
2. **job_statement** must follow "When X, I want Y, so I can Z" format
3. **granularity** must be one of the valid enum values
4. **parent_job** must be set for `user_story` and `procedure` records
5. **job_map_stage** should not be "Unknown" for final outputs
6. **prerequisites** and **related_jobs** should use job descriptions, not section names
7. **evidence** should include line numbers when available
