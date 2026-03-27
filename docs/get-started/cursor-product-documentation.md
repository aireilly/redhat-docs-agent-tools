---
icon: lucide/files
---

# Using Cursor with your product documentation

Follow this workflow when your AsciiDoc or Markdown source lives in a **different** Git
repository from Red Hat Docs Agent Tools and you want to apply Agent Tools skills in Cursor. The
[Cursor documentation](https://cursor.com/docs) describes how to open folders, use multi-root
workspaces, and attach context in the editor.

## Prerequisites

Confirm the following before you rely on skills during a session:

- **Environment** — Cursor is installed. Git is installed and can reach your documentation
  repository and GitHub. You do **not** need `python3` or a local docs build in the Agent Tools
  clone to run skills against your product documentation.
- **Workspace** — You have cloned both repositories (Agent Tools and your documentation source) to your local disk, and the Cursor workspace shows the root directory of both repos (see
  [Set up the workspace](#set-up-the-workspace)).
- **Context** — You have attached `AGENTS.md` from the Agent Tools clone and the correct
  `SKILL.md` for your task (see [Attach files and write a prompt](#attach-files-and-write-a-prompt)).
- **Prompting** — You know how to refer to a fully qualified `plugin:skill` and repo-relative paths in
  your prompt (see [Example prompt](#example-prompt)).
- **Cursor product** — You picked an assistant mode that allows the agent to make edits (see [Where to learn the
  Cursor interface](cursor-fundamentals.md#where-to-learn-the-cursor-interface)).

## Procedure overview

The end-to-end flow has three parts. Each part links to a section with concrete steps.

1. **Prepare disk and workspace** — Clone both repositories into a shared parent directory, then
   open a multi-root workspace so Cursor lists both folder roots. See [Set up the
   workspace](#set-up-the-workspace).
1. **Attach context and prompt** — Add `AGENTS.md` and the skill file from the Agent Tools tree,
   then write a prompt with `plugin:skill` and paths. See [Attach files and write a
   prompt](#attach-files-and-write-a-prompt) and [Example prompt](#example-prompt).
1. **Find skill names** — Use the `plugins/` tree in the clone or the published plugin catalog
   when you need a skill ID. See the note under [Example prompt](#example-prompt).

## Set up the workspace

Skills stay in the Agent Tools clone under `plugins/<plugin>/skills/`. Skill files are **not** copied into your docs repository.

### Clone both repositories

Clone both repositories into sub-directories below a shared parent directory.

```text
~/repos/
  my-product-docs/          # your documentation repository
  redhat-docs-agent-tools/  # Agent Tools plugins and skills
```

```bash
mkdir -p ~/repos && cd ~/repos
git clone https://github.com/your-org/my-product-docs.git
git clone https://github.com/redhat-documentation/redhat-docs-agent-tools.git
```

### Open a multi-root workspace

Open a **multi-root** workspace in Cursor so both clones appear in the sidebar. VS Code’s workspace documentation applies to Cursor for adding folders. See [Multi-root workspaces](https://code.visualstudio.com/docs/editor/workspaces#_multiroot-workspaces) in the Visual Studio Code documentation.

### Attach files and write a prompt

1. Open a file from your docs repository in the editor.
1. Add [AGENTS.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/AGENTS.md) from the **redhat-docs-agent-tools** root (next to `plugins/`, not from your product tree) to the chat using the method described in the Cursor documentation for file context.
1. Add the skill file you need (for example `plugins/docs-tools/skills/rh-ssg-formatting/SKILL.md`).
1. Write your prompt with the `plugin:skill` name and paths relative to your docs repository root.

## Example prompt

Replace paths and the skill name with your actual file names.

```text
Context loaded: @AGENTS.md, @plugins/docs-tools/skills/rh-ssg-formatting/SKILL.md,
and my topic at modules/install/overview.adoc (path in the docs repo).

Task: Apply docs-tools:rh-ssg-formatting to modules/install/overview.adoc only.
List concrete issues first, then propose minimal edits. Do not change other modules.
```

Expect the Cursor agent to provide its findings followed by proposed edits for the paths you named. To find skill names and descriptions, browse **`plugins/<plugin>/skills/`** in the Agent Tools clone, or open the **Browse plugins** section on the [published site](https://redhat-documentation.github.io/redhat-docs-agent-tools/) **Overview** or run `make update` locally and read **`docs/plugins.md`**.

## Privacy

Follow your team rules about putting product content in the assistant. If policy limits what may leave your network, use offline or approved workflows. See [Privacy and responsibility](cursor-fundamentals.md#privacy-and-responsibility).

For other issues (skill names, checkpoints, usage limits), see [Common tips and troubleshooting](cursor-fundamentals.md#common-tips-and-troubleshooting).

## See also

- [Cursor fundamentals](cursor-fundamentals.md) — repository rules and `plugin:skill` naming
- [Contributing with Cursor](../contribute/cursor-contributing-tools.md) — working inside the Tools repository
- [Cursor workflows](../contribute/cursor-workflows.md) — parity with Claude Code
