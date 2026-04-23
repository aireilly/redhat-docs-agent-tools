# Step Result Sidecar Schema

Workflow steps write a `step-result.json` file alongside their primary output. The orchestrator and downstream scripts use this sidecar to read structured metadata without parsing markdown.

## Common fields

All sidecars share these fields:

```json
{
  "schema_version": 1,
  "step": "<step-name>",
  "ticket": "<TICKET>",
  "completed_at": "<ISO 8601>"
}
```

| Field | Type | Description |
|---|---|---|
| `schema_version` | integer | Always `1`. Bump when the schema changes incompatibly |
| `step` | string | Step name matching the YAML step list (e.g., `"requirements"`) |
| `ticket` | string | JIRA ticket ID as provided by the user (preserves original case) |
| `completed_at` | string | ISO 8601 timestamp of when the step finished |

## Per-step extensions

### requirements

```json
{
  "schema_version": 1,
  "step": "requirements",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T14:30:00Z",
  "title": "Add installation guide for the Operator"
}
```

| Field | Type | Description | Consumed by |
|---|---|---|---|
| `title` | string | First heading from requirements.md (max 80 chars, ticket prefix stripped) | `create_mr.sh` — PR/MR title |

### planning

```json
{
  "schema_version": 1,
  "step": "planning",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T14:45:00Z",
  "module_count": 5
}
```

| Field | Type | Description | Consumed by |
|---|---|---|---|
| `module_count` | integer | Number of documentation modules in the plan | Informational (orchestrator summary) |

### prepare-branch

```json
{
  "schema_version": 1,
  "step": "prepare-branch",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T14:50:00Z",
  "branch": "proj-123",
  "based_on": "upstream/main",
  "skipped": false,
  "skip_reason": null
}
```

When skipped:

```json
{
  "schema_version": 1,
  "step": "prepare-branch",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T14:50:00Z",
  "branch": null,
  "based_on": null,
  "skipped": true,
  "skip_reason": "draft"
}
```

| Field | Type | Description | Consumed by |
|---|---|---|---|
| `branch` | string\|null | Branch name created (null when skipped) | Orchestrator |
| `based_on` | string\|null | Remote/branch ref used as base (null when skipped) | Orchestrator |
| `skipped` | boolean | Whether branch creation was skipped | Orchestrator |
| `skip_reason` | string\|null | `"draft"` or `"repo-path"` when skipped | Orchestrator |

### writing

```json
{
  "schema_version": 1,
  "step": "writing",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T15:10:00Z",
  "files": [
    "/home/user/docs-repo/modules/proc-installing-operator.adoc",
    "/home/user/docs-repo/modules/con-operator-overview.adoc",
    "/home/user/docs-repo/assemblies/assembly-operator-guide.adoc"
  ],
  "mode": "update-in-place",
  "format": "adoc"
}
```

| Field | Type | Description | Consumed by |
|---|---|---|---|
| `files` | string[] | Absolute paths of all files written or modified | `commit.sh` — file staging |
| `mode` | string | `"update-in-place"`, `"draft"`, or `"fix"` | Informational |
| `format` | string | `"adoc"` or `"mkdocs"` | Informational |

### technical-review

```json
{
  "schema_version": 1,
  "step": "technical-review",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T15:30:00Z",
  "confidence": "MEDIUM",
  "severity_counts": {
    "critical": 0,
    "significant": 0,
    "minor": 3,
    "sme": 2
  },
  "iteration": 1
}
```

| Field | Type | Description | Consumed by |
|---|---|---|---|
| `confidence` | string | `"HIGH"`, `"MEDIUM"`, or `"LOW"` | Orchestrator — iteration logic |
| `severity_counts` | object | Issue counts by severity level | Orchestrator — iteration logic |
| `severity_counts.critical` | integer | Critical issues found | Orchestrator |
| `severity_counts.significant` | integer | Significant issues found | Orchestrator |
| `severity_counts.minor` | integer | Minor issues found | Orchestrator |
| `severity_counts.sme` | integer | Issues requiring SME verification | Orchestrator |
| `iteration` | integer | Which iteration of review this represents (1-based) | Orchestrator |

### style-review

```json
{
  "schema_version": 1,
  "step": "style-review",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T15:45:00Z"
}
```

No extra fields. Common schema only.

## Backward compatibility

Downstream consumers use a sidecar-first pattern: read from `step-result.json` when present, fall back to parsing the markdown output when absent. This ensures in-flight workflows from before sidecar adoption continue to work.
