---
name: dita-check-asciidoctor
description: Run asciidoctor to check AsciiDoc files for syntax errors. Outputs timestamped build log to /tmp. Reports warnings and errors, then reviews source to suggest fixes for common issues like unclosed conditionals, admonitions, and code blocks.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Read, Glob
---

# Check AsciiDoc with Asciidoctor

Run asciidoctor on AsciiDoc files to check for syntax errors and warnings. The build output is saved to a timestamped file in `/tmp` for reference.

## Overview

This skill runs `asciidoctor` on an input file to validate its syntax. It captures all warnings and errors, saves them to a timestamped log file, and reports whether the file is broken. If errors are found, the skill reviews the source and suggests fixes for common issues.

## Usage

```bash
bash dita-tools/skills/dita-check-asciidoctor/scripts/check_asciidoctor.sh <file.adoc>
```

### Examples

```bash
# Check a single module
bash dita-tools/skills/dita-check-asciidoctor/scripts/check_asciidoctor.sh modules/con-overview.adoc

# Check an assembly
bash dita-tools/skills/dita-check-asciidoctor/scripts/check_asciidoctor.sh guides/master.adoc
```

## Output

The script:
1. Runs `asciidoctor` with syntax highlighting and verbose mode
2. Generates HTML output to `/tmp/asciidoctor-check-<basename>-<timestamp>.html`
3. Redirects stderr to `/tmp/asciidoctor-check-<basename>-<timestamp>.log`
4. Prints a summary to stdout and displays the log contents

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | No warnings or errors |
| 1 | Warnings found (file may have issues) |
| 2 | Errors found (file is broken) |

### Sample output

```
Checking: /path/to/guides/master.adoc
HTML output: /tmp/asciidoctor-check-master-20260121-143022.html
Log output: /tmp/asciidoctor-check-master-20260121-143022.log

RESULT: BROKEN (2 errors, 1 warning)

See log for details: /tmp/asciidoctor-check-master-20260121-143022.log

Asciidoctor Check Report
========================
File: /path/to/guides/master.adoc
Date: Tue Jan 21 14:30:22 UTC 2026
HTML: /tmp/asciidoctor-check-master-20260121-143022.html

asciidoctor: ERROR: guides/master.adoc:45: include file not found: modules/missing.adoc
asciidoctor: ERROR: guides/master.adoc:78: unclosed block delimiter
asciidoctor: WARNING: guides/master.adoc:23: skipping reference to missing attribute: product-version
```

## Common issues and fixes

When errors are found, review the source file for these common problems:

### Unclosed conditionals

**Symptom:** `unexpected end of file` or content appearing in wrong places

**Check for:**
- `ifdef::` or `ifndef::` without matching `endif::[]`
- Mismatched conditional attribute names

**Fix:** Ensure every `ifdef::attr[]` has a matching `endif::[]`

```asciidoc
// WRONG - missing endif
ifdef::openshift[]
This content is OpenShift-specific.

// CORRECT
ifdef::openshift[]
This content is OpenShift-specific.
endif::[]
```

### Unclosed admonition blocks

**Symptom:** Content after admonition rendered incorrectly

**Check for:**
- `====` delimiters without closing pair
- Admonition type on wrong line

**Fix:** Use proper block delimiters or single-line format

```asciidoc
// WRONG - unclosed
[NOTE]
====
This is a note.

// CORRECT - closed block
[NOTE]
====
This is a note.
====

// CORRECT - single line
NOTE: This is a note.
```

### Unclosed code/listing blocks

**Symptom:** `unclosed block delimiter` error

**Check for:**
- `----` blocks without closing delimiter
- Mismatched number of dashes
- Code containing `----` inside the block

**Fix:** Ensure delimiters match exactly

```asciidoc
// WRONG - unclosed
[source,bash]
----
echo "hello"

// CORRECT
[source,bash]
----
echo "hello"
----
```

### Unclosed example blocks

**Symptom:** Content included in example that shouldn't be

**Check for:**
- `====` delimiters without closing pair

**Fix:** Close with matching delimiter

```asciidoc
// WRONG
.Example title
====
Example content

// CORRECT
.Example title
====
Example content
====
```

### Missing include files

**Symptom:** `include file not found` error

**Check for:**
- Typos in file paths
- Incorrect relative paths
- Files that were moved or deleted

**Fix:** Correct the path or create the missing file

### Undefined attributes

**Symptom:** `skipping reference to missing attribute` warning

**Check for:**
- Typos in attribute names
- Attributes not defined in document or included files

**Fix:** Define the attribute or fix the typo

## Workflow

1. Run the check script on the target file
2. Review the output log location printed by the script
3. If errors are found:
   - Read the source file at the reported line numbers
   - Look for the common issues listed above
   - Suggest specific fixes based on the error type
4. If only warnings are found:
   - Report them but note the file will still build
   - Suggest fixes if they're straightforward

## Prerequisites

- `asciidoctor` must be installed: `gem install asciidoctor`

## Example invocations

- "Check if this AsciiDoc file builds"
- "Run asciidoctor on master.adoc"
- "Validate the AsciiDoc syntax"
- "Why is this adoc file broken?"
- "Find syntax errors in the assembly"

## Script location

```
dita-tools/skills/dita-check-asciidoctor/scripts/
└── check_asciidoctor.sh    # Bash script for asciidoctor validation
```
