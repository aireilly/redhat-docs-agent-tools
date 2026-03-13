# DITA AsciiDoc Rewrite — Fixing Instructions

## General Principles

For every issue, you must:
- Provide the user with an explanation of the issue
- Suggest a fix following the **AI Action plan** for that issue type
- Use the **Detail** section to understand nuances and generate user-facing explanations
- If an action plan includes the keyword **Group**, list all issues of that type together under a single heading
- Otherwise, list every issue separately unless a single fix resolves multiple, adjacent issues

### The "Following Rule"

When rewording content (e.g., block titles to normal text), follow phrases that flow naturally:
- "as in the following example:"
- "The following example shows..."
- "as shown:"

Do NOT use:
- "Following is..."
- "The following shows..."

---

## Issue Types and Fixes

### EntityReference

**AI action plan**
**Group**
- If there are few (5 or less) unsupported entity references, replace them with AsciiDoc built-in attributes or normal characters
- Display an explanation to the user, including links to:
  - [Built-in AsciiDoc attributes](https://docs.asciidoctor.org/asciidoc/latest/attributes/character-replacement-ref/)
  - [AsciiDoc DITA Toolkit](https://github.com/rheslop/asciidoc-dita-toolkit/tree/main)

**Detail**

Replace unsupported entity references with built-in AsciiDoc attributes or normal characters (such as `&` or `<`).

The five standard XML entity references are supported and should NOT be replaced:
- `&amp;`
- `&lt;`
- `&gt;`
- `&apos;`
- `&quot;`

---

### AttributeReference

**AI action plan**
**Group**
- This is an informational message, not requiring a fix
- Inform the user that attribute references like `{attribute}` exist in the text
- The user must discuss with the conversion team which attributes to resolve vs. which to keep as DITA shared content

---

### AuthorLine

**AI action plan**
- Add a blank line after the document title

**Detail**

AsciiDoc interprets a non-blank line immediately following a document title as the author line. The DITA conversion process does not support author lines. Add a blank line between the document title and the following text.

---

### DocumentId

**AI action plan**
- Add a `[id=...]` statement immediately before the section heading
- Ask the user to ensure that the ID is unique

**Detail**

Every module or assembly must have an `id` attribute set immediately before the section heading:

```asciidoc
[id="sample-module"]
= Sample module
```

The user must ensure this ID is unique across all modules and assemblies in the same document.

---

### DocumentTitle

**AI action plan**
- Add a document title (first-level section heading like `= Title`) after the `id` attribute
- Ensure the title reflects the content of the file
- Alternatively, the user can change the content type to `SNIPPET` to bypass this requirement

**Detail**

Every module or assembly must have a document title immediately after the `id` attribute:

```asciidoc
[id="sample-module"]
= Sample module
```

---

### ShortDescription

**AI action plan**
- If the module starts with a paragraph that summarizes the purpose, add a `[role="_abstract"]` block attribute before it
- Otherwise, suggest adding a new summarizing paragraph with `[role="_abstract"]` based on the module content

**Detail**

For high-quality DITA conversion, every module must have a short description - a single paragraph summarizing the purpose. It must immediately follow the title and have the `[role="_abstract"]` attribute:

```asciidoc
[id="sample-procedure"]
= Sample procedure

[role="_abstract"]
To configure the system, provide the necessary data in the *System configuration* dialog.
```

---

### ExampleBlock

**AI action plan**
- Analyze the example block and convert to normal text or a code block as appropriate
- If the preceding text does not mention an example, add phrasing like "as in the following example"
- If the example block title contains information absent from preceding text, integrate it into the text

**Detail**

Example blocks can usually be converted to normal text or code blocks. Ensure the preceding text makes clear that an example follows. Block titles in example blocks must be removed - if they contain relevant information, integrate it into the text.

---

### TaskExample

**AI action plan**
- Analyze extra example blocks, including those within procedure steps, and convert to normal text or code blocks
- Ensure blocks in steps are joined using the `+` joiner line
- If content is a code block but uses `====` delimiter, change to `----` at both start and end
- If preceding text doesn't mention an example, add appropriate phrasing
- Integrate any relevant block title information into the text

**Detail**

Only one example block can be present in a procedure, and it must not be part of a step. Example blocks in steps should be converted to code blocks with proper `+` joiner lines.

---

### NestedSection

**AI action plan**
1. Determine if the file is an assembly:
   - Has `:_mod-docs-content-type: ASSEMBLY` definition
   - Has "assembly" in its name
   - Contains `include:` directives with `[leveloffset=...]` settings
2. If the file IS an assembly:
   - Recommend adding `:_mod-docs-content-type: ASSEMBLY` if missing
   - Recommend manual review for flattening structure or splitting
   - **Do not suggest specific candidate text for splitting assemblies**
3. If the file IS NOT an assembly:
   - Recommend splitting subsections into separate modules

**Detail**

DITA modules support up to one level of nesting (`==`), but deeper nesting (`===` and beyond) is not supported. This aligns with Red Hat modular documentation best practices, which recommend a maximum of 2 heading levels per module. Subsections must be split into separate modules.

When advising module breakup, provide a snippet for the assembly that includes both the original module and new modules with proper `[leveloffset=+N]` settings:

```asciidoc
include:modules/head_module.adoc[leveloffset=+1]
include:modules/subsection_module.adoc[leveloffset=+2]
```

**Do NOT** add `include` statements or references (`xref:`, `link:`, `<<...>>`) to modules themselves.

**IMPORTANT**: When extracting subsections to new modules, preserve all conditional directives (`ifdef`, `ifndef`, `endif`). If a subsection heading or content uses product-conditional variants, the new module must include all conditional branches. See the `AssemblyContents` section for detailed examples.

---

### TaskSection

**AI action plan**
- Determine if the subheading should be a block title (e.g., `.Procedure` instead of `== Procedure`)
- If a typo exists (e.g., `== Proedure`), suggest the correct block title
- Otherwise, suggest splitting subsections into separate modules

**Detail**

Procedures cannot contain subsections or subheadings. Only block titles from the procedure template are allowed: `.Prerequisites`, `.Procedure`, `.Verification`, `.Result`, `.Troubleshooting`, `.Next steps`.

---

### TaskContents

**AI action plan**
1. Check if "Procedure" exists as a section heading instead of block title - if so, suggest changing to `.Procedure`
2. If the text contains a list of procedural steps, suggest adding a `.Procedure` block title
3. If there's a single procedural step, suggest formatting as an unordered list with `.Procedure`
4. Otherwise, suggest rewriting the module as a procedure

**Detail**

A procedure module must include a `.Procedure` block title followed by a list of steps. If the list starts immediately after the heading, remind the user to add a short description before `.Procedure`.

---

### TaskDuplicate

**AI action plan**
- Identify duplicate block titles that map to the same DITA element
- Merge contents under duplicate titles so only one remains

**Duplicate groups (only one per group allowed):**
- `.Prerequisite`, `.Prerequisites`
- `.Procedure`
- `.Verification`, `.Result`, `.Results`
- `.Troubleshooting`, `.Troubleshooting step`, `.Troubleshooting steps`
- `.Next step`, `.Next steps`

Most commonly, `.Verification` and `.Result`/`.Results` appear together and should be merged.

---

### AdmonitionTitle

**AI action plan**
- If the admonition title can be removed without affecting information, remove it
- Otherwise, integrate the title content into the admonition body

**Example - Remove redundant title:**

Before:
```asciidoc
[NOTE]
.Consideration for system updates
====
A system update sometimes requires a reboot. Make sure all important tasks can shut down gracefully.
====
```

After:
```asciidoc
[NOTE]
====
A system update sometimes requires a reboot. Make sure all important tasks can shut down gracefully.
====
```

**Example - Integrate title into body:**

Before:
```asciidoc
[IMPORTANT]
.Caring for floppy disks
====
* Put 5 inch floppies in sleeves at all times
* Never expose to direct sunlight
* Keep away from magnets
====
```

After:
```asciidoc
[IMPORTANT]
====
Take the following steps to care for floppy disks:

* Put 5 inch floppies in sleeves at all times
* Never expose to direct sunlight
* Keep away from magnets
====
```

---

### BlockTitle

**AI action plan**

1. Determine if the module is a procedure (has `:_mod-docs-content-type: PROCEDURE`)
2. Apply these rules in order:
   - If `.Procedure` title exists but content type is NOT procedure: analyze and suggest converting module to procedure or splitting
   - If a procedure-related block title appears in a non-procedure: consider if content should be a procedure
   - If `.Example` or `.Examples` is the only such block: convert to a single `[example]` block (max one per file, never inside lists)
   - If several block titles represent a list: convert to unordered or description list (except `.Procedure`)
   - If block title should be a subheading: convert to `==` subheading or suggest splitting
   - If block title is a heading for a code block: reword into normal text using the "Following Rule"

**IMPORTANT:**
- Never add more than one example block per file
- Example blocks must not be inside lists (no `+` joining)
- Do NOT use bold text (`*bold*`) to replicate block title visual effect

**Example - Block title to list:**

Before:
```asciidoc
.For Platform 1.0:
Configure option A.

.For Platform 2.0:
Configure option B.
```

After:
```asciidoc
* For Platform 1.0, configure option A.
* For Platform 2.0, configure option B.
```

**Example - Block title to normal text:**

Before:
```asciidoc
.Example command
----
$ ls f*
----
```

After:
```asciidoc
The following example shows the command:

----
$ ls f*
----
```

---

### ContentType

**AI action plan**
- Always include link to [AsciiDoc DITA Toolkit](https://github.com/rheslop/asciidoc-dita-toolkit/tree/main)
- Determine content type and add `:_mod-docs-content-type: <TYPE>` at start of file
- Valid types: `CONCEPT`, `PROCEDURE`, `REFERENCE`, `ASSEMBLY`, `SNIPPET`
- **If content type is PROCEDURE**: immediately validate against procedure template and fix all structural issues

**Procedure template requirements:**
- No subheadings or subsections
- Only approved block titles
- `.Procedure` block title is mandatory
- Procedure section must be a single AsciiDoc list (ordered or unordered for single step)
- If procedure ends with additional text, add appropriate block title (`.Verification`, `.Result`, etc.)

**Short description rule:** If you generate an introduction from scratch, describe what the user will accomplish. Do NOT use self-referential phrases like "This procedure describes...".

---

### CrossReference

**AI action plan**
**Group**
- Display explanation that this can usually be ignored
- Do not suggest fixes

**Detail**

Cross-references to AsciiDoc files convert cleanly. References to IDs only require extra work but have standard conversion approaches. Users can safely ignore these warnings.

---

### LineBreak

**AI action plan**
Analyze the context of the `+` character:

1. **In a table**: Remove `+`, replace with blank line, add `a` prefix operator to cell
2. **At end of line within a list, before a block**: Move `+` to its own line
3. **At end of line, not in list, before a block**: Remove `+`, add blank line for paragraph break
4. **At end of line, followed by text**:
   - If text can be logically joined to preceding sentence: remove `+` and join
   - Otherwise: remove `+` and add blank line for paragraph break
5. **On own line with incorrect spacing**: Remove extra blank lines or comments around it
6. **For complex formatting**: Consider using AsciiDoc open block (`--` delimiters)

**Example - Fix inline line break:**

Before:
```asciidoc
.. Click *Edit* beside the pod. +
A new pod gets created.
```

After:
```asciidoc
.. Click *Edit* beside the pod.
A new pod gets created.
```

**Example - Fix in table:**

Before:
```asciidoc
|===
| List files | `ls`
+
`ls -l` for long list
|===
```

After:
```asciidoc
|===
| List files a| `ls`

`ls -l` for long list
|===
```

---

### LinkAttribute

**AI action plan**
**Group**
- Display explanation that the user must either replace the link manually or provide attribute values to conversion team
- **Include the names of attributes used in links**
- Do not suggest fixes

**Detail**

DITA does not support attributes as part of link targets. Either the entire link must be one attribute, or no attributes at all:

Valid: `link:https://docs.redhat.com/[RHEL docs]`
Valid: `:rhel_docs: link:https://docs.redhat.com/[RHEL docs]`
Invalid: `link:{red_hat_docs}/rhel/8[RHEL 8 docs]`

---

### TaskStep

**AI action plan**
1. Analyze content from the error line to the next block title or end of file
2. **If error is inside a table (empty line between rows)**: Remove empty lines between table rows (false positive)
3. **If content continues the list but has breaks**: Fix using `+` continuation markers
4. **If content has conceptual subtitles (bold text)**: Convert to unordered substep list
5. **If content continues procedure but isn't formatted as steps**: Reformat into proper steps/substeps
6. **If content doesn't continue procedure**: Add appropriate block title (`.Verification`, `.Result`, etc.)

**After joining content into single list**: Check if only one top-level step remains. If so, convert to unordered list (`*`) per procedure template.

**IMPORTANT:** If a new `.Result` or similar section starts with an admonition, add a short phrase describing the result before the admonition.

**Example - Fix broken list:**

Before:
```asciidoc
. Run the following command:
----
ls
----
. Review the output.
```

After:
```asciidoc
. Run the following command:
+
----
ls
----
. Review the output.
```

**Example - Convert subtitles to substeps:**

Before:
```asciidoc
. Give medicine to your animal:

*Procedure for dogs*
.. Roll tablet into ham.
.. Offer to dog.

*Procedure for cats*
.. Put on protective clothing.
.. Hold cat firmly.
```

After:
```asciidoc
. Give medicine to your animal:
** Procedure for dogs:
... Roll tablet into ham.
... Offer to dog.
** Procedure for cats:
... Put on protective clothing.
... Hold cat firmly.
```

---

### AssemblyContents

**AI action plan**

Assembly files exist to organize modules. Text between or after includes is not reliably processed in DITA conversion. **You must relocate or integrate all assembly text content - never simply delete it.**

Handle assembly content based on its location:

1. **Assembly abstract (intro before first include)**:
   - If the only content before the first include is an abstract paragraph, leave the content as is. Do not move it.

2. **Section headings with explanatory text (e.g., `== Adding certificates` followed by explanation)**:
   - Create a new concept module (e.g., `about-adding-certificates.adoc`) containing the heading and explanatory text
   - Add an include directive for the new module in the assembly at the appropriate position
   - Alternatively, integrate the explanatory text into the end of the preceding module if it flows naturally

3. **Text between includes (mid-assembly content)**:
   - If the text introduces the following include(s): integrate it into the start of the next included module
   - If the text concludes the preceding include(s): integrate it into the end of the preceding module
   - If the text is self-sufficient (like "Next steps" guidance): create a new module and add an include

4. **Text after the last include**:
   - If it's an "Additional resources" section: keep it in the assembly (this is supported)
   - Otherwise: integrate into the end of the last included module or create a new module

**CRITICAL**: Never remove assembly content without relocating it. Assembly introductions, section explanations, and transitional text provide valuable context for readers.

**CRITICAL**: Preserve all conditional directives when extracting content to modules. If a section heading has product-conditional variants (e.g., `{sno}` vs `{sno-okd}` inside `ifdef`/`ifndef` blocks), reproduce all variants in the new module using the same conditional structure. If an Additional resources section has product-specific links inside conditional blocks, preserve both branches. Never drop content from a conditional branch — both branches must appear in the output.

**Example - Conditional section heading preserved in extracted module:**

Before (assembly):
```asciidoc
include::modules/previous-module.adoc[leveloffset=+2]

ifndef::openshift-origin[]
[id="installing-manually"]
== Installing {sno} manually
endif::openshift-origin[]
ifdef::openshift-origin[]
[id="installing-manually"]
== Installing {sno-okd} manually
endif::openshift-origin[]

To install {product-title} on a single node, generate the installation ISO.

include::modules/next-module.adoc[leveloffset=+2]
```

After (assembly):
```asciidoc
include::modules/previous-module.adoc[leveloffset=+2]

include::modules/con_installing-manually.adoc[leveloffset=+1]

include::modules/next-module.adoc[leveloffset=+2]
```

New module (con_installing-manually.adoc):
```asciidoc
:_mod-docs-content-type: CONCEPT

[id="installing-manually_{context}"]
ifndef::openshift-origin[]
= Installing {sno} manually
endif::openshift-origin[]
ifdef::openshift-origin[]
= Installing {sno-okd} manually
endif::openshift-origin[]

[role="_abstract"]
To install {product-title} on a single node, generate the installation ISO.
```

**Example - Conditional Additional resources preserved:**

Before (assembly):
```asciidoc
* xref:../../path/to/usb-media.adoc#id[Creating a bootable ISO image on a USB drive]
ifndef::openshift-origin[]
* xref:../../path/to/workers.adoc#id[Adding worker nodes to {sno} clusters]
endif::openshift-origin[]
ifdef::openshift-origin[]
* xref:../../path/to/workers.adoc#id[Adding worker nodes to {sno-okd} clusters]
endif::openshift-origin[]
```

This structure must be preserved exactly — do NOT collapse it to only the `ifndef` branch or only the `ifdef` branch.

**Example - Section heading with explanation becomes new module:**

Before (assembly):
```asciidoc
include::modules/understanding-certificates.adoc[leveloffset=+1]

== Adding certificates

You have two options for adding certificates:
* Add to cluster-wide bundle for global trust
* Add to custom bundle for limited scope

include::modules/adding-to-cluster-bundle.adoc[leveloffset=+1]
```

After (assembly):
```asciidoc
include::modules/understanding-certificates.adoc[leveloffset=+1]

include::modules/about-adding-certificates.adoc[leveloffset=+1]

include::modules/adding-to-cluster-bundle.adoc[leveloffset=+2]
```

New module (about-adding-certificates.adoc):
```asciidoc
:_module-type: CONCEPT

[id="about-adding-certificates_{context}"]
= Adding certificates

[role="_abstract"]
You have two options for adding certificates:

* Add to cluster-wide bundle for global trust
* Add to custom bundle for limited scope
```

---

### CalloutList

**AI action plan**
1. **For value callouts**: Replace callout markers (e.g., `<1>`) with user-replaceable placeholders (`<value>`), then convert callout list to description list
2. **For code section callouts**: Remove callouts and convert to bulleted list explaining each section

**Example - Value callouts to description list (multi-line):**

Before:
```asciidoc
----
name: my_secret <1>
data: <2>
----
<1> The secret name.
<2> The secret data.
```

After:
```asciidoc
----
name: <my_secret>
data: <secret_data>
----

where:

`<my_secret>`:: Specifies the secret name.
`<secret_data>`:: Specifies the secret data.
```

**Example - Value callouts to description list (single-line command):**

For single-line commands, only use the replacement value as the description list term, not the entire command line:

Before:
```asciidoc
----
$ oc delete -f <file_name> -n <cluster_namespace> <1>
----
<1> Namespace of the cluster on which LVMS is installed.
```

After:
```asciidoc
----
$ oc delete -f <file_name> -n <cluster_namespace>
----

where:

`<cluster_namespace>`:: Specifies the namespace of the cluster on which LVMS is installed.
```

**Do NOT** use the full command as the description list term:
```asciidoc
// WRONG:
`$ oc delete -f <file_name> -n <cluster_namespace>`:: Namespace of the cluster...
```

---

### RelatedLinks

**AI action plan**
- The "Additional resources" block must contain only an unordered list of links
- Remove any explanatory text
- Ensure links use `xref` or `link` format

**Example:**

Before:
```asciidoc
.Additional resources

You can use any of the following search engines:
* link:http://www.google.com[Google], which is often the default
* link:http://www.duckduckgo.com[DuckDuckGo]
```

After:
```asciidoc
.Additional resources

* link:http://www.google.com[Google search]
* link:http://www.duckduckgo.com[DuckDuckGo search]
```

---

## References

- [Actions and explanations for fixing some errors and warnings](https://github.com/mramendi/asciidoctor-vale-assistant/blob/main/assistant/fixing-instructions-AI.md)
- [Built-in AsciiDoc attributes](https://docs.asciidoctor.org/asciidoc/latest/attributes/character-replacement-ref/)
- [AsciiDoc list continuation](https://docs.asciidoctor.org/asciidoc/latest/lists/continuation/)
- [AsciiDoc open blocks](https://docs.asciidoctor.org/asciidoc/latest/blocks/open-blocks/)
