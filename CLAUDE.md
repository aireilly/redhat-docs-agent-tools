# Red Hat Docs Agent Tools

A collection of plugins, skills, and agent tools for Red Hat documentation workflows.

## Repository structure

```bash
.claude-plugin/marketplace.json  # Registry of all plugins (must stay in sync with plugin.json files)
plugins/<name>/
  .claude-plugin/plugin.json   # Plugin metadata (name, version, description)
  commands/<command>.md        # Command definitions with frontmatter
  skills/<skill>.md            # Skill definitions
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
| `Skill: plugin:skill` | Loading full skill knowledge — rules, checklists, domain expertise the LLM applies | `docs-tools:rh-ssg-formatting`, `docs-tools:ibm-sg-punctuation` |

## Contributing rules

- Use kebab-case for plugin and command names
- Each plugin must have a `.claude-plugin/plugin.json` with name, version, description
- Bump version in plugin.json when making changes
- When adding a new plugin or updating an existing plugin's name, description, or version, also update `.claude-plugin/marketplace.json` at the repo root to keep it in sync
- Auto-generated files (plugins.md, docs/plugins.md, docs/plugins/, docs/install/) are gitignored and built by CI only. Run `make update` locally to preview them
- Use the hello-world plugin as a reference implementation
- Use `.work/` directory for temporary files (gitignored)
- When referencing Python in install steps or prerequisites, always refer to `python3`. Use `python3 -m pip install` instead of `pip install`

## Cursor users

For Cursor-specific instructions (including workspace-relative script paths), see [AGENTS.md](AGENTS.md) and [docs/contribute/cursor-workflows.md](docs/contribute/cursor-workflows.md).
