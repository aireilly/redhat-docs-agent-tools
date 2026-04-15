# Headless Documentation Pipeline

Scheduled, autonomous documentation pipeline for the Ambient Code Platform.

## Autonomy rules

- **No user interaction.** Never prompt for input, confirmation, or approval.
- **Auto-advance.** Move through all workflow stages without pausing.
- **Error isolation.** If a ticket fails, log the error and continue to the next ticket.
- **Batch completion.** Always write a batch summary before session ends.

## Hard limits

- **No content fabrication.** If JIRA or source access fails, mark the ticket as failed and move on.
- **Git operations are scoped.** Git operations are restricted to the target docs repo specified in `repo-mapping.yaml`. The pipeline clones, branches, commits, and pushes only to that repo. Never perform git operations on the agent-tools repo itself (this repo). Never push to `main` or `master` — all pushes go to feature branches only. `commit.sh` enforces this with a hard check.
- **No skipping technical review.** Always run tech review and check confidence scores.

## ACP integrations

This pipeline runs on ACP which injects platform credentials as environment variables.

| Integration | Use for | ACP env var | Script-expected name |
|-------------|---------|-------------|---------------------|
| **JIRA** | Searching tickets, reading issue details, updating labels | `JIRA_API_TOKEN` | `JIRA_API_TOKEN` |
| **GitHub** | Reading PRs, fetching file contents, code search | `GITHUB_TOKEN` | `GITHUB_TOKEN` |
| **GitLab** | Reading MRs, fetching file contents, commit diffs | `GITLAB_TOKEN` | `GITLAB_TOKEN` |
| **Google Docs** | Reading Google Docs linked from JIRA tickets | — | — |

### Credential mapping

ACP injects credentials as environment variables. `setup.sh` writes `~/.env` so scripts that source it or use `load_env_file()` pick up the credentials automatically. JIRA scripts now use `JIRA_API_TOKEN` natively (matching the ACP convention), with `JIRA_AUTH_TOKEN` accepted as a backward-compatible fallback.

### How to use integrations

Pipeline scripts (`jira_reader.py`, `jira_writer.py`, `git_pr_reader.py`) are the primary API access method. They authenticate via `~/.env`, which `setup.sh` populates from ACP-injected environment variables. For label operations, use `jira_writer.py` with `--labels-add`/`--labels-remove`.

## Repo integration

The batch controller can write documentation directly into a target docs repository, push a feature branch, and raise a MR/PR. This is controlled by `adapters/ambient/repo-mapping.yaml`:

```yaml
repos:
  - jira_project: VROOM
    repo_url: https://gitlab.com/amcleod/sig-docs-ambient
    default_branch: main
    format: mkdocs
```

`repo-setup.sh` runs before the orchestrator to resolve the repo, clone it, and create a feature branch. Publishing (commit + push) and MR/PR creation are handled by the orchestrator's `commit` and `create-mr` workflow steps — the same steps used by the local interactive workflow.

If no mapping exists for a ticket's project, the pipeline falls back to `--draft` mode automatically.

## Output structure

All output goes to `artifacts/` organized by ticket ID:

```
artifacts/
├── batch-summary.md
└── <ticket>/
    ├── repo-info.json
    ├── requirements/requirements.md
    ├── planning/plan.md
    ├── writing/
    │   ├── _index.md
    │   ├── modules/*.adoc    (AsciiDoc)
    │   └── docs/*.md         (MkDocs)
    ├── technical-review/review.md
    ├── style-review/review.md
    ├── commit/commit-info.json
    ├── create-mr/mr-info.json
    └── workflow/docs-workflow_<ticket>.json
```

## Configuration

| Variable | Required | Purpose | Default |
|----------|----------|---------|---------|
| `DOCS_TRIGGER_LABEL` | No | JIRA label to scrape for | `ambient-docs-ready` |
| `DOCS_PROCESSING_LABEL` | No | Label added when ticket is claimed by a session | `ambient-docs-processing` |
| `DOCS_DONE_LABEL` | No | Label added on success | `ambient-docs-generated` |
| `DOCS_FAILED_LABEL` | No | Label added on failure | `ambient-docs-failed` |
| `DOCS_JIRA_PROJECT` | No | Limit to specific JIRA project | — |

## Authentication

Plugin agents have a 2-step access failure procedure:

1. `source ~/.env` and retry
2. STOP and report

**In ACP, step 1 always works.** `setup.sh` writes `~/.env` from ACP-injected credentials. Scripts use `JIRA_API_TOKEN` directly (matching the ACP convention). If ACP has not yet injected credentials when `setup.sh` runs, `~/.env` will contain empty values and agents will stop and report the error.

## Output routing

All pipeline output (requirements, plans, drafts, reviews, batch summary) writes to `artifacts/` at the repository root. This matches the ACP platform convention used by all built-in workflows and is surfaced in the ACP UI as session output.

On ACP, `setup.sh` creates a symlink from `${REPO_ROOT}/artifacts/` to `/workspace/artifacts/` so all scripts write to the ACP platform directory that is surfaced in the UI. This is transparent — no scripts need modification.

If troubleshooting missing output, verify:
1. The symlink exists: `ls -la artifacts/` (should show `artifacts -> /workspace/artifacts`)
2. The target is writable: `touch artifacts/.test && rm artifacts/.test`

## Skill resolution

Skills, agents, and reference files are available in `.claude/skills/`, `.claude/agents/`, and `.claude/reference/` at the repo root via symlinks to the plugin directories. All skill references use bare names (no `plugin:skill` prefix).
