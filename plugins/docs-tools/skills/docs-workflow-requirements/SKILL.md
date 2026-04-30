---
name: docs-workflow-requirements
description: Analyze documentation requirements for a JIRA ticket using a two-pass fanout. Pass 1 dispatches a discovery agent to enumerate requirements. Pass 2 fans out one deep-analysis agent per requirement for isolated, thorough analysis. Assembles the standard requirements.md output. Invoked by the orchestrator.
argument-hint: <ticket> --base-path <path> [--pr <url>]...
allowed-tools: Read, Write, Glob, Grep, Edit, Bash, Skill, Agent, WebSearch, WebFetch
---

# Requirements Analysis Step

Step skill for the docs-orchestrator pipeline. Follows the step skill contract: **parse args → discover → fan out → merge → write output**.

This skill uses a two-pass architecture to analyze documentation requirements:

1. **Discovery pass** — A single `docs-tools:requirements-discoverer` agent enumerates requirements from JIRA, PRs, and specs, producing a JSON skeleton
2. **Deep analysis pass** — One `docs-tools:requirements-analyst` agent per requirement, all running in parallel, each performing thorough analysis with a clean context window
3. **Merge** — The orchestrator assembles per-requirement JSON results into the standard `requirements.md` format

## Arguments

- `$1` — JIRA ticket ID (required)
- `--base-path <path>` — Base output path (e.g., `.claude/docs/proj-123`)
- `--pr <url>` — PR/MR URL to include in analysis (repeatable)

## Output

```
<base-path>/requirements/requirements.md
<base-path>/requirements/step-result.json
```

## Execution

### 1. Parse arguments

Extract the ticket ID, `--base-path`, and any `--pr` URLs from the args string.

Set the output path:

```bash
OUTPUT_DIR="${BASE_PATH}/requirements"
OUTPUT_FILE="${OUTPUT_DIR}/requirements.md"
DISCOVERY_FILE="${OUTPUT_DIR}/discovery.json"
mkdir -p "$OUTPUT_DIR"
```

### 2. Pass 1 — Discovery

Dispatch one `docs-tools:requirements-discoverer` agent to enumerate requirements from all sources.

```
Agent:
  subagent_type: docs-tools:requirements-discoverer
  description: "Discover requirements for <TICKET>"
  prompt: |
    Discover documentation requirements for JIRA ticket <TICKET>.

    PR/MR URLs to include in analysis (merge with any auto-discovered, dedup):
    - <PR_URL_1>
    - <PR_URL_2>

    Save your JSON output to: <DISCOVERY_FILE>

    Follow your standard discovery procedure: JIRA fetch, ticket graph traversal,
    PR listing, spec identification, requirement enumeration.
```

The PR URL bullet list is conditional — include those bullets only if `--pr` URLs were provided.

After the agent completes, read `<DISCOVERY_FILE>`.

If the discovery JSON has an `error` field set, STOP and report the error (likely an access failure).

### 3. Parse discovery output

Read the discovery JSON and extract:
- `requirements` — the list of requirement skeletons
- `related_tickets` — shared context for all deep-analysis agents
- `release` — release/sprint identifier
- `ticket_summary` — primary ticket summary
- `sources_consulted` — all sources the discovery agent found

If `requirements` is empty, write a minimal `requirements.md` noting that no requirements were found, write `step-result.json`, and exit successfully.

### 4. Pass 2 — Fan out deep analysis

For each requirement in the discovery skeleton, dispatch one `docs-tools:requirements-analyst` agent. Launch ALL agents in a **single message** (parallel execution).

For each requirement, use:

```
Agent:
  subagent_type: docs-tools:requirements-analyst
  description: "Analyze REQ-NNN: <title truncated to 40 chars>"
  prompt: |
    Perform deep analysis of this single documentation requirement.

    REQUIREMENT:
    <JSON of the requirement skeleton: id, title, priority, category, sources, one_line_summary>

    RELATED_TICKETS:
    <JSON of related_tickets from discovery output>

    RELEASE: <release from discovery output>

    Fetch detailed content from each source, perform web search expansion,
    and produce complete documentation requirements with acceptance criteria.

    Print your JSON result to stdout.
```

**Important:** All Agent calls MUST be in a single message so they run in parallel.

### 5. Merge results

Each agent returns a JSON object (or text containing a JSON object). Parse each agent's response to extract the JSON.

If an agent's response is not valid JSON or is missing the `id` field, create a fallback entry. Carry forward the skeleton's source references so the requirement retains traceability even on failure:

```json
{
  "id": "<expected REQ-NNN>",
  "title": "<expected title from skeleton>",
  "error": "Agent did not return valid JSON",
  "priority": "<from skeleton>",
  "category": "<from skeleton>",
  "sources": [
    {"label": "<source.key or source.url>", "url": "<source.url>", "note": "From discovery (deep analysis failed)"}
  ],
  "summary": "<one_line_summary from skeleton>",
  "user_impact": null,
  "scope": null,
  "documentation_actions": [],
  "acceptance_criteria": [],
  "references": [],
  "web_findings": [],
  "is_breaking_change": false,
  "deprecation_version": null,
  "notes": "Deep analysis failed — using skeleton data only"
}
```

Convert each entry in the skeleton's `sources` array to the analyst format: use `key` (for JIRA) or the URL as the label, preserve the URL, and add a note indicating discovery-only data.

Collect all per-requirement results into a list ordered by requirement ID.

### 6. Assemble requirements.md

Write `<OUTPUT_FILE>` by assembling the merged results into the standard requirements format. The document structure must match the existing output contract exactly:

```markdown
# Documentation Requirements

**Source**: <ticket_summary from discovery>
**Date**: <YYYY-MM-DD>
**Release/Sprint**: <release from discovery>

## Summary

- Total requirements analyzed: <count>
- New modules needed: <count documentation_actions with action "Create">
- Existing modules to update: <count documentation_actions with action "Update">
- Breaking changes requiring docs: <count where is_breaking_change is true>

## Requirements by priority

### Critical

#### REQ-001: [title]
- **Source**: [label](url) | [label](url)
- **Summary**: [summary]
- **User impact**: [user_impact]
- **Documentation action**:
  - [ ] [action] `[file]` ([type]) [note if present]
- **Acceptance criteria**:
  - [ ] [criterion]
- **References**:
  - [label](url): [note]

### High
[Same format, requirements with priority "high"]

### Medium
[Same format, requirements with priority "medium"]

### Low
[Same format, requirements with priority "low"]

## Documentation scope

### New documentation needed

| Requirement | Scope | References |
|-------------|-------|------------|
| REQ-XXX | [From documentation_actions where action is "Create"] | [source labels] |

### Existing documentation to update

| Requirement | What changed | References |
|-------------|-------------|------------|
| REQ-XXX | [From documentation_actions where action is "Update"] | [source labels] |

## Breaking changes

[Table of requirements where is_breaking_change is true. Omit section if none.]

| Change | Migration steps needed | Deprecation notice | References |
|--------|------------------------|-------------------|------------|

## Notes

[Aggregate any non-null notes from requirements. Omit section if none.]

## Related tickets

[Format related_tickets from discovery output. Omit section if empty.]

## Sources consulted

### JIRA tickets
[From sources_consulted.jira_tickets — deduplicated across all requirements]

### Pull requests / Merge requests
[From sources_consulted.pull_requests — deduplicated]

### Code files
[From references with type "code" across all requirements — deduplicated]

### Existing documentation
[From sources_consulted.existing_docs — deduplicated]

### External references
[From references without type "code" that are not JIRA/PR/web_findings — deduplicated]

### Web search findings
[From web_findings across all requirements — deduplicated by URL]
```

**Priority section rules:**
- Only include priority sections that have requirements (omit empty `### High` if no high-priority requirements)
- Requirements with errors should be included under their original priority with a note: `**Note:** Deep analysis failed for this requirement. Skeleton data only.`

**Deduplication:** Sources consulted and references are gathered across all per-requirement results. Deduplicate by URL or file path.

### 7. Write step-result.json

Run the title-extraction script:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/parse_title.py "<OUTPUT_FILE>"
```

The script prints `{"title": "..."}` to stdout. If it exits non-zero, report the stderr message as an error.

Use the `title` value from the script's JSON output to write the sidecar to `<OUTPUT_DIR>/step-result.json`:

```json
{
  "schema_version": 1,
  "step": "requirements",
  "ticket": "<TICKET>",
  "completed_at": "<current ISO 8601 timestamp>",
  "title": "<first heading, max 80 chars>"
}
```

### 8. Verify output

Verify that `<OUTPUT_FILE>` and `<OUTPUT_DIR>/step-result.json` exist.

## Notes

- **Two-pass architecture:** Pass 1 (discovery) is lightweight — JIRA traversal, PR listing, spec identification. Pass 2 (deep analysis) is thorough — each requirement gets a dedicated agent with a clean context window
- **Context isolation:** Each deep-analysis agent sees only one requirement's sources. This prevents context degradation when analyzing tickets with 10+ requirements
- **Parallel execution:** All pass-2 agents are dispatched in a single message for parallel execution
- **Error isolation:** A failed deep-analysis agent does not block other requirements — the merge step uses skeleton data as a fallback
- **Output contract:** The assembled `requirements.md` is identical in format to the previous single-pass output. Downstream consumers (scope-req-audit, planning, orchestrator) see no change
- **Discovery JSON:** The `discovery.json` file is retained in the output directory as a debugging artifact. It is not consumed by downstream steps
- **Intermediate artifacts:** The previous version had the requirements-analyst save intermediary files to `artifacts/`. The deep-analysis agents do not write intermediary files — their structured JSON output is the artifact. If intermediary research is needed for audit, it can be reconstructed from the discovery JSON and per-requirement sources
