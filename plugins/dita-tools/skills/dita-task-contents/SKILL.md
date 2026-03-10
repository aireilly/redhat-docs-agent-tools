---
name: dita-task-contents
description: Add missing .Procedure block title to procedure modules for DITA compatibility. Use this skill when asked to fix procedure titles, add .Procedure markers, or prepare procedure files for DITA conversion.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read, Edit, Write
---

# Task contents (Procedure title) skill

Add missing `.Procedure` block title to procedure modules for DITA compatibility.

## Overview

This skill uses the `task_contents.rb` Ruby script to find procedure modules that are missing the `.Procedure` block title and adds it before the first ordered list (the procedure steps).

## What it detects

The Vale rule `TaskContents.yml` detects procedure modules (files with `:_mod-docs-content-type: PROCEDURE`) that do not have a `.Procedure` or `..Procedure` block title.

## What it adds

### Missing .Procedure title

**Before:**
```asciidoc
:_mod-docs-content-type: PROCEDURE
[id="installing-software"]
= Installing the software

[role="_abstract"]
Install the software using the package manager.

.Prerequisites

* You have admin access.
* The repository is configured.

. Download the package.
. Run the installer.
. Verify the installation.
```

**After:**
```asciidoc
:_mod-docs-content-type: PROCEDURE
[id="installing-software"]
= Installing the software

[role="_abstract"]
Install the software using the package manager.

.Prerequisites

* You have admin access.
* The repository is configured.

.Procedure

. Download the package.
. Run the installer.
. Verify the installation.
```

## Why this matters

The `.Procedure` block title is required to properly map procedure steps to DITA task elements. Without it, the converter cannot identify where the task steps begin.

## Usage

When the user asks to fix procedure titles:

1. Identify the target folder or file containing AsciiDoc content
2. Find procedure modules (files with `:_mod-docs-content-type: PROCEDURE`)
3. Run the Ruby script against each file:
   ```bash
   ruby skills/dita-task-contents/scripts/task_contents.rb <file>
   ```
4. Report the changes made

### Dry run mode

To preview changes without modifying files:

```bash
ruby skills/dita-task-contents/scripts/task_contents.rb <file> --dry-run
```

### Output to different file

```bash
ruby skills/dita-task-contents/scripts/task_contents.rb <file> -o <output.adoc>
```

### Process all files in a directory

```bash
find <folder> -name "*.adoc" -exec ruby skills/dita-task-contents/scripts/task_contents.rb {} \;
```

## Example invocations

- "Add .Procedure titles to procedures in modules/"
- "Fix missing procedure markers in the getting_started folder"
- "Add .Procedure block title to all procedure files"
- "Preview procedure title changes in modules/ --dry-run"

## Behavior notes

- **Only processes procedures**: Files without `:_mod-docs-content-type: PROCEDURE` are skipped
- **Skips existing titles**: Files that already have `.Procedure` are not modified
- **Finds first ordered list**: The `.Procedure` title is inserted before the first ordered list after any Prerequisites section
- **Handles Prerequisites**: If a Prerequisites section exists, the script inserts after it
- **Skips code blocks**: Ordered lists inside code blocks are not considered

## Output format

```
<file>: Added .Procedure title before line N
```

Or:

```
<file>: .Procedure title already exists
```

Or:

```
<file>: Not a procedure module (skipped)
```

Or:

```
<file>: No ordered list found for procedure steps
```

## Extension location

The Ruby script is located at: `skills/dita-task-contents/scripts/task_contents.rb`

## Related Vale rule

This skill addresses the warning from: `.vale/styles/AsciiDocDITA/TaskContents.yml`
