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

In agent files, use the `Skill:` pseudocode format for invocation examples:
```
Skill: docs-tools:jira-reader, args: "PROJ-123"
```

Do NOT use old slash-command syntax (e.g., `/jira-reader --issue PROJ-123`).

## Contributing rules

- Use kebab-case for plugin and command names
- Each plugin must have a `.claude-plugin/plugin.json` with name, version, description
- Bump version in plugin.json when making changes
- When adding a new plugin or updating an existing plugin's name, description, or version, also update `.claude-plugin/marketplace.json` at the repo root to keep it in sync
- Auto-generated files (plugins.md, docs/plugins.md, docs/plugins/, docs/install/) are gitignored and built by CI only. Run `make update` locally to preview them
- Use the hello-world plugin as a reference implementation
- Use `.work/` directory for temporary files (gitignored)
- When referencing Python in install steps or prerequisites, always refer to `python3`. Use `python3 -m pip install` instead of `pip install`
