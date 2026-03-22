---
name: cqa-titles-descriptions
description: Use when assessing CQA parameters P8-P11 (titles and short descriptions). Checks abstract quality, character limits, and title conventions.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# CQA P8-P11: Titles and Short Descriptions

## Parameters

| # | Parameter | Level |
|---|-----------|-------|
| P8 | Short descriptions are clear and describe why the user should read the content | Required |
| P9 | Short descriptions: 50-300 chars, `[role="_abstract"]` present | Required |
| P10 | Titles support short, long, and descriptive forms (DITA) | Important |
| P11 | Titles are brief, complete, and descriptive | Required |

## Directory note

Some repos use `modules/` instead of `topics/` for content files. All `topics/` references in this skill apply equally to `modules/`.

## Step 1: Identify the docs repo

Ask the user for the path to their Red Hat modular documentation repository. Store as `DOCS_REPO`.

## Step 2: P8 — Short description quality

### Rule

The short description (the paragraph after `[role="_abstract"]`) maps to the DITA `<shortdesc>` element. Per the DITA 1.3 spec, it "represents the purpose or theme of the topic" and is "intended to be used as a link preview and for search results."

Reference: https://docs.oasis-open.org/dita/dita/v1.3/errata02/os/complete/part3-all-inclusive/langRef/base/shortdesc.html

### Content requirements by module type

| Module type | Short description must... |
|-------------|--------------------------|
| PROCEDURE | Explain WHAT the user can accomplish AND WHY (benefit/purpose). Not just "Do X." |
| CONCEPT | Answer "What is this?" AND "Why do I care about this?" |
| REFERENCE | Describe what the reference item does, what it is, or what it is used for |
| ASSEMBLY | Explain what the user will accomplish by working through the modules (the user story reworded) |

### Quality criteria

- **Action-oriented**: Tell the user what they can DO or UNDERSTAND
- **Customer-centric**: Written from the user's perspective, not the product's
- **WHAT + WHY**: State both what the topic covers and why it matters
- **Technically accurate**: Use correct product attributes (`{prod-short}`, `{orch-name}`)
- **Self-contained**: Must work as a standalone snippet in search results — no context-dependent pronouns, no xrefs
- **SEO/AI discoverable**: Include keywords that users are likely to search on

### Anti-patterns to flag

| Category | Pattern | Example | Fix |
|----------|---------|---------|-----|
| Self-referential | "This topic describes...", "This section covers...", "Learn how to..." | "This section describes how to configure OAuth." | "Configure OAuth to allow users to interact with Git repositories without re-entering credentials." |
| Forward-referencing | "The following steps describe...", "the following methods:" | "The following steps describe how to create the required objects." | "Create the required objects for {prod-short} workspace configuration." |
| Title repetition | Restates the title with "You can" | Title: "Listing workspaces" → SD: "You can list your workspaces." | Add the WHY: "List workspaces to monitor their status, resource usage, and running state." |
| Missing WHY | States WHAT but not WHY | "Configure the Dashboard to display custom samples." | "Configure the Dashboard to display custom samples that demonstrate recommended devfile patterns for your team." |
| Fallback framing | Positions content as secondary | "If you have trouble installing on the CLI, use the web console." | "Install {prod-short} through the {orch-name} web console for a guided, visual installation workflow." |
| Sentence fragment | Ends with colon, flows into list | "Implement the following methods:" | "Implement the telemetry backend methods to collect and process workspace activity data." |
| Links in abstract | Contains `link:`, `xref:`, or `<<...>>` | "See xref:topic[] for details." | Remove links. Links belong in `.Additional resources`. |

### Good examples

- **Procedure**: "Configure OAuth to allow {prod-short} users to interact with remote Git repositories without re-entering credentials." (WHAT + WHY)
- **Concept**: "The {prod-short} server components manage multi-tenancy and workspace lifecycle. Understanding these components helps you troubleshoot issues and plan cluster capacity." (WHAT + WHY)
- **Reference**: "Customize the CheCluster Custom Resource by configuring its specification fields to control {prod-short} server, dashboard, gateway, and workspace components." (standalone, keyword-rich)
- **Assembly**: "Configure OAuth to allow {prod-short} users to interact with remote Git repositories without re-entering credentials." (user story reworded)

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All short descriptions meet DITA quality standards: explain WHAT + WHY, no self-referential language, no title repetition, no fragments, self-contained for search results |
| **3** | Most abstracts are good quality. Fewer than 15 have quality issues (missing WHY, title repetition, or minor patterns). |
| **2** | Widespread quality failures: self-referential abstracts, title repetitions, or fragments in many files |
| **1** | Short description quality not assessed or pervasive anti-patterns |

## Step 3: P9 — Short description structural requirements

### Rule

Every non-snippet module must have a `[role="_abstract"]` annotation followed by a prose paragraph within specific character limits.

Reference: Ingrid Towey, "Rewrite for Impact: DITA short descriptions" (CCS presentation)

### Structural checks

| Rule | Check |
|------|-------|
| **`[role="_abstract"]` present** | Every non-snippet file must have this annotation |
| **Blank line between title and abstract** | At least one blank line must separate `= Title` from `[role="_abstract"]` |
| **No blank line between annotation and paragraph** | `[role="_abstract"]` must be followed immediately by the abstract paragraph on the next line. A blank line disconnects them, making the abstract empty in DITA. |
| **Single paragraph** | The abstract must be exactly one contiguous paragraph. No blank lines within it, no code blocks, no lists, no admonition blocks. A blank line must terminate the abstract before any subsequent body content. |
| **Character count 50-300** | Count raw AsciiDoc text. Attributes like `{prod-short}` count as their literal text (12 characters). "300 characters is between 42 and 75 words" (Ingrid Towey). |
| **Max 50 words** | "A single, concise paragraph containing one or two sentences of no more than 50 words" (DITA 1.3 spec). |

### Common structural violations

| Pattern | Problem | Fix |
|---------|---------|-----|
| Blank line after `[role="_abstract"]` | Abstract is empty in DITA conversion | Remove the blank line |
| Abstract flows into code block | Code block becomes part of abstract (inflated character count) | Insert blank line after abstract paragraph |
| Abstract flows into bullet list | List becomes part of abstract | Insert blank line after abstract paragraph |
| Multiple paragraphs before first block title | Only the first paragraph is the shortdesc | Ensure only one paragraph between `[role="_abstract"]` and the next blank line |
| Abstract exceeds 300 characters | Too long for link preview | Shorten to 1-2 sentences |
| Abstract under 50 characters | Too short to be informative | Expand with WHAT + WHY |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All modules have `[role="_abstract"]`, correct formatting (no blank line gap, single paragraph), all within 50-300 characters |
| **3** | All annotations present. 1-5 files with character count violations (minor over/under). |
| **2** | Multiple missing annotations or widespread structural violations |
| **1** | Not assessed or pervasive missing abstracts |

## Step 4: P10 — Title forms (DITA compatibility)

### Rule

DITA supports three title forms per topic: short title (`<titlealt>` with `title-role="search"`), navigation title (`<navtitle>`), and the primary title. In AsciiDoc, the `= Title` heading serves all three purposes, so it must work in all contexts:

1. **Search results** — title must be self-descriptive without guide context
2. **TOC navigation** — title must be scannable at a glance
3. **Full page heading** — title must accurately describe the content

### Check procedure

For each file in `topics/` and `assemblies/`, verify the title works in all three contexts:

| Context | What to check |
|---------|---------------|
| Search | Would a user understand this title in isolation? (e.g., "Architecture" fails — "Dev Spaces architecture overview" works) |
| Navigation | Is the title scannable in a TOC list? (too long titles hurt navigation) |
| Page heading | Does the title accurately describe the content below? |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All titles work as search results, TOC entries, and page headings |
| **3** | 1-3 titles that are ambiguous in search context (e.g., overly generic single-word titles) |
| **2** | Multiple titles that fail in one or more contexts |
| **1** | Not assessed or titles frequently misleading |

## Step 5: P11 — Title quality

### Rule

Titles must be brief, complete, and descriptive.

Reference:
- https://redhat-documentation.github.io/modular-docs/#con-creating-procedure-modules_writing-mod-docs
- https://ccs-internal-documentation.pages.redhat.com/peer-review/#_style

### Check 1: Grammatical form

| Module type | Required form | Examples |
|-------------|--------------|----------|
| PROCEDURE | Gerund phrase (verb + -ing) | "Configuring OAuth", "Installing Dev Spaces" |
| CONCEPT | Noun phrase (NOT gerund) | "Architecture overview", "Server components" |
| REFERENCE | Noun phrase | "Supported platforms", "CheCluster fields" |
| ASSEMBLY (task-based) | Gerund phrase | "Configuring server components" |
| ASSEMBLY (non-procedural) | Noun phrase | "Architecture overview" |

An assembly is task-based if it contains procedure modules.

### Check 2: Title length

| Metric | Target | Flag |
|--------|--------|------|
| Word count | 3-11 words (resolved) | Flag titles under 3 words (if vague) or over 11 words |
| Character count | 50-80 characters (resolved) | Titles under 50 chars acceptable if clear. Flag titles over 80 chars |

**Attribute resolution for counting:**
- `{prod-short}` = 3 words / 20 characters
- `{prod}` = 5 words / 35 characters
- `{ocp}` = 3 words / 30 characters
- `{orch-name}` = 1 word / 9 characters
- `{devworkspace}` = 2 words / 13 characters
- Backtick-quoted strings = 1 word each

**When fixing long titles:** Use shorter attribute forms (`{prod-short}` instead of `{prod}`, `{orch-name}` instead of `{ocp}`) to reduce word/character count while preserving meaning.

### Check 3: Title quality rules

| Criterion | Rule |
|-----------|------|
| Sentence case | Only capitalize proper nouns, product names, and Kubernetes resource names |
| No weak openers | Do not start concept titles with "About" or "Understanding" — use a noun phrase |
| No vague titles | Single-word titles like "Architecture" lack context — add component/product name |
| Correct article before attributes | `{prod-short}` (vowel "O") → "an {prod-short}". `{prod}` (consonant "R") → "a {prod}" |
| No redundant product names | Do not hardcode names before attributes: "OpenShift {prod}" doubles "OpenShift" |
| No possessives of brand names | "the OpenShift configuration" not "OpenShift's configuration" |
| Concise phrasing | Remove filler words: "the code of applications running in" → "application code from" |

### Acceptable exceptions

- Single Kubernetes resource names as subsection headings (`== DevWorkspaceTemplate`) when parent provides context
- Two-word titles like "Creating workspaces" or "Server components" that are clear and descriptive

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All titles use correct grammatical form, are within length range, follow quality rules, and use sentence case |
| **3** | 1-3 minor issues (borderline title length, one incorrect grammatical form) |
| **2** | Multiple titles with wrong form, length violations, or quality issues |
| **1** | Titles not checked or widespread violations |

## Step 6: Verify

After fixing any violations, run Vale to ensure no new warnings were introduced:

```bash
cd "$DOCS_REPO"
vale assemblies/ topics/ titles/administration_guide/master.adoc titles/user_guide/master.adoc
```
