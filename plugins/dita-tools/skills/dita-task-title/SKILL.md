---
name: dita-task-title
description: Remove unsupported block titles from procedure modules for DITA compatibility. Use this skill when asked to fix task titles, remove unsupported titles, or prepare procedure files for DITA conversion.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read, Edit, Write
---

# Task title (unsupported titles) skill

Remove unsupported block titles from procedure modules for DITA compatibility.

## Overview

This skill uses the `task_title.rb` Ruby script to find and remove block titles in procedure modules that are not supported for DITA task mapping.

## What it detects

The Vale rule `TaskTitle.yml` detects block titles (lines starting with `.` or `..`) in procedure modules that are not one of the supported titles:

### Supported titles (kept)

- `.Prerequisite` / `.Prerequisites`
- `.Procedure`
- `.Verification`
- `.Result` / `.Results`
- `.Troubleshooting` / `.Troubleshooting steps`
- `.Next step` / `.Next steps`
- `.Additional resources`

### Unsupported titles (removed)

Any other block title like:
- `.Example`
- `.Important`
- `.Note`
- `.Overview`
- `.Configuration file`
- etc.

## What it removes

**Before:**
```asciidoc
:_mod-docs-content-type: PROCEDURE
[id="configuring-app"]
= Configuring the application

.Overview

This procedure configures the application.

.Prerequisites

* You have access.

.Configuration file

The following shows the config file format:

.Procedure

. Edit the file.
. Save changes.

.Example output

[source,text]
----
Success
----

.Verification

* Check the status.
```

**After:**
```asciidoc
:_mod-docs-content-type: PROCEDURE
[id="configuring-app"]
= Configuring the application

This procedure configures the application.

.Prerequisites

* You have access.

The following shows the config file format:

.Procedure

. Edit the file.
. Save changes.

[source,text]
----
Success
----

.Verification

* Check the status.
```

## Why this matters

DITA tasks have a fixed structure with specific elements (prereq, context, steps, result, postreq, etc.). Block titles that don't map to these elements cause conversion errors.

## Usage

When the user asks to remove unsupported titles:

1. Identify the target folder or file containing AsciiDoc content
2. Find procedure modules (files with `:_mod-docs-content-type: PROCEDURE`)
3. Run the Ruby script against each file:
   ```bash
   ruby skills/dita-task-title/scripts/task_title.rb <file>
   ```
4. Report the changes made

### Dry run mode

To preview changes without modifying files:

```bash
ruby skills/dita-task-title/scripts/task_title.rb <file> --dry-run
```

### Output to different file

```bash
ruby skills/dita-task-title/scripts/task_title.rb <file> -o <output.adoc>
```

### Process all files in a directory

```bash
find <folder> -name "*.adoc" -exec ruby skills/dita-task-title/scripts/task_title.rb {} \;
```

## Example invocations

- "Remove unsupported titles from procedures in modules/"
- "Fix task titles in the getting_started folder"
- "Remove .Example and .Note titles from procedure files"
- "Preview title removal in modules/ --dry-run"

## Behavior notes

- **Only processes procedures**: Files without `:_mod-docs-content-type: PROCEDURE` are skipped
- **Preserves supported titles**: The standard DITA-mappable titles are kept
- **Removes title line only**: The content following the title is preserved
- **Skips code blocks**: Titles inside code blocks are not removed
- **Skips comments**: Titles inside comment blocks are not removed
- **Handles list continuations**: Titles after `+` are not removed (they're block titles for content within steps)

## Output format

```
<file>: Removed N unsupported title(s)
  Line 5: .Overview
  Line 15: .Example output
```

Or:

```
<file>: No unsupported titles found
```

Or:

```
<file>: Not a procedure module (skipped)
```

## Extension location

The Ruby script is located at: `skills/dita-task-title/scripts/task_title.rb`

## Related Vale rule

This skill addresses the warning from: `.vale/styles/AsciiDocDITA/TaskTitle.yml`
