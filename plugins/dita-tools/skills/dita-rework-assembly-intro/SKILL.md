---
name: dita-rework-assembly-intro
description: Rework introductory content from AsciiDoc assembly files (master.adoc) into separate concept modules. Use when refactoring assemblies to follow Red Hat modular documentation standards, when asked to move intro content to modules, or when creating about-* modules from assembly preambles.
model: claude-opus-4-5@20251101
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, TodoWrite
---

# Extract assembly introductory content

This skill extracts introductory content from AsciiDoc assembly files and moves it into separate concept modules following Red Hat modular documentation standards.

## When to use

Use this skill when:

- Refactoring assemblies to follow modular documentation best practices
- Moving inline introductory paragraphs from assemblies into reusable modules
- Creating `about-*` concept modules from assembly preambles
- The user asks to "extract intro content" or "move preamble to modules"

## Process overview

1. Find all target assembly files (typically `master.adoc` or files with `:_mod-docs-content-type: ASSEMBLY`)
2. For each assembly, identify introductory content between the title/attributes and the first `include::` directive
3. Create a new concept module containing the extracted content
4. Update the assembly to include the new module
5. Preserve any admonitions, additional resources, and formatting

## Step-by-step instructions

### Step 1: Find assembly files

Search for assembly files in the repository:

```
Glob pattern: **/master.adoc
```

Or search for files with the assembly content type:

```
Grep pattern: :_mod-docs-content-type: ASSEMBLY
```

### Step 2: Analyze each assembly

For each assembly file, identify:

1. **Header section**: Lines containing `:_mod-docs-content-type:`, `include::_attributes/`, title (`=`), and document attributes (`:doctype:`, `:toc:`, `:context:`)
2. **Introductory content**: All content between the header section and the first `include::modules/` directive
3. **First include**: The first `include::` statement that references a module

Introductory content may include:

- `[role="_abstract"]` blocks
- Paragraphs describing the assembly topic
- `[NOTE]` or `[IMPORTANT]` admonition blocks
- `[role="_additional-resources"]` sections with links

### Step 3: Create the concept module

Create a new file in the `modules/` directory with the naming convention:

```
modules/about-<parent-folder-name>.adoc
```

Where `<parent-folder-name>` is derived from the assembly's parent directory (e.g., `server_arguments` becomes `about-server-arguments.adoc`).

Use this template for the new module:

```asciidoc
:_mod-docs-content-type: CONCEPT
[id="about-<topic>_{context}"]
= About <topic title>

[role="_abstract"]
<Original introductory paragraph(s) from the assembly>

<Additional descriptive content explaining the scope and purpose>

<Preserved admonitions if any>

<Preserved additional resources section if any>
```

### Step 4: Enhance the preamble

Add descriptive content that explains what the reader will learn. Avoid constructions like "This assembly covers..." or bullet lists of topics. Instead, write flowing prose that:

- Expands on the original introductory content
- Provides context about the feature or topic
- Mentions key capabilities or use cases
- Uses product attribute references (e.g., `{product-title}`, `{prodname-short}`)

### Step 5: Update the assembly

Replace the inline introductory content in the assembly with an include statement:

```asciidoc
:context: <context-value>

include::modules/about-<topic>.adoc[leveloffset=+1]

include::modules/<first-original-module>.adoc[leveloffset=+1]
```

Remove:

- The `[role="_abstract"]` tag and its content
- Introductory paragraphs
- Admonition blocks that were moved
- Additional resources sections that were moved

Keep:

- The assembly header (`:_mod-docs-content-type: ASSEMBLY`, attributes include, title, document attributes)
- All other `include::` statements
- Any trailing additional resources sections that apply to the whole assembly

## Example transformation

### Before (master.adoc)

```asciidoc
:_mod-docs-content-type: ASSEMBLY
include::_attributes/attributes.adoc[]
= Getting started
:doctype: book
:toc: left
:context: getting-started

{product-title} is a container image that optimizes serving and inferencing with LLMs.
Using {prodname-short}, you can serve and inference models in a way that boosts their performance.

include::modules/overview.adoc[leveloffset=+1]

include::modules/installation.adoc[leveloffset=+1]
```

### After (master.adoc)

```asciidoc
:_mod-docs-content-type: ASSEMBLY
include::_attributes/attributes.adoc[]
= Getting started
:doctype: book
:toc: left
:context: getting-started

include::modules/about-getting-started.adoc[leveloffset=+1]

include::modules/overview.adoc[leveloffset=+1]

include::modules/installation.adoc[leveloffset=+1]
```

### New module (modules/about-getting-started.adoc)

```asciidoc
:_mod-docs-content-type: CONCEPT
[id="about-getting-started_{context}"]
= About {product-title}

[role="_abstract"]
{product-title} is a container image that optimizes serving and inferencing with LLMs.
Using {prodname-short}, you can serve and inference models in a way that boosts their performance.

{product-title} supports multiple hardware platforms including NVIDIA CUDA accelerators,
AMD ROCm accelerators, and other supported AI accelerators. You can run {prodname-short}
with Podman on supported hosts, enabling flexible deployment options for development,
testing, and production workloads.
```

## Style guidelines

Follow these guidelines when creating the new modules:

- Use sentence case for headings
- Include `[role="_abstract"]` immediately after the title
- Use product attributes from `_attributes/attributes.adoc` for product names
- Do not use file prefixes like `con-`, `proc-`, `ref-`
- Preserve any `[NOTE]` or `[IMPORTANT]` admonitions from the original content
- Preserve `[role="_additional-resources"]` sections with their links
- Write descriptive prose rather than bullet lists of topics
- Avoid phrases like "This assembly covers..." or "In this section, you will learn..."

## Verification

After completing the extraction:

1. Verify the new module file exists in the `modules/` directory
2. Verify the assembly includes the new module as the first include after attributes
3. Verify no duplicate content exists between the module and assembly
4. Check that all product attributes resolve correctly
