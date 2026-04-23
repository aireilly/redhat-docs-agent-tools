# Contributing to Red Hat Docs Agent Tools

This repository is a collection of plugins, skills, agents, and commands for Red Hat documentation workflows. The plugin format targets Claude Code, but contributions are primarily Markdown files — skills, reference material, checklists, and style guides — that can be authored in any editor or AI coding tool. Contributions are welcome from anyone in the Red Hat documentation community.

This guide helps you contribute effectively and helps maintainers review efficiently.

## Cursor users

Cursor users follow the same conventions as Claude Code contributors. Start with these resources:

- **[AGENTS.md](AGENTS.md)** — Shared skill naming, script paths, and contributing rules. [CLAUDE.md](CLAUDE.md) covers Claude Code-only details (for example cross-skill `${CLAUDE_PLUGIN_ROOT}` paths).
- **[Get Started with Cursor](docs/get-started/index.md)** — Fundamentals, product documentation workflows, and contributing guides.
- **[Cursor workflows](docs/contribute/cursor-workflows.md)** — How skills, commands, and evals map to Cursor.

In Cursor, use paths relative to the repository root instead of `${CLAUDE_PLUGIN_ROOT}`. See AGENTS.md for examples. The eval runner described in [Evaluating skills](docs/contribute/evaluating-skills.md) is a Claude Code tool. If you use Cursor, keep `evals/evals.json` accurate and explain in your pull request how reviewers can verify behavior.

## Branch policy

This repository uses two long-lived branches:

- **`main`** — CLI-focused. All plugin, skill, agent, and script development targets `main` via pull request.
- **`acp`** — Ambient Code Platform integration branch. Carries ACP-specific files (`adapters/ambient/`, `.ambient/`, `.claude/skills/` symlinks, `.claude/docs-acp.yaml`, batch-controller) on top of everything in `main`.

A GitHub Actions workflow automatically merges `main` into `acp` on every push, so `acp` always has the latest plugin and skill updates.

**Rules:**

- PRs that change plugins, skills, agents, scripts, or CI target **`main`**.
- PRs that change ACP-only files (adapters, batch-controller, `.ambient/`, ACP workflow config) target **`acp`**.
- Never edit shared files (plugins, skills, agents, scripts) directly on `acp` — those changes must flow through `main`.

## Before you contribute

### Check for existing capabilities

Before creating something new, search the existing plugins to see if your use case is already covered:

1. Browse the [plugin catalog](https://redhat-documentation.github.io/redhat-docs-agent-tools/) or run `make update` locally.
2. Read the README, commands, skills, and agents in each plugin under `plugins/`.
3. Search for keywords related to your capability using `grep -r "your-keyword" plugins/`.

#### If similar functionality already exists

Contribute to the existing plugin rather than creating a new one. For example:

- A new AsciiDoc linting rule belongs in `vale-tools`, not in a new plugin.
- A new documentation review checklist belongs in `docs-tools`, not in a new plugin.
- A Google Docs conversion improvement belongs in the existing `docs-convert-gdoc-md` skill, not in a parallel skill.

Duplicate capabilities fragment the user experience and increase the maintenance burden. Pull requests that duplicate existing functionality will be asked to merge into the existing capability instead.

### Decide what type of contribution to make

| Type | When to use | Location |
| --- | --- | --- |
| **Skill** | Reusable knowledge, checklists, style rules, or domain expertise that the agent applies automatically | `plugins/<plugin>/skills/<skill-name>/SKILL.md` |
| **Command** | A user-invokable action (`plugin-name:command` after install in Claude Code) | `plugins/<plugin>/commands/<command>.md` |
| **Agent** | A specialized agent persona with a defined role and workflow | `plugins/<plugin>/agents/<agent>.md` |
| **Reference** | Static reference material that skills or agents can consult | `plugins/<plugin>/reference/<ref>.md` |
| **New plugin** | A genuinely new capability domain that doesn't fit any existing plugin | `plugins/<new-plugin>/` |

Create a new plugin only when your contribution represents a distinct capability domain. Most contributions should be additions to an existing plugin.

## What will be accepted

Contributions are accepted when they meet **all** of the following criteria:

- **Useful to the Red Hat documentation community.** The capability addresses a real workflow need shared by multiple documentation teams or contributors.
- **Non-duplicative.** No existing skill, command, or agent already covers the same use case.
- **Tested where possible.** Skills and commands should include evals that demonstrate the capability works as described (see [Evaluating skills](docs/contribute/evaluating-skills.md)). If you cannot run evals, describe how reviewers can verify the capability works.
- **Well-scoped.** Each skill, command, or agent does one thing well. Avoid monolithic capabilities that try to do everything.
- **Documented.** The plugin README explains what it does, any prerequisites, and how to use it. Commands and skills have clear descriptions.
- **Follows conventions.** Uses the repo structure, naming conventions, and patterns described below.

## What will not be accepted

- **Duplicates of existing capabilities.** If a skill for AsciiDoc review already exists, don't create another one. Improve the existing one.
- **Personal or team-specific tooling.** If a capability is only useful to one person or one team's private workflow, maintain it in your own fork or a separate marketplace.
- **Contributions without any form of testing or demonstration.** Evals are strongly encouraged; if you cannot run them, describe how reviewers can verify the capability works.
- **Overly broad or vague capabilities.** A skill called "improve docs" with no specific guidance is not useful. Be specific about what the skill does and when it applies.
- **Capabilities that require proprietary or inaccessible dependencies.** All prerequisites must be available to the broader Red Hat documentation community.
- **Changes that break existing functionality.** If your change modifies an existing skill or command, ensure backward compatibility or clearly document the breaking change with a major version bump.

## Contribution workflow

### 1. Open an issue first

For anything beyond trivial fixes, open an issue to discuss your contribution before writing code. Describe:

- What capability you want to add or change
- Why it's needed
- Whether it overlaps with anything existing

This prevents wasted effort on contributions that won't be accepted.

### 2. Fork and branch

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/<your-username>/redhat-docs-agent-tools.git
cd redhat-docs-agent-tools
git checkout -b my-contribution
```

### 3. Make your changes

Follow the structure and conventions below. Use `plugins/hello-world/` as a reference implementation.

### 4. Test locally

```bash
# Regenerate docs to verify your plugin is picked up
make update

# Preview the site
make serve
```

If you can run evals, test your skill or command using the eval runner described in [Evaluating skills](docs/contribute/evaluating-skills.md).

### 5. Submit a pull request

- Write a clear PR title and description.
- Reference the issue you opened.
- Include eval results (benchmark output or a summary of test outcomes).
- Keep the PR focused: one capability per PR. Don't bundle unrelated changes.

## Plugin structure

```text
plugins/<plugin-name>/
├── .claude-plugin/
│   └── plugin.json          # Required: name, version, description, author
├── commands/
│   └── <command>.md         # User-invokable commands
├── skills/
│   └── <skill-name>/
│       └── SKILL.md         # Skill definitions
├── agents/
│   └── <agent>.md           # Agent definitions
├── reference/
│   └── <ref>.md             # Reference material
├── evals/
│   └── evals.json           # Test cases
└── README.md                # Required: what the plugin does, prerequisites, usage
```

### plugin.json

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Brief description of what this plugin does",
  "author": {
    "name": "Your Name or Team",
    "email": "you@redhat.com"
  }
}
```

### Naming conventions

- **Plugin names:** kebab-case (`my-plugin`, not `myPlugin` or `my_plugin`)
- **Command names:** kebab-case (`my-command.md`)
- **Skill directories:** kebab-case (`my-skill-name/SKILL.md`)
- **Agent names:** kebab-case (`my-agent.md`)

### Versioning

Plugins follow [semantic versioning](https://semver.org/). Bump the version in `plugin.json` with every change:

- **Patch** (0.0.x): Bug fixes, typo corrections, documentation updates
- **Minor** (0.x.0): New commands, skills, or agents; non-breaking changes
- **Major** (x.0.0): Breaking changes to existing commands, skills, or agents

## Writing good skills

Skills are the most common contribution type. A good skill:

- **Has a clear trigger description.** The description tells the agent exactly when to activate the skill. Be specific about input types, file formats, or contexts.
- **Provides actionable guidance.** Don't just describe what to do; provide the rules, checklists, or templates the agent should follow.
- **Focuses on one concern.** A skill for "AsciiDoc structure validation" is better than a skill for "everything about AsciiDoc."
- **Is grounded in authoritative sources.** Reference official style guides, standards, or documented team practices — not personal preferences.

## Writing good commands

Commands are user-invokable actions. A good command:

- **Has a clear description in frontmatter.** The `description` field tells users what the command does before they run it.
- **Uses `argument-hint` to document expected input.** Show users what arguments the command accepts.
- **Produces consistent output.** The same input should produce the same output. Write evals to verify this.

## Writing good agents

Agents are specialized personas. A good agent:

- **Has a defined role and scope.** "You are a technical reviewer who checks for..." is better than "You help with docs."
- **Delegates to existing skills.** Agents should reference and use skills from the same plugin or other installed plugins, rather than inlining duplicate logic.
- **Has a clear workflow.** Describe the steps the agent follows, in order.

## Writing evals

Every skill and command should include evals where possible. See [Evaluating skills](docs/contribute/evaluating-skills.md) for the full guide.

At minimum, your `evals/evals.json` should include:

- At least 2 test cases covering normal usage
- Assertions that are **discriminating** — they pass with the skill and fail without it
- Descriptive assertion names that explain what's being tested

## Auto-generated files

These files are built by CI on merge to `main` and are gitignored:

- `docs/plugins.md`
- `docs/plugins/` (per-plugin catalog pages)
- `docs/install/` (install documentation)

Run `make update` locally to preview them. Do not commit them.

## Code review expectations

To keep reviews manageable:

- **One capability per PR.** Don't add three skills and two commands in a single PR.
- **Small, focused diffs.** Reviewers should be able to understand the full change in a single sitting.
- **Self-review first.** Before requesting review, re-read your own diff. Check for typos, formatting issues, and adherence to conventions.
- **Respond to feedback promptly.** Stale PRs that go unresponsive for more than 2 weeks may be closed.

## Getting help

- Open an issue with questions about contribution scope or approach.
- Use the `hello-world` plugin as a reference for structure and conventions.
- Review existing plugins to understand the patterns in use.

## License

By contributing, you agree that your contributions will be licensed under the [Apache-2.0 license](LICENSE).
