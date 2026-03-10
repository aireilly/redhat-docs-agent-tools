---
name: dita-task-step
description: Fix list continuations in procedure steps for DITA compatibility. Use this skill when asked to fix task steps, add list continuations, or prepare procedure files for DITA conversion.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read, Edit, Write
---

# Task step (list continuation) skill

Fix list continuations in procedure steps for DITA compatibility.

## Overview

This skill uses the `task_step.rb` Ruby script to find procedure steps that contain multi-block content without proper list continuation markers (`+`) and adds them.

## What it detects

The Vale rule `TaskStep.yml` detects content in procedure modules that appears after steps but is not properly attached to a step using the list continuation marker (`+`).

## List continuations explained

In AsciiDoc, a list continuation marker (`+` on its own line) attaches a block to the preceding list item. Without it, the block is not part of the list item.

See: https://docs.asciidoctor.org/asciidoc/latest/lists/continuation/

## What it fixes

### Missing continuation before code blocks

**Before:**
```asciidoc
.Procedure

. Run the following command:

[source,bash]
----
oc get pods
----

. Check the output.
```

**After:**
```asciidoc
.Procedure

. Run the following command:
+
[source,bash]
----
oc get pods
----

. Check the output.
```

### Missing continuation before paragraphs

**Before:**
```asciidoc
.Procedure

. Configure the settings.

The configuration file is located at `/etc/myapp/config.yaml`.

. Restart the service.
```

**After:**
```asciidoc
.Procedure

. Configure the settings.
+
The configuration file is located at `/etc/myapp/config.yaml`.

. Restart the service.
```

### Missing continuation before admonitions

**Before:**
```asciidoc
.Procedure

. Run the installer.

[NOTE]
====
The installation may take several minutes.
====

. Verify the installation.
```

**After:**
```asciidoc
.Procedure

. Run the installer.
+
[NOTE]
====
The installation may take several minutes.
====

. Verify the installation.
```

## Usage

When the user asks to fix list continuations:

1. Identify the target folder or file containing AsciiDoc content
2. Find procedure modules (files with `:_mod-docs-content-type: PROCEDURE`)
3. Run the Ruby script against each file:
   ```bash
   ruby skills/dita-task-step/scripts/task_step.rb <file>
   ```
4. Report the changes made

### Dry run mode

To preview changes without modifying files:

```bash
ruby skills/dita-task-step/scripts/task_step.rb <file> --dry-run
```

### Output to different file

```bash
ruby skills/dita-task-step/scripts/task_step.rb <file> -o <output.adoc>
```

### Process all files in a directory

```bash
find <folder> -name "*.adoc" -exec ruby skills/dita-task-step/scripts/task_step.rb {} \;
```

## Example invocations

- "Fix list continuations in modules/"
- "Add missing + markers to procedure steps"
- "Fix task steps in the getting_started folder"
- "Preview list continuation changes in modules/ --dry-run"

## Behavior notes

- **Only processes procedures**: Files without `:_mod-docs-content-type: PROCEDURE` are skipped
- **Only in Procedure section**: Only content within the `.Procedure` section is processed
- **Detects orphan content**: Paragraphs, code blocks, admonitions, and other blocks after steps are detected
- **Adds + markers**: The list continuation marker is inserted on a line by itself
- **Preserves existing continuations**: Existing `+` markers are not duplicated
- **Handles nested lists**: Nested list items are properly handled

## Output format

```
<file>: Added N list continuation(s)
```

Or:

```
<file>: No missing list continuations found
```

Or:

```
<file>: Not a procedure module (skipped)
```

## Extension location

The Ruby script is located at: `skills/dita-task-step/scripts/task_step.rb`

## Related Vale rule

This skill addresses the warning from: `.vale/styles/AsciiDocDITA/TaskStep.yml`
