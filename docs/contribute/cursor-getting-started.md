---
icon: lucide/book-open
---

# Getting started with Cursor

Use the following sections if you are new to Cursor or to agent-style workflows in an editor. The page explains basic ideas first, then concrete steps to open the repository and try a small task and then a more complex task.

For how these ideas map to Red Hat Docs Agent Tools (skills, commands, parity with Claude Code), see [Cursor workflows](cursor-workflows.md).

## What Cursor is in this context

Cursor is a code editor based on VS Code with integrated AI assistance. If you know VS Code, you will already feel comfortable in the Cursor UI.

In the Red Hat Docs Agent Tools repository, you use Cursor to read and edit skills, commands, and agents under `plugins/`. These items are formatted as plain Markdown. You can also preview the Red Hat Docs Agent Tools documentation site locally with `make serve`.

The Red Hat Docs Agent Tools repository also includes [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) and [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules) so that enables the Cursor assistant to follow the same conventions as [CLAUDE.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CLAUDE.md) for Claude Code.

## What agentic workflows mean here

An **agentic** workflow means the model can work across multiple steps and files using a project's context (open files, repository layout, and rules) and is not restricted to answering a single isolated question as with most generic chat LLMs like Gemini or ChatGPT.

In practice, you provide a goal in a prompt. The assistant then might read files, propose edits, and run terminal commands where allowed. For security purposes, you will be prompted often for permission by the asstant to carry out actions.

The project rules in AGENTS.md and `.cursor/rules/` act as guardrails so changes stay aligned with repository naming, script paths, contribution expectations, and other restrictions.

## How the repository uses AI context

Skills are Markdown knowledge under `plugins/<plugin>/skills/`. Rules and AGENTS.md tell the assistant how to reference skills, run scripts, and match plugin metadata.

Note that no Claude Code marketplace equivalent exists inside Cursor. You work with the tree on disk. For other limits compared to Claude Code (slash commands, eval runner, and so on), see [Parity limits](cursor-workflows.md#parity-limits) on the Cursor workflows page.

## Skills and fully qualified names

Always reference **skills** with the fully qualified form `plugin:skill` (for example, `docs-tools:jira-reader`, not `jira-reader` alone). The same rule applies in agent instructions, cross-references, and inline text. See [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) for the full convention and examples.

## Privacy and responsibility

Do not paste secrets, credentials, or customer-only content into the chat. Follow your team and organizational policies for AI-assisted editing. For how Cursor handles data and privacy, see the [Cursor documentation](https://cursor.com/docs).

## Suggested path for a new contributor

```mermaid
flowchart TD
  newbie[New contributor]
  prereq[Prerequisites Cursor Git python3]
  workspace[Open repo root as workspace]
  orient[Orient UI modes and model]
  loadRules[Load AGENTS.md]
  minimal[Try minimal workflow]
  complex[Invoke complex workflow]
  site[make update and make serve]
  nextSteps[CONTRIBUTING and cursor workflows]
  tips[Tips and troubleshooting]
  newbie --> prereq --> workspace --> orient --> loadRules --> minimal --> complex --> site --> nextSteps
  nextSteps -.-> tips
```
## Prerequisites

1. You have installed Cursor.
1. You have installed Git and it has access to GitHub (fork or clone permissions as required by your organization).
1. You have installed `python3` so that you can run `make update` and the Zensical docs build (see [README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md)).

## Open the repository as the workspace

1. Clone the upstream repository or your fork. For the upstream copy:

   ```bash
   git clone https://github.com/redhat-documentation/redhat-docs-agent-tools.git
   ```

   Use your fork URL instead if you contribute through a fork (for example `https://github.com/<your-username>/redhat-docs-agent-tools.git`).

1. In Cursor, open the **repository root** as the folder or workspace, not a parent directory that only contains the repo. After the clone command above, that folder is `redhat-docs-agent-tools/`.

Paths in [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) and in scripts assume the workspace root matches the repository root.

## Orient yourself in the UI

Cursor exposes the coding assistant in the **Agent** side panel (common shortcut **Cmd+I** on macOS and **Ctrl+I** on Windows and Linux). Open that panel first, then choose **how** the assistant should behave (**mode**) and **which model** should answer (**model**), then type your message.

**Switch modes:** Use **Shift+Tab** to cycle modes, or open the **mode** control in the input area (labels vary by version). Official overviews: [Ask mode](https://cursor.com/help/ai-features/ask-mode), [Plan Mode](https://cursor.com/docs/agent/modes), [Cursor Agent](https://cursor.com/docs/agent/overview), [Debug Mode](https://cursor.com/docs/agent/debug-mode).

**Ask**

Ask mode is **read-only**. The assistant answers questions and explores files **without** applying edits. Use it to learn where skills live, what a command file contains, or how two paths relate. When you are ready to change files, switch to **Agent** (or **Plan** first for large work).

**Plan**

Plan mode produces a **written plan** before the assistant applies broad changes. The assistant can research the workspace, ask clarifying questions, and output a plan you can review or edit. Use it for ambiguous scope, many files, or architectural choices. Plans save under your home directory by default; you can move a plan into the workspace for sharing. For quick, familiar edits, **Agent** mode alone is often enough.

**Agent**

Agent mode is the usual **do the work** mode: the assistant can edit files, run terminal commands, and use tools (search, rules, and more). Use it for everyday contribution tasks in the repository (Markdown edits, `make update`, pull-request prep). The [Cursor Agent](https://cursor.com/docs/agent/overview) overview describes tools, checkpoints, and related behavior.

**Debug**

Debug mode targets **bugs that need runtime evidence**. The assistant forms hypotheses, may add instrumentation, asks you to **reproduce** the problem, reads logs, then applies a focused fix. Use it when something **fails at run time** (for example scripts, tests, or local tooling), not for ordinary documentation-only edits. See [Debug Mode](https://cursor.com/docs/agent/debug-mode).

**How to pick a mode in the repository**

1. **Ask** — Learn the layout, read skills or commands, or confirm conventions before you edit.
1. **Plan** — Large or risky changes where you want an agreed plan before edits (for example a new plugin or wide refactor).
1. **Agent** — Normal editing and automation you already understand.
1. **Debug** — Investigating failures that depend on execution, logs, or reproduction steps.

**Choosing a model**

The Agent input area includes a **model** control (often a dropdown). That control selects which **frontier model** runs the request. Details and billing differ by plan; see [Models and pricing](https://cursor.com/docs/models).

1. **Auto** (and related **Composer** options where your plan offers them) — Cursor **chooses** a model to balance quality, speed, and cost for everyday work. A good default for most tasks in the repository.
1. **A specific named model** — You pick a provider model explicitly. That usually draws from the **API** usage pool at the rate for that model, so per-task cost varies. Use a stronger model when tasks are large, subtle, or cross many files; use a lighter or faster model for short questions or mechanical edits if your plan exposes those choices.
1. **Max Mode** — Increases the **context window** to the maximum the model supports for harder tasks; it typically consumes usage faster. Enable when the assistant needs more of the tree in one pass.
1. **Policy** — Your organization may limit which models you may select. Follow internal rules.

Shortcuts, control names, and panel layout **change between Cursor versions**. For the current UI, see the [Cursor documentation](https://cursor.com/docs).

## Load project instructions

The repository ships [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) at the **root** of the clone (the same folder that contains `README.md` and `plugins/`). That file is the Cursor-oriented summary of how to name skills, call scripts, and match contribution rules. The assistant can guess from open files, but **you get more reliable answers** when AGENTS.md is explicitly part of the conversation before you ask for edits or refactors.

**Why beginners should load it first:** Without those rules, the model may suggest skill names, paths, or workflows that fit generic Markdown projects but not Red Hat Docs Agent Tools. Loading AGENTS.md reduces rework and keeps suggestions closer to what reviewers expect.

**What to load**

1. **AGENTS.md** — Always start here for project-wide rules. It complements [CLAUDE.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CLAUDE.md), which is aimed at Claude Code in other environments.
1. **Optional extras** — After you are comfortable with `@`, you can add specific skill files or command files the same way when a task should follow one document exactly (for example a `SKILL.md` under `plugins/<plugin>/skills/`).

**How to add AGENTS.md to a message (typical flow)**

1. Open the **Agent** panel in Cursor (sidebar or layout varies by version).
1. Start the message where you will ask for help.
1. Type **`@`** (at-sign). Cursor usually shows a menu of files, symbols, or context types.
1. Begin typing **`AGENTS`** or **`agents`** and choose **`AGENTS.md`** from the list when it appears, or select **File** / workspace file search if your build offers it and pick `AGENTS.md` from the repository root.
1. Confirm that **`AGENTS.md`** appears as an attachment or inline reference in the compose box (wording differs by build).
1. On a **new line**, write your request (for example, “Summarize the skill naming rule in AGENTS.md” or “Help me edit this plugin following AGENTS.md”).

If your Cursor build does not show `AGENTS.md` after `@`, try **`@`** then the full relative path from the repo root, for example **`@AGENTS.md`** as plain text, or open **`AGENTS.md`** in the editor first and use the editor’s “add to chat” or “include in context” action if available. You can also **paste a short excerpt** from AGENTS.md into the message when you only need one rule, though attaching the whole file is better for large tasks.

**Automatic rules:** Cursor may already apply files under [`.cursor/rules/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/.cursor/rules) without you doing anything. Those rules still pair best with AGENTS.md when you want the assistant to follow the **full** project contract in one place.

**When to load again:** Start a **new chat thread** or re-attach AGENTS.md when you switch to a different task, when the assistant seems to ignore naming or path conventions, or after Cursor updates that might clear context. For product-specific behavior of `@` and context, see the [Cursor documentation](https://cursor.com/docs).

## Try a minimal workflow

1. Open [`plugins/hello-world/commands/greet.md`](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/plugins/hello-world/commands/greet.md) in the workspace. Cursor does not support `/hello-world:greet` as a slash command; read the **Implementation** and **Examples** sections and use that text as the basis for a chat prompt or agent task.
1. Alternatively, open any `SKILL.md` under `plugins/docs-tools/skills/` and ask the assistant to summarize when the skill applies, using the fully qualified name `docs-tools:<skill-name>` in the answer.

## Invoke a more complex workflow

Use the following approach when work spans multiple files, needs a short plan, or may run terminal commands you want to review. The goal is structured, multi-step assistance rather than a single factual answer.

**When to escalate:** Prefer **Agent** mode (or the product equivalent) for those cases. Keep quick questions and narrow lookups in the primary chat panel. Feature names and layout change between Cursor versions; see the [Cursor documentation](https://cursor.com/docs) for current UI behavior.

**Layer context deliberately** before you start the run:

1. [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) for repository-wide rules (for example via `@AGENTS.md` where supported).
1. The relevant `SKILL.md` or flat skill file under `plugins/<plugin>/skills/` when output must follow a named skill.
1. A **command** file under `plugins/<plugin>/commands/` when you want the **Implementation** and **Examples** sections to act as the ordered procedure for the session.
1. Optionally an **agent** Markdown file under [`plugins/<plugin>/agents/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/plugins/docs-tools/agents) (for example a docs-tools persona) so the model follows that role or checklist for the task.

**Structured prompts** help reviewers and keep behavior aligned with the repo: state the goal, constraints (for example branch name, scope, no unrelated refactors), which fully qualified skill applies (`plugin:skill`), and which paths or file types to touch. Automation and human review expect fully qualified skill names; see [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md).

**Example structured prompt:** Use a layout like the following when you want the assistant to apply **one named skill** to a **bounded set of paths** (for example before opening a pull request that only touches documentation under a plugin).

```text
Goal: Apply Red Hat style checks from docs-tools:rh-ssg-formatting to
plugins/docs-tools/README.md only.

Constraints:
- Do not edit files outside that path.
- Do not bump plugin.json or .claude-plugin/marketplace.json in this pass.
- Reference the skill as docs-tools:rh-ssg-formatting in summaries and commit intent.

Context to load: @AGENTS.md and
plugins/docs-tools/skills/rh-ssg-formatting/SKILL.md

Steps:
1. Summarize which checks from the skill apply to README-style Markdown.
2. Propose edits to plugins/docs-tools/README.md that match the skill.
3. Give a short bullet list of changes suitable for a PR description.
```

You would paste or adapt that block in **Agent** mode after attaching the listed files (or their `@` references). The same pattern works for other skills and paths; replace the skill name, files, and constraints to match your task.

**No slash-command execution in Cursor:** A larger task does not enable `/plugin:command`. The pattern stays the same as on [Cursor workflows](cursor-workflows.md): read the command or agent Markdown, then drive the assistant with that content in the prompt or attached context.

**Privacy:** Long-running threads with more context increase the chance of accidental paste errors. Do not put secrets or customer-only material into the chat; see [Privacy and responsibility](#privacy-and-responsibility) above.

## Preview the documentation site

1. Install Zensical if needed: `python3 -m pip install zensical`.
1. From the repository root, run `make update` to regenerate plugin-related pages under `docs/` (generated files may be gitignored; see [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md)).
1. Run `make serve` to start the local site, or `make build` for a full build.

See the [README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md) for the same commands in short form.

## Next steps for contributors

1. Read [Cursor workflows](cursor-workflows.md) for repository-specific behavior and parity with Claude Code.
1. Follow [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md) for branches, `plugin.json`, marketplace sync, and pull requests.

## Tips and troubleshooting

**Workspace path looks wrong.** If paths in errors include an extra parent folder, or `@` search never finds `AGENTS.md`, you may have opened a directory **above** the repository root. Close the folder, then open the clone folder that contains **`AGENTS.md`**, **`plugins/`**, and **`README.md`** in one place. See [Open the repository as the workspace](#open-the-repository-as-the-workspace).

**The assistant suggests bare skill names or wrong script paths.** Start a **new thread**, attach [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) again, and ask for `plugin:skill` names and paths **relative to the repository root**. If the assistant still drifts, paste the exact rule you need from AGENTS.md into the message.

**Slash commands like `/hello-world:greet` do nothing.** Expected in Cursor. Use command Markdown as prompts; see [Cursor workflows](cursor-workflows.md) and [Try a minimal workflow](#try-a-minimal-workflow).

**`make update`, `make build`, or `make serve` fails.** Run commands from the **repository root** where the `Makefile` lives. Confirm `python3` is on your `PATH`. Install Zensical with `python3 -m pip install zensical` if the error says the command is missing. Read the full error text; it often names a missing dependency or a bad path.

**The docs site shows a Mermaid diagram as plain code.** The Zensical site needs the Mermaid fence configuration in [`zensical.toml`](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/zensical.toml). Build with `make build` and open the generated site. The **Markdown preview inside the editor** may not render Mermaid unless you use a preview extension; rely on `make serve` or the published site for diagrams.

**Agent changed files you did not intend.** Cursor can offer **checkpoints** to roll back agent edits; see the [Cursor Agent](https://cursor.com/docs/agent/overview) overview. For permanent history, use **Git** to inspect diffs and revert.

**Usage limits, model errors, or empty responses.** Open your Cursor account **usage** or **billing** view and confirm the plan still has quota. Try **Auto** or another **model** from the dropdown. For product errors, see [Cursor documentation](https://cursor.com/docs) or support channels.

**Debug mode loops without fixing the issue.** Give **exact** reproduction steps, expected versus actual behavior, and any log or stderr text. If the problem is only wording in Markdown, switch to **Agent** mode instead; Debug mode targets **runtime** failures.
