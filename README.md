# Red Hat Docs Agent Tools

A collection of Claude Code plugins, skills, and agent tools for Red Hat documentation workflows.

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

**Live site:** https://redhat-documentation.github.io/redhat-docs-agent-tools/

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

```
.
├── .github/workflows/     # CI: docs build + deploy on merge to main
├── .claude-plugin/        # Plugin marketplace configuration
├── docs/                  # Zensical site source (Markdown)
├── plugins/               # Plugin implementations
│   └── hello-world/       # Reference plugin
├── scripts/               # Doc generation scripts
├── zensical.toml          # Zensical site config
├── Makefile               # Build automation
├── CLAUDE.md              # Claude Code project config
├── CONTRIBUTING.md        # Contribution guidelines
├── PLUGINS.md             # Auto-generated plugin catalog
└── LICENSE                # Apache-2.0
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on creating plugins and submitting changes.

## License

Apache-2.0. See [LICENSE](LICENSE).
