---
name: docs-workflow-create-mr
description: Create or find an existing merge request (GitLab) or pull request (GitHub) for the published documentation branch. Skipped in draft mode or when the branch was not pushed.
model: claude-haiku-4-5@20251001
argument-hint: <ticket> --base-path <path> [--repo-path <path>] [--draft]
allowed-tools: Bash, Read
---

# Create MR/PR Step

Step skill for the docs-orchestrator pipeline. Creates a GitLab MR or GitHub PR for the feature branch pushed by the commit step.

**Skipped when `--draft` is set** or when `commit-info.json` has `pushed: false`.

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--repo-path <path>` — Path to the docs repo (accepted for compatibility; context comes from `commit-info.json`)
- `--draft` — If present, skip MR/PR creation entirely

## Input

```text
<base-path>/commit/commit-info.json
```

Produced by the commit step. Must have `pushed: true` for this step to proceed.

## Output

```text
<base-path>/create-mr/mr-info.json
<base-path>/create-mr/step-result.json
```

`mr-info.json` contains platform, MR/PR URL, action taken (`created`, `found_existing`, or `skipped`), and title. `step-result.json` is the standard sidecar with MR/PR metadata.

## Execution

Run the create-mr script, passing through all arguments:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/create_mr.py <ticket> --base-path <base-path> [--repo-path <path>] [--draft]
```

The script handles:

1. **Draft mode check** — writes a skip record and exits if `--draft` is set
2. **Commit check** — reads `commit-info.json` and skips if branch was not pushed
3. **Context resolution** — determines platform and repo URL from `commit-info.json`, default branch from `repo-info.json` if available
4. **Fork detection** — checks local git remotes first, then queries the GitLab API (via `python-gitlab`) to detect fork relationships and targets the upstream project for cross-fork MRs. GitHub fork detection is handled automatically by `PyGithub`
5. **Existing MR/PR check** — looks for an open MR/PR from the feature branch before creating a new one
6. **MR/PR creation** — creates a GitLab MR (via `python-gitlab`) or GitHub PR (via `PyGithub`)
7. **Output** — writes both `mr-info.json` and `step-result.json` (do NOT write step-result.json separately — the script handles it)
