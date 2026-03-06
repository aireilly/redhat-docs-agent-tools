---
name: rh-ssg-grammar-and-language
description: Review documentation for Red Hat Supplementary Style Guide grammar and language issues including conscious language, contractions, conversational style, minimalism, and user references. Use this skill for grammar-focused peer reviews of Red Hat docs.
model: claude-opus-4-5@20251101
---

# Red Hat SSG: Grammar and Language review skill

Review documentation for grammar and language compliance with the Red Hat Supplementary Style Guide. This supplements the IBM Style Guide — Red Hat-specific rules take precedence.

## Checklist

### Conscious language

- [ ] No instances of "blacklist" or "whitelist" — use "blocklist/allowlist", "denylist/allowlist", or "blocklist/passlist"
- [ ] No instances of "master" or "slave" — use "primary/secondary", "source/replica", "controller/worker", or "initiator/responder"
- [ ] Replacement terms are consistent with what engineering uses in the product

### Contractions

- [ ] No contractions in standard product documentation
- [ ] Contractions are acceptable only in content using "fairly conversational" or "more conversational" style (quick starts, cloud services docs)

### Conversational style

- [ ] Default style is "less conversational" for most product documentation
- [ ] "Fairly conversational" style is used only for new-user content or cloud services
- [ ] "Least conversational" style is used for API documentation and expert audiences

### Minimalism

- [ ] Content is action-oriented and focused on customer goals (Principle 1)
- [ ] Conceptual and background information is separated from procedural tasks
- [ ] Content is scannable: short paragraphs, short sentences, bulleted lists (Principle 2)
- [ ] Titles and headings are 3–11 words with clear, familiar keywords (Principle 3)
- [ ] No long introductions or unnecessary context; sentences are concise (Principle 4)
- [ ] Troubleshooting, error recovery, and verification steps are included where needed (Principle 5)

### Users

- [ ] Animate users (people) use "who": "Users who want to install..."
- [ ] Inanimate users (system accounts like `root`, SELinux users) use "that": "Specify a user that is allowed..."
- [ ] No mixing of animate/inanimate pronouns for the same user type

### Abbreviations and acronyms

- [ ] Do NOT flag command names, utility names, tool names, or executable names as undefined acronyms — these are proper nouns or literal strings, not abbreviations (for example, `db2trc`, `ULOAD`, `SETUP`, `oc`, `kubectl`, `podman`)

### Homographs

- [ ] Words with multiple meanings (application, attribute, block, object, project) are not used ambiguously near each other

## How to use

1. Review only changed content and necessary context
2. For each issue found, cite the relevant SSG section
3. Mark issues as **required** (conscious language violations, incorrect contractions) or **[SUGGESTION]** (minimalism improvements)

## Example invocations

- "Review this file for Red Hat grammar and language issues"
- "Check conscious language compliance in modules/con_overview.adoc"
- "Do an SSG grammar review on the changed modules"

## References

For detailed guidance, consult:
- [Red Hat Supplementary Style Guide: Grammar and language](https://redhat-documentation.github.io/supplementary-style-guide/#grammar-and-language)
- IBM Style Guide (primary reference)
