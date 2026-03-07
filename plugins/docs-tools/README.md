# docs-tools

Documentation review, writing, and workflow tools for Red Hat AsciiDoc and Markdown documentation.

## Commands

| Command | Description |
|---------|-------------|
| `/docs-tools:docs-review --local` | Multi-agent review of local branch changes with confidence scoring |
| `/docs-tools:docs-review --pr <url>` | Multi-agent review of a GitHub PR or GitLab MR |
| `/docs-tools:docs-review --pr <url> --post-comments` | Review and post inline comments to PR/MR |
| `/docs-tools:docs-review --action-comments [url]` | Interactively action unresolved PR/MR review comments (auto-detects PR from branch) |
| `/docs-tools:docs-workflow` | Run the multi-stage documentation workflow |

## Agents

| Agent | Description |
|-------|-------------|
| `docs-reviewer` | Documentation reviewer using Vale linting and style guide checks |
| `docs-writer` | Technical writer for AsciiDoc documentation |
| `docs-planner` | Documentation architect for planning and analysis |
| `requirements-analyst` | Requirements analyst for JIRA issues, PRs, and specs |

## Skills

### Review Skills

| Skill | Focus |
|-------|-------|
| `docs-review-content-quality` | Logical flow, user journey, scannability, conciseness |
| `docs-review-modular-docs` | Module types, anchor IDs, assemblies (.adoc) |

### IBM Style Guide Skills

| Skill | Focus |
|-------|-------|
| `ibm-sg-audience-and-medium` | Accessibility, global audiences, tone |
| `ibm-sg-language-and-grammar` | Abbreviations, capitalization, active voice, inclusive language |
| `ibm-sg-legal-information` | Claims, trademarks, copyright, personal info |
| `ibm-sg-numbers-and-measurement` | Numerals, formatting, currency, dates, units |
| `ibm-sg-punctuation` | Colons, commas, dashes, hyphens, quotes |
| `ibm-sg-references` | Citations, product names, versions |
| `ibm-sg-structure-and-format` | Headings, lists, procedures, tables, emphasis |
| `ibm-sg-technical-elements` | Code, commands, syntax, files, UI elements |

### Red Hat Supplementary Style Guide Skills

| Skill | Focus |
|-------|-------|
| `rh-ssg-accessibility` | Colors, images, links, tables, WCAG |
| `rh-ssg-formatting` | Code blocks, user values, titles, product names |
| `rh-ssg-grammar-and-language` | Conscious language, contractions, minimalism |
| `rh-ssg-gui-and-links` | Screenshots, UI elements, links, cross-references |
| `rh-ssg-legal-and-support` | Cost refs, future releases, Developer/Technology Preview |
| `rh-ssg-release-notes` | Release note style, tenses, Jira refs |
| `rh-ssg-structure` | Admonitions, lead-ins, prerequisites, short descriptions |
| `rh-ssg-technical-examples` | Root privileges, YAML, IPs/MACs, syntax highlighting |

## Prerequisites

### System dependencies

```bash
# RHEL/Fedora
sudo dnf install python3 jq curl
```

| Dependency | Purpose |
|------------|---------|
| Python 3 | Git review API, JIRA ticket graph, workflow scripts |
| jq | Workflow state management |
| curl | API calls with tokens |
| Vale | Style linting (optional, used by docs-reviewer agent) |

### Python packages

```bash
pip install PyGithub python-gitlab jira pyyaml ratelimit requests beautifulsoup4 html2text
```

For Google Docs reading (`docs-read-gdoc` skill), also install:

```bash
pip install google-api-python-client google-auth-httplib2
```

### Tokens

Create an `~/.env` file with your tokens:

```bash
JIRA_AUTH_TOKEN=your_jira_token
JIRA_URL=https://issues.redhat.com          # optional: override default JIRA instance
GITHUB_TOKEN=your_github_pat                # repo scope for private, public_repo for public
GITLAB_TOKEN=your_gitlab_pat                # api scope
```

Source the file in your `~/.bashrc` or `~/.zshrc`:

```bash
if [ -f ~/.env ]; then
    set -a
    source ~/.env
    set +a
fi
```

Restart your terminal and Claude Code for changes to take effect.

### Related plugin marketplaces

The `requirements-analyst` agent references skills from these companion marketplaces:

| Marketplace | Skills used | Install |
|-------------|-------------|---------|
| pr-plugins | `jira-reader`, `git-pr-reader` | `/plugin install pr-plugins@redhat-docs-marketplace` |
| docs-rh-plugins | `article-extractor`, `redhat-docs-toc` | `/plugin install docs-rh-plugins@redhat-docs-marketplace` |

Add the marketplace first:

```bash
/plugin marketplace add https://github.com/redhat-documentation/redhat-docs-agent-tools.git
```

## Installation

```
/plugin install docs-tools@redhat-docs-agent-tools
```
