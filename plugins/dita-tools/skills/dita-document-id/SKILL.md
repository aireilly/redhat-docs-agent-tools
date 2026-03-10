---
name: dita-document-id
description: Generate and insert missing document IDs for AsciiDoc titles. Use this skill when asked to add IDs, fix missing anchors, or prepare files for DITA conversion.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read, Edit, Write
---

# Document ID generation skill

Generate and insert missing document IDs (anchor IDs) for AsciiDoc document titles.

## Overview

This skill uses the `document_id.rb` Ruby script to find AsciiDoc files with missing IDs on their document titles (level 0 headings) and automatically generates appropriate IDs following AsciiDoc conventions.

## What it does

For a file like this:

```asciidoc
:_mod-docs-content-type: PROCEDURE

= Installing the application server

This procedure explains...
```

The script adds the missing ID:

```asciidoc
:_mod-docs-content-type: PROCEDURE

[id="installing-the-application-server_{context}"]
= Installing the application server

This procedure explains...
```

## ID generation rules

The generated ID follows AsciiDoc conventions:

1. Converts title to lowercase
2. Removes inline formatting (`*bold*`, `_italic_`, etc.)
3. Removes inline macros and attribute references
4. Replaces spaces and special characters with hyphens
5. Removes leading/trailing hyphens
6. Collapses multiple consecutive hyphens
7. Appends `_{context}` suffix (configurable)

### Examples

| Title | Generated ID |
|-------|--------------|
| `Installing the server` | `installing-the-server_{context}` |
| `*Server* configuration options` | `server-configuration-options_{context}` |
| `Using GPUs (NVIDIA CUDA)` | `using-gpus-nvidia-cuda_{context}` |

## Usage

When the user asks to add document IDs:

1. Identify the target folder or file containing AsciiDoc content
2. Find all `.adoc` files in the target location
3. Run the Ruby script against each file:
   ```bash
   ruby skills/dita-document-id/scripts/document_id.rb <file>
   ```
4. Report which files were updated and what IDs were generated

### Dry run mode

To preview changes without modifying files:

```bash
ruby skills/dita-document-id/scripts/document_id.rb <file> --dry-run
```

### Without {context} suffix

For files that don't use the context variable:

```bash
ruby skills/dita-document-id/scripts/document_id.rb <file> --no-context
```

### Output to different file

```bash
ruby skills/dita-document-id/scripts/document_id.rb <file> -o <output.adoc>
```

## Example invocations

- "Add document IDs to modules/getting_started/"
- "Generate missing IDs in the assemblies folder"
- "Fix missing anchors in all AsciiDoc files"
- "Add an ID to modules/deploying-with-podman.adoc"
- "Preview ID changes in modules/ --dry-run"

## Behavior notes

- **Skips files with existing IDs**: If an ID is already assigned before the title, no changes are made
- **Skips snippet files**: Files marked as `:_mod-docs-content-type: SNIPPET` are handled appropriately
- **Skips code blocks and comments**: The script properly handles files with code blocks and comments before the title
- **Handles conditional titles**: Titles wrapped in `ifdef::` directives are detected correctly
- **Assembly IDs never include `_{context}`**: Files marked as `:_mod-docs-content-type: ASSEMBLY` automatically generate IDs without the `_{context}` suffix. Only modules (CONCEPT, PROCEDURE, REFERENCE) use the `_{context}` suffix.

## Output format

When an ID is added:
```
<file>: Added ID [id="generated-id_{context}"]
  Title: Original Title Text
```

When no changes needed:
```
<file>: ID already assigned
```

Or:
```
<file>: No document title found
```

## Extension location

The Ruby script is located at: `skills/dita-document-id/scripts/document_id.rb`
