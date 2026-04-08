---
name: dita-reduce-asciidoc
description: Reduce AsciiDoc files by expanding all include directives into a single flattened document using asciidoctor-reducer. Use this skill when asked to reduce, flatten, resolve, or normalize AsciiDoc assemblies.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read
---

# Reduce AsciiDoc Skill

Flatten AsciiDoc assemblies by expanding all include directives into a single self-contained document using `asciidoctor-reducer`.

## Prerequisites

```bash
gem install asciidoctor-reducer
```

## Usage

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/reduce_asciidoc.sh <file.adoc> [-o output.adoc]
```

### Examples

```bash
# Reduce an assembly (output to master-reduced.adoc in same directory)
bash ${CLAUDE_SKILL_DIR}/scripts/reduce_asciidoc.sh master.adoc

# Reduce with custom output path
bash ${CLAUDE_SKILL_DIR}/scripts/reduce_asciidoc.sh master.adoc -o /tmp/flat-master.adoc
```

## Example invocations

- "Reduce the assembly in docs/master.adoc"
- "Flatten all includes into a single file"
- "Normalize the nested assemblies"
- "Expand includes in the documentation"

## Script location

```
skills/dita-reduce-asciidoc/scripts/
└── reduce_asciidoc.sh    # Shell wrapper for asciidoctor-reducer
```
