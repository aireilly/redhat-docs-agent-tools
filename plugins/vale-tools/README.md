# vale-tools

Vale linting tools for validating documentation using the Vale CLI.

**Important:** Always run Claude Code from a terminal in the root of the documentation repository you are working on.

## Prerequisites

### GitHub CLI

Install the [GitHub CLI (`gh`)](https://cli.github.com/) and authenticate:

```bash
gh auth login
```

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
