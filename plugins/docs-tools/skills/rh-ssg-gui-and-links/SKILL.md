---
name: rh-ssg-gui-and-links
description: Review documentation for Red Hat Supplementary Style Guide graphical interface and link issues including UI elements, screenshots, link text, cross-references, and external links. Use this skill for GUI and links-focused peer reviews of Red Hat docs.
model: claude-opus-4-5@20251101
---

# Red Hat SSG: Graphical Interfaces and Links review skill

Review documentation for GUI and link compliance with the Red Hat Supplementary Style Guide.

## Checklist

### Screenshots

- [ ] Screenshots are avoided where possible (for accessibility and localization)
- [ ] If screenshots are used, alt text is unique and descriptive

### Text entry

- [ ] "Enter" is used (not "type" or "input") for user text entry
- [ ] The text to enter is in monospace: `In the *Name* field, enter \`test-postgresql\`.`

### User interface elements

- [ ] All GUI element names use bold text: `*Installed Operators*`
- [ ] Bold is used even for non-clickable elements if the name appears in the GUI
- [ ] Unlabeled elements use a generic description without bold: "the search field" not "the **Search** field"

### Cross-references

- [ ] Cross-references are included only when necessary
- [ ] Critical information is included inline rather than cross-referenced
- [ ] Format: `For more information about <topic>, see xref:<link>[<link_text>].`

### External links

- [ ] Links to non-Red Hat/IBM sites are avoided unless necessary
- [ ] Links use top-level pages, not deep links (which break more frequently)
- [ ] No bare URLs — always include descriptive link text
- [ ] No URL shorteners
- [ ] Meaningful link text describes the target content (not "click here")
- [ ] `nofollow` link option is not used unless absolutely necessary

### Links to Red Hat documentation

- [ ] Red Hat docs links use `latest` in the URL path
- [ ] Format: `https://docs.redhat.com/en/documentation/.../latest/html/...`

### Links to Knowledgebase articles

- [ ] Link text uses the article title or descriptive running text
- [ ] In "Additional resources" sections: article title followed by `(Red Hat Knowledgebase)` within the link

## How to use

1. Review only changed content and necessary context
2. For each issue found, cite the relevant SSG section
3. Mark issues as **required** (bare URLs, missing alt text on screenshots) or **[SUGGESTION]** (improvements)

## Example invocations

- "Review UI elements and links in this module"
- "Check link formatting in assembly_getting-started.adoc"
- "Do an SSG GUI and links review on the changed files"

## References

For detailed guidance, consult:
- [Red Hat Supplementary Style Guide: Graphical interfaces](https://redhat-documentation.github.io/supplementary-style-guide/#graphical-interfaces)
- [Red Hat Supplementary Style Guide: Links](https://redhat-documentation.github.io/supplementary-style-guide/#links)
- [PatternFly UX writing](https://www.patternfly.org/ux-writing/about)
