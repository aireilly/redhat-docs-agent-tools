---
name: dita-line-break
description: Remove hard line breaks from AsciiDoc files for DITA compatibility. Use this skill when asked to fix line breaks, remove forced breaks, or prepare files for DITA conversion.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read, Edit, Write
---

# Line break removal skill

Remove hard line breaks from AsciiDoc files for DITA compatibility.

## Overview

This skill uses the `line_break.rb` Ruby script to find and remove hard line breaks that are not supported in DITA. Hard line breaks in AsciiDoc can be created using:

1. A space followed by `+` at the end of a line (` +`)
2. The `:hardbreaks-option:` document attribute
3. The `%hardbreaks` option on blocks
4. The `options=hardbreaks` attribute

## What it removes

### Line continuation markers

**Before:**
```asciidoc
This is the first line +
and this continues on a new line.
```

**After:**
```asciidoc
This is the first line and this continues on a new line.
```

### Document-level hardbreaks attribute

**Before:**
```asciidoc
:hardbreaks-option:

This text has
forced line breaks
everywhere.
```

**After:**
```asciidoc
This text has forced line breaks everywhere.
```

### Block-level hardbreaks option

**Before:**
```asciidoc
[%hardbreaks]
First line
Second line
Third line
```

**After:**
```asciidoc
First line
Second line
Third line
```

## Why this matters

Hard line breaks cannot be mapped to DITA output. The AsciiDocDITA Vale rule `LineBreak.yml` warns:

> Hard line breaks are not supported in DITA.

## Usage

When the user asks to fix line breaks:

1. Identify the target folder or file containing AsciiDoc content
2. Find all `.adoc` files in the target location
3. Run the Ruby script against each file:
   ```bash
   ruby skills/dita-line-break/scripts/line_break.rb <file>
   ```
4. Report the number of line breaks removed

### Dry run mode

To preview changes without modifying files:

```bash
ruby skills/dita-line-break/scripts/line_break.rb <file> --dry-run
```

### Output to different file

```bash
ruby skills/dita-line-break/scripts/line_break.rb <file> -o <output.adoc>
```

### Process all files in a directory

```bash
find <folder> -name "*.adoc" -exec ruby skills/dita-line-break/scripts/line_break.rb {} \;
```

## Example invocations

- "Fix line breaks in modules/"
- "Remove hard line breaks from the getting_started folder"
- "Remove all ` +` line continuations"
- "Preview line break changes in modules/ --dry-run"

## Behavior notes

- **Joins lines**: When removing ` +` at end of line, the following line is joined with a space
- **Removes attribute**: The `:hardbreaks-option:` attribute line is removed entirely
- **Removes block option**: The `%hardbreaks` option is removed from block attribute lists
- **Skips code blocks**: Line breaks inside code blocks (---- or ....) are not modified
- **Skips comments**: Line breaks inside comment blocks (////) are not modified

## Output format

```
<file>: Removed N hard line break(s)
```

Or:

```
<file>: No hard line breaks found
```

## Extension location

The Ruby script is located at: `skills/dita-line-break/scripts/line_break.rb`

## Related Vale rule

This skill addresses the warning from: `.vale/styles/AsciiDocDITA/LineBreak.yml`
