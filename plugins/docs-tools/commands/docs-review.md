---
description: Multi-agent documentation review with confidence scoring — local, PR/MR, or action comments
argument-hint: "[--local | --pr <url> [--post-comments] | --action-comments [url]] [--threshold <0-100>]"
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, WebFetch, Task, AskUserQuestion
---

## Name

docs-tools:docs-review

## Synopsis

`/docs-tools:docs-review [--local | --pr <url> [--post-comments] | --action-comments [url]] [--threshold <0-100>]`

## Description

A unified multi-agent documentation review command with confidence-based scoring. Supports four modes:

- `--local` — Review changes in the current branch against main/master
- `--pr <url>` — Review changes in a GitHub PR or GitLab MR
- `--pr <url> --post-comments` — Review and post inline comments to PR/MR
- `--action-comments [url]` — Interactively action unresolved PR/MR review comments (auto-detects PR from current branch if URL omitted)

## Mode Selection

Parse the arguments to determine the mode:

| Argument | Mode | Description |
|----------|------|-------------|
| `--local` | Local review | Review documentation changes in current branch vs base branch |
| `--pr <url>` | PR/MR review | Review documentation changes in a GitHub PR or GitLab MR |
| `--pr <url> --post-comments` | PR/MR review + post | Review and post inline comments to PR/MR |
| `--action-comments [url]` | Action comments | Fetch and interactively action unresolved PR/MR review comments. URL is optional — if omitted, auto-detects the PR/MR for the current branch. |
| *(no arguments)* | Error | Display usage and ask user to specify a mode |

## Global Options

- `--threshold <0-100>` — Confidence threshold for reporting issues (default: 80). Only issues scoring at or above this threshold are reported. Applies to `--local` and `--pr` modes.

If no arguments are provided, display:

```
Usage: /docs-tools:docs-review <mode> [options]

Modes:
  --local                          Review changes in current branch against main/master
  --pr <url>                       Review changes in a GitHub PR or GitLab MR
  --pr <url> --post-comments       Review and post inline comments to PR/MR
  --action-comments [url]          Interactively action unresolved PR/MR review comments
                                   (auto-detects PR from current branch if URL omitted)

Options:
  --threshold <0-100>              Confidence threshold (default: 80)

Supported URL formats:
  GitHub: https://github.com/owner/repo/pull/123
  GitLab: https://gitlab.com/group/project/-/merge_requests/123
```

---

## Implementation

# Agent Assumptions

These apply to ALL agents and subagents across all modes:

- All tools are functional and will work without error. Do not test tools or make exploratory calls. Make sure this is clear to every subagent that is launched.
- Only call a tool if it is required to complete the task. Every tool call should have a clear purpose.
- The confidence threshold is 80 by default (adjustable with `--threshold`). Only issues scoring at or above this threshold are reported.

---

# Multi-Agent Review Pipeline

The `--local` and `--pr` modes share the same multi-agent review pipeline. The only difference is how files are discovered and how results are delivered.

## Step 1: Pre-flight Checks

Resolve the plugin root directory first — all subsequent steps use it to locate scripts and agent files:

```bash
CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
```

### For --pr mode

Launch a haiku agent to check if any of the following are true:
- The pull request is closed
- The pull request is a draft
- The pull request does not need documentation review (e.g. automated PR, code-only change with no .adoc or .md files)
- Claude has already commented on this PR (check `gh pr view <PR> --comments` for comments left by claude)

If any condition is true, stop and do not proceed.

Note: Still review Claude-generated PRs.

### For --local mode

```bash
# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"

# Detect base branch (prefer main, fall back to master)
if git show-ref --verify --quiet refs/heads/main; then
    BASE_BRANCH="main"
elif git show-ref --verify --quiet refs/heads/master; then
    BASE_BRANCH="master"
else
    echo "ERROR: No main or master branch found"
    exit 1
fi
echo "Base branch: $BASE_BRANCH"

# Check if we're on the base branch
if [ "$CURRENT_BRANCH" = "$BASE_BRANCH" ]; then
    echo "ERROR: Currently on $BASE_BRANCH branch. Switch to a feature branch first."
    exit 1
fi
```

## Step 2: Discover Documentation Files

### For --local mode

```bash
# Get modified files compared to base branch
git diff --name-only "$BASE_BRANCH"...HEAD > /tmp/docs-review-all-files.txt

# Also include uncommitted changes
git diff --name-only HEAD >> /tmp/docs-review-all-files.txt
git diff --name-only --cached >> /tmp/docs-review-all-files.txt

# Remove duplicates and filter for documentation files
sort -u /tmp/docs-review-all-files.txt | grep -E '\.(adoc|md)$' > /tmp/docs-review-doc-files.txt || true

# Count files
DOC_FILES=$(wc -l < /tmp/docs-review-doc-files.txt)
echo "Documentation files (.adoc, .md): $DOC_FILES"
```

### For --pr mode

Launch a haiku agent to return:
- A list of all changed files in the PR, identifying which are documentation files (.adoc, .md)
- The PR title and description for context
- Any `.vale.ini` configuration in the repository root

```bash
# Or use the Git Review API
python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py files "${PR_URL}" --json | \
    python3 -c "import json,sys; files=[f['path'] for f in json.load(sys.stdin) if f['path'].endswith(('.adoc','.md'))]; print('\n'.join(files))" > /tmp/docs-review-doc-files.txt

DOC_FILES=$(wc -l < /tmp/docs-review-doc-files.txt)
echo "Documentation files (.adoc, .md): ${DOC_FILES}"
```

### For both modes

If no documentation files are found, report and exit:

```bash
if [ "$DOC_FILES" -eq 0 ]; then
    echo "No documentation files (.adoc or .md) found. Review complete."
    exit 0
fi
```

## Step 3: Summarize Changes

Launch a sonnet agent to view the changes and return a summary noting:
- Which files are new vs modified
- Whether files appear to be concepts, procedures, references, or assemblies
- Any structural patterns (e.g. modular docs, release notes)

For `--pr` mode, use:
```bash
python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py diff "${PR_URL}" > /tmp/pr-diff.txt
```

For `--local` mode, use:
```bash
git diff "$BASE_BRANCH"...HEAD -- $(cat /tmp/docs-review-doc-files.txt) > /tmp/local-diff.txt
```

## Step 4: Multi-Agent Parallel Review

Launch 4 agents in parallel to independently review the documentation changes. Each agent should return a list of issues, where each issue includes:
- `file`: file path
- `line`: line number
- `description`: what the issue is
- `reason`: which review category flagged it
- `confidence`: 0-100 score of how certain the agent is this is a real issue
- `severity`: error, warning, or suggestion

For `--pr` mode, use `python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py extract` for deterministic line numbers from the diff.

The 4 agents are defined below. Each uses a dedicated `subagent_type` that loads the agent's instructions and enforces its declared tool restrictions automatically.

**Important**: The agent files describe a JIRA-based drafts workflow for their standalone use. In this docs-review command context, ignore the JIRA/drafts workflow sections — instead, review the changed files from the diff (Step 3) and return issues in the format described above (file, line, description, reason, confidence, severity).

**Agent 1: Style guide compliance**
- `subagent_type`: `docs-tools:docs-reviewer`
Focus on these skills only:
- `docs-tools:ibm-sg-language-and-grammar` — abbreviations, capitalization, active voice, inclusive language
- `docs-tools:ibm-sg-punctuation` — colons, commas, dashes, hyphens, quotes
- `docs-tools:ibm-sg-structure-and-format` — headings, lists, procedures, tables, emphasis
- `docs-tools:ibm-sg-technical-elements` — code, commands, syntax, files, UI elements
- `docs-tools:rh-ssg-grammar-and-language` — conscious language, contractions, minimalism
- `docs-tools:rh-ssg-formatting` — code blocks, user values, titles, product names
- `docs-tools:rh-ssg-structure` — admonitions, lead-ins, prerequisites, short descriptions
- `docs-tools:rh-ssg-technical-examples` — root privileges, YAML, IPs/MACs, syntax highlighting

**Agent 2: Style guide compliance**
- `subagent_type`: `docs-tools:docs-reviewer`
Focus on these skills only:
- `docs-tools:ibm-sg-audience-and-medium` — accessibility, global audiences, tone
- `docs-tools:ibm-sg-numbers-and-measurement` — numerals, formatting, currency, dates, units
- `docs-tools:ibm-sg-references` — citations, product names, versions
- `docs-tools:ibm-sg-legal-information` — claims, trademarks, copyright, personal info
- `docs-tools:rh-ssg-gui-and-links` — screenshots, UI elements, links, cross-references
- `docs-tools:rh-ssg-legal-and-support` — cost refs, future releases, Developer/Technology Preview
- `docs-tools:rh-ssg-accessibility` — colors, images, links, tables, WCAG
- `docs-tools:rh-ssg-release-notes` — release note style, tenses, Jira refs (apply only to .adoc files that appear to be release notes)

**Agent 3: Modular docs structure and content quality**
- `subagent_type`: `docs-tools:docs-reviewer`
Focus on these skills only:
- `docs-tools:docs-review-modular-docs` — module types, anchor IDs, assemblies, title conventions
- `docs-tools:docs-review-content-quality` — logical flow, user journey, scannability, conciseness
- Run Vale once per file if Vale is available. Fix clear errors, skip ambiguous issues.

**Agent 4: Technical accuracy and consistency**
- `subagent_type`: `docs-tools:technical-reviewer`
- `model`: `opus`

Follow the full technical review process, including doc type detection, reviewer persona (developer/architect lens), the 6 review dimensions (code integrity, prerequisites, command accuracy, failure paths, architectural coherence, audience level), confidence scoring, and output format. Use `docs-tools:jira-reader`, `docs-tools:git-pr-reader`, and `docs-tools:article-extractor` skills to cross-check technical claims against source materials when PR or JIRA context is available. Do not duplicate style or formatting checks — those are covered by Agents 1-3.

**CRITICAL: We only want HIGH SIGNAL issues.** Flag issues where:
- The documentation will actively mislead users (wrong commands, broken examples, incorrect terminology)
- Required modular docs structure is missing or incorrect (missing content type, broken anchor IDs)
- Clear, unambiguous style guide violations where you can cite the specific rule
- Accessibility failures (missing alt text, inaccessible tables)

Do NOT flag:
- Minor stylistic preferences that don't affect clarity
- Potential issues that depend on context outside the changed files
- Subjective wording suggestions unless they violate a specific style rule
- Pre-existing issues in unchanged content

If you are not certain an issue is real, do not flag it. False positives erode trust and waste reviewer time.

In addition to the above, each agent should be given the PR title/description or branch context. This provides context regarding the author's intent.

## Step 5: Validate Issues

For each issue found in step 4, launch parallel subagents to validate the issue. These subagents should get the context (PR title/description or branch info) along with a description of the issue. The agent's job is to review the issue to validate that the stated issue is truly an issue with high confidence. For example:
- If a "missing short description" issue was flagged, the subagent validates that the `[role="_abstract"]` block is actually absent
- If a style guide violation was flagged, the subagent confirms the specific rule applies and the text truly violates it
- If a broken cross-reference was flagged, the subagent verifies the target doesn't exist
- If a terminology error was flagged, the subagent checks that it's not an acceptable variant

Use opus subagents for structural and technical issues, and sonnet subagents for style guide violations.

## Step 6: Filter Issues

Filter out any issues that:
- Were not validated in step 5
- Score below the confidence threshold (default: 80)

This gives us our list of high-signal issues for the review.

## Step 7: Generate Report and Present Results

Generate the review report at `/tmp/docs-review-report.md` using the standard report format (see Report Format section below).

Output a summary of the review findings to the terminal:

```
## Documentation Review

**Source**: <branch vs base | PR/MR URL>
**Files reviewed**: X documentation files
**Issues found**: Y (Z above confidence threshold)

### Issues

1. **file.adoc:15** [confidence: 92] — Missing `:_mod-docs-content-type:` attribute (modular-docs)
2. **file.adoc:42** [confidence: 85] — Use "data center" not "datacenter" (RedHat.TermsErrors)
...

### Skipped (below threshold)

- **file.adoc:55** [confidence: 60] — Consider using active voice

Full report saved to: /tmp/docs-review-report.md
```

### For --local mode: Offer to Apply Changes

After presenting the summary:
1. For each **required change** (errors), offer to apply the fix using the Edit tool
2. For each **suggestion**, describe the improvement but let the user decide

```
Would you like me to apply the suggested fixes?
```

### For --pr mode without --post-comments

Stop here. Do not post any GitHub or GitLab comments.

### For --pr mode with --post-comments

If NO issues were found, post a summary comment using `gh pr comment`:

---

## Documentation review

No issues found. Checked for style guide compliance, modular docs structure, content quality, and technical accuracy.

🤖 RHAI docs Claude Code review

---

If issues were found, continue to step 8.

## Step 8: Prepare Comments (--post-comments only)

Create a list of all comments that you plan on leaving. This is only for you to review before posting. Do not post this list anywhere.

## Step 9: Post Inline Comments (--post-comments only)

Build the comments JSON and post inline comments for each issue.

First, get deterministic line numbers for each issue:

```bash
# Get the exact line number from the PR diff
LINE=$(python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py extract "${PR_URL}" "path/to/file.adoc" "pattern from the issue")
```

Build the comments JSON file:

```bash
cat > /tmp/docs-review-comments.json << 'EOF'
[
  {"file": "path/to/file.adoc", "line": 15, "severity": "error", "message": "Missing `:_mod-docs-content-type:` attribute. Add one of: CONCEPT, PROCEDURE, REFERENCE, or ASSEMBLY."},
  {"file": "path/to/file.adoc", "line": 42, "severity": "warning", "message": "Use \"data center\" not \"datacenter\" (RedHat.TermsErrors)."}
]
EOF
```

Post the comments:

```bash
python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py post "${PR_URL}" /tmp/docs-review-comments.json
```

For each comment:
- Provide a brief description of the issue with the style guide rule or skill that identified it
- For small, self-contained fixes, include the corrected text as a suggestion
- For larger structural fixes, describe the issue and suggested fix without inline code
- Never suggest a fix that would require changes in multiple locations

**IMPORTANT: Only post ONE comment per unique issue. Do not post duplicate comments.**

---

# Mode: --action-comments

Fetch unresolved review comments from GitHub Pull Requests or GitLab Merge Requests and interactively action them one by one with the user.

## Required Argument

- **url**: GitHub PR or GitLab MR URL

## Supported URL Formats

- **GitHub**: `https://github.com/owner/repo/pull/123`
- **GitLab**: `https://gitlab.com/group/project/-/merge_requests/123`

## Authentication

Authentication is handled automatically by `git_review_api.py`. Tokens are **required**:

| Platform | Token |
|----------|-------|
| GitHub | `GITHUB_TOKEN` in `~/.env` |
| GitLab | `GITLAB_TOKEN` in `~/.env` |

Required token scopes:
- **GitHub**: `repo` scope for private repos, `public_repo` for public
- **GitLab**: `api` scope for full API access

## Workflow

### Step 1: Resolve PR/MR URL

If a URL is provided, use it directly. If omitted, auto-detect the PR/MR for the current branch:

```bash
PR_URL="${1}"

if [ -z "$PR_URL" ]; then
    # Auto-detect PR for current branch using gh CLI
    echo "No URL provided. Detecting PR for current branch..."
    PR_URL=$(gh pr view --json url --jq '.url' 2>/dev/null)

    if [ -z "$PR_URL" ]; then
        echo "ERROR: No open PR found for the current branch."
        echo "Either push your branch and open a PR, or provide a URL:"
        echo "  /docs-tools:docs-review --action-comments <pr-url>"
        exit 1
    fi

    echo "Auto-detected PR: $PR_URL"
else
    echo "PR/MR URL: $PR_URL"
fi
```

### Step 2: Fetch Unresolved Comments

```bash
# Get review comments (bot comments and resolved threads are filtered automatically)
python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py comments "${PR_URL}" --json

# Or get human-readable output
python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py comments "${PR_URL}"

# Include resolved comments if needed
python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py comments "${PR_URL}" --include-resolved --json
```

### Step 3: Comment Filtering

The `git_review_api.py comments` command automatically:

1. **Filters bot comments**: Ignores comments from bots (gemini, mergify, github-actions, dependabot)
2. **Filters resolved threads**: Only returns unresolved/open comments (unless `--include-resolved`)
3. **Returns top-level comments only**: Skips replies (in_reply_to_id is null)

Each comment includes:
- `id`: Comment ID
- `path`: File path
- `line`: Line number
- `body`: Comment text
- `author`: Username of commenter
- `resolved`: Boolean (GitLab only)

### Step 4: Process Each Comment Interactively

For each unresolved comment, present to the user with the following format:

```markdown
## Comment from @{author} on `{file_path}:{line}`

> {comment_body}

### Current Content

{Show the relevant lines from the file}

### Suggested Change

{Analyze the comment and propose a specific change}
```

Use the AskUserQuestion tool to get user decision with these options:

| Option | Action |
|--------|--------|
| **Apply** | Apply the suggested change using Edit tool |
| **Edit** | Let user modify the suggestion before applying |
| **Skip** | Move to next comment without changes |
| **View context** | Read more of the file before deciding |

### Step 5: Apply Approved Changes

When the user approves a change:

1. Read the target file using the Read tool
2. Apply the edit using the Edit tool
3. Confirm the change was applied
4. Move to the next comment

### Step 6: Validate Line Numbers (Optional)

Before posting response comments, validate line numbers against the actual diff:

```bash
python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py extract --validate \
    "$PR_URL" /tmp/response-comments.json
```

### Step 7: Post Response Comments (Optional)

If needed, post response comments using the Python API:

```bash
# Post response comments
python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py post \
    "$PR_URL" /tmp/response-comments.json

# Or dry-run first
python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py post \
    "$PR_URL" /tmp/response-comments.json --dry-run
```

### Step 8: Summary

After processing all comments, provide a summary:

```markdown
## Summary

| Metric | Count |
|--------|-------|
| Total comments | X |
| Comments addressed | Y |
| Comments skipped | Z |
| Bot comments filtered | N |

### Changes Made

1. **file.adoc:42**: Applied fix for typo
2. **file.adoc:15**: Updated formatting

### Comments Skipped

1. **file.md:8**: User chose to skip (needs discussion)
```

## Comment Categories

Categorize comments to help prioritize:

| Category | Description | Action |
|----------|-------------|--------|
| **Required** | Style violations, typos, errors | Must fix |
| **Suggestion** | Improvements, rewording | User discretion |
| **Question** | Clarification needed | May need discussion |
| **Outdated** | Already addressed | Skip or confirm |

---

# False Positives

Use this list when evaluating issues in Steps 4 and 5 (these are false positives, do NOT flag):

- Pre-existing issues in unchanged content
- Something that appears to be a style violation but is an accepted project convention
- Pedantic nitpicks that a senior technical writer would not flag
- Issues that Vale will catch automatically (do not run Vale to verify unless the agent has Vale available)
- General quality concerns (e.g., "could be more concise") unless they violate a specific rule
- Style suggestions that conflict with existing content in the same document
- Terminology that matches the product's official naming even if it differs from the style guide

---

# Report Format

All review modes use this standardized report format:

```markdown
# Documentation Review Report

**Source**: [Branch: <branch> vs <base> | PR/MR URL]
**Date**: YYYY-MM-DD

## Summary

| Metric | Count |
|--------|-------|
| Files reviewed | X |
| Errors (must fix) | Y |
| Warnings (should fix) | Z |
| Suggestions (optional) | N |

## Files Reviewed

### 1. path/to/file.adoc

**Type**: CONCEPT | PROCEDURE | REFERENCE | ASSEMBLY

#### Vale Linting

| Line | Severity | Rule | Message |
|------|----------|------|---------|

#### Structure Review

| Line | Severity | Issue |
|------|----------|-------|

#### Language Review

| Line | Severity | Issue |
|------|----------|-------|

#### Elements Review

| Line | Severity | Issue |
|------|----------|-------|

---

## Required Changes

1. **file.adoc:15** — Description

## Suggestions

1. **file.adoc:55** — Description

---

*Generated with [Claude Code](https://claude.com/claude-code)*
```

**Report sections:**
- **Errors**: Must fix before merging/finalizing.
- **Warnings**: Should fix — style guide violations that impact quality.
- **Suggestions**: Optional improvements.

**Do NOT include:** positive findings or praise, executive summaries or conclusions, compliance metrics or percentages, references sections.

## Feedback Guidelines

- **In scope**: Content changed in the branch or PR/MR. **Out of scope**: Unchanged content, enhancement requests, technical accuracy (for SMEs). For out-of-scope issues, use: "This is out of scope, but consider fixing in a future update."
- **Required** (blocks merging): Typographical errors, modular docs violations, style guide violations. Mark with **Required:** or no prefix.
- **Optional** (does not block): Wording improvements, reorganization, stylistic preferences. Mark with **[SUGGESTION]** or use softer language.
- Support comments with style guide references. Explain the impact on the audience. Use softening language for suggestions: "consider", "suggest", "might". Be concise. For recurring issues: "[GLOBAL] This issue occurs elsewhere. Please address all instances."

**Comment format:**

```
**[REQUIRED/SUGGESTION]** Brief description

Explanation with style guide reference if applicable.

Suggested fix:
> Alternative wording here
```

---

# Review Skills Reference

### Red Hat Docs Skills

| Skill | Applies To | Focus |
|-------|------------|-------|
| `vale-tools:lint-with-vale` | .adoc, .md | Style guide linting (RedHat, IBM rules) |
| `docs-tools:docs-review-modular-docs` | .adoc | Module types, anchor IDs, assemblies |
| `docs-tools:docs-review-content-quality` | .adoc, .md | Logical flow, user journey, scannability, conciseness |

### IBM Style Guide Skills

| Skill | Focus |
|-------|-------|
| `docs-tools:ibm-sg-audience-and-medium` | Accessibility, global audiences, tone, conversational style |
| `docs-tools:ibm-sg-language-and-grammar` | Abbreviations, capitalization, active voice, inclusive language, terminology |
| `docs-tools:ibm-sg-punctuation` | Colons, commas, dashes, hyphens, quotes, semicolons, slashes |
| `docs-tools:ibm-sg-numbers-and-measurement` | Numerals, formatting, currency, dates, times, units |
| `docs-tools:ibm-sg-structure-and-format` | Headings, lists, procedures, tables, emphasis, figures |
| `docs-tools:ibm-sg-references` | Citations, product names, versions |
| `docs-tools:ibm-sg-technical-elements` | Code, commands, syntax, files, UI elements, web addresses |
| `docs-tools:ibm-sg-legal-information` | Claims, trademarks, copyright, personal info |

### Red Hat Supplementary Style Guide Skills

| Skill | Focus |
|-------|-------|
| `docs-tools:rh-ssg-grammar-and-language` | Conscious language, contractions, conversational style, minimalism |
| `docs-tools:rh-ssg-formatting` | Code blocks, user values, titles, product names, dates |
| `docs-tools:rh-ssg-structure` | Admonitions, lead-ins, prerequisites, short descriptions |
| `docs-tools:rh-ssg-technical-examples` | Root privileges, YAML, IPs/MACs, code, syntax highlighting |
| `docs-tools:rh-ssg-gui-and-links` | Screenshots, UI elements, links, cross-references |
| `docs-tools:rh-ssg-legal-and-support` | Cost refs, future releases, Developer/Technology Preview |
| `docs-tools:rh-ssg-accessibility` | Colors, images, links, tables, HTML structure, WCAG |
| `docs-tools:rh-ssg-release-notes` | Release note style, tenses, Jira refs, note types (.adoc only) |

---

# Git Review API Reference

The `git_review_api.py` Python script provides a unified API for interacting with GitHub PRs and GitLab MRs.

## Script Location

```
${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py
```

## Available Commands

| Command | Purpose |
|---------|---------|
| `info <url> --json` | Fetch PR/MR information |
| `files <url> --json` | List changed files |
| `diff <url>` | Get the full diff |
| `comments <url> --json` | Get review comments |
| `extract --dump <url> <file>` | Dump all lines with file line numbers |
| `extract <url> <file> <pattern>` | Find line number for a pattern |
| `extract --validate <url> <json>` | Validate comments against PR diff |
| `post <url> <json>` | Post review comments to PR/MR |
| `post <url> <json> --dry-run` | Preview without posting |

## Comments JSON Format

```json
[
  {"file": "path/to/file.adoc", "line": 42, "severity": "error", "message": "Typo: \"deloyed\" should be \"deployed\""},
  {"file": "path/to/file.adoc", "line": 15, "severity": "warning", "message": "Service selector mismatch"},
  {"file": "path/to/file.md", "line": 8, "severity": "suggestion", "message": "Consider expanding acronym on first use"}
]
```

**Message format guidelines:**
- Keep messages concise — do NOT include line numbers (the comment is already positioned)
- Do NOT include "Suggested fix:" in the message body
- The signature "🤖 RHAI docs Claude review" is added automatically

**Severity levels** (used internally for tracking, not shown in comment body):
- `error` / `critical`: Must fix
- `warning`: Should fix
- `suggestion`: Optional improvement

## Prerequisites for Posting Comments

Tokens configured in `~/.env`:

```bash
# ~/.env file format
GITLAB_TOKEN=your_gitlab_personal_access_token
GITHUB_TOKEN=your_github_personal_access_token
```

Token scopes:
- **GitLab**: `api` scope
- **GitHub**: `repo` scope

---

# Usage Examples

Review modified files in current branch:
```bash
/docs-tools:docs-review --local
```

Review with a lower confidence threshold:
```bash
/docs-tools:docs-review --local --threshold 60
```

Review a GitHub PR (terminal output only):
```bash
/docs-tools:docs-review --pr https://github.com/redhat-documentation/openshift-docs/pull/12345
```

Review a GitLab MR (terminal output only):
```bash
/docs-tools:docs-review --pr https://gitlab.cee.redhat.com/documentation/rhel-docs/-/merge_requests/678
```

Review and post inline comments to a GitHub PR:
```bash
/docs-tools:docs-review --pr https://github.com/owner/repo/pull/123 --post-comments
```

Review with custom threshold and post comments:
```bash
/docs-tools:docs-review --pr https://github.com/owner/repo/pull/123 --post-comments --threshold 70
```

Action comments on current branch's PR (auto-detected):
```bash
/docs-tools:docs-review --action-comments
```

Action comments on a specific GitHub PR:
```bash
/docs-tools:docs-review --action-comments https://github.com/owner/repo/pull/123
```

Action comments on a specific GitLab MR:
```bash
/docs-tools:docs-review --action-comments https://gitlab.cee.redhat.com/group/project/-/merge_requests/456
```

---

# Notes

- For .adoc files, modular docs compliance is checked using `docs-tools:docs-review-modular-docs`
- All files are reviewed with IBM Style Guide and Red Hat Supplementary Style Guide skills
- Release notes skills are only applied to .adoc files that appear to be release notes
- Vale linting requires Vale to be installed and configured
- **Comments are posted under YOUR username** using tokens from `~/.env`
- Duplicate comments are automatically skipped
- **CRITICAL: Always use `git_review_api.py extract` for deterministic line numbers** — never estimate or guess line numbers
- Always use Bash with heredoc/cat for writing /tmp files (not the Write tool)
- Use `python ${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py` for all Git platform interactions. Use `gh` CLI only for simple operations like `gh pr view`.
- Cite the specific style guide rule or review skill for each issue (e.g., "RedHat.TermsErrors", "IBM Style Guide: Capitalization", "modular-docs: missing content type").
