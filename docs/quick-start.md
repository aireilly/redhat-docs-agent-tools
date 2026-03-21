---
icon: lucide/rocket
---

# Quick start

The steps below use the **Claude Code** `claude plugin` CLI. For Cursor, see [Get Started with Cursor](get-started/index.md).

1. Add the marketplace:

    ```text
    claude plugin marketplace add redhat-documentation/redhat-docs-agent-tools
    ```

1. Install a plugin:

    ```text
    claude plugin install hello-world@redhat-docs-agent-tools
    ```

1. Use a command:

    ```text
    hello-world:greet
    ```
