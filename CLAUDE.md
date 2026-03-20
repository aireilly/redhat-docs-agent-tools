# Red Hat Docs Agent Tools

A collection of plugins, skills, and agent tools for Red Hat documentation workflows.

## Repository structure

```bash
.claude-plugin/marketplace.json  # Registry of all plugins (must stay in sync with plugin.json files)
plugins/<name>/
  .claude-plugin/plugin.json   # Plugin metadata (name is required; version, description optional)
  skills/<skill-name>/SKILL.md # Skill definitions (new standard)
  agents/<agent-name>.md       # Subagent definitions
  hooks/hooks.json             # Hook configurations
  commands/<command>.md        # Legacy — use skills/ for new work
  README.md                    # Plugin documentation
```

## Docs site development commands

- `make update` - Regenerate plugins.md and docs pages from plugin metadata
- `make serve` - Start local Zensical dev server
- `make build` - Build the Zensical site

## Skill naming convention

Always use fully qualified `plugin:skill` names when referencing skills anywhere — agent frontmatter, Skill tool invocations, inline text references, and cross-references between skills:

- `docs-tools:jira-reader` (not `jira-reader`)
- `docs-tools:rh-ssg-formatting` (not `rh-ssg-formatting`)
- `vale-tools:lint-with-vale` (not `vale`)

## Calling scripts from skills and commands

### From within a skill (internal calls)

When a skill's own Markdown calls its co-located script, use a relative path from the skill directory:

```bash
python3 scripts/git_pr_reader.py info <url> --json
ruby scripts/callouts.rb "$file"
bash scripts/find_includes.sh "$file"
```

### From other commands and agents (cross-skill calls)

When a command or agent calls a script that belongs to a different skill, use `${CLAUDE_PLUGIN_ROOT}`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py info <url> --json
ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-callouts/scripts/callouts.rb "$file"
bash ${CLAUDE_PLUGIN_ROOT}/skills/dita-includes/scripts/find_includes.sh "$file"
```

### Knowledge-only skills

Use `Skill:` pseudocode only for pure knowledge/checklist skills that have no backing script:

```bash
Skill: docs-tools:rh-ssg-formatting, args: "review path/to/file.adoc"
```

Do NOT use old slash-command syntax (e.g., `/jira-reader --issue PROJ-123`).

### When to use each approach

| Approach | When to use | Examples |
|---|---|---|
| `python3 scripts/...` | Calling a co-located script from within the same skill | `scripts/git_pr_reader.py`, `scripts/callouts.rb` |
| `python3 ${CLAUDE_PLUGIN_ROOT}/...` | Cross-skill/command script calls | `git_pr_reader.py info`, `jira_reader.py`, `callouts.rb` |
| `Skill: plugin:skill` | Loading full skill knowledge — rules, checklists, domain expertise the LLM applies | `rh-ssg-formatting`, `ibm-sg-punctuation`, review skills |

## Contributing rules

- Use kebab-case for plugin and command names
- Each plugin must have a `.claude-plugin/plugin.json`
- Bump version in plugin.json when making changes
- When adding a new plugin or updating an existing plugin's name, description, or version, also update `.claude-plugin/marketplace.json` at the repo root to keep it in sync
- Auto-generated files (plugins.md, docs/plugins.md, docs/plugins/, docs/install/) are gitignored and built by CI only. Run `make update` locally to preview them
- Use the hello-world plugin as a reference implementation
- Use `.work/` directory for temporary files (gitignored)
- When referencing Python in install steps or prerequisites, always refer to `python3`. Use `python3 -m pip install` instead of `pip install`

## Authoring skills, agents, and plugins — Anthropic documentation compliance

When creating or modifying skills, agents, hooks, or plugin components, follow the official Anthropic documentation. Do NOT rely on training data for schemas, frontmatter fields, or best practices — use WebFetch to consult the canonical docs listed below before generating any component.

### Canonical documentation references

Before creating any component, consult the relevant page:

| Component | Documentation |
|---|---|
| Skill authoring best practices | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md |
| Skills overview and structure | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview.md |
| Skills in Claude Code | https://code.claude.com/docs/en/skills.md |
| Plugin schema and reference | https://code.claude.com/docs/en/plugins-reference.md |
| Plugin creation guide | https://code.claude.com/docs/en/plugins.md |
| Subagents | https://code.claude.com/docs/en/sub-agents.md |
| Hooks | https://code.claude.com/docs/en/hooks.md |
| Tools reference | https://code.claude.com/docs/en/tools-reference.md |
| CLAUDE.md and memory | https://code.claude.com/docs/en/memory.md |
| Plugin marketplaces | https://code.claude.com/docs/en/plugin-marketplaces.md |

### Skill files

New skills must use the directory-based format: `skills/<skill-name>/SKILL.md`. The `commands/<name>.md` format is legacy and should not be used for new work. Existing commands continue to work.

For frontmatter fields, content guidelines, string substitution variables, and best practices, consult the canonical docs:
- https://code.claude.com/docs/en/skills.md
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview.md
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md

### Agent files (subagents)

For the full subagent schema (required/optional frontmatter fields), consult https://code.claude.com/docs/en/sub-agents.md

Key behavioral constraints:
- The markdown body becomes the agent's system prompt — agents do NOT receive the full Claude Code system prompt
- Plugin agents cannot use `hooks`, `mcpServers`, or `permissionMode` frontmatter fields (these are ignored for security)
- Subagents cannot spawn other subagents

### Hooks

For valid event names, hook types, exit codes, and matchers, consult https://code.claude.com/docs/en/hooks.md

Project conventions:
- Use `${CLAUDE_PLUGIN_ROOT}` for all script paths in plugin hooks
- Scripts must be executable (`chmod +x`)

### Plugin structure

Required directory layout — components at plugin root, NOT inside `.claude-plugin/`:

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Only manifest here
├── commands/                # At root level
├── skills/                  # At root level (skill-name/SKILL.md)
├── agents/                  # At root level
├── hooks/
│   └── hooks.json           # At root level
├── .mcp.json                # MCP server definitions
├── .lsp.json                # LSP server configurations
└── settings.json            # Default settings
```

For `plugin.json` schema (required/optional fields, component path overrides), consult https://code.claude.com/docs/en/plugins-reference.md

All paths in plugin.json must be relative and start with `./`. Plugins cannot reference files outside their directory (no `../`).

### marketplace.json

For the marketplace schema (required fields, plugin entry format, source types), consult https://code.claude.com/docs/en/plugin-marketplaces.md

Version management: use semver (`MAJOR.MINOR.PATCH`). If version is unchanged, users will not receive updates due to caching. Set version in either `plugin.json` or `marketplace.json`, not both (plugin.json wins silently).
