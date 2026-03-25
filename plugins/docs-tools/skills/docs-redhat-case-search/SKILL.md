---
name: docs-redhat-case-search
description: Search and retrieve Red Hat support cases. Full-text search via Hydra, single case details and comments via REST API. Outputs to a folder for orchestrator integration.
argument-hint: <query> [--output-dir <path>] [--product <name>] [--severity <level>] [--status <status>] [--type <type>] [--rows <n>]
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Red Hat Case Search

> **Note:** PII (names, emails, account numbers) is stripped from all output. The Hydra field list excludes PII fields entirely, REST API responses are scrubbed before display or file output. Ensure `REDHAT_API_TOKEN` is stored as a masked CI secret.

Search and retrieve Red Hat support cases using two APIs:
- **Hydra Search** — full-text search with facets, wildcards, and filtering
- **Support REST API** — get single case details, comments, and list cases

By default, searches return only **open cases** scoped to case type **"Usage / Documentation Help"**, sorted by **severity** (urgent first). Use `--include-closed` to include closed cases, `--type` to change the case type filter.

## Prerequisites

- Python 3 with `requests` library (`python3 -m pip install requests`)
- `REDHAT_API_TOKEN` set in `~/.env` (offline token from https://access.redhat.com/management/api)

## Usage

```bash
# Full-text search (Hydra)
python3 scripts/case_search.py <query> [options]

# Single case detail (REST API)
python3 scripts/case_search.py --get <case-number>

# Case comments (REST API)
python3 scripts/case_search.py --comments <case-number>

# List cases (REST API)
python3 scripts/case_search.py --list [options]
```

### Search examples

```bash
python3 scripts/case_search.py "vllm*"
python3 scripts/case_search.py "kernel panic" --product "Red Hat Enterprise Linux"
python3 scripts/case_search.py "openshift" --severity "1 (Urgent)" --rows 5
python3 scripts/case_search.py "openshift" --status Closed --start 10 --rows 10
python3 scripts/case_search.py "vllm" --json | jq '.[].case_number'
```

### Case detail examples

```bash
python3 scripts/case_search.py --get 04394864
python3 scripts/case_search.py --get 04394864 --raw
python3 scripts/case_search.py --comments 04394864
```

### List examples

```bash
python3 scripts/case_search.py --list --rows 5
python3 scripts/case_search.py --list --status "Waiting on Red Hat" --rows 10
```

### Output to directory (orchestrator integration)

```bash
python3 scripts/case_search.py "vllm*" --output-dir .claude/docs/proj-123/case-search/
```

## Options

| Option | Description |
|---|---|
| `--product <name>` | Filter by product name |
| `--severity <level>` | Filter: "1 (Urgent)", "2 (High)", "3 (Normal)", "4 (Low)" |
| `--status <status>` | Filter: "Waiting on Red Hat", "Waiting on", "Closed" |
| `--type <type>` | Filter by case type (default: "Usage / Documentation Help") |
| `--include-closed` | Include closed cases (excluded by default) |
| `--start <n>` | Pagination offset (default: 0) |
| `--rows <n>` | Results per page (default: 10) |
| `--output-dir <path>` | Write results to directory (cases.json + cases.md) |
| `--raw` | Output full raw JSON response |
| `--json` | Output cases as JSON array |
| `--get <num>` | Get single case details |
| `--comments <num>` | Get case comments |
| `--list` | List cases via REST API |

## Output

### Terminal (default)

Human-readable formatted output to stdout.

### Directory output (`--output-dir`)

When `--output-dir` is provided, results are written to the specified folder:

```text
<output-dir>/
  cases.json        # Raw case docs array (machine-readable)
  cases.md          # Markdown summary with per-case details and facet breakdowns
```

### Orchestrator integration

This skill can slot into the docs-workflow orchestrator as a step. The orchestrator passes `--output-dir <base-path>/case-search/`, and the step writes `cases.json` and `cases.md` to that directory.

To add as a workflow step in `docs-workflow.yaml`:

```yaml
- name: case-search
  skill: docs-tools:docs-redhat-case-search
  description: Search cases for related issues
```

The orchestrator invokes:

```text
Skill: docs-tools:docs-redhat-case-search, args: "<query> --output-dir <base-path>/case-search/ [--product <name>]"
```
