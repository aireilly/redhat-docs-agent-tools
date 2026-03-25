# docs-tools

!!! tip

    Always run Claude Code from a terminal in the root of the documentation repository you are working on. The docs-tools commands and agents operate on the current working directory, they read local files, check git branches, and write output relative to the repo root.

## Prerequisites

- Install the [Red Hat Docs Agent Tools marketplace](https://redhat-documentation.github.io/redhat-docs-agent-tools/install/)

- [Install GitHub CLI (`gh`)](https://cli.github.com/)

    ```bash
    gh auth login
    ```

- Install system dependencies

    ```bash
    # RHEL/Fedora
    sudo dnf install python3 jq curl
    ```

- [Install gcloud CLI](https://cloud.google.com/sdk/docs/install)

    ```bash
    gcloud auth login --enable-gdrive-access
    ```

- Install Python packages

    ```bash
    python3 -m pip install python-pptx PyGithub python-gitlab jira pyyaml ratelimit requests beautifulsoup4 html2text pip-system-certs
    ```

    The `python-pptx` package is only required for Google Slides conversion. Google Docs and Sheets conversion has no extra dependencies.

- Create an `~/.env` file with your tokens:

    ```bash
    JIRA_AUTH_TOKEN=your_jira_api_token
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

The docs orchestrator (`/docs-tools:docs-orchestrator`) runs a YAML-defined step list. You can customize it per-repo without modifying the plugin.

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
      skill: docs-tools:docs-workflow-requirements
      description: Analyze documentation requirements

    - name: planning
      skill: docs-tools:docs-workflow-planning
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

Local standalone skills use short names (e.g., `my-review-skill`), while plugin skills use fully qualified names (e.g., `docs-tools:docs-workflow-writing`). Both can coexist in the same workflow YAML.

### Conditional steps

Use the `when` field to make steps run only when a CLI flag is passed:

```yaml
- name: create-jira
  skill: docs-tools:docs-workflow-create-jira
  when: create_jira_project
  inputs: [planning]
```

This step only runs when `--create-jira <PROJECT>` is passed to the orchestrator.

### Multiple workflow variants

Use `--workflow <name>` to maintain different workflows for different purposes:

```bash
# Uses .claude/docs-quick.yaml
/docs-tools:docs-orchestrator PROJ-123 --workflow quick

# Uses .claude/docs-full.yaml
/docs-tools:docs-orchestrator PROJ-123 --workflow full
```

## Using the docs orchestrator in CI/CD

The docs orchestrator can run in GitHub Actions or GitLab CI using [Claude Code in the CLI](https://code.claude.com/docs/en/cli-reference). This lets you automate documentation workflows — for example, generating draft docs from a JIRA ticket when a PR is opened, or running style and technical reviews on documentation changes.

### Prerequisites

Your CI environment needs:

- **Claude Code** installed (`npm install -g @anthropic-ai/claude-code`)
- **API key** set as `ANTHROPIC_API_KEY` secret
- **JIRA token** set as `JIRA_AUTH_TOKEN` secret (and `JIRA_EMAIL` for Atlassian Cloud)
- **Python 3** with required packages (see [Prerequisites](#prerequisites))
- The docs-tools plugin installed or available in the runner

### How it works

The CI pattern has two phases:

1. **Phase 1 — JIRA ready check**: The `docs-tools:docs-workflow-jira-ready` skill queries JIRA for tickets matching a JQL filter, excludes tickets that already have a workflow progress file or tracking label, and returns a JSON list of actionable ticket IDs.
2. **Phase 2 — Orchestrator loop**: For each ready ticket, run the `docs-tools:docs-orchestrator` skill to execute the full documentation workflow.

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
          JIRA_AUTH_TOKEN: ${{ secrets.JIRA_AUTH_TOKEN }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
        run: |
          RESULT=$(claude -p "Skill: docs-tools:docs-workflow-jira-ready, args: \"--jql '${{ env.DOCS_JQL }}' --add-label\"")
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
          JIRA_AUTH_TOKEN: ${{ secrets.JIRA_AUTH_TOKEN }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          claude -p "Skill: docs-tools:docs-orchestrator, args: \"${{ matrix.ticket }} --draft\""

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: docs-${{ matrix.ticket }}
          path: .claude/docs/
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
      RESULT=$(claude -p "Skill: docs-tools:docs-workflow-jira-ready, args: \"--jql 'project=PROJ AND labels=docs-needed' --add-label\"")
      TICKETS=$(echo "$RESULT" | jq -r '.ready[]' 2>/dev/null || true)
      if [ -z "$TICKETS" ]; then
        echo "No tickets ready for docs workflow."
        exit 0
      fi
      for TICKET in $TICKETS; do
        echo "=== Starting workflow for $TICKET ==="
        claude -p "Skill: docs-tools:docs-orchestrator, args: \"$TICKET --draft\"" \
          2>&1 | tee -a .work/cron-runs/$(date +%Y%m%d-%H%M%S)-${TICKET}.log
      done
  artifacts:
    paths:
      - .claude/docs/
      - .work/cron-runs/
    expire_in: 1 week
```

Set `ANTHROPIC_API_KEY`, `JIRA_AUTH_TOKEN`, `JIRA_EMAIL`, and any Git platform tokens as CI/CD variables (masked/protected).

### Tips for CI usage

- Use `--draft` to write output to `.claude/docs/` staging area instead of modifying repo files directly
- Use `--add-label` in the JIRA ready check to prevent re-processing tickets on the next run
- Use `--workflow` to select a CI-specific workflow variant (e.g., a lighter review-only pipeline)
- Collect the `.claude/docs/` directory as an artifact for downstream review or PR creation
- The orchestrator writes a progress JSON file, so failed runs can be resumed in a subsequent job if the artifact is restored
- For PR-triggered workflows, pass `--pr $CI_MERGE_REQUEST_URL` or `--pr $GITHUB_PR_URL` to include the PR context in requirements analysis

## Commit-driven workflow

The docs orchestrator also supports triggering documentation workflows based on new commits to a code repository. This is useful when the docs repo is separate from the code repo and you want to automatically detect code changes that need documentation updates.

### How it works

1. **Gate check**: The `docs-tools:docs-workflow-commits-ready` skill polls a code repository for new commits since the last processed marker
2. **Commit analysis**: The `commit-analyst` agent scrapes commit diffs, extracts change signals (new APIs, config changes, breaking changes), and grades documentation impact
3. **Short-circuit**: If no doc impact is detected (`DOC_IMPACT: None`), the workflow completes immediately — no requirements analysis or writing
4. **Full pipeline**: If doc impact exists, the workflow continues through requirements, planning, writing, and reviews
5. **PR creation** (optional): When `--create-pr` is passed, a PR/MR is created in the docs repo with the documentation changes

### Manual usage

```bash
# Analyze specific commits
/docs-tools:docs-orchestrator my-service/a1b2c3d-e4f5g6h \
    --commits https://github.com/org/code-repo sha1,sha2,sha3

# With automatic PR creation
/docs-tools:docs-orchestrator my-service/a1b2c3d-e4f5g6h \
    --commits https://github.com/org/code-repo sha1,sha2,sha3 \
    --create-pr
```

### CI/CD integration (scheduled poll)

The commit-driven workflow uses a two-phase CI pattern similar to the JIRA workflow:

1. **Phase 1 — Commits ready check**: Poll the code repo for new commits since the last marker
2. **Phase 2 — Orchestrator**: If commits are ready, run the full workflow with `--create-pr`

#### GitLab CI example

```yaml
docs-commit-check:
  stage: docs
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
  script:
    - |
      RESULT=$(claude -p "Skill: docs-tools:docs-workflow-commits-ready, \
        args: \"--repo https://github.com/org/code-repo --branch main\"")
      READY=$(echo "$RESULT" | jq -r '.ready')
      if [ "$READY" != "true" ]; then
        echo "No doc-impacting commits found."
        exit 0
      fi
      IDENTIFIER=$(echo "$RESULT" | jq -r '.batch.identifier')
      COMMITS=$(echo "$RESULT" | jq -r '.batch.commits | join(",")')
      claude -p "Skill: docs-tools:docs-orchestrator, \
        args: \"$IDENTIFIER --commits https://github.com/org/code-repo $COMMITS --create-pr\""
```

#### GitHub Actions example

```yaml
name: Docs from Commits
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  docs-from-commits:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          npm install -g @anthropic-ai/claude-code
          python3 -m pip install PyGithub python-gitlab jira pyyaml ratelimit requests beautifulsoup4 html2text

      - name: Check and process commits
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          RESULT=$(claude -p "Skill: docs-tools:docs-workflow-commits-ready, \
            args: \"--repo https://github.com/org/code-repo --branch main\"")
          READY=$(echo "$RESULT" | jq -r '.ready')
          if [ "$READY" != "true" ]; then
            echo "No doc-impacting commits found."
            exit 0
          fi
          IDENTIFIER=$(echo "$RESULT" | jq -r '.batch.identifier')
          COMMITS=$(echo "$RESULT" | jq -r '.batch.commits | join(",")')
          claude -p "Skill: docs-tools:docs-orchestrator, \
            args: \"$IDENTIFIER --commits https://github.com/org/code-repo $COMMITS --create-pr\""
```

### Marker files

The commit-driven workflow tracks which commits have been processed using marker files at `.claude/docs/.commit-markers/<repo-slug>.json`. The orchestrator updates the marker on workflow completion, so failed workflows don't skip commits on retry.

> **Tip**: In CI/CD pipelines, persist the `.commit-markers/` directory between runs using your platform's cache mechanism (GitHub Actions `actions/cache`, GitLab CI `cache:` directive) or by committing marker updates back to the repo. Without persistence, each run treats all recent commits as new.
