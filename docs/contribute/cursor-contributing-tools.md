---
icon: lucide/git-branch
---

# Contributing with Cursor

<!-- markdownlint-disable MD013 -->

Use this page when you want to contribute to **Red Hat Docs Agent Tools** (skills, plugins, commands, or docs under `plugins/`). For general Cursor concepts, see [Cursor fundamentals](../get-started/cursor-fundamentals.md).

## What to load in context

- **[AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md)** — Naming (`plugin:skill`), script paths from the repo root, and contribution expectations. Attach it for any work that touches plugins or skills.
- **Skills** — `plugins/<plugin>/skills/<skill>/SKILL.md`. Attach the files you need with `@` (or equivalent) so the model follows the right checklists.
- **Commands** — Cursor does not run `plugin:command` the way Claude Code does. Open the command Markdown under `plugins/<plugin>/commands/` and reuse its **Implementation** text in your prompt. See [Cursor workflows](cursor-workflows.md).
- **Agents** — Optional: attach `plugins/<plugin>/agents/*.md` when you want a defined persona or ordered steps for the session.

## Submit changes

Follow **[CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md)** for branches, `plugin.json`, `.claude-plugin/marketplace.json`, tests or eval notes, and pull requests. Run **`make update`** when your change affects generated catalog or install docs. Use **`make serve`** / **`make build`** to preview the site if needed ([README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md)).

## See also

- [Cursor fundamentals](../get-started/cursor-fundamentals.md) — rules, skills, and `plugin:skill` naming
- [Product documentation workflow](../get-started/cursor-product-documentation.md) — Agent Tools plus a separate docs repo
- [Cursor workflows](cursor-workflows.md) — Cursor versus Claude Code
