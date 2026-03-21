---
icon: lucide/layers
---

# Cursor fundamentals for Agent Tools

Cursor is a VS Code-based editor with built-in AI assistance. In the Agent panel, you chat with a model that can read files, propose edits, and run commands. Red Hat Docs Agent Tools gives the model project-specific skills, rules, and naming conventions so the model's output matches the guidelines.

## How the repository works with Cursor

Skills live under `plugins/<plugin>/skills/` as plain Markdown. The project rules in [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) and [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules) tell the model how to reference those skills, run scripts, and follow contribution conventions.

Cursor does **not** provide a Claude Code-style marketplace. You work with the repository on disk and attach files with `@`. See [Cursor workflows](../contribute/cursor-workflows.md) for more about what differs from Claude Code.

## Choose a mode

Open the **Agent** panel (**Cmd+I** on macOS, **Ctrl+I** on Windows and Linux). Pick a mode from the input area, then type your prompt.

| Mode | Purpose | When to use |
| --- | --- | --- |
| **Ask** | Read-only answers and file exploration | Learn the layout, read skills, confirm conventions |
| **Plan** | Written plan before broad changes | Ambiguous scope, many files, or architectural choices |
| **Agent** | Edit files and run commands | Everyday tasks you already understand |
| **Debug** | Fix runtime failures with logs and reproduction | Scripts or tests that fail at run time (not Markdown-only edits) |

Use **Shift+Tab** to cycle modes. For more detail see the [Cursor documentation](https://cursor.com/docs).

### Choose a model

Leave the **model** on **Auto** unless your team sets a policy. **Auto** balances quality, speed, and cost. For details see [Models and pricing](https://cursor.com/docs/models).

## Load project instructions

The repository root contains [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md). That file summarizes skill naming, script paths, and contribution rules. Attach it to every new chat thread.

### Attach AGENTS.md

1. Open the **Agent** panel and start a message.
1. Type **`@`**, then start typing **`AGENTS`** and select **AGENTS.md** from the list.
1. Confirm the file appears as an attachment in the compose box.
1. Write your request on a new line.

If `@` does not show the file, type the full path as plain text (for example `@AGENTS.md`), or open the file in the editor first and use the "add to chat" action.

### Automatic rules

Cursor applies files under [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules) without you doing anything. Those rules pair best with AGENTS.md when you want the model to follow the full project contract.

### When to reload

Re-attach AGENTS.md when you start a new thread, switch tasks, or notice the model ignoring naming or path conventions.

## Terminology

- **workspace** — The folder (or folders) Cursor has open as the project.
- **`plugin:skill`** — A fully qualified skill name such as `docs-tools:jira-reader`. The repository requires that form everywhere.
- **`@` mention** — Typing `@` in the input to attach a file so the model includes it in context.
- **Agent panel** — The Cursor sidebar for chat and Agent tasks. An **agent file** under `plugins/<plugin>/agents/` is unrelated Markdown.
- **model** — The AI model selected from the dropdown. **Max Mode** uses a larger context window.
- **Claude Code** — A separate assistant product that shares the same plugin Markdown.

## Privacy and responsibility

Do not paste secrets, credentials, or customer-only content into the chat. Follow your organization's policies for AI-assisted editing.

## Common tips and troubleshooting

### The assistant suggests bare skill names or wrong script paths

Start a **new thread**, attach [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) again, and ask for `plugin:skill` names and paths **relative to the repository root**.

### Agent changed files you did not intend

Cursor offers **checkpoints** to roll back edits. See the [Cursor Agent](https://cursor.com/docs/agent/overview) overview. For permanent history, use **Git** to inspect diffs and revert.

### Usage limits, model errors, or empty responses

Open your Cursor account **usage** or **billing** view and confirm quota remains. Try **Auto** or another model. For product errors see the [Cursor documentation](https://cursor.com/docs).

### Debug mode loops without fixing the issue

Provide **exact** reproduction steps, expected versus actual output, and any log text. If the problem is only wording in Markdown, switch to **Agent** mode.
