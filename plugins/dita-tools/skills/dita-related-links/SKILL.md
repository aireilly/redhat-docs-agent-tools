---
name: dita-related-links
description: Fix Additional resources sections by removing or relocating non-link content for DITA compatibility. Use this skill when asked to fix additional resources, clean up related links, or prepare files for DITA conversion.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Glob, Read, Edit, Write
---

# Related links cleanup skill

Fix Additional resources sections by removing non-link content for DITA compatibility.

## Overview

This skill uses the `related_links.rb` Ruby script to find and fix Additional resources sections that contain content other than links. In DITA, the `<related-links>` element can only contain link elements, not arbitrary content.

## What it detects

The Vale rule `RelatedLinks.yml` detects content in Additional resources sections that is not:

- Link macros: `link:url[text]` or `mailto:email[text]`
- Inline links: `https://...` or `<https://...>`
- Xref macros: `xref:target[text]`
- Inline xrefs: `<<target>>`
- Attribute references that resolve to links: `{some-link-attribute}`

## What it normalizes

### Trailing text after links

Links with additional descriptive text are preserved but normalized by removing the trailing text.

**Before:**
```asciidoc
.Additional resources

* link:https://kueue.sigs.k8s.io/docs/concepts/resource_flavor/[Resource Flavor] in the Kueue documentation
* link:https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/[Cluster Queue] in the Kueue documentation
```

**After:**
```asciidoc
.Additional resources

* link:https://kueue.sigs.k8s.io/docs/concepts/resource_flavor/[Resource Flavor]
* link:https://kueue.sigs.k8s.io/docs/concepts/cluster_queue/[Cluster Queue]
```

### Paragraph-style links

Links embedded in paragraph text (e.g., "See also link:...") are converted to proper list items.

**Before:**
```asciidoc
.Additional resources

ifdef::cloud-service[]
See also link:https://docs.redhat.com/en/documentation/openshift_dedicated/index[OpenShift Dedicated cluster administration].
endif::[]
```

**After:**
```asciidoc
.Additional resources

ifdef::cloud-service[]
* link:https://docs.redhat.com/en/documentation/openshift_dedicated/index[OpenShift Dedicated cluster administration]
endif::[]
```

## What it removes

### Paragraphs and explanatory text (without links)

**Before:**
```asciidoc
.Additional resources

This section provides helpful links for further reading.

* link:https://example.com[Example site]
* xref:related-topic[Related topic]
```

**After:**
```asciidoc
.Additional resources

* link:https://example.com[Example site]
* xref:related-topic[Related topic]
```

### Admonitions and notes

**Before:**
```asciidoc
.Additional resources

[NOTE]
====
Remember to check these resources regularly.
====

* link:https://example.com[Example site]
```

**After:**
```asciidoc
.Additional resources

* link:https://example.com[Example site]
```

### Non-link list items

**Before:**
```asciidoc
.Additional resources

* This is just text, not a link
* link:https://example.com[Example site]
* Another plain text item
```

**After:**
```asciidoc
.Additional resources

* link:https://example.com[Example site]
```

## Usage

When the user asks to fix additional resources:

1. Identify the target folder or file containing AsciiDoc content
2. Find all `.adoc` files in the target location
3. Run the Ruby script against each file:
   ```bash
   ruby skills/dita-related-links/scripts/related_links.rb <file>
   ```
4. Report the changes made

### Dry run mode

To preview changes without modifying files:

```bash
ruby skills/dita-related-links/scripts/related_links.rb <file> --dry-run
```

### Output to different file

```bash
ruby skills/dita-related-links/scripts/related_links.rb <file> -o <output.adoc>
```

### Process all files in a directory

```bash
find <folder> -name "*.adoc" -exec ruby skills/dita-related-links/scripts/related_links.rb {} \;
```

## Example invocations

- "Fix additional resources in modules/"
- "Clean up related links in the getting_started folder"
- "Remove non-link content from Additional resources sections"
- "Preview related-links changes in modules/ --dry-run"

## Behavior notes

- **Preserves valid links**: All link items are kept, even those with trailing descriptive text
- **Normalizes trailing text**: Removes trailing text after link macros (e.g., "in the Kueue documentation")
- **Converts paragraph-style links**: Links embedded in prose (e.g., "See also link:...") are converted to list items
- **Removes non-link paragraphs**: Plain text paragraphs without links are removed
- **Removes non-link list items**: List items without links are removed
- **Handles multiple sections**: Multiple Additional resources sections are all processed
- **Skips comments**: Content inside comment blocks is not modified
- **Handles conditionals**: Conditional directives (ifdef/ifndef/endif) are preserved

## Output format

```
<file>: normalized N link(s) in Additional resources
```

Or:

```
<file>: removed N non-link item(s), normalized M link(s) in Additional resources
```

Or:

```
<file>: No issues found in Additional resources
```

Or:

```
<file>: No Additional resources section found
```

## Extension location

The Ruby script is located at: `skills/dita-related-links/scripts/related_links.rb`

## Related Vale rule

This skill addresses the warning from: `.vale/styles/AsciiDocDITA/RelatedLinks.yml`
