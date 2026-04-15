# Red Hat Modular Docs Rules for RHIVOS

Rules for structuring RHIVOS AsciiDoc content according to Red Hat modular documentation conventions.

## Module types

### Concept modules (`con_`)

- File prefix: `con_`
- Content type attribute: `:_mod-docs-content-type: CONCEPT`
- Purpose: Explain what something is or why it matters
- Structure:
  1. Module anchor: `[id="con_<topic-name>_{context}"]`
  2. Title: Noun phrase (e.g., "RHIVOS image building mechanics")
  3. Abstract paragraph with `[role="_abstract"]`
  4. Body: Explanatory content, no numbered steps

### Procedure modules (`proc_`)

- File prefix: `proc_`
- Content type attribute: `:_mod-docs-content-type: PROCEDURE`
- Purpose: Guide the user through a task
- Structure:
  1. Module anchor: `[id="proc_<topic-name>_{context}"]`
  2. Title: Gerund phrase (e.g., "Installing the Automotive Image Builder tool")
  3. Abstract paragraph with `[role="_abstract"]`
  4. Prerequisites section (if applicable)
  5. Numbered steps in `.Procedure` block
  6. Verification section (if applicable)

### Reference modules (`ref_`)

- File prefix: `ref_`
- Content type attribute: `:_mod-docs-content-type: REFERENCE`
- Purpose: Provide lookup information (tables, lists, parameters)
- Structure:
  1. Module anchor: `[id="ref_<topic-name>_{context}"]`
  2. Title: Noun phrase describing the data (e.g., "Manifest configuration options")
  3. Abstract paragraph with `[role="_abstract"]`
  4. Body: Tables, definition lists, or structured data

## Assembly files

- File prefix: `assembly_`
- Purpose: Collect related modules into a user-facing document
- Structure:
  1. Assembly anchor: `[id="assembly_<doc-title>_{context}"]`
  2. Title
  3. Abstract paragraph with `[role="_abstract"]`
  4. `include::` directives for each module, with `[leveloffset=+1]`

```asciidoc
[id="assembly_rhivos-image-building_{context}"]
= RHIVOS image building

[role="_abstract"]
Build and customize RHIVOS images for your target platform.

include::modules/con_image-build-mechanics.adoc[leveloffset=+1]

include::modules/proc_install-aib.adoc[leveloffset=+1]

include::modules/ref_manifest-options.adoc[leveloffset=+1]
```

## File naming

- Use lowercase with hyphens: `con_image-build-mechanics.adoc`
- Prefix must match content type: `con_`, `proc_`, `ref_`, `assembly_`
- Use descriptive, concise names that reflect the topic
- Avoid version numbers or dates in filenames

## Common elements

### Module anchor

Every module must start with an anchor that includes `{context}`:

```asciidoc
[id="<prefix>_<topic-name>_{context}"]
```

### Abstract paragraph

The first paragraph after the title must have `[role="_abstract"]`:

```asciidoc
[role="_abstract"]
This module describes how to configure boot options for your RHIVOS deployment.
```

### Additional resources

Use `.Additional resources` at the end of a module to link related content:

```asciidoc
[role="_additional-resources"]
.Additional resources
* xref:con_related-topic_{context}[Related topic title]
* link:https://example.com[External resource]
```
