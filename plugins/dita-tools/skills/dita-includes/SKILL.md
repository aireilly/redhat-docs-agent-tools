---
name: dita-includes
description: List all AsciiDoc files referenced via include directives, recursively traversing child includes. Use this skill when asked to find includes, list dependencies, or analyze AsciiDoc file structure.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read
---

# List AsciiDoc Includes Skill

Recursively find all AsciiDoc files referenced via `include::` directives in a document, traversing all child includes to build a complete dependency list.

## Overview

This skill parses AsciiDoc files for `include::` directives and follows them recursively to produce a complete, sorted, and deduplicated list of all referenced files. This is useful for:

- Understanding document structure before DITA conversion
- Identifying all files that compose an assembly
- Checking for missing or broken includes
- Preparing file lists for batch processing

## What it does

### Input: Assembly with nested includes

```asciidoc
= Master Guide

include::_attributes/common.adoc[]

include::modules/con-intro.adoc[leveloffset=+1]

include::assemblies/getting-started.adoc[leveloffset=+1]
```

Where `assemblies/getting-started.adoc` contains:

```asciidoc
= Getting Started

include::../modules/proc-install.adoc[leveloffset=+1]

include::../modules/proc-configure.adoc[leveloffset=+1]
```

### Output: Complete file list (absolute paths)

```
/home/user/docs/_attributes/common.adoc
/home/user/docs/assemblies/getting-started.adoc
/home/user/docs/master.adoc
/home/user/docs/modules/con-intro.adoc
/home/user/docs/modules/proc-configure.adoc
/home/user/docs/modules/proc-install.adoc
```

## Key features

- **Recursive traversal**: Follows includes in child files to any depth
- **Cycle detection**: Prevents infinite loops from circular includes
- **Sorted output**: Results are alphabetically sorted
- **Deduplicated**: Each file appears only once
- **Absolute paths**: Outputs absolute paths by default (works from any directory)
- **Missing file handling**: Reports files that don't exist (can be filtered)

## Usage

```bash
bash dita-tools/skills/dita-includes/scripts/find_includes.sh <file.adoc> [options]
```

### Options

| Option | Description |
|--------|-------------|
| `-a, --absolute` | Output absolute paths (default) |
| `-r, --relative` | Output paths relative to input file directory |
| `-e, --existing` | Only output files that exist |
| `-h, --help` | Show help message |

### Examples

```bash
# List all includes from an assembly (absolute paths by default)
bash dita-tools/skills/dita-includes/scripts/find_includes.sh master.adoc

# Get relative paths instead
bash dita-tools/skills/dita-includes/scripts/find_includes.sh docs/guide.adoc --relative

# Only list files that exist (skip broken includes)
bash dita-tools/skills/dita-includes/scripts/find_includes.sh master.adoc --existing

# Combine options
bash dita-tools/skills/dita-includes/scripts/find_includes.sh master.adoc -e
```

## Limitations

- **Attribute references**: Paths containing `{attribute}` placeholders are skipped with a warning, as they cannot be resolved without knowing attribute values
- **Conditional includes**: The script does not evaluate `ifdef`/`ifndef` preprocessor directives; all includes are listed regardless of conditions

## Example invocations

- "List all files included in master.adoc"
- "Find all includes in the assembly"
- "What files does this document depend on?"
- "Show me the include tree for the guide"
- "Check for missing includes"

## Script location

```
dita-tools/skills/dita-includes/scripts/
└── find_includes.sh      # Bash script for recursive include discovery
```
