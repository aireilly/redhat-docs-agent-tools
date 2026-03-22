---
name: cqa-procedures
description: Use when assessing CQA parameters P12, Q12-Q16 (procedure quality). Checks prerequisites, step counts, command examples, optional/conditional step formatting, verification sections, and Additional resources.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# CQA P12, Q12-Q16: Procedures

## Parameters

| # | Parameter | Level |
|---|-----------|-------|
| P12 | Prerequisites: `.Prerequisites` label, unordered list, max 10 items | Required |
| Q12 | Procedures have <= 10 top-level steps | Important |
| Q13 | Procedures include command examples | Important |
| Q14 | Optional/conditional steps use correct formatting | Important |
| Q15 | Procedures include `.Verification` section | Important |
| Q16 | Procedures include `Additional resources` section | Important |

## Directory note

Some repos use `modules/` instead of `topics/` for content files. All `topics/` references in this skill apply equally to `modules/`. The automation scripts accept `--scan-dirs` to override the default scan directories.

## Cross-references

- **P12 prerequisites** overlap with `cqa-tools:cqa-modularization` P4 Check 5 (same checks for label, formatting, count, declarative language, and placement). If both skills run, use the cqa-modularization result as canonical and skip the duplicate check here.
- **Procedure title grammar** (gerund form) is canonically assessed in `cqa-tools:cqa-modularization` P3 Check 5a. This skill focuses on procedure-specific quality (step count, examples, verification, formatting).

## Step 1: Identify the docs repo

Ask the user for the path to their Red Hat modular documentation repository. Store as `DOCS_REPO`.

## Step 2: P12 — Prerequisites

### Rule

Prerequisites state conditions that already exist, not actions the user must perform. They are optional in procedure modules.

Reference: https://redhat-documentation.github.io/modular-docs/#prerequisites

### Check 1: Label format

- Must use `.Prerequisites` (plural, dot-prefixed AsciiDoc block title), even with a single item
- Flag: `.Prerequisite` (singular), `**Prerequisites**` (bold pseudo-heading), `== Prerequisites` (subsection heading)

### Check 2: Formatting

- Prerequisites must use unordered list (`*` bullet markers), not ordered list (`. `)
- List items must have parallel grammatical structure
- Admonition blocks within the prerequisites section must be attached to a list item via `+` continuation — not placed as standalone blocks between `.Prerequisites` and `.Procedure`

### Check 3: Maximum count

- Do not exceed 10 prerequisite items per procedure
- Flag any procedure with more than 10 prerequisite items

### Check 4: Declarative language (no steps in prerequisites)

Prerequisites are conditions that must already be true, not steps the user must perform.

| Pattern | Assessment | Fix |
|---------|------------|-----|
| "You have access to..." | GOOD — declarative condition | — |
| "A running instance of..." | GOOD — declarative state | — |
| "`tool-name` is installed." | GOOD — declarative condition | — |
| "You know the namespace name." | GOOD — declarative condition | — |
| "The certificate files are generated." | GOOD — declarative state | — |
| "You must have access to..." | BAD — imperative "must have" | "You have access to..." |
| "You need to know the namespace name." | BAD — imperative "need to" | "You know the namespace name." |
| "Install the CLI tool." | BAD — imperative action step | "`{orch-cli}` is installed." |
| "Ensure that you have..." | BAD — imperative instruction | "You have..." |
| "To get X, rebuild Y." | BAD — imperative action disguised as prerequisite | "Your container image is based on the latest tag or SHA." |
| "Ask a DNS provider to..." | BAD — imperative action step | "A DNS record for the custom domain is configured." |
| "Generate the certificate and key files." | BAD — imperative action step | "The certificate and private key files are generated." |

A prerequisite may reference another procedure with an xref for HOW to achieve the condition:
```asciidoc
* `{prod-cli}` is installed. See: xref:proc_installing-the-dsc-management-tool_{context}[].
```

### Check 5: Placement

- `.Prerequisites` must appear before `.Procedure`
- No rendered content (admonitions, paragraphs, snippet includes) between the prerequisites list and `.Procedure` unless attached to a list item via `+` continuation

Common placement violations:

| Pattern | Problem | Fix |
|---------|---------|-----|
| Standalone `[WARNING]` block between prerequisites and `.Procedure` | Content gap between sections | Attach to last prerequisite item with `+` continuation |
| `include::snippets/...` between prerequisites and `.Procedure` | Snippet renders outside list | Attach to last prerequisite item with `+` continuation |
| `[IMPORTANT]` block with imperative text between prerequisites and `.Procedure` | Combines placement and language violations | Convert to proper prerequisite list items with declarative wording |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All procedures use `.Prerequisites` label, unordered list, ≤10 items, declarative language, correct placement, admonitions attached via `+` |
| **3** | 1-3 minor issues (e.g., a few "You must have" phrases, one misplaced admonition) |
| **2** | Multiple violations: imperative prerequisites, wrong label format, or misplaced admonitions |
| **1** | Prerequisites not checked or widespread violations |

## Step 3: Q12 — Procedure step count

### Rule

Procedures must have a maximum of 10 top-level steps in the `.Procedure` section. More than 10 steps indicates the procedure should be split or restructured.

### Check procedure

For each `proc_*.adoc` file:

1. Find the `.Procedure` section
2. Count top-level ordered list items (`. ` at the start of a line)
3. Do NOT count sub-steps (`.. ` or `... `) — only top-level steps
4. Flag files with more than 10 top-level steps

### Restructuring strategies for long procedures

| Strategy | When to use |
|----------|-------------|
| **Split into multiple procedures** | Steps fall into natural phases (setup, configure, verify) |
| **Merge logically coupled steps** | Two steps always happen together (e.g., "Create the file" then "Apply the file") |
| **Extract preparation steps** | Initial steps are generic setup — move to prerequisites |
| **Move verification to `.Verification`** | Last steps verify the result — use a separate section |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All procedures have ≤10 top-level steps |
| **3** | 1-2 procedures with 11 steps (borderline cases) |
| **2** | Multiple procedures with >10 steps |
| **1** | Step count not checked or widespread violations |

## Step 4: Q13 — Command examples

### Rule

Procedures involving CLI operations must include source blocks with actual commands the user can run or adapt. Source blocks must use correct language attributes and placeholder formatting.

### Check procedure

1. **Identify CLI procedures**: Procedures that reference `{orch-cli}`, `{prod-cli}`, `kubectl`, `curl`, `podman`, `docker`, or other CLI tools
2. **Verify source blocks exist**: Each CLI step should include a `[source,bash]` block with the actual command
3. **Verify source block language**: The language attribute must match the content

| Content | Source attribute |
|---------|----------------|
| Shell commands (`oc`, `curl`, `dsc`, etc.) | `[source,bash]` |
| SQL queries (`SELECT`, `DELETE`, `BEGIN`) | `[source,sql]` |
| Interactive terminal sessions (`psql`, `\c`) | `[source,terminal]` |
| YAML configuration | `[source,yaml]` |
| JSON data | `[source,json]` |

4. **Verify placeholder formatting**: Replaceable text must use `__<placeholder>__` with `subs="+quotes"` on the source block

```asciidoc
[source,bash,subs="+quotes",options="nowrap"]
----
oc exec -n openvsx "$POD" -- psql -d __<database_name>__
----
```

5. **Source block style**: Always use `[source,LANG]` — never bare `[LANG,...]`. The `source,` prefix is required for ccutil compatibility.

### Common issues

| Issue | Example | Fix |
|-------|---------|-----|
| Bare language attribute | `[bash,subs="verbatim"]` | `[source,bash]` |
| Wrong language for SQL | `[source,bash]` with SQL queries | `[source,sql]` |
| Bare placeholders | `<placeholder>` | `__<placeholder>__` with `subs="+quotes"` |
| Missing source block | "Run `oc get pods`" with no source block | Add `[source,bash]` block with the command |
| Bold backticks | `**\`command\`**` | Simplify to `` `command` `` |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All CLI procedures have source blocks with correct language, correct placeholders, and `source,` prefix |
| **3** | 1-3 minor issues (e.g., a few missing source blocks for simple single commands, minor placeholder formatting) |
| **2** | Multiple procedures lack command examples or widespread source block formatting issues |
| **1** | Command examples not checked or no source blocks in CLI procedures |

## Step 5: Q14 — Optional and conditional step formatting

### Rule

Optional and conditional steps must use standardized formatting so readers can quickly identify and skip them.

### Optional steps

Optional steps must begin with `Optional:` (capitalized, with colon, no parentheses):

| Pattern | Assessment |
|---------|------------|
| `. Optional: Configure the activity types...` | CORRECT |
| `. (Optional) Configure...` | INCORRECT — remove parentheses, add colon |
| `. (OPTIONAL) Configure...` | INCORRECT — remove parentheses, lowercase, add colon |
| `. Optionally, configure...` | INCORRECT — use "Optional:" prefix |
| `. Optionally configure...` | INCORRECT — use "Optional:" prefix |

### Conditional steps

Conditional steps must state the condition clearly, typically by leading with an "if" clause or specifying the context:

| Pattern | Assessment |
|---------|------------|
| `. If the storage_type is local, remove the extension files...` | CORRECT — specific condition |
| `. Master repository only: In the IP address field, type the IP address.` | CORRECT — scoped context |
| `. For restricted environments: Configure the proxy settings.` | CORRECT — scoped context |
| `. If applicable, remove the extension files...` | INCORRECT — vague. Specify what makes it applicable |
| `. If needed, configure...` | INCORRECT — vague. Specify the condition |

### Check procedure

Search all `proc_*.adoc` files for:

```bash
grep -rn -i 'optional' topics/ modules/ --include='*.adoc' 2>/dev/null
grep -rn -i 'if applicable' topics/ modules/ --include='*.adoc' 2>/dev/null
grep -rn -i 'if needed' topics/ modules/ --include='*.adoc' 2>/dev/null
```

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All optional steps use `Optional:` prefix. All conditional steps specify the condition clearly. No vague "if applicable" or "if needed". |
| **3** | 1-3 minor formatting issues (e.g., `Optionally,` instead of `Optional:`) |
| **2** | Multiple formatting violations or vague conditional steps |
| **1** | Not checked or no consistent formatting |

## Step 6: Q15 — Verification sections

### Rule

Procedures with observable outcomes should include a separate `.Verification` section after `.Procedure`. Verification steps must not be embedded as the last step inside `.Procedure`.

### When verification is required

- Procedures that create or modify resources (workspaces, secrets, configmaps, operators)
- Procedures that install or upgrade components
- Procedures that configure authentication (OAuth, TLS, certificates)
- Procedures that enable/disable features

### When verification can be omitted

- Simple UI navigation procedures (click a menu item, open a page)
- Single-command configuration changes with self-evident results
- Procedures that end with "the workspace starts" or similar immediate feedback
- Procedures where verification is part of the workflow itself (e.g., viewing a dashboard)

### Verification format

```asciidoc
.Verification

* Verify the result by running:
+
[source,bash]
----
oc get pods -n {prod-namespace}
----

* The output shows the pod in `Running` state.
```

- Uses unordered list (`*` items)
- Placed after `.Procedure`, before `.Troubleshooting` or `.Additional resources`
- No `[role="_additional-resources"]` annotation (unlike `.Additional resources`)

### Common issues

| Issue | Fix |
|-------|-----|
| Verification as last procedure step (`. Verify that...`) | Move to separate `.Verification` section |
| Verification mixed into the last procedure step | Extract into `.Verification` |
| No verification for critical procedure (OAuth, TLS, install) | Add `.Verification` with observable check |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All critical procedures have `.Verification`. No verification steps embedded as last `.Procedure` step. Verification omitted only where self-evident. |
| **3** | Most critical procedures have verification. 1-3 missing where they would be useful. Minor embedded verification in procedure steps. |
| **2** | Many critical procedures lack verification. Verification commonly embedded in `.Procedure`. |
| **1** | No verification sections or not checked |

## Step 7: Q16 — Additional resources sections

### Rule

Every procedure file must include an `[role="_additional-resources"]` `.Additional resources` section with relevant links to related content.

### Check procedure

1. Count all `proc_*.adoc` files
2. For each, check for the presence of `[role="_additional-resources"]` followed by `.Additional resources`
3. Flag any procedure file without an Additional resources section
4. Verify the section contains at least one link (xref or external link)
5. Verify the `[role="_additional-resources"]` annotation is present on the line immediately before `.Additional resources`

### Link quality

- Links must be relevant to the topic (not generic "learn more" links)
- Within-guide links use `xref:target_{context}[]`
- Cross-guide links use `link:{prod-ag-url}` or `link:{prod-ug-url}` with descriptive link text
- External links use `link:https://...[descriptive text]`

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | 100% of procedure files have Additional resources with relevant links and correct `[role="_additional-resources"]` annotation |
| **3** | ≥90% of procedure files have Additional resources. Minor formatting issues (≤3 files). |
| **2** | <90% of procedure files have Additional resources. Missing annotations. |
| **1** | Most files lack Additional resources or not checked |

## Step 8: Verify

After fixing any violations, run Vale to ensure no new warnings were introduced:

```bash
cd "$DOCS_REPO"
# Adjust directory names to match your repo structure (topics/ or modules/)
vale assemblies/ topics/ titles/administration_guide/master.adoc titles/user_guide/master.adoc
```
