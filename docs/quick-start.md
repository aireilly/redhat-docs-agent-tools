---
icon: lucide/rocket
---

# Quick start

The following steps use **Claude Code** slash commands. If you use **Cursor** with
this repository, read [Get Started with Cursor](get-started/index.md)
and [Cursor fundamentals](get-started/cursor-fundamentals.md) first. Cursor does
not expose the same marketplace or slash-command surface.

1. Add the marketplace:

    ```text
    /plugin marketplace add https://github.com/redhat-documentation/redhat-docs-agent-tools.git
    ```

2. Install a plugin:

    ```text
    /plugin install hello-world@redhat-docs-agent-tools
    ```

3. Use a command:

    ```text
    /hello-world:greet
    ```
