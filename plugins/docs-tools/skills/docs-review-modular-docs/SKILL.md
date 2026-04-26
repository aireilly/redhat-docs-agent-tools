---
context: fork
name: docs-review-modular-docs
description: Review AsciiDoc (.adoc) files for Red Hat modular documentation compliance — module types (concept, procedure, reference), assembly structure, anchor IDs, context variables, leveloffset, and include directives. Use this skill whenever someone asks about modular docs, checks .adoc file structure, asks if a module is the right type, needs to verify anchor IDs have _{context}, or reviews assemblies. Also triggers for questions about concept vs procedure vs reference modules, prerequisites formatting, or Red Hat doc structure.
---

# Modular documentation review skill

Review AsciiDoc source files for Red Hat modular documentation compliance: module types, required sections, anchor IDs, and assembly structure.

**Applies to**: `.adoc` files only

For detailed module type guidance, templates, and structural rules, read [asciidoc-reference.md](../../reference/asciidoc-reference.md). It contains full descriptions of each module type, required/optional parts, templates, and examples.

## Concept checklist

- [ ] Title is noun phrase (NOT gerund) and uses sentence case (not Title Case)
- [ ] Anchor ID includes `_{context}`
- [ ] Introduction provides overview (what and why)
- [ ] No step-by-step instructions (those belong in procedures)
- [ ] Actions avoided unless highly context-dependent
- [ ] If subheadings used, first tried splitting into separate modules
- [ ] Standard subheadings (included in TOC) have anchor IDs with `_{context}`: `[#anchor-id_{context}]`
- [ ] Only valid admonition types used: NOTE, IMPORTANT, WARNING, TIP (CAUTION is not supported by the Red Hat Customer Portal)
- [ ] Additional resources focused on relevant items only

## Procedure checklist

- [ ] Title uses imperative phrase (verb without -ing) and sentence case (not Title Case)
- [ ] Anchor ID includes `_{context}`
- [ ] Introduction explains why and where
- [ ] `.Procedure` section present with numbered steps
- [ ] Each step describes ONE action
- [ ] Steps use imperative form ("Click...", "Run...")
- [ ] Single-step procedures use bullet (`*`) not number
- [ ] No custom subheadings - only allowed sections used
- [ ] `.Next steps` contains links only, not instructions
- [ ] Prerequisites written as conditions, not instructions
- [ ] Only valid admonition types used: NOTE, IMPORTANT, WARNING, TIP (CAUTION is not supported by the Red Hat Customer Portal)
- [ ] Optional sections in correct order: Limitations, Prerequisites, Verification, Troubleshooting, Next steps, Additional resources

## Reference checklist

- [ ] Title is noun phrase and uses sentence case (not Title Case)
- [ ] Anchor ID includes `_{context}`
- [ ] Introduction explains what data is provided
- [ ] Body uses tables or labeled lists
- [ ] Data logically organized (alphabetical, categorical)
- [ ] Consistent structure for similar data
- [ ] Standard subheadings (included in TOC) have anchor IDs with `_{context}`: `[#anchor-id_{context}]`
- [ ] Additional resources focused on relevant items only

## Assembly checklist

- [ ] Title matches content (imperative if procedures included)
- [ ] Anchor ID does NOT include `_{context}`
- [ ] Context variable set: `:context: my-assembly-name`
- [ ] Introduction explains what user accomplishes
- [ ] Modules included with `leveloffset=` and appropriate level
- [ ] Next steps and Additional resources in correct order

## Common violations

| Issue | Wrong | Correct |
|-------|-------|---------|
| Missing context | `[id="my-assembly"]` | `[id="my-module_{context}"]` |
| Standard subheading without anchor ID | `== Subheading` | `[#anchor-id_{context}]` then `== Subheading` |
| Procedure title | `= Database Configuration` | `= Configure the database` |
| Custom subheading in procedure | `== Additional setup` | Use allowed sections only |
| Instructions in Next steps | Numbered steps | Links only |
| Module contains module | `include::` of module | Only snippets in modules |
| Missing leveloffset | `include::mod.adoc[]` | `include::mod.adoc[leveloffset=+1]` |
| Prerequisite as step | `* Install JDK 11` | `* JDK 11 is installed.` |
| Deep assembly nesting | Many levels of nested assemblies | Link to assemblies instead |
| Writers defining user stories | Writer creates user story | Product management defines user stories |

## How to use

1. Verify file is `.adoc` format
2. Identify module type from content (concept, procedure, reference, assembly)
3. Check required parts are present using the checklists above
4. Verify anchor ID includes `_{context}` (except assemblies)
5. Check for common violations
6. Mark issues as **required** (modular violations) or **[SUGGESTION]**

## Example invocations

- "Review this procedure module for modular docs compliance"
- "Check if this assembly follows Red Hat modular guidelines"
- "Verify the anchor IDs include context variable"
- "Do a modular docs review on modules/\*.adoc"

## Integrates with

- **lint-with-vale**: Run `vale <file>` for automated style linting

## References

- Red Hat Modular Documentation Guide: https://redhat-documentation.github.io/modular-docs/
- Templates and detailed reference: [asciidoc-reference.md](../../reference/asciidoc-reference.md)
