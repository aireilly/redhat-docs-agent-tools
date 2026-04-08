---
name: docs-workflow-prepare-branch
description: Create a fresh git branch from the latest upstream default branch before writing documentation. Only runs in UPDATE-IN-PLACE mode (no --draft flag). Skipped in draft mode.
model: claude-haiku-4-5@20251001
argument-hint: <ticket> --base-path <path> [--draft]
allowed-tools: Bash, Read
---

# Prepare Branch Step

Step skill for the docs-orchestrator pipeline. Creates a clean working branch from the latest upstream default branch before the writing step modifies repo files.

**Only runs in UPDATE-IN-PLACE mode.** When `--draft` is set, this step is a no-op (mark completed immediately).

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--draft` — If present, skip branch creation entirely

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
bash ${CLAUDE_SKILL_DIR}/scripts/prepare_branch.sh <ticket> --base-path <base-path> [--draft]
```

The script handles:

1. **Argument parsing** — extracts ticket ID, `--base-path`, and `--draft` flag
2. **Draft mode** — writes a skip note and exits early if `--draft` is set
3. **Default branch detection** — tries `upstream` remote first, falls back to `origin`, detects HEAD branch with fallback to `main`/`master`
4. **Uncommitted changes check** — stops with an error if working tree is dirty (never force-checkouts)
5. **Fetch** — fetches latest from remote; warns but continues if fetch fails (network/auth issues)
6. **Branch creation** — creates `<ticket-id-lowercase>` branch from remote default; switches to existing branch if it already exists
7. **Output** — writes `branch-info.md` with branch name, base ref, and timestamp
