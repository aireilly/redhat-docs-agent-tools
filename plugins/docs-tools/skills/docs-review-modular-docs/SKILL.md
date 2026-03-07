---
name: docs-review-modular-docs
description: Review AsciiDoc files for Red Hat modular documentation compliance including module types, structure, and assembly formation. Use this skill for modular docs-focused peer reviews of .adoc files only.
---

# Modular documentation review skill

Review AsciiDoc source files for Red Hat modular documentation compliance: module types, required sections, anchor IDs, and assembly structure.

**Applies to**: `.adoc` files only

---

## Module types overview

| Type | Purpose | Title format |
|------|---------|--------------|
| Concept | Explain what something is | Noun phrase |
| Procedure | Step-by-step instructions | Imperative phrase (verb) |
| Reference | Lookup data (tables, lists) | Noun phrase |
| Assembly | Combine modules into user story | Imperative if includes procedures |

---

## Concept modules (understand)

A concept module gives users descriptions and explanations needed to understand and use a product.

### Required parts

1. **Title**: H1 heading (`= Title`) with noun phrase
2. **Anchor ID**: With context variable `[id="concept-name_{context}"]`
3. **Introduction**: Single, concise paragraph answering:
   - What is the concept?
   - Why should the user care?
4. **Body**: Explanation using paragraphs, lists, tables, examples, diagrams

### Optional parts

- Additional resources section
- Subheadings (if content cannot be split into separate modules)

### Concept body

**Allowed elements**:
- Paragraphs
- Lists
- Tables
- Examples
- Graphics or diagrams (to speed up understanding)

**Actions in concept modules**:
- **Generally avoid** instructions to perform actions (those belong in procedure modules)
- **Exception**: Simple actions that are highly dependent on context and have no place in any procedure module
- **If including actions**: Ensure the heading remains a noun phrase, NOT an imperative

### Subheadings in concept modules

If a concept module is large and complex:

1. **First try**: Split into multiple standalone concept modules
2. **If that is not possible**: Use subheadings to structure content

**Subheading options**:
- **Discrete subheading** (excluded from TOC): `[discrete]` followed by `== Subheading`
- **Standard subheading** (included in TOC): `== Subheading`

**Note**: Subheadings are allowed in concept and reference modules, but NOT in procedure modules.

### Finding concepts to document

- Look at **nouns** in related procedure modules and assemblies
- Explain only things that are **visible to users**
- Even if a concept is interesting, it probably does not require explanation if it is not visible to users

### Types of conceptual information

- **Principle**: Fundamental truth or rule
- **Concept**: Abstract idea or general notion
- **Structure**: Organization or arrangement
- **Process**: Series of actions or steps
- **Fact**: Verified piece of information

### Concept checklist

- [ ] Title is noun phrase (NOT gerund)
- [ ] Anchor ID includes `_{context}`
- [ ] Introduction provides overview (what and why)
- [ ] No step-by-step instructions (those belong in procedures)
- [ ] Actions avoided unless highly context-dependent
- [ ] If subheadings used, first tried splitting into separate modules
- [ ] Additional resources focused on relevant items only

---

## Procedure modules (do)

Procedure modules explain how to do something. They contain numbered, step-by-step instructions to help users accomplish a single task.

### Required parts

1. **Title**: H1 heading with **imperative phrase** ("Configure...", "Install...", "Deploy...")
2. **Anchor ID**: With context variable `[id="procedure-name_{context}"]`
3. **Introduction**: Short paragraph providing context
4. **Procedure section**: One or more numbered steps

### Optional parts (in this order only)

1. `.Limitations` - Bulleted list of limitations (not used often)
2. `.Prerequisites` - Bulleted list of conditions
3. `.Verification` - Steps to verify success
4. `.Troubleshooting` - Keep short; consider separate module
5. `.Next steps` - **Links only, NOT instructions**
6. `.Additional resources` - Links to related material

**Critical rule**: Do NOT change or embellish these subheading names. Do NOT create additional subheadings unless absolutely necessary.

### Procedure introduction

A short paragraph that provides context and overview.

**Should include**:
- What the module will help the user do
- Why it will be beneficial to the user
- Key words for search engine optimization

**Key questions to answer**:
- Why perform this procedure?
- Where do you perform this procedure?
- Special considerations specific to the procedure

### Limitations section

**Requirements**:
- Use bulleted list
- Use plural heading "Limitations" even if only one limitation exists
- Not used often

### Prerequisites section

Conditions that must be satisfied before the user starts the procedure.

**Requirements**:
- Use bulleted list
- Use plural heading "Prerequisites" even if only one prerequisite exists
- Can be full sentences or sentence fragments (must be parallel)
- Focus on relevant prerequisites users might not be aware of
- Do NOT list obvious prerequisites

**Best practice**: If a prerequisite applies to all procedures in a user story, list it in the assembly file instead.

**Good** (conditions):
- "JDK 11 or later is installed."
- "You are logged in to the console."
- "A running Kubernetes cluster."

**Bad** (instructions):
- "Install JDK 11" - this is a step, not a prerequisite
- "You should have JDK 11" - "should" is unnecessary

### Procedure section

**Requirements**:
- Each step describes one action
- Written in imperative form (e.g., "Do this action")
- Use numbered list for multiple steps
- Use unnumbered bullet for single-step procedures

**Important note**: Not all numbered lists are procedures. You can also use numbered lists for non-procedural sequences (e.g., process flow of system actions).

### Verification section

Steps to verify that the procedure provided the intended outcome.

**Can include**:
- Example of expected command output
- Pop-up window the user should see when successful
- Actions to complete (e.g., entering a command) to determine success or failure

### Troubleshooting section

**Requirements**:
- Keep this section short
- Not used often
- Consider whether the information might be better as:
  - A separate troubleshooting procedure
  - Part of a reference module with other troubleshooting sections

### Next steps section

Links to resources with instructions that might be useful after completing this procedure.

**Critical warning**: Do NOT use "Next steps" to provide a second list of instructions. It is for links only.

### Additional resources section

Links to closely related material:
- Other documentation resources
- Instructional videos
- Labs

**Best practice**:
- Focus on relevant resources that might interest the user
- Do NOT list resources just for completeness
- If a resource applies to all modules in a user story, list it in the assembly file instead

### No subheadings in procedures

You cannot use custom subheadings in procedure modules. Only use the allowed optional sections listed above.

### Procedure checklist

- [ ] Title uses imperative phrase (verb without -ing)
- [ ] Anchor ID includes `_{context}`
- [ ] Introduction explains why and where
- [ ] `.Procedure` section present with numbered steps
- [ ] Each step describes ONE action
- [ ] Steps use imperative form ("Click...", "Run...")
- [ ] Single-step procedures use bullet (`*`) not number
- [ ] No custom subheadings - only allowed sections used
- [ ] `.Next steps` contains links only, not instructions
- [ ] Prerequisites written as conditions, not instructions
- [ ] Optional sections in correct order

---

## Reference modules (lookup)

Reference modules provide data that users might want to look up, but do not need to remember.

### Common examples

- List of commands users can use with an application
- Table of configuration files with definitions and usage examples
- List of default settings for a product
- API parameters and options
- Environment variables

### Required parts

1. **Title**: H1 heading (`= Title`) with noun phrase
2. **Anchor ID**: With context variable `[id="reference-name_{context}"]`
3. **Introduction**: Single, concise paragraph
4. **Body**: Reference data in structured format (tables, lists)

### Optional parts

- Additional resources section
- Subheadings (if content cannot be split)

### Reference introduction

A single, concise paragraph that provides a short overview of the module.

**Purpose**: Enables users to quickly determine whether the reference is useful without reading the entire module.

### Reference body

A very strict structure, often in the form of a list or table.

**Key principle**: A well-organized reference module enables users to scan it quickly to find the details they want.

**Organization options**:
- Logical order (e.g., alphabetically)
- Table format
- Labeled lists
- Unordered lists

**Recommended AsciiDoc markup**:
- Lists (unordered, labeled)
- Tables

**For large volumes of similar data**:
- Use a consistent structure
- Document each logical unit as one reference module
- Think of man pages: different information but consistent titles and formats

### Subheadings in reference modules

If a reference module is large and complex:

1. **First try**: Split into multiple standalone reference modules
2. **If that is not possible**: Use subheadings to structure content

**Subheading options**:
- **Discrete subheading** (excluded from TOC): `[discrete]` followed by `== Subheading`
- **Standard subheading** (included in TOC): `== Subheading`

**Note**: Subheadings are allowed in concept and reference modules, but NOT in procedure modules.

### Lists vs. tables

Consider these factors when choosing between lists and tables:
- Tables are better for multi-dimensional data
- Lists are easier to scan for simple key-value pairs
- Tables provide better structure for complex relationships

### Reference checklist

- [ ] Title is noun phrase
- [ ] Anchor ID includes `_{context}`
- [ ] Introduction explains what data is provided
- [ ] Body uses tables or labeled lists
- [ ] Data logically organized (alphabetical, categorical)
- [ ] Consistent structure for similar data
- [ ] Additional resources focused on relevant items only

---

## Assemblies

An assembly is a collection of modules that describes how to accomplish a user story.

### Required parts

1. **Title**: Imperative form if includes procedures, noun phrase otherwise
2. **Anchor ID**: With context variable `[id="assembly-name"]` **Do not use _{context} in assembly IDs**
3. **Context variable**: Set before module includes
4. **Introduction**: Explains what user accomplishes
5. **Modules**: One or more included modules

### Optional parts

- Prerequisites (before modules)
- Next steps (after modules)
- Additional resources (after modules)

### Assembly title guidelines

- **With procedure modules**: Use imperative form (e.g., "Encrypt block devices using LUKS")
- **Without procedure modules**: Use noun phrase (e.g., "Red Hat Process Automation Manager API reference")

### Assembly introduction

The introduction explains what the user accomplishes by working through the assembled modules.

**Technique**: Reword the user story to write the assembly introduction.

**Example transformation**:
- **User story**: "As an administrator, I want to provide external identity, authentication and authorization services for my Atomic Host, so that users from external identity sources can access the Atomic Host."
- **Assembly introduction**: "As a system administrator, you can use SSSD in a container to provide external identity, authentication, and authorization services for the Atomic Host system. This enables users from external identity sources to authenticate to the Atomic Host."

### Prerequisites section

- Conditions that must be satisfied before starting the assembly
- Applicable to all modules in the assembly
- Use second-level heading syntax (`==`) for table of contents display

### Including modules

Use the AsciiDoc `include` directive with `leveloffset` attribute:

```asciidoc
:context: my-assembly-name

include::modules/con-my-concept.adoc[leveloffset=+1]
include::modules/proc-my-procedure.adoc[leveloffset=+1]
include::modules/ref-my-reference.adoc[leveloffset=+1]
```

**Critical rule**: All module and assembly titles must use H1 heading (`= My heading`)

### Next steps and Additional resources

- Optional sections at the end of the assembly
- If using both, list **Next steps** first, then **Additional resources**
- Focus on relevant resources that might interest the user
- Do NOT list resources just for completeness

**Warning**: If the last module in the assembly also has Next steps or Additional resources, check the rendered HTML and consider rewriting or reorganizing.

### Assembly checklist

- [ ] Title matches content (imperative if procedures included)
- [ ] Anchor ID does not include `_{context}`
- [ ] Context variable set: `:context: my-assembly-name`
- [ ] Introduction explains what user accomplishes
- [ ] Modules included with `leveloffset=` and appropriate level
- [ ] Next steps and Additional resources in correct order

---

## Creating modules

### Module types

1. **Concept modules**: Explain concepts and ideas (understand modules)
2. **Procedure modules**: Describe step-by-step actions (do modules)
3. **Reference modules**: Provide lookup data (reference modules)

### Critical rules

**Modules should NOT contain other modules**

A module should not contain another module. However, a module can contain a text snippet.

### Anchor IDs and context

All CONCEPT, PROCEDURE, and REFERENCE module anchor IDs must include the `{context}` variable with an underscore:

```asciidoc
[id="module-name_{context}"]
= Module Title
```

---

## Text snippets

A text snippet is a section of text stored in an AsciiDoc file that is reused in multiple modules or assemblies.

### Key requirements

- A text snippet is NOT a module
- Cannot include structural elements (anchor ID, H1 heading)
- Prefix file name with `snip-` or `snip_`, OR add `:_mod-docs-content-type: SNIPPET`

### Examples of snippets

- One or more paragraphs of text
- A step or series of steps in a procedure
- A table or list
- A note (e.g., technology preview disclaimer)

### Usage

```asciidoc
include::snippets/snip-beta-note.adoc[]
```

---

## Common violations

| Issue | Wrong | Correct |
|-------|-------|---------|
| Missing context | `[id="my-assembly"]` | `[id="my-module_{context}"]` |
| Procedure title | `= Database Configuration` | `= Configure the database` |
| Custom subheading in procedure | `== Additional setup` | Use allowed sections only |
| Instructions in Next steps | Numbered steps | Links only |
| Module contains module | `include::` of module | Only snippets in modules |
| Missing leveloffset | `include::mod.adoc[]` | `include::mod.adoc[leveloffset=+1]` |
| Prerequisite as step | `* Install JDK 11` | `* JDK 11 is installed.` |
| Deep assembly nesting | Many levels of nested assemblies | Link to assemblies instead |
| Writers defining user stories | Writer creates user story | Product management defines user stories |

---

## How to use

1. Verify file is `.adoc` format
2. Identify module type from content (concept, procedure, reference, assembly)
3. Check required parts are present
4. Verify anchor ID includes `_{context}`
5. Check for common violations
6. Mark issues as **required** (modular violations) or **[SUGGESTION]**

## Example invocations

- "Review this procedure module for modular docs compliance"
- "Check if this assembly follows Red Hat modular guidelines"
- "Verify the anchor IDs include context variable"
- "Do a modular docs review on modules/\*.adoc"

## Integrates with

- **Vale skill**: Run `vale <file>` for automated style linting

## References

- Red Hat Modular Documentation Guide: https://redhat-documentation.github.io/modular-docs/
