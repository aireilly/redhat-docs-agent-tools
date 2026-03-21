---
icon: lucide/monitor
---

# Cursor workflows

The plugin format and marketplace in this repository target **Claude Code**. Cursor does not provide the same marketplace or slash-command surface, but you can author and review the same Markdown skills, commands, agents, and reference material.

## How Cursor fits this repository

1. **Project instructions** — Cursor loads [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) and rules under [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules), mirroring [CLAUDE.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CLAUDE.md) conventions.
1. **Skills** — Skill files live at `plugins/<plugin>/skills/` as plain Markdown. Point the agent at a path or use fully qualified names such as `docs-tools:jira-reader`.
1. **Commands** — Claude Code exposes commands like `hello-world:greet`. Cursor has no slash-command system. Treat command files as prompts: open the Markdown and follow the **Implementation** and **Examples** sections.
1. **Agents** — Agent definitions under `plugins/<plugin>/agents/` are Markdown personas. Use them as system instructions or project rules.
1. **Installation** — Clone the repository. All plugin sources are available on disk under `plugins/`.

## Contributing from Cursor

Follow [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md). Branch, edit Markdown under the right plugin, bump `plugin.json`, sync [`.claude-plugin/marketplace.json`](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/.claude-plugin/marketplace.json), run `make update`, and open a pull request.

### Script paths

Cross-skill scripts in Claude Code documentation use `${CLAUDE_PLUGIN_ROOT}`. In Cursor, use paths relative to the repository root (see [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md)).

### Testing and evals

[Evaluating skills](evaluating-skills.md) describes eval JSON and the Claude Code `skill-creator` flow. Cursor does not ship that runner. Add or update `evals/evals.json` where applicable and describe in your pull request how reviewers can verify behavior. Treat eval definitions as checklists when you cannot run the Claude Code tool.

## Parity limits

Cursor does not include a plugin marketplace, a `plugin:command` execution model, or a built-in eval runner. Skills and reference Markdown remain the main shared surface for both tools.
