---
name: docs-review-e2e
description: End-to-end multi-agent documentation review with confidence scoring. Supports local branch review, PR/MR review with optional inline comment posting, interactive comment actioning, and code-aware technical validation against source code repos. MUST BE USED whenever the user asks to review documentation, check docs quality, validate docs against code, review a PR/MR containing .adoc or .md files, action or address PR review comments, or run a docs review. Also use when the user mentions style guide compliance, modular docs structure, or technical accuracy of documentation.
argument-hint: "[--local | --pr <url> [--post-comments] | --action-comments [url]] [--code <url>] [--fix] [--threshold <0-100>]"
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch, AskUserQuestion
---

# End-to-End Documentation Review

A unified multi-agent documentation review with confidence-based scoring and optional code-aware technical validation.

## Modes

| Arguments | Mode | Description |
|-----------|------|-------------|
| `--local` | Local review | Review doc changes in current branch vs base branch |
| `--pr <url>` | PR/MR review | Review doc changes in a GitHub PR or GitLab MR |
| `--pr <url> --post-comments` | PR/MR + post | Review and post inline comments to PR/MR |
| `--action-comments [url]` | Action comments | Fetch and interactively action unresolved PR/MR review comments (auto-detects PR if URL omitted) |
| *(no arguments)* | Error | Display usage |

## Global Options

| Option | Description |
|--------|-------------|
| `--threshold <0-100>` | Confidence threshold for reporting issues (default: 80) |
| `--code <url>` | Code repository URL for technical validation (repeatable). Enables Agent 5. |
| `--fix` | Auto-fix high-confidence issues (>=65%), then interactively walk through remaining |

If no arguments are provided, display usage and ask the user to specify a mode.

## Agent Assumptions

These apply to ALL agents and subagents:

- All tools are functional. Do not test tools or make exploratory calls.
- Only call a tool if required. Every tool call should have a clear purpose.
- The confidence threshold is 80 by default (adjustable with `--threshold`).

---

# Multi-Agent Review Pipeline

The `--local` and `--pr` modes share the same pipeline. The difference is how files are discovered and how results are delivered.

## Step 1: Pre-flight Checks

### For --pr mode

Launch a haiku agent to run pre-flight checks using `docs-tools:git-pr-reader`. Stop if any condition is true (still review Claude-generated PRs):

- **PR/MR is closed or draft**: Check the PR/MR state from the platform API.
- **No documentation files changed**: Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py files "${PR_URL}" --json` and check if any changed files end with `.adoc` or `.md`.
- **Claude already commented**: Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py comments "${PR_URL}" --include-resolved --json` and check if any comment `author` matches Claude's username.

### For --local mode

```bash
CURRENT_BRANCH=$(git branch --show-current)
# Detect base branch from remote default, fall back to local refs
BASE_BRANCH=$(git rev-parse --abbrev-ref origin/HEAD 2>/dev/null | sed 's|^origin/||')
if [ -z "$BASE_BRANCH" ]; then
    if git show-ref --verify --quiet refs/heads/main; then
        BASE_BRANCH="main"
    elif git show-ref --verify --quiet refs/heads/master; then
        BASE_BRANCH="master"
    else
        echo "ERROR: Cannot determine base branch"; exit 1
    fi
fi
if [ "$CURRENT_BRANCH" = "$BASE_BRANCH" ]; then
    echo "ERROR: Currently on $BASE_BRANCH. Switch to a feature branch first."; exit 1
fi
```

## Step 2: Discover Documentation Files

### For --local mode

```bash
git diff --name-only "$BASE_BRANCH"...HEAD > /tmp/docs-review-all-files.txt
git diff --name-only HEAD >> /tmp/docs-review-all-files.txt
git diff --name-only --cached >> /tmp/docs-review-all-files.txt
sort -u /tmp/docs-review-all-files.txt | grep -E '\.(adoc|md)$' > /tmp/docs-review-doc-files.txt || true
DOC_FILES=$(wc -l < /tmp/docs-review-doc-files.txt)
```

### For --pr mode

Use `docs-tools:git-pr-reader` to get changed files:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py files "${PR_URL}" --json | \
    python3 -c "import json,sys; files=[f['path'] for f in json.load(sys.stdin) if f['path'].endswith(('.adoc','.md'))]; print('\n'.join(files))" > /tmp/docs-review-doc-files.txt
```

### For both modes

If no documentation files found, report and exit.

## Step 3: Summarize Changes

Launch a sonnet agent to view changes and return a summary noting:
- Which files are new vs modified
- Whether files appear to be concepts, procedures, references, or assemblies
- Any structural patterns (modular docs, release notes)

For `--pr` mode: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py diff "${PR_URL}"`
For `--local` mode: `git diff "$BASE_BRANCH"...HEAD -- $(cat /tmp/docs-review-doc-files.txt)`

## Step 4: Multi-Agent Parallel Review

Launch agents in parallel. Each agent returns issues with: `file`, `line`, `description`, `reason`, `confidence` (0-100), `severity` (error/warning/suggestion).

For `--pr` mode, use `python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py extract` for deterministic line numbers.

**Important**: The agent files describe a JIRA-based drafts workflow for standalone use. In this context, ignore JIRA/drafts sections — review changed files from the diff and return issues in the format above.

### Agent 1: Style guide compliance (batch A)

- `subagent_type`: `docs-tools:docs-reviewer`

Focus on: `docs-tools:ibm-sg-language-and-grammar`, `docs-tools:ibm-sg-punctuation`, `docs-tools:ibm-sg-structure-and-format`, `docs-tools:ibm-sg-technical-elements`, `docs-tools:rh-ssg-grammar-and-language`, `docs-tools:rh-ssg-formatting`, `docs-tools:rh-ssg-structure`, `docs-tools:rh-ssg-technical-examples`

### Agent 2: Style guide compliance (batch B)

- `subagent_type`: `docs-tools:docs-reviewer`

Focus on: `docs-tools:ibm-sg-audience-and-medium`, `docs-tools:ibm-sg-numbers-and-measurement`, `docs-tools:ibm-sg-references`, `docs-tools:ibm-sg-legal-information`, `docs-tools:rh-ssg-gui-and-links`, `docs-tools:rh-ssg-legal-and-support`, `docs-tools:rh-ssg-accessibility`, `docs-tools:rh-ssg-release-notes`

### Agent 3: Modular docs structure and content quality

- `subagent_type`: `docs-tools:docs-reviewer`

Focus on: `docs-tools:docs-review-modular-docs`, `docs-tools:docs-review-content-quality`. Run Vale once per file if available.

### Agent 4: Technical accuracy and consistency

- `subagent_type`: `docs-tools:technical-reviewer`
- `model`: `opus`

Follow the full technical review process: doc type detection, reviewer persona (developer/architect lens), 6 review dimensions, confidence scoring, and output format. Use `docs-tools:jira-reader`, `docs-tools:git-pr-reader`, and `docs-tools:article-extractor` to cross-check technical claims. Do not duplicate style or formatting checks.

### Agent 5: Code-aware technical scan (conditional)

**Only runs when**: `--code <url>` is provided, or code repos can be auto-discovered from the PR URL, JIRA ticket context, or `:code-repo-url:` AsciiDoc attributes in the changed files.

**Dispatched as**: a general-purpose agent.

Workflow:

1. **Clone repos** to `/tmp/tech-review/<repo-name>/` using `git clone` (full history, not `--depth 1` — `git log` search needs history). Try specified ref, fall back to default branch.

2. **Extract references** from doc files:
   ```bash
   python3 scripts/code_scanner.py extract $(cat /tmp/docs-review-doc-files.txt) --output /tmp/tech-review-refs.json
   ```

3. **Search repos directly** — Read `/tmp/tech-review-refs.json` and search the cloned repos using native tools (Grep, Glob, Bash, Read). For each reference category:

   - **Commands**: Skip external system commands (sudo, grep, git, oc, kubectl, docker, podman, curl, ssh, systemctl, ansible, make, etc.). For project-specific commands, use Grep to find the binary in the repo. Read the source to check flag names, default values, and subcommands match the docs.
   - **Code blocks**: Use Grep to find the first meaningful line of each block in the repo. Read surrounding source to check values, function signatures, and import paths match.
   - **APIs** (functions/classes/endpoints): Use Grep to find definitions. Read the source to verify signatures, parameters, and return types match the docs.
   - **Configs**: Use Glob to find config files (*.yaml, *.yml, *.json, *.toml). Read them to compare key names, default values, and structure against what the docs show.
   - **File paths**: Use Glob to check if the documented path exists. If not, search by basename to detect renames.
   - **Git history**: When a reference is not found in code, use `git log --all --oneline --grep="<term>"` to check for renames, deprecations, or removals. This provides evidence for confidence scoring (e.g., "flag `--enable-feature` was renamed to `--feature-enable` in commit abc123").

   Focus on finding **concrete discrepancies**: wrong default values (e.g., "docs say pool_size=10, code says pool_size=5"), renamed flags, missing parameters, stale import paths, undocumented features. Do not report "not found in code" without evidence of a real problem.

4. Return issues in the standard format: `file`, `line`, `description`, `reason`, `confidence`, `severity`. Include the code evidence in `reason`.

### Signal quality filter

**Flag issues where:**
- Documentation will actively mislead users (wrong commands, broken examples, incorrect terminology)
- Required modular docs structure is missing or incorrect
- Clear, unambiguous style guide violations with a citable rule
- Accessibility failures (missing alt text, inaccessible tables)

**Do NOT flag:**
- Minor stylistic preferences that don't affect clarity
- Potential issues depending on context outside changed files
- Subjective wording suggestions unless they violate a specific rule
- Pre-existing issues in unchanged content

Do NOT flag (false positives):
- Pre-existing issues in unchanged content
- Something that appears to be a style violation but is an accepted project convention
- Pedantic nitpicks that a senior technical writer would not flag
- Issues that Vale will catch automatically (do not run Vale to verify unless the agent has Vale available)
- General quality concerns (e.g., "could be more concise") unless they violate a specific rule
- Style suggestions that conflict with existing content in the same document
- Terminology that matches the product's official naming even if it differs from the style guide
- Minor stylistic preferences that don't affect clarity
- Potential issues that depend on context outside the changed files
- Subjective wording suggestions unless they violate a specific style rule

## Step 5: Validate Agent 5 Findings

Review each issue reported by Agent 5. For each finding:

- Confirm the agent read the actual source file (not just grep output) and the discrepancy is real
- Confirm the issue is not a test fixture, example, or deprecated path that is intentionally different
- Assign confidence based on evidence quality: direct value mismatch = 90%+, renamed/moved = 70-85%, absent with no code evidence = skip
- Assign severity: `High` = users will hit errors. `Medium` = misleading but not blocking. `Low` = cosmetic.

Discard findings where the agent could not confirm the discrepancy by reading source code.

## Step 6: Validate Issues

For each issue from Steps 4-5, launch parallel subagents to validate:
- Missing short description → verify `[role="_abstract"]` is actually absent
- Style violation → confirm the specific rule applies and text truly violates it
- Broken cross-reference → verify the target doesn't exist
- Terminology error → check it's not an acceptable variant

Use opus subagents for structural/technical issues, sonnet for style violations.

## Step 7: Filter Issues

Remove issues that:
- Were not validated in Step 6
- Score below the confidence threshold (default: 80)

## Step 8: Whole-Repo Anti-Pattern Scan (conditional)

**Only runs when Agent 5 ran.** Catches issues extraction+search may miss.

**Scan scope**: `.adoc` and `.md` files in the parent directories of the files listed in `/tmp/docs-review-doc-files.txt`.

**8a: Anti-pattern scan** — For each confirmed issue from Agent 5, use Grep to search the broader doc tree for additional occurrences of the same error pattern (e.g., same wrong flag name, same stale config key, same renamed path).

**8b: Blast radius scan** — For each issue from Step 5, search the doc tree for additional occurrences. Record every file and line.

## Step 9: Generate Report and Present Results

Write report to `/tmp/docs-review-report.md` using the format below. Output summary to terminal:

```
## Documentation Review

**Source**: <branch vs base | PR/MR URL>
**Files reviewed**: X documentation files
**Issues found**: Y (Z above confidence threshold)

### Issues

1. **file.adoc:15** [confidence: 92] — Missing `:_mod-docs-content-type:` attribute (modular-docs)
2. **file.adoc:42** [confidence: 85] — Use "data center" not "datacenter" (RedHat.TermsErrors)

### Skipped (below threshold)

- **file.adoc:55** [confidence: 60] — Consider using active voice

Full report saved to: /tmp/docs-review-report.md
```

### For --local mode: Offer to Apply Changes

After the summary, offer to apply fixes for errors. Describe suggestions but let the user decide.

### For --pr mode without --post-comments

Stop here.

### For --pr mode with --post-comments

If NO issues found, post a summary comment via `git-pr-reader`:

```bash
cat <<'SUMMARY' > /tmp/docs-review-summary.json
[{"file": "", "line": 0, "message": "## Documentation review\n\nNo issues found. Checked for style guide compliance, modular docs structure, content quality, and technical accuracy.", "severity": "suggestion"}]
SUMMARY
python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py post "${PR_URL}" /tmp/docs-review-summary.json
```

If issues found, continue to Step 10.

## Step 10: Post Inline Comments (--post-comments only)

Get deterministic line numbers:
```bash
LINE=$(python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py extract "${PR_URL}" "path/to/file.adoc" "pattern from the issue")
```

Build comments JSON and post:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py post "${PR_URL}" /tmp/docs-review-comments.json
```

For each comment: brief description with style guide rule, include corrected text for small fixes, describe larger fixes without inline code. **Only ONE comment per unique issue.**

## Step 10a: Fix Mode (--fix only)

**Phase A — Auto-fix**: For each issue with confidence >=65%, apply the fix using the Edit tool.

**Phase B — Interactive walkthrough**: For each issue with confidence <65%, present to user:

```
Issue 1 of 5: Command flag renamed | Confidence: 60% | Severity: High
File: modules/proc-install.adoc

Current:   $ my-tool --enable-feature
Suggested: $ my-tool --feature-enable

Evidence: Flag renamed in commit abc123
```

Ask user via AskUserQuestion: **Apply** | **Modify** | **Skip** | **Delete section**

---

# Mode: --action-comments

Fetch unresolved review comments from GitHub PRs or GitLab MRs and interactively action them.

## Step 1: Resolve PR/MR URL

If URL provided, use directly. If omitted, auto-detect:
```bash
PR_URL=$(python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py detect 2>/dev/null)
```

## Step 2: Fetch Unresolved Comments

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py comments "${PR_URL}" --json
```

The script automatically filters bot comments, resolved threads, and returns top-level comments only with: `id`, `path`, `line`, `body`, `author`, `resolved`.

## Step 3: Process Each Comment Interactively

For each unresolved comment, present:

```markdown
## Comment from @{author} on `{file_path}:{line}`

> {comment_body}

### Current Content
{relevant lines from the file}

### Suggested Change
{analysis and proposed change}
```

Ask user via AskUserQuestion: **Apply** | **Edit** | **Skip** | **View context**

When approved: Read target file, apply Edit, confirm, move to next.

## Step 4: Summary

```markdown
## Summary

| Metric | Count |
|--------|-------|
| Total comments | X |
| Comments addressed | Y |
| Comments skipped | Z |
| Bot comments filtered | N |
```

Categorize comments: **Required** (style violations, errors — must fix), **Suggestion** (improvements — user discretion), **Question** (needs discussion), **Outdated** (already addressed — skip).

---

# Report Format

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

#### Code Validation (if Agent 5 ran)

| Line | Severity | Issue | Evidence |
|------|----------|-------|----------|

Show specific value mismatches (e.g., "Docs: pool_size=10, Code: pool_size=5"), undocumented features, and import path errors. Do not list every `found: false` result — only report items where there is concrete evidence of a discrepancy or where a documented feature is provably absent from the code.

---

## Required Changes

1. **file.adoc:15** — Description

## Suggestions

1. **file.adoc:55** — Description

---

*Generated with [Claude Code](https://claude.com/claude-code)*
```

**Sections**: Errors = must fix. Warnings = should fix. Suggestions = optional.

**Do NOT include**: positive findings, executive summaries, compliance percentages, references sections.

## Feedback Guidelines

- **In scope**: Content changed in the branch or PR/MR. **Out of scope**: Unchanged content, enhancement requests.
- **Required** (blocks merging): Typos, modular docs violations, style guide violations.
- **Optional** (does not block): Wording improvements, reorganization, stylistic preferences. Mark with **[SUGGESTION]**.
- Cite specific style guide rules. Use softening language for suggestions. For recurring issues: "[GLOBAL] This issue occurs elsewhere."

---

# Notes

- Always use `python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py` for all Git platform interactions (see `docs-tools:git-pr-reader` for full API reference)
- Always use `git_pr_reader.py extract` for deterministic line numbers — never estimate or guess
- Use Bash with heredoc/cat for writing /tmp files (not the Write tool)
- Cite the specific style guide rule or review skill for each issue
- Comments are posted under YOUR username using tokens from `~/.env`
- For .adoc files, modular docs compliance uses `docs-tools:docs-review-modular-docs`
- Release notes skills only apply to .adoc files that appear to be release notes
- Vale linting requires Vale to be installed and configured
