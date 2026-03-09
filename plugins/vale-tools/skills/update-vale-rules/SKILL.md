---
name: update-vale-rules
description: Run Vale RedHat rules against PR/MR changed files only, analyze output for false positives with 90%+ certainty, and create a PR to update vale-at-red-hat rules. Use this skill when asked to improve Vale rules, find false positives in a PR, or update the Vale at Red Hat style guide.
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Bash(git diff:*), Bash(git log:*), Bash(vale:*), Bash(gh:*), Bash(python:*), Glob, Read, Edit, Write, Grep
---

# Update Vale Rules skill

Detect false positives in Vale RedHat rules by analyzing only the changed files in a PR/MR, then raise a PR against [vale-at-red-hat](https://github.com/redhat-documentation/vale-at-red-hat) to fix confirmed false positives.

## Key principles

- **Scope**: Only run Vale against files changed in the current PR/MR — never the entire repo.
- **Certainty threshold**: Only flag a Vale alert as a false positive when you are 90%+ certain it is wrong. When in doubt, leave it.
- **Target repo**: PRs with rule fixes go to `https://github.com/redhat-documentation/vale-at-red-hat` (from the user's fork).

## Workflow

### 1. Identify changed files

Get the list of documentation files changed in the current branch compared to the base branch:

```bash
# Detect the base branch (main or master)
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

# List changed adoc/md files only
git diff --name-only --diff-filter=ACMR "$BASE"...HEAD -- '*.adoc' '*.md'
```

If no changed documentation files are found, inform the user and stop.

### 2. Create a minimal RedHat-only Vale config

Write a temporary config that uses only the RedHat style package:

```bash
cat <<-'EOF' > .work/update-rh-vale.ini
StylesPath = .vale/styles
MinAlertLevel = suggestion
Packages = RedHat

[*.adoc]
BasedOnStyles = RedHat

[*.md]
BasedOnStyles = RedHat
EOF
```

### 3. Sync Vale styles

```bash
vale --config=.work/update-rh-vale.ini sync
```

### 4. Run Vale against changed files only

```bash
vale --config=.work/update-rh-vale.ini --output=JSON <changed-files>
```

Parse the JSON output. If no alerts are found, inform the user and stop.

### 5. Read and understand the triggering rule

Before judging any alert, **read the actual rule YAML file** that triggered it. The rule files live in `.vale/styles/RedHat/` (downloaded by `vale sync`).

For each unique rule that fired:

```bash
# Example: if the alert is from RedHat.TermsWarnings, read:
cat .vale/styles/RedHat/TermsWarnings.yml
```

Understand:
- **`extends`**: The rule type (e.g., `substitution`, `existence`, `occurrence`, `consistency`)
- **`message`**: What the rule is checking for
- **`level`**: `suggestion`, `warning`, or `error`
- **`tokens`** or **`swap`**: The specific patterns or substitution pairs the rule matches
- **`exceptions`**: Any existing exceptions already defined
- **`filters`**: Any existing filter patterns

This understanding is critical for:
- Determining whether the alert is truly a false positive or the rule is working as intended
- Knowing the correct mechanism to add an exception (e.g., `exceptions:` list vs `filters:` pattern)
- Avoiding duplicate exceptions that already exist
- Writing accurate PR descriptions that reference the rule's purpose

### 6. Analyze each alert for false positives

For each unique Vale alert (deduplicated by rule + match text), determine whether it is a genuine style violation or a false positive.

**Read the surrounding context** (at least 5 lines before and after) from the source file to understand usage. **Cross-reference with the rule YAML** to understand exactly what the rule is checking and why it fired.

**A false positive exists when:**
- The matched text is a valid technical term, product name, or proper noun in context
- The context makes the flagged usage correct (e.g., a code reference, CLI command, API name)
- The rule pattern is too broad and matches legitimate domain-specific language
- The suggestion would make the text technically inaccurate
- The rule's `swap` or `tokens` list matches a term that has a different meaning in this technical domain

**NOT a false positive when:**
- The flagged text genuinely violates the style guide
- An alternative phrasing exists that is both correct and style-compliant
- The match is ambiguous — when in doubt, it is NOT a false positive
- The rule's `message` correctly identifies a real style issue in this context

**Assign a confidence score (0-100%) to each determination.** Only proceed with alerts scored at 90% or above as confirmed false positives.

### 7. Report findings to the user

Present a summary table:

```
| Rule | Match | Confidence | Determination |
|------|-------|------------|---------------|
| RedHat.Foo | "matched text" | 95% | False positive — valid product name |
| RedHat.Bar | "other text" | 72% | Uncertain — skipping |
```

If no false positives meet the 90% threshold, inform the user and stop.

### 8. Raise a PR against vale-at-red-hat

Only proceed if the user confirms. The PR targets the user's fork of `https://github.com/redhat-documentation/vale-at-red-hat`.

**Prerequisites** (verify before proceeding):
- The user has a fork of `redhat-documentation/vale-at-red-hat`
- The fork is cloned locally or accessible via `gh`
- `gh` CLI is authenticated

**Steps:**

1. Clone or locate the user's fork of vale-at-red-hat
2. Create a branch: `vale-fp-fix-<short-description>`
3. For each confirmed false positive (90%+), update the corresponding rule YAML file in the clone's `.vale/styles/RedHat/`:
   - Use the mechanism appropriate for the rule type (learned in step 5):
     - For `substitution` rules: add the term to `exceptions:`
     - For `existence` rules: add the term to `exceptions:` or refine `tokens:`
     - For `consistency` rules: adjust the `swap:` pairs or add `exceptions:`
     - For rules with `filters:`: add a filter pattern to exclude the match
   - Do NOT duplicate exceptions that already exist in the rule file
4. Update corresponding test fixtures if they exist in `.vale/fixtures/RedHat/`
5. Commit with a descriptive message explaining which false positives were found and in which repo
6. Push and create a PR against `redhat-documentation/vale-at-red-hat` main branch

**PR template:**

```markdown
## False positives identified in <repo-name>

Analyzed changed files in PR/MR and identified the following false positives
with 90%+ certainty:

| Rule | Match | Confidence | Reason |
|------|-------|------------|--------|
| ... | ... | ...% | ... |

### Changes
- Updated rule files in `.vale/styles/RedHat/` to add exceptions

### How to verify
- Run Vale against the original files — the false positives should no longer trigger

Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>
```

## Example invocations

- "Check my PR for Vale false positives and fix them upstream"
- "Run Vale on my changed files and update the RedHat rules"
- "Find false positives in this branch's docs changes"
- "Analyze Vale alerts on my PR and raise fixes to vale-at-red-hat"

## Prerequisites

- Vale CLI installed (`brew install vale` or `dnf install vale`)
- Git and GitHub CLI (`gh`) configured and authenticated
- A fork of `redhat-documentation/vale-at-red-hat`
- Current branch has documentation changes compared to the base branch
