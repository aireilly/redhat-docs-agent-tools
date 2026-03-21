# Red Hat Docs Agent Tools

**Red Hat Docs Agent Tools** is a collection of plugins, skills, commands, and agent definitions for Red Hat documentation workflows. **Claude Code** installs plugins with the `claude plugin` CLI and runs namespaced commands such as `hello-world:greet`. **Cursor** uses the repository on disk with project rules and `@` context. See [Get started with Cursor](#get-started-with-cursor) below.

## Quick start

### Install Agent Tools for Claude Code from the marketplace

```bash
# Add the marketplace
claude plugin marketplace add redhat-documentation/redhat-docs-agent-tools

# Install a plugin
claude plugin install hello-world@redhat-docs-agent-tools

# Refresh marketplace listings and installed plugins from this catalog
claude plugin marketplace update redhat-docs-agent-tools
```

For installation scopes, updates, and troubleshooting, see Anthropic’s [Discover and install plugins](https://docs.anthropic.com/en/docs/claude-code/discover-plugins) documentation for the **`claude plugin`** CLI and in-app plugin manager.

### Get started with Cursor

Cursor does not use the Claude Code marketplace. You work from a **local clone** (or copy) of this repository and load context with **`@`** and project rules.

1. Open the **repository root** as the Cursor workspace (the folder that contains `AGENTS.md`, `plugins/`, and `Makefile`). For docs in another repo, use a **multi-root** workspace.
1. Attach **[AGENTS.md](AGENTS.md)** in the Agent panel so the assistant follows the same naming and path rules as [CLAUDE.md](CLAUDE.md).
1. Read **[Get Started with Cursor](docs/get-started/index.md)** for fundamentals, product documentation workflows, and contributing guides.

### Available Claude Code plugins

Run `make update` to generate the plugin catalog locally, or browse the [live site](https://redhat-documentation.github.io/redhat-docs-agent-tools/).

## Documentation

The documentation site is built with [Zensical](https://zensical.org/) and auto-deployed to GitHub Pages on every merge to main.

### Live site

[Published documentation](https://redhat-documentation.github.io/redhat-docs-agent-tools/)

### Local development

```bash
# Install zensical
python3 -m pip install zensical

# Start dev server
make serve

# Build site
make build

# Regenerate plugin docs and Cursor skill index
make update
```

## Repository structure

```text
.
├── .github/workflows/     # CI: docs build + deploy on merge to main
├── .claude-plugin/        # Plugin marketplace configuration
├── docs/                  # Zensical site source (Markdown)
├── plugins/               # Plugin implementations (see plugin catalog for the full list)
│   ├── dita-tools/        # DITA and AsciiDoc conversion tools
│   ├── docs-tools/        # Documentation review, writing, and workflow tools
│   ├── hello-world/       # Reference plugin
│   ├── jtbd-tools/        # Jobs-to-be-done and research-oriented tools
│   └── vale-tools/        # Vale linting tools
├── scripts/               # Doc generation scripts
├── zensical.toml          # Zensical site config
├── Makefile               # Build automation
├── AGENTS.md              # Cursor project instructions (mirrors CLAUDE.md conventions)
├── .cursor/rules/         # Cursor rules for this repository
├── CLAUDE.md              # Claude Code project config
├── CONTRIBUTING.md        # Contribution guidelines
└── LICENSE                # Apache-2.0
```

## Contributing

Contributions are welcome from anyone using any editor or AI coding tool (including Cursor). See [CONTRIBUTING.md](CONTRIBUTING.md) and, for Cursor-specific workflows, [docs/contribute/cursor-workflows.md](docs/contribute/cursor-workflows.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
