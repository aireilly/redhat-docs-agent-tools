---
name: rh-ssg-technical-examples
description: Review documentation for Red Hat Supplementary Style Guide technical example issues including root privileges, IP addresses, code examples, and syntax highlighting. Use this skill for technical-examples-focused peer reviews of Red Hat docs.
model: claude-opus-4-5@20251101
---

# Red Hat SSG: Technical Examples review skill

Review documentation for technical example compliance with the Red Hat Supplementary Style Guide.

## Checklist

### Commands requiring root privileges

- [ ] Commands requiring root privileges use `sudo` prefix, not `su -`
- [ ] Commands with `sudo` use the `$` prompt, not `#`
- [ ] Shell prompts alone are not the only indicator of required privilege level — step text, intro, or prerequisites also state the requirement
- [ ] If multiple commands require root, introductory text mentions it: "Some tasks in this procedure require root privileges..."

### Ellipses in YAML code blocks

- [ ] Ellipses in YAML use `# ...` (commented out), not bare `...`
- [ ] Bare `...` in YAML is reserved for "end of document" per YAML spec

### IP addresses and MAC addresses

- [ ] Example IPv4 addresses use RFC 5737 reserved ranges:
  - `192.0.2.0/24`
  - `198.51.100.0/24`
  - `203.0.113.0/24`
- [ ] Example IPv6 addresses use RFC 3849 reserved range: `2001:0DB8::/32`
- [ ] Example MAC addresses use RFC 7042 reserved ranges:
  - Unicast: `00:00:5E:00:53:00` – `00:00:5E:00:53:FF`
  - Multicast: `01:00:5E:90:10:00` – `01:00:5E:90:10:FF`
- [ ] No real IP or MAC addresses are used in examples

### Long code examples

- [ ] All code blocks are necessary, accurate, and helpful
- [ ] Code blocks are copy-and-paste friendly (except for user-replaced values)

### Syntax highlighting

- [ ] Source language is provided when supported: `[source,yaml]`, `[source,xml]`, etc.
- [ ] `bash` is NOT used for terminal commands — it misinterprets `#` as a comment instead of a root prompt
- [ ] Use `terminal` or `console` or omit the source language for shell commands

## How to use

1. Review only changed content and necessary context
2. For each issue found, cite the relevant SSG section
3. Mark issues as **required** (real IP addresses, `bash` source language for shell commands) or **[SUGGESTION]** (improvements)

## Example invocations

- "Review technical examples in this procedure module"
- "Check IP addresses and code blocks in proc_configuring-network.adoc"
- "Do an SSG technical examples review on the changed files"

## References

For detailed guidance, consult:
- [Red Hat Supplementary Style Guide: Technical examples](https://redhat-documentation.github.io/supplementary-style-guide/#technical-examples)
