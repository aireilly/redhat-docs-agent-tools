---
icon: lucide/git-pull-request
---

# Contributing

This repository is a collection of plugins for Red Hat documentation workflows. Contributions are primarily Markdown files — skills, reference material, checklists, and style guides — that can be authored in any editor or AI coding tool. Contributions are welcome from anyone in the community.

For the full contributor guide, see [CONTRIBUTING.md](https://github.com/redhat-documentation/redhat-docs-agent-tools/blob/main/CONTRIBUTING.md).

If you use **Cursor**, start with [Get Started with Cursor](../get-started/index.md) and [Cursor fundamentals](../get-started/cursor-fundamentals.md). Then pick the guide that matches your task:

- [Product documentation](../get-started/cursor-product-documentation.md) — your docs live in another repository.
- [Contributing with Cursor](cursor-contributing-tools.md) — you are editing plugins in this repository.
- [Cursor workflows](cursor-workflows.md) — parity between Cursor and Claude Code.

## Key principles

### Extend, don't duplicate

Before creating a new plugin, skill, or command, check whether the capability already exists. If it does, improve the existing one rather than creating a parallel version. Duplicate capabilities fragment the user experience and increase maintenance burden.

### One capability per PR

Keep pull requests focused. Each PR should add or modify a single skill, command, or agent. Don't bundle unrelated changes.

### Test your work

Every skill and command should include evals that demonstrate it works. See [Evaluating skills](evaluating-skills.md) for how to write and run tests. If you cannot run evals, describe how reviewers can verify the capability works.

### Open an issue first

For anything beyond trivial fixes, open an issue to discuss your contribution before writing code. This prevents wasted effort.

## What's accepted

- Capabilities useful to the broader Red Hat documentation community
- Non-duplicative additions or improvements to existing plugins
- Well-tested skills and commands with evals
- Clear, focused, well-documented contributions

## What's not accepted

- Duplicates of existing capabilities
- Personal or single-team-specific tooling
- Contributions without any form of testing or demonstration
- Overly broad or vague capabilities
- Dependencies that aren't accessible to the community

## Contribution types

| Type | When to use | Location |
| --- | --- | --- |
| **Skill** | Reusable knowledge, checklists, style rules, or domain expertise | `plugins/<plugin>/skills/<name>/SKILL.md` |
| **Command** | User-invokable action (`plugin:command` after install in Claude Code) | `plugins/<plugin>/commands/<name>.md` |
| **Agent** | Specialized agent persona with a defined role | `plugins/<plugin>/agents/<name>.md` |
| **Reference** | Static reference material for skills or agents | `plugins/<plugin>/reference/<name>.md` |
| **New plugin** | A genuinely new capability domain | `plugins/<new-plugin>/` |

Most contributions are additions to existing plugins. Create a new plugin only when your contribution represents a distinct capability domain.

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
- `docs/install/index.md`

These are regenerated on every merge to main via CI.

## Code review

All changes require a pull request with at least one approval. Keep PRs small, focused, and self-reviewed before requesting review.
