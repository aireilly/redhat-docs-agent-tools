---
name: cqa-tables-images
description: Use when assessing CQA parameters Q19, Q21-Q22 (tables and images). Checks for excessive screenshots, table captions, and image alt text.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# CQA Q19, Q21-Q22: Tables and Images

## Parameters

| # | Parameter | Level |
|---|-----------|-------|
| Q19 | No excessive use of screen images | Important |
| Q21 | Tables have captions and are clearly labeled | Important |
| Q22 | Images have captions and meaningful alt text | Important |

## Directory note

Some repos use `modules/` instead of `topics/` for content files. All `topics/` references in this skill apply equally to `modules/`. The automation scripts accept `--scan-dirs` to override the default scan directories.

## Checks

### Q19: Screenshot usage (IBM Style screen capture guidelines)

Screen captures are useful when they:
- Illustrate a user interface that is complex or difficult to explain in text
- Help the user find a small element in a complex user interface
- Show the results of a series of steps or user actions
- Orient readers who are reading without the user interface in front of them

Screen captures are less successful when:
- Too many are used (documenting the interface instead of tasks)
- Used inconsistently (captures for some complex processes but not others)
- Simple user interfaces are displayed that provide no additional help
- Poor-quality captures are used

#### Guidelines

- Use captures of windows and UI elements sparingly
- Include cursor, mouse pointer, or menus only when their presence is significant
- Capture just the part of the screen or window that users must focus on
- Show UI elements exactly as displayed for quick recognition
- Keep captures in proportion to each other
- Annotate screen captures where it helps the reader find a UI element
- No excessive step-by-step screenshots for simple UI actions (text instructions preferred)

#### What to check

- Count images per file — flag files with more than 6-8 images unless justified (e.g., multi-step IDE workflow)
- Verify all `image::` references have meaningful alt text (not empty `[]` or generic "screenshot")
- Check that simple UI actions (clicking a button, selecting a menu item) use text instructions, not screenshots
- Verify consistency: similar workflows should have similar image coverage
- Check for orphaned images (files in `images/` not referenced by any topic)
- Check for duplicate images (same image stored in multiple locations)

### Q21: Table captions and labeling

Every table must have:
1. A `.Title` caption (line starting with `.` immediately before `[cols=...]` or `|===`)
2. An `options="header"` attribute (or `[%header,...]`) to mark the header row
3. Surrounding text that introduces or explains the table

```asciidoc
.Supported platforms
[cols="1,1",options="header"]
|===
| Platform | Version

| OpenShift
| 4.15+
|===
```

#### What to check

1. Find all `|===` table delimiters in `topics/` and `assemblies/`
2. For each opening `|===`, check that a `.Title` caption exists on a preceding line (before `[cols=...]` or directly before `|===`)
3. Check that `options="header"` or `[%header,...]` is present in the table attribute
4. Verify the first row of content after `|===` is a header row (column labels, not data)
5. Check for surrounding introductory text — a sentence or paragraph before the table that explains its purpose

#### Common issues

- Tables under `==` subsection headings may lack `.Title` captions because the heading seems to serve as the label. Both are needed: `==` is a section heading, `.Title` is the table caption (maps to `<title>` in DITA).
- Tables without `[cols=...]` attribute may omit `options="header"` — add `[cols="1,1",options="header"]` before `|===`.
- Tables in procedure steps (after `. step text` with `+` continuation) still need captions.

### Q22: Image captions, alt text, and contextual explanation

This parameter covers four aspects of image quality (Usability checklist):

1. **Content** — Images and figures are clearly explained immediately before or after they appear
2. **Accessibility** — Images have meaningful alt text (not empty `[]` or generic "screenshot", "image")
3. **Links** — Images linked from external sources load correctly
4. **Visual continuity** — Images appear near the text that refers to them; captions and labels are consistent in style and formatting

#### Alt text requirements

Every `image::` must have meaningful alt text in brackets:
```asciidoc
image::architecture/overview.png[Dev Spaces architecture overview]
```

Empty brackets `[]` or generic alt text ("screenshot", "image") are violations. Alt text should describe the content or purpose of the image, not just its format.

#### Block title captions

Images in concept files should have `.Title` block title captions on the line before the `image::` directive:
```asciidoc
.High-level architecture with the DevWorkspace operator
image::architecture/devspaces-interacting-with-devworkspace.png[High-level architecture diagram]
```

The block title maps to `<title>` in DITA output and serves as the figure caption in rendered documentation.

**When block titles are required:**
- All images in **concept** files — architecture diagrams, component interaction diagrams, conceptual illustrations
- Images in **verification** sections that show dashboard panels or output displays in sequence (each needs identification)
- Images in `.Additional resources` or standalone image blocks

**When block titles are acceptable to omit:**
- Images in **procedure steps** attached via `+` continuation where the step text provides the caption context (e.g., ". Create a workspace on the Dashboard and choose `IntelliJ IDEA Ultimate`:" followed by screenshot)
- The step text itself serves as the image explanation in this case

#### Contextual explanation

Every image must be clearly explained by surrounding text:
- **Concept images**: A paragraph before or after the image explains what it depicts and why it matters
- **Procedure images**: The step instruction text explains the UI state or action being captured
- **Verification images**: The verification step explains what the reader should see in the screenshot

#### What to check

1. Grep all `image::` directives in `topics/` and `assemblies/`
2. Verify all images have non-empty, meaningful alt text (not `[]`, `[screenshot]`, `[image]`)
3. For concept file images, verify a `.Title` block caption exists on the preceding line
4. For procedure step images, verify the step text provides explanatory context
5. Check that images appear near the text referencing them (visual continuity)
6. Verify caption style consistency — `.Title` captions should use sentence case, no trailing period

#### Common issues

- Concept images without `.Title` captions — inconsistent with other concept images in the repo
- Alt text that merely repeats the filename instead of describing the content
- Images placed far from the text that references them (breaks visual continuity)
- Missing explanatory text around standalone images outside procedure steps

## Scoring

See [scoring-guide.md](../../reference/scoring-guide.md).
