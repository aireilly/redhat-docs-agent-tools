---
icon: lucide/git-branch
---

# Contributing with Cursor

Use this guide when you clone **Red Hat Docs Agent Tools** to contribute skills, plugins, commands, or documentation under `plugins/`. Read [Cursor fundamentals](../get-started/cursor-fundamentals.md) first.

## Checklist

1. Install Cursor, Git, and optionally `python3` for repository tooling (see [Prerequisites](#prerequisites)).
1. Clone and open the [repository root](#open-the-repository-as-the-workspace).
1. Open the **Agent** panel, pick **Agent** mode, and attach **`AGENTS.md`**.
1. Try a [minimal workflow](#try-a-minimal-workflow) or [invoke a more complex workflow](#invoke-a-more-complex-workflow).
1. Follow [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md) for branches, `plugin.json`, and pull requests.

## Prerequisites

- Cursor and Git are installed.
- `python3` is installed if you plan to run repository tooling (for example `make update`).

## Open the repository as the workspace

1. Clone the upstream repository or your fork:

   ```bash
   git clone https://github.com/redhat-documentation/redhat-docs-agent-tools.git
   ```

1. In Cursor, use **File > Open Folder** and select the **repository root** (the folder that contains `Makefile`, `AGENTS.md`, and `plugins/`).

To run `git`, `make`, or `python3` commands, open **Terminal > New Terminal** and confirm the shell is in the repository root.

## Try a minimal workflow

1. Open `plugins/hello-world/commands/greet.md` and read the **Implementation** and **Examples** sections. Cursor cannot run `hello-world:greet` as a slash command, so use the text as the basis for a prompt.
1. Or open any `SKILL.md` under `plugins/docs-tools/skills/` and ask the assistant to summarize when the skill applies, using the fully qualified `docs-tools:<skill-name>` form.

## Invoke a more complex workflow

Use the following approach when work spans multiple files or may run terminal commands.

### Layer context deliberately

Before you start:

1. Attach [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) for repository-wide rules (for example `@AGENTS.md`).
1. Attach the relevant `SKILL.md` under `plugins/<plugin>/skills/` when output must follow a named skill.
1. Optionally attach a **command** or **agent** file under `plugins/<plugin>/` when you want ordered steps or a persona for the session.

### Example structured prompt

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

Paste or adapt that block in **Agent** mode after attaching the listed files. Replace the skill name, files, and constraints to match your task.

### Slash commands do not run in Cursor

Read command or agent Markdown and drive the assistant with that content in the prompt. See [Cursor workflows](cursor-workflows.md) for more detail.

## Preview the documentation site

You do **not** need Zensical or a local docs build to use Cursor with skills. If your changes affect the published site, see [README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md) for `make update`, `make serve`, and `make build`.

## Tips and troubleshooting

### Workspace path looks wrong

If `@` search never finds `AGENTS.md`, you may have opened a directory **above** the repository root. Close the folder, then open the clone folder that contains `AGENTS.md`, `plugins/`, and `README.md`.

### `make` or the local docs build fails

Run commands from the **repository root** where the `Makefile` lives. See [README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md) for dependencies and typical errors.

For other issues (skill names, Agent checkpoints, usage limits, Debug mode), see [Common tips and troubleshooting](../get-started/cursor-fundamentals.md#common-tips-and-troubleshooting).

## See also

- [Cursor fundamentals](../get-started/cursor-fundamentals.md) — Agent panel, modes, and `plugin:skill` naming
- [Product documentation workflow](../get-started/cursor-product-documentation.md) — multi-root workspace with your docs repo
- [Cursor workflows](cursor-workflows.md) — parity with Claude Code
