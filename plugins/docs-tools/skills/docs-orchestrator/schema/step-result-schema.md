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
| `title` | string | First heading from requirements.md (max 80 chars, ticket prefix stripped) | `create_mr.py` — PR/MR title |

### scope-req-audit

```json
{
  "schema_version": 1,
  "step": "scope-req-audit",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T14:35:00Z",
  "recommendation": "proceed",
  "grounded": 6,
  "partial": 2,
  "absent": 1,
  "total": 9,
  "discovered_repos_count": 2
}
```

| Field | Type | Description | Consumed by |
|---|---|---|---|
| `recommendation` | string | `"proceed"`, `"gather-more"`, or `"review-needed"` | Orchestrator — post-step logging |
| `grounded` | integer | Requirements with strong code evidence | Orchestrator — post-step logging |
| `partial` | integer | Requirements with weak or ambiguous evidence | Orchestrator — post-step logging |
| `absent` | integer | Requirements with no code evidence | Orchestrator — post-step logging |
| `total` | integer | Total requirements classified | Orchestrator — post-step logging |
| `discovered_repos_count` | integer | Number of related repos found but not indexed | Orchestrator — post-step logging |

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

### code-evidence

```json
{
  "schema_version": 1,
  "step": "code-evidence",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T15:00:00Z",
  "topic_count": 8,
  "snippet_count": 42,
  "repo_path": "/home/user/docs-repo/.claude/docs/proj-123/code-repo/my-project"
}
```

| Field | Type | Description | Consumed by |
|---|---|---|---|
| `topic_count` | integer | Number of search topics extracted from the plan | Informational (orchestrator summary) |
| `snippet_count` | integer | Total code snippets retrieved across all topics (source + context) | Informational (orchestrator summary) |
| `repo_path` | string | Absolute path to the source repository searched | Informational |

### commit

```json
{
  "schema_version": 1,
  "step": "commit",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T16:00:00Z",
  "commit_sha": "abc1234",
  "branch": "proj-123",
  "pushed": true,
  "skipped": false,
  "skip_reason": null
}
```

When skipped (draft mode or no changes):

```json
{
  "schema_version": 1,
  "step": "commit",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T16:00:00Z",
  "commit_sha": null,
  "branch": null,
  "pushed": false,
  "skipped": true,
  "skip_reason": "draft"
}
```

| Field | Type | Description | Consumed by |
|---|---|---|---|
| `commit_sha` | string\|null | Git commit SHA (null when skipped) | Informational |
| `branch` | string\|null | Branch name committed to (null when skipped) | Orchestrator |
| `pushed` | boolean | Whether the branch was pushed to the remote | `create-mr` — skip check |
| `skipped` | boolean | Whether committing was skipped | Orchestrator |
| `skip_reason` | string\|null | `"draft"` or `"no_changes"` when skipped | Orchestrator |

### create-mr

```json
{
  "schema_version": 1,
  "step": "create-mr",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T16:05:00Z",
  "url": "https://github.com/org/repo/pull/42",
  "action": "created",
  "platform": "github",
  "skipped": false,
  "skip_reason": null
}
```

When skipped (draft mode or branch not pushed):

```json
{
  "schema_version": 1,
  "step": "create-mr",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T16:05:00Z",
  "url": null,
  "action": "skipped",
  "platform": "unknown",
  "skipped": true,
  "skip_reason": "draft"
}
```

| Field | Type | Description | Consumed by |
|---|---|---|---|
| `url` | string\|null | MR/PR URL (null when skipped) | Orchestrator (final summary) |
| `action` | string | `"created"`, `"found_existing"`, or `"skipped"` | Orchestrator |
| `platform` | string | `"github"`, `"gitlab"`, or `"unknown"` | Informational |
| `skipped` | boolean | Whether MR/PR creation was skipped | Orchestrator |
| `skip_reason` | string\|null | `"draft"` or `"not_pushed"` when skipped | Orchestrator |

### create-jira

```json
{
  "schema_version": 1,
  "step": "create-jira",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T16:10:00Z",
  "jira_url": "https://redhat.atlassian.net/browse/DOCS-456",
  "jira_key": "DOCS-456",
  "action": "created",
  "skipped": false,
  "skip_reason": null
}
```

When an existing linked ticket is found:

```json
{
  "schema_version": 1,
  "step": "create-jira",
  "ticket": "PROJ-123",
  "completed_at": "2026-04-23T16:10:00Z",
  "jira_url": "https://redhat.atlassian.net/browse/DOCS-456",
  "jira_key": "DOCS-456",
  "action": "found_existing",
  "skipped": false,
  "skip_reason": null
}
```

| Field | Type | Description | Consumed by |
|---|---|---|---|
| `jira_url` | string\|null | URL of the created or found JIRA ticket (null on failure) | Orchestrator (final summary) |
| `jira_key` | string\|null | JIRA issue key (e.g., `DOCS-456`) | Orchestrator |
| `action` | string | `"created"`, `"found_existing"`, or `"skipped"` | Orchestrator |
| `skipped` | boolean | Whether JIRA creation was skipped | Orchestrator |
| `skip_reason` | string\|null | Reason when skipped (e.g., `"existing_link"`) | Orchestrator |

## Backward compatibility

Downstream consumers use a sidecar-first pattern: read from `step-result.json` when present, fall back to parsing the markdown output when absent. This ensures in-flight workflows from before sidecar adoption continue to work.
