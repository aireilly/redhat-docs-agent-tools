---
name: cqa-modularization
description: Use when assessing CQA parameters P2-P7 (modularization). Checks assembly structure, module prefixes, required elements, templates, and nesting depth.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# CQA P2-P7: Modularization

## Parameters

| # | Parameter | Level |
|---|-----------|-------|
| P2 | Assemblies contain only intro + includes (no rendered text between includes) | Required |
| P3 | Content is modularized (correct prefixes: assembly_, con_, proc_, ref_, snip_) | Required |
| P4 | Modules use official templates (Concept, Procedure, Reference) | Required |
| P5 | All required modular elements present (content type, ID, title, abstract) | Required |
| P6 | Assemblies use official template | Required |
| P7 | Content not deeply nested (max 3 levels: master -> assembly -> topic) | Important |

## Automation scripts

This skill has an automation script:

| Script | Parameters | What it checks |
|--------|-----------|----------------|
| `check-content-types.py` | P3, P4, P5 | Prefix vs content type match, required elements, invalid block titles, procedure structure |

Python 3.9+ stdlib only, no dependencies. Exit code 0 = pass, 1 = issues found.

```bash
python3 ../cqa-assess/scripts/check-content-types.py "$DOCS_REPO"
```

Checks: filename prefix matches `:_mod-docs-content-type:`, `[role="_abstract"]` present, `[id="..._{context}"]` present, no procedure-only block titles in non-procedure files, no `==` subsections in procedures, ordered list after `.Procedure`.

## Step 1: Identify the docs repo

Ask the user for the path to their Red Hat modular documentation repository. This is the directory that contains `assemblies/`, `topics/`, and `titles/` directories.

Store this as `DOCS_REPO` for all subsequent steps.

## Step 2: P2 — Assembly structure (no rendered text between includes)

Assemblies map to DITA maps. DITA maps do not accept rendered text between module includes.

### Rule

An assembly has three sections in strict order:

1. **Introductory section** (before the first `include::`) — metadata, title, abstract, and one or more paragraphs, admonition blocks, and/or lists. All rendered text must appear here.
2. **Include statements** — `include::` directives for topics, separated only by blank lines and AsciiDoc comments (`// ...`). No rendered text is allowed between includes.
3. **Additional resources** (optional, after all includes) — a `[role="_additional-resources"]` `.Additional resources` section with links.

### Check procedure

For each `assembly_*.adoc` file in `assemblies/`:

1. Read the file
2. Find the line number of the first `include::` directive
3. Find the line number of the last `include::` directive
4. Scan lines between the first and last `include::` — only the following are allowed:
   - `include::` directives
   - Blank lines
   - AsciiDoc comments (`// ...`)
5. Any other content (paragraphs, bullet lists, ordered lists, admonition blocks, bold text) is a **violation**

### Fix pattern

Move all rendered text that appears between includes to the introductory section before the first `include::`. If the text is specific to a particular topic, consider absorbing it into that topic's abstract or content instead.

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All assemblies have no rendered text between includes |
| **3** | 1-2 assemblies with minor text between includes (e.g., a single comment-like sentence) |
| **2** | Multiple assemblies with paragraphs, lists, or admonitions between includes |
| **1** | Assembly structure not assessed or widespread violations |

## Step 3: P3 — Content is modularized

Reference: https://redhat-documentation.github.io/modular-docs/

### Rule

Content is modularized when it follows the Red Hat modular documentation framework:

1. **All content is organized into discrete modules** — each module is an independent, self-contained chunk of information that makes sense on its own.
2. **Each module has a single content type** — Concept (explains what/why), Procedure (step-by-step how-to), or Reference (lookup data). No mixed types in a single file.
3. **Modules are grouped into assemblies** — assemblies correspond to user stories and include related modules via `include::` directives.
4. **Consistent naming prefixes** — every file uses the correct prefix for its content type.
5. **Content type declaration matches actual content** — the `:_mod-docs-content-type:` attribute, the filename prefix, and the actual content must all agree.

### Check 1: File prefix compliance

Ask the user for the directory structure of their docs repo. The typical Red Hat modular docs repo has `assemblies/`, `topics/` (or `modules/`), and `snippets/` directories.

For each `.adoc` file, verify it uses the correct prefix:

| Directory | Required prefix(es) |
|-----------|---------------------|
| Assemblies directory | `assembly_` |
| Topics/modules directory (concepts) | `con_` |
| Topics/modules directory (procedures) | `proc_` |
| Topics/modules directory (references) | `ref_` |
| Snippets directory | `snip_` |

List all files and flag any that don't match the expected prefix pattern.

### Check 2: Content type declaration

For each `.adoc` file in the assemblies and topics directories, read the first line and check for `:_mod-docs-content-type:` attribute. Valid values: `ASSEMBLY`, `CONCEPT`, `PROCEDURE`, `REFERENCE`, `SNIPPET`.

Flag any files that:
- Are missing the `:_mod-docs-content-type:` declaration
- Have an invalid or misspelled value

### Check 3: Prefix vs content type cross-check

For each file, verify the filename prefix matches the declared content type:

| Prefix | Expected `:_mod-docs-content-type:` |
|--------|--------------------------------------|
| `assembly_` | `ASSEMBLY` |
| `con_` | `CONCEPT` |
| `proc_` | `PROCEDURE` |
| `ref_` | `REFERENCE` |
| `snip_` | `SNIPPET` |

Flag any mismatches.

### Check 4: Content type vs actual content

Verify the declared content type matches what the file actually contains:

| Content type | Must contain | Must NOT contain |
|--------------|-------------|------------------|
| PROCEDURE | `.Procedure` section with ordered list steps (`. `) | — |
| CONCEPT | Explanatory/descriptive content | `.Procedure` section |
| REFERENCE | Structured data (tables, lists, source blocks) | `.Procedure` section |
| ASSEMBLY | `include::` directives | `.Procedure` section |

Check ALL procedure files for `.Procedure` with ordered steps. Check ALL concept files to confirm they have no `.Procedure` section. Check ALL reference files to confirm they contain structured data.

### Check 5: Title quality

Reference:
- https://redhat-documentation.github.io/modular-docs/#con-creating-procedure-modules_writing-mod-docs
- https://ccs-internal-documentation.pages.redhat.com/peer-review/#_style

Titles must be brief, complete, and descriptive. Assess three dimensions:

**Check 5a: Grammatical form**

| Module type | Required form | Examples |
|-------------|--------------|----------|
| PROCEDURE | Gerund phrase (verb + -ing) | "Configuring OAuth", "Installing Dev Spaces" |
| CONCEPT | Noun phrase (NOT gerund) | "Architecture overview", "Server components" |
| REFERENCE | Noun phrase | "Supported platforms", "CheCluster fields" |
| ASSEMBLY (task-based) | Gerund phrase | "Configuring server components" |
| ASSEMBLY (non-procedural) | Noun phrase | "Red Hat Process Automation Manager API reference" |

An assembly is task-based if it contains procedure modules. Flag any procedure title not starting with a gerund, concept/reference titles using gerunds, or task-based assembly titles using noun phrases.

**Check 5b: Title length**

Per the CCS peer review guide, titles should be **3-11 words** long and have **50-80 characters**.

| Violation | Threshold | Action |
|-----------|-----------|--------|
| Too short | 1-2 words AND title is vague without context | Flag — add descriptive context |
| Too long | Over 11 words OR over 80 resolved characters | Flag — shorten by removing redundant qualifiers |
| Borderline short | 2 words but unambiguous (e.g., "Creating workspaces") | Do NOT flag — acceptable in context |

When counting characters, resolve AsciiDoc attributes to their display text (e.g., `{prod-short}` = "OpenShift Dev Spaces" = 20 chars).

**Check 5c: Title quality**

| Criterion | Rule |
|-----------|------|
| Descriptive | A reader should understand what the content covers from the title alone |
| Customer-focused | Focus on customer tasks, not product features |
| Sentence case | Only proper nouns, product names, and Kubernetes resource names are capitalized |
| No weak openers | Do not start concept titles with "About" or "Understanding" — use a noun phrase that directly names the concept |
| No vague titles | Single-word titles like "Architecture" or "Gateway" lack context — add the product or component name |
| Correct article before attributes | `{prod-short}` resolves to "OpenShift Dev Spaces" (vowel sound) — use "an {prod-short}", not "a {prod-short}" |
| No redundant product names | Do not hardcode product names before attributes that already contain them (e.g., "OpenShift {prod}" doubles "OpenShift") |
| Concise phrasing | Remove filler words ("the code of applications running in" → "application code from") |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All files use correct prefixes, all content type declarations match, all content matches declared type, all titles follow conventions |
| **3** | 1-3 minor issues (e.g., a borderline title, a concept with a minor procedural element) |
| **2** | Multiple files with wrong prefixes, missing declarations, or content type mismatches |
| **1** | Content is not modularized or no consistent structure |

Record: total file count, count by content type, number of violations per check.

## Step 4: P4 — Modules use official templates

Reference: https://github.com/redhat-documentation/modular-docs/tree/main/modular-docs-manual/files

The official templates define the required structural elements for each module type. Every module must conform to its type's template.

### Check 1: Required elements (all non-snippet files)

Every module (except snippets) must have these 4 elements:

1. `:_mod-docs-content-type:` attribute as the first content line (value: `CONCEPT`, `PROCEDURE`, `REFERENCE`, or `ASSEMBLY`)
2. `[id="name_{context}"]` anchor with `{context}` suffix
3. `= Title` level-1 heading
4. `[role="_abstract"]` annotation followed by a short description paragraph

For each `.adoc` file in the assemblies and topics directories, verify all 4 elements are present. Report any files missing any element.

### Check 2: Procedure template compliance

Per the official procedure template, procedure modules must have:

- `.Procedure` section followed by ordered list steps (`. `)

The following block titles are optional but, when present, must appear in the correct order:

| Block title | Position | Required? |
|-------------|----------|-----------|
| `.Prerequisites` or `.Prerequisite` | Before `.Procedure` | Optional |
| `.Procedure` | Required position | **Required** |
| `.Verification`, `.Results`, or `.Result` | After `.Procedure` | Optional |
| `.Troubleshooting`, `.Troubleshooting steps`, or `.Troubleshooting step` | After `.Verification` | Optional |
| `.Next steps` or `.Next step` | After `.Troubleshooting` | Optional |
| `.Additional resources` | Last section | Optional |

Each block title can appear at most once per module. Check all procedure files for:
- Presence of `.Procedure` with ordered list steps
- Correct ordering of optional sections
- No duplicate block titles

### Check 3: Procedure-only block titles in wrong module types

These block titles are ONLY allowed in procedure modules:

- `.Prerequisites` / `.Prerequisite`
- `.Procedure`
- `.Verification` / `.Results` / `.Result`
- `.Troubleshooting` / `.Troubleshooting steps` / `.Troubleshooting step`
- `.Next steps` / `.Next step`

Search ALL concept, reference, and assembly files for these block titles. Any occurrence is a violation.

### Check 4: Additional resources annotation

For every file that contains `.Additional resources`, verify that `[role="_additional-resources"]` appears on the line immediately before it. A missing role annotation is a violation.

### Check 5: Prerequisites quality

Reference: https://redhat-documentation.github.io/modular-docs/#prerequisites

If a procedure includes prerequisites, verify:

**Check 5a: Label format**

- Must use `.Prerequisites` (plural, dot-prefixed AsciiDoc block title), even with a single prerequisite item
- Flag: `.Prerequisite` (singular), `**Prerequisites**` (bold pseudo-heading), `== Prerequisites` (heading)

**Check 5b: Formatting**

- Prerequisites must be an unordered list using `*` bullet markers
- List items must have parallel grammatical structure
- Admonition blocks within the prerequisites section must be attached to a list item via `+` continuation — not placed as standalone blocks between `.Prerequisites` and `.Procedure`

**Check 5c: Maximum count**

- Do not exceed 10 prerequisite items per procedure

**Check 5d: No steps in prerequisites (declarative language)**

Prerequisites are conditions that must already be true, not steps the user must perform.

| Pattern | Assessment |
|---------|------------|
| "You have access to..." | GOOD — declarative condition |
| "A running instance of..." | GOOD — declarative state |
| "`tool-name` is installed." | GOOD — declarative condition |
| "You must have access to..." | BAD — imperative "must have", change to "You have" |
| "Install the CLI tool." | BAD — imperative action step |
| "Ensure that you have..." | BAD — imperative instruction |
| "To get X, rebuild Y." | BAD — imperative action disguised as prerequisite |
| "Ask a DNS provider to..." | BAD — imperative action step |

A prerequisite may reference another procedure with an xref for HOW to achieve the condition (e.g., "`{prod-cli}`. See: xref:proc_installing-the-dsc-management-tool_{context}[].").

**Check 5e: Placement**

- `.Prerequisites` must appear before `.Procedure`
- No rendered content (admonitions, paragraphs, snippet includes) between the prerequisites list and `.Procedure` unless attached to a list item via `+` continuation

**Common placement violations:**

| Pattern | Problem | Fix |
|---------|---------|-----|
| Standalone `[WARNING]` block between prerequisites and `.Procedure` | Content gap between sections | Attach to last prerequisite item with `+` continuation |
| `include::snippets/...` between prerequisites and `.Procedure` | Snippet renders outside list | Attach to last prerequisite item with `+` continuation |
| `[IMPORTANT]` block with imperative items between prerequisites and `.Procedure` | Combines placement and language violations | Convert to proper prerequisite list items with declarative wording |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All modules conform to their official template — all required elements present, correct block title usage, no procedure-only titles in wrong types, all Additional resources annotated, all prerequisites use declarative language with correct formatting |
| **3** | 1-3 minor issues (e.g., a missing optional annotation, one misplaced block title) |
| **2** | Multiple files missing required elements or widespread block title violations |
| **1** | Templates not followed or not assessed |

Record: total files checked, checks performed per file, number of violations per check category.

## Step 5: P5 — All required modular elements are present

Reference:
- Templates: https://github.com/redhat-documentation/modular-docs/tree/main/modular-docs-manual/files
- Assembly definition: https://redhat-documentation.github.io/modular-docs/#assembly-definition

P5 checks that every non-negotiable modular element is present AND meets quality standards. The structural presence of elements is checked in P4. P5 adds the quality dimension — particularly for the short description (abstract).

### Check 1: Structural elements and abstract formatting

Reference: Ingrid Towey, "Rewrite for Impact: DITA short descriptions" (CCS presentation)

Every non-snippet module must have:

1. `:_mod-docs-content-type:` attribute as first content line
2. `[id="name_{context}"]` anchor with `{context}` suffix
3. `= Title` level-1 heading
4. `[role="_abstract"]` annotation followed by a prose paragraph

If P4 Check 1 passed, the above 4 elements are already verified. Additionally, verify:

**Abstract formatting rules (AsciiDoc-specific):**

| Rule | Check |
|------|-------|
| **Blank line between title and abstract** | There must be at least one blank line between the `= Title` line and `[role="_abstract"]`. Other content (anchors, passthrough comments) may appear between them, but a blank line must exist. |
| **No blank line between annotation and paragraph** | `[role="_abstract"]` must be followed **immediately** by the abstract paragraph on the next line — no blank lines between them. A blank line after the annotation disconnects the paragraph from the abstract role, making the abstract empty in DITA. |
| **Single paragraph** | The abstract must be exactly one contiguous paragraph. No blank lines within it, no code blocks, no lists, no admonition blocks. A blank line must terminate the abstract before any subsequent body content. |
| **Character count 50-300** | The abstract paragraph must be between 50 and 300 characters. Count raw AsciiDoc text (attributes like `{prod-short}` count as their literal text, e.g., 12 characters). "300 characters is between 42 and 75 words" (Ingrid Towey). |

**Common structural violations:**

| Pattern | Problem | Fix |
|---------|---------|-----|
| Blank line after `[role="_abstract"]` | Abstract is empty in DITA conversion | Remove the blank line |
| Abstract flows into code block | Code block becomes part of abstract (inflated character count) | Insert blank line after abstract paragraph to separate |
| Abstract flows into bullet list | List becomes part of abstract | Insert blank line after abstract paragraph |
| Multiple paragraphs before first block title | Only the first paragraph is the shortdesc; the rest is `<context>` in DITA | Ensure only one paragraph between `[role="_abstract"]` and the first blank line |

### Check 2: Short description quality

Reference: https://docs.oasis-open.org/dita/dita/v1.3/errata02/os/complete/part3-all-inclusive/langRef/base/shortdesc.html

Per the DITA 1.3 specification, the short description (the paragraph after `[role="_abstract"]`) "represents the purpose or theme of the topic" and is "intended to be used as a link preview and for search results."

**Structural requirements:**

| Criterion | Rule |
|-----------|------|
| Word count | Max 50 words — "a single, concise paragraph containing one or two sentences of no more than 50 words" (DITA 1.3 spec) |
| Completeness | Must be complete sentences, not fragments ending in colons |
| Self-contained | Must not flow into a list or block below it; must not use "the following" to reference content below |
| Placement | Must be prose immediately after `[role="_abstract"]` — no admonition blocks or passthrough comments between the annotation and the paragraph |
| Link preview | Must work as a standalone snippet in search results — no context-dependent pronouns, no xrefs, no references that only make sense within the document |

**Content requirements by module type:**

| Module type | Short description must... |
|-------------|--------------------------|
| PROCEDURE | Explain WHAT the user can accomplish AND WHY (benefit/purpose). Not just "Do X." |
| CONCEPT | Answer "What is this?" AND "Why do I care about this?" |
| REFERENCE | Describe what the reference item does, what it is, or what it is used for |
| ASSEMBLY | Explain what the user will accomplish by working through the modules (the user story reworded) |

**Reader motivation**: The short description must describe WHY the user should read the content — what they will gain, accomplish, or understand. A reader scanning search results should immediately understand whether this content addresses their need.

**SEO and AI discoverability**: The short description should include keywords that users are likely to search on. For technical documentation, this means including relevant product names, technology terms, and action verbs that match user search intent.

**Violations to flag:**

| Category | Pattern | Example |
|----------|---------|---------|
| Over word limit | Exceeds 50 words | Count words in the abstract paragraph; attributes like `{prod-short}` count as 1 word |
| Self-referential | "This topic describes...", "This section covers...", "Learn how to...", "The following steps describe..." | "The following steps describe how to create the required objects." |
| Forward-referencing | "the following methods:", "the following field descriptions", "as shown below" | "Implement the following methods:" (dangling reference in search snippet) |
| Title repetition | Restates the title with "You can" or imperative rewording and adds nothing new | Title: "Listing all workspaces" → SD: "You can list your workspaces by using the command line." |
| Missing WHY | States WHAT to do but not WHY it matters or what the user gains | "Configure the Dashboard to display custom samples." (no benefit) |
| Sentence fragment | Ends with a colon and flows into a list | "Implement the following methods:" |
| Poor link preview | Depends on title context, starts with pronouns, or is too vague to stand alone | "It is possible to fine-tune the log levels." (what log levels? which product?) |
| Fallback framing | Positions the content as secondary to another topic | "If you have trouble doing X, you can do Y instead." |
| Missing keywords | Contains no searchable technical terms relevant to the topic | Abstract with only generic words, no product/technology terms |

### Check 3: Abstract annotation consistency

Verify:
- The `[role="_abstract"]` annotation is followed immediately by a prose paragraph (no admonition blocks, no passthrough comments, no blank lines with markup between them)
- The prose paragraph after the annotation is the actual short description (not a code block, not a list)

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All modules have all required elements; all short descriptions meet DITA quality standards (correct length, explain WHAT + WHY, no self-referential language, no title repetition, complete sentences) |
| **3** | All structural elements present; fewer than 15 short descriptions have quality issues (missing WHY, title repetition, or fragments) |
| **2** | Structural elements missing in multiple files or widespread short description quality failures |
| **1** | Required elements not present or not assessed |

Record: total files, violations per category (length, self-referential, title repetition, missing WHY, fragments), severity counts (high/medium/low).

## Step 6: P6 — Assemblies use official template / Assemblies are one user story

Reference:
- Template: https://github.com/redhat-documentation/modular-docs/tree/main/modular-docs-manual/files
- Definition: https://redhat-documentation.github.io/modular-docs/#assembly-definition

An assembly is "the docs realization of a user story" — a collection of modules that describes how to accomplish a single user goal. Every assembly must conform to the official template AND represent a coherent user story.

### Check 1: Template structural elements

For each assembly file, verify these required elements:

1. `:_mod-docs-content-type: ASSEMBLY` as first content line
2. `[id="assembly_name_{context}"]` anchor with `{context}` suffix
3. `= Title` level-1 heading
4. `[role="_abstract"]` followed by an introduction paragraph
5. At least one `include::` directive
6. `[leveloffset=+N]` on every `include::` directive

Flag any assembly missing any element. Flag any `include::` missing `[leveloffset=+N]`.

### Check 2: Assembly title convention

Per the modular docs guide:
- **Task-based assemblies** (containing procedure modules): title must use a gerund phrase ("Configuring...", "Installing...", "Managing...")
- **Non-procedural assemblies** (reference-heavy, conceptual): title should use a noun phrase ("Supported platforms", "Architecture overview")

For each assembly, check whether the title form matches its content. A task-based assembly with a noun-phrase title is a violation.

### Check 3: No assembly-inside-assembly

For each assembly, verify that every `include::` path points to a file in the topics directory, NOT another file in the assemblies directory. Assembly nesting is a violation.

### Check 4: User story coherence

Each assembly should document a single, coherent user story. For each assembly:

1. Read the abstract/introduction and the list of included modules
2. Assess whether all modules serve one user goal
3. Flag assemblies that are unfocused topic clusters or catch-all grab-bags mixing unrelated tasks

Signs of poor user story coherence:
- Modules span multiple distinct sub-domains with different user goals
- Modules target different personas (e.g., developer tasks mixed with operator tasks)
- The assembly title is very broad to accommodate unrelated modules
- A user working through one part of the assembly has no need for another part

### Check 5: Introduction quality

The introduction (abstract paragraph) should be the user story reworded. For each assembly, verify:

1. The abstract paragraph exists (not just the `[role="_abstract"]` annotation with no text)
2. It is action-oriented — tells the user what they will accomplish
3. It is NOT self-referential ("This section describes...", "This chapter contains...")
4. It is NOT purely explanatory without framing the user's goal

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All assemblies follow the template, use correct title conventions, avoid nesting, represent coherent user stories, and have action-oriented introductions |
| **3** | 1-3 minor issues (e.g., a borderline user story, one weak introduction, a known ID inconsistency) |
| **2** | Multiple assemblies missing template elements, mixing user stories, or with non-functional introductions |
| **1** | Assemblies do not follow the template or user story principle |

Record: total assemblies, per-assembly pass/fail, specific violations per check.

## Step 7: P7 — Nesting depth

Reference: https://redhat-documentation.github.io/modular-docs/#modular-docs-terms-definitions

Content must not be deeply nested in the TOC. The recommended maximum is **3 levels of content nesting**.

### Level counting rule

For migration assessments, start counting levels where **user content starts**, not including categories and the repetitive book titles that Pantheon generates. The Pantheon publishing system adds Category → Book title layers above the content — these do not count toward the 3-level limit.

| Level | What it contains | AsciiDoc mechanism |
|-------|------------------|--------------------|
| **Level 1** | Assemblies and standalone topics included from `master.adoc` | `include::assemblies/...adoc[leveloffset=+1]` or `include::topics/...adoc[leveloffset=+1]` |
| **Level 2** | Topics included from assemblies | `include::topics/...adoc[leveloffset=+1]` inside an assembly |
| **Level 3** | Subsections within topics (`==` headings) or sub-topics at `leveloffset=+2` | `== Heading` inside a topic, or `include::topics/...adoc[leveloffset=+2]` inside an assembly |

**Level 4 would be a violation**: `===` headings in topics, topics including other topics, or assemblies including assemblies.

### Check 1: Master files include only assemblies and standalone topics

Read each `master.adoc` file. Verify every `include::` directive points to:
- A file in `assemblies/` (an assembly)
- A file in `topics/` (a standalone topic)
- A `common/` file (metadata — does not count as content nesting)

Flag any include pointing to an unexpected location or nesting pattern.

### Check 2: No assembly-inside-assembly nesting

For every assembly file in `assemblies/`, read all `include::` directives. Verify every include points to a file in `topics/` or `snippets/` — **never** to a file in `assemblies/`.

Assembly nesting creates Level 4+ content, which violates the 3-level limit.

### Check 3: No topic-inside-topic nesting

For every topic file in `topics/`, search for `include::` directives. Verify all includes point to files in `snippets/` — **never** to other files in `topics/`.

Topic nesting creates Level 4+ content when the parent topic is already at Level 2.

### Check 4: No Level 4+ headings in topics

Search all topic files for `===` headings (AsciiDoc level-3 headings). When a topic is included at Level 2 via an assembly, a `===` heading becomes Level 4 in the TOC — a violation.

Notes:
- `==` headings in concept topics are acceptable (Level 3 in the TOC)
- `====` lines used as admonition/example block delimiters are NOT headings — do not flag them
- Some assemblies use `leveloffset=+2` for sub-topics; verify that these sub-topics contain no `==` headings (which would push to Level 4)

### Fix patterns

| Violation | Fix |
|-----------|-----|
| Assembly includes assembly | Flatten: promote inner assembly's topics into the outer assembly, or make both top-level assemblies in master |
| Topic includes topic | Extract the included content into a snippet, or merge the two topics |
| `===` heading in topic | Restructure: use bold text, definition lists, or split into separate topics |
| `==` heading in `leveloffset=+2` sub-topic | Remove the subsection or restructure the assembly to use `leveloffset=+1` |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | Strict 3-level hierarchy — 0 violations across all 4 checks |
| **3** | 1 minor nesting issue (e.g., a single `===` heading in one topic) |
| **2** | Assembly-inside-assembly nesting found, or multiple `===` headings |
| **1** | Deeply nested structure with no clear hierarchy or not assessed |

Record: total files checked per check, number of violations, specific file paths with violations.

## Quality: Information is conveyed using the correct content type

Each file must use the modular documentation content type (CONCEPT, PROCEDURE, REFERENCE) that is most appropriate for the information it conveys. This goes beyond structural checks (P3/P4) — it verifies that the content type *selection* is correct.

### Check 1: Procedure files contain actionable steps

Every PROCEDURE file must have a `.Procedure` section with ordered steps (`. `) that are actionable instructions. Flag:

- Procedure files where `.Procedure` contains only an xref redirect with no actual steps
- Procedure files that are mostly explanatory with minimal/trivial steps

### Check 2: Concept files contain explanatory content

CONCEPT files must explain what/why — not how to do something. Flag:

- Concept files with ordered lists (`. `) that function as undeclared procedures — rewrite as prose summary or unordered list
- Concept files with `.Procedure` sections (also caught by P4 Check 3)

Do NOT flag:
- Concept files with unordered lists (`*`) — these are fine
- Concept files with `==` subsections — these are allowed
- Ordered lists that describe system behavior or enumerate options (not user steps)

### Check 3: Reference files contain structured data

REFERENCE files must contain tables, definition lists, or structured lookup data. Flag files that are primarily narrative explanation (→ should be concept) or step-by-step instructions (→ should be procedure).

### Check 4: No mixed content types

Each file must convey one type of information. Flag files that mix significant procedural steps with conceptual explanation in a way that should be split into separate modules.

### Check 5: Thin wrapper modules

Flag concept files that contain only an abstract and xrefs (typically ≤15 lines). These should be absorbed into the parent assembly's introductory text. Also flag orphaned concept files that are not included from any assembly.

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All content uses the correct content type, no procedural content in concepts, no trivial procedures, no orphaned files |
| **3** | 1-3 minor issues (e.g., one thin wrapper, one concept with ordered-list steps rewritten as prose) |
| **2** | Multiple content type mismatches or widespread thin wrappers |
| **1** | Content types not checked or pervasive mismatches |

Record: total files checked per type, violations per check category, files fixed.

## Quality: American English grammar

Content must be grammatically correct and follow American English conventions.

### Check 1: American English spelling

Use American spellings. Flag and fix British variants:

| British | American |
|---------|----------|
| behaviour | behavior |
| colour | color |
| customise | customize |
| analyse | analyze |
| organisation | organization |
| licence (noun) | license |
| centre | center |
| defence | defense |
| catalogue | catalog |
| programme | program |

### Check 2: Article usage before AsciiDoc attributes

When an AsciiDoc attribute resolves to a word starting with a vowel sound, the preceding article must be "an", not "a". Check all prose (not code blocks or YAML) for these patterns:

| Attribute | Resolves to | Starts with | Correct article |
|-----------|-------------|-------------|-----------------|
| `{prod-short}` | OpenShift Dev Spaces | vowel "O" | **an** {prod-short} |
| `{orch-name}` | OpenShift | vowel "O" | **an** {orch-name} |
| `{ocp}` | OpenShift Container Platform | vowel "O" | **an** {ocp} |
| `{prod}` | Red Hat OpenShift Dev Spaces | consonant "R" | **a** {prod} |
| `{devworkspace}` | Dev Workspace | consonant "D" | **a** {devworkspace} |

**Important**: When an adjective intervenes between the article and the attribute, the article agrees with the adjective, not the attribute. For example, "a new {orch-name} Secret" is correct because "a" modifies "new" (consonant).

Search patterns:
- `" a {prod-short}"` — all matches are violations
- `" a {orch-name}"` — violations unless an adjective follows (e.g., "a new {orch-name}")
- `" a {ocp}"` — all matches are violations

### Check 3: Subject-verb agreement

Verify that singular subjects take singular verbs and plural subjects take plural verbs. Common issues in technical docs:

| Pattern | Problem | Fix |
|---------|---------|-----|
| "content are empty" | "content" (uncountable) takes singular verb | "contents are empty" or "content is empty" |
| "a ... containers" | article "a" with plural noun | Remove article or use singular noun |
| "data are" | Red Hat style: "data" is singular | "data is" |

### Check 4: Compound modifier hyphenation

Hyphenate compound modifiers that precede a noun:

| Pattern | Problem | Fix |
|---------|---------|-----|
| "{prod-short} managed containers" | unhyphenated compound modifier | "{prod-short}-managed containers" |
| "command line tool" | unhyphenated compound modifier | "command-line tool" |

Do NOT hyphenate when the modifier follows the noun: "the containers are {prod-short} managed" (no hyphen needed).

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All content uses American English spelling, correct article usage before attributes, correct subject-verb agreement, and proper hyphenation |
| **3** | 1-3 minor issues (e.g., a few article mismatches, one British spelling) |
| **2** | Multiple British spellings, widespread article errors, or subject-verb disagreements |
| **1** | Content not checked or pervasive grammar issues |

Record: total files checked, violations per check category, files fixed.

## Step 8: Verify

After fixing any violations, re-run all checks to confirm compliance. Run Vale to ensure no new warnings were introduced:

```bash
cd "$DOCS_REPO"
vale assemblies/ topics/ titles/administration_guide/master.adoc titles/user_guide/master.adoc
```
