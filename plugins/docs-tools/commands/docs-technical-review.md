---
description: Validate documentation technical accuracy against code repositories — detects stale commands, flags, APIs, config keys, code examples, and file paths. Use when asked to check if docs match the code, verify examples, find outdated references, or run a technical review.
argument-hint: --docs <source> [--docs <source>...] [--code URL] [--jira TICKET] [--pr URL] [--gdoc URL] [--fix]
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Skill, WebFetch, AskUserQuestion
---

## Name

docs-tools:docs-technical-review

## Synopsis

`/docs-tools:docs-technical-review --docs <source> [--docs <source>...] [--code URL] [--jira TICKET] [--pr URL] [--gdoc URL] [--fix]`

## Description

Validate documentation for technical accuracy by comparing against source code repositories.

**Two modes**:

1. **Report only** (default) — validate and produce a human-readable report. No files are modified.
2. **Fix mode** (`--fix`) — validate, auto-fix high-confidence issues (>=65%), then interactively walk through remaining issues one by one.

## Implementation

### Arguments

### Required

- `--docs <source>` — Documentation to validate (repeatable). Can be a file path, directory, glob pattern, PR/MR URL, Google Doc URL, or remote repo URL.

If no `--docs` is provided, stop and ask the user.

### Repository Discovery (at least one required)

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
| *(none)* | Validate only, write report. No files modified. |
| `--fix` | Validate, auto-fix high-confidence issues (>=65%), then interactively step through remaining issues. |

## Usage Examples

```bash
# Report only — validate docs against a code repo
/docs-tools:docs-technical-review --docs modules/ \
  --code https://github.com/org/repo

# Fix mode — auto-fix + interactive walkthrough
/docs-tools:docs-technical-review --docs modules/ \
  --code https://github.com/org/repo --fix

# Multiple doc sources and repos via JIRA + PR
/docs-tools:docs-technical-review --docs modules/ --docs guides/admin/ \
  --jira PROJ-123 --pr https://github.com/org/repo/pull/456 --fix
```

## Implementation Workflow

### Step 1: Parse Arguments

Extract arguments from the user's command. If `--docs` is empty, stop and ask the user.

### Step 2: Resolve Docs Sources

Each `--docs` source is auto-detected and resolved:

| Source Type | Detection | Resolution |
|-------------|-----------|------------|
| Local file | Path exists as file | Use directly |
| Local directory | Path exists as directory | Glob for `*.adoc` and `*.md` files |
| Glob pattern | Contains `*` or `?` | Expand pattern to matching files |
| PR/MR URL | Matches GitHub/GitLab PR URL pattern | Fetch changed doc files via `./scripts/git_review_api.py` |
| Google Doc URL | Matches `docs.google.com` | Read via `docs-tools:docs-convert-gdoc-md` skill, save to temp file |
| Remote repo URL | Matches `https://github.com` or `https://gitlab.com` (non-PR) | Clone and glob for doc files |

### Step 3: Discover Code Repositories

Use discovery methods in priority order. If `--jira` is provided, fetch the JIRA ticket using the `docs-tools:jira-reader` skill, extract linked PR/MR URLs, and parse for repo references. If no repos are found by any method, search for `:code-repo-url:` attributes in AsciiDoc files as a fallback.

Verify at least one repo was found. If not, stop with an error listing the available discovery options.

### Step 4: Clone Code Repositories

Clone each repo to `/tmp/tech-review/<repo-name>/` using `git clone`. Do NOT use `--depth 1` — the search script uses `git log` to find rename and deprecation evidence, which requires full history. Try the specified `--ref` first, fall back to default branch. Skip repos already cloned. Warn and continue if a clone fails.

### Parallelization

When multiple code repositories are involved, parallelize the extract+search pipeline across repos using subagents. Each repo's pipeline (Steps 5-6) is independent and can run concurrently. Merge results before proceeding to Step 7.

For single-repo reviews, run sequentially.

### Step 5: Extract Technical References

Run the `extract_tech_references.rb` script from `./scripts/`:

```bash
ruby "./scripts/extract_tech_references.rb" \
  "${DOCS_FILES[@]}" \
  --output /tmp/tech-review-refs.json
```


### Step 6: Search and Validate References Against Code

Run the `search_tech_references.rb` script:

```bash
ruby "./scripts/search_tech_references.rb" \
  /tmp/tech-review-refs.json \
  /tmp/tech-review/repo1 /tmp/tech-review/repo2 \
  --output /tmp/tech-review-search.json
```

**Search results by category**:

| Category | Result Fields | What It Finds |
|----------|---------------|---------------|
| **Commands** | `found`, `scope`, `flags_checked`, `cli_validation`, `git_evidence` | Whether command exists, scope classification (in-scope/external/unknown), flag validation against argparse/click/cobra definitions |
| **Code Blocks** | `found`, `matches` (with `type`: first_line/identifier_ratio), `missing_identifiers` | Exact or fuzzy content matches in source files of the matching language |
| **APIs/Functions** | `found`, `matches` (with `type`: definition/usage/endpoint), `git_evidence` | Function/class/endpoint definitions and whether signatures match |
| **Configuration** | `found`, `keys_checked`, `schema_validation`, `git_evidence` | Whether config keys exist in schema/example files, validation against discovered schema files |
| **File Paths** | `found`, `matches` (with `type`: exact/basename) | Whether referenced paths exist, fuzzy matches if file was moved |

**Search result enrichments**:

- **`scope`** field on commands: `external` (system tool — skip), `in-scope` (lives in code repo — validate), `unknown` (needs investigation)
- **`cli_validation`** on commands: If argparse/click/cobra definitions were discovered, shows `unknown_flags`, `valid_flags`, `known_flags`, and `subcommand_check` (validates only the first positional arg as a subcommand — file paths and values are ignored)
- **`schema_validation`** on configs: If schema files were discovered, shows `keys_only_in_doc` (potentially wrong), `keys_only_in_schema` (potentially missing from docs), and `overlap_ratio`
- **`discovered_schemas`** and **`discovered_cli_definitions`** in the top-level output: Lists what was auto-discovered for transparency

### Step 6a: Structured Triage (Deterministic Classification)

Process ALL search results through a deterministic classification pipeline — not just not-found items. A command can be `found: true` (binary exists) but still have stale flags (`cli_validation.unknown_flags`). Do NOT skip this step or use ad-hoc exploration.

**Pass 1: Scope filtering (commands only)** — For each command result, check the `scope` field. Non-command categories (code blocks, APIs, configs, file paths) do not have scope and always proceed to Pass 2.
- `scope: external` → Tag as `out-of-scope`, skip further analysis. These are system commands (sudo, dnf, oc, kubectl, etc.) that cannot be validated against the code repo.
- `scope: in-scope` or `scope: unknown` → Continue to Pass 2.

**Pass 2: Deterministic validation** — For items that passed scope filtering:
- **Commands with `cli_validation`**: If `cli_validation.unknown_flags` is non-empty, flag each unknown flag as an issue. The `cli_validation.known_flags` list shows what flags actually exist in the code. Confidence is high (>=80%) because this is source-code-derived ground truth.
- **Configs with `schema_validation`**: If `schema_validation.matched_schemas` has entries with `keys_only_in_doc` items, flag each as a potential stale/renamed key. Use `keys_only_in_schema` as candidate replacements. Confidence is medium-high (70-85%) based on `overlap_ratio`.
- **File paths with `found: false`**: If basename matches exist, likely a moved file. Confidence 70-80%. If no matches at all, confidence <50%.

**Pass 3: Evidence-based analysis** — For remaining items not resolved by Pass 2:
- Cross-reference `git_evidence` with search results. Git log mentions of renames or deprecation → medium-high confidence (70-90%).
- Partial matches or similar-but-different results → medium confidence (50-64%).
- No matches at all and no git evidence → low confidence (<50%). Could be wrong repo, or reference lives elsewhere.

**Pass 4: Read source files** — For items flagged in passes 2-3 with confidence >=50%, read the actual source file referenced by the match to confirm the issue. Do not report issues based solely on search output without verifying against the source.

**Assigning severity**: `High` = users will hit errors (broken commands, missing APIs). `Medium` = misleading but not blocking (wrong names, stale options). `Low` = cosmetic or informational (undocumented features, formatting).

**Threshold**: >=65% = auto-fixable, <65% = needs interactive review.

### Step 7: Proactive Whole-Repo Scanning

This step is **mandatory** and runs regardless of whether issues were found in Step 6. It catches issues that extraction+search may miss.

**Scan scope**: The scan searches `.adoc` and `.md` files in the parent directories of the `--docs` sources. For example, if `--docs modules/proc-install.adoc` was provided, scan all `.adoc` and `.md` files under `modules/`. If `--docs` was a directory, use that directory. This captures sibling files that may have the same issues without scanning unrelated parts of the filesystem.

**7a: Anti-pattern scan** — Use the discovered CLI definitions and schemas to scan the doc tree for known anti-patterns:

1. **Deprecated flags**: For each `cli_validation.unknown_flags` found in Step 6, search for additional occurrences. This catches the same stale flag in files that weren't part of the initial `--docs` set.
2. **Stale config keys**: For each `schema_validation.keys_only_in_doc` found in Step 6, search for additional occurrences.
3. **Old binary names**: If the code repo's entry point binary name differs from what docs reference, scan for the old name.

**7b: Blast radius scan** — For each issue flagged in Step 6a, search the doc tree for additional occurrences of the same pattern. Record every file and line where the pattern appears so the report captures the full blast radius.

### Step 8: Report or Fix

#### Path 1: Report only (no `--fix`)

Write `.claude_docs/technical-review-report.md` with these sections:

1. **Header** — docs sources, timestamp, repo count
2. **Discovery Summary** — discovered schemas, CLI definitions, and scope classification stats (how many commands were external/in-scope/unknown)
3. **Triage Summary** — counts by pass (scope-filtered, deterministic, evidence-based, source-verified)
4. **Summary table** — per-category counts (validated, issues found, by severity)
5. **Code Repositories** — URL, ref, source, clone path
6. **Issues Found** — each with ID, location, severity, confidence, issue description, evidence, suggested fix, reasoning, validation source (cli_validation/schema_validation/git_evidence/manual_analysis)
7. **Whole-Repo Scan Results** — grouped by issue type, listing all files/lines affected
8. **Out-of-Scope References** — summary count of external commands skipped, grouped by tool name (collapsed, not individual items)

Display the summary to the user and the path to the report file.

#### Path 2: Fix mode (`--fix`)

**Phase A — Auto-fix high-confidence issues**:

For each issue with confidence >=65%, apply the fix using the Edit tool. Track each fix applied.

**Phase B — Interactive walkthrough of remaining issues**:

For each issue with confidence <65%, present it to the user and ask how to proceed. If there are no remaining issues, skip to the report.

**For each item**:

1. **Read current file** to verify the issue text exists
2. **Present** the item:

```
Issue 1 of 5: Command flag renamed | Confidence: 60% | Severity: High
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

**After all items**: Write `.claude_docs/technical-review-report.md` with the same sections as Path 1, plus:

- **Issues Auto-Fixed** — each with ID (`AF-N`), location, issue, evidence, before/after diff
- **Issues Interactively Resolved** — each with ID, action taken (applied/modified/deleted)
- **Issues Skipped** — each with ID, location, issue (for future reference)

Display counts of auto-fixed, interactively applied, modified, skipped, and deleted items.

## Error Handling

- **No `--docs` provided**: Stop and ask the user
- **No repos discovered**: Exit with error, show discovery options
- **Clone failures**: Warn and skip repo, continue with others
- **No references found**: Exit gracefully with summary
- **Issue text not found in file**: Warn user, show current file content, ask how to proceed
- **Edit operation fails**: Report error, ask to retry or skip

## Prerequisites

- `ruby` — for reference extraction and search scripts
- `python3` — for JIRA and Git review API scripts
- `git` — for cloning repositories
- For JIRA discovery: `JIRA_AUTH_TOKEN` in `~/.env`
- For PR discovery: `GITHUB_TOKEN` or `GITLAB_TOKEN` in `~/.env`
