---
icon: lucide/git-branch
---

# Contributing with Cursor

This guide is for people who **clone Red Hat Docs Agent Tools** to contribute skills, plugins, commands, or documentation under `plugins/` (and related files).

Read [Cursor fundamentals](../get-started/cursor-fundamentals.md) first (Agent panel, `AGENTS.md`, `@` mentions, and `plugin:skill` names). For the section overview, see [Get Started with Cursor](../get-started/index.md).

## Start here

### Checklist

1. Meet the [Prerequisites](#prerequisites): install Cursor and Git. Install `python3` when you need repository tooling (see [README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md)).
1. Clone and open the [repository root](#open-the-repository-as-the-workspace).
1. Open Cursor. Open the **Agent** panel and pick **Agent** mode and a model (see [Orient yourself in the UI](../get-started/cursor-fundamentals.md#orient-yourself-in-the-ui)).
1. Attach **`AGENTS.md`** before substantive edits. See [Load project instructions](../get-started/cursor-fundamentals.md#load-project-instructions).
1. Try a [minimal workflow](#try-a-minimal-workflow), optionally [invoke a more complex workflow](#invoke-a-more-complex-workflow). Follow [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md) for branches, `plugin.json`, and docs-site build steps when your change affects the published site.
1. Read [Next steps for contributors](#next-steps-for-contributors). If something fails, see [Tips and troubleshooting](#tips-and-troubleshooting).

## Prerequisites

- You have installed Cursor.
- You have installed Git and it has access to GitHub (fork or clone permissions as
   required by your organization).
- You have installed `python3`. Python is required if you plan to run repository tooling (for example
   the docs site commands in [README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md)).

## Open the repository as the workspace

Use this section when the workspace contains **only** the Red Hat Docs Agent Tools clone.

1. Clone the upstream repository or your fork. For the upstream copy:

   ```bash
   git clone https://github.com/redhat-documentation/redhat-docs-agent-tools.git
   ```

   Use your fork URL instead if you contribute through a fork (for example
   `https://github.com/<your-username>/redhat-docs-agent-tools.git`).

1. In Cursor, use **File** → **Open Folder** (or your operating system equivalent) and
   select the **repository root**, not a parent directory that only contains the repo.
   After the clone command above, that folder is `redhat-docs-agent-tools/`. The
   workspace root is the folder that contains **`Makefile`**, **`AGENTS.md`**, and
   **`plugins/`** in one place.

   Paths in [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) and in scripts assume the workspace root matches the repository root.

### Integrated terminal

To run `git`, `make`, or `python3` commands later, open
**Terminal** → **New Terminal** (or the command palette shortcut your build uses). If
the shell opens in another directory, run `cd` into `redhat-docs-agent-tools` and
confirm with `pwd` (Linux or macOS) or `cd` with no arguments (Windows PowerShell:
`Get-Location`) that the current directory lists `Makefile` when you run `ls` or `dir`.

## Try a minimal workflow

1. In the workspace, open `plugins/hello-world/commands/greet.md` from the repository root (use the file tree or **File** → **Open File**). You can also [view the file on GitHub](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/plugins/hello-world/commands/greet.md). Cursor does not support `/hello-world:greet` as a slash command; read the **Implementation** and **Examples** sections and use that text as the basis for a chat prompt or agent task.
1. Alternatively, open any `SKILL.md` under `plugins/docs-tools/skills/` and ask the assistant to summarize when the skill applies, using the fully qualified name `docs-tools:<skill-name>` in the answer.

## Invoke a more complex workflow

Use the following approach when work spans multiple files, needs a short plan, or may run terminal commands you want to review. The goal is structured, multi-step assistance rather than a single factual answer.

### When to escalate

Prefer **Agent** mode (or the product equivalent) for those cases. Keep quick questions and narrow lookups in the primary chat panel. Feature names and layout change between Cursor versions; see the [Cursor documentation](https://cursor.com/docs) for current UI behavior.

### Layer context deliberately

Complete the following steps before you start the run:

1. [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) for repository-wide rules (for example via `@AGENTS.md` where supported).
1. The relevant `SKILL.md` or flat skill file under `plugins/<plugin>/skills/` when output must follow a named skill.
1. A **command** file under `plugins/<plugin>/commands/` when you want the **Implementation** and **Examples** sections to act as the ordered procedure for the session.
1. Optionally an **agent** Markdown file under [`plugins/<plugin>/agents/`](https://github.com/redhat-documentation/redhat-docs-agent-tools/tree/main/plugins/docs-tools/agents) (for example a docs-tools persona) so the model follows that role or checklist for the task.

### Structured prompts

The following practices help reviewers and keep behavior aligned with the repo: state the goal, constraints (for example branch name, scope, no unrelated refactors), which fully qualified skill applies (`plugin:skill`), and which paths or file types to touch. Automation and human review expect fully qualified skill names; see [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md).

### Example structured prompt

Use a layout like the following when you want the assistant to apply **one named skill** to a **bounded set of paths** (for example before opening a pull request that only touches documentation under a plugin).

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
1. Propose edits to plugins/docs-tools/README.md that match the skill.
1. Give a short bullet list of changes suitable for a PR description.
```

You would paste or adapt that block in **Agent** mode after attaching the listed files (or their `@` references). The same pattern works for other skills and paths; replace the skill name, files, and constraints to match your task.

### No slash-command execution in Cursor

A larger task does not enable `/plugin:command`. Read command or agent Markdown, then drive the assistant with that content in the prompt or attached context. See [Cursor workflows](cursor-workflows.md) for the full picture.

### Privacy

Long-running threads with more context increase the chance of accidental paste errors. Do not put secrets or customer-only material into the chat; see [Privacy and responsibility](../get-started/cursor-fundamentals.md#privacy-and-responsibility).

### Checklist before you run a complex task

1. Attach or cite [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md).
1. Attach the relevant `SKILL.md`, command file, or agent file if the task must follow one of them.
1. State the goal, constraints, and fully qualified `plugin:skill` name in the prompt.

## Preview the documentation site

You do **not** need Zensical, `make`, or a local docs build to use Cursor with skills.

If you contribute changes that affect the published site, [README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md) and [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md) describe dependencies, `make update`, `make serve`, and `make build` from the repository root.

## Next steps for contributors

1. Read [Cursor workflows](cursor-workflows.md) for repository-specific behavior and parity with Claude Code.
1. Follow [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md) for branches, `plugin.json`, marketplace sync, and pull requests.

## Tips and troubleshooting

### Workspace path looks wrong

If paths in errors include an extra parent folder, or `@` search never finds `AGENTS.md`, you may have opened a directory **above** the repository root. Close the folder, then open the clone folder that contains **`AGENTS.md`**, **`plugins/`**, and **`README.md`** in one place. See [Open the repository as the workspace](#open-the-repository-as-the-workspace).

### Slash commands like `/hello-world:greet` do nothing

Expected in Cursor. Use command Markdown as prompts; see [Cursor workflows](cursor-workflows.md) and [Try a minimal workflow](#try-a-minimal-workflow).

### `make` or the local docs build fails

Run commands from the **repository root**
where the `Makefile` lives. See [README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md) and [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md) for dependencies and typical errors.

### The docs site shows a Mermaid diagram as plain code

See [README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md) and [`zensical.toml`](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/zensical.toml). Editor Markdown preview may not render Mermaid; use the local site or the published site for diagrams.

For other issues (skill names, Agent checkpoints, usage limits, Debug mode), see [Common tips and troubleshooting](../get-started/cursor-fundamentals.md#common-tips-and-troubleshooting).

## See also

- [Get Started with Cursor](../get-started/index.md) — section overview and guide links
- [Using Cursor with your product documentation](../get-started/cursor-product-documentation.md) — multi-root workspace with your docs repo
- [Cursor workflows](cursor-workflows.md) — parity with Claude Code
