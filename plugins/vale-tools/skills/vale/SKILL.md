---
name: vale
description: Run Vale linting to check for style guide violations. Supports Markdown, AsciiDoc, reStructuredText, HTML, XML, and source code comments. Use this skill when asked to lint, check style, or validate documentation.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read
---

# Vale linting skill

Run Vale style linting against documentation files to check for style guide violations.

## Before linting

### Check for vale.ini

Before running Vale, check if a `.vale.ini` or `vale.ini` exists in the project root:

```bash
ls .vale.ini vale.ini 2>/dev/null
```

If neither exists, inform the user that no Vale config was found and that a minimal config would look like this:

```ini
StylesPath = .vale/styles

MinAlertLevel = suggestion

Packages = RedHat

[*.adoc]

BasedOnStyles = RedHat

[*.md]

BasedOnStyles = RedHat
```

Do NOT create the file automatically — ask the user if they want to create it first.

### Sync styles

Always run `vale sync` before linting to ensure style packages are up to date:

```bash
vale sync
```

This downloads and updates the style packages defined in `.vale.ini` (e.g., the `RedHat` package).

## Supported file types

Vale supports many file formats:

- **Markup**: Markdown (`.md`), AsciiDoc (`.adoc`, `.asciidoc`), reStructuredText (`.rst`), HTML (`.html`), XML (`.xml`, `.dita`)
- **Source code comments**: Python, Go, JavaScript, TypeScript, C, C++, Java, Ruby, Rust, and more
- **Other**: Org mode (`.org`), plain text (`.txt`)

## Usage

Run Vale directly against files or directories:

```bash
# Single file
vale README.md
vale doc.adoc
vale guide.rst

# Multiple files
vale file1.md file2.adoc file3.rst

# Directory (lints all supported files)
vale docs/

# Specific file patterns
vale --glob='*.md' docs/
vale --glob='*.{md,adoc,rst}' docs/
```

## Required configuration

Add these overrides to your project's `.vale.ini` to ensure critical style violations are caught as errors:

```ini
[*.adoc]
BasedOnStyles = RedHat, AsciiDoc

# Critical style violations - must be errors
RedHat.SelfReferentialText = error
RedHat.ProductCentricWriting = error
```

## Common options

```bash
# Use a specific config file
vale --config=/path/to/.vale.ini docs/

# Match specific file types
vale --glob='**/*.md' path/to/files
vale --glob='**/*.{adoc,md}' path/to/files

# Only show errors and warnings (skip suggestions)
vale --minAlertLevel=warning docs/

# Only show errors
vale --minAlertLevel=error docs/

# JSON output for programmatic use
vale --output=JSON docs/

# Exclude certain files
vale --glob='!**/*-generated.md' docs/

# Lint source code comments
vale --glob='*.py' src/
vale --glob='*.go' pkg/
```

## Example invocations

- "Lint the docs/ folder"
- "Check style on README.md"
- "Run Vale against all Markdown files"
- "Validate the AsciiDoc modules"
- "Show only errors in the documentation"
- "Lint Python docstrings in src/"
- "Check style guide compliance for all documentation"

## Output format

```
docs/guide.md:15:3: error: Style.Spelling - 'kubernetes' should be 'Kubernetes'
docs/guide.md:23:1: warning: Style.PassiveVoice - Avoid passive voice
modules/intro.adoc:45:10: suggestion: Style.SentenceLength - Consider shortening this sentence
```

## Prerequisites

Vale must be installed:

```bash
# Fedora/RHEL
sudo dnf copr enable mczernek/vale && sudo dnf install vale

# macOS
brew install vale

# Other platforms
# See: https://vale.sh/docs/install
```
