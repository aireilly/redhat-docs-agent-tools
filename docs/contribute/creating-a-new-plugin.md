---
icon: lucide/plus-circle
---

# Creating a new plugin

1. Create a directory under `plugins/` with your plugin name (use kebab-case):

    ```bash
    plugins/my-plugin/
    ├── .claude-plugin/
    │   └── plugin.json
    ├── commands/
    │   └── my-command.md
    ├── evals/          # optional
    │   └── evals.json
    └── README.md
    ```

2. Define `plugin.json` with metadata:

    ```json
    {
      "name": "my-plugin",
      "version": "1.0.0",
      "description": "What this plugin does",
      "author": "github.com/your-username"
    }
    ```

3. Add commands as Markdown files in `commands/` with frontmatter:

    ```markdown
    ---
    description: "What this command does"
    argument-hint: "[optional-args]"
    ---

    # Name
    ...
    ```
