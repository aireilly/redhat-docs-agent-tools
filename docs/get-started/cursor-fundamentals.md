---
icon: lucide/layers
---

# Cursor fundamentals for Agent Tools

This page collects **shared** concepts for using Cursor with **Red Hat Docs Agent Tools**:
the Agent panel, modes, loading `AGENTS.md`, `@` mentions, and fully qualified
`plugin:skill` names.

Read it before (or beside) [Using Cursor with your product documentation](cursor-product-documentation.md) or [Contributing with Cursor](../contribute/cursor-contributing-tools.md). Repository-specific behavior compared with Claude Code is summarized in [Cursor workflows](../contribute/cursor-workflows.md).

## What Cursor is

Cursor is a code editor based on VS Code with integrated AI assistance.

In any repository, you can open Cursor and select different modes (`Ask`, `Debug`, `Plan`, `Agent`) to match your goal. You can also choose the model you want to use to provide assistance (including different `claude` and `gpt` models).

When the **Red Hat Docs Agent Tools** repository is on disk, you use Cursor to read skills under `plugins/<plugin>/skills/`, attach `AGENTS.md`, and follow the same conventions as [CLAUDE.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CLAUDE.md) for collaborators who use Claude Code elsewhere. The repository includes [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) and [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules).

If you work **only** inside the Tools clone, you can build or preview the project documentation site locally; see [README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md).

## What "agentic workflows" mean here

An **agentic** workflow means the model can work across multiple steps and files using a project's context (open files, repository layout, and rules) and is not restricted to answering a single isolated question as with most generic chat LLMs like Gemini or ChatGPT.

In practice, you provide a goal in a prompt. The assistant might then read files, propose edits, and run terminal commands where allowed. For security purposes, the assistant will often prompt you for permission before carrying out actions.

The project rules in AGENTS.md and `.cursor/rules/` act as guardrails so changes stay aligned with repository naming, script paths, contribution expectations, and other restrictions.

## How the repository uses AI context

Skills are Markdown knowledge under `plugins/<plugin>/skills/`. Rules and AGENTS.md tell the assistant how to reference skills, run scripts, and match plugin metadata.

Cursor does **not** provide a Claude Code–style marketplace inside the editor. You use the repository tree on disk and attach files with `@`. Slash commands, the eval runner, and other differences are summarized under [Parity limits](../contribute/cursor-workflows.md#parity-limits) on the Cursor workflows page.

## Orient yourself in the UI

### Beginner defaults

Open the **Agent** side panel first (shortcut **Cmd+I** on macOS and
**Ctrl+I** on Windows and Linux). Use **Agent** mode for normal edits and commands. Use
**Ask** mode when you only want answers and file reads **without** edits. Leave the
**model** on **Auto** unless your team sets a policy. Then type your message.

### Details: modes and models

#### If you only remember one thing

Use **Ask** to explore **without** edits; use **Agent** for normal edits and commands; use **Plan** when you want a written plan before large changes; use **Debug** only for **runtime** bugs (scripts, tests), not for ordinary Markdown edits.

Cursor displays the coding assistant in the **Agent** side panel. Open that panel first, then choose **how** the assistant should behave (**mode**) and **which model** should provide assistance (**model**), and then type your prompt.

#### Switch modes

Use **Shift+Tab** to cycle modes, or open the **mode** control in the input area (labels vary by version). Official overviews: [Ask mode](https://cursor.com/help/ai-features/ask-mode), [Plan Mode](https://cursor.com/docs/agent/modes), [Cursor Agent](https://cursor.com/docs/agent/overview), [Debug Mode](https://cursor.com/docs/agent/debug-mode).

#### Ask

Ask mode is **read-only**. The assistant answers questions and explores files **without** applying edits. Use it to learn where skills live, what a command file contains, or how two paths relate. When you are ready to change files, switch to **Agent** (or **Plan** first for large work).

#### Plan

Plan mode produces a **written plan** before the assistant applies broad changes. The assistant can research the workspace, ask clarifying questions, and output a plan you can review or edit. Use it for ambiguous scope, many files, or architectural choices. Plans save under your home directory by default; you can move a plan into the workspace for sharing. For quick, familiar edits, **Agent** mode alone is often enough.

#### Agent

Agent mode is the usual **do the work** mode: the assistant can edit files, run terminal commands, and use tools (search, rules, and more). Use it for everyday tasks (edits, scripts, pull-request prep). The [Cursor Agent](https://cursor.com/docs/agent/overview) overview describes tools, checkpoints, and related behavior.

#### Debug

Debug mode targets **bugs that need runtime evidence**. The assistant forms hypotheses, may add instrumentation, asks you to **reproduce** the problem, reads logs, then applies a focused fix. Use it when something **fails at run time** (for example scripts, tests, or local tooling), not for ordinary documentation-only edits. See [Debug Mode](https://cursor.com/docs/agent/debug-mode).

#### How to pick a mode in the repository

1. **Ask** — Learn the layout, read skills or commands, or confirm conventions before you edit.
1. **Plan** — Large or risky changes where you want an agreed plan before edits (for example a new plugin or wide refactor).
1. **Agent** — Normal editing and automation you already understand.
1. **Debug** — Investigating failures that depend on execution, logs, or reproduction steps.

#### Choosing a model

The Agent input area includes a **model** control (often a dropdown). **Auto** (and related **Composer** options where your plan offers them) is a good default: Cursor **chooses** a model to balance quality, speed, and cost. Details and billing differ by plan; see [Models and pricing](https://cursor.com/docs/models).

#### More detail on model choices

1. **A specific named model** — You pick a provider model explicitly. That usually draws from the **API** usage pool at the rate for that model, so per-task cost varies. Use a stronger model when tasks are large, subtle, or cross many files; use a lighter or faster model for short questions or mechanical edits if your plan exposes those choices.
1. **Max Mode** — Increases the **context window** to the maximum the model supports for harder tasks; it typically consumes usage faster. Enable when the assistant needs more of the tree in one pass.
1. **Policy** — Your organization may limit which models you may select. Follow internal rules.

Shortcuts, control names, and panel layout **change between Cursor versions**. For the current UI, see the [Cursor documentation](https://cursor.com/docs).

If you know VS Code, you will already feel comfortable in the Cursor UI. If you have never used VS Code, treat Cursor like any desktop editor with a file tree on the side, tabs for open files, and a **Terminal** menu for a built-in shell. The **Agent** side panel on the right is separate from the file tree.

## Load project instructions

The repository ships [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) at the **root** of the clone (the same folder that contains `README.md` and `plugins/`). That file is the Cursor-oriented summary of how to name skills, call scripts, and match contribution rules. The assistant can guess from open files, but **you get more reliable answers** when AGENTS.md is explicitly part of the conversation before you ask for edits or refactors.

### Why beginners should load it first

Without those rules, the model may suggest skill names, paths, or workflows that fit generic Markdown projects but not Red Hat Docs Agent Tools. Loading AGENTS.md reduces rework and keeps suggestions closer to what reviewers expect.

### What to load

1. **AGENTS.md** — Always start here for project-wide rules. It complements [CLAUDE.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CLAUDE.md), which is aimed at Claude Code in other environments.
1. **Optional extras** — After you are comfortable with `@`, you can add specific skill files or command files the same way when a task should follow one document exactly (for example a `SKILL.md` under `plugins/<plugin>/skills/`).

### How to add AGENTS.md to a message (typical flow)

1. Open the **Agent** panel in Cursor (sidebar or layout varies by version).
1. Start the message where you will ask for help.
1. Type **`@`** (at-sign). Cursor usually shows a menu of files, symbols, or context types.
1. Begin typing **`AGENTS`** or **`agents`** and choose **`AGENTS.md`** from the list when it appears, or select **File** / workspace file search if your build offers it and pick `AGENTS.md` from the repository root.
1. Confirm that **`AGENTS.md`** appears as an attachment or inline reference in the compose box (wording differs by build).
1. On a **new line**, write your request (for example, “Summarize the skill naming rule in AGENTS.md” or “Help me edit a plugin following AGENTS.md”).

### If `@` does not show AGENTS.md

Try **`@`** and the full relative path from the repo root, for example **`@AGENTS.md`** as plain text. Or open **`AGENTS.md`** in the editor first and use the editor’s “add to chat” or “include in context” action if available.

### Other ways to add context

You can **paste a short excerpt** from AGENTS.md when you only need one rule. For large tasks, attaching the whole file works better than a short paste.

### Automatic rules

Cursor may already apply files under [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules) without you doing anything. Those rules still pair best with AGENTS.md when you want the assistant to follow the **full** project contract in one place.

### When to load again

Start a **new chat thread** or re-attach AGENTS.md when you switch to a different task, when the assistant seems to ignore naming or path conventions, or after Cursor updates that might clear context. For product-specific behavior of `@` and context, see the [Cursor documentation](https://cursor.com/docs).

## Terminology

The following terms appear in the repository documentation. The list is not exhaustive.

- **workspace** — The folder Cursor has open as the project. That may be the **repository root** of the Tools clone (the folder that contains `AGENTS.md` and `plugins/`), or a **multi-root workspace** that includes that clone plus your product documentation repository.
- **`plugin:skill`** — The fully qualified name of a skill (for example `docs-tools:jira-reader`). The repository requires that form everywhere. See [How to refer to skills and fully qualified names](#how-to-refer-to-skills-and-fully-qualified-names) for more information.
- **`@` mention** — Typing `@` in the chat or Agent input to attach a file or symbol to the message so the model includes it in context.
- **Agent panel** — The Cursor UI area for chat and Agent tasks (shortcut **Cmd+I** / **Ctrl+I**). An **agent file** under `plugins/<plugin>/agents/` is unrelated Markdown. Do not confuse the two.
- **model** — The AI model selected for a request from the model dropdown list. **Context window** is how much text the model can consider at once. **Max Mode** uses a larger context window when your plan allows it.
- **Claude Code** — A separate assistant product that uses the same plugin Markdown. You do not install it inside Cursor; see [Cursor workflows](../contribute/cursor-workflows.md) for how the files map.

## How to refer to skills and fully qualified names

Always reference **skills** with the fully qualified form `plugin:skill` (for example, `docs-tools:jira-reader`, not `jira-reader` alone). The same rule applies in agent instructions, cross-references, and inline text. See [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) for the full convention and examples.

## Privacy and responsibility

Do not paste secrets, credentials, or customer-only content into the chat. Follow your team and organizational policies for AI-assisted editing. For how Cursor handles data and privacy, see the [Cursor documentation](https://cursor.com/docs).

## Common tips and troubleshooting

### The assistant suggests bare skill names or wrong script paths

Start a **new thread**, attach [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) again, and ask for `plugin:skill` names and paths **relative to the repository root**. If the assistant still drifts, paste the exact rule you need from AGENTS.md into the message.

### Agent changed files you did not intend

Cursor can offer **checkpoints** to roll back agent edits; see the [Cursor Agent](https://cursor.com/docs/agent/overview) overview. For permanent history, use **Git** to inspect diffs and revert.

### Usage limits, model errors, or empty responses

Open your Cursor account **usage** or **billing** view and confirm the plan still has quota. Try **Auto** or another **model** from the dropdown. For product errors, see [Cursor documentation](https://cursor.com/docs) or support channels.

### Debug mode loops without fixing the issue

Give **exact** reproduction steps, expected versus actual behavior, and any log or stderr text. If the problem is only wording in Markdown, switch to **Agent** mode instead; Debug mode targets **runtime** failures.
