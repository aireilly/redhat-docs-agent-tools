---
name: rhivos-jtbd-restructure
description: >-
  Restructures converted RHIVOS AsciiDoc modules according to Jobs To Be Done
  principles. Reframes headings as job-oriented titles, reorders sections by
  JTBD job map stages, creates stubs for net-new topics, and generates assembly
  files. Use this skill after rhivos-fetch-convert has produced approved modules.
argument-hint: "<doc-title-slug>"
allowed-tools: Read, Write, Bash, Glob, Grep, Edit, Skill, AskUserQuestion
---

# JTBD Restructure

Restructures converted AsciiDoc content from a technology-oriented to a job-oriented structure using the JTBD framework.

## When to use

- After `rhivos-fetch-convert` has produced approved AsciiDoc modules
- When the skeleton ToC has been updated and modules need re-structuring
- When reviewing JTBD alignment of existing modules

## Inputs

Parse from `$ARGUMENTS`:

- **`<doc-title-slug>`** (required, positional) — the kebab-case slug identifying the Doc Title (e.g., `rhivos-image-building`)

Expects these artifacts to exist:
- `artifacts/<doc-title-slug>/modules/` — converted `.adoc` files from Skill B
- `artifacts/<doc-title-slug>/upstream-mapping.yaml` — for downstream intent context

If the modules directory is empty or missing, stop with a clear error.

## Process

### 1. Read inputs

Read all `.adoc` files from `artifacts/<doc-title-slug>/modules/`.

Read the `upstream-mapping.yaml` to recover:
- The original downstream topic text (for intent context)
- Content types assigned to each topic
- Net-new topics that need stub creation

### 2. Extract JTBD records

Invoke the JTBD analysis skill on each module:

```
Skill: jtbd-analyze-adoc, args: "artifacts/<doc-title-slug>/modules/<file>"
```

This produces structured JTBD records: job statements, user stories, and procedures extracted from the content.

### 3. Compare against skeleton ToC

Invoke the JTBD comparison skill:

```
Skill: jtbd-compare, args: "artifacts/<doc-title-slug>/upstream-mapping.yaml artifacts/<doc-title-slug>/jtbd/jtbd-records.jsonl"
```

This identifies:
- Topics that align well with the target hierarchy
- Topics that need reframing (technology-oriented headings)
- Topics that should be split or merged
- Gaps in the job map

### 4. Restructure content

Apply JTBD principles to the modules. For each module:

#### a. Reframe headings

Transform technology-oriented headings into job-oriented titles:

| Before (technology-oriented) | After (job-oriented) |
|------------------------------|---------------------|
| "Automotive Image Builder manifests" | "Defining your image contents with a manifest" |
| "Boot options" | "Configuring boot behavior for your target platform" |
| "Testing overview" | "Verifying your image before deployment" |
| "RPM-OSTree" | "Managing system updates with RPM-OSTree" |

Heading rewrite rules:
- Concept modules: Frame as "Understanding..." or a noun phrase describing the user's mental model
- Procedure modules: Frame as gerund phrase describing the job ("Installing...", "Configuring...", "Building...")
- Reference modules: Frame as noun phrase describing what the user looks up ("Manifest configuration options", "Supported platform parameters")

#### b. Reorder sections

Within each module, reorder sections to follow the JTBD job map stages where applicable:

1. **Define** — What the user needs to understand before starting
2. **Locate** — Where to find required tools, files, or resources
3. **Prepare** — Prerequisites, setup, configuration
4. **Confirm** — Validation of readiness
5. **Execute** — The core task steps
6. **Monitor** — Checking progress and status
7. **Modify** — Adjustments and troubleshooting
8. **Conclude** — Cleanup, verification of completion

Not all stages apply to every module. Only reorder where it improves clarity.

#### c. Split or merge modules

Based on the JTBD comparison:
- **Split** a module if it covers two distinct jobs (e.g., a concept + procedure combined). Create separate files with appropriate prefixes.
- **Merge** modules if they cover fragments of the same job. Combine into a single module and flag the merge.

#### d. Add job-context abstracts

For each module, write or rewrite the `[role="_abstract"]` paragraph to follow the JTBD pattern:

```
When [situation], you need to [motivation], so you can [outcome].
```

Example:
```asciidoc
[role="_abstract"]
When you are preparing to build a RHIVOS image for a specific hardware platform, you need to define the image contents in a manifest file, so you can control exactly which packages, configurations, and customizations are included in the final image.
```

#### e. Create stub modules for net-new topics

For each entry in the mapping with `net_new: true`:

1. Create a stub module with the appropriate prefix and filename
2. Add the module anchor, content type attribute, and title
3. Add a JTBD-framed abstract paragraph
4. Add a `TODO` marker:

```asciidoc
[id="con_<topic-name>_{context}"]
= <Job-oriented title>
:_mod-docs-content-type: CONCEPT

[role="_abstract"]
When [situation], you need to [motivation], so you can [outcome].

// TODO: Requires SME input. No upstream equivalent exists for this topic.
// Downstream intent from ToC: "<original topic text>"
```

### 5. Generate assembly file

Create `artifacts/<doc-title-slug>/assemblies/assembly_<doc-title-slug>.adoc`:

```asciidoc
[id="assembly_<doc-title-slug>_{context}"]
= <Doc Title>
:context: <doc-title-slug>

[role="_abstract"]
<JTBD-framed abstract for the overall Doc Title>

include::modules/<module-1>.adoc[leveloffset=+1]

include::modules/<module-2>.adoc[leveloffset=+1]

...
```

Order the `include::` directives according to the JTBD job map sequence, not the original ToC order.

### 6. Generate consolidation report

Invoke the consolidation skill:

```
Skill: jtbd-consolidate, args: "artifacts/<doc-title-slug>"
```

Write JTBD artifacts to `artifacts/<doc-title-slug>/jtbd/`:
- `jtbd-records.jsonl` — extracted JTBD records
- `jtbd-toc-proposed.md` — proposed JTBD-structured ToC
- `jtbd-comparison.md` — comparison of current vs proposed structure
- `jtbd-consolidation-report.md` — summary consolidation report

### 7. Present results for review

Display the restructuring summary and ask the writer to review:

```
Restructured "<Doc Title>" using JTBD framework:
  - <N> modules reframed (<X> headings changed, <Y> sections reordered)
  - <N> stub modules created for net-new topics
  - <N> module splits, <N> module merges
  - Assembly file generated: assembly_<slug>.adoc

Heading rewrites:
  "<old heading>" -> "<new heading>"
  ...

Stubs created (require SME input):
  <filename>
  ...

JTBD comparison: artifacts/<slug>/jtbd/jtbd-comparison.md

Actions:
  approve — Accept restructuring, continue to next stage
  inspect <file> — Display a specific module
  reject-reframe <topic> — Revert a heading/structure change to pre-JTBD version
  accept-reframe <topic> — Explicitly confirm a reframe
  view-comparison — Display the full JTBD comparison report
  view-assembly — Display the generated assembly file
  abort — Stop and save progress

Your choice?
```

Repeat the review loop until the writer approves.

## Output

```
artifacts/<doc-title-slug>/
  modules/                                   # Updated/restructured
    con_<topic>.adoc
    proc_<topic>.adoc
    con_<net-new-topic>.adoc                 # Stubs
  assemblies/
    assembly_<doc-title-slug>.adoc
  jtbd/
    jtbd-records.jsonl
    jtbd-toc-proposed.md
    jtbd-comparison.md
    jtbd-consolidation-report.md
```

## Constraint

Restructuring reframes presentation, not technical content. Technical facts, commands, code examples, and configuration values must be preserved exactly as they appear in the converted modules. Only headings, section order, abstracts, and module boundaries change.
