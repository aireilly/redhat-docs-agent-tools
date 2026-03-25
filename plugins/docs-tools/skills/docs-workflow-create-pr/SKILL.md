---
name: docs-workflow-create-pr
description: Create a pull request or merge request with documentation changes. Reads branch info and plan from prior workflow steps. Invoked by the orchestrator when --create-pr is set.
model: claude-haiku-4-5@20251001
argument-hint: <identifier> --base-path <path>
allowed-tools: Read, Bash
---

# Create PR/MR Step

Step skill for the docs-orchestrator pipeline. Creates a pull request (GitHub) or merge request (GitLab) in the docs repository containing the documentation changes written by earlier steps.

**Only runs when the `create_pr` condition is set.** The orchestrator passes `--create-pr` to enable this step; without it, the step is skipped.

## Arguments

- `$1` — Workflow identifier (e.g., `my-service/a1b2c3d-e4f5g6h` or `PROJ-123`)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/my-service/a1b2c3d-e4f5g6h`)

## Input

Reads outputs from prior steps:
- `<base-path>/prepare-branch/branch-info.md` — Branch name and base ref
- `<base-path>/planning/plan.md` — Documentation plan (for PR description)
- `<base-path>/requirements/requirements.md` — Requirements summary (for PR description)

## Output

```
<base-path>/create-pr/pr-info.md
```

Contains the PR/MR URL, number, title, and branch details.

## Execution

Run the PR creation script:

```bash
python3 scripts/create_pr.py \
    --identifier <IDENTIFIER> \
    --base-path <BASE_PATH> \
    --json
```

The script:

1. **Reads branch info** from the prepare-branch step output to get the source branch name
2. **Reads plan and requirements** for the PR/MR description body
3. **Auto-detects platform** (GitHub/GitLab) from the git remote URL (`upstream`, falling back to `origin`)
4. **Detects default branch** of the remote for the PR/MR target
5. **Creates the PR/MR** via the GitHub/GitLab API
6. **Writes output** to `<base-path>/create-pr/pr-info.md`

### Verification

After the script completes, verify the output file exists at `<base-path>/create-pr/pr-info.md` and contains a valid PR/MR URL.
