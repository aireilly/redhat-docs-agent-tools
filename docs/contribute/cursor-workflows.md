---
icon: lucide/monitor
---

# Cursor workflows

If you are new to Cursor or to agent-style workflows in the editor, read [Get Started with Cursor](../get-started/index.md) and [Cursor fundamentals](../get-started/cursor-fundamentals.md) first.

This page describes how to use and contribute to Red Hat Docs Agent Tools from **Cursor**. The plugin format and marketplace in this repository target **Claude Code**; Cursor does not implement the same marketplace or slash-command surface. You can still author and review the same Markdown skills, commands, agents, and reference material when you work in this repository.

## How Cursor fits this repository

1. **Project instructions:** Cursor loads [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) at the repository root and rules under [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules). They mirror [CLAUDE.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CLAUDE.md) conventions (skill naming, script paths, contributing rules).
1. **Skills:** Skill files live at `plugins/<plugin>/skills/` as `SKILL.md` or flat `*.md`. They are plain Markdown. Point the agent at a path or ask it to apply a named skill using fully qualified names such as `docs-tools:jira-reader`.
1. **Commands:** Claude Code exposes commands like `/hello-world:greet`. Cursor has no identical slash-command system. Treat command files under `plugins/<plugin>/commands/` as prompts or procedures: open the Markdown file and follow the **Implementation** and **Examples** sections, or paste the intended user request into the agent.
1. **Agents:** Agent definitions under `plugins/<plugin>/agents/` are portable as Markdown personas; use them as system-style instructions or project rules when appropriate. For procedural steps (layering AGENTS.md, skills, commands, and agents in Agent mode), see [Invoke a more complex workflow](cursor-contributing-tools.md#invoke-a-more-complex-workflow).
1. **Installation:** There is no Cursor equivalent to `/plugin marketplace add`. Clone or add this repository as a workspace. All plugin sources are available on disk under `plugins/`.

## Contributing from Cursor

Follow [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md). The workflow matches any other editor: branch, change Markdown under the right plugin, bump `plugin.json`, sync [`.claude-plugin/marketplace.json`](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/.claude-plugin/marketplace.json), run `make update`, and open a pull request.

### Script paths

In documentation and prompts aimed at Claude Code, cross-skill scripts use `${CLAUDE_PLUGIN_ROOT}`. When you run or document commands for Cursor, use paths relative to the repository root (see [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md)).

## Testing and evals

[Evaluating skills](evaluating-skills.md) describes eval JSON and the Claude Code `skill-creator` flow. Cursor does not ship that runner. You should still add or update `evals/evals.json` where applicable and describe in your pull request how reviewers can verify behavior (for example, manual steps or expected outputs). Treat eval definitions as checklists when you cannot run the Claude Code tool.

## Finding skill files

Skill sources live under `plugins/<plugin>/skills/`. Open paths from the repository tree in your editor or search the workspace when you need a specific `SKILL.md`.

## Parity limits

Full feature parity with Claude Code is not possible in Cursor today: there is no plugin marketplace, no `/plugin:command` execution model, and no built-in eval runner described in the evaluating-skills guide. Skills and reference Markdown remain the main shared surface for both tools.
