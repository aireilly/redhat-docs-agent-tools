---
icon: lucide/git-branch
---

# Contributing with Cursor

<!-- markdownlint-disable MD013 -->

Use this workflow when you clone **Red Hat Docs Agent Tools** to contribute skills,
plugins, commands, or documentation under `plugins/`. Read
[Cursor fundamentals](../get-started/cursor-fundamentals.md) first. The
[Cursor documentation](https://cursor.com/docs) describes how to open a folder, use the
terminal, and attach context.

## Prerequisites

Confirm the following before you start substantive edits:

- [ ] **Environment** — You have installed Cursor and Git. If you plan to run
  repository tooling (for example `make update` or other Makefile targets from the repository root),
  you have installed `python3`.
- [ ] **Workspace** — The [repository root](#open-the-repository-as-the-workspace) is the
  workspace folder (it contains `Makefile`, `AGENTS.md`, and `plugins/`).
- [ ] **Rules in context** — You have attached
  [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md)
  when the task affects plugins, skills, or contribution conventions.
- [ ] **Contribution policy** — You have reviewed
  [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md)
  for branches, `plugin.json`, marketplace sync, and pull requests.

## Procedure overview

The usual workflow has four parts. Each part links to a section with concrete steps.

1. **Open the clone** — Clone the upstream Agent Tools repository or a fork, then open the repository root in Cursor. See
   [Open the repository as the workspace](#open-the-repository-as-the-workspace).
1. **Try a small task** — Run a [minimal workflow](#try-a-minimal-workflow) to confirm skills and
   project rules work with attached context.
1. **Scale up** — For larger changes,
   [invoke a more complex workflow](#invoke-a-more-complex-workflow) (layer `SKILL.md`, command,
   or agent files as needed).
1. **Ship changes** — Follow
   [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md)
   for tests, `make update` when required, and the pull request. See [Preview the documentation
   site](#preview-the-documentation-site) when your change affects the published site.

## Open the repository as the workspace

1. Clone the upstream repository (or, alternatively, your fork):

   ```bash
   git clone https://github.com/redhat-documentation/redhat-docs-agent-tools.git
   ```

1. In Cursor, open the **repository root** folder (the directory that contains `Makefile`,
   `AGENTS.md`, and `plugins/`). See the [Cursor documentation](https://cursor.com/docs) for opening
   folders.

To run `git`, `make`, or `python3` commands, you can use the integrated terminal in the Cursor
UI. Confirm that the shell’s current directory is the repository root before running
commands.

## Try a minimal workflow

Start with a **skill** and `@` attachments. Cursor does not run `plugin:command` entries the way
Claude Code does. For how commands differ, see [Cursor workflows](cursor-workflows.md).

1. Attach [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md)
   from the repository root (for example with `@` per the [Cursor documentation](https://cursor.com/docs)).
1. Attach one skill file, for example
   [`plugins/docs-tools/skills/rh-ssg-formatting/SKILL.md`](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/plugins/docs-tools/skills/rh-ssg-formatting/SKILL.md).
1. Ask a narrow question that uses the fully qualified name `docs-tools:rh-ssg-formatting`, for
   example to summarize when the skill applies or to name one checklist area from the skill.

Example prompt:

```text
@AGENTS.md @plugins/docs-tools/skills/rh-ssg-formatting/SKILL.md

Summarize when docs-tools:rh-ssg-formatting applies. List two checklist areas from the skill.
```

To reuse **Implementation** steps from a **command** file instead, open the command Markdown under
`plugins/<plugin>/commands/` and use that text as the prompt. See [Cursor workflows](cursor-workflows.md).

## Invoke a more complex workflow

Use the following approach when work spans multiple files or may run terminal commands.

### Layer context deliberately

Before you start:

1. Attach
   [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md)
   for repository-wide rules (for example `@AGENTS.md` where the product supports it).
1. Attach the relevant `SKILL.md` under `plugins/<plugin>/skills/` when output must follow a named
   skill.
1. Optionally attach a **command** or **agent** file under `plugins/<plugin>/` when you want ordered
   steps or a persona for the session.

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

Paste or adapt that block after attaching the listed files. Replace the skill name, files, and
constraints to match your task.

## Preview the documentation site

You do **not** need Zensical or a local docs build to use Cursor with skills. If your changes
affect the published site, see
[README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md) for
`make update`, `make serve`, and `make build`.

## Tips and troubleshooting

### Workspace path looks wrong

If context search never finds `AGENTS.md`, you may have opened a directory **above** the repository
root. Close the folder, then open the clone folder that contains `AGENTS.md`, `plugins/`, and
`README.md`.

### `make` or the local docs build fails

Run commands from the **repository root** where the `Makefile` lives. See
[README.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/README.md) for
dependencies and typical errors.

For other issues (skill names, checkpoints, usage limits), see [Common tips and
troubleshooting](../get-started/cursor-fundamentals.md#common-tips-and-troubleshooting).

## See also

- [Cursor fundamentals](../get-started/cursor-fundamentals.md) — repository rules and `plugin:skill`
  naming
- [Product documentation workflow](../get-started/cursor-product-documentation.md) — multi-root
  workspace with your docs repo
- [Cursor workflows](cursor-workflows.md) — parity with Claude Code
