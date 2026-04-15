---
name: rhivos-map-upstream
description: >-
  Parses a Google Doc skeleton ToC and maps downstream RHIVOS topics to upstream
  CentOS Automotive SIG (sig-docs) Markdown files. Use this skill when starting
  work on a RHIVOS Doc Title to identify which upstream content to adapt and which
  topics require net-new writing.
argument-hint: "<google-doc-url>" --title "Doc Title" [--sig-docs-path <path>]
allowed-tools: Read, Write, Bash, Glob, Grep, Skill, AskUserQuestion
---

# Map Upstream Content

Maps downstream RHIVOS topics from a Google Doc skeleton ToC to upstream CentOS Automotive SIG source files.

## When to use

- Starting work on a new RHIVOS Doc Title
- Re-mapping after the skeleton ToC has been updated
- Checking which upstream files cover a specific downstream topic

## Inputs

Parse from `$ARGUMENTS`:

- **Google Doc URL** (required, positional) — the skeleton ToC document
- **`--title "Doc Title"`** (required) — one of the 8 Doc Titles to process
- **`--sig-docs-path <path>`** (optional) — path to local sig-docs clone. Default: `~/Documents/git-repos/sig-docs`

If the Doc Title or URL is missing, stop and ask the user.

## Process

### 1. Fetch the Google Doc

Invoke the Google Doc conversion skill:

```
Skill: docs-convert-gdoc-md, args: "<google-doc-url>"
```

Read the resulting Markdown file.

### 2. Parse the ToC hierarchy

Extract the hierarchy for the specified Doc Title:

1. Find the heading matching the `--title` argument (case-insensitive, partial match OK)
2. Extract all bullet-point topics and sub-topics under that heading, stopping at the next Doc Title heading
3. Preserve the nesting structure (top-level topics and their sub-topics)

### 3. Build upstream file index

Read the upstream `mkdocs.yml` to build a map of all upstream files:

```bash
cat "${sig_docs_path}/mkdocs.yml"
```

Also scan the upstream `docs/` directory for all `.md` files:

```bash
find "${sig_docs_path}/docs" -name "*.md" -type f
```

For each upstream file, extract:
- File path (relative to sig-docs root)
- Title (from YAML frontmatter `title:` or first `#` heading)
- First 500 characters of content (for keyword matching)

### 4. Match downstream topics to upstream files

For each downstream topic from the ToC, search upstream for matching content using these signals (in priority order):

1. **Title similarity** — compare the downstream topic text against upstream headings and filenames. Use case-insensitive substring matching and common synonym handling (e.g., "install" matches "installing", "setup" matches "setting up")
2. **Keyword overlap** — extract key nouns and verbs from the topic description, match against upstream file content
3. **File prefix matching** — match topic intent to upstream file prefixes:
   - Topic mentions "understand", "overview", "about" -> look for `con_*.md` files
   - Topic mentions "install", "configure", "create", "build" -> look for `proc_*.md` files
   - Topic mentions "supported", "options", "reference", "list" -> look for `ref_*.md` files
4. **Directory affinity** — topics about a technology area match files in the corresponding upstream directory (e.g., "image building" topics match files under `docs/building/`)

Assign a relevance level to each match:
- **exact**: upstream file directly covers the downstream topic
- **high**: strong overlap, will need adaptation
- **partial**: some relevant content, may need supplementing
- **low**: tangential, may be useful as reference

### 5. Infer content type

Determine the modular docs content type from the topic phrasing:

| Topic pattern | Content type |
|---------------|-------------|
| "Understand...", "Overview of...", "About...", "...concepts", "...architecture" | CONCEPT |
| "Install...", "Configure...", "Create...", "Build...", "Deploy...", "Set up..." | PROCEDURE |
| "Supported...", "...options", "...reference", "...parameters", "...list of..." | REFERENCE |

If ambiguous, default to CONCEPT and flag for writer review.

### 6. Generate mapping YAML

Write the mapping to `artifacts/<doc-title-slug>/upstream-mapping.yaml`:

```yaml
doc_title: "<Doc Title>"
generated: "<ISO 8601 timestamp>"
sig_docs_path: "<path used>"
mappings:
  - downstream_topic: "<topic text from ToC>"
    content_type: CONCEPT | PROCEDURE | REFERENCE
    upstream_sources:
      - path: <relative path to upstream file>
        relevance: exact | high | partial | low
        usage: adapt
        title: "<upstream file title>"
      - path: <another file>
        relevance: partial
        usage: reference
    notes: "<any observations about merging, gaps, or ambiguity>"
    net_new: false
  - downstream_topic: "<topic with no upstream match>"
    content_type: CONCEPT
    upstream_sources: []
    net_new: true
    notes: "No upstream equivalent - requires SME input"
```

The `<doc-title-slug>` is the Doc Title in kebab-case lowercase (e.g., "RHIVOS Image Building" -> `rhivos-image-building`).

Create the `artifacts/<doc-title-slug>/` directory if it does not exist.

### 7. Present mapping for review

Display a structured summary to the writer:

- Total topics mapped
- Count by confidence level (exact, high, partial, low)
- Count of net-new topics
- Flag any ambiguous content type inferences
- List low-confidence and net-new items explicitly

Then ask the writer to review using `AskUserQuestion`:

```
Mapped <N> topics for "<Doc Title>":
  - <X> high-confidence matches (exact/high)
  - <Y> low-confidence matches (partial/low) — flagged below
  - <Z> net-new topics (no upstream equivalent)

<list low-confidence and net-new items>

Review the full mapping at: artifacts/<slug>/upstream-mapping.yaml

Actions:
  approve — Accept mapping as-is
  inspect <topic> — Show full details for a topic
  reassign <topic> <upstream-path> — Change the upstream source
  set-type <topic> <CONCEPT|PROCEDURE|REFERENCE> — Override content type
  add-source <topic> <path> — Add an additional upstream source
  abort — Stop and save progress

Your choice?
```

If the writer makes changes, update the YAML and re-present the summary. Repeat until the writer approves.

## Output

```
artifacts/<doc-title-slug>/
  upstream-mapping.yaml
```
