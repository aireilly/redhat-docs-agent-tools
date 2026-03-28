# Verify-Procedure Profiles

**Date:** 2026-03-25
**Status:** Draft
**Scope:** verify-procedure skill, new profiles directory

## Problem

The verify-procedure skill executes AsciiDoc procedures against a live cluster, but every run requires interactive guidance from the user:

1. **Placeholders block execution.** Procedures contain `<your-registry-url>`, `${PROJECT_NAME}`, `CHANGEME` patterns. The skill skips these blocks entirely — often the most important steps in the procedure.

2. **Conditional branches are guessed.** `ifdef::openshift-enterprise[]` blocks require Claude to guess which branch to take. Wrong guesses silently test the wrong content.

3. **Prerequisites are discovered at runtime.** A procedure assumes a namespace exists or an operator is installed. Claude discovers this when step 3 fails, not before step 1.

4. **No repeatability.** Running the same procedure next week requires re-explaining the same context. There is no way to share a "known-good run configuration" with a colleague or store it for CI.

5. **No assertions beyond exit codes.** A command that exits 0 passes, even if its output shows `0/0 pods running` or `Pending` instead of `Succeeded`.

6. **Profiles cannot live in the target repo.** Users verify procedures in external repositories like `openshift-docs` where they can only commit AsciiDoc source. Run configuration must live elsewhere.

## Decision

Add **profiles** — Markdown files stored in this repo (`redhat-docs-agent-tools`) that configure verify-procedure runs against procedures in external repositories. A profile maps to a specific procedure and provides substitutions, attributes, prerequisites, scope controls, assertions, and cleanup behavior.

The term "profile" is used instead of "spec" to avoid confusion with design specs in the `specs/` directory.

Profiles are additive: a procedure without a profile runs exactly as it does today. Profiles only add context — they never remove existing skill behavior.

## Design

### Profile storage

Profiles live in this repo under the verify-procedure skill directory:

```
plugins/docs-tools/skills/verify-procedure/
├── profiles/
│   ├── openshift-docs/                          # one directory per target repo
│   │   ├── networking/
│   │   │   ├── installing-ptp-operator.profile.md
│   │   │   └── installing-ptp-operator-sno.profile.md
│   │   └── security/
│   │       └── configuring-certificates.profile.md
│   └── validated-patterns-docs/
│       └── getting-started.profile.md
├── scripts/
│   └── verify_proc.sh
└── SKILL.md
```

The directory structure under `profiles/` mirrors the topic structure of the target repo for discoverability. This is a convention, not enforced.

### Profile format

A profile is a Markdown file with YAML frontmatter and optional sections.

#### Frontmatter

```yaml
---
procedure: ~/openshift-docs/modules/networking/installing-ptp-operator.adoc
description: Verify PTP operator installation on SNO cluster
cluster: sno
timeout: 300
cleanup: auto
---
```

| Field | Required | Default | Description |
|---|---|---|---|
| `procedure` | **Yes** | — | Absolute or `~`-relative path to the `.adoc` file in the external repo |
| `description` | No | — | Human-readable label shown in output header |
| `cluster` | No | — | Freeform tag for organizing profiles by environment |
| `timeout` | No | `120` | Command timeout in seconds, passed as `VERIFY_TIMEOUT` env var |
| `cleanup` | No | `manual` | `auto` runs cleanup after summary; `skip` disables it; `manual` (default) waits for user |

The `procedure` field is what connects this profile to an external file. It must be an absolute path or use `~` expansion. Relative paths are relative to the profile file itself.

#### Sections

All sections are optional. A profile with only frontmatter is valid (it just points at the procedure and sets timeout/cleanup).

**## Attributes** — AsciiDoc attribute values and ifdef/ifndef conditional flags:

```markdown
## Attributes

| Attribute | Value |
|---|---|
| `product-title` | `OpenShift Container Platform` |
| `product-version` | `4.17` |

### Conditionals

| Attribute | Defined? |
|---|---|
| `openshift-enterprise` | yes |
| `openshift-origin` | no |
```

**## Substitutions** — placeholder-to-value mappings that turn skipped blocks into executable blocks:

```markdown
## Substitutions

| Placeholder | Value | Notes |
|---|---|---|
| `<your-registry-url>` | `quay.io/kquinn-test` | |
| `<project-name>` | `verify-test-ns` | Created in prerequisites |
| `CHANGEME` | `my-real-value` | |
```

Matching rules:
- `<placeholder>` — literal angle-bracket match
- `${VAR}` and `$VAR` — both forms matched
- `CHANGEME`, `REPLACE` — whole-word match only

**## Prerequisites** — assumed state (informational) and setup commands (executed before step 1):

```markdown
## Prerequisites

### Assumed state

- User has `cluster-admin` role
- Cluster is SNO (single-node OpenShift)

### Setup commands

```bash
oc create namespace verify-test-ns --dry-run=client -o yaml | oc apply -f -
```
```

Setup command failures abort the run.

**## Scope** — controls which steps to execute:

```markdown
## Scope

| Control | Value |
|---|---|
| `mode` | `execute` |
| `steps` | `1-5` |
| `skip` | `3.b, 4.a` |
```

| Control | Values | Default |
|---|---|---|
| `mode` | `execute`, `dry-run-only`, `yaml-only` | `execute` |
| `steps` | Range (`1-5`), list (`1,3,5`), or `all` | `all` |
| `skip` | Comma-separated step labels | — |

- `dry-run-only`: validates YAML with `--dry-run=client` but skips `oc create/apply`
- `yaml-only`: syntax checks only, no cluster connection required

**## Assertions** — expected outcomes checked after step execution:

```markdown
## Assertions

| Step | Type | Expected |
|---|---|---|
| `1.b` | `contains` | `created` |
| `4` | `contains` | `Succeeded` |
| `4` | `not-contains` | `Failed` |
| `6` | `regex` | `ptp-operator\.v4\.\d+\.\d+` |
```

| Type | Description |
|---|---|
| `contains` | stdout includes the string (case-sensitive) |
| `not-contains` | stdout does NOT include the string |
| `regex` | stdout matches the regex pattern |
| `exit-code` | command exited with this code (default is `0`) |

A step can have multiple assertions. Assertion failures override exit-code pass/fail.

**## Cleanup** — preserve list and additional teardown commands:

```markdown
## Cleanup

### Preserve

- `namespace/openshift-ptp`

### Additional

```bash
oc delete project verify-test-ns --ignore-not-found
```
```

### Profile discovery

When the user invokes verify-procedure, profiles are found in this order:

1. **Explicit path**: user passes a profile file path as a second argument
2. **Profile directory search**: the skill searches `profiles/` for a profile whose `procedure` frontmatter matches the `.adoc` path the user provided
3. **No profile**: run with default behavior (current behavior, unchanged)

The skill reports which profile was loaded (or "none") in the output header.

### Invocation

```bash
# With explicit profile
/verify-procedure ~/openshift-docs/modules/networking/installing-ptp-operator.adoc profiles/openshift-docs/networking/installing-ptp-operator.profile.md

# With auto-discovery (skill searches profiles/ for matching procedure path)
/verify-procedure ~/openshift-docs/modules/networking/installing-ptp-operator.adoc

# Run a profile directly (procedure path comes from frontmatter)
/verify-procedure --profile profiles/openshift-docs/networking/installing-ptp-operator.profile.md

# No profile (current behavior)
/verify-procedure ~/openshift-docs/modules/networking/installing-ptp-operator.adoc
```

## Changes by file

### `plugins/docs-tools/skills/verify-procedure/SKILL.md`

#### New section: Profiles (after Architecture, before Workflow)

Add profile documentation covering:
- What profiles are and where they live
- Discovery order
- How to invoke with a profile

#### Step 0: Connectivity check

- If a profile defines `timeout`, export `VERIFY_TIMEOUT` before calling `init`
- If profile `mode` is `yaml-only`, skip the connection check (no cluster needed)

#### New: Step 0.5 — Run prerequisite setup

- If the profile has `## Prerequisites` → `### Setup commands`, execute each command via `verify_proc.sh execute "prereq-N" "<command>"`
- Failures abort the run
- "Assumed state" items appear in the output header

#### Step 1: Parse the AsciiDoc file

Attribute resolution priority changes to:
1. **Profile attributes** (highest priority)
2. Document header
3. `_attributes.adoc`
4. Cluster fallback (`oc version`)

Conditional resolution:
- Profile conditional flags take priority over document/attribute file

Classification changes:
- `skip-placeholder` classification now checks the profile's substitution map. If all placeholders in a block are covered, reclassify as `execute`/`validate-yaml`/`save-to-file`

New sub-steps after classification:
- **Apply substitutions**: replace placeholders with profile values, reclassify blocks
- **Apply scope controls**: filter by `steps` range, remove `skip` labels, enforce `mode`

#### Step 2: Execute the procedure

New sub-step after each execution:
- **Check assertions**: if the profile defines assertions for this step label, check them. Report `[ASSERT]` results. Assertion failures override exit-code pass/fail.

#### Step 4: Cleanup

Behavior determined by profile `cleanup` value:
- `auto` — run immediately after summary
- `manual` (default) — wait for user
- `skip` — do not clean up

Profile cleanup overrides:
- **Preserve list**: resources not deleted during cleanup, reported as `[PRESERVED]`
- **Additional commands**: extra teardown after standard cleanup

#### Output format

Updated header to include profile information:

```
--- Procedure Verification: <filename> ---
Profile: installing-ptp-operator.profile.md (or "none")
Workdir: /tmp/verify-proc-XXXXXX
CLI: oc | Cluster: https://api.cluster.example.com:6443
Mode: execute | Timeout: 300s | Cleanup: auto
Assumed state: User has cluster-admin
```

Summary line updated:
```
Total: 7 | Passed: 7 | Failed: 0 | Assertions: 2/2 passed
```

### `plugins/docs-tools/skills/verify-procedure/scripts/verify_proc.sh`

One change:

```bash
# Before
TIMEOUT=120

# After
TIMEOUT="${VERIFY_TIMEOUT:-120}"
```

This allows the SKILL.md to pass `export VERIFY_TIMEOUT=300` before calling `init`, driven by the profile's `timeout` frontmatter value.

### New directory: `plugins/docs-tools/skills/verify-procedure/profiles/`

Created as an empty directory (with `.gitkeep`) to establish the convention. Profiles are added as users create them for specific procedures they want to verify repeatably.

### New file: `plugins/docs-tools/skills/verify-procedure/profile-format.md`

Reference document for profile authors. Documents all frontmatter fields, sections, matching rules, and includes a complete example. Not a skill — a plain reference file.

## End-to-end flows

### With profile (default mode)

```
1. User: /verify-procedure ~/openshift-docs/modules/networking/installing-ptp-operator.adoc
2. Skill discovers matching profile in profiles/openshift-docs/networking/
3. Parse profile: timeout=300, cleanup=auto, substitutions, assertions
4. export VERIFY_TIMEOUT=300 && bash scripts/verify_proc.sh init
5. bash scripts/verify_proc.sh check-connection
6. Run prereq setup commands from profile
7. Read .adoc file, resolve includes/ifdefs using profile conditionals
8. Classify blocks, apply substitutions (skip-placeholder → execute)
9. Apply scope controls (step range, skip list, mode)
10. Execute blocks sequentially, check assertions after each step
11. bash scripts/verify_proc.sh summary
12. Auto-cleanup (profile says cleanup: auto)
```

### Without profile (current behavior, unchanged)

```
1. User: /verify-procedure ~/openshift-docs/modules/networking/some-procedure.adoc
2. No matching profile found — proceed silently
3. bash scripts/verify_proc.sh init
4. bash scripts/verify_proc.sh check-connection
5. Read .adoc file, resolve includes/ifdefs (Claude guesses)
6. Classify blocks (placeholders skipped, attributes best-effort)
7. Execute blocks sequentially (exit code = pass/fail)
8. bash scripts/verify_proc.sh summary
9. Cleanup when user asks
```

### yaml-only mode (offline validation)

```
1. User: /verify-procedure --profile profiles/openshift-docs/networking/installing-ptp-operator-sno.profile.md
2. Profile has mode: yaml-only
3. bash scripts/verify_proc.sh init (no check-connection)
4. Read .adoc, classify blocks
5. Validate YAML/JSON syntax only — no execution, no dry-runs
6. Summary
```

## Migration

No migration needed. This is purely additive — existing behavior is unchanged when no profile is present.
