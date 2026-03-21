---
icon: lucide/files
---

# Using Cursor with your product documentation

Use this guide when your AsciiDoc or Markdown source lives in a **different** Git repository from Red Hat Docs Agent Tools, and you want to run Agent Tools skills in Cursor.

## Checklist

1. Install Cursor and Git (see [Prerequisites](#prerequisites)).
1. Clone **Red Hat Docs Agent Tools** beside your docs repository and open both in a **multi-root workspace** (see [Set up the workspace](#set-up-the-workspace)).
1. Open the Agent panel, pick **Agent** mode, and attach **`AGENTS.md`** from the Agent Tools tree.
1. Attach the **`SKILL.md`** you need and write a prompt with the `plugin:skill` name and your file paths (see [Example prompt](#example-prompt)).
1. If something fails, see [Tips and troubleshooting](#tips-and-troubleshooting).

## Prerequisites

- Cursor is installed.
- Git is installed and can access your documentation repository and GitHub.
- You do **not** need `python3` or a local docs build to use skills on your product docs.

## Set up the workspace

Skills stay in the Agent Tools clone under `plugins/<plugin>/skills/`. Do not copy skill files into your docs repository.

### Clone both repositories

Place both repositories in a shared parent directory.

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

1. Use **File > Open Folder** and select your docs repository first.
1. Use **File > Add Folder to Workspace** and add `redhat-docs-agent-tools`.
1. Save the workspace when prompted so you can reopen both folders next time.

Confirm the sidebar shows **two** top-level roots.

### Attach files and write a prompt

1. Open a file from your docs repository in the editor.
1. In the Agent panel, type **`@`** and attach **`AGENTS.md`** from the **redhat-docs-agent-tools** root (next to `plugins/`, not from your docs tree).
1. Attach the skill file you need (for example `plugins/docs-tools/skills/rh-ssg-formatting/SKILL.md`).
1. Write your prompt using the `plugin:skill` name and repo-relative paths.

## Example prompt

Replace paths and the skill name with your actual file names.

```text
Context loaded: @AGENTS.md, @plugins/docs-tools/skills/rh-ssg-formatting/SKILL.md,
and my topic at modules/install/overview.adoc (path in the docs repo).

Task: Apply docs-tools:rh-ssg-formatting to modules/install/overview.adoc only.
List concrete issues first, then propose minimal edits. Do not change other modules.
```

Expect a short list of findings followed by proposed edits for the paths you named. Browse available skill names in the [Cursor skill index](../cursor-skills-index.md).

## Tips and troubleshooting

### Sidebar shows only one repository

Add the missing folder with **File > Add Folder to Workspace**, then save the workspace.

### Wrong `AGENTS.md` in the `@` picker

In a multi-root workspace, choose `AGENTS.md` under **`redhat-docs-agent-tools/`** next to `plugins/`, not a copy from your product docs.

### Privacy

Follow your team rules about putting product content in the assistant. If policy limits what may leave your network, use offline or approved workflows. See [Privacy and responsibility](cursor-fundamentals.md#privacy-and-responsibility).

For other issues (skill names, Agent checkpoints, usage limits, Debug mode), see [Common tips and troubleshooting](cursor-fundamentals.md#common-tips-and-troubleshooting).

## See also

- [Cursor fundamentals](cursor-fundamentals.md) — Agent panel, modes, and `plugin:skill` naming
- [Contributing with Cursor](../contribute/cursor-contributing-tools.md) — working inside the Tools repository
- [Cursor workflows](../contribute/cursor-workflows.md) — parity with Claude Code
