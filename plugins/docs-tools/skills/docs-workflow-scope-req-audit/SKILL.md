---
name: docs-workflow-scope-req-audit
description: Classify JIRA requirements by code evidence status before planning. Queries the code-finder index once per requirement to determine if each is grounded (implemented), partial, or absent in the codebase. Prevents hallucinated documentation for unimplemented features and surfaces gaps for implemented ones. Conditional on has_source_repo. Reuses find_evidence.py from the code-evidence step.
argument-hint: <ticket> --base-path <path> --repo <path> [--grounded-threshold <float>] [--absent-threshold <float>]
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Scope Requirements Audit Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → run tool → write output**.

This skill classifies each JIRA requirement from the requirements step as grounded, partial, or absent by querying the code-finder index. The planning step then uses these classifications to scope documentation modules — grounded requirements get full specs, partial ones are flagged for SME review, and absent ones are deferred to prevent documenting unimplemented features.

This is a tool-only step (no agent dispatch). Claude executes the steps directly.

## Prerequisites

- **code-finder** Python package. Install once with `python3 -m pip install code-finder`, or let the step auto-install via `uv run --with code-finder` (requires **uv**: `brew install uv` on macOS, or see https://docs.astral.sh/uv/getting-started/installation/)
- The `find_evidence.py` wrapper script from the code-evidence step at `plugins/docs-tools/skills/code-evidence/scripts/find_evidence.py`

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--repo <path>` — Path to the source code repository (required, provided by orchestrator)
- `--grounded-threshold <float>` — Minimum top score for grounded classification (default: 0.5)
- `--absent-threshold <float>` — Maximum top score for absent classification (default: 0.25)

## Input

```text
<base-path>/requirements/requirements.md
<repo-path>/
```

## Output

```text
<base-path>/scope-req-audit/evidence-status.json
<base-path>/scope-req-audit/summary.md
<base-path>/scope-req-audit/step-result.json
```

## Execution

### 1. Parse arguments and validate inputs

Extract the ticket ID, `--base-path`, `--repo`, and optional threshold overrides from the args string.

Set the paths:

```bash
REQUIREMENTS_FILE="${BASE_PATH}/requirements/requirements.md"
OUTPUT_DIR="${BASE_PATH}/scope-req-audit"
EVIDENCE_STATUS_FILE="${OUTPUT_DIR}/evidence-status.json"
SUMMARY_FILE="${OUTPUT_DIR}/summary.md"
QUERIES_FILE="${OUTPUT_DIR}/queries.json"
mkdir -p "$OUTPUT_DIR"
```

Set threshold defaults:

```
GROUNDED_THRESHOLD=0.5   (or value from --grounded-threshold)
ABSENT_THRESHOLD=0.25    (or value from --absent-threshold)
```

Validate:
- Verify `--repo` was provided. If not, STOP with error: "scope-req-audit requires --repo. The orchestrator should provide the repo path."
- Verify `$REQUIREMENTS_FILE` exists. If not, STOP with error: "Requirements step must complete before scope-req-audit."
- Verify the repo path exists and is a directory. If not, STOP with error: "Repo path does not exist: `<path>`."

Locate the `find_evidence.py` script from the code-evidence skill.

Claude Code:

```bash
FIND_EVIDENCE_SCRIPT="${CLAUDE_PLUGIN_ROOT}/skills/code-evidence/scripts/find_evidence.py"
```

Cursor (paths are relative to the repository root):

```bash
FIND_EVIDENCE_SCRIPT="plugins/docs-tools/skills/code-evidence/scripts/find_evidence.py"
```

Verify the script exists. If not, STOP with error: "find_evidence.py not found at expected path."

### 2. Discover related repos

Scan the source repo's top-level markdown files for GitHub and GitLab repository URLs that are not the current repo. This provides context for recommended actions when requirements are absent.

Files to scan:
- `README.md`, `README.rst`, `README`
- `CONTRIBUTING.md`
- `docs/*.md` (one level only)

For each file, extract URLs matching:
- `https://github.com/<org>/<repo>` (GitHub)
- `https://gitlab.<host>/<path>` (GitLab)

Filter out:
- The current repo URL (discover the remote via `git remote -v` in the repo directory and use the first available remote's URL). Normalize before comparing: strip trailing `.git`, convert `git@<host>:<org>/<repo>` SSH URLs to `https://<host>/<org>/<repo>` form
- Duplicate URLs (after normalization)
- URLs that are clearly not repos (e.g., GitHub issue links, badge URLs)

Store the results as a list of `discovered_repos` entries, each with:
- `url` — the repository URL
- `source` — the file and approximate location where it was found (e.g., `README.md`)
- `relevance` — a brief note on why it might be relevant (e.g., "Python SDK referenced in project README")

### 3. Parse requirements

Read `$REQUIREMENTS_FILE` and extract each requirement. The requirements-analyst produces requirements in this pattern:

```
### REQ-NNN: [title]

**Summary**: [description]
```

For each requirement, extract:
- `id` — the REQ-NNN identifier
- `title` — the requirement title
- `summary` — the summary text

If no requirements are found matching this pattern, STOP with error: "No requirements found in requirements.md. Expected REQ-NNN pattern."

### 4. Build queries and run batch retrieval

For each requirement, generate one natural-language search query that tests for implementation evidence. Convert the requirement summary into a query focused on code existence:

- Strip documentation-oriented language ("document how to", "explain the", "describe the")
- Focus on the implementation artifact (e.g., "Python SDK client library" not "Python SDK documentation")
- Keep the query specific enough to distinguish from tangential matches

Examples:
- REQ "CA bundle configuration support" → query "CA bundle configuration implementation"
- REQ "Python SDK for notebook-based workflows" → query "Python SDK client library implementation"
- REQ "Kueue workload scheduling integration" → query "Kueue queue integration workload scheduling"
- REQ "Audit logging for evaluation jobs" → query "audit logging implementation evaluation jobs"

Write the queries to `$QUERIES_FILE` as a JSON array:

```json
[
  {"query": "CA bundle configuration implementation", "limit": 5},
  {"query": "Python SDK client library implementation", "limit": 5}
]
```

Then run batch retrieval using `find_evidence.py`. First, check if code-finder is already installed:

```bash
python3 -c "import claude_context.skills.evidence_retrieval" 2>/dev/null && echo "INSTALLED" || echo "NOT_INSTALLED"
```

If **INSTALLED**, run directly:

```bash
python3 "$FIND_EVIDENCE_SCRIPT" \
  --repo "$REPO_PATH" \
  --queries-file "$QUERIES_FILE" \
  --limit 5
```

If **NOT_INSTALLED**, fall back to uv:

```bash
uv run --with code-finder python3 "$FIND_EVIDENCE_SCRIPT" \
  --repo "$REPO_PATH" \
  --queries-file "$QUERIES_FILE" \
  --limit 5
```

The script outputs a JSON array of results to stdout. Capture this output.

This creates the code-finder index on the first query. The index is cached at `{repo}/.vibe2doc/index.db` and will be reused by the later code-evidence step.

### 5. Classify results

Parse the batch retrieval output. For each requirement's query results, classify based on the top-N results:

The batch retrieval output is a JSON array. Each entry has the structure:

```json
{
  "query": "...",
  "filter_paths": null,
  "result": {
    "query": "...",
    "repo_path": "...",
    "result_count": 5,
    "results": [
      {
        "rank": 1,
        "file_path": "...",
        "scores": {"vector": 0.37, "bm25": 17.1, "combined": 0.78},
        ...
      }
    ]
  }
}
```

Results are under `result.results` (not `result.chunks`). Scores are under each result's `scores.combined` (not `combined_score`).

Classify based on the top-N results:

**Grounded:** top hit `scores.combined` >= grounded threshold (default 0.5) AND 2 or more snippets with scores above the absent threshold.

**Partial:** top hit score is between the absent and grounded thresholds, OR only 1 snippet scores above the grounded threshold. This covers cases where a stub, configuration reference, or partial implementation exists but the full feature is unclear.

**Absent:** top hit score < absent threshold (default 0.25), or the result set is empty. This indicates no meaningful code evidence for the requirement.

For each requirement, record:
- `id`, `title` — from step 3
- `query` — the search query used
- `status` — `grounded`, `partial`, or `absent`
- `top_score` — the highest `scores.combined` from the results
- `snippet_count` — number of result snippets returned
- `key_files` — file paths from the top 3 results (deduplicated)

### 6. Generate recommended actions

For each **partial** or **absent** requirement, generate a contextual recommended action and assign a gap category.

Read the prompt from `${CLAUDE_SKILL_DIR}/prompts/gap-classification.md`. Combine it with:
- The list of partial and absent requirements (id, title, status, top_score, snippet_count, key_files)
- The `discovered_repos` list from step 2

Use the prompt to generate a `recommended_action` and `gap_category` for each partial or absent requirement.

For **grounded** requirements, set `recommended_action` and `gap_category` to `null`.

### 7. Write output

#### evidence-status.json

Write the complete classification results to `$EVIDENCE_STATUS_FILE`:

```json
{
  "ticket": "<TICKET>",
  "repo_path": "<REPO_PATH>",
  "thresholds": { "grounded": 0.5, "absent": 0.25 },
  "recommendation": "proceed|gather-more|review-needed",
  "requirements": [
    {
      "id": "REQ-001",
      "title": "...",
      "query": "...",
      "status": "grounded|partial|absent",
      "top_score": 0.87,
      "snippet_count": 4,
      "key_files": ["path/to/file.go"],
      "gap_category": null,
      "recommended_action": null
    }
  ],
  "summary": {
    "grounded": 0,
    "partial": 0,
    "absent": 0,
    "total": 0
  },
  "discovered_repos": [
    {
      "url": "https://github.com/org/repo",
      "source": "README.md",
      "relevance": "..."
    }
  ]
}
```

The `recommendation` field is derived from the summary counts:
- **`proceed`** — no absent requirements
- **`gather-more`** — some absent requirements, but grounded outnumber absent
- **`review-needed`** — absent requirements equal or outnumber grounded, or more than half of all requirements are absent

The `gap_category` field classifies the type of missing evidence for partial and absent requirements. Set to `null` for grounded requirements.

#### summary.md

Write a human-readable summary to `$SUMMARY_FILE`:

```markdown
# Scope Requirements Audit

**Ticket:** <TICKET>
**Repository:** <REPO_PATH>
**Thresholds:** grounded >= <GROUNDED_THRESHOLD>, absent < <ABSENT_THRESHOLD>
**Recommendation:** proceed|gather-more|review-needed

## Classification Summary

| Status | Count |
|--------|-------|
| Grounded | N |
| Partial | N |
| Absent | N |
| **Total** | **N** |

## Grounded Requirements

- **REQ-001: [title]** — score: 0.87, files: `path/to/file.go`, `path/to/other.go`

## Partial Requirements

- **REQ-003: [title]** — score: 0.41, category: implementation, files: `path/to/stub.go`
  Action: [recommended_action]

## Absent Requirements

- **REQ-002: [title]** — score: 0.12, category: sdk
  Action: [recommended_action]

## Discovered Repos (not indexed)

- [https://github.com/org/companion-sdk](https://github.com/org/companion-sdk) — referenced in README.md
```

### 8. Write step-result.json

Write the sidecar to `${OUTPUT_DIR}/step-result.json`:

```json
{
  "schema_version": 1,
  "step": "scope-req-audit",
  "ticket": "<TICKET>",
  "completed_at": "<current ISO 8601 timestamp>",
  "recommendation": "<recommendation from evidence-status.json>",
  "grounded": <grounded count>,
  "partial": <partial count>,
  "absent": <absent count>,
  "total": <total count>,
  "discovered_repos_count": <length of discovered_repos list>
}
```

- `recommendation`: the `recommendation` field from `evidence-status.json`
- `grounded`, `partial`, `absent`, `total`: the counts from `evidence-status.json`'s `summary` object
- `discovered_repos_count`: length of the `discovered_repos` array

### 9. Verify output

Verify that `$EVIDENCE_STATUS_FILE`, `$SUMMARY_FILE`, and `${OUTPUT_DIR}/step-result.json` exist.

## How downstream steps use the output

The **planning step** checks for `<base-path>/scope-req-audit/evidence-status.json`. If it exists, the planner uses evidence status when scoping modules:

- **Grounded** requirements get full module specifications
- **Partial** requirements get module specifications with a gap note flagging SME review
- **Absent** requirements are listed in a "Deferred requirements (no code evidence)" section — no module specs are created for them

If `evidence-status.json` does not exist (step was skipped or not configured), the planning step works exactly as before — all requirements are included. This preserves composability.

## Notes

- The code-finder index is created on the first query and cached at `{repo}/.vibe2doc/index.db`. The later code-evidence step reuses this cached index
- Single-pass unfiltered retrieval is used (no source-scoped vs context distinction) since the goal is existence classification, not detailed snippet retrieval
- The thresholds (0.5 grounded, 0.25 absent) are based on empirical data from the comparison report — known-good matches scored 0.87+, known-absent items scored below 0.2
- This step queries the primary source repo only. Multi-repo querying is a follow-on enhancement
- The `discovered_repos` section helps bridge the multi-repo gap by surfacing companion repos that the user could add via `--source-code-repo` in a re-run
