# vale-tools

!!! tip

    Always run Claude Code from a terminal in the root of the documentation repository you are working on.

## Prerequisites

- Install the [Red Hat Docs Agent Tools marketplace](https://redhat-documentation.github.io/redhat-docs-agent-tools/install/)

- Install [software dependencies](https://redhat-documentation.github.io/redhat-docs-agent-tools/install/#software-dependencies) (Vale CLI)

- [Install GitHub CLI (`gh`)](https://cli.github.com/) and authenticate with `gh auth login`

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
