---
name: dita-callouts
description: Transform callouts in AsciiDoc source blocks to prepare for DITA conversion. Use this skill when asked to transform, convert, or fix callouts in AsciiDoc files or folders.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read, Edit, Write
---

# Callout transform skill

Transform callout usage in AsciiDoc source blocks for DITA compatibility.

## Overview

This skill uses Ruby to transform AsciiDoc files with callout markers in source blocks, which are not supported in the AsciiDoc DITA conversion. The script offers three transformation modes:

1. **Bullet list mode** (`--rewrite-bullets`): Converts callouts to bullet lists after the code block (default behavior)
2. **Definition list mode** (`--rewrite-deflists`): Converts callouts to definition lists after the code block
3. **Inline comments mode** (`--add-inline-comments`): Converts callouts to inline comments within the code block

## Usage

When the user asks to transform callouts:

1. Identify the target folder or file containing AsciiDoc content
2. Find all `.adoc` files in the target location
3. Ask which mode they prefer (bullet lists, definition lists, or inline comments)
4. Run the Ruby extension against each file with the appropriate option:

   For bullet lists (default):
   ```bash
   ruby skills/dita-callouts/scripts/callouts.rb <file> --rewrite-bullets
   ```

   For definition lists:
   ```bash
   ruby skills/dita-callouts/scripts/callouts.rb <file> --rewrite-deflists
   ```

   For inline comments:
   ```bash
   ruby skills/dita-callouts/scripts/callouts.rb <file> --add-inline-comments
   ```

5. **For bullet list and definition list modes**: After running the script, review and rewrite each entry to follow the Red Hat style guide format:
   - Begin each description with "Specifies" (for user-replaced values) or an appropriate verb
   - Ensure the description is clear and concise
   - The script moves content verbatim; you should improve the wording

6. Report the updated files and/or any errors found

## Command options

```
ruby callouts.rb <file.adoc> [OPTIONS]

Options:
  --rewrite-bullets      Convert callouts to bullet lists after the code block (default)
  --rewrite-deflists     Convert callouts to definition lists after the code block
  --add-inline-comments  Convert callouts to inline comments in the code block
  --dry-run              Show what would be changed without modifying files
  -o <file>              Write output to specified file instead of modifying in place
```

## Transformation modes

### Bullet list mode (--rewrite-bullets)

Converts callouts to bullet lists after the code block. This is the default mode and follows the Red Hat supplementary style guide recommendations for explaining commands and variables in code blocks using bulleted lists.

The script:
- Removes all callout markers from the code block
- Attaches an open block to the code block using `+` continuation
- Creates a bullet list with the code line content in backticks followed by the callout description
- Wraps the bullet list in `--` open block delimiters

**Before:**
```asciidoc
[source,bash]
----
vllm serve \
  --model meta-llama/Llama-2-7b \  # <1>
  --port 8000 \  # <2>
  --host 0.0.0.0  # <3>
----
<1> Specify the model to load from Hugging Face
<2> Set the port for the API server
<3> Bind to all network interfaces
```

**After (script output):**
```asciidoc
[source,bash]
----
vllm serve \
  --model meta-llama/Llama-2-7b \
  --port 8000 \
  --host 0.0.0.0
----
+
--
* `--model meta-llama/Llama-2-7b` Specify the model to load from Hugging Face
* `--port 8000` Set the port for the API server
* `--host 0.0.0.0` Bind to all network interfaces
--
```

**After rewriting (recommended):**
```asciidoc
[source,bash]
----
vllm serve \
  --model meta-llama/Llama-2-7b \
  --port 8000 \
  --host 0.0.0.0
----
+
--
* `--model` specifies the model to load from Hugging Face.
* `--port` specifies the port for the API server.
* `--host` specifies the network interface to bind to. Use `0.0.0.0` to bind to all interfaces.
--
```

### Definition list mode (--rewrite-deflists)

Converts callouts to definition lists after the code block. This follows the Red Hat supplementary style guide recommendations for explaining commands and variables in code blocks using definition lists with a "Where:" introduction.

The script:
- Removes all callout markers from the code block
- Attaches an open block to the code block using `+` continuation
- Creates a definition list with the code line content as the term
- Wraps the definition list in `--` open block delimiters

**Before:**
```asciidoc
[source,bash]
----
vllm serve \
  --model meta-llama/Llama-2-7b \  # <1>
  --port 8000 \  # <2>
  --host 0.0.0.0  # <3>
----
<1> Specify the model to load from Hugging Face
<2> Set the port for the API server
<3> Bind to all network interfaces
```

**After (script output):**
```asciidoc
[source,bash]
----
vllm serve \
  --model meta-llama/Llama-2-7b \
  --port 8000 \
  --host 0.0.0.0
----
+
--
Where:

--model meta-llama/Llama-2-7b:: Specify the model to load from Hugging Face
--port 8000:: Set the port for the API server
--host 0.0.0.0:: Bind to all network interfaces
--
```

**After rewriting (recommended):**
```asciidoc
[source,bash]
----
vllm serve \
  --model meta-llama/Llama-2-7b \
  --port 8000 \
  --host 0.0.0.0
----
+
--
Where:

`--model`:: Specifies the model to load from Hugging Face.
`--port`:: Specifies the port for the API server.
`--host`:: Specifies the network interface to bind to. Use `0.0.0.0` to bind to all interfaces.
--
```

**Single-line commands:** For one-line commands, only use the replacement value as the description list term — not the entire command line:

```asciidoc
[source,terminal]
----
$ oc delete -f <file_name> -n <cluster_namespace>
----

where:

`<cluster_namespace>`:: Specifies the namespace of the cluster.
```

Do NOT echo the full command as the term (e.g., `` `$ oc delete -f <file_name> -n <cluster_namespace>` ``).

### Inline comments mode (--add-inline-comments)

Converts callout markers to inline comments within the code block. This mode preserves the original content as comments in the code.

**Before:**
```asciidoc
[source,bash]
----
vllm serve \
  --model meta-llama/Llama-2-7b \  # <1>
  --port 8000 \  # <2>
  --host 0.0.0.0  # <3>
----
<1> Specify the model to load from Hugging Face
<2> Set the port for the API server
<3> Bind to all network interfaces
```

**After:**
```asciidoc
[source,bash]
----
vllm serve \
  # Specify the model to load from Hugging Face
  --model meta-llama/Llama-2-7b \
  # Set the port for the API server
  --port 8000 \
  # Bind to all network interfaces
  --host 0.0.0.0
----
```

## Style guide reference

The bullet list and definition list modes follow the Red Hat supplementary style guide section "Explanation of commands and variables used in code blocks":

- **Bullet lists**: Use a bulleted list to explain multiple code lines, YAML structure, or multiple parameters. Explain items in the order they appear in the code block.
- **Definition lists**: Use a definition list to explain multiple options, parameters, user-replaced values, or placeholders. Introduce with "Where:" and begin each variable description with "Specifies".

See: https://redhat-documentation.github.io/supplementary-style-guide/#explain-commands-variables-in-code-blocks

## Example invocations

- "Transform callouts in modules/getting_started/ using bullet lists"
- "Convert callout usage in the assemblies folder to definition lists"
- "Run callout transformation on all AsciiDoc files with --rewrite-deflists"
- "Transform the callouts in modules/deploying-with-podman.adoc"
- "Transform callouts using inline comments mode"

## Output format

Issues are reported in a parseable format:
```
<file>:<line>: <TYPE>: <message>
```

Where TYPE is one of:
- `ERROR`: Critical issue that must be fixed
- `WARNING`: Issue that should be reviewed

## Extension location

The Ruby extension is located at: `skills/dita-callouts/scripts/callouts.rb`
