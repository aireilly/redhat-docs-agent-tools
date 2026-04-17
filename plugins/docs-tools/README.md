# docs-tools

!!! tip

    Always run Claude Code from a terminal in the root of the documentation repository you are working on. The docs-tools commands and agents operate on the current working directory, they read local files, check git branches, and write output relative to the repo root.

## Prerequisites

- Install the [Red Hat Docs Agent Tools marketplace](https://redhat-documentation.github.io/redhat-docs-agent-tools/install/)

- Install [software dependencies](https://redhat-documentation.github.io/redhat-docs-agent-tools/install/#software-dependencies)

- Create an `~/.env` file with your tokens:

    ```bash
    JIRA_API_TOKEN=your_jira_api_token
    # Required for Atlassian Cloud authentication
    JIRA_EMAIL=you@redhat.com
    # Optional: defaults to https://redhat.atlassian.net if not set
    JIRA_URL=https://redhat.atlassian.net
    # Required scopes: "repo" for private repos, "public_repo" for public repos
    GITHUB_TOKEN=your_github_pat
    # Required scope: "api"
    GITLAB_TOKEN=your_gitlab_pat
    ```
    
- Add the following to the end of your `~/.bashrc` (Linux) or `~/.zshrc` (macOS):
    
    ```bash
    if [ -f ~/.env ]; then
        set -a
        source ~/.env
        set +a
    fi
    ```

    Restart your terminal and Claude Code for changes to take effect.

## Customizing the docs workflow

The docs orchestrator (`/docs-orchestrator`) runs a YAML-defined step list. You can customize it per-repo without modifying the plugin.

### Override the workflow steps

The orchestrator looks for workflow YAML in this order:

1. `.claude/docs-<name>.yaml` — if `--workflow <name>` is passed
2. `.claude/docs-workflow.yaml` — project-level default
3. Plugin default — `skills/docs-orchestrator/defaults/docs-workflow.yaml`

To customize, download the default into your docs repo and edit it:

```bash
mkdir -p .claude
curl -sL https://raw.githubusercontent.com/redhat-documentation/redhat-docs-agent-tools/main/plugins/docs-tools/skills/docs-orchestrator/defaults/docs-workflow.yaml \
   -o .claude/docs-workflow.yaml
```

Then modify `.claude/docs-workflow.yaml` to add, remove, or reorder steps:

```yaml
workflow:
  name: docs-workflow
  steps:
    - name: requirements
      skill: docs-workflow-requirements
      description: Analyze documentation requirements

    - name: planning
      skill: docs-workflow-planning
      inputs: [requirements]

    # Add a custom step using a local skill
    - name: sme-review
      skill: my-review-skill
      description: Domain-specific review by SME checklist
      inputs: [writing]

    # Remove or skip steps by deleting them from the list
```

### Supplement with local skills

You can reference local standalone skills (from `.claude/skills/`) alongside plugin skills in your workflow YAML. Create a local skill in your docs repo:

```
.claude/skills/my-review-skill/SKILL.md
```

Then reference it by its standalone name in the step list:

```yaml
- name: sme-review
  skill: my-review-skill
  description: Run team-specific review checklist
  inputs: [writing]
```

Local standalone skills use short names (e.g., `my-review-skill`), while plugin skills use fully qualified names (e.g., `docs-workflow-writing`). Both can coexist in the same workflow YAML.

### Conditional steps

Use the `when` field to make steps run only when a CLI flag is passed:

```yaml
- name: create-jira
  skill: docs-workflow-create-jira
  when: create_jira_project
  inputs: [planning]
```

This step only runs when `--create-jira <PROJECT>` is passed to the orchestrator.

### Multiple workflow variants

Use `--workflow <name>` to maintain different workflows for different purposes:

```bash
# Uses .claude/docs-quick.yaml
/docs-orchestrator PROJ-123 --workflow quick

# Uses .claude/docs-full.yaml
/docs-orchestrator PROJ-123 --workflow full
```

## Using the docs orchestrator locally

Run the docs orchestrator from a Claude Code command prompt in the root of your documentation repository or from the chat panel in Agent mode in Cursor. The orchestrator reads a JIRA ticket, analyzes requirements, plans the documentation structure, writes modules, and runs technical and style reviews.

### Basic usage

To write files directly into your repo (update-in-place mode), run as follows:

```bash
/docs-orchestrator PROJ-123
```

In update-in-place mode, the orchestrator detects your repo's documentation framework (Antora, ccutil, etc.), creates a branch, writes files to the correct locations, and can commit and open a merge request.

### Grounding documentation in source code

When documenting a feature that lives in a source code repository, pass `--repo` to provide the code repository. The orchestrator clones the repo, indexes it using AST chunking and hybrid search, and retrieves relevant code snippets for each topic in the documentation plan. The writer then uses this evidence to ground its output in actual function signatures, class definitions, and configuration — rather than generating from the JIRA description alone.

```bash
/docs-orchestrator PROJ-123 --repo https://github.com/org/repo
```

The code-evidence step runs automatically when `--repo` is provided. It:

1. Clones the repository (or uses it if it's a local path)
2. Indexes the codebase using tree-sitter AST chunking
3. Extracts search queries from the documentation plan
4. Runs two-pass retrieval per query — source-scoped (function signatures, types) and unfiltered (READMEs, examples, docs)
5. Writes `artifacts/<ticket>/code-evidence/evidence.json` for the writer and `summary.md` for human review

Without `--repo`, the code-evidence step is skipped and the writer works from the JIRA ticket and documentation plan only.

!!! tip

    Code-evidence is most effective when the JIRA ticket has a detailed description. A well-described ticket combined with source code evidence produces documentation with significantly fewer technical review issues.

### Including PR context

If the feature has associated pull requests, pass their URLs to include the code changes in the requirements analysis:

```bash
/docs-orchestrator PROJ-123 --pr https://github.com/org/repo/pull/456
```

Multiple `--pr` flags can be passed. The requirements analyst will read the PR diff, comments, and description alongside the JIRA ticket.

### Other options

| Flag | Description |
|------|-------------|
| `--repo <url-or-path>` | Source code repository for code-evidence grounding |
| `--pr <url>` | PR/MR URL to include in requirements analysis (repeatable) |
| `--mkdocs` | Generate Material for MkDocs Markdown instead of AsciiDoc |
| `--repo-path <path>` | Write files to a specific repo path (e.g., an external clone) |
| `--create-jira <PROJECT>` | Create a linked JIRA ticket in the specified project |
| `--workflow <name>` | Use `.claude/docs-<name>.yaml` instead of the default workflow |

### Resuming a workflow

The orchestrator saves progress to `artifacts/<ticket>/workflow/docs-workflow_<ticket>.json`. If a run is interrupted or fails, start the orchestrator again with the same ticket and it will resume from where it left off:

```bash
/docs-orchestrator PROJ-123
```

Completed steps are skipped automatically. You can add flags on resume (e.g., add `--create-jira` to a run that didn't originally include it).

## Using the docs orchestrator in CI/CD

The docs orchestrator can run in GitHub Actions or GitLab CI using [Claude Code in the CLI](https://code.claude.com/docs/en/cli-reference). This lets you automate documentation workflows — for example, generating draft docs from a JIRA ticket when a PR is opened, or running style and technical reviews on documentation changes.

### Prerequisites

Your CI environment needs:

- **Claude Code** installed (`npm install -g @anthropic-ai/claude-code`)
- **API key** set as `ANTHROPIC_API_KEY` secret
- **JIRA token** set as `JIRA_API_TOKEN` secret (and `JIRA_EMAIL` for Atlassian Cloud)
- **Python 3** with required packages (see [Prerequisites](#prerequisites))
- The docs-tools plugin installed or available in the runner

### How it works

The CI pattern has two phases:

1. **Phase 1 — JIRA ready check**: The `docs-workflow-jira-ready` skill queries JIRA for tickets matching a JQL filter, excludes tickets that already have a workflow progress file or tracking label, and returns a JSON list of actionable ticket IDs.
2. **Phase 2 — Orchestrator loop**: For each ready ticket, run the `docs-orchestrator` skill to execute the full documentation workflow.

All invocations go through `claude -p` (headless mode) so the plugin system resolves script paths via `CLAUDE_PLUGIN_ROOT`. No local checkout of the tools repo is needed — only the plugin installed in Claude Code.

### GitHub Actions example

```yaml
name: Docs Workflow
on:
  schedule:
    - cron: '0 8 * * 1-5'  # Weekdays at 8am
  workflow_dispatch: {}

env:
  DOCS_JQL: "project=PROJ AND labels=docs-needed AND labels != docs-workflow-started"

jobs:
  check:
    runs-on: ubuntu-latest
    outputs:
      tickets: ${{ steps.check.outputs.tickets }}
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          npm install -g @anthropic-ai/claude-code
          python3 -m pip install PyGithub python-gitlab jira pyyaml ratelimit requests beautifulsoup4 html2text

      - name: Check for ready tickets
        id: check
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
        run: |
          RESULT=$(claude -p "Skill: docs-workflow-jira-ready, args: \"--jql '${{ env.DOCS_JQL }}' --add-label\"")
          echo "tickets=$(echo "$RESULT" | jq -c '.ready')" >> "$GITHUB_OUTPUT"

  run-workflow:
    needs: check
    if: needs.check.outputs.tickets != '[]'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        ticket: ${{ fromJson(needs.check.outputs.tickets) }}
      max-parallel: 2
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          npm install -g @anthropic-ai/claude-code
          python3 -m pip install python-pptx PyGithub python-gitlab jira pyyaml ratelimit requests beautifulsoup4 html2text

      - name: Run docs orchestrator
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          claude -p "Skill: docs-orchestrator, args: \"${{ matrix.ticket }} --draft\""

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: docs-${{ matrix.ticket }}
          path: artifacts/
```

This uses a matrix strategy to parallelize orchestrator runs across tickets. The `check` job queries JIRA and passes ready ticket IDs to `run-workflow` via `fromJson`.

### GitLab CI example

```yaml
docs-check-tickets:
  stage: docs
  image: node:20
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
    - when: manual
  before_script:
    - npm install -g @anthropic-ai/claude-code
    - apt-get update && apt-get install -y python3 python3-pip jq
    - python3 -m pip install PyGithub python-gitlab jira pyyaml ratelimit requests beautifulsoup4 html2text
  script:
    - |
      RESULT=$(claude -p "Skill: docs-workflow-jira-ready, args: \"--jql 'project=PROJ AND labels=docs-needed' --add-label\"")
      TICKETS=$(echo "$RESULT" | jq -r '.ready[]' 2>/dev/null || true)
      if [ -z "$TICKETS" ]; then
        echo "No tickets ready for docs workflow."
        exit 0
      fi
      for TICKET in $TICKETS; do
        echo "=== Starting workflow for $TICKET ==="
        claude -p "Skill: docs-orchestrator, args: \"$TICKET --draft\"" \
          2>&1 | tee -a .work/cron-runs/$(date +%Y%m%d-%H%M%S)-${TICKET}.log
      done
  artifacts:
    paths:
      - artifacts/
      - .work/cron-runs/
    expire_in: 1 week
```

Set `ANTHROPIC_API_KEY`, `JIRA_API_TOKEN`, `JIRA_EMAIL`, and any Git platform tokens as CI/CD variables (masked/protected).

### Tips for CI usage

- Use `--draft` to write output to `artifacts/` staging area instead of modifying repo files directly
- Use `--add-label` in the JIRA ready check to prevent re-processing tickets on the next run
- Use `--workflow` to select a CI-specific workflow variant (e.g., a lighter review-only pipeline)
- Collect the `artifacts/` directory as an artifact for downstream review or PR creation
- The orchestrator writes a progress JSON file, so failed runs can be resumed in a subsequent job if the artifact is restored
- For PR-triggered workflows, pass `--pr $CI_MERGE_REQUEST_URL` or `--pr $GITHUB_PR_URL` to include the PR context in requirements analysis
