---
name: dita-add-shortdesc-abstract
description: Add missing [role="_abstract"] attribute to AsciiDoc files for DITA short description support. Use this skill when asked to add abstract role attributes, mark short descriptions, or prepare files for DITA conversion.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read, Edit, Write
---

# Add short description abstract role

Add missing `[role="_abstract"]` attributes to AsciiDoc files for DITA compatibility.

## Overview

This skill uses the `short_description.rb` Ruby script to find AsciiDoc files missing the `[role="_abstract"]` attribute and automatically adds it before the first paragraph after the document title.

**The short description is the first paragraph and cannot be more than a single paragraph.**

## What it does

For a file like this:

```asciidoc
:_mod-docs-content-type: CONCEPT
[id="about-optimization_{context}"]
= About optimization

As AI applications mature and new compression algorithms are published...

More content here...
```

The script adds the missing abstract role:

```asciidoc
:_mod-docs-content-type: CONCEPT
[id="about-optimization_{context}"]
= About optimization

[role="_abstract"]
As AI applications mature and new compression algorithms are published...

More content here...
```

## Why this matters

The `[role="_abstract"]` attribute marks a paragraph as the short description (`<shortdesc>`) element in DITA output. This is required by the AsciiDocDITA Vale rule `ShortDescription.yml` which warns:

> Assign [role="_abstract"] to a paragraph to use it as `<shortdesc>` in DITA.

## Usage

When the user asks to add abstract role to files:

1. Identify the target folder or file containing AsciiDoc content
2. Find all `.adoc` files in the target location
3. Run the Ruby script against each file:
   ```bash
   ruby skills/dita-add-shortdesc-abstract/scripts/short_description.rb <file>
   ```
4. Report which files were updated

### Process all files in a directory

```bash
find <folder> -name "*.adoc" -exec ruby skills/dita-add-shortdesc-abstract/scripts/short_description.rb {} \;
```

## Example invocations

- "Add abstract role to files in modules/"
- "Add [role="_abstract"] to all AsciiDoc files"
- "Mark short descriptions in the getting_started folder"
- "Preview abstract changes in modules/ --dry-run"

## Behavior notes

- **Skips assembly files**: Files with `:_mod-docs-content-type: ASSEMBLY` are skipped (assemblies use a different structure)
- **Skips snippet files**: Files with `:_mod-docs-content-type: SNIPPET` are skipped
- **Skips files with existing abstracts**: If `[role="_abstract"]` already exists, no changes are made
- **Finds first paragraph**: The script locates the first regular paragraph after the title, skipping:
  - Empty lines
  - Attribute definitions
  - Attribute lists
  - Conditionals (ifdef/ifndef/endif)
  - Section headings
  - List items
  - Include directives
  - Admonition blocks

## Output format

When an abstract is added:
```
<file>: Added [role="_abstract"] before line N
```

When no changes needed:
```
<file>: Abstract already exists
```

Or:
```
<file>: Assembly or snippet file (skipped)
```

Or:
```
<file>: No document title found
```

Or:
```
<file>: No paragraph found after title
```

## Script location

The Ruby script is located at: `skills/dita-add-shortdesc-abstract/scripts/short_description.rb`

## Related skills

- **dita-rewrite-shortdesc**: For rewriting or improving existing short descriptions
- **dita-asciidoc-rewrite**: For comprehensive DITA issue fixing including short descriptions

## Related Vale rule

This skill addresses the warning from: `.vale/styles/AsciiDocDITA/ShortDescription.yml`
