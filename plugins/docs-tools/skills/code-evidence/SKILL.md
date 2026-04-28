---
name: code-evidence
description: Search a code repository for evidence matching a natural language query. Uses AST chunking and hybrid search (BM25 + vector) to find relevant functions, classes, methods, configuration, and documentation. Returns ranked code snippets with file paths, signatures, and relevance scores.
argument-hint: --repo <path> --query "<search query>" [--filter-paths <dirs>] [--limit N] [--reindex]
allowed-tools: Read, Bash
dependencies:
  python:
    - code-finder
---

# Code Evidence Retrieval

Standalone skill for searching a code repository using natural language queries. Retrieves ranked code snippets grounded in actual source code — function signatures, class definitions, configuration blocks, and documentation.

Uses hybrid search: BM25 for exact keyword matches + vector embeddings for semantic similarity. The index is built once per repo using AST chunking (tree-sitter) and cached for subsequent queries.

## Prerequisites

- **code-finder** Python package. Install once with `python3 -m pip install code-finder`, or let the skill auto-install via `uv run --with code-finder` (requires **uv**: `brew install uv` on macOS, or see https://docs.astral.sh/uv/getting-started/installation/)
- The wrapper script at `${CLAUDE_SKILL_DIR}/scripts/find_evidence.py` calls the code-finder Python API directly (no CLI entry point required)

## Arguments

- `--repo <path>` — Path to the repository to search (required)
- `--query "<query>"` — Natural language search query (single query mode)
- `--queries-file <path>` — Path to a JSON file with batch queries (use instead of `--query` for multiple searches in one invocation). Schema: `[{"query": "...", "limit": N, "filter_paths": ["dir1", "dir2"]}, ...]`
- `--filter-paths <dirs>` — Comma-separated directory prefixes to scope results (e.g., `src/auth,src/config`). Single query mode only. Resolved relative to the repo root.
- `--limit <N>` — Max results to return (default: 5). In batch mode, acts as default limit per query (overridden by per-entry `limit`).
- `--reindex` — Force re-indexing even if a cached index exists (in batch mode, applied to first query only)

## Execution

### 1. Parse arguments

Extract `--repo`, `--query`, and optional flags from the args string.

Validate:
- Verify the repo path exists. If not, STOP with error: "Repo path does not exist: <path>"
- Verify the wrapper script exists. If not, STOP with error: "find_evidence.py script not found."

### 2. Run evidence retrieval

First, check if code-finder is already installed:

```bash
python3 -c "import claude_context" 2>/dev/null && echo "INSTALLED" || echo "NOT_INSTALLED"
```

Use the appropriate command based on the result. If **INSTALLED**, run directly (avoids re-downloading ~1GB of ML dependencies). If **NOT_INSTALLED**, prefix with `uv run --with code-finder`.

**Direct (code-finder installed):**

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/find_evidence.py \
  --repo "<REPO_PATH>" \
  --query "<QUERY>" \
  --limit <LIMIT>
```

**Fallback (via uv):**

```bash
uv run --with code-finder python3 ${CLAUDE_SKILL_DIR}/scripts/find_evidence.py \
  --repo "<REPO_PATH>" \
  --query "<QUERY>" \
  --limit <LIMIT>
```

If `--filter-paths` was provided, add `--filter-paths <FILTER_PATHS>` to the command.

If `--reindex` was provided, add `--reindex` to the command.

### 3. Present results

Parse the JSON output and present results to the user in a readable format:

```markdown
## Results for: "<query>"

**Repository:** <repo_path>
**Results:** <count>

### 1. <file_name>:<start_line>-<end_line> — `<chunk_name>` (<chunk_type>)
   Score: <combined_score> (vector: <vector_score>, BM25: <bm25_score>)

   ```<language>
   <content preview — first 20 lines>
   ```

### 2. ...
```

Include the full content of each result so the user can see the actual code. If a result has a signature or docstring, show those prominently.

## Notes

- First run on a repo takes a few seconds to a few minutes depending on repo size (AST chunking + embeddings)
- Subsequent runs reuse the cached index at `{repo}/.vibe2doc/index.db`
- Use `--reindex` after significant code changes
- Default index exclusions skip `archive/`, `vendor/`, `node_modules/`, `docs/generated/`, `.vibe2doc/`, and other non-source directories
- Supports Go, Python, JavaScript, and TypeScript via tree-sitter grammars
- `--filter-paths` is useful for scoping to specific modules (e.g., `--filter-paths src/auth` to search only the auth module)

## Examples

Search an entire repo:
```text
Skill: docs-tools:code-evidence, args: "--repo /path/to/repo --query \"how does authentication work\""
```

Search scoped to specific directories:
```text
Skill: docs-tools:code-evidence, args: "--repo /path/to/repo --query \"reconciler builder pattern\" --filter-paths internal/controller,pkg/reconciler"
```

Re-index after pulling new changes:
```text
Skill: docs-tools:code-evidence, args: "--repo /path/to/repo --query \"new feature\" --reindex"
```
