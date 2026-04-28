---
name: docs-workflow-code-evidence
description: Retrieve code evidence from a source repository to ground documentation in actual implementation. Indexes using AST chunking and hybrid search, then retrieves relevant code snippets for each topic in the documentation plan. Uses two-pass retrieval — source-scoped for API accuracy, unfiltered for README/narrative context. Supports glob-based scope filtering for whole-repo or subdirectory-scoped documentation. Repo must be available (cloned by orchestrator or provided via --repo). Requires uv for automatic code-finder dependency management.
argument-hint: <ticket> --base-path <path> --repo <path> [--scope-include <globs>] [--scope-exclude <globs>] [--reindex] [--limit N]
allowed-tools: Read, Write, Glob, Grep, Bash
dependencies:
  python:
    - code-finder
---

# Code Evidence Retrieval Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → run tool → write output**.

This skill bridges code-finder's code analysis capabilities into the docs-orchestrator workflow. It indexes a source code repository using AST chunking and hybrid search (BM25 + vector), then retrieves code snippets relevant to the documentation plan topics. The writer step can then use this evidence to ground its output in actual implementation details.

The writer typically works from the **documentation repository**, not the code repository. The orchestrator handles cloning the source repo; this step receives the repo path and focuses on search.

## Prerequisites

- **code-finder** Python package. Install once with `python3 -m pip install code-finder`, or let the skill auto-install via `uv run --with code-finder` (requires **uv**: `brew install uv` on macOS, or see https://docs.astral.sh/uv/getting-started/installation/)
- The wrapper script `${CLAUDE_PLUGIN_ROOT}/skills/code-evidence/scripts/find_evidence.py` calls the code-finder Python API directly (no CLI entry point required)

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--repo <path>` — Path to the source code repository (required — provided by the orchestrator after clone/verify, or by the user for standalone invocation)
- `--scope-include <globs>` — Comma-separated glob patterns to include (e.g., `src/controllers/**,pkg/api/v1/**,README.md`). Scopes both source directory detection and search results. If omitted, the entire repo is in scope.
- `--scope-exclude <globs>` — Comma-separated glob patterns to exclude (e.g., `**/vendor/**,**/*_test.go`). Applied as post-retrieval filters since code-finder does not support exclude globs natively.
- `--reindex` — Force re-indexing even if a cached index exists
- `--limit <N>` — Max results per topic (default: 5)

## Input

```text
<base-path>/planning/plan.md
<repo-path>/                      (source repo, provided via --repo)
```

## Output

```text
<base-path>/code-evidence/evidence.json
<base-path>/code-evidence/summary.md
```

## Execution

### 1. Parse arguments

Extract the ticket ID, `--base-path`, `--repo`, and optional flags from the args string.

Set the paths:

```bash
PLAN_FILE="${BASE_PATH}/planning/plan.md"
OUTPUT_DIR="${BASE_PATH}/code-evidence"
EVIDENCE_FILE="${OUTPUT_DIR}/evidence.json"
SUMMARY_FILE="${OUTPUT_DIR}/summary.md"
mkdir -p "$OUTPUT_DIR"
```

Validate:
- Verify `--repo` was provided. If not, STOP with error: "code-evidence requires --repo. The orchestrator should provide the repo path."
- Verify `$PLAN_FILE` exists. If not, STOP with error: "Planning step must complete before code-evidence."
- Verify the wrapper script exists at `${CLAUDE_PLUGIN_ROOT}/skills/code-evidence/scripts/find_evidence.py`. If not, STOP with error: "find_evidence.py script not found."

### 2. Validate repo path

Verify the `--repo` path exists and is a directory. If not, STOP with error: "Repo path does not exist: `<path>`. The orchestrator should clone the repo before this step runs."

Set `REPO_PATH` to the provided path.

### 3. Detect source directories

Determine the source directories for the filtered pass (Pass 1). The goal is to identify where the actual source code lives so that Pass 1 returns function signatures, class definitions, and implementation details — not READMEs or test fixtures.

**If `--scope-include` was provided:**
- Use the include globs to derive source directory prefixes. For example, `src/controllers/**` → `src/controllers`. These become the `--filter-paths` for Pass 1.
- If `--scope-exclude` was provided, note the exclude patterns for post-retrieval filtering in step 5.

**If no scope was provided (whole-repo mode):**
- Scan the repo root for common source directory conventions:
  - General: `src/`, `lib/`, `pkg/`, `cmd/`, `internal/`, `app/`
  - Python: `src/<project_name>/` (detect via `setup.py`, `pyproject.toml`, or top-level package directories)
  - Java/Kotlin: `src/main/`
  - Go: directories containing `.go` files at the root level
- If recognizable source directories are found, use them for Pass 1
- If no recognizable source directories are found (flat repo, single-package project), use the repo root — Pass 1 and Pass 2 will search the same space, which is acceptable for small or flat repos

Store the detected source paths and any exclude patterns for use in step 5.

### 4. Extract topics from the plan

Read `$PLAN_FILE` and extract the key topics to search for. Look for:

- Module names and file paths mentioned in the plan
- Section headings that describe features or components
- JTBD statements or user goals that reference specific functionality
- API or CLI references

Produce a list of 5-15 natural language search queries that cover the plan's scope. Each query should be specific enough to retrieve relevant code (e.g., "authentication middleware implementation" not "auth").

Additionally, derive 1-2 **pattern-level queries** that ask how the codebase implements the general pattern, not the specific component. For example, if the plan is about adding Prometheus monitoring for a new component, add a query like "how do components implement monitoring and alerting" alongside the component-specific queries. These pattern queries help the unfiltered pass surface analogous implementations from other parts of the codebase, giving the writer examples to reference.

### 5. Run two-pass evidence retrieval for each topic

For each search query, run code-finder's evidence retrieval **twice** to capture both accurate source code and narrative context. Use **batch mode** to run all queries in a single process invocation — this pays the import and index-load cost once instead of per-query.

#### 5a. Build the queries file

Create a JSON file at `${OUTPUT_DIR}/queries.json` containing all queries for both passes. Each entry specifies the query text, result limit, and optional filter paths:

```json
[
  {"query": "auth middleware implementation", "limit": 5, "filter_paths": ["src/controllers"]},
  {"query": "auth middleware implementation", "limit": 5},
  {"query": "reconciler builder pattern",    "limit": 5, "filter_paths": ["src/controllers"]},
  {"query": "reconciler builder pattern",    "limit": 5}
]
```

For each search query derived from the plan, add **two entries**:

1. **Source-scoped** (Pass 1) — with `filter_paths` set to the source directories detected in step 3. Returns function signatures, class definitions, and implementation details.
2. **Unfiltered** (Pass 2) — without `filter_paths`. Picks up READMEs, documentation, examples, and configuration files that provide narrative context.

#### 5b. Run batch retrieval

First, check if code-finder is already installed:

```bash
python3 -c "import claude_context" 2>/dev/null && echo "INSTALLED" || echo "NOT_INSTALLED"
```

If **INSTALLED**, run directly (avoids re-downloading ~1GB of ML dependencies):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/code-evidence/scripts/find_evidence.py \
  --repo "$REPO_PATH" \
  --queries-file "${OUTPUT_DIR}/queries.json" \
  --limit <LIMIT>
```

If **NOT_INSTALLED**, fall back to uv:

```bash
uv run --with code-finder python3 ${CLAUDE_PLUGIN_ROOT}/skills/code-evidence/scripts/find_evidence.py \
  --repo "$REPO_PATH" \
  --queries-file "${OUTPUT_DIR}/queries.json" \
  --limit <LIMIT>
```

If `--reindex` is specified, add `--reindex` — it is applied to the first query only; subsequent queries reuse the freshly built index.

The script outputs a JSON array of results, one per query entry:

```json
[
  {"query": "auth middleware implementation", "filter_paths": ["src/controllers"], "result": { ... }},
  {"query": "auth middleware implementation", "filter_paths": null, "result": { ... }},
  ...
]
```

#### 5c. Post-retrieval processing

Parse the batch output. For each pair of results (source-scoped + unfiltered) corresponding to the same search query, assign them to `source_results` and `context_results` respectively.

**Post-retrieval exclude filtering**: If `--scope-exclude` patterns were provided, filter both source and context results after retrieval. Remove any result whose `file_path` matches an exclude glob (e.g., `**/vendor/**`, `**/*_test.go`). This is necessary because code-finder does not support exclude globs natively.

**Note on indexing**: The index is built once on the first query and cached at `{repo}/.vibe2doc/index.db`. All queries in the batch reuse the same cached index.

Collect all results into a combined evidence structure:

```json
{
  "ticket": "<TICKET>",
  "repo_path": "<REPO_PATH>",
  "scope": {
    "include": ["src/controllers/**", "pkg/api/v1/**"],
    "exclude": ["**/vendor/**"],
    "source_dirs_used": ["src/controllers", "pkg/api/v1"]
  },
  "topics": [
    {
      "query": "authentication middleware implementation",
      "source_results": [ ... ],
      "context_results": [ ... ]
    }
  ],
  "index_info": { ... }
}
```

The `scope` field records what was searched so downstream steps know the boundaries. If no scope was provided, `include` and `exclude` are `null` and `source_dirs_used` lists the auto-detected directories.

Write this to `$EVIDENCE_FILE`.

### 6. Generate evidence summary

Create a human-readable markdown summary at `$SUMMARY_FILE` with:

```markdown
# Code Evidence Summary

**Ticket:** <TICKET>
**Repository:** <REPO_PATH>
**Topics searched:** <N>
**Total code snippets found:** <N> (source: <N>, context: <N>)

## Topics

### 1. <query>

**Source code:**
- **<file_path>:<start_line>-<end_line>** — `<function_name>` (<chunk_type>)
  Score: <combined_score>
- ...

**Context (READMEs, docs, examples):**
- **<file_path>:<start_line>-<end_line>** — `<section_name>` (<chunk_type>)
  Score: <combined_score>
- ...

### 2. <query>
- ...
```

This summary is for human review. The JSON file is what downstream steps consume.

### 7. Write step-result.json

After generating the evidence, read `$EVIDENCE_FILE` to count topics and total snippets. Write the sidecar to `${OUTPUT_DIR}/step-result.json`:

```json
{
  "schema_version": 1,
  "step": "code-evidence",
  "ticket": "<TICKET>",
  "completed_at": "<current ISO 8601 timestamp>",
  "topic_count": 8,
  "snippet_count": 42,
  "repo_path": "<REPO_PATH>"
}
```

- `topic_count`: length of the `topics` array in `evidence.json`
- `snippet_count`: sum of all `source_results` and `context_results` entries across all topics

### 8. Verify output

After completion, verify that `$EVIDENCE_FILE`, `$SUMMARY_FILE`, and `${OUTPUT_DIR}/step-result.json` exist.

## How downstream steps use the evidence

The **writing step** can reference the evidence to ground documentation in actual code:

> The code evidence at `<base-path>/code-evidence/evidence.json` contains two types of evidence per topic:
> - **`source_results`**: Accurate function signatures, parameter types, class structure from the source code (scoped to source directories or `--scope-include` globs). Use these for API references, code examples, and technical accuracy.
> - **`context_results`**: README content, documentation, examples, and analogous implementations from across the repository. Use these for narrative flow, installation instructions, quickstart guides, and architectural context.
>
> Prefer source_results for "what the code does" and context_results for "why and how to use it."
>
> When `context_results` contain analogous patterns from other components (e.g., how another component implements the same monitoring, reconciler, or API pattern), use them to explain the general pattern first, then show how this component follows it. This gives readers both the "how it works here" and the "how the project does this in general" perspective.

The **technical review step** can use it to verify claims:

> Cross-reference documentation claims against the code evidence at `<base-path>/code-evidence/evidence.json`. Use `source_results` to verify function signatures, parameters, and return types. Flag any claims that contradict the retrieved source code.

## Notes

- First run on a repo takes a few seconds to a few minutes depending on repo size (AST chunking + embeddings)
- Subsequent runs reuse the cached index at `{repo}/.vibe2doc/index.db`
- Use `--reindex` after significant code changes
- The index is deterministic — same code produces the same index
- Evidence retrieval uses hybrid search: BM25 for exact keyword matches + vector search for semantic similarity
- Default index exclusions skip `archive/`, `vendor/`, `node_modules/`, `docs/generated/`, `.vibe2doc/`, and other non-source directories
- The two-pass approach adds negligible overhead (~30-200ms per query) since both passes reuse the same cached index
- `--scope-include` narrows the Pass 1 filter paths but does not affect indexing — the entire repo is indexed, and scope is applied at query time
- `--scope-exclude` is applied as post-retrieval filtering since code-finder does not support exclude globs natively. Results matching exclude patterns are removed from both pass outputs before writing to evidence.json
- The repo clone is managed by the orchestrator (see the "Resolve source repository" section in the orchestrator skill). This step does not clone or manage repos — it receives a path via `--repo`
