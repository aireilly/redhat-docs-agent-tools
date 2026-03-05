---
icon: lucide/git-pull-request
---

# Contributing

Use the `hello-world` plugin as a reference implementation.

## Versioning

Bump the version in `plugin.json` when making changes:

- **Patch** (1.0.x): Bug fixes, documentation updates
- **Minor** (1.x.0): New commands, non-breaking changes
- **Major** (x.0.0): Breaking changes to existing commands

!!! tip
    Plugins use [semantic versioning](https://semver.org/). 

## Auto-generated docs

The following files are auto-generated and should not be edited manually:

- `plugins.md`
- `docs/plugins.md`
- `docs/installing/index.md`

These are regenerated on every merge to main via CI.

## Code review

All changes require a pull request with at least one approval.
