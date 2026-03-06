---
name: ibm-sg-technical-elements
description: Review documentation for IBM Style Guide technical element issues including code examples, commands, UI elements, keyboard keys, and file paths. Use this skill for technical-element-focused peer reviews.
model: claude-opus-4-5@20251101
---

# IBM Style Guide: Technical Elements review skill

Review documentation for technical element issues: code examples, command line, command syntax, files, keyboard keys, menus, UI elements, and web addresses.

## Checklist

### Code examples

- [ ] Code blocks use monospace formatting, not plain text or screenshots
- [ ] Examples are complete and runnable when possible
- [ ] Fenced code blocks specify the language: ```python, ```yaml, ```json
- [ ] Realistic variable names and values are used, not "foo," "bar," "baz"
- [ ] Example domains use RFC 2606: example.com
- [ ] Example IPs use RFC 5737: 192.0.2.x, 198.51.100.x, 203.0.113.x
- [ ] Placeholder values cannot be mistaken for real values

### Command line

- [ ] All commands are in monospace: `kubectl get pods`
- [ ] Command prompts indicate user type where relevant: `$` (user), `#` (root)
- [ ] Prompt characters are not included in copyable command blocks
- [ ] One command per line
- [ ] Long commands use backslash (\) for line continuation
- [ ] Command output is shown separately from the command

### Command syntax

- [ ] Syntax conventions are consistent:
  - `command` — literal text (monospace)
  - `<variable>` — required user-supplied values
  - `[optional]` — optional parameters
  - `{choice1 | choice2}` — mutually exclusive required choices
  - `...` — repeatable elements
- [ ] Every parameter is explained in a table or description list
- [ ] Syntax notation is not mixed within a document

### Commands

- [ ] Command names are in monospace: `grep`, `kubectl`, `docker`
- [ ] Lowercase command names are not capitalized
- [ ] Imperative mood is used: "Run the `deploy` command" not "The `deploy` command should be run"

### Files and directories

- [ ] File names and paths are in monospace: `config.yaml`, `/etc/hosts`
- [ ] Forward slashes (/) are used for paths in cross-platform docs
- [ ] "File name" is two words (not "filename")
- [ ] "Directory" or "folder" is used consistently (prefer "directory" in CLI contexts)
- [ ] File extensions are included: `README.md` not `README`

### Keyboard keys

- [ ] Key names are in bold: **Enter**, **Tab**, **Ctrl**
- [ ] Key combinations use plus with no spaces: **Ctrl+C**, **Cmd+Shift+P**
- [ ] Platform-appropriate modifier keys are specified: **Ctrl+S** (Windows/Linux) or **Cmd+S** (macOS)
- [ ] "Press" is used, not "hit" or "strike"
- [ ] Key names are capitalized: **Enter**, **Backspace**, **Escape**

### Menus and navigation

- [ ] Menu names and items are in bold: **File > Save As**
- [ ] ">" separates menu levels with spaces: **Edit > Preferences > General**
- [ ] "Click" is used for mouse actions; "select" or "choose" for menu items
- [ ] "Go to" is not used for menu navigation; "click" or "select" is used

### Mouse actions

- [ ] "Click" is used, not "click on," "single-click," or "left-click"
- [ ] "Right-click" is used only when the context menu is needed
- [ ] "Point to" or "rest the pointer on" is used, not "hover over"

### UI elements

- [ ] UI element names are in bold, matching exact on-screen text: **Submit**, **Cancel**
- [ ] UI capitalization matches the product exactly
- [ ] Element type is named when not obvious: "the **Name** field," "the **Advanced** tab"
- [ ] Quotation marks are not used around UI elements (bold is used)
- [ ] Correct interaction verbs are used:
  - **click** — buttons, links, checkboxes
  - **select** — menu items, dropdown options
  - **enter** or **type** — text fields
  - **clear** — checkboxes (to deselect)
  - **turn on/turn off** — toggles (not "enable/disable")

### Web, IP, and email addresses

- [ ] URLs and email addresses are in monospace: `https://example.com`
- [ ] HTTPS is used by default
- [ ] Example domains use RFC 2606; example IPs use RFC 5737; example IPv6 uses RFC 3849
- [ ] Real email addresses are not used in examples; `user@example.com` is used
- [ ] URLs include the protocol: `https://example.com` not `example.com`

## How to use

1. Review only changed content and necessary context
2. For each issue found, cite the relevant IBM Style Guide section
3. Mark issues as **required** (incorrect formatting, wrong syntax conventions) or **[SUGGESTION]** (preferences)

## Example invocations

- "Review this file for technical element formatting"
- "Check code examples and command syntax in this procedure"
- "Do an IBM technical elements review on modules/cli-reference.adoc"

## References

For detailed guidance, consult:
- IBM Style Guide: Technical elements sections
