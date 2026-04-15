# Batch Controller Reference

## repo-info.json schema

Written by `repo-setup.sh` to `artifacts/<ticket>/repo-info.json`:

| Field | Type | Description |
|-------|------|-------------|
| `ticket` | string | Original ticket key (e.g., `VROOM-123`) |
| `jira_project` | string | Extracted project key (e.g., `VROOM`) |
| `repo_url` | string\|null | Target repo URL, or null if no mapping / clone failed |
| `clone_path` | string | Absolute path to local clone (under `.work/`) |
| `branch` | string | Feature branch name (lowercase ticket key) |
| `platform` | string | `github`, `gitlab`, or `unknown` |
| `default_branch` | string | Target branch for MR/PR (usually `main`) |
| `format` | string | `mkdocs` or `adoc` |

## commit-info.json schema

Written by the `docs-workflow-commit` step skill to `artifacts/<ticket>/commit/commit-info.json`:

| Field | Type | Description |
|-------|------|-------------|
| `branch` | string\|null | Feature branch name |
| `commit_sha` | string\|null | Commit SHA if committed, null if skipped |
| `files_committed` | string[] | List of committed file paths (relative to repo root) |
| `platform` | string\|null | `github`, `gitlab`, or `unknown` |
| `repo_url` | string\|null | Target repo URL |
| `pushed` | boolean | Whether the branch was pushed to remote |
| `skip_reason` | string | Present only for intentional skips (draft mode, no manifest, etc.), absent on push failures |

## mr-info.json schema

Written by the `docs-workflow-create-mr` step skill to `artifacts/<ticket>/create-mr/mr-info.json`:

| Field | Type | Description |
|-------|------|-------------|
| `platform` | string | `github`, `gitlab`, or `unknown` |
| `url` | string\|null | MR/PR URL, or null if skipped |
| `action` | string | `created`, `found_existing`, or `skipped` |
| `title` | string\|null | MR/PR title |

Both commit and MR/PR creation are handled by the orchestrator's workflow steps, not by adapter scripts.

## Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `DOCS_TRIGGER_LABEL` | Label marking tickets for processing | `ambient-docs-ready` |
| `DOCS_PROCESSING_LABEL` | Label added when ticket is claimed | `ambient-docs-processing` |
| `DOCS_DONE_LABEL` | Label added after success | `ambient-docs-generated` |
| `DOCS_FAILED_LABEL` | Label added after failure | `ambient-docs-failed` |
| `DOCS_JIRA_PROJECT` | Limit to specific JIRA project | — |

## Batch summary format

Write to `artifacts/batch-summary.md`:

```markdown
# Batch Summary

**Date**: YYYY-MM-DD HH:MM UTC
**Tickets processed**: N
**Successful**: X
**Failed**: Y

## Results

| Ticket | Status | Output Path | MR/PR | Notes |
|--------|--------|-------------|-------|-------|
| PROJ-123 | success | artifacts/proj-123/ | <url> | 5 modules written |
| PROJ-456 | failed | — | — | Error: ... |

## Errors

### PROJ-456

<error details>
```
