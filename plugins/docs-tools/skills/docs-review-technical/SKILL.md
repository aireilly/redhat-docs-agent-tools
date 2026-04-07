---
name: docs-review-technical
description: Technical accuracy review and code-aware validation with confidence scoring. Supports local branch review, PR/MR review with optional inline comment posting, interactive comment actioning, and code-aware technical validation against source code repos. MUST BE USED when the user asks to validate documentation against code, check technical accuracy, verify commands/APIs/configs in docs match source code, or run a technical review. Also use when the user provides a --code URL or mentions code-aware review.
argument-hint: "[--local | --pr <url> [--post-comments] | --action-comments [url]] [--code <url>] [--fix] [--threshold <0-100>]"
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch, AskUserQuestion
---

# Technical Accuracy and Code-Aware Review

Multi-agent technical accuracy review with confidence-based scoring and optional code-aware validation against source repositories.

For style guide compliance and modular docs review, use `docs-review-style`.

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
| `--code <url>` | Code repository URL for technical validation (repeatable). Enables Agent 2. |
| `--fix` | Auto-fix high-confidence issues (>=65%), then interactively walk through remaining |
| `--jira <TICKET-123>` | Auto-discover code repos from JIRA ticket (uses `jira-reader`). Enables Agent 2. |
| `--ref <branch>` | Git ref to check out in `--code` repos (default: default branch). Applies to preceding `--code`. |

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

Launch a haiku agent to run pre-flight checks using `git-pr-reader`. Stop if any condition is true (still review Claude-generated PRs):

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

Use `git-pr-reader` to get changed files:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py files "${PR_URL}" --json | \
    python3 -c "import json,sys; files=[f['path'] for f in json.load(sys.stdin) if f['path'].endswith(('.adoc','.md'))]; print('\n'.join(files))" > /tmp/docs-review-doc-files.txt
```

### For both modes

If no documentation files found, report and exit.

## Step 2a: Extract Changed Line Ranges

Extract the exact changed line ranges so review agents only flag issues in changed content.

### For --local mode

```bash
git diff "$BASE_BRANCH"...HEAD -- $(cat /tmp/docs-review-doc-files.txt | tr '\n' ' ') | \
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/extract_changed_ranges.py \
    --context 3 -o /tmp/docs-review-changed-ranges.json
```

### For --pr mode

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py diff "${PR_URL}" | \
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/extract_changed_ranges.py \
    --context 3 -o /tmp/docs-review-changed-ranges.json
```

The output is a JSON file mapping each file to either `"new"` (entire file is in scope) or a list of `[start, end]` line ranges (inclusive, 1-based). Read and store this as `CHANGED_RANGES` for use in Steps 4 and 8.

## Step 3: Summarize Changes

Launch a sonnet agent to view changes and return a summary noting:
- Which files are new vs modified
- Whether files appear to be concepts, procedures, references, or assemblies
- Any structural patterns (modular docs, release notes)

For `--pr` mode: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py diff "${PR_URL}"`
For `--local` mode: `git diff "$BASE_BRANCH"...HEAD -- $(cat /tmp/docs-review-doc-files.txt)`

## Step 4: Agent 1 — Technical Accuracy and Consistency

- `subagent_type`: `technical-reviewer`
- `model`: `opus`

Follow the full technical review process: doc type detection, reviewer persona (developer/architect lens), 6 review dimensions, confidence scoring, and output format. Use `jira-reader`, `git-pr-reader`, and `article-extractor` skills to cross-check technical claims. Do not duplicate style or formatting checks.

Returns issues with: `file`, `line`, `description`, `reason`, `confidence` (0-100), `severity` (error/warning/suggestion).

For `--pr` mode, use `python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py extract` for deterministic line numbers.

**Important**: The agent file describes a JIRA-based drafts workflow for standalone use. In this context, ignore JIRA/drafts sections — review changed files from the diff and return issues in the format above.

**CRITICAL — Scope constraint**: Include the contents of `/tmp/docs-review-changed-ranges.json` in the agent's prompt. Instruct the agent:

> **You MUST only flag issues on lines that fall within the changed ranges below. For files marked `"new"`, all lines are in scope. For files with line ranges, ONLY lines within those ranges are in scope. Do NOT flag issues on lines outside these ranges — they are pre-existing content that is not part of this review.**
>
> Changed ranges: `{CHANGED_RANGES}`

## Step 5: Agent 2 — Code-Aware Technical Scan (conditional)

**Only runs when**: `--code <url>` is provided, or code repos can be auto-discovered from the PR URL, JIRA ticket context, or `:code-repo-url:` AsciiDoc attributes in the changed files.

**Dispatched as**: a general-purpose agent.

Workflow:

1. **Clone repos** to `/tmp/tech-review/<repo-name>/` using `git clone` (full history, not `--depth 1` — `git log` search needs history).

   **Repository discovery priority**: `--code` (explicit) > PR URL linked repos > `--jira` ticket linked repos > `:code-repo-url:` AsciiDoc attributes.

   If `--jira` is provided, fetch the ticket using `jira-reader` and extract linked PR/MR URLs and repository references. Parse repo URLs from PR links and JIRA ticket fields.

   If `--ref` was specified for a repo, check out that ref after cloning: `git checkout <ref>`. Otherwise use the default branch.

2. **Extract references** from doc files:
   ```bash
   python3 scripts/code_scanner.py extract $(cat /tmp/docs-review-doc-files.txt) --output /tmp/tech-review-refs.json
   ```

3. **Search repos for references** — Run the search subcommand to validate extracted references against cloned repos:
   ```bash
   python3 scripts/code_scanner.py search /tmp/tech-review-refs.json \
     /tmp/tech-review/repo1 [/tmp/tech-review/repo2 ...] \
     --output /tmp/tech-review-search.json
   ```

   The search output includes per-reference structured data:
   - **Commands**: `scope` (external/in-scope/unknown), `cli_validation` (unknown_flags, valid_flags, known_flags, framework), `git_evidence`
   - **Configs**: `schema_validation` (matched_schema, keys_only_in_doc, keys_only_in_schema, overlap_ratio), `git_evidence`
   - **APIs**: `matches` (with type: definition/usage/endpoint), `git_evidence`
   - **Code blocks**: `matches` (with type: first_line), `identifiers`
   - **File paths**: `matches` (with type: exact/basename), `git_evidence`
   - **Top-level**: `discovered_cli_definitions`, `discovered_schemas`

4. **Discover undocumented features** — Run the discover subcommand to build a code-first feature inventory and compare it against the extracted doc references:
   ```bash
   python3 scripts/code_scanner.py discover \
     /tmp/tech-review/repo1 [/tmp/tech-review/repo2 ...] \
     --refs-json /tmp/tech-review-refs.json \
     --output /tmp/tech-review-discover.json
   ```

   The discover output includes:
   - **inventory**: env_vars, cli_args, config_keys, api_endpoints, data_models found in code
   - **comparison**: `undocumented` (in code but not in docs) and `doc_only` (in docs but not in code)

5. **Validate search results** — Read `/tmp/tech-review-search.json` and `/tmp/tech-review-discover.json`. For each category, apply the structured triage pipeline from Step 6 (below). Use native tools (Grep, Glob, Read) only to verify ambiguous results — do not re-search everything the script already checked.

5. Return issues in the standard format: `file`, `line`, `description`, `reason`, `confidence`, `severity`. Include the code evidence in `reason`.

## Step 6: Structured Triage (Deterministic Classification)

Process ALL search results from `/tmp/tech-review-search.json` through a deterministic classification pipeline — not just not-found items. A command can be `found: true` (binary exists) but still have stale flags (`cli_validation.unknown_flags`). Do NOT skip this step or use ad-hoc exploration.

**Pass 1: Scope filtering (commands only)** — For each command result, check the `scope` field. Non-command categories (code blocks, APIs, configs, file paths) do not have scope and always proceed to Pass 2.
- `scope: external` → Tag as `out-of-scope`, skip further analysis. These are system commands (sudo, dnf, oc, kubectl, etc.) that cannot be validated against the code repo.
- `scope: in-scope` or `scope: unknown` → Continue to Pass 2.

**Pass 2: Deterministic validation** — For items that passed scope filtering:
- **Commands with `cli_validation`**: If `cli_validation.unknown_flags` is non-empty, flag each unknown flag as an issue. The `cli_validation.known_flags` list shows what flags actually exist in the code. Confidence is high (>=80%) because this is source-code-derived ground truth.
- **Configs with `schema_validation`**: If `schema_validation.keys_only_in_doc` is non-empty, flag each as a potential stale/renamed key. Use `keys_only_in_schema` as candidate replacements. Confidence is medium-high (70-85%) based on `overlap_ratio`.
- **File paths with `found: false`**: If basename matches exist, likely a moved file. Confidence 70-80%. If no matches at all, confidence <50%.

**Pass 3: Evidence-based analysis** — For remaining items not resolved by Pass 2:
- Cross-reference `git_evidence` with search results. Git log mentions of renames or deprecation → medium-high confidence (70-90%).
- Partial matches or similar-but-different results → medium confidence (50-64%).
- No matches at all and no git evidence → low confidence (<50%). Could be wrong repo, or reference lives elsewhere.

**Pass 4: Read source files** — For items flagged in passes 2-3 with confidence >=50%, read the actual source file referenced by the match to confirm the issue. Do not report issues based solely on search output without verifying against the source.

**Pass 5: Undocumented feature triage** — Process the `comparison` section from `/tmp/tech-review-discover.json`:
- `undocumented` items: Features found in code but not mentioned in any reviewed doc. Severity: Low-Medium. Confidence: 60-80% (lower because absence from *changed* docs doesn't mean absence from *all* docs).
- `doc_only` items: References in docs with no corresponding code. Cross-reference with Pass 2/3 results — if already flagged as stale, skip. Otherwise flag as potential stale reference. Confidence: 50-70%.

**Assigning severity**: `High` = users will hit errors (broken commands, missing APIs). `Medium` = misleading but not blocking (wrong names, stale options). `Low` = cosmetic or informational (undocumented features, formatting).

### Signal quality filter

**Flag issues where:**
- Documentation will actively mislead users (wrong commands, broken examples, incorrect terminology)
- Code examples contain wrong default values, renamed flags, or missing parameters
- API signatures, return types, or import paths don't match source code
- Configuration keys or values are stale or incorrect

**Do NOT flag:**
- "Not found in code" without concrete evidence of a problem
- Test fixtures, examples, or intentionally different deprecated paths
- External system commands (sudo, grep, git, etc.) that aren't project-specific
- Pre-existing issues in unchanged content
- Minor discrepancies that don't affect functionality

## Step 7: Validate All Issues

For each issue from Steps 4-6, launch parallel subagents to validate:
- Wrong command/flag -> verify the correct command exists in the code
- Stale API reference -> confirm the API was renamed or removed
- Broken code example -> verify the example doesn't compile/run as documented
- Incorrect config value -> confirm the actual default in source

Use opus subagents for structural/technical issues.

## Step 8: Filter Issues

Remove issues that:
- Were not validated in Step 7
- Score below the confidence threshold (default: 80)
- **Fall outside the changed line ranges from Step 2a** — For each issue, check that its `line` number falls within the `CHANGED_RANGES` for its file. For files marked `"new"`, all lines pass. For files with `[[start, end], ...]` ranges, the issue's line must fall within at least one range. Drop any issue that fails this check, regardless of confidence or severity.

## Step 9: Whole-Repo Anti-Pattern Scan (conditional)

**Only runs when Agent 2 ran.** Catches issues extraction+search may miss.

**Scan scope**: `.adoc` and `.md` files in the parent directories of the files listed in `/tmp/docs-review-doc-files.txt`.

**9a: Anti-pattern scan** — For each confirmed issue from Agent 2, use Grep to search the broader doc tree for additional occurrences of the same error pattern (e.g., same wrong flag name, same stale config key, same renamed path).

**9b: Blast radius scan** — For each issue from Step 6, search the doc tree for additional occurrences. Record every file and line.

## Step 10: Generate Report and Present Results

Write report to `/tmp/docs-review-technical-report.md` using the format below. Output summary to terminal:

```
## Technical Review

**Source**: <branch vs base | PR/MR URL>
**Files reviewed**: X documentation files
**Issues found**: Y (Z above confidence threshold)

### Issues

1. **file.adoc:23** [confidence: 95] — Flag `--enable-feature` renamed to `--feature-enable` in v2.3 (code-scan)
2. **file.adoc:67** [confidence: 88] — Default `pool_size` is 5, not 10 (technical-review)

### Skipped (below threshold)

- **file.adoc:91** [confidence: 55] — Config key `max_retries` not found in source

Full report saved to: /tmp/docs-review-technical-report.md
```

### For --local mode: Offer to Apply Changes

After the summary, offer to apply fixes for errors. Describe suggestions but let the user decide.

### For --pr mode without --post-comments

Stop here.

### For --pr mode with --post-comments

If NO issues found, post a summary comment via `git-pr-reader`:

```bash
cat <<'SUMMARY' > /tmp/docs-review-summary.json
[{"file": "", "line": 0, "message": "## Technical review\n\nNo issues found. Checked for technical accuracy and code-aware validation.", "severity": "suggestion"}]
SUMMARY
python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py post "${PR_URL}" /tmp/docs-review-summary.json
```

If issues found, continue to Step 11.

## Step 11: Post Inline Comments (--post-comments only)

Get deterministic line numbers:
```bash
LINE=$(python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py extract "${PR_URL}" "path/to/file.adoc" "pattern from the issue")
```

Build comments JSON and post:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py post "${PR_URL}" /tmp/docs-review-comments.json
```

For each comment: brief description with evidence from source code, include corrected values for small fixes, describe larger fixes without inline code. **Only ONE comment per unique issue.**

## Step 11a: Fix Mode (--fix only)

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

**Fix-mode report** — When `--fix` is used, the report at `/tmp/docs-review-technical-report.md` includes additional sections:

### Issues Auto-Fixed

| ID | File:Line | Issue | Evidence | Before | After |
|----|-----------|-------|----------|--------|-------|
| AF-1 | file.adoc:23 | Flag renamed | cli_validation | `--enable-feature` | `--feature-enable` |

### Issues Interactively Resolved

| ID | File:Line | Issue | Action |
|----|-----------|-------|--------|
| IR-1 | file.adoc:45 | Stale config key | Applied suggested fix |
| IR-2 | file.adoc:67 | Wrong default | Modified by user |

### Issues Skipped

| ID | File:Line | Issue | Confidence |
|----|-----------|-------|------------|
| SK-1 | file.adoc:91 | Config key not found | 55% |

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

Categorize comments: **Required** (technical errors — must fix), **Suggestion** (improvements — user discretion), **Question** (needs discussion), **Outdated** (already addressed — skip).

---

# Report Format

```markdown
# Technical Review Report

**Source**: [Branch: <branch> vs <base> | PR/MR URL]
**Date**: YYYY-MM-DD

## Discovery Summary

| Metric | Count |
|--------|-------|
| CLI definitions discovered | X |
| Schema files discovered | Y |
| Commands: in-scope | A |
| Commands: external (out-of-scope) | B |
| Commands: unknown scope | C |

## Code Repositories

| Repo | Ref | Clone Path | Source |
|------|-----|------------|--------|
| repo-name | main | /tmp/tech-review/repo-name | --code |

## Triage Summary

| Pass | Description | Items Processed | Issues Flagged |
|------|-------------|-----------------|----------------|
| Pass 1 | Scope filtering | X | Y |
| Pass 2 | Deterministic validation | X | Y |
| Pass 3 | Evidence-based analysis | X | Y |
| Pass 4 | Source file verification | X | Y |
| Pass 5 | Undocumented feature triage | X | Y |

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

#### Technical Accuracy

| Line | Severity | Issue | Evidence |
|------|----------|-------|----------|

#### Code Validation (if Agent 2 ran)

| Line | Severity | Issue | Evidence | Validation Source |
|------|----------|-------|----------|-------------------|

Show specific value mismatches (e.g., "Docs: pool_size=10, Code: pool_size=5"), undocumented features, and import path errors. Do not list every `found: false` result — only report items where there is concrete evidence of a discrepancy or where a documented feature is provably absent from the code.

---

## Required Changes

1. **file.adoc:23** — Description (evidence) [validation: cli_validation]

## Suggestions

1. **file.adoc:91** — Description [validation: manual_analysis]

## Undocumented Features (if discover ran)

Features found in source code but not mentioned in reviewed documentation:

| Category | Name | Source File | Evidence |
|----------|------|-------------|----------|
| env_var | SECRET_KEY | src/app.py:15 | os.environ.get("SECRET_KEY") |
| api_endpoint | /api/v2/health | src/routes.py:42 | @app.route("/api/v2/health") |

## Out-of-Scope References

| Tool | Count |
|------|-------|
| sudo | X |
| kubectl | Y |

---

*Generated with [Claude Code](https://claude.com/claude-code)*
```

**Sections**: Errors = must fix. Warnings = should fix. Suggestions = optional.

**Do NOT include**: positive findings, executive summaries, compliance percentages, references sections.

## Feedback Guidelines

- **In scope**: Content changed in the branch or PR/MR. **Out of scope**: Unchanged content, enhancement requests.
- **Required** (blocks merging): Incorrect commands, wrong API references, broken code examples, stale config values.
- **Optional** (does not block): Minor accuracy improvements, additional context. Mark with **[SUGGESTION]**.
- Include source code evidence for each issue. For recurring issues: "[GLOBAL] This issue occurs elsewhere."

---

# Notes

- Always use `python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py` for all Git platform interactions (see `git-pr-reader` for full API reference)
- Always use `git_pr_reader.py extract` for deterministic line numbers — never estimate or guess
- Use Bash with heredoc/cat for writing /tmp files (not the Write tool)
- Include source code evidence in each issue's `reason` field
- Comments are posted under YOUR username using tokens from `~/.env`
- The `code_scanner.py` script is co-located in `scripts/` for Agent 2's reference extraction
- Vale linting is NOT part of the technical review — use `docs-review-style` for that
