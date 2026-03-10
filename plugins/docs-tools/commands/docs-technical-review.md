---
description: Validate documentation technical accuracy against code repositories. Detects removed commands, changed API signatures, stale code examples, renamed config keys, and moved file paths. Auto-fixes high-confidence issues (>=65%) and interactively walks through lower-confidence fixes. Use this command when asked to check if docs match the code, verify CLI examples still work, validate API references, find outdated commands or stale documentation, compare docs against a PR or JIRA ticket, or run a technical review. Also use when the user says things like "are these docs accurate" or "check the code examples".
argument-hint: --docs <source> [--docs <source>...] [--code URL] [--jira TICKET] [--pr URL] [--gdoc URL] [--fix] [--apply]
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Skill, WebFetch, AskUserQuestion
---

# Technical Review

Validate documentation for technical accuracy by comparing against source code repositories. Auto-fixes high-confidence issues and generates detailed reports. Optionally walks through lower-confidence fixes interactively.

## Arguments

### Required

- `--docs <source>` — Documentation to validate (repeatable). Can be a file path, directory, glob pattern, PR/MR URL, Google Doc URL, or remote repo URL.

If no `--docs` is provided, stop and ask the user.

### Repository Discovery (at least one required, unless --report)

| Argument | Description |
|----------|-------------|
| `--code <URL>` | Explicit code repository URL (repeatable) |
| `--ref <branch>` | Git ref for previous `--code` (default: main) |
| `--jira <TICKET-123>` | Auto-discover repos from JIRA ticket |
| `--pr <URL>` | Auto-discover from PR/MR URL (repeatable) |
| `--gdoc <URL>` | Auto-discover from Google Doc |

**Discovery priority**: `--code` > `--pr` > `--jira` > `--gdoc` > AsciiDoc `:code-repo-url:` attributes

### Actions

| Flag | Description |
|------|-------------|
| `--fix` | Auto-fix high-confidence issues (>=65%) |
| `--apply` | After validation, interactively walk through lower-confidence fixes (<65%) |
| `--dry-run` | Preview changes without applying |

### Resume from Previous Run

| Argument | Description |
|----------|-------------|
| `--report <path>` | Skip validation, apply fixes from existing report JSON |
| `--items <ID,ID,...>` | Only process these specific item IDs (with `--report` or `--apply`) |
| `--confidence <MIN-MAX>` | Only process items in this confidence range (with `--report` or `--apply`) |

### Flag Combinations

| Flags | Behavior |
|-------|----------|
| *(none)* | Validate only, write report |
| `--fix` | Validate + auto-fix >=65%, write report |
| `--apply` | Validate + interactive apply <65% |
| `--fix --apply` | Full flow: validate + auto-fix + interactive apply |
| `--report <path>` | Skip validation, interactive apply from saved report |

## Usage Examples

```bash
# Validate and auto-fix
/docs-tools:docs-technical-review --docs modules/ \
  --code https://github.com/org/repo --fix

# Full flow: auto-fix + interactive apply
/docs-tools:docs-technical-review --docs modules/ \
  --jira RHAISTRAT-123 --fix --apply

# Multiple doc sources and repos
/docs-tools:docs-technical-review --docs modules/ --docs guides/admin/ \
  --jira RHAISTRAT-123 --pr https://github.com/org/repo/pull/456 --fix

# Resume from a previous report
/docs-tools:docs-technical-review --report .claude_docs/technical-review-report.json \
  --items MR-1,MR-3

# Dry run
/docs-tools:docs-technical-review --docs modules/ \
  --code https://github.com/org/repo --dry-run
```

## Implementation Workflow

### Step 1: Parse Arguments

Extract arguments from the user's command. If `--report` is provided, skip to Step 10 (interactive apply from saved report).

If `--docs` is empty and `--report` is not provided, stop and ask the user.

### Step 2: Resolve Docs Sources

Each `--docs` source is auto-detected and resolved:

| Source Type | Detection | Resolution |
|-------------|-----------|------------|
| Local file | Path exists as file | Use directly |
| Local directory | Path exists as directory | Glob for `*.adoc` and `*.md` files |
| Glob pattern | Contains `*` or `?` | Expand pattern to matching files |
| PR/MR URL | Matches GitHub/GitLab PR URL pattern | Fetch changed doc files via `${CLAUDE_PLUGIN_ROOT}/commands/scripts/git_review_api.py` |
| Google Doc URL | Matches `docs.google.com` | Read via `docs-convert-gdoc-md` skill, save to temp file |
| Remote repo URL | Matches `https://github.com` or `https://gitlab.com` (non-PR) | Clone and glob for doc files |

### Step 3: Discover Code Repositories

Use discovery methods in priority order. If `--jira` is provided, fetch the JIRA ticket using the `jira-reader` skill, extract linked PR/MR URLs, and parse for repo references. If no repos are found by any method, search for `:code-repo-url:` attributes in AsciiDoc files as a fallback.

Verify at least one repo was found. If not, stop with an error listing the available discovery options.

### Step 4: Clone Code Repositories

Clone each repo to `/tmp/tech-review/<repo-name>/` using `git clone --depth 1`. Try the specified `--ref` first, fall back to default branch. Skip repos already cloned. Warn and continue if a clone fails.

### Parallelization

When multiple code repositories are involved, parallelize the extract+search pipeline across repos using subagents. Each repo's pipeline (Steps 5-6) is independent and can run concurrently. Merge results before proceeding to Step 7.

For single-repo reviews, run sequentially.

### Step 5: Extract Technical References

Run the `extract_tech_references.rb` script from `${CLAUDE_PLUGIN_ROOT}/commands/scripts/`:

```bash
ruby "${CLAUDE_PLUGIN_ROOT}/commands/scripts/extract_tech_references.rb" \
  "${DOCS_FILES[@]}" \
  --output /tmp/tech-review-refs.json
```

If the script path cannot be resolved, search for `extract_tech_references.rb` using Glob.

### Step 6: Search and Validate References Against Code

Run the `search_tech_references.rb` script:

```bash
ruby "${CLAUDE_PLUGIN_ROOT}/commands/scripts/search_tech_references.rb" \
  /tmp/tech-review-refs.json \
  /tmp/tech-review/repo1 /tmp/tech-review/repo2 \
  --output /tmp/tech-review-search.json
```

**Search results by category**:

| Category | Result Fields | What It Finds |
|----------|---------------|---------------|
| **Commands** | `found`, `found_path`, `flags_missing`, `similar_commands`, `git_log_mentions` | Whether command binary/script exists, which flags are missing, git history for renames |
| **Code Blocks** | `match_type` (exact/partial/none), `match_ratio`, `matched_file`, `actual_code` | Exact or fuzzy content matches in source files of the matching language |
| **APIs/Functions** | `definition_found`, `actual_signature`, `type` (function/class/endpoint) | Function/class/endpoint definitions and whether signatures match |
| **Configuration** | `key_found`, `found_in_file`, `git_log_mentions` | Whether config keys exist in schema/example files, git history for renames |
| **File Paths** | `exists`, `moved_to`, `similar_files` | Whether referenced paths exist, fuzzy matches if file was moved |

**Interpreting results and assigning confidence**:

The search results are raw evidence — use your judgment to assign confidence scores. Confidence reflects how certain you are about both the problem and the fix, not just the problem.

- **Exact matches** with only syntax/formatting differences → high confidence (>=85%), fix is obvious
- **Git log evidence** of renames or deprecation → medium-high (70-90%), history confirms intentional change
- **Partial matches** or similar-but-different results → medium (50-64%), right fix is ambiguous
- **No matches at all** → low (<50%), could be removal, wrong repo, or reference lives elsewhere
- **Context matters**: a missing flag in a command that otherwise exists is higher confidence than a completely missing command

Cross-reference multiple signals (search results + git history + related files) before finalizing confidence.

**Assigning severity**: `High` = users will hit errors (broken commands, missing APIs). `Medium` = misleading but not blocking (wrong names, stale options). `Low` = cosmetic or informational (undocumented features, formatting).

**Threshold**: >=65% = auto-fixable, <65% = needs manual review.

### Step 7: Perform Whole-Repo Scanning

For each flagged issue, search all `.adoc` and `.md` files for additional occurrences of the same pattern. Record every file and line where the pattern appears so the report captures the full blast radius.

### Step 8: Apply Auto-Fixes (if --fix)

For each issue with confidence >=65%, apply the fix using the Edit tool. Track each fix applied and its before/after text for the report.

### Step 9: Generate Reports

#### Markdown Report

Write `.claude_docs/technical-review-report.md` with these sections:

1. **Header** — docs sources, timestamp, repo count
2. **Summary table** — per-category counts (validated, issues, auto-fixed, manual review)
3. **Code Repositories** — URL, ref, source, clone path
4. **Issues Auto-Fixed** — each with ID (`AF-N`), location, issue, evidence, diff
5. **Issues Requiring Manual Review** — each with ID (`MR-N`), location, severity, issue, evidence, suggested diff, reasoning
6. **Whole-Repo Scan Results** — grouped by issue type, listing all files/lines affected
7. **Next Steps** — review auto-fixes, run with `--apply`, run Vale, test examples

#### JSON Sidecar

Write `.claude_docs/technical-review-report.json` — array of issue objects:

```json
[
  {
    "id": "AF-1",
    "file": "modules/proc-install.adoc",
    "line": 42,
    "category": "commands",
    "confidence": 90,
    "old_text": "--enable-feature",
    "new_text": "--feature-enable",
    "evidence": "Flag renamed in commit abc123",
    "description": "Command flag renamed in v2.0",
    "severity": "Medium",
    "reasoning": "Git log shows flag renamed in v2.0 release"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Issue ID (`AF-N` for auto-fixed, `MR-N` for manual review) |
| `file` | string | Path to the documentation file |
| `line` | number | Line number in the file |
| `category` | string | One of: `commands`, `code_blocks`, `apis`, `configs`, `file_paths`, `conceptual` |
| `confidence` | number | Confidence score (0-100) |
| `old_text` | string | Original text in the documentation (used for content-based matching) |
| `new_text` | string | Suggested or applied replacement text |
| `evidence` | string | What was found in the code repository |
| `description` | string | Human-readable description of the issue |
| `severity` | string | `High`, `Medium`, or `Low` |
| `reasoning` | string | Why the change is suggested and confidence rationale |

The `old_text` field enables content-based matching so fixes apply correctly even if line numbers shift.

#### Display Summary

Show total issues found, auto-fixed count, manual review count, and paths to both report files.

### Step 10: Interactive Apply (if --apply or --report)

If `--apply` was specified (or `--report` for resume mode), proceed to interactively walk through lower-confidence fixes. If there are no manual review items, stop with a success message.

**Load items**: Read the JSON sidecar. Filter for items with confidence <65%, then apply any `--confidence` or `--items` filters.

If `--report` was provided and the JSON sidecar is missing, fall back to parsing the markdown report (warn the user).

**For each item**:

1. **Read current file** to verify `old_text` exists
2. **Present** the item:

```
MR-1 (1 of 5): Command flag renamed | Confidence: 60% | Severity: High
File: modules/proc-install.adoc

Current:   $ my-tool --enable-feature
Suggested: $ my-tool --feature-enable

Evidence: Flag renamed in commit abc123, git log confirms deprecation
Reasoning: Exact command exists, only the flag changed — likely a rename
```

3. **Ask user** via `AskUserQuestion` with four options:
   - **Apply suggested fix** — use as-is
   - **Modify fix** — ask what they want changed, apply modified version
   - **Skip** — leave for manual editing later
   - **Delete section** — remove entirely from documentation

4. **Apply fix** using content-based matching: `Edit(file_path=FILE, old_string=old_text, new_string=new_text)`

**After all items**: Display counts of applied, modified, skipped, and deleted items. Back up the report file and mark applied items.

## Error Handling

- **No `--docs` provided**: Stop and ask the user
- **No repos discovered**: Exit with error, show discovery options
- **Clone failures**: Warn and skip repo, continue with others
- **No references found**: Exit gracefully with summary
- **`old_text` not found in file**: Warn user, show current file content, ask how to proceed
- **Edit operation fails**: Report error, ask to retry or skip

## Prerequisites

- `ruby` — for reference extraction and search scripts
- `python3` — for JIRA and Git review API scripts
- `git` — for cloning repositories
- For JIRA discovery: `JIRA_AUTH_TOKEN` in `~/.env`
- For PR discovery: `GITHUB_TOKEN` or `GITLAB_TOKEN` in `~/.env`
