# Red Hat Docs Agent Tools

A collection of Claude Code plugins, skills, and agent tools for Red Hat documentation workflows. Cursor users can start with [Get Started with Cursor](docs/get-started/index.md), then use [AGENTS.md](AGENTS.md) and [docs/contribute/cursor-workflows.md](docs/contribute/cursor-workflows.md).

## Quick start

### Install from marketplace

```bash
# Add the marketplace
/plugin marketplace add https://github.com/redhat-documentation/redhat-docs-agent-tools.git

# Install a plugin
/plugin install hello-world@redhat-docs-agent-tools

# Update all plugins
/plugin marketplace update redhat-docs-agent-tools
```

### Available plugins

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

# Regenerate plugin docs
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
