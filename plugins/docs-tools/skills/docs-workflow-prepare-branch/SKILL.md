---
name: docs-workflow-prepare-branch
description: Create a fresh git branch from the latest upstream default branch before writing documentation. Only runs in UPDATE-IN-PLACE mode (no --draft flag). Skipped in draft mode and when --repo-path is set (branch created externally).
model: claude-haiku-4-5@20251001
argument-hint: <ticket> --base-path <path> [--draft] [--repo-path <path>]
allowed-tools: Bash, Read
---

# Prepare Branch Step

Step skill for the docs-orchestrator pipeline. Creates a clean working branch from the latest upstream default branch before the writing step modifies repo files.

**Only runs in default UPDATE-IN-PLACE mode (no flags).** Skipped when `--draft` is set (no repo modifications) or when `--repo-path` is set (branch already created externally by `repo-setup.sh`).

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `artifacts/proj-123`)
- `--draft` — If present, skip branch creation entirely
- `--repo-path <path>` — If present, skip branch creation (branch managed externally)

## Input

None. This step has no upstream file dependencies.

## Output

```
<base-path>/prepare-branch/branch-info.md
```

Contains the branch name created and the base ref used.

## Execution

Run the branch preparation script, passing through all arguments:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/prepare_branch.sh <ticket> --base-path <base-path> [--draft] [--repo-path <path>]
```

The script handles:

1. **Argument parsing** — extracts ticket ID, `--base-path`, `--draft`, and `--repo-path` flags
2. **Skip mode** — writes a skip note and exits early if `--draft` or `--repo-path` is set
3. **Default branch detection** — tries `upstream` remote first, falls back to `origin`, detects HEAD branch with fallback to `main`/`master`
4. **Uncommitted changes check** — stops with an error if working tree is dirty (never force-checkouts)
5. **Fetch** — fetches latest from remote; warns but continues if fetch fails (network/auth issues)
6. **Branch creation** — creates `<ticket-id-lowercase>` branch from remote default; switches to existing branch if it already exists
7. **Output** — writes `branch-info.md` with branch name, base ref, and timestamp
