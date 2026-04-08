---
icon: lucide/terminal
---

# Get started with Claude Code

Claude Code installs plugins from a marketplace and runs namespaced commands directly in the terminal. The steps below walk through adding the Red Hat Docs Agent Tools marketplace, installing your first plugin, and running a command.

## Install from the marketplace

1. Add the marketplace:

    ```text
    claude plugin marketplace add redhat-documentation/redhat-docs-agent-tools
    ```

1. Install a plugin (using `hello-world` as an example):

    ```text
    claude plugin install hello-world@redhat-docs-agent-tools
    ```

1. Run a command:

    ```text
    hello-world:greet
    ```

## Install additional plugins

The marketplace contains six plugins. After adding the marketplace, install any plugin by name:

```text
claude plugin install docs-tools@redhat-docs-agent-tools
claude plugin install vale-tools@redhat-docs-agent-tools
claude plugin install dita-tools@redhat-docs-agent-tools
claude plugin install jtbd-tools@redhat-docs-agent-tools
claude plugin install cqa-tools@redhat-docs-agent-tools
```

To refresh marketplace listings and update installed plugins, run:

```text
claude plugin marketplace update redhat-docs-agent-tools
```

Browse the [plugin catalog](../plugins.md) for descriptions and skill lists for each plugin.

## Further reading

For installation scopes, updates, and troubleshooting, see the Anthropic [Discover and install plugins](https://docs.anthropic.com/en/docs/claude-code/discover-plugins) documentation for the `claude plugin` CLI and in-app plugin manager.
