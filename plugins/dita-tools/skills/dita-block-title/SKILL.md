---
name: dita-block-title
description: Fix unsupported block titles for DITA compatibility. Block titles are only valid for examples, figures (images), and tables. Use this skill when asked to fix block titles, remediate BlockTitle warnings, or prepare files for DITA conversion.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read, Edit, Write
---

# Block title skill

Fix unsupported block titles in AsciiDoc files for DITA compatibility.

## Overview

This skill uses the `block_title.rb` Ruby script to identify and remediate block titles that are not supported in DITA. In DITA, block titles can only be assigned to examples, figures (images), and tables.

## What it detects

The Vale rule `BlockTitle.yml` detects block titles (lines starting with `.` or `..`) that appear before unsupported content types.

### Supported block title contexts (kept)

Block titles are valid ONLY before:

- **Images** (`image::`)
- **Tables** (`|===`)
- **Example blocks** (`[example]` or `====` delimiters)

### Unsupported block title contexts (remediated)

Block titles before any other content type must be remediated:

- Source/code blocks (`[source,...]` or `----`)
- Regular paragraphs
- Lists (ordered, unordered, definition)
- Admonitions (`[NOTE]`, `[WARNING]`, etc.)
- Literal blocks
- Sidebars

### Exceptions

The following block titles in PROCEDURE modules are handled by the `dita-task-title` skill instead:

- `.Prerequisites`
- `.Procedure`
- `.Verification`
- `.Results`
- `.Troubleshooting`
- `.Next steps`
- `.Additional resources`

## Remediation strategies

The script applies context-appropriate remediation:

### 1. Block title before source block

Convert to inline text with colon and add list continuation for proper rendering.

**Before:**
```asciidoc
.Example manifest
[source,yaml]
----
apiVersion: v1
kind: Pod
----
```

**After:**
```asciidoc
Example manifest:
+
[source,yaml]
----
apiVersion: v1
kind: Pod
----
```

### 2. Block title before source block in a list step

Add double list continuation (`++`) when inside a numbered list.

**Before:**
```asciidoc
. Create a manifest file:
+
.Example manifest
[source,yaml]
----
apiVersion: v1
----
```

**After:**
```asciidoc
. Create a manifest file.
+
Example manifest:
++
[source,yaml]
----
apiVersion: v1
----
```

### 3. Block title before paragraph or list

Convert to inline text with colon.

**Before:**
```asciidoc
.Use cases

* Case 1
* Case 2
```

**After:**
```asciidoc
Use cases:

* Case 1
* Case 2
```

### 4. Redundant block titles

Remove block titles that duplicate surrounding context.

**Before:**
```asciidoc
You can create an instance type manifest by using the `virtctl` CLI utility. For example:

.Example `virtctl` command with required fields
[source,terminal]
----
$ virtctl create instancetype --cpu 2 --memory 256Mi
----
```

**After:**
```asciidoc
You can create an instance type manifest by using the `virtctl` CLI utility. For example:

[source,terminal]
----
$ virtctl create instancetype --cpu 2 --memory 256Mi
----
```

### 5. Block title that looks like a section title

Convert standalone descriptive titles to definition lists.

**Before:**
```asciidoc
.VM snapshot controller and custom resources

The VM snapshot feature introduces three new API objects...
```

**After:**
```asciidoc
VM snapshot controller and custom resources::
The VM snapshot feature introduces three new API objects...
```

## Usage

When the user asks to fix block titles:

1. Identify the target folder or file containing AsciiDoc content
2. Run the Ruby script against each file:
   ```bash
   ruby skills/dita-block-title/scripts/block_title.rb <file>
   ```
3. Report the changes made

### Dry run mode

To preview changes without modifying files:

```bash
ruby skills/dita-block-title/scripts/block_title.rb <file> --dry-run
```

### Output to different file

```bash
ruby skills/dita-block-title/scripts/block_title.rb <file> -o <output.adoc>
```

### Process all files in a directory

```bash
find <folder> -name "*.adoc" -exec ruby skills/dita-block-title/scripts/block_title.rb {} \;
```

## Example invocations

- "Fix block titles in modules/"
- "Remediate BlockTitle Vale warnings in the getting_started folder"
- "Remove unsupported block titles before source blocks"
- "Preview block title fixes in modules/ --dry-run"

## Behavior notes

- **Preserves valid titles**: Titles before images, tables, and examples are kept
- **Skips code blocks**: Titles inside code blocks are not modified
- **Skips comments**: Titles inside comment blocks are not modified
- **Handles list context**: Properly adds list continuations when needed
- **Skips procedure-specific titles**: Titles like `.Prerequisites` and `.Procedure` are left for `dita-task-title`

## Output format

```
<file>: Fixed N block title(s)
  Line 15: ".Example manifest" -> "Example manifest:" (before source block)
  Line 42: ".Use cases" -> "Use cases:" (before list)
  Line 78: ".Configuration" -> removed (redundant)
```

Or:

```
<file>: No unsupported block titles found
```

## Extension location

The Ruby script is located at: `skills/dita-block-title/scripts/block_title.rb`

## Related Vale rule

This skill addresses the warning from: `.vale/styles/AsciiDocDITA/BlockTitle.yml`

Message: "Block titles can only be assigned to examples, figures, and tables in DITA."
