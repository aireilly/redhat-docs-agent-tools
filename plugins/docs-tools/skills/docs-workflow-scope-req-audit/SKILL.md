---
name: docs-workflow-scope-req-audit
description: Classify JIRA requirements by code evidence status before planning. Fans out one subagent per requirement for isolated classification — each subagent queries the code-finder index independently, keeping context clean regardless of requirement count. Prevents hallucinated documentation for unimplemented features and surfaces gaps for implemented ones. Conditional on has_source_repo.
argument-hint: <ticket> --base-path <path> --repo <path> [--grounded-threshold <float>] [--absent-threshold <float>]
allowed-tools: Read, Write, Glob, Grep, Bash, Agent
---

# Scope Requirements Audit Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → fan out → merge → write output**.

This skill classifies each JIRA requirement from the requirements step as grounded, partial, or absent by dispatching one subagent per requirement. Each subagent queries the code-finder index independently with a clean context window. The planning step then uses these classifications to scope documentation modules — grounded requirements get full specs, partial ones are flagged for SME review, and absent ones are deferred to prevent documenting unimplemented features.

## Prerequisites

- **code-finder** Python package (install with `python3 -m pip install code-finder`).

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

### 4. Pre-flight: warm the code-finder index

Warm the code-finder index before fanning out. This ensures the index is built once (expensive) and all subagents reuse the cached index at `{repo}/.vibe2doc/index.db`. Run one throwaway query:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/code-evidence/scripts/find_evidence.py --repo "$REPO_PATH" --query "initialization" --limit 1
```

Discard the output. If this fails, STOP with error including the stderr output — the index cannot be built.

### 5. Fan out: dispatch one agent per requirement

For each requirement extracted in step 3, dispatch one Agent call. Launch ALL requirement agents in a **single message** (parallel execution).

For each requirement, use:

```
Agent:
  subagent_type: docs-tools:evidence-classifier
  model: haiku
  description: "Classify REQ-NNN: <title truncated to 40 chars>"
  prompt: |
    Classify this requirement by code evidence status.

    REQUIREMENT:
    - ID: <id>
    - Title: <title>
    - Summary: <summary>

    CONFIGURATION:
    - REPO_PATH: <absolute repo path>
    - GROUNDED_THRESHOLD: <threshold>
    - ABSENT_THRESHOLD: <threshold>

    DISCOVERED_REPOS:
    <JSON array of discovered_repos from step 2, or [] if none>
```

**Important:** All Agent calls MUST be in a single message so they run in parallel. Do not dispatch them sequentially.

### 6. Merge: collect agent results

Each agent returns a JSON object. Parse each agent's response to extract the JSON.

If an agent's response is not valid JSON or is missing required fields (`id`, `status`), create a fallback entry:

```json
{
  "id": "<expected REQ-NNN>",
  "title": "<expected title>",
  "query": "unknown",
  "status": "absent",
  "error": "Agent did not return valid JSON",
  "top_score": 0.0,
  "snippet_count": 0,
  "key_files": [],
  "gap_category": null,
  "recommended_action": null
}
```

Fallback entries use `"status": "absent"` so the downstream contract (`grounded|partial|absent`) is preserved. The optional `"error"` field carries diagnostic detail for debugging.

Collect all per-requirement results into a list ordered by requirement ID.

Compute summary counts:
- `grounded` — count of requirements with status `grounded`
- `partial` — count of requirements with status `partial`
- `absent` — count of requirements with status `absent`
- `total` — total requirements

Compute the recommendation:
- **`proceed`** — no absent requirements
- **`gather-more`** — some absent requirements, but grounded outnumber absent
- **`review-needed`** — absent requirements equal or outnumber grounded, or more than half of all requirements are absent

### 7. Write output

#### evidence-status.json

Write the merged classification results to `$EVIDENCE_STATUS_FILE`:

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

The output format is identical to the previous single-pass implementation. Downstream consumers (planning step, orchestrator) see no change.

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

- **Fanout pattern:** Each requirement is classified by an independent subagent with a clean context window. This prevents context degradation when processing many requirements — classification quality for REQ-015 is identical to REQ-001
- **Index warming:** The code-finder index is built once in step 4 (pre-flight) and cached at `{repo}/.vibe2doc/index.db`. All subagents reuse this cached index, so only the first query pays the indexing cost
- **Parallel execution:** All subagent Agent calls are dispatched in a single message for parallel execution. The orchestrator waits for all to complete before merging
- **Error isolation:** A failed subagent does not affect other requirements — the merge step creates a fallback entry with `"status": "absent"` and an `"error"` field for diagnostics
- **Model choice:** Subagents use `model: haiku` since the task is mechanical (run script, parse JSON, apply thresholds). The gap classification requires minimal language understanding
- **Intermediate artifacts:** The previous version wrote a `queries.json` file to the output directory. This file is no longer produced — each subagent builds its query internally. The file was not consumed by any downstream step
- The thresholds (0.5 grounded, 0.25 absent) are based on empirical data from the comparison report — known-good matches scored 0.87+, known-absent items scored below 0.2
- This step queries the primary source repo only. Multi-repo querying is a follow-on enhancement
- The `discovered_repos` section helps bridge the multi-repo gap by surfacing companion repos that the user could add via `--source-code-repo` in a re-run
