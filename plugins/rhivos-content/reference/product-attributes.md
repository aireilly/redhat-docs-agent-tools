# RHIVOS Product Attributes

Product attributes for use in AsciiDoc content. These replace hardcoded product names to enable single-sourcing and consistency.

## Required attributes

Set these in the doc-level `master.adoc` or equivalent entry point:

```asciidoc
:ProductName: Red Hat In-Vehicle Operating System
:ProductShortName: RHIVOS
:ProductVersion: 2.0
:ProductRelease: 2.0 Core
```

## Upstream-to-downstream substitution map

When converting from upstream CentOS Automotive SIG content, apply these substitutions:

| Upstream term | Downstream attribute |
|---------------|---------------------|
| AutoSD | `{ProductName}` |
| Automotive Stream Distribution | `{ProductName}` |
| CentOS Automotive SIG | Red Hat |
| sig-docs | RHIVOS documentation |
| autosd | `{ProductShortName}` |

## Usage rules

- Always use `{ProductName}` on first mention in a module, `{ProductShortName}` thereafter
- Never hardcode "RHIVOS" or "Red Hat In-Vehicle Operating System" in module body text
- Attribute definitions belong in the assembly or master entry point, not in individual modules
- Version-specific references use `{ProductVersion}` or `{ProductRelease}`

## ASIL B and functional safety attributes

For safety-critical content:

```asciidoc
:ASILB: ASIL B
:FuSa: functional safety
```

- ASIL B references in body text must appear inside admonition blocks (IMPORTANT, WARNING, NOTE, TIP) or in the module abstract
- Safety Guidance document references must be italicized: `_RHIVOS Safety Guidance_`
- Use `include::snip_fusa-disclaimer.adoc[]` for the standard functional safety disclaimer
