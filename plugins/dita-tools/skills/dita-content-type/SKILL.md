---
name: dita-content-type
description: Add or update :_mod-docs-content-type: attribute in AsciiDoc files. Detects content type (CONCEPT, PROCEDURE, ASSEMBLY, SNIPPET) from file structure and adds the attribute if missing. Use this skill when asked to add content types, fix module types, or prepare files for DITA conversion.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read, Edit, Write
---

# Content type attribute skill

Add or update `:_mod-docs-content-type:` attributes in AsciiDoc files for DITA compatibility and Red Hat modular documentation compliance.

## Overview

This skill uses the `content_type.rb` Ruby script to:
1. Detect the content type of AsciiDoc files based on structure and patterns
2. Add `:_mod-docs-content-type: <TYPE>` if missing
3. Update legacy `:_module-type:` attributes to the new format

## Allowed content types

| Type | Description |
|------|-------------|
| `CONCEPT` | Explains what something is |
| `PROCEDURE` | Step-by-step instructions |
| `ASSEMBLY` | Combines modules into a topic |
| `SNIPPET` | Reusable content fragments |
| `REFERENCE` | Lookup information (tables, options) |

## What it does

For a file like this:

```asciidoc
[id="about-optimization_{context}"]
= About optimization

As AI applications mature and new compression algorithms are published...
```

The script adds the content type attribute:

```asciidoc
:_mod-docs-content-type: CONCEPT
[id="about-optimization_{context}"]
= About optimization

As AI applications mature and new compression algorithms are published...
```

## Detection logic

The script uses multiple signals to determine content type (in priority order):

### 1. Existing attribute (highest priority)

If `:_mod-docs-content-type:` already exists, the file is skipped.

### 2. Legacy attribute update

If `:_module-type:` exists, it is renamed to `:_mod-docs-content-type:`.

### 3. Filename prefix

| Prefix | Content Type |
|--------|--------------|
| `assembly_` or `assembly-` | ASSEMBLY |
| `con_` or `con-` | CONCEPT |
| `proc_` or `proc-` | PROCEDURE |
| `ref_` or `ref-` | REFERENCE |
| `snip_` or `snip-` | SNIPPET |

### 4. Folder location

| Folder Pattern | Content Type |
|----------------|--------------|
| `assemblies/` | ASSEMBLY |
| `concepts/` | CONCEPT |
| `procedures/` | PROCEDURE |
| `references/` | REFERENCE |
| `snippets/` | SNIPPET |

### 5. Content analysis (lowest priority)

| Pattern | Content Type |
|---------|--------------|
| `.Procedure` block title | PROCEDURE |
| Numbered list after title | PROCEDURE |
| Table with header row | REFERENCE |
| `include::` directives | ASSEMBLY |

## Usage

When the user asks to add content type attributes:

1. Identify the target folder or file containing AsciiDoc content
2. Find all `.adoc` files in the target location
3. Run the Ruby script against each file:
   ```bash
   ruby skills/dita-content-type/scripts/content_type.rb <file>
   ```
4. Report which files were updated

### Process all files in a directory

```bash
find <folder> -name "*.adoc" -exec ruby skills/dita-content-type/scripts/content_type.rb {} \;
```

### Dry-run mode

Preview changes without modifying files:

```bash
ruby skills/dita-content-type/scripts/content_type.rb <file.adoc> --dry-run
```

## Example invocations

- "Add content type attributes to files in modules/"
- "Fix missing :_mod-docs-content-type: in the getting_started folder"
- "Update :_module-type: to :_mod-docs-content-type:"
- "Preview content type detection in modules/ --dry-run"

## Output format

When content type is added:
```
<file>: Added :_mod-docs-content-type: CONCEPT
```

When legacy attribute is updated:
```
<file>: Updated :_module-type: to :_mod-docs-content-type: PROCEDURE
```

When no changes needed:
```
<file>: Already has :_mod-docs-content-type: CONCEPT
```

When type cannot be determined:
```
<file>: Unable to determine content type (use --type to specify)
```

## Command-line options

```
Usage: ruby content_type.rb <file.adoc> [options]

Options:
  -o FILE       Write output to FILE (default: overwrite input)
  --dry-run     Show what would be changed without modifying files
  --type TYPE   Force a specific content type (CONCEPT, PROCEDURE, REFERENCE, ASSEMBLY, SNIPPET)
  --help        Show this help message
```

## Extension location

The Ruby script is located at: `skills/dita-content-type/scripts/content_type.rb`

## Related

- `:_mod-docs-content-type:` is required by Red Hat modular documentation standards
- This attribute maps to DITA topic types during conversion
