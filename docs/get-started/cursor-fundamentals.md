---
icon: lucide/layers
---

# Learn Cursor fundamentals for Agent Tools

Cursor is a VS Code-based editor with integrated agentic AI assistance

In the Cursor UI, you attach the files and rules from Red Hat Docs Agent Tools repository to your chat prompt so that the selected agentic model can plan, edit, review, and suggest changes to your documentation using the skills and rules as defined in the Agent Tools files.

The Agent Tools repository contains project-specific Markdown under `plugins/` and rules in [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) and [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules).

## Skills and rules

**Skills** in this repository are Markdown files under `plugins/<plugin>/skills/` (often named `SKILL.md`). They hold checklists, style guidance, and domain knowledge you want the model to follow for a given task (for example Red Hat supplementary style or modular-docs structure).

In Cursor, you **use** a skill by attaching the file to the chat (for example with `@`) and by naming the fully qualified **`plugin:skill`** ID in your prompt (for example `docs-tools:rh-ssg-formatting`). You would use skills when you want repeatable, repo-aligned review or editing behavior without pasting long instructions every time.

**Rules** refers to two things that work together:

- **[AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md)** at the repository root — project instructions you should attach so the model knows naming, script paths, and how this repository expects contributions to work.
- **[`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules)** — Cursor-specific rule files to apply automatically to all prompts so that baseline expectations stay in force even when you only attach a single skill file.

Use rules so answers stay consistent with team conventions, point to the right scripts, and use **`plugin:skill`** names instead of vague instructions or bare skill labels.

## How the repository works with Cursor

Skills are located under `plugins/<plugin>/skills/` as Markdown files. AGENTS.md and `.cursor/rules/` tell the model how to reference skills, run scripts, and follow contribution conventions.

Cursor does **not** provide a Claude Code-style marketplace. In Cursor, you work from the cloned repo on disk and add skill files to the chat with `@`. Keep the Agent Tools clone current with Git when you rely on upstream skills.

## Where to learn about the Cursor interface

You can learn more about how to use the Cursor UI (Agent panel, modes, **`@` mentions**, checkpoints, models, and billing) in the official Cursor documentation:

- [Cursor documentation](https://cursor.com/docs) — main help hub
- [Cursor Agent overview](https://cursor.com/docs/agent/overview) — tools, checkpoints, and related behavior
- [Plan mode](https://cursor.com/docs/agent/modes) — plan before edits (this page focuses on Plan mode)
- [Ask mode](https://cursor.com/help/ai-features/ask-mode) — read-only exploration
- [Models and pricing](https://cursor.com/docs/models) — model selection and plans

 Choose **Agent** mode if you want a Cursor agent to carry out your instructions immediately and make changes without prompting.

 Choose **Plan** mode if you want to ask Cursor to help you develop a plan for more complex work that you can approve before the agent makes any changes.

 Choose **Ask** mode when you only need to explore options without having an agent make any changes.

 Choose **Debug** for runtime code failures in scripts or tests rather than for content editing tasks.

The agentic models you can choose to use vary. The default model option is **Auto**, which dynamically chooses an available model based on the complexity of the prompt you provide to Cursor.

## Load project instructions from AGENTS.md

[AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) at the repository root summarizes skill naming, script paths, and contribution rules. Attach it when you start a chat so that the agent's suggestions stay aligned with the defined rules and guardrails.

Follow the Cursor documentation for adding files to provide context in your prompt (for example **`@`** and file pickers). Confirm that the attachment lists **AGENTS.md** from the Agent Tools root. If the picker is unclear, open `AGENTS.md` in the editor and use the product’s action to include it in context.

### Automatic rules

Cursor applies rules that exist under [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules) without manual steps. Those rules work in conjunction with the constraints defined in AGENTS.md.

### When to attach AGENTS.md again

Attach AGENTS.md again when you open a new thread, change tasks, or see the model ignore naming or path conventions.

## Terminology

- **workspace** — The folder or folders Cursor has open for the project.
- **skill** — Markdown under `plugins/<plugin>/skills/` that encodes knowledge or checklists for a named capability. See [Skills and rules](#skills-and-rules).
- **rules** — [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) and files under [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules) that constrain how the model should behave in this repository. See [Skills and rules](#skills-and-rules).
- **`@` mention** — How Cursor attaches a file or skill so that the model includes it in the current context.
- **model** — The AI model selected for a request.
- **Claude Code** — A separate assistant product that shares the same plugin Markdown.
- **`plugin:skill`** — Fully qualified skill identifier (for example `docs-tools:jira-reader`). This repository expects that form in prompts and cross-references. See [Skills and rules](#skills-and-rules).

## Common tips and troubleshooting

### The assistant suggests bare skill names or wrong script paths

Start a new thread, attach [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) again, and ask for `plugin:skill` names and paths **relative to the repository root** (Agent Tools clone).

### Agent changed files you did not intend

Revert changes in the Cursor UI or use Git to inspect diffs. See the [Cursor Agent overview](https://cursor.com/docs/agent/overview) for checkpoints.

### Usage limits, model errors, or empty responses

Check your Cursor account usage or billing and the [Cursor documentation](https://cursor.com/docs) for product errors.

### Debug mode loops without fixing the issue

Give exact reproduction steps, expected versus actual output, and any log text. For documentation editing issues, prefer **Agent** mode over **Debug**. See [Debug mode](https://cursor.com/docs/agent/debug-mode) in the Cursor documentation.

## Privacy and responsibility

Do not paste secrets, credentials, or customer-only content into the chat. Follow your organization’s policies for AI-assisted editing. For data handling, see the [Cursor documentation](https://cursor.com/docs).
