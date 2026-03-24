# Red Hat Docs Agent Tools

A collection of plugins, skills, and agent tools for Red Hat documentation workflows. This file defines the shared project conventions for all AI coding agents. For Claude Code-specific instructions, see [CLAUDE.md](CLAUDE.md). For additional Cursor workflows, see [docs/contribute/cursor-workflows.md](docs/contribute/cursor-workflows.md).

## Repository structure

```bash
.claude-plugin/marketplace.json  # Registry of all plugins (must stay in sync with plugin.json files)
plugins/<name>/
  .claude-plugin/plugin.json   # Plugin metadata (name, version, description)
  commands/<command>.md        # Command definitions with frontmatter
  skills/<skill>/SKILL.md      # Skill definitions (flat skills/*.md also supported)
  agents/<agent>.md            # Agent definitions
  README.md                    # Plugin documentation
```

## Docs site development commands

- `make update` — Regenerate plugin catalog pages and install docs under `docs/`
- `make serve` — Start local Zensical dev server
- `make build` — Build the Zensical site

## Skill naming convention

Always use fully qualified `plugin:skill` names in agent instructions, Skill invocations, inline text references, and cross-references between skills:

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

In **Cursor**, use paths relative to the repository root (workspace) so commands work from the project directory:

```bash
python3 plugins/docs-tools/skills/git-pr-reader/scripts/git_pr_reader.py info <url> --json
ruby plugins/dita-tools/skills/dita-callouts/scripts/callouts.rb "$file"
bash plugins/dita-tools/skills/dita-includes/scripts/find_includes.sh "$file"
```

Adjust the `plugins/<plugin>/skills/<skill>/scripts/...` segment to match the skill that owns the script.

In **Claude Code**, use `${CLAUDE_PLUGIN_ROOT}` instead of the workspace-relative path. See [CLAUDE.md](CLAUDE.md) for examples.

### Knowledge-only skills

Use `Skill:` pseudocode only for pure knowledge or checklist skills that have no backing script:

```bash
Skill: docs-tools:rh-ssg-formatting, args: "review path/to/file.adoc"
```

Do not use old slash-command syntax (for example, `/jira-reader --issue PROJ-123`).

### When to use each approach

| Approach | When to use | Examples |
| --- | --- | --- |
| `python3 scripts/...` | Calling a co-located script from within the same skill | `scripts/git_pr_reader.py`, `scripts/callouts.rb` |
| Path from repo root under `plugins/.../scripts/` | Cross-skill or cross-command script calls in Cursor | Same scripts as above, with full path from workspace root |
| `python3 ${CLAUDE_PLUGIN_ROOT}/...` | Cross-skill or cross-command script calls in Claude Code | `${CLAUDE_PLUGIN_ROOT}/skills/git-pr-reader/scripts/git_pr_reader.py` |
| `Skill: plugin:skill` | Loading full skill knowledge — rules, checklists, domain expertise the model applies | `docs-tools:rh-ssg-formatting`, `docs-tools:ibm-sg-punctuation` |

## Contributing rules

- Use kebab-case for plugin and command names
- Each plugin must have a `.claude-plugin/plugin.json` with name, version, description
- Bump version in `plugin.json` when making changes
- When adding a new plugin or updating an existing plugin's name, description, or version, also update `.claude-plugin/marketplace.json` at the repo root to keep it in sync
- Auto-generated files (`docs/plugins.md`, `docs/plugins/`, `docs/install/`) are gitignored and built by CI. Run `make update` locally to preview them
- Use the `hello-world` plugin as a reference implementation
- Use `.work/` directory for temporary files (gitignored)
- When referencing Python in install steps or prerequisites, always refer to `python3`. Use `python3 -m pip install` instead of `pip install`

## Further reading

- [CLAUDE.md](CLAUDE.md) — Claude Code-specific conventions
- [CONTRIBUTING.md](CONTRIBUTING.md) — Full contributor guide, including a section for Cursor users
- [docs/contribute/cursor-workflows.md](docs/contribute/cursor-workflows.md) — Cursor workflows, testing, and limitations relative to Claude Code
