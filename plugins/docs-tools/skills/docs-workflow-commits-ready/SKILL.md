---
name: docs-workflow-commits-ready
description: >-
  Check a code repository for new commits on the default branch that may
  need documentation. Queries the Git API for commits since the last
  processed marker, applies file filtering to exclude irrelevant commits,
  and returns a JSON payload of actionable commit batches. Designed as
  the entry point for CI-triggered commit-driven docs-orchestrator runs.
model: claude-haiku-4-5@20251001
argument-hint: --repo <url> [--branch <name>] [--base-path <path>] [--dry-run]
allowed-tools: Read, Bash, Glob, Grep
---

# Commits Ready Check

This skill is a **check-and-return** gate — it does not dispatch the orchestrator. The caller (cron script, CI workflow, or human) decides what to do with the returned batch.
Unlike other step skills, this skill does **not** dispatch an agent.

Gate skill for automated commit-driven docs-orchestrator runs. Checks a code repository for new commits since the last processed marker, filters out already-processed batches, and outputs an actionable commit batch.

## Arguments

- `--repo <url>` — Code repository URL (required). Supports GitHub and GitLab.
- `--branch <name>` — Branch to check (default: `main`)
- `--base-path <path>` — Directory to check for existing progress/marker files (default: `.claude/docs`)
- `--since <sha>` — Override: check commits since this SHA instead of the stored marker
- `--max-commits <n>` — Maximum number of commits to return (default: 50)
- `--dry-run` — Show what would be returned without side effects (default behavior; included for explicitness)

## Environment

Requires `GITHUB_TOKEN` or `GITLAB_TOKEN` in the environment (typically sourced from `~/.env`).

## Execution

Run the check script:

```bash
bash scripts/commits-ready-check.sh \
  --repo "https://github.com/org/code-repo" \
  --branch main \
  --base-path .claude/docs
```

The script:

1. Reads the marker file at `<base-path>/.commit-markers/<repo-slug>.json` for the last processed SHA
2. Calls `git_commit_reader.py list` for commits since the marker, with `--drop-empty` to exclude commits where all changed files are filtered out by `git_filters.yaml` (tests, CI, lock files, etc.)
3. Checks whether a workflow progress file already exists for the batch
4. Outputs a JSON payload with the batch identifier, commit SHAs, and summary stats

If all commits in the batch are dropped by `--drop-empty`, `ready` is `false`.

### Output format

When commits are found:
```json
{
  "repository": "https://github.com/org/repo",
  "branch": "main",
  "marker_sha": "abc1234",
  "total_new_commits": 5,
  "filtered_out": 0,
  "ready": true,
  "batch": {
    "identifier": "repo/def5678-ghi9012",
    "commits": ["def5678...", "jkl3456...", "ghi9012..."],
    "first_sha": "def5678...",
    "last_sha": "ghi9012...",
    "summary": "5 commits"
  },
  "filtered_stats": {
    "total_files": 47,
    "relevant_files": 18,
    "excluded_files": 29
  },
  "filtered": {}
}
```

When no new commits:
```json
{
  "repository": "https://github.com/org/repo",
  "branch": "main",
  "marker_sha": "abc1234",
  "total_new_commits": 0,
  "filtered_out": 0,
  "ready": false,
  "batch": null,
  "filtered": {}
}
```

### Marker file

The marker file at `<base-path>/.commit-markers/<repo-slug>.json` tracks the last processed commit SHA per repository. The **orchestrator** updates the marker on workflow completion — not this gate skill.

```json
{
  "repository": "https://github.com/org/repo",
  "last_processed_sha": "ghi9012...",
  "last_processed_at": "2026-03-25T10:30:00Z"
}
```

### First run

When no marker file exists, the script defaults to the last N commits (configurable via `--max-commits`), providing a reasonable starting point.
