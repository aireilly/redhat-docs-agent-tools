---
name: docs-workflow-commit
description: Commit manifest-listed files and push the feature branch to the remote. Works in both local (current directory) and ACP (cloned repo) environments. Skipped in draft mode.
model: claude-haiku-4-5@20251001
argument-hint: <ticket> --base-path <path> [--repo-path <path>] [--draft]
allowed-tools: Bash, Read
---

# Commit Step

Step skill for the docs-orchestrator pipeline. Commits documentation files listed in the writing manifest and pushes the feature branch to the remote.

**Skipped when `--draft` is set** (no repo modifications in draft mode).

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--repo-path <path>` — Target repository path. If omitted, uses the current working directory
- `--draft` — If present, skip committing entirely

## Input

```text
<base-path>/writing/_index.md
```

The writing manifest listing all files written or modified.

## Output

```text
<base-path>/commit/commit-info.json
```

Contains branch name, commit SHA, files committed, platform, repo URL, and push status.

## Execution

Run the commit script, passing through all arguments:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/commit.sh <ticket> --base-path <base-path> [--repo-path <path>] [--draft]
```

The script handles:

1. **Draft mode check** — writes a skip record and exits if `--draft` is set
2. **Context resolution** — determines repo path, branch, platform, and remote URL from `--repo-path` argument or current working directory git context
3. **Safety checks** — refuses to push to `main`/`master`, refuses to push if in the agent-tools repo (contains `adapters/ambient/`)
4. **Manifest reading** — extracts file paths from `<base-path>/writing/_index.md`
5. **Commit** — stages manifest-listed files and commits with a descriptive message
6. **Push** — pushes the feature branch to origin (uses `--force-with-lease` for pipeline-generated branches)
7. **Output** — writes `commit-info.json` with commit metadata
