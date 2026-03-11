---
icon: lucide/plus-circle
---

# Creating a new plugin

!!! warning "Check existing plugins first"
    Before creating a new plugin, verify that no existing plugin covers your use case. If similar functionality exists, contribute to that plugin instead. See the [plugin catalog](../plugins.md) or browse `plugins/` in the repo.

Create a new plugin only when your contribution represents a **genuinely distinct capability domain** that doesn't fit any existing plugin.

## Steps

1. Create a directory under `plugins/` with your plugin name (use kebab-case):

    ```bash
    plugins/my-plugin/
    ├── .claude-plugin/
    │   └── plugin.json
    ├── commands/
    │   └── my-command.md
    ├── skills/
    │   └── my-skill/
    │       └── SKILL.md
    ├── evals/
    │   └── evals.json
    └── README.md
    ```

2. Define `plugin.json` with metadata:

    ```json
    {
      "name": "my-plugin",
      "version": "1.0.0",
      "description": "What this plugin does",
      "author": {
        "name": "Your Name or Team",
        "email": "you@redhat.com"
      }
    }
    ```

3. Add commands as Markdown files in `commands/` with frontmatter:

    ```markdown
    ---
    description: "What this command does"
    argument-hint: "[optional-args]"
    ---

    # Command Name

    Your command prompt here.
    ```

4. Add skills as `SKILL.md` files in `skills/<skill-name>/`:

    ```markdown
    Your skill content — rules, checklists, domain knowledge
    that the agent applies automatically.
    ```

5. Write a `README.md` that explains:
    - What the plugin does
    - Prerequisites (tools, tokens, dependencies)
    - How to use each command and skill

6. Add evals in `evals/evals.json` with at least 2 test cases. See [Evaluating skills](evaluating-skills.md).

7. Test locally:

    ```bash
    make update
    make serve
    ```

## Reference implementation

Use `plugins/hello-world/` as a minimal reference for structure and conventions.
