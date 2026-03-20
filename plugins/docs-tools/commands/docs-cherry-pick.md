---
description: Intelligently cherry-pick documentation changes to enterprise branches, excluding files that don't exist on each target release
argument-hint: <pr-url|--commit sha> --target <branch> [--dry-run]
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, AskUserQuestion, Agent
---

## Name

docs-tools:docs-cherry-pick

## Synopsis

`/docs-tools:docs-cherry-pick <pr-url|--commit sha> --target <branch1[,branch2,...]> [--dry-run] [--deep] [--no-push] [--ticket <id>]`

## Description

Intelligently backport documentation changes from a PR or commit to one or more enterprise branches. Automatically identifies which files exist on each target branch and creates clean, targeted backport PRs that exclude modules not present on that release.

### Required Arguments

- **source**: A GitHub PR URL, GitLab MR URL, or `--commit <sha>`
- **--target**: Target enterprise branch(es), comma-separated (e.g., `enterprise-4.17` or `enterprise-4.17,enterprise-4.16`)

### Options

| Option | Description |
|--------|-------------|
| `--target <branches>` | Comma-separated target branches (required) |
| `--commit <sha>` | Use a commit SHA instead of a PR URL |
| `--dry-run` | Audit only — show what would be included/excluded without making changes |
| `--deep` | Run deep content comparison to assess patch applicability and flag version-specific content |
| `--no-push` | Create branch and commits locally but don't push |
| `--ticket <id>` | JIRA ticket ID for branch naming (auto-detected from PR title if not set) |

**IMPORTANT**: This command requires a source and `--target`. If either is missing, stop and ask the user to provide them.

### Usage Examples

```bash
# Backport a PR to enterprise-4.17
/docs-tools:docs-cherry-pick https://github.com/openshift/openshift-docs/pull/106280 \
  --target enterprise-4.17

# Backport to multiple branches
/docs-tools:docs-cherry-pick https://github.com/openshift/openshift-docs/pull/106280 \
  --target enterprise-4.17,enterprise-4.16

# Audit only (no changes)
/docs-tools:docs-cherry-pick https://github.com/openshift/openshift-docs/pull/106280 \
  --target enterprise-4.17,enterprise-4.16 --dry-run

# Deep audit — check patch applicability and flag version-specific content
/docs-tools:docs-cherry-pick https://github.com/openshift/openshift-docs/pull/106280 \
  --target enterprise-4.17 --dry-run --deep

# Backport with deep analysis and intelligent conflict resolution
/docs-tools:docs-cherry-pick https://github.com/openshift/openshift-docs/pull/106280 \
  --target enterprise-4.17 --deep

# Backport from a specific commit
/docs-tools:docs-cherry-pick --commit abc123def \
  --target enterprise-4.17 --ticket TELCODOCS-2647

# Local only (don't push)
/docs-tools:docs-cherry-pick https://github.com/openshift/openshift-docs/pull/106280 \
  --target enterprise-4.17 --no-push
```

## Implementation

### Workflow Overview

1. **Validate**: Check inputs and access
2. **Audit**: Run `docs-branch-audit` to determine file applicability per branch
3. **Deep audit** (if `--deep`): Content comparison and patch applicability check
4. **Confirm**: Present the plan and ask for approval
5. **Apply**: Create branch, cherry-pick, resolve conflicts
6. **Push**: Push branch and generate PR description
7. **Repeat**: Process additional target branches if specified

---

### Phase 1: Validate Inputs

#### Step 1: Parse arguments

```bash
# Check for required arguments
# Source: first positional arg (PR URL) or --commit <sha>
# Target: --target <branch1,branch2>
# Optional: --dry-run, --no-push, --ticket <id>
```

If the source is a PR URL, detect the platform:

```bash
if echo "$SOURCE" | grep -q "github.com"; then
    PLATFORM="github"
elif echo "$SOURCE" | grep -q "gitlab"; then
    PLATFORM="gitlab"
fi
```

#### Step 2: Verify access

```bash
# For PR source: verify token
if [[ "$PLATFORM" = "github" ]]; then
    [ -n "$GITHUB_TOKEN" ] || { echo "ERROR: GITHUB_TOKEN not set"; exit 1; }
elif [[ "$PLATFORM" = "gitlab" ]]; then
    [ -n "$GITLAB_TOKEN" ] || { echo "ERROR: GITLAB_TOKEN not set"; exit 1; }
fi

# Verify we're in a git repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "ERROR: Not in a git repo"; exit 1; }
```

#### Step 3: Extract source information

```bash
# Get PR info
python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py info "$SOURCE" --json > /tmp/cherry-pick-pr-info.json

# Extract ticket ID from PR title if not provided
if [[ -z "$TICKET" ]]; then
    TICKET=$(jq -r '.title' /tmp/cherry-pick-pr-info.json | grep -oP '^[A-Z]+-[0-9]+' || echo "")
fi

# Get the list of changed files
python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py files "$SOURCE" > /tmp/cherry-pick-source-files.txt
```

#### Step 3a: Resolve commit SHA for cherry-pick

The cherry-pick requires a commit SHA. How to obtain it depends on the PR state:

```bash
# Check PR state
PR_STATE=$(jq -r '.state' /tmp/cherry-pick-pr-info.json)
PR_MERGED=$(jq -r '.merged' /tmp/cherry-pick-pr-info.json)

if [[ "$PR_MERGED" == "true" ]]; then
    # Merged PR — use the merge commit's parent (the actual PR commit)
    COMMIT_SHA=$(jq -r '.merge_commit_sha' /tmp/cherry-pick-pr-info.json)
elif [[ "$PR_STATE" == "open" ]]; then
    # Open (unmerged) PR — fetch the PR head ref
    PR_NUMBER=$(echo "$SOURCE" | grep -oP '\d+$')
    git fetch upstream "pull/${PR_NUMBER}/head:pr-${PR_NUMBER}"
    COMMIT_SHA=$(git rev-parse "pr-${PR_NUMBER}")
    echo "WARNING: PR is not merged. Using head commit: ${COMMIT_SHA}"
else
    # Closed without merging
    echo "ERROR: PR is closed without being merged. Cannot cherry-pick."
    exit 1
fi
```

For `--commit` mode, verify the commit exists locally:

```bash
if ! git cat-file -e "$COMMIT_SHA" 2>/dev/null; then
    echo "ERROR: Commit $COMMIT_SHA not found. Try 'git fetch upstream' first."
    exit 1
fi
```

#### Step 3b: Capture source PR stats

Collect the file count and line delta from the source PR for later comparison:

```bash
# Get source PR diff stats
if [[ -n "$SOURCE" && "$SOURCE" == http* ]]; then
    # From PR: use git_pr_reader.py to get diff, then summarize
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py diff "$SOURCE" > /tmp/cherry-pick-source-diff.txt
else
    # From commit: generate diff directly
    git diff "${COMMIT_SHA}^..${COMMIT_SHA}" > /tmp/cherry-pick-source-diff.txt
fi

SOURCE_FILE_COUNT=$(grep -c '^diff --git' /tmp/cherry-pick-source-diff.txt || echo 0)
SOURCE_INSERTIONS=$(grep -c '^+[^+]' /tmp/cherry-pick-source-diff.txt || echo 0)
SOURCE_DELETIONS=$(grep -c '^-[^-]' /tmp/cherry-pick-source-diff.txt || echo 0)
echo "Source PR stats: ${SOURCE_FILE_COUNT} files changed, +${SOURCE_INSERTIONS} -${SOURCE_DELETIONS}"
```

---

### Phase 2: Branch Audit

#### Step 4: Run branch audit

Use the `docs-branch-audit` skill to check file existence on each target branch:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/docs-branch-audit/scripts/branch_audit.sh \
  --pr "$SOURCE" \
  --branches "$TARGET_BRANCHES" \
  --json > /tmp/cherry-pick-audit.json
```

Or for commit mode:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/docs-branch-audit/scripts/branch_audit.sh \
  --commit "$COMMIT_SHA" \
  --branches "$TARGET_BRANCHES" \
  --json > /tmp/cherry-pick-audit.json
```

Also run the text output for display:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/docs-branch-audit/scripts/branch_audit.sh \
  --pr "$SOURCE" \
  --branches "$TARGET_BRANCHES"
```

#### Step 5: Analyze assembly paths

Assemblies may have different paths on different branches. The openshift-docs repo has reorganized directory structures across releases (e.g., `networking/ptp/` on 4.16 became `networking/advanced_networking/ptp/` on 4.17+). This step detects these path differences proactively.

For each target branch, check whether excluded assembly files exist at a different path:

```bash
for TARGET_REF in ${TARGET_REFS[@]}; do
    while IFS= read -r filepath; do
        # Skip non-assembly files (modules don't move)
        [[ "$filepath" == modules/* ]] && continue

        # Check if this file was excluded (not found at the original path)
        if ! git cat-file -e "${TARGET_REF}:${filepath}" 2>/dev/null; then
            BASENAME=$(basename "$filepath")
            # Search for the same filename at a different path on the target branch
            ALT_PATH=$(git ls-tree -r --name-only "$TARGET_REF" | grep "/${BASENAME}$" | head -1)
            if [[ -n "$ALT_PATH" ]]; then
                echo "PATH DIFFERENCE: $filepath → $ALT_PATH on $(basename $TARGET_REF)"
                # Track this for conflict resolution — the cherry-pick will create a
                # modify/delete conflict at the old path. The changes need to be applied
                # to the file at the new (target branch) path instead.
            fi
        fi
    done < /tmp/cherry-pick-source-files.txt
done
```

**When a path difference is detected:**

1. The cherry-pick will produce a modify/delete conflict for the original path (file doesn't exist there on the target branch)
2. Remove the conflict file at the old path: `git rm <old-path>`
3. Apply the PR's changes to the file at the target branch path instead:
   - Read the file at the target path: `git show ${TARGET_REF}:<alt-path>`
   - Apply the same editorial changes (abstract tags, callout transforms, etc.)
   - The xref paths in the file will use the target branch's directory structure — keep those paths, only apply the editorial fixes

**Real-world example (4.16):**
- Source PR changes `networking/advanced_networking/ptp/configuring-ptp.adoc`
- On enterprise-4.16, this file exists at `networking/ptp/configuring-ptp.adoc`
- The cherry-pick creates a modify/delete conflict at the `advanced_networking` path
- Resolution: remove the conflict file, apply editorial changes to `networking/ptp/configuring-ptp.adoc`
- Keep 4.16-correct xref paths (`../../networking/ptp/` not `../../../networking/advanced_networking/ptp/`)

Report any path differences to the user in the confirmation step.

#### Step 5a: Deep content comparison (if `--deep`)

If `--deep` is set, run the deep audit to check patch applicability and flag version-specific content:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/docs-branch-audit/scripts/branch_audit.sh \
  --pr "$SOURCE" \
  --branches "$TARGET_BRANCHES" \
  --deep
```

This runs `deep_audit.sh` for each included file and reports:

- **Confidence level** per file: `HIGH` (identical or minor divergence), `MEDIUM` (conditionals, moderate divergence), `NEEDS-REVIEW` (large divergence, patch conflicts)
- **Content divergence**: how many lines differ between main and target branch
- **Conditional directives**: `ifdef::`, `ifndef::`, `ifeval::` blocks that gate version-specific content
- **Structural differences**: heading count changes indicating reorganized content
- **Patch applicability**: whether the PR's diff applies cleanly to the target branch version

Files marked `NEEDS-REVIEW` will require conflict resolution during the apply phase.

---

### Phase 3: Confirm Plan

#### Step 6: Present the plan

If `--dry-run` is set, display the audit results (and deep audit if `--deep`) and stop.

Otherwise, present the plan to the user using `AskUserQuestion`:

```
Cherry-pick plan for <source> → <target-branch>:

Include (<N> files):
  <file list>

Exclude (<N> files — not on target branch):
  <file list>

[If --deep was used:]
Confidence assessment:
  HIGH:         <N> files (will apply cleanly)
  MEDIUM:       <N> files (likely applies, minor differences)
  NEEDS-REVIEW: <N> files (conflicts expected, Claude will resolve)

Assembly notes:
  <any path differences>

Proceed with cherry-pick? (yes/no)
```

Wait for user confirmation before proceeding. If the user says no, stop.

---

### Phase 4: Apply Changes

Process each target branch sequentially.

#### Step 7: Create backport branch

```bash
TARGET_BRANCH="enterprise-4.17"  # current target being processed
BRANCH_NAME="${TICKET:-cherry-pick}-${TARGET_BRANCH##*-}-CP"

# Fetch the target branch
git fetch upstream "$TARGET_BRANCH"

# Create the backport branch
git checkout -b "$BRANCH_NAME" "upstream/$TARGET_BRANCH"
echo "Created branch: $BRANCH_NAME from upstream/$TARGET_BRANCH"
```

#### Step 8: Cherry-pick and resolve conflicts

##### Step 8a: Attempt cherry-pick

```bash
# Try cherry-picking the source commit(s)
git cherry-pick --no-commit "$COMMIT_SHA" 2>/tmp/cherry-pick-result.txt
CP_EXIT=$?
```

##### Step 8b: Remove excluded files

Whether the cherry-pick succeeded or conflicted, unstage any excluded files:

```bash
for excluded_file in "${EXCLUDE_FILES[@]}"; do
    git checkout HEAD -- "$excluded_file" 2>/dev/null || git rm --cached "$excluded_file" 2>/dev/null || true
done
```

##### Step 8c: Handle clean cherry-pick (exit code 0)

If the cherry-pick applied cleanly, skip to Step 9 (Commit).

##### Step 8d: Resolve conflicts (exit code != 0)

If the cherry-pick has conflicts, identify and resolve them:

```bash
# List conflicted files
CONFLICTED_FILES=$(git diff --name-only --diff-filter=U)
echo "Conflicted files:"
echo "$CONFLICTED_FILES"
```

For each conflicted file, use Claude to resolve the conflict intelligently:

**Conflict resolution with subagents** — spawn one `Agent` per conflicted file:

```
Agent(subagent_type="general-purpose", description="resolve conflict in <file>",
  prompt="You are resolving a git cherry-pick conflict for a documentation backport.

  Context:
  - Source branch: main (latest version)
  - Target branch: <target-branch> (older release)
  - The PR applied editorial/DITA-prep changes on main
  - The file on the target branch may have different content because features
    were added or reorganized in newer versions

  Conflicted file: <filepath>

  Instructions:
  1. Read the conflicted file (it contains <<<<<<< HEAD / ======= / >>>>>>> markers)
  2. For each conflict block:
     a. The HEAD version is what exists on the TARGET branch (keep structure/content appropriate for this release)
     b. The incoming version is the CHANGE from the PR (editorial fixes we want to apply)
     c. RESOLVE by applying the editorial change to the TARGET branch content
        - If the change is purely editorial (formatting, abstract tags, callout transforms): apply it to the target version
        - If the change modifies content that doesn't exist on the target branch: keep the target version
        - If the change references features/UI elements not in this release: keep the target version
        - If unclear: keep the target version and add a comment '// REVIEW: <reason>' on the line above
  3. Remove ALL conflict markers (<<<<<<, =======, >>>>>>>)
  4. Verify the file is valid AsciiDoc (no broken blocks, no orphaned markers)
  5. Return a summary:
     FILE: <filepath>
     CONFLICTS: <number of conflict blocks>
     RESOLVED: <number resolved automatically>
     KEPT-TARGET: <number where target version was kept>
     FLAGGED: <number marked for review>
     DETAILS:
     - Line <N>: <what was done and why>
  ")
```

**Key resolution rules:**

| Conflict type | Resolution |
|---------------|------------|
| Editorial fix (abstract tag, callout transform, block delimiter) | Apply the fix to the target branch content |
| Content that exists on both branches but differs slightly | Apply the editorial fix, keep the target branch wording |
| Content that only exists on main (new feature) | Keep the target branch version |
| UI element references (e.g., Operators → Ecosystem) | Keep the target branch version (UI may differ between releases) |
| Xref paths that differ between branches | Keep the target branch xref paths (directory structure may differ between releases) |
| New xref to an anchor/module that doesn't exist on the target branch | Drop the xref (don't add broken cross-references) |
| Ambiguous — can't determine correct resolution | Keep target version, flag with `// REVIEW:` comment |

##### Step 8e: Verify resolution

After all conflicts are resolved:

```bash
# Check no conflict markers remain
if grep -rn '<<<<<<\|======\|>>>>>>' ${CONFLICTED_FILES} 2>/dev/null; then
    echo "ERROR: Unresolved conflict markers found"
    # List files with remaining markers for manual review
fi

# Stage resolved files
git add ${CONFLICTED_FILES}
```

##### Step 8f: Handle files that need human review

If any conflicts were flagged with `// REVIEW:` comments, present them to the user via `AskUserQuestion`:

```
The following conflicts could not be resolved automatically:

File: modules/nw-ptp-installing-operator-web-console.adoc
Line 19: PR changes 'Operators' to 'Ecosystem' but this UI label may differ on 4.17
  Current (4.17): .. In the {product-title} web console, click *Operators* -> *OperatorHub*.
  PR (main):      .. In the {product-title} web console, click *Ecosystem* -> *Software Catalog*.

Keep the 4.17 version or apply the main version?
```

Apply the user's decision and remove the `// REVIEW:` comment.

#### Step 9: Commit changes

```bash
# Build commit message with exclusion and conflict documentation
COMMIT_MSG=$(cat <<EOF
${TICKET}: Backport DITA-prep fixes to ${TARGET_BRANCH}

Backport of ${SOURCE} to ${TARGET_BRANCH}.

${INCLUDE_COUNT} files included, ${EXCLUDE_COUNT} files excluded.
${CONFLICT_COUNT:-0} conflict(s) resolved.

Excluded (not present on ${TARGET_BRANCH}):
$(for f in "${EXCLUDE_FILES[@]}"; do echo "- $(basename "$f" .adoc)"; done)

$(if [[ ${CONFLICT_COUNT:-0} -gt 0 ]]; then
echo "Conflicts resolved:"
for detail in "${CONFLICT_DETAILS[@]}"; do echo "- $detail"; done
fi)

Co-Authored-By: Claude <model> <noreply@anthropic.com>
EOF
)

git add -A
git commit -m "$COMMIT_MSG"
```

The `CONFLICT_DETAILS` array should be populated during Step 8d with a summary of each resolution, e.g.:
- `cnf-configuring-log-filtering-for-linuxptp.adoc: applied abstract rewrite`
- `configuring-ptp.adoc: kept 4.16-correct xref paths`

#### Step 9a: Compare stats with source PR

Compare the backport's file count and line delta against the source PR to satisfy the CQA requirement that reviewers can verify counts match or have documented reasons for differences:

```bash
# Get backport diff stats (compare backport branch to its base)
git diff "upstream/${TARGET_BRANCH}...HEAD" > /tmp/cherry-pick-backport-diff.txt

BACKPORT_FILE_COUNT=$(grep -c '^diff --git' /tmp/cherry-pick-backport-diff.txt || echo 0)
BACKPORT_INSERTIONS=$(grep -c '^+[^+]' /tmp/cherry-pick-backport-diff.txt || echo 0)
BACKPORT_DELETIONS=$(grep -c '^-[^-]' /tmp/cherry-pick-backport-diff.txt || echo 0)

FILE_DIFF=$((SOURCE_FILE_COUNT - BACKPORT_FILE_COUNT))
INS_DIFF=$((SOURCE_INSERTIONS - BACKPORT_INSERTIONS))
DEL_DIFF=$((SOURCE_DELETIONS - BACKPORT_DELETIONS))
```

Display the comparison:

```
Stats comparison (source PR vs backport):
  Original PR:  <SOURCE_FILE_COUNT> files changed, +<SOURCE_INSERTIONS> -<SOURCE_DELETIONS>
  Backport:     <BACKPORT_FILE_COUNT> files changed, +<BACKPORT_INSERTIONS> -<BACKPORT_DELETIONS>
  Difference:   <FILE_DIFF> files, +<INS_DIFF> -<DEL_DIFF>

Reason for difference: <EXCLUDE_COUNT> file(s) excluded (not present on <TARGET_BRANCH>)
```

If the difference in files does not equal the number of excluded files, or line deltas diverge beyond what exclusions explain, flag this for user attention:

```
⚠️  Stats divergence exceeds excluded files — review the backport for unintended changes.
```

Save the stats for inclusion in the PR description:

```bash
cat > /tmp/cherry-pick-stats.md <<EOF
## Stats comparison

| Metric | Original PR | Backport | Difference |
|--------|-------------|----------|------------|
| Files changed | ${SOURCE_FILE_COUNT} | ${BACKPORT_FILE_COUNT} | ${FILE_DIFF} |
| Insertions (+) | ${SOURCE_INSERTIONS} | ${BACKPORT_INSERTIONS} | ${INS_DIFF} |
| Deletions (-) | ${SOURCE_DELETIONS} | ${BACKPORT_DELETIONS} | ${DEL_DIFF} |

**Reason for difference:** ${EXCLUDE_COUNT} file(s) excluded (not present on ${TARGET_BRANCH})
EOF
```

---

### Phase 5: Push and Report

#### Step 10: Push branch

Unless `--no-push` is set:

```bash
git push -u origin "$BRANCH_NAME"
```

#### Step 11: Generate PR description

Write a structured PR description to `/tmp/cherry-pick-pr-description.md`:

```markdown
## Summary

Backport of <source-pr-link> to <target-branch>.

<original PR title/description summary>

## Files

<include-count> files included, <exclude-count> files excluded.

### Excluded files (not present on <target-branch>)

| Module | Reason |
|--------|--------|
| `<module-name>` | Not present on <target-branch> |

### Included files

<list of included files>

## Stats comparison

| Metric | Original PR | Backport | Difference |
|--------|-------------|----------|------------|
| Files changed | <SOURCE_FILE_COUNT> | <BACKPORT_FILE_COUNT> | <FILE_DIFF> |
| Insertions (+) | <SOURCE_INSERTIONS> | <BACKPORT_INSERTIONS> | <INS_DIFF> |
| Deletions (-) | <SOURCE_DELETIONS> | <BACKPORT_DELETIONS> | <DEL_DIFF> |

**Reason for difference:** <EXCLUDE_COUNT> file(s) excluded (not present on <target-branch>)

## Assembly notes

<any path difference notes>

## Verification

- [ ] Preview renders correctly
- [ ] No broken includes or cross-references
- [ ] Content is appropriate for this release version
```

Write the file and inform the user:

```
Branch pushed: <branch-name>

PR description written to /tmp/cherry-pick-pr-description.md

Copy to clipboard:
  cat /tmp/cherry-pick-pr-description.md | xclip -selection clipboard

Create the PR targeting <target-branch> and paste the description.
```

#### Step 12: Process additional branches

If multiple target branches were specified, switch back to the original branch and repeat Steps 7-11 for each remaining target branch.

```bash
# Return to original branch before processing next target
git checkout -
```

---

## Related

- **docs-branch-audit skill**: The underlying file existence and content comparison check used by this command
- **git-pr-reader skill**: PR/MR file listing and diff extraction used for source analysis
