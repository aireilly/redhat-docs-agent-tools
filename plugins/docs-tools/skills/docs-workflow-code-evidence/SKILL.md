---
name: docs-workflow-code-evidence
description: Retrieve code evidence from a source repository to ground documentation in actual implementation. Clones the code repo if needed (from PR URL), indexes using AST chunking and hybrid search, then retrieves relevant code snippets for each topic in the documentation plan. Uses two-pass retrieval — source-scoped for API accuracy, unfiltered for README/narrative context. Requires code-finder to be pip-installed.
argument-hint: <ticket> --base-path <path> [--repo <code-repo-path>] [--reindex] [--limit N]
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Code Evidence Retrieval Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → run tool → write output**.

This skill bridges code-finder's code analysis capabilities into the docs-orchestrator workflow. It indexes a source code repository using AST chunking and hybrid search (BM25 + vector), then retrieves code snippets relevant to the documentation plan topics. The writer step can then use this evidence to ground its output in actual implementation details.

The writer typically works from the **documentation repository**, not the code repository. This skill handles cloning the code repo from the PR URL when needed.

## Prerequisites

- **code-finder** must be pip-installed: `pip install code-finder`
- `git` must be available for cloning code repositories
- `gh` CLI is recommended for private repos (uses GitHub auth)

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--repo <path>` — Path to a local clone of the source code repository (optional — if omitted, the skill clones the repo from the PR URL in the requirements output)
- `--reindex` — Force re-indexing even if a cached index exists
- `--limit <N>` — Max results per topic (default: 5)

## Input

```
<base-path>/planning/plan.md
<base-path>/requirements/requirements.md   (for PR URL when --repo is not provided)
```

## Output

```
<base-path>/code-evidence/evidence.json
<base-path>/code-evidence/summary.md
<base-path>/code-repo/                     (cloned repo, if not provided via --repo)
```

## Execution

### 1. Parse arguments

Extract the ticket ID, `--base-path`, `--repo` (optional), and optional flags from the args string.

Set the paths:

```bash
PLAN_FILE="${BASE_PATH}/planning/plan.md"
OUTPUT_DIR="${BASE_PATH}/code-evidence"
EVIDENCE_FILE="${OUTPUT_DIR}/evidence.json"
SUMMARY_FILE="${OUTPUT_DIR}/summary.md"
CLONE_DIR="${BASE_PATH}/code-repo"
mkdir -p "$OUTPUT_DIR"
```

Validate:
- Verify `$PLAN_FILE` exists. If not, STOP with error: "Planning step must complete before code-evidence."
- Verify `code-finder-evidence` is available (i.e., code-finder is pip-installed). If not, STOP with error: "code-finder not installed. Run: pip install code-finder"

### 2. Ensure code repo is available

If `--repo <path>` was provided:
- Verify the path exists and is a directory
- If not, STOP with error: "Repo path does not exist: <path>"
- Set `REPO_PATH` to the provided path

If `--repo` was NOT provided:
- Check if `$CLONE_DIR` already exists (from a previous run). If so, reuse it and set `REPO_PATH="${CLONE_DIR}"`.
- If not, extract the repo URL from the requirements step output:

  ```bash
  # Read requirements output for PR URL
  REQUIREMENTS_FILE="${BASE_PATH}/requirements/requirements.md"
  ```

  Extract the git clone URL from the PR URL. For GitHub PRs:

  ```bash
  # From PR URL like https://github.com/org/repo/pull/123
  # Derive: https://github.com/org/repo.git
  REPO_URL=$(echo "$PR_URL" | sed 's|/pull/[0-9]*||').git
  ```

  Or use `gh` for private repos:

  ```bash
  REPO_URL=$(gh pr view "$PR_URL" --json headRepository --jq '.headRepository.url')
  ```

  Extract the PR branch name so the clone reflects the code being documented, not just `main`:

  ```bash
  PR_BRANCH=$(gh pr view "$PR_URL" --json headRefName --jq '.headRefName')
  ```

  Clone the repo at the PR branch (shallow — file contents are sufficient, git history is not needed):

  ```bash
  git clone --depth 1 --branch "$PR_BRANCH" "$REPO_URL" "$CLONE_DIR"
  ```

  If the branch clone fails (e.g., fork-based PR where the branch isn't on the upstream repo), fall back to cloning the default branch:

  ```bash
  git clone --depth 1 "$REPO_URL" "$CLONE_DIR"
  ```

  If the clone fails, STOP with a clear error:
  - **Auth failure**: "Cannot clone <REPO_URL>. For private repos, ensure `gh` is authenticated or provide `--repo <local_path>`."
  - **Bad URL**: "Could not extract repo URL from PR. Provide `--repo <local_path>` explicitly."
  - **Network error**: "Clone failed for <REPO_URL>. Check network connectivity."

  Set `REPO_PATH="${CLONE_DIR}"`.

### 3. Detect source directories

Identify the repository's source code directories for the filtered pass. Look for common patterns:

- `src/`, `lib/`, `pkg/`, `cmd/`, `internal/`, `app/`
- Language-specific: `src/<project_name>/` (Python), `src/main/` (Java/Kotlin)

If a PR URL is available in the requirements step output, extract changed file paths and derive their parent directories as the filter scope.

Store the detected source paths for use in step 4.

### 4. Extract topics from the plan

Read `$PLAN_FILE` and extract the key topics to search for. Look for:

- Module names and file paths mentioned in the plan
- Section headings that describe features or components
- JTBD statements or user goals that reference specific functionality
- API or CLI references

Produce a list of 5-15 natural language search queries that cover the plan's scope. Each query should be specific enough to retrieve relevant code (e.g., "authentication middleware implementation" not "auth").

Additionally, derive 1-2 **pattern-level queries** that ask how the codebase implements the general pattern, not the specific component. For example, if the plan is about adding Prometheus monitoring for a new component, add a query like "how do components implement monitoring and alerting" alongside the component-specific queries. These pattern queries help the unfiltered pass surface analogous implementations from other parts of the codebase, giving the writer examples to reference.

### 5. Run two-pass evidence retrieval for each topic

For each search query, run code-finder's evidence retrieval **twice** to capture both accurate source code and narrative context:

**Pass 1 — Source-scoped** (API accuracy):

```bash
code-finder-evidence \
  --repo "$REPO_PATH" \
  --query "<search_query>" \
  --limit <LIMIT> \
  --filter-paths <SOURCE_DIRS>
```

Where `<SOURCE_DIRS>` is the comma-separated list of source directories detected in step 3 (e.g., `src/speculators`). Filter paths are resolved relative to the repo path automatically.

This pass returns function signatures, class definitions, and implementation details scoped to actual source code.

**Pass 2 — Unfiltered** (narrative context):

```bash
code-finder-evidence \
  --repo "$REPO_PATH" \
  --query "<search_query>" \
  --limit <LIMIT>
```

This pass picks up READMEs, documentation, examples, and configuration files that provide the "why", installation steps, quickstart patterns, and architectural context.

**Note on indexing**: The index is built once on the first query and cached at `{repo}/.vibe2doc/index.db`. Both passes and all subsequent queries reuse the cached index. The second pass adds ~30-200ms per query, not a full re-index.

If `--reindex` is specified, add it to the **first** query only. Subsequent queries reuse the freshly built index.

Collect all results into a combined evidence structure:

```json
{
  "ticket": "<TICKET>",
  "repo_path": "<REPO_PATH>",
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

### 7. Verify output

After completion, verify that both `$EVIDENCE_FILE` and `$SUMMARY_FILE` exist.

## How downstream steps use the evidence

The **writing step** can reference the evidence to ground documentation in actual code:

> The code evidence at `<base-path>/code-evidence/evidence.json` contains two types of evidence per topic:
> - **`source_results`**: Accurate function signatures, parameter types, class structure from the PR branch source code. Use these for API references, code examples, and technical accuracy.
> - **`context_results`**: README content, documentation, examples, and analogous implementations from other parts of the codebase. Use these for narrative flow, installation instructions, quickstart guides, and architectural context.
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
- Shallow clone (`--depth 1`) is sufficient — code-finder indexes file contents, not git history
- The cloned repo is cached at `<base-path>/code-repo/` and reused on resume
