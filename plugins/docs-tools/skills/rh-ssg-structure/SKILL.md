---
name: rh-ssg-structure
description: Review documentation for Red Hat Supplementary Style Guide structure issues including admonitions, lead-in sentences, prerequisites, and short descriptions. Use this skill for structure-focused peer reviews of Red Hat docs.
model: claude-opus-4-5@20251101
---

# Red Hat SSG: Structure review skill

Review documentation for structural compliance with the Red Hat Supplementary Style Guide.

## Checklist

### Admonitions

- [ ] Admonitions are kept to a minimum; no multiple admonitions clustered together
- [ ] Only valid types are used: NOTE, IMPORTANT, WARNING, TIP
- [ ] CAUTION admonition is not used (not supported by Red Hat Customer Portal)
- [ ] Admonitions are short and concise — no procedures inside admonitions
- [ ] Only singular admonition headings ("NOTE" not "NOTES")
- [ ] Modules do not start with an admonition — a short description must come first

### Lead-in sentences

- [ ] No unnecessary lead-in sentences after "Prerequisites" or "Procedure" headings
- [ ] Lead-in sentences are used only when needed for navigation or clarity (e.g., grouping long prerequisite lists, emphasizing all steps must be completed)
- [ ] Lead-in sentences are complete sentences (not fragments)

### Prerequisites

- [ ] Prerequisites are written as checks or completed states, not imperative commands
- [ ] Passive voice is acceptable when the agent is unknown or unimportant: "JDK 11 or later is installed"
- [ ] Imperative formations are avoided: not "Install JDK 11" but "JDK 11 or later is installed"
- [ ] Parallel language is used across all prerequisite bullets

### Short descriptions

- [ ] Every module and assembly has a short description (abstract) before the main content
- [ ] Short descriptions are 2–3 sentences
- [ ] Short descriptions include **what** users must do and **why** they must do it
- [ ] Product name appears in either the title or short description
- [ ] No self-referential language: not "This topic covers..." or "Use this procedure to..."
- [ ] No feature-focused language: not "This product allows you to..."
- [ ] Customer-centric language is used: "You can... by..." or "To..., configure..."
- [ ] Active voice and present tense are used

## How to use

1. Review only changed content and necessary context
2. For each issue found, cite the relevant SSG section
3. Mark issues as **required** (missing short description, CAUTION admonition used, imperative prerequisites) or **[SUGGESTION]** (improvements)

## Example invocations

- "Review structure in this procedure module"
- "Check admonitions and prerequisites in proc_configuring-auth.adoc"
- "Do an SSG structure review on the changed modules"

## References

For detailed guidance, consult:
- [Red Hat Supplementary Style Guide: Structure](https://redhat-documentation.github.io/supplementary-style-guide/#structure)
- [Modular Documentation Reference Guide](https://redhat-documentation.github.io/modular-docs/)
