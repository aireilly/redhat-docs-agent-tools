---
icon: lucide/monitor
---

# Cursor workflows

The plugin format and marketplace in this repository target **Claude Code**. Cursor does not provide
a marketplace, but you can still author, use, and review the same skills, commands,
agents, and reference material.

For what **skills** and **rules** mean in Cursor and why to use them, see [Skills and
rules](../get-started/cursor-fundamentals.md#skills-and-rules) in **Cursor fundamentals**.

## How Cursor works with this repository

1. **Project instructions** — Attach [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) from the repository root when you need shared naming, path, and contribution rules. Rules under [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules) can apply automatically in Cursor (see [Automatic rules](../get-started/cursor-fundamentals.md#automatic-rules) in **Cursor fundamentals**). [CLAUDE.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CLAUDE.md) documents Claude Code-specific behavior and complements AGENTS.md.
1. **Skills** — Skills are located at `plugins/<plugin>/skills/` as plain Markdown files. You can point the Cursor agent to a path that contains skills, you can refer to skills using fully qualified names such as `docs-tools:jira-reader`, or you can use an `@` command to attach the skill to a prompt.
1. **Commands** — In Claude Code, you can run commands like `hello-world:greet`. Cursor has no equivalent
   command system. Attaching **skills** to a prompt is the usual first step in Cursor rather than invoking a command. However, you can use the Claude Code commands from this repository in Cursor by opening the command file and copy/pasting the content into your prompt.
1. **Agents** — Agent definitions in the Markdown files under `plugins/<plugin>/agents/` are personas to apply to your prompt or project. You can use the personas as system instructions or project rules to guide the types of responses the agent will provide to your prompt.

## Contributing from Cursor

Follow [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md). Branch, edit Markdown under the right plugin, bump `plugin.json`, sync [`.claude-plugin/marketplace.json`](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/.claude-plugin/marketplace.json), run `make update`, and open a pull request.

### Script paths

Cross-skill scripts in Claude Code documentation use `${CLAUDE_PLUGIN_ROOT}`. In Cursor, you must use paths relative to the repository root (see [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md)).

### Testing and evals

[Evaluating skills](evaluating-skills.md) describes eval JSON and the Claude Code `skill-creator` flow. Cursor does not ship that runner. Add or update `evals/evals.json` where applicable and describe in your pull request how reviewers can verify behavior. Treat eval definitions as checklists when you cannot run the Claude Code tool.
