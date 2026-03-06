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
| `/docs-tools:docs-technical-review` | Run the two-phase technical review workflow |
| `/docs-tools:docs-upstream-pr-sync` | Review upstream PRs with documentation labels |
| `/docs-tools:docs-summarize-claude-work` | Summarize Claude-assisted documentation work |

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

### Other Skills

| Skill | Focus |
|-------|-------|
| `docs-technical-review-validate` | Validate documentation against code repositories |
| `docs-technical-review-apply` | Interactively apply fixes from technical review |

## Installation

```
/install github:redhat-documentation/redhat-docs-agent-tools/plugins/docs-tools
```
