---
description: Run the DITA rework workflow to prepare AsciiDoc files for DITA conversion
argument-hint: <file.adoc|assembly.adoc> [--rewrite [--no-commit] [--dry-run] [--branch <name>]] [--review]
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, TodoWrite
---

# DITA Rework Command

Prepare AsciiDoc files for DITA conversion. This unified command supports three modes:

| Mode | Switch | Description |
|------|--------|-------------|
| **Default** | _(none)_ | Script-based rework pipeline — runs DITA cleanup skills in sequence |
| **Rewrite** | `--rewrite` | LLM-guided rewrite pipeline — uses AI to fix AsciiDocDITA issues |
| **Review** | `--review` | Post-rework review — compares changes against upstream/main |

## Required Argument

- **file**: (required) Path to an AsciiDoc module, assembly, or folder (e.g., `modules/con-overview.adoc` or `working-on-projects/master.adoc`)

**IMPORTANT**: This command requires a file path. If no argument is provided, stop and ask the user to provide one.

## Switch Parsing

Before executing any workflow, parse the arguments to determine the mode:

1. If `--review` is present → execute **Review Mode** (Phase R)
2. If `--rewrite` is present → execute **Rewrite Mode** (Phase W)
3. Otherwise → execute **Default Mode** (Phase D)

Also parse these options (rewrite mode only):
- `--no-commit`: Set `NO_COMMIT=true`
- `--dry-run`: Set `DRY_RUN=true`
- `--branch <name>`: Set `BRANCH_NAME=<name>`

---

# Phase D: Default Mode — Script-Based Rework

Run a suite of DITA cleanup tools against an AsciiDoc assembly and all its included files, preparing them for DITA conversion.

## Workflow Overview

1. **Setup**: Create a git branch for the rework
2. **Discovery**: Find all included files using `dita-includes`
3. **Baseline**: Run Vale with AsciiDocDITA rules to establish baseline
4. **Remediation**: Run DITA cleanup skills in sequence, committing after each
5. **Validation**: Run Vale again to compare results
6. **Push**: Push the branch to origin
7. **Summary**: Write a summary file for use in PR/MR description

## Step-by-Step Instructions

### Step 1: Validate Input

First, verify the assembly file exists:

```bash
# Check if the file exists
test -f "${1}" && echo "File exists: ${1}" || echo "ERROR: File not found: ${1}"
```

If the file does not exist, STOP and inform the user.

### Step 2: Create Git Branch

Derive the branch name from the assembly path:

1. Take the parent directory of the assembly file
2. Replace `/` with `-`
3. Append `-dita-rework`

Example: `working-on-projects/master.adoc` → `working-on-projects-dita-rework`

```bash
# Get the parent directory path relative to repository root
ASSEMBLY_PATH="${1}"
PARENT_DIR=$(dirname "${ASSEMBLY_PATH}")
BRANCH_NAME="${PARENT_DIR//\//-}-dita-rework"

# Create and checkout the new branch
git checkout -b "${BRANCH_NAME}"
```

### Step 3: Discover Included Files

Use the `dita-includes` skill to build a list of all files referenced by the assembly:

```bash
# Get absolute path of the assembly
ASSEMBLY_ABS=$(realpath "${ASSEMBLY_PATH}")

# Find all includes recursively
bash ${CLAUDE_PLUGIN_ROOT}/skills/dita-includes/scripts/find_includes.sh "${ASSEMBLY_ABS}" --existing > /tmp/dita-rework-files.txt

# Display the file list
cat /tmp/dita-rework-files.txt
```

Store this list for use in subsequent steps.

### Step 4: Run Baseline Vale Check

Use the `dita-validate-asciidoc` skill to run Vale with AsciiDocDITA rules against all files.

**IMPORTANT**: The following rules are informational only and should be excluded from before/after counts (but listed separately):
- `ConditionalCode` - ifdef/ifndef directives
- `AttributeReference` - attribute references
- `IncludeDirective` - include directives
- `TagDirective` - tag directives

```bash
# Run dita-validate-asciidoc to get all AsciiDocDITA issues
bash ${CLAUDE_PLUGIN_ROOT}/skills/dita-validate-asciidoc/scripts/validate_asciidoc.sh "${ASSEMBLY_PATH}" --existing > /tmp/dita-rework-vale-before-all.txt

# Separate actionable issues from informational issues
grep -v -E "AsciiDocDITA\.(ConditionalCode|AttributeReference|IncludeDirective|TagDirective)" /tmp/dita-rework-vale-before-all.txt > /tmp/dita-rework-vale-before.txt || true
grep -E "AsciiDocDITA\.(ConditionalCode|AttributeReference|IncludeDirective|TagDirective)" /tmp/dita-rework-vale-before-all.txt > /tmp/dita-rework-vale-before-info.txt || true

# Count issues
echo "Baseline AsciiDocDITA issues (actionable): $(wc -l < /tmp/dita-rework-vale-before.txt)"
echo "Baseline AsciiDocDITA issues (informational): $(wc -l < /tmp/dita-rework-vale-before-info.txt)"
```

If Vale is not available, skip this step with a warning.

### Step 5: Run DITA Cleanup Skills

Run each skill in sequence against all files. After each skill completes, create a git commit.

**CRITICAL**: Use `--rewrite-deflists` for dita-callouts as specified.

#### 5a. dita-content-type

```bash
# For each file in the list
while read -r file; do
    ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-content-type/scripts/content_type.rb "$file"
done < /tmp/dita-rework-files.txt

# Commit changes
git add -A && git commit -m "dita-content-type: Add :_mod-docs-content-type: attributes

Applied dita-content-type skill to detect and add content type attributes
(CONCEPT, PROCEDURE, REFERENCE, ASSEMBLY, SNIPPET) for DITA compatibility.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 5b. dita-document-id

```bash
while read -r file; do
    ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-document-id/scripts/document_id.rb "$file"
done < /tmp/dita-rework-files.txt

git add -A && git commit -m "dita-document-id: Add missing document IDs

Applied dita-document-id skill to generate and insert missing anchor IDs
for document titles. IDs follow AsciiDoc conventions with _{context} suffix
for modules.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 5c. dita-callouts (rewrite for deflists)

```bash
# For each file in the list
while read -r file; do
    ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-callouts/scripts/callouts.rb "$file" --rewrite-deflists
done < /tmp/dita-rework-files.txt

# Commit changes
git add -A && git commit -m "dita-callouts: Transform callouts to definition lists

Applied dita-callouts skill with --rewrite-deflists to convert callout
markers to definition lists for DITA compatibility.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 5d. dita-entity-reference

```bash
while read -r file; do
    ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-entity-reference/scripts/entity_reference.rb "$file"
done < /tmp/dita-rework-files.txt

git add -A && git commit -m "dita-entity-reference: Replace HTML entities with Unicode

Applied dita-entity-reference skill to replace HTML character entity
references with Unicode equivalents for DITA compatibility.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 5e. dita-line-break

```bash
while read -r file; do
    ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-line-break/scripts/line_break.rb "$file"
done < /tmp/dita-rework-files.txt

git add -A && git commit -m "dita-line-break: Remove hard line breaks

Applied dita-line-break skill to remove hard line breaks and
[%hardbreaks] options for DITA compatibility.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 5f. dita-related-links

```bash
while read -r file; do
    ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-related-links/scripts/related_links.rb "$file"
done < /tmp/dita-rework-files.txt

git add -A && git commit -m "dita-related-links: Clean up Additional resources sections

Applied dita-related-links skill to fix Additional resources sections
by removing or relocating non-link content for DITA compatibility.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 5g. dita-add-shortdesc-abstract

```bash
while read -r file; do
    ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-add-shortdesc-abstract/scripts/short_description.rb "$file"
done < /tmp/dita-rework-files.txt

git add -A && git commit -m "dita-add-shortdesc-abstract: Add [role=\"_abstract\"] attributes

Applied dita-add-shortdesc-abstract skill to add missing [role=\"_abstract\"]
attributes for DITA short description support.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 5h. dita-task-contents

```bash
while read -r file; do
    ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-task-contents/scripts/task_contents.rb "$file"
done < /tmp/dita-rework-files.txt

git add -A && git commit -m "dita-task-contents: Add .Procedure block titles

Applied dita-task-contents skill to add missing .Procedure block titles
to procedure modules for DITA compatibility.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 5i. dita-task-step

```bash
while read -r file; do
    ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-task-step/scripts/task_step.rb "$file"
done < /tmp/dita-rework-files.txt

git add -A && git commit -m "dita-task-step: Fix list continuations in procedure steps

Applied dita-task-step skill to add list continuation markers (+)
for multi-block step content in procedures.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 5j. dita-task-title

```bash
while read -r file; do
    ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-task-title/scripts/task_title.rb "$file"
done < /tmp/dita-rework-files.txt

git add -A && git commit -m "dita-task-title: Remove unsupported block titles

Applied dita-task-title skill to remove unsupported block titles from
procedure modules for DITA compatibility.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

#### 5k. dita-block-title

```bash
while read -r file; do
    ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-block-title/scripts/block_title.rb "$file"
done < /tmp/dita-rework-files.txt

git add -A && git commit -m "dita-block-title: Fix unsupported block titles

Applied dita-block-title skill to convert or remove block titles that
are not valid in DITA (only examples, figures, and tables support titles).

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 6: Validate Changes and Count Fixed Errors

Run `dita-validate-asciidoc` again and compare with the baseline to validate the remediation work.

**IMPORTANT**: Exclude informational rules (ConditionalCode, AttributeReference, IncludeDirective, TagDirective) from before/after counts. List them separately.

```bash
# Run dita-validate-asciidoc to get all AsciiDocDITA issues
bash ${CLAUDE_PLUGIN_ROOT}/skills/dita-validate-asciidoc/scripts/validate_asciidoc.sh "${ASSEMBLY_PATH}" --existing > /tmp/dita-rework-vale-after-all.txt

# Separate actionable issues from informational issues
grep -v -E "AsciiDocDITA\.(ConditionalCode|AttributeReference|IncludeDirective|TagDirective)" /tmp/dita-rework-vale-after-all.txt > /tmp/dita-rework-vale-after.txt || true
grep -E "AsciiDocDITA\.(ConditionalCode|AttributeReference|IncludeDirective|TagDirective)" /tmp/dita-rework-vale-after-all.txt > /tmp/dita-rework-vale-after-info.txt || true

# Count actionable issues before and after
BEFORE_COUNT=$(wc -l < /tmp/dita-rework-vale-before.txt)
AFTER_COUNT=$(wc -l < /tmp/dita-rework-vale-after.txt)
FIXED_COUNT=$((BEFORE_COUNT - AFTER_COUNT))

# Count informational issues
INFO_COUNT=$(wc -l < /tmp/dita-rework-vale-after-info.txt)
```

#### Analyze remaining actionable issues

If actionable issues remain after remediation, categorize them by rule and capture full details:

```bash
# Group remaining actionable issues by rule
echo "Remaining actionable issues by rule:"
grep -oE "AsciiDocDITA\.[A-Za-z]+" /tmp/dita-rework-vale-after.txt | sort | uniq -c | sort -rn

# Display full issue details (file:line:col: severity: [Rule] Message)
echo ""
echo "Issue details:"
cat /tmp/dita-rework-vale-after.txt
```

The Vale output format is: `file:line:col: severity: [Rule] Message`

Parse this to extract:
- **File**: The file path (before first `:`)
- **Line**: The line number (between first and second `:`)
- **Rule**: The rule name in brackets (e.g., `AsciiDocDITA.ShortDescription`)
- **Message**: The descriptive message after the rule name

#### Why issues remain unprocessed

For each remaining issue, determine why it was not fixed by the automated scripts:

| Rule | Reason Not Auto-Fixed |
|------|----------------------|
| **ShortDescription** | Abstract paragraph needs human judgment to write meaningful content |
| **TaskStep** | Complex nested content requires manual review of list structure |
| **BlockTitle** | Ambiguous whether title should become figure caption, example title, or be removed |
| **CalloutList** | Callouts in non-standard format or complex nesting not handled by script |
| **EntityReference** | Entity in attribute, URL, or other context where replacement might break functionality |
| **DocumentId** | ID generation skipped due to complex title or existing conflicting ID |
| **RelatedLinks** | Mixed content in Additional resources requires human decision on what to keep |

Document specific reasons for each remaining issue in the PR/MR description to guide manual remediation.

#### Analyze informational issues

List the informational issues separately (these don't count toward fixed/remaining):

```bash
# Group informational issues by rule
echo "Informational issues (excluded from counts):"
grep -oE "AsciiDocDITA\.[A-Za-z]+" /tmp/dita-rework-vale-after-info.txt | sort | uniq -c | sort -rn
```

**IMPORTANT**: Review any remaining actionable AsciiDocDITA issues. Some may require manual intervention that the automated scripts cannot handle. Document these in the PR/MR description.

### Step 7: Push Branch

Push the branch to the remote:

```bash
# Push the branch
git push -u origin "${BRANCH_NAME}"
```

Inform the user that the branch has been pushed and they can create a PR/MR when ready.

**IMPORTANT**: When creating a PR/MR, always target the **upstream** repository, not the user's fork. If using `gh pr create`, use `--repo <upstream-org>/<repo>` to ensure the PR is opened against upstream.

### Step 8: Write Workflow Summary to File

After completing all steps, write a markdown-formatted summary to a file so the user can copy it for the PR/MR description.

**IMPORTANT**: Use the Write tool to create or overwrite the file `/tmp/dita-rework-pr-summary.md` with the raw markdown content. Do NOT output the summary directly to the CLI as it will be rendered instead of shown as copyable text.

#### Generating the Issue Details table

Before writing the summary, parse the remaining Vale issues to populate the Issue Details table:

1. Read `/tmp/dita-rework-vale-after.txt` which contains lines in Vale output format:
   ```
   file:line:col: severity: [AsciiDocDITA.RuleName] Message text here
   ```

2. For each line, extract:
   - **File:Line**: The file path and line number (before the second `:`)
   - **Rule**: The rule name from brackets (e.g., `ShortDescription` from `[AsciiDocDITA.ShortDescription]`)
   - **Message**: The text after the rule name

3. Look up the "Why Not Auto-Fixed" reason based on the rule name using this mapping:
   - **ShortDescription** → Abstract paragraph needs human judgment to write meaningful content
   - **TaskStep** → Complex nested content requires manual review of list structure
   - **BlockTitle** → Ambiguous whether title should become figure caption, example title, or be removed
   - **CalloutList** → Callouts in non-standard format or complex nesting not handled by script
   - **EntityReference** → Entity in attribute, URL, or other context where replacement might break functionality
   - **DocumentId** → ID generation skipped due to complex title or existing conflicting ID
   - **RelatedLinks** → Mixed content in Additional resources requires human decision on what to keep
   - **Other rules** → Requires manual review

4. Generate a table row for EACH remaining issue (not just one placeholder row)

Write the following template to `/tmp/dita-rework-pr-summary.md`, replacing placeholders with actual values:

```
## Summary

Prepared AsciiDoc files in `<parent_dir>/` for DITA conversion by running the DITA rework workflow.

## Changes Applied

The following DITA cleanup skills were applied in sequence:

1. **dita-content-type**: Added :_mod-docs-content-type: attributes (<count> files)
2. **dita-document-id**: Added missing document IDs (<count> files)
3. **dita-callouts**: Transformed callouts to definition lists (<count> files)
4. **dita-entity-reference**: <status>
5. **dita-line-break**: <status>
6. **dita-related-links**: Cleaned up Additional resources sections (<count> files)
7. **dita-short-description**: Added [role="_abstract"] attributes (<count> files)
8. **dita-task-contents**: <status>
9. **dita-task-step**: Fixed list continuations in procedure steps (<count> files)
10. **dita-task-title**: Removed unsupported block titles (<count> files)
11. **dita-block-title**: Fixed unsupported block titles (<count> files)

## Files Processed

<file_count> files were processed from the assembly and its includes.

## Vale Validation Results (Actionable Issues Only)

| Metric | Count |
|--------|-------|
| Issues before | <before_count> |
| Issues after | <after_count> |
| **Fixed** | **<fixed_count>** |
| Improvement | <percent>% |

### Remaining Actionable Issues

| Rule | Count |
|------|-------|
| <rule_name> | <count> |

#### Issue Details

<!-- Generate one row per issue from /tmp/dita-rework-vale-after.txt -->
<!-- IMPORTANT: Use the FULL relative file path exactly as it appears in Vale output. Do NOT abbreviate or truncate paths with "..." -->
| File:Line | Rule | Message | Why Not Auto-Fixed |
|-----------|------|---------|--------------------|
| upstream/modules/common/backing-up-your-cluster.adoc:42 | ShortDescription | Missing abstract paragraph | Abstract paragraph needs human judgment to write meaningful content |
| upstream/modules/common/configuring-oidc-auth-gateway-api.adoc:15 | BlockTitle | Block title not supported | Ambiguous whether title should become figure caption, example title, or be removed |
<!-- ... one row for each remaining issue, using FULL relative file paths from Vale output ... -->

**Common reasons issues are not auto-fixed:**
- **ShortDescription**: Abstract paragraph needs human judgment to write meaningful content
- **TaskStep**: Complex nested content requires manual review of list structure
- **BlockTitle**: Ambiguous whether title should become figure caption, example title, or be removed
- **CalloutList**: Callouts in non-standard format or complex nesting not handled by script
- **EntityReference**: Entity in attribute, URL, or other context where replacement might break functionality
- **DocumentId**: ID generation skipped due to complex title or existing conflicting ID
- **RelatedLinks**: Mixed content in Additional resources requires human decision on what to keep

### Informational Issues (Excluded from Counts)

The following issues are informational only and excluded from the before/after counts:

| Rule | Count |
|------|-------|
| AsciiDocDITA.ConditionalCode | <count> |
| AsciiDocDITA.AttributeReference | <count> |
| AsciiDocDITA.IncludeDirective | <count> |
| AsciiDocDITA.TagDirective | <count> |

**Note:** Informational issues represent conditional content, attribute references, and include directives that may need manual review for DITA conversion but are not errors.

## Test Plan

- [ ] Verify the AsciiDoc renders correctly
- [ ] Run DITA conversion on the modified files
- [ ] Review definition lists created from callouts
- [ ] Review block title conversions

---
Generated with [Claude Code](https://claude.com/claude-code)
```

After writing the file, inform the user:

```
Branch pushed: ${BRANCH_NAME}

Summary written to /tmp/dita-rework-pr-summary.md

Copy the summary to clipboard:
  cat /tmp/dita-rework-pr-summary.md | xclip -selection clipboard

Suggested MR/PR title:
  Claude Code DITA rework run for <relative_assembly_path>

Create the MR/PR and paste the rework summary into the description field.
```

Replace `<relative_assembly_path>` with the original assembly path argument (e.g., `getting-started/master.adoc`).

## Usage Examples

```bash
# Run DITA rework on an assembly
/dita-tools:dita-rework working-on-projects/master.adoc

# Run on a nested assembly
/dita-tools:dita-rework guides/administration/master.adoc
```

## Notes

- Each skill is run in sequence to avoid conflicts
- A commit is created after each skill for easy rollback
- The workflow requires ruby for running the DITA scripts
- Vale is optional but recommended for tracking improvements
- If any skill fails, the workflow continues with remaining skills
- Empty commits (no changes) are skipped automatically

---

# Phase W: Rewrite Mode (`--rewrite`)

Run Vale to identify AsciiDocDITA issues and use LLM-guided refactoring to fix them through intelligent content rewriting. This workflow creates commits and PR/MR for version control.

## Options

| Option | Description |
|--------|-------------|
| `--no-commit` | Skip commit creation |
| `--dry-run` | Show what would be done without making changes |
| `--branch <name>` | Use custom branch name (default: auto-generated) |

## Workflow Overview

1. **Setup**: Validate input, create working branch
2. **Discover**: If assembly, find all included files using `dita-includes`
3. **Baseline**: Run Vale to establish issue count
4. **Rewrite**: Use LLM-guided refactoring to fix issues (following dita-asciidoc-rewrite skill instructions)
5. **Validate**: Run Vale to confirm issues are resolved
6. **Commit**: Create per-file commits with issue summary
7. **Push**: Push the branch to origin
8. **Summary**: Write a summary file for use in PR/MR description

---

## Rewrite Phase 1: Setup and Analysis

### Step 1: Validate Input

```bash
# Check for required argument
if [ -z "${1}" ]; then
    echo "ERROR: No file path provided"
    echo "Usage: /dita-tools:dita-rework <file.adoc> --rewrite [options]"
    exit 1
fi

# Verify the file/folder exists
test -f "${1}" -o -d "${1}" && echo "Input exists: ${1}" || { echo "ERROR: Not found: ${1}"; exit 1; }
```

If the file does not exist, STOP and inform the user.

### Step 2: Create Working Branch

Unless `--no-commit` or `--dry-run` is set:

```bash
# Generate branch name from input path
INPUT_NAME=$(basename "${1}" .adoc)
BRANCH_NAME="${BRANCH_NAME:-dita-rewrite-${INPUT_NAME}-$(date +%Y%m%d-%H%M%S)}"

# Create and switch to branch
git checkout -b "$BRANCH_NAME"
echo "Created branch: $BRANCH_NAME"
```

### Step 3: Build File List

Determine input type and build list of files to process:

```bash
# Get absolute path
INPUT_ABS=$(realpath "${1}")

if [ -d "${1}" ]; then
    # Folder: find all .adoc files
    echo "Folder detected - finding all AsciiDoc files"
    find "${INPUT_ABS}" -name "*.adoc" -type f > /tmp/dita-rewrite-files.txt
elif grep -q "^include::" "${1}"; then
    # Assembly: use dita-includes skill
    echo "Assembly detected - discovering includes"
    bash ${CLAUDE_PLUGIN_ROOT}/skills/dita-includes/scripts/find_includes.sh "${INPUT_ABS}" --existing > /tmp/dita-rewrite-files.txt
else
    # Single module
    echo "Module detected"
    echo "${INPUT_ABS}" > /tmp/dita-rewrite-files.txt
fi

FILE_COUNT=$(wc -l < /tmp/dita-rewrite-files.txt)
echo "Files to process: ${FILE_COUNT}"
cat /tmp/dita-rewrite-files.txt
```

### Step 4: Run Vale BEFORE (Baseline)

Use the `dita-validate-asciidoc` skill to run Vale with AsciiDocDITA rules:

```bash
# Create output directory
mkdir -p .claude_docs/vale-reports

# Run dita-validate-asciidoc to get all AsciiDocDITA issues
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
bash ${CLAUDE_PLUGIN_ROOT}/skills/dita-validate-asciidoc/scripts/validate_asciidoc.sh "${1}" --existing > /tmp/dita-rewrite-vale-baseline.txt

# Separate actionable from informational issues
grep -v -E "AsciiDocDITA\.(ConditionalCode|AttributeReference|IncludeDirective|TagDirective|CrossReference)" /tmp/dita-rewrite-vale-baseline.txt > /tmp/dita-rewrite-vale-actionable.txt || true

# Count baseline issues
BASELINE_COUNT=$(wc -l < /tmp/dita-rewrite-vale-actionable.txt)
echo ""
echo "=== Baseline Vale Results ==="
echo "Actionable AsciiDocDITA issues: ${BASELINE_COUNT}"
echo ""
echo "Issues by rule:"
grep -oE "AsciiDocDITA\.[A-Za-z]+" /tmp/dita-rewrite-vale-actionable.txt | sort | uniq -c | sort -rn
```

Save the baseline counts for comparison.

---

## Rewrite Phase 2: LLM-Guided Refactoring

For each file in the processing list, apply fixes using the **dita-asciidoc-rewrite skill** instructions.

### For Each File:

1. **Read the file** to understand current content and structure
2. **Review Vale issues** for this specific file from the baseline
3. **Apply fixes** following the AI Action plans in the skill for each issue type:
   - EntityReference, AttributeReference, AuthorLine
   - DocumentId, DocumentTitle, ShortDescription
   - ExampleBlock, TaskExample, NestedSection
   - TaskSection, TaskContents, TaskDuplicate
   - AdmonitionTitle, BlockTitle, ContentType
   - LineBreak, LinkAttribute, TaskStep
   - AssemblyContents, CalloutList, RelatedLinks
4. **Validate** that changes maintain document integrity and flow
5. **Commit** (unless `--no-commit` or `--dry-run`):

```bash
git add "<file>"
git commit -m "$(cat <<'EOF'
fix(<module-name>): DITA compatibility fixes

- Fixed <issue-type-1>
- Fixed <issue-type-2>
...

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

Track which issues were fixed for each file.

---

## Rewrite Phase 3: Validation and Reporting

### Step 1: Run Vale AFTER

Use the `dita-validate-asciidoc` skill to run Vale again and compare with baseline:

```bash
# Run dita-validate-asciidoc to get final AsciiDocDITA issues
bash ${CLAUDE_PLUGIN_ROOT}/skills/dita-validate-asciidoc/scripts/validate_asciidoc.sh "${1}" --existing > /tmp/dita-rewrite-vale-final.txt

# Separate actionable issues
grep -v -E "AsciiDocDITA\.(ConditionalCode|AttributeReference|IncludeDirective|TagDirective|CrossReference)" /tmp/dita-rewrite-vale-final.txt > /tmp/dita-rewrite-vale-final-actionable.txt || true

FINAL_COUNT=$(wc -l < /tmp/dita-rewrite-vale-final-actionable.txt)
TOTAL_FIXED=$((BASELINE_COUNT - FINAL_COUNT))

echo ""
echo "=== Final Results ==="
echo "Baseline issues: ${BASELINE_COUNT}"
echo "Final issues: ${FINAL_COUNT}"
echo "Total fixed: ${TOTAL_FIXED}"
if [ ${BASELINE_COUNT} -gt 0 ]; then
    echo "Improvement: $(( (TOTAL_FIXED * 100) / BASELINE_COUNT ))%"
fi
```

### Step 2: Write Workflow Summary to File

After completing all steps, write a markdown-formatted summary to a file so the user can copy it for the PR/MR description.

**IMPORTANT**: Use the Write tool to create or overwrite the file `/tmp/dita-rewrite-pr-summary.md` with the raw markdown content. Do NOT output the summary directly to the CLI as it will be rendered instead of shown as copyable text.

#### Generating the Issue Details table

Before writing the summary, parse the remaining Vale issues to populate the Issue Details table:

1. Read `/tmp/dita-rewrite-vale-final-actionable.txt` which contains lines in Vale output format:
   ```
   file:line:col: severity: [AsciiDocDITA.RuleName] Message text here
   ```

2. For each line, extract:
   - **File:Line**: The file path and line number (before the second `:`)
   - **Rule**: The rule name from brackets (e.g., `ShortDescription` from `[AsciiDocDITA.ShortDescription]`)
   - **Message**: The text after the rule name

3. Look up the "Why Not Auto-Fixed" reason based on the rule name using this mapping:
   - **ShortDescription** → Abstract paragraph needs human judgment to write meaningful content
   - **TaskStep** → Complex nested content requires manual review of list structure
   - **BlockTitle** → Ambiguous whether title should become figure caption, example title, or be removed
   - **CalloutList** → Callouts in non-standard format or complex nesting not handled by script
   - **EntityReference** → Entity in attribute, URL, or other context where replacement might break functionality
   - **DocumentId** → ID generation skipped due to complex title or existing conflicting ID
   - **RelatedLinks** → Mixed content in Additional resources requires human decision on what to keep
   - **Other rules** → Requires manual review

4. Generate a table row for EACH remaining issue (not just one placeholder row)

Write the following template to `/tmp/dita-rewrite-pr-summary.md`, replacing placeholders with actual values:

```
## Summary

Refactored AsciiDoc files in `<input_path>` for DITA conversion compatibility using LLM-guided rewriting.

## Changes Applied

The following DITA issues were fixed through LLM-guided refactoring:

- **EntityReference**: Replaced HTML entities with Unicode equivalents
- **DocumentId**: Added missing document IDs
- **ShortDescription**: Added or improved [role="_abstract"] paragraphs
- **TaskStep**: Fixed list continuations in procedure steps
- **BlockTitle**: Converted or removed unsupported block titles
- **RelatedLinks**: Cleaned up Additional resources sections
- (list all issue types that were actually fixed)

## Files Processed

<file_count> files were processed.

| File | Issues Before | Issues After | Fixed |
|------|---------------|--------------|-------|
| <file1.adoc> | <before> | <after> | <fixed> |
| <file2.adoc> | <before> | <after> | <fixed> |

## Vale Validation Results (Actionable Issues Only)

| Metric | Count |
|--------|-------|
| Issues before | <before_count> |
| Issues after | <after_count> |
| **Fixed** | **<fixed_count>** |
| Improvement | <percent>% |

### Remaining Actionable Issues

| Rule | Count |
|------|-------|
| <rule_name> | <count> |

#### Issue Details

<!-- Generate one row per issue from /tmp/dita-rewrite-vale-final-actionable.txt -->
<!-- IMPORTANT: Use the FULL relative file path exactly as it appears in Vale output. Do NOT abbreviate or truncate paths with "..." -->
| File:Line | Rule | Message | Why Not Auto-Fixed |
|-----------|------|---------|--------------------|
| upstream/modules/common/backing-up-your-cluster.adoc:42 | ShortDescription | Missing abstract paragraph | Abstract paragraph needs human judgment to write meaningful content |
| upstream/modules/common/configuring-oidc-auth-gateway-api.adoc:15 | BlockTitle | Block title not supported | Ambiguous whether title should become figure caption, example title, or be removed |
<!-- ... one row for each remaining issue, using FULL relative file paths from Vale output ... -->

**Common reasons issues are not auto-fixed:**
- **ShortDescription**: Abstract paragraph needs human judgment to write meaningful content
- **TaskStep**: Complex nested content requires manual review of list structure
- **BlockTitle**: Ambiguous whether title should become figure caption, example title, or be removed
- **CalloutList**: Callouts in non-standard format or complex nesting not handled by script
- **EntityReference**: Entity in attribute, URL, or other context where replacement might break functionality
- **DocumentId**: ID generation skipped due to complex title or existing conflicting ID
- **RelatedLinks**: Mixed content in Additional resources requires human decision on what to keep

### Informational Issues (Excluded from Counts)

The following issues are informational only and excluded from the before/after counts:

| Rule | Count |
|------|-------|
| AsciiDocDITA.ConditionalCode | <count> |
| AsciiDocDITA.AttributeReference | <count> |
| AsciiDocDITA.IncludeDirective | <count> |
| AsciiDocDITA.TagDirective | <count> |
| AsciiDocDITA.CrossReference | <count> |

**Note:** Informational issues represent conditional content, attribute references, cross-references, and include directives that may need manual review for DITA conversion but are not errors.

## Test Plan

- [ ] Verify the AsciiDoc renders correctly
- [ ] Run DITA conversion on the modified files
- [ ] Content meaning preserved
- [ ] Links and cross-references work

---
Generated with [Claude Code](https://claude.com/claude-code)
```

After writing the file, inform the user:

```
Branch pushed: ${BRANCH_NAME}

Summary written to /tmp/dita-rewrite-pr-summary.md

Copy the summary to clipboard:
  cat /tmp/dita-rewrite-pr-summary.md | xclip -selection clipboard

Suggested MR/PR title:
  Claude Code DITA rewrite run for <input_path>

Create the MR/PR and paste the rewrite summary into the description field.
```

Replace `<input_path>` with the original input path argument.

---

## Rewrite Phase 4: Push Branch

Unless `--no-commit` or `--dry-run` is set:

```bash
git push -u origin "$BRANCH_NAME"
```

Inform the user that the branch has been pushed and they can create a PR/MR when ready.

**IMPORTANT**: When creating a PR/MR, always target the **upstream** repository, not the user's fork. If using `gh pr create`, use `--repo <upstream-org>/<repo>` to ensure the PR is opened against upstream.

---

## Rewrite Usage Examples

```bash
# Single module
/dita-tools:dita-rework modules/installing/proc_installing-component.adoc --rewrite

# Assembly with all includes
/dita-tools:dita-rework assemblies/installing.adoc --rewrite

# Folder of modules
/dita-tools:dita-rework modules/configuring/ --rewrite

# Dry run (preview only)
/dita-tools:dita-rework modules/installing/ --rewrite --dry-run

# Custom branch name
/dita-tools:dita-rework assemblies/admin.adoc --rewrite --branch dita-admin-fixes
```

## Rewrite Notes

- This workflow uses **only** LLM-guided refactoring (no automated Ruby scripts)
- The **dita-asciidoc-rewrite skill** provides detailed fixing instructions for 22+ issue types — invoke it with `/dita-tools:dita-asciidoc-rewrite` for the fixing guidelines
- Each file is processed individually with contextual understanding
- Vale is used before and after to measure progress
- Commits are created per-file for easy review and potential revert
- Informational issues (AttributeReference, CrossReference, etc.) are reported but not fixed

---

# Phase R: Review Mode (`--review`)

Review DITA rework and rewrite changes by comparing the current version of a file against the upstream/main version. For assemblies, the workflow reduces both versions to single flattened documents for comprehensive content comparison.

## Prerequisites

**Run this command after completing a DITA rework or rewrite workflow:**

1. Run `/dita-tools:dita-rework <assembly.adoc>` or `/dita-tools:dita-rework <file.adoc> --rewrite`
2. Remain on the feature branch created by the rework/rewrite command
3. Run this review command to validate the changes before creating a PR/MR

This command assumes you are on a branch with DITA rework changes and compares against `upstream/main` or `origin/main`.

## Review Workflow Overview

1. **Build Check**: Run asciidoctor to verify file builds without errors
2. **Setup**: Validate input file exists and has changes vs upstream
3. **Detect Type**: Determine if file is an assembly or module
4. **Prepare Comparison**:
   - For assemblies: Reduce both current and upstream/main versions
   - For modules: Compare files directly
5. **Generate Diff**: Compare the two versions
6. **Analyze Changes**: Identify content modifications, additions, and deletions
7. **Produce Review**: Output structured review with module-level change tracking

---

## Review Phase 1: Build Check (GATE)

**CRITICAL**: Before any other processing, verify the reworked file builds successfully with asciidoctor. If errors are found, STOP and help fix them.

### Step 1: Run Asciidoctor Check

```bash
FILE_PATH="${1}"

# Run asciidoctor build check
bash ${CLAUDE_PLUGIN_ROOT}/skills/dita-check-asciidoctor/scripts/check_asciidoctor.sh "${FILE_PATH}"
EXIT_CODE=$?

if [ ${EXIT_CODE} -eq 2 ]; then
    echo ""
    echo "ERROR: Asciidoctor build failed with errors."
    echo "The reworked file has syntax errors that must be fixed before review."
    echo ""
    echo "Review the errors above and fix them before proceeding."
    exit 1
fi

if [ ${EXIT_CODE} -eq 1 ]; then
    echo ""
    echo "WARNING: Asciidoctor build completed with warnings."
    echo "Continuing with review, but consider addressing warnings."
    echo ""
fi
```

### Step 2: Handle Build Errors

If the asciidoctor check returns exit code 2 (errors found):

1. **STOP all further processing** — Do not continue to diff generation or review
2. **Read the source file** at the line numbers reported in the errors
3. **Identify the issue** — Look for:
   - Unclosed conditionals (`ifdef::` without `endif::[]`)
   - Unclosed admonition blocks (`====` without closing pair)
   - Unclosed code/listing blocks (`----` without closing pair)
   - Unclosed open blocks (`--` without closing pair)
   - Missing include files
   - Malformed attributes
4. **Suggest specific fixes** — Provide the exact edits needed to fix each error
5. **Offer to apply fixes** — Ask the user if they want you to fix the issues

**Example response when errors are found:**

```
BUILD CHECK FAILED

The file has asciidoctor errors that must be fixed before review can proceed.

Errors found:
1. Line 45: Unclosed conditional block
   - Found `ifdef::openshift[]` without matching `endif::[]`
   - Fix: Add `endif::[]` after the conditional content

2. Line 78: Unclosed code block
   - The `----` delimiter at line 72 is not closed
   - Fix: Add `----` after line 77

Would you like me to apply these fixes?
```

---

## Review Phase 2: Setup and Validation

### Step 1: Validate Input

```bash
# Check for required argument
if [ -z "${1}" ]; then
    echo "ERROR: No file path provided"
    echo "Usage: /dita-tools:dita-rework <file.adoc> --review"
    exit 1
fi

# Verify the file exists
test -f "${1}" && echo "File exists: ${1}" || { echo "ERROR: Not found: ${1}"; exit 1; }
```

If the file does not exist, STOP and inform the user.

### Step 2: Check Git Status

Verify the file has changes compared to upstream/main:

```bash
# Get the file path
FILE_PATH="${1}"

# Check if the file has changes against upstream/main
git diff upstream/main -- "${FILE_PATH}" > /dev/null 2>&1 || git diff origin/main -- "${FILE_PATH}" > /dev/null 2>&1

# Determine the upstream ref to use
if git rev-parse --verify upstream/main > /dev/null 2>&1; then
    UPSTREAM_REF="upstream/main"
elif git rev-parse --verify origin/main > /dev/null 2>&1; then
    UPSTREAM_REF="origin/main"
else
    echo "ERROR: Neither upstream/main nor origin/main found"
    exit 1
fi

echo "Using upstream reference: ${UPSTREAM_REF}"
```

### Step 3: Detect File Type

Determine if the input is an assembly (contains includes) or a module:

```bash
FILE_PATH="${1}"

# Check if file contains include directives
if grep -q "^include::" "${FILE_PATH}"; then
    echo "File type: ASSEMBLY (contains include directives)"
    FILE_TYPE="assembly"
else
    echo "File type: MODULE (no include directives)"
    FILE_TYPE="module"
fi
```

---

## Review Phase 3: Prepare Comparison Files

### For Assemblies

When the input is an assembly, use `dita-reduce-asciidoc` to create flattened versions of both current and upstream/main:

#### Step A: Create Reduced Version of Current File

```bash
FILE_PATH="${1}"
FILE_DIR=$(dirname "${FILE_PATH}")
FILE_NAME=$(basename "${FILE_PATH}" .adoc)

# Create temp directory for comparison files
REVIEW_DIR="/tmp/dita-rework-review"
mkdir -p "${REVIEW_DIR}"

# Reduce the current version
ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-reduce-asciidoc/scripts/reduce_asciidoc.rb "${FILE_PATH}" -o "${REVIEW_DIR}/${FILE_NAME}-current-reduced.adoc"

echo "Created reduced current version: ${REVIEW_DIR}/${FILE_NAME}-current-reduced.adoc"
```

#### Step B: Create Reduced Version of Upstream/Main File

```bash
# Get the upstream/main version of the assembly
git show "${UPSTREAM_REF}:${FILE_PATH}" > "${REVIEW_DIR}/${FILE_NAME}-upstream.adoc"

# For assembly reduction, we need to temporarily create the upstream file structure
# Create a temporary working directory
UPSTREAM_WORK_DIR="${REVIEW_DIR}/upstream-work"
mkdir -p "${UPSTREAM_WORK_DIR}"

# Get the directory structure from the assembly
ASSEMBLY_DIR=$(dirname "${FILE_PATH}")

# Extract all included files from upstream/main
echo "Extracting upstream/main file tree for reduction..."

# Get list of includes from the upstream assembly
bash ${CLAUDE_PLUGIN_ROOT}/skills/dita-includes/scripts/find_includes.sh "${FILE_PATH}" --relative 2>/dev/null | while read -r include_file; do
    if [ -n "${include_file}" ]; then
        # Create parent directory in temp location
        include_dir=$(dirname "${include_file}")
        mkdir -p "${UPSTREAM_WORK_DIR}/${include_dir}"
        # Extract the upstream version
        git show "${UPSTREAM_REF}:${include_file}" > "${UPSTREAM_WORK_DIR}/${include_file}" 2>/dev/null || true
    fi
done

# Also extract the main assembly file
mkdir -p "${UPSTREAM_WORK_DIR}/${ASSEMBLY_DIR}"
git show "${UPSTREAM_REF}:${FILE_PATH}" > "${UPSTREAM_WORK_DIR}/${FILE_PATH}"

# Run asciidoctor-reducer on the upstream assembly
cd "${UPSTREAM_WORK_DIR}"
ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-reduce-asciidoc/scripts/reduce_asciidoc.rb "${FILE_PATH}" -o "${REVIEW_DIR}/${FILE_NAME}-upstream-reduced.adoc" 2>/dev/null || {
    # Fallback: if reduction fails, use the raw upstream assembly
    cp "${UPSTREAM_WORK_DIR}/${FILE_PATH}" "${REVIEW_DIR}/${FILE_NAME}-upstream-reduced.adoc"
    echo "Warning: Upstream reduction failed, using non-reduced upstream file"
}
cd -

echo "Created reduced upstream version: ${REVIEW_DIR}/${FILE_NAME}-upstream-reduced.adoc"
```

#### Step C: Render to HTML and Extract Text

Render both reduced AsciiDoc files to HTML, then convert to plain text for content-level comparison that ignores markup differences:

```bash
# Render current reduced AsciiDoc to HTML
asciidoctor -o "${REVIEW_DIR}/${FILE_NAME}-current.html" "${REVIEW_DIR}/${FILE_NAME}-current-reduced.adoc"

# Render upstream reduced AsciiDoc to HTML
asciidoctor -o "${REVIEW_DIR}/${FILE_NAME}-upstream.html" "${REVIEW_DIR}/${FILE_NAME}-upstream-reduced.adoc"

# Convert current HTML to plain text
python3 -c "
import html2text
h = html2text.HTML2Text()
h.ignore_links = False
h.ignore_images = True
h.body_width = 0
with open('${REVIEW_DIR}/${FILE_NAME}-current.html', 'r') as f:
    print(h.handle(f.read()))
" > "${REVIEW_DIR}/${FILE_NAME}-current.txt"

# Convert upstream HTML to plain text
python3 -c "
import html2text
h = html2text.HTML2Text()
h.ignore_links = False
h.ignore_images = True
h.body_width = 0
with open('${REVIEW_DIR}/${FILE_NAME}-upstream.html', 'r') as f:
    print(h.handle(f.read()))
" > "${REVIEW_DIR}/${FILE_NAME}-upstream.txt"

echo "Rendered and extracted text for content comparison"
```

#### Step D: Set Comparison File Paths

```bash
CURRENT_FILE="${REVIEW_DIR}/${FILE_NAME}-current.txt"
UPSTREAM_FILE="${REVIEW_DIR}/${FILE_NAME}-upstream.txt"
```

### For Modules

When the input is a module, compare files directly without reduction:

```bash
FILE_PATH="${1}"
FILE_NAME=$(basename "${FILE_PATH}" .adoc)

# Create temp directory
REVIEW_DIR="/tmp/dita-rework-review"
mkdir -p "${REVIEW_DIR}"

# Get upstream version
git show "${UPSTREAM_REF}:${FILE_PATH}" > "${REVIEW_DIR}/${FILE_NAME}-upstream.adoc"

# Render current module to HTML
asciidoctor -o "${REVIEW_DIR}/${FILE_NAME}-current.html" "${FILE_PATH}"

# Render upstream module to HTML
asciidoctor -o "${REVIEW_DIR}/${FILE_NAME}-upstream.html" "${REVIEW_DIR}/${FILE_NAME}-upstream.adoc"

# Convert current HTML to plain text
python3 -c "
import html2text
h = html2text.HTML2Text()
h.ignore_links = False
h.ignore_images = True
h.body_width = 0
with open('${REVIEW_DIR}/${FILE_NAME}-current.html', 'r') as f:
    print(h.handle(f.read()))
" > "${REVIEW_DIR}/${FILE_NAME}-current.txt"

# Convert upstream HTML to plain text
python3 -c "
import html2text
h = html2text.HTML2Text()
h.ignore_links = False
h.ignore_images = True
h.body_width = 0
with open('${REVIEW_DIR}/${FILE_NAME}-upstream.html', 'r') as f:
    print(h.handle(f.read()))
" > "${REVIEW_DIR}/${FILE_NAME}-upstream.txt"

# Set comparison paths to plain text files
CURRENT_FILE="${REVIEW_DIR}/${FILE_NAME}-current.txt"
UPSTREAM_FILE="${REVIEW_DIR}/${FILE_NAME}-upstream.txt"
```

---

## Review Phase 4: Generate Diff and Analyze

### Step 1: Generate Rendered Content Diff

```bash
# Generate rendered content diff
diff -u "${UPSTREAM_FILE}" "${CURRENT_FILE}" > "${REVIEW_DIR}/changes.diff" || true

# Count additions and deletions
ADDITIONS=$(grep -c "^+" "${REVIEW_DIR}/changes.diff" 2>/dev/null | grep -v "^+++" || echo 0)
DELETIONS=$(grep -c "^-" "${REVIEW_DIR}/changes.diff" 2>/dev/null | grep -v "^---" || echo 0)

echo "Changes detected:"
echo "  Lines added: ${ADDITIONS}"
echo "  Lines removed: ${DELETIONS}"
```

### Step 2: Identify Modified Sections

For assemblies, track which modules have changed by parsing the reduced content:

```bash
# If assembly, identify module boundaries in the diff
if [ "${FILE_TYPE}" = "assembly" ]; then
    echo ""
    echo "Analyzing module-level changes..."

    # Extract section headers from the diff to identify affected modules
    # Sections typically start with = or == markers
    grep -E "^[-+]= " "${REVIEW_DIR}/changes.diff" 2>/dev/null || echo "No section header changes found"
fi
```

### Step 3: Analyze Content Changes

Use the Read tool to examine the diff and identify:

1. **Content additions** — New paragraphs, sections, or elements
2. **Content deletions** — Removed content that may have been important
3. **Content modifications** — Changed wording, rewritten sections
4. **Structural changes** — Reordered content, moved sections
5. **Potential issues** — Malformed markup, broken cross-references

Read both the diff file and the two reduced files to perform a comprehensive analysis.

---

## Review Phase 5: Track Module-Level Changes

For assemblies, identify which individual modules were modified:

### Step 1: Get List of Changed Files

```bash
FILE_PATH="${1}"

# Get list of included files
bash ${CLAUDE_PLUGIN_ROOT}/skills/dita-includes/scripts/find_includes.sh "${FILE_PATH}" --existing > "${REVIEW_DIR}/current-includes.txt"

# For each include, check if it differs from upstream
echo ""
echo "=== Module-Level Change Analysis ==="
echo ""

while read -r module_path; do
    if [ -n "${module_path}" ]; then
        # Check if module has changes vs upstream
        if git diff --quiet "${UPSTREAM_REF}" -- "${module_path}" 2>/dev/null; then
            : # No changes
        else
            echo "MODIFIED: ${module_path}"
            # Get summary of changes for this module
            git diff --stat "${UPSTREAM_REF}" -- "${module_path}" 2>/dev/null || true
        fi
    fi
done < "${REVIEW_DIR}/current-includes.txt"
```

### Step 2: Categorize Module Changes

For each modified module, categorize the type of changes:

- **Formatting only** — Whitespace, line breaks, attribute formatting
- **Content changes** — Text modifications, rewrites
- **Structural changes** — Section reorganization, list modifications
- **DITA fixes** — Changes made by DITA rework tools

---

## Review Phase 6: Produce Review Output

Generate a structured review report. Use the Write tool to create the report file:

**IMPORTANT**: Use the Write tool to create `/tmp/dita-rework-review-report.md` with the complete review.

### Review Report Template

Write the following structure to `/tmp/dita-rework-review-report.md`:

```
# DITA Rework Review Report

**File reviewed**: <file_path>
**Upstream reference**: <upstream_ref>
**File type**: <assembly|module>
**Review date**: <timestamp>

---

## Summary

| Metric | Count |
|--------|-------|
| Lines added | <count> |
| Lines removed | <count> |
| Modules modified | <count> |

## Content Analysis

### Added Content

<!-- List any significant content additions -->
- <description of addition>
- <location and impact>

### Removed Content

<!-- List any content that was removed - FLAG if important content appears missing -->
- <description of removal>
- <assessment: intentional removal or potential issue?>

### Modified Content

<!-- List significant content modifications -->
- <description of change>
- <assessment: improvement, neutral, or potential issue?>

### Structural Changes

<!-- List any structural reorganization -->
- <description of structural change>

## Module Change Report

<!-- Only for assemblies - list each modified module -->
| Module | Change Type | Summary |
|--------|-------------|---------|
| <module_path> | <formatting|content|structural> | <brief description> |

## Potential Issues

<!-- Flag any concerns for reviewer attention -->

### Missing Content
<!-- Content that appears to have been accidentally removed -->
- [ ] <issue description>

### Malformed Markup
<!-- AsciiDoc syntax that may be broken -->
- [ ] <issue description>

### Broken References
<!-- Cross-references or links that may be broken -->
- [ ] <issue description>

### Style Concerns
<!-- Content that may not follow guidelines -->
- [ ] <issue description>

## Recommendations

<!-- Provide actionable recommendations -->
1. <recommendation>
2. <recommendation>

---

## Rendered Content Diff

<details>
<summary>Click to expand full rendered content diff</summary>

\`\`\`diff
<contents of changes.diff>
\`\`\`

</details>

---
Generated with [Claude Code](https://claude.com/claude-code)
```

### Report Generation Instructions

1. **Read the diff file** at `${REVIEW_DIR}/changes.diff`
2. **Read both rendered text files** to understand the full content:
   - `${CURRENT_FILE}` — Current version (rendered plain text)
   - `${UPSTREAM_FILE}` — Upstream/main version (rendered plain text)
3. **Read the reduced AsciiDoc files** if markup-level context is needed:
   - `${REVIEW_DIR}/${FILE_NAME}-current-reduced.adoc` (assemblies) or the original file (modules)
   - `${REVIEW_DIR}/${FILE_NAME}-upstream-reduced.adoc` or `${REVIEW_DIR}/${FILE_NAME}-upstream.adoc`
4. **Analyze the changes** to populate each section of the report
5. **Flag potential issues** such as:
   - Content that appears accidentally removed
   - Malformed AsciiDoc syntax introduced
   - Broken cross-references or includes
   - Missing abstract paragraphs or IDs
6. **Write the report** using the Write tool to `/tmp/dita-rework-review-report.md`

---

## Review Phase 7: Display Results

After generating the report:

```bash
echo ""
echo "=== Review Complete ==="
echo ""
echo "Review report written to: /tmp/dita-rework-review-report.md"
echo ""
echo "To view the report:"
echo "  cat /tmp/dita-rework-review-report.md"
echo ""
echo "To copy to clipboard:"
echo "  cat /tmp/dita-rework-review-report.md | xclip -selection clipboard"
```

Display a summary of key findings to the user in the CLI output.

---

## Review Usage Examples

```bash
# Review after default rework
/dita-tools:dita-rework guides/admin/master.adoc
/dita-tools:dita-rework guides/admin/master.adoc --review

# Review after rewrite
/dita-tools:dita-rework modules/installing/ --rewrite
/dita-tools:dita-rework modules/installing/proc-install-component.adoc --review

# Review an assembly
/dita-tools:dita-rework assemblies/installing.adoc --review

# Review on an existing rework branch
git checkout guides-admin-dita-rework
/dita-tools:dita-rework guides/admin/master.adoc --review
```

## Review Notes

- **Post-rework review**: This mode is designed to run after the default rework or `--rewrite` to validate changes before PR/MR creation
- **Read-only**: This mode does not modify files — it only analyzes and reports
- **Assembly reduction**: For assemblies, both versions are reduced to enable content-level comparison across all included modules
- **HTML-rendered comparison**: Both versions are rendered to HTML via asciidoctor and converted to plain text via html2text, so the diff shows only content changes visible to the reader, not markup noise (added attributes, IDs, block titles, etc.)
- **Module tracking**: For assemblies, the report identifies which individual modules were modified
- **Human review**: Potential issues are flagged but require human judgment to assess
- **Rendered content diff included**: The full rendered content diff is included in the report for detailed inspection
