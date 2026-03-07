# vale-tools

Vale linting tools for validating documentation using the Vale CLI.

**Important:** Always run Claude Code from a terminal in the root of the documentation repository you are working on.

## Skills

| Skill | Description |
|-------|-------------|
| `vale` | Run Vale linting to check for style guide violations. Syncs styles before linting and checks for `.vale.ini` |
| `update-vale-rules` | Analyze Vale output for false positives and create a PR to update Vale-at-Red-Hat rules |

## Prerequisites

### Vale CLI

```bash
# Fedora/RHEL
sudo dnf copr enable mczernek/vale && sudo dnf install vale

# macOS
brew install vale
```

### Vale configuration

A `.vale.ini` file should exist in the project root. Minimal example:

```ini
StylesPath = .vale/styles

MinAlertLevel = suggestion

Packages = RedHat

[*.adoc]

BasedOnStyles = RedHat

[*.md]

BasedOnStyles = RedHat
```

Run `vale sync` to download the style packages after creating the config.

## Installation

```
/plugin install vale-tools@redhat-docs-agent-tools
```
