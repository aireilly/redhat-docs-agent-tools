---
icon: lucide/files
---

# Using Cursor with your product documentation

This guide is for people who edit AsciiDoc or Markdown in a separate Git
repository and want to apply skills from Red Hat Docs Agent Tools in Cursor.

Read [Cursor fundamentals](cursor-fundamentals.md) first to learn about the Agent
panel, `AGENTS.md`, `@` mentions, and `plugin:skill` names. For an overview, see
[Get Started with Cursor](index.md).

## Start here

### Checklist

1. Meet the [Prerequisites](#prerequisites): install Cursor and Git.
1. Clone **Red Hat Docs Agent Tools** beside your product documentation repository
   and open a **multi-root** workspace in Cursor. See [Use a skill in your
   documentation repository](#use-a-skill-in-your-documentation-repository).
1. Open Cursor. Open the **Agent** panel and pick **Agent** mode and a model (see
   [Orient yourself in the
   UI](cursor-fundamentals.md#orient-yourself-in-the-ui)).
1. Attach **`AGENTS.md`** from the **redhat-docs-agent-tools** tree before substantive
   edits. See [Load project
   instructions](cursor-fundamentals.md#load-project-instructions).
1. Attach the relevant **`SKILL.md`**, scope paths under your docs root, and use
   a `plugin:skill` name in the prompt. See the example prompt below. Browse names
   in the [Cursor skill index](../cursor-skills-index.md).
1. If something fails, see [Tips and troubleshooting](#tips-and-troubleshooting).

## Prerequisites

- You have installed Cursor.
- You have installed Git and it has access to your documentation repository (and
  to GitHub if you clone Agent Tools from there).
- You do **not** need `python3` or a local docs build in the Tools repo to use
  skills on your product docs.

## Use a skill in your documentation repository

Read [Cursor fundamentals](cursor-fundamentals.md) first. The steps below assume
you already use **Agent** mode and `@` to attach files.

Your product documentation usually sits in its own Git repository.

The skills you want live only in a clone of the Red Hat Docs Agent Tools repo, under
`plugins/<plugin>/skills/`.

You **do not** copy those skill files into your docs repo. That is, you do not
change the docs repo layout to “install” skills from the Agent Tools repo.

However, you **can** keep both folders in a single Cursor multi-root workspace so
that you can attach the skill files (and `AGENTS.md` when needed) in the chat
panel. The assistant can then use them while you edit AsciiDoc, Markdown, or other
doc sources in the product repo.

### Recommended layout: multi-root workspace

1. **Clone both repositories to your local disk.** Clone
    [redhat-docs-agent-tools](https://github.com/redhat-documentation/redhat-docs-agent-tools)
    so the skill sources exist locally.

    1. Use a shared parent directory with two sibling folders (for example the
        layout below).

        ```text
        ~/repos/
          my-product-docs/          # your documentation repository
          redhat-docs-agent-tools/  # Agent Tools plugins and skills
        ```

    1. On Linux or macOS, run commands such as the following (adjust URLs and
        paths to match your forks and directories).

        ```bash
        mkdir -p ~/repos && cd ~/repos
        git clone https://github.com/your-org/my-product-docs.git
        git clone https://github.com/redhat-documentation/redhat-docs-agent-tools.git
        ```

1. **Open a multi-root workspace in Cursor.**

    1. Use **File** → **Open Folder** and select `~/repos/my-product-docs` (or your
        real docs path) first.
    1. Use **File** → **Add Folder to Workspace** and add
        `~/repos/redhat-docs-agent-tools`.
    1. Save the workspace if prompted (for example **File** → **Save Workspace As**
        → `my-docs-and-tools.code-workspace`) so you can reopen both folders next
        time.
    1. In the sidebar, confirm **two** top-level roots, often labeled with the
        folder names `my-product-docs` and `redhat-docs-agent-tools`.

1. **Open a file from your docs repo.** For example open
    `modules/install/overview.adoc`, `assemblies/assembly-about.adoc`, or `README.md`
    at the root of `my-product-docs`. The path depends on your project. The file
    must be located under **your** documentation tree, not under
    `redhat-docs-agent-tools/`.

1. **Attach Agent Tools repo files in Agent mode.**

    1. Switch to **Agent** mode. In the message box, type **`@`**.
    1. Attach **`AGENTS.md`** from the **redhat-docs-agent-tools** root (if the
        picker shows a prefix, choose the copy that lives next to `plugins/`, not a
        file from your product docs).
    1. Attach the skill file you need, for example
        `plugins/docs-tools/skills/rh-ssg-formatting/SKILL.md`, from the
        **redhat-docs-agent-tools** tree.
    1. If the menu lists workspace folder names, select paths that start with
        **`redhat-docs-agent-tools/`**. Attach your content file the same way (for
        example `my-product-docs/modules/install/overview.adoc`) if it is not
        already open in the editor context.

1. **Enter a prompt with `plugin:skill` and your paths.**

    1. Name the fully qualified skill and paths under **your** docs repo root, as
        in the example block below. Use repo-relative paths (for example
        `modules/install/overview.adoc`) so the assistant edits the correct file.
    1. When you need a `plugin:skill` name, browse the [Cursor skill
        index](../cursor-skills-index.md) or under `plugins/` in the clone.

### Example prompt (AsciiDoc or Markdown topic)

Use a pattern such as the following; replace paths and the skill with your actual
file names and `plugin:skill` name:

```text
Context loaded: @AGENTS.md, @plugins/docs-tools/skills/rh-ssg-formatting/SKILL.md,
and my topic at modules/install/overview.adoc (path in the docs repo).

Task: Apply docs-tools:rh-ssg-formatting to modules/install/overview.adoc only.
List concrete issues first, then propose minimal edits. Do not change other modules.
```

### Expected result

The assistant should respond with a short list of findings or
questions, then proposed edits (or diffs) scoped to the paths you named—not a
whole-repo rewrite unless you asked for one.

If your documentation uses a different structure, keep the same idea: **load the
skill and AGENTS.md from the Tools tree**, **point at one or more paths in your docs
repo**, and **name the skill** as `plugin:skill` in the prompt.

### Privacy

Follow your team rules for putting product or customer content in the
assistant. If policy limits what may leave your network, use offline or approved
workflows; see [Privacy and
responsibility](cursor-fundamentals.md#privacy-and-responsibility).

## Tips and troubleshooting

### Sidebar shows only one repository

You wanted a multi-root workspace but only
added one folder. Use **File** → **Add Folder to Workspace**, add
`redhat-docs-agent-tools` (or your docs repo) as the second root, and save the
workspace. See [Use a skill in your documentation
repository](#use-a-skill-in-your-documentation-repository).

### Wrong `AGENTS.md` in the `@` picker

In a multi-root workspace, pick the file
under **`redhat-docs-agent-tools/`** next to `plugins/`, not a file from your
product docs repo.

For other issues (skill names, Agent checkpoints, usage limits, Debug mode), see
[Common tips and
troubleshooting](cursor-fundamentals.md#common-tips-and-troubleshooting).

## See also

- [Get Started with Cursor](index.md) — section overview and guide links
- [Contributing with Cursor](../contribute/cursor-contributing-tools.md) — working
  inside the Tools repository
- [Cursor workflows](../contribute/cursor-workflows.md) — parity with Claude Code
