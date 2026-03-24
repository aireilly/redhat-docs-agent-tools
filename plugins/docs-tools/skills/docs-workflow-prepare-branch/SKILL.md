---
name: docs-workflow-prepare-branch
description: Create a fresh git branch from the latest upstream default branch before writing documentation. Only runs in UPDATE-IN-PLACE mode (no --draft flag). Skipped in draft mode.
model: claude-haiku-4-5@20251001
argument-hint: <ticket> --base-path <path> [--draft]
allowed-tools: Bash, Read, Write
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

### 1. Parse arguments

Extract the ticket ID, `--base-path`, and `--draft` flag.

### 2. Check for draft mode

If `--draft` is set, write a short note to the output file:

```
# Branch Preparation — Skipped
Draft mode: no branch created.
```

Mark the step completed and return.

### 3. Detect the default upstream branch

```bash
# Try upstream remote first, fall back to origin
DEFAULT_REMOTE=$(git remote | grep -m1 upstream || git remote | head -1)
DEFAULT_BRANCH=$(git remote show "$DEFAULT_REMOTE" 2>/dev/null | sed -n 's/.*HEAD branch: //p')
```

If detection fails, fall back to `main`, then `master`.

### 4. Fetch latest from remote

```bash
git fetch "$DEFAULT_REMOTE" "$DEFAULT_BRANCH"
```

### 5. Create and switch to new branch

Branch name format: `<ticket-id-lowercase>` (e.g., `proj-123`).

```bash
TICKET_LOWER=$(echo "$TICKET" | tr '[:upper:]' '[:lower:]')
BRANCH_NAME="${TICKET_LOWER}"
git checkout -b "$BRANCH_NAME" "${DEFAULT_REMOTE}/${DEFAULT_BRANCH}"
```

If the branch already exists (e.g., resuming a workflow), switch to it instead:

```bash
git checkout "$BRANCH_NAME"
```

### 6. Write output

Write `<base-path>/prepare-branch/branch-info.md`:

```markdown
# Branch Preparation

- **Branch**: `<BRANCH_NAME>`
- **Based on**: `<DEFAULT_REMOTE>/<DEFAULT_BRANCH>`
- **Created at**: <ISO 8601 timestamp>
```

### Error handling

- If the working tree has uncommitted changes that would be lost by checkout, **STOP** and ask the user to stash or commit them first. Do NOT force checkout.
- If `git fetch` fails (no network, auth issue), warn the user but continue with the local copy of the default branch.
