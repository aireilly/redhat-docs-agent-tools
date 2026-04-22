# Gap Classification Prompt

You are assessing whether JIRA documentation requirements have code evidence in a source repository. For each requirement classified as **partial** or **absent**, generate a recommended action and assign a gap category.

## Input

You will receive:
- A list of requirements with their classification status, top score, snippet count, and key files
- A list of discovered repos (companion repositories found in the source repo's README/docs but not indexed)

## Recommended Actions

For each partial or absent requirement, write a concise recommended action (one or two sentences):

- If the requirement's topic appears in a `discovered_repos` entry, reference that specific repo (e.g., "eval-hub-sdk (referenced in README.md) may contain Python SDK implementation")
- If partial evidence exists (stubs, config, tests), note what was found and what is missing
- If no evidence exists, suggest confirming with SME whether the feature is implemented

## Gap Categories

Assign exactly one category to each partial or absent requirement:

- `api_reference` — missing API specs, CRD definitions, or endpoint documentation
- `implementation` — missing core feature implementation code
- `sdk` — missing SDK, client library, or CLI tooling
- `configuration` — missing configuration options, environment variables, or CR fields
- `architecture` — missing design docs, component relationships, or data flow
- `examples` — missing sample configurations, tutorials, or quickstart content

## Output Format

For each requirement, produce:

```json
{
  "id": "REQ-NNN",
  "gap_category": "implementation",
  "recommended_action": "One or two sentence recommendation."
}
```
