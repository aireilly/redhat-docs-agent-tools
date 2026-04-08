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

Use bare skill names for portability. Qualified names (`plugin:skill`) are only needed to disambiguate when two plugins have the same skill name:

- `jira-reader` (not `docs-tools:jira-reader`)
- `rh-ssg-formatting` (not `docs-tools:rh-ssg-formatting`)
- `lint-with-vale` (not `vale-tools:lint-with-vale`)

## Calling scripts from skills and commands

### From within a skill (internal calls)

The runtime working directory is the **project root**, not the skill directory. Bare relative paths like `scripts/foo.py` will fail with "No such file or directory". Always use an absolute-style path:

In **Claude Code**, two substitution variables are available in skill content:

- **`${CLAUDE_SKILL_DIR}`** — the directory containing the skill's `SKILL.md`. Use for scripts bundled with the same skill.
- **`${CLAUDE_PLUGIN_ROOT}`** — the plugin's installation directory. Use for cross-skill calls.

```bash
# Same-skill call
python3 ${CLAUDE_SKILL_DIR}/scripts/git_pr_reader.py info <url> --json

# Cross-skill calls
ruby ${CLAUDE_PLUGIN_ROOT}/skills/dita-callouts/scripts/callouts.rb "$file"
bash ${CLAUDE_PLUGIN_ROOT}/skills/dita-includes/scripts/find_includes.sh "$file"
```

In **Cursor**, use paths relative to the repository root (workspace):

```bash
python3 plugins/docs-tools/skills/git-pr-reader/scripts/git_pr_reader.py info <url> --json
ruby plugins/dita-tools/skills/dita-callouts/scripts/callouts.rb "$file"
bash plugins/dita-tools/skills/dita-includes/scripts/find_includes.sh "$file"
```

### From other commands and agents (cross-skill calls)

The same path conventions apply. Adjust the `skills/<skill>/scripts/...` segment to match the skill that owns the script.

### Knowledge-only skills

Use `Skill:` pseudocode only for pure knowledge or checklist skills that have no backing script:

```bash
Skill: rh-ssg-formatting, args: "review path/to/file.adoc"
```

Do not use old slash-command syntax (for example, `/jira-reader --issue PROJ-123`).

### When to use each approach

| Approach | When to use | Examples |
| --- | --- | --- |
| `${CLAUDE_SKILL_DIR}/scripts/...` | Same-skill script calls in Claude Code | `${CLAUDE_SKILL_DIR}/scripts/git_pr_reader.py` |
| `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/...` | Cross-skill script calls in Claude Code | `${CLAUDE_PLUGIN_ROOT}/skills/dita-callouts/scripts/callouts.rb` |
| `plugins/<plugin>/skills/<skill>/scripts/...` | All script calls in Cursor (internal and cross-skill) | `plugins/docs-tools/skills/git-pr-reader/scripts/git_pr_reader.py` |
| `Skill: skill-name` | Loading full skill knowledge — rules, checklists, domain expertise the model applies | `rh-ssg-formatting`, `ibm-sg-punctuation` |

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
