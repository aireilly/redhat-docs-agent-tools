---
name: docs-cherry-pick
description: Intelligently cherry-pick documentation changes to enterprise branches, excluding files that don't exist on each target release
argument-hint: <pr-url|--commit sha> --target <branch> [--dry-run]
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, AskUserQuestion, Agent
disable-model-invocation: true
---

# Cherry-Pick Backport

Backport documentation changes from a PR or commit to enterprise branches. Automatically excludes files not present on target releases and resolves cherry-pick conflicts.

**Required:** source (PR URL or `--commit <sha>`) and `--target <branches>`. If either is missing, ask the user.

## Usage

```bash
# Run the cherry-pick script
bash ${CLAUDE_SKILL_DIR}/scripts/cherry_pick.sh \
  --pr <url> --target <branches> [--dry-run] [--deep] [--no-push] [--ticket <id>]

# Commit mode
bash ${CLAUDE_SKILL_DIR}/scripts/cherry_pick.sh \
  --commit <sha> --target <branches>
```

## Options

| Option | Description |
|--------|-------------|
| `--target <branches>` | Comma-separated target branches (required) |
| `--commit <sha>` | Use a commit SHA instead of PR URL |
| `--dry-run` | Audit only — show what would be included/excluded |
| `--deep` | Deep content comparison for patch applicability |
| `--no-push` | Create branch locally, don't push |
| `--ticket <id>` | JIRA ticket ID (auto-detected from PR title) |

## Workflow

1. Run the script. For `--dry-run`, display results and stop.
2. For full runs, the script handles: validate, audit, cherry-pick, commit, push.
3. If the script exits with code **2**, there are conflicts. Follow the conflict resolution process below.

## Conflict Resolution (exit code 2)

When the script reports conflicts, resolve them using these steps:

### Step 1: Read conflict state

```bash
cat /tmp/cherry-pick-state/conflicted-files.txt
cat /tmp/cherry-pick-state/current-target.txt
```

### Step 2: Resolve each conflicted file

Spawn one Agent per conflicted file for parallel resolution:

```
Agent(subagent_type="general-purpose", prompt="
  Resolve cherry-pick conflict in <filepath>.
  Target branch: <target-branch>
  The PR applied editorial/DITA-prep changes on main.

  1. Read the file (contains <<<<<<< / ======= / >>>>>>> markers)
  2. Apply resolution rules (see below)
  3. Remove ALL conflict markers
  4. Verify valid AsciiDoc
  5. Return summary: FILE, CONFLICTS count, RESOLVED count, DETAILS
")
```

### Resolution rules

| Conflict type | Resolution |
|---------------|------------|
| Editorial fix (abstract tag, callout, block delimiter) | Apply fix to target branch content |
| Content exists on both branches, differs slightly | Apply editorial fix, keep target wording |
| Content only exists on main (new feature) | Keep target branch version |
| UI element references (e.g., Operators vs Ecosystem) | Keep target version (UI may differ) |
| Xref paths differ between branches | Keep target branch xref paths |
| New xref to anchor/module not on target branch | Drop the xref |
| Ambiguous | Keep target version, flag with `// REVIEW: <reason>` |

### Step 3: After resolution

```bash
# Verify no conflict markers remain
grep -rn '<<<<<<\|======\|>>>>>>' <conflicted-files>

# Stage and commit
git add <resolved-files>
TICKET=$(cat /tmp/cherry-pick-state/ticket.txt)
TARGET=$(cat /tmp/cherry-pick-state/current-target.txt)
git commit -m "${TICKET}: Backport to ${TARGET}

Co-Authored-By: Claude <model> <noreply@anthropic.com>"
```

### Step 4: Resume push phase

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/cherry_pick.sh \
  --pr <url> --target <target> --phase push
```

### Step 5: Handle `// REVIEW:` flags

If any conflicts were flagged, present them to the user via AskUserQuestion with the two versions and ask which to keep.

## Path differences

Assemblies may have different paths across releases (e.g., `networking/ptp/` on 4.16 became `networking/advanced_networking/ptp/` on 4.17+). The script detects these automatically.

When a path difference causes a modify/delete conflict:
1. Remove the conflict file at the old path: `git rm <old-path>`
2. Apply the PR's editorial changes to the file at the target branch path
3. Keep xref paths correct for the target branch's directory structure

## Related

- `docs-tools:docs-branch-audit` — file existence and content comparison
- `docs-tools:git-pr-reader` — PR/MR file listing and diff extraction
