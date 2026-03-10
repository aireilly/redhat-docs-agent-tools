---
name: dita-rewrite-shortdesc
description: Rewrite or improve short descriptions in AsciiDoc files for better clarity and DITA compliance. Use this skill when asked to fix short descriptions, improve abstracts, rewrite summaries, or make short descriptions more effective.
model: claude-sonnet-4-20250514
allowed-tools: Read, Edit, Glob, Grep
---

# Rewrite short descriptions

Analyze and rewrite short descriptions in AsciiDoc files for better clarity, conciseness, and DITA compliance.

## Overview

This skill provides LLM-guided analysis and rewriting of short descriptions (paragraphs marked with `[role="_abstract"]`). Use this skill when existing short descriptions need improvement, not just when the abstract attribute is missing.

For adding the `[role="_abstract"]` attribute to files that don't have it, use the **dita-add-shortdesc-abstract** skill instead.

## What is a short description?

A short description is the first paragraph after the document title, marked with `[role="_abstract"]`. It provides a concise summary of the topic's purpose and is used as:

- The first paragraph in rendered output
- Link preview text when hovering over cross-references
- Subordinate topic previews in navigation
- Search result summaries

**Constraint**: A short description must be exactly one paragraph, under 50 words.

## General rules

- **Keep it standalone, concise, and complete.** Don't rely on the surrounding topic for meaning.
- **One or two sentences, under 50 words.**
- **Use complete sentences.** Avoid fragments except for very short API references.
- **Don't repeat the title**, state the obvious, start with "this topic…," or treat it as a lead-in sentence.

## Writing tips

- Focus on clarity and utility.
- If you can't fit a clear summary within ~50 words, the topic may be too complex and could need splitting.
- Including a short description encourages topic clarity and improves navigation and search results.

## CONCEPT topic guidance

Concept topics answer "what is this?" and "why should I care?" Start with a brief definition if the term is unfamiliar. Make the main point clear.

**Poor (repeats title, lead-in style):**
```asciidoc
= About model optimization

[role="_abstract"]
This topic explains about model optimization.
```

**Good (standalone, explains value):**
```asciidoc
= About model optimization

[role="_abstract"]
Model optimization reduces neural network size and inference time through techniques like quantization and pruning, enabling AI applications to run efficiently on resource-constrained devices without significant accuracy loss.
```

## PROCEDURE topic guidance

Procedure topics explain what the task does, its benefits or purpose, and when or why the user should perform it. Include who performs the task if relevant.

**Poor (states the obvious):**
```asciidoc
= Configuring authentication

[role="_abstract"]
Follow these steps to configure authentication.
```

**Good (explains purpose and benefit):**
```asciidoc
= Configuring authentication

[role="_abstract"]
Configure LDAP authentication to enable single sign-on for your organization, allowing users to access the application with their existing corporate credentials.
```

**Good (includes who and when):**
```asciidoc
= Rotating encryption keys

[role="_abstract"]
Cluster administrators should rotate encryption keys annually or immediately after a security incident to maintain compliance and protect sensitive data at rest.
```

## REFERENCE topic guidance

Reference topics describe what the items are, what they do, and what they're used for. Use consistent phrasing across topics.

**Poor (vague, no context):**
```asciidoc
= Configuration parameters

[role="_abstract"]
The following table lists configuration parameters.
```

**Good (describes purpose and usage):**
```asciidoc
= Configuration parameters

[role="_abstract"]
The following configuration parameters control memory allocation, connection pooling, and timeout behavior for the database driver. Set these values in the `application.properties` file before starting the server.
```

**Good (consistent reference style):**
```asciidoc
= Environment variables for the CLI

[role="_abstract"]
Use the following environment variables to configure authentication, output format, and logging behavior when running commands non-interactively or in CI/CD pipelines.
```

## Usage

When the user asks to rewrite or improve short descriptions:

1. Read the target file(s)
2. Identify the current short description (paragraph after `[role="_abstract"]`)
3. Analyze the module content to understand its purpose
4. Determine the content type (CONCEPT, PROCEDURE, REFERENCE)
5. Rewrite the short description following the guidance above
6. Use the Edit tool to update the file

### Workflow

```
1. Read the file
2. Identify content type from :_mod-docs-content-type: attribute
3. Find the [role="_abstract"] paragraph
4. Analyze the full module content
5. Draft a new short description that:
   - Summarizes the topic's purpose
   - Stays under 50 words
   - Follows content-type-specific guidance
6. Edit the file to replace the old short description
```

## Example invocations

- "Rewrite the short description in modules/con-overview.adoc"
- "Improve the abstracts in the getting_started folder"
- "Fix poorly written short descriptions in modules/"
- "Make the short descriptions more concise"

## Common problems to fix

| Problem | Solution |
|---------|----------|
| Repeats the title | Summarize purpose/value instead |
| Starts with "This topic..." | Start with actionable content |
| Too vague | Add specific details about what/why |
| Too long (>50 words) | Condense to essential points |
| Lead-in style | Make it standalone and complete |
| States the obvious | Explain benefits or context |

## Related skills

- **dita-add-shortdesc-abstract**: For adding `[role="_abstract"]` to files missing it
- **dita-asciidoc-rewrite**: For comprehensive DITA issue fixing

## Related Vale rule

This skill helps improve content flagged by: `.vale/styles/AsciiDocDITA/ShortDescription.yml`
