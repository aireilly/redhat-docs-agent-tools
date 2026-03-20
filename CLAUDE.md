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
- Each plugin must have a `.claude-plugin/plugin.json` (only `name` is required; `version` and `description` are recommended)
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
| Skill authoring best practices | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices |
| Skills overview and structure | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview |
| Skills in Claude Code | https://code.claude.com/docs/en/skills |
| Plugin schema and reference | https://code.claude.com/docs/en/plugins-reference |
| Plugin creation guide | https://code.claude.com/docs/en/plugins |
| Subagents | https://code.claude.com/docs/en/sub-agents |
| Hooks | https://code.claude.com/docs/en/hooks |
| Tools reference | https://code.claude.com/docs/en/tools-reference |
| CLAUDE.md and memory | https://code.claude.com/docs/en/memory |
| Plugin marketplaces | https://code.claude.com/docs/en/plugin-marketplaces |

### Skill files

New skills must use the directory-based format: `skills/<skill-name>/SKILL.md`. The `commands/<name>.md` format is legacy and should not be used for new work. Existing commands continue to work.

Frontmatter validation rules:

- `name`: optional (defaults to directory name when omitted), but when provided: max 64 characters, lowercase letters + numbers + hyphens only, no XML tags, cannot contain reserved words "anthropic" or "claude"
- `description`: strongly recommended (falls back to first paragraph of content if omitted), max 1024 characters, no XML tags. Must describe what the skill does AND when to use it. Write in third person ("Processes files..." not "I can help you...")
- `disable-model-invocation`: set `true` for skills with side effects (deploy, send, commit) that users should trigger manually
- `user-invocable`: set `false` for background knowledge skills users should not invoke directly
- Other valid frontmatter fields: `argument-hint`, `allowed-tools`, `model`, `context`, `agent`, `hooks`

Content guidelines:

- Keep SKILL.md body under 500 lines — move detailed content to separate reference files
- Only add context Claude does not already have — challenge each paragraph's token cost
- Reference files should be one level deep from SKILL.md (no nested chains of references)
- Use forward slashes in all file paths, never backslashes
- Provide a default tool/approach rather than listing many options
- No time-sensitive information (no "before August 2025" conditionals)
- Use consistent terminology throughout (pick one term, use it everywhere)
- For complex workflows, provide a checklist Claude can track progress against
- Implement feedback loops (run validator, fix errors, repeat) for quality-critical tasks

String substitution variables available in skill content: `$ARGUMENTS` (all args), `$ARGUMENTS[N]` or `$N` (positional), `${CLAUDE_SESSION_ID}`, `${CLAUDE_SKILL_DIR}`. Use `context: fork` frontmatter to run a skill in an isolated subagent (no conversation history). Use `!`command`` syntax to inject shell output into skill content at invocation time.

### Agent files (subagents)

Required frontmatter: `name` (lowercase + hyphens) and `description` (when Claude should delegate).

Optional frontmatter fields: `tools`, `disallowedTools`, `model` (`sonnet`/`opus`/`haiku`/`inherit`/full model ID), `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`

- The markdown body becomes the agent's system prompt — agents do NOT receive the full Claude Code system prompt
- Plugin agents cannot use `hooks`, `mcpServers`, or `permissionMode` frontmatter fields (these are ignored for security)
- Subagents cannot spawn other subagents

### Hooks

Valid hook event names (case-sensitive): `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStart`, `SubagentStop`, `StopFailure`, `Notification`, `TeammateIdle`, `TaskCompleted`, `ConfigChange`, `InstructionsLoaded`, `WorktreeCreate`, `WorktreeRemove`, `PreCompact`, `PostCompact`, `Elicitation`, `ElicitationResult`, `SessionEnd`

Hook types: `command`, `http`, `prompt`, `agent`

Exit codes for command hooks: `0` = success (parse JSON stdout), `2` = blocking error (prevents action, stderr as feedback), other = non-blocking error

- Use `${CLAUDE_PLUGIN_ROOT}` for all script paths in plugin hooks
- Scripts must be executable (`chmod +x`)
- Matchers use regex against tool names (e.g., `"Write|Edit"`, `"Bash"`, `"mcp__.*"`)

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
└── settings.json            # Default settings (only `agent` key supported)
```

`plugin.json` required field: `name` (kebab-case, no spaces). Optional: `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, plus component path overrides.

Environment variables available in skill content, hook commands, MCP/LSP configs:
- `${CLAUDE_PLUGIN_ROOT}` — absolute path to plugin installation directory (changes on update)
- `${CLAUDE_PLUGIN_DATA}` — persistent directory for plugin state (survives updates)

All paths in plugin.json must be relative and start with `./`. Plugins cannot reference files outside their directory (no `../`).

### marketplace.json

Required fields: `name` (kebab-case), `owner` (object with `name`), `plugins` (array).

Each plugin entry requires: `name` (kebab-case) and `source` (relative path starting with `./`, or object with `source` type).

Source types: relative path, `github` (`repo` field), `url` (git URL), `git-subdir` (`url` + `path`), `npm` (`package`), `pip` (`package`).

Version management: use semver (`MAJOR.MINOR.PATCH`). If version is unchanged, users will not receive updates due to caching. Set version in either `plugin.json` or `marketplace.json`, not both (plugin.json wins silently).
