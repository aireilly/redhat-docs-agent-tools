---
name: dita-validate-asciidoc
description: Validate AsciiDoc files for DITA conversion readiness by running Vale linting with AsciiDocDITA rules. Reports warnings and errors in a markdown table format. Use this skill when asked to validate, check, or assess AsciiDoc files before DITA conversion.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Read, Glob
---

# Validate AsciiDoc for DITA Conversion

Validate AsciiDoc assemblies or modules for DITA conversion readiness by running Vale linting with AsciiDocDITA rules. Results are formatted as a markdown table with one issue per row.

## Overview

This skill runs Vale with the AsciiDocDITA rule set to identify DITA compatibility issues in AsciiDoc files. For assemblies, it automatically discovers all included files using `dita-includes`. Only warnings and errors are reported (suggestions are excluded).

## Usage

```bash
bash scripts/validate_asciidoc.sh <file.adoc> [options]
```

### Options

| Option | Description |
|--------|-------------|
| `-l, --list-only` | Only list files, don't run Vale |
| `-h, --help` | Show help message |

### Examples

```bash
# Validate an assembly and all includes (only existing files are processed)
bash scripts/validate_asciidoc.sh master.adoc

# List files that would be validated
bash scripts/validate_asciidoc.sh master.adoc --list-only
```

## Output format

The script outputs Vale issues in line format:

```
file:line:column:severity:rule:message
```

Example output:

```
/path/to/modules/con-intro.adoc:12:5:warning:AsciiDocDITA.BlockTitle:Block titles are not supported
/path/to/modules/proc-install.adoc:8:1:error:AsciiDocDITA.HardLineBreak:Hard line breaks are not supported
/path/to/modules/ref-options.adoc:25:10:warning:AsciiDocDITA.EntityReference:Use Unicode instead of HTML entities
```

## Formatting as markdown table

After running the script, format the output as a markdown table:

| File | Line | Severity | Rule | Message |
|------|------|----------|------|---------|
| modules/con-intro.adoc | 12 | warning | AsciiDocDITA.BlockTitle | Block titles are not supported |
| modules/proc-install.adoc | 8 | error | AsciiDocDITA.HardLineBreak | Hard line breaks are not supported |
| modules/ref-options.adoc | 25 | warning | AsciiDocDITA.EntityReference | Use Unicode instead of HTML entities |

Include a summary at the end:

**Summary:** 1 error, 2 warnings

## How it works

1. Discovers all included files using the `dita-includes` script
2. Creates a temporary Vale config with AsciiDocDITA rules only
3. Runs `vale sync` to download the AsciiDocDITA package
4. Runs Vale with `--minAlertLevel=warning` on all files
5. Outputs issues in parseable line format

## Vale configuration

The script uses a hardcoded Vale configuration:

```ini
StylesPath = .vale/styles

MinAlertLevel = warning

Packages = https://github.com/jhradilek/asciidoctor-dita-vale/releases/latest/download/AsciiDocDITA.zip

[*.adoc]
BasedOnStyles = AsciiDocDITA
```

## Prerequisites

- Vale must be installed: https://vale.sh/docs/vale-cli/installation/
- The `dita-tools:dita-includes` skill script must be available

## Example invocations

- "Validate the master.adoc for DITA conversion"
- "Check the assembly for DITA issues"
- "Run DITA validation on modules/con-overview.adoc"
- "What issues will I have converting this to DITA?"
- "Are there any AsciiDocDITA errors in the assembly?"

## Script location

```
scripts/
└── validate_asciidoc.sh    # Bash script for DITA validation
```
