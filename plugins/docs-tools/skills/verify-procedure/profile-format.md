# Verify-Procedure Profile Format

A profile is a Markdown file that configures a verify-procedure run against a procedure in an external repository. Profiles live in `profiles/` under this skill directory, organized by target repo and topic.

## File naming

```
<procedure-name>.profile.md
```

Examples:
- `installing-ptp-operator.profile.md`
- `installing-ptp-operator-sno.profile.md` (environment-specific variant)

## Directory structure

```
profiles/
├── openshift-docs/
│   ├── networking/
│   │   ├── installing-ptp-operator.profile.md
│   │   └── installing-ptp-operator-sno.profile.md
│   └── security/
│       └── configuring-certificates.profile.md
└── validated-patterns-docs/
    └── getting-started.profile.md
```

The directory structure mirrors the target repo's topic layout. This is a convention for discoverability, not enforced.

## Frontmatter

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

## Sections

All sections are optional. A profile with only frontmatter is valid.

### Attributes

Define AsciiDoc attribute values and ifdef/ifndef conditional resolution.

```markdown
## Attributes

| Attribute | Value |
|---|---|
| `product-title` | `OpenShift Container Platform` |
| `product-version` | `4.17` |
| `op-system-base-full` | `Red Hat Enterprise Linux (RHEL)` |

### Conditionals

| Attribute | Defined? |
|---|---|
| `openshift-enterprise` | yes |
| `openshift-origin` | no |
| `openshift-dedicated` | no |
```

- Attribute values replace `{attribute-name}` references in source blocks before execution
- Conditional flags determine which `ifdef::`/`ifndef::` branches to include
- Profile attributes override values found in the document header or `_attributes.adoc`

### Substitutions

Map placeholders to real values. Blocks that would be skipped as `skip-placeholder` become executable when all their placeholders are covered.

```markdown
## Substitutions

| Placeholder | Value | Notes |
|---|---|---|
| `<your-registry-url>` | `quay.io/kquinn-test` | |
| `<project-name>` | `verify-test-ns` | Created in prerequisites |
| `<your-token>` | `sha256~ABCdef123` | SA token from prereqs |
| `CHANGEME` | `my-real-value` | |
```

Matching rules:
- `<placeholder>` — matches the literal angle-bracket string
- `${VAR}` and `$VAR` — both forms are matched
- `CHANGEME`, `REPLACE` — matched as whole words only

### Prerequisites

Declare assumed cluster state and setup commands to run before the procedure.

```markdown
## Prerequisites

### Assumed state

- Operator `ptp-operator` is installed in namespace `openshift-ptp`
- User has `cluster-admin` role
- Cluster is SNO (single-node OpenShift)

### Setup commands

```bash
oc create namespace verify-test-ns --dry-run=client -o yaml | oc apply -f -
oc label namespace verify-test-ns test-run=verify --overwrite
```
```

- "Assumed state" is informational — included in the output header and used to contextualize failures
- "Setup commands" execute sequentially before Step 1. A failure aborts the run

### Scope

Control which steps to execute, skip, or treat differently.

```markdown
## Scope

| Control | Value |
|---|---|
| `mode` | `execute` |
| `steps` | `1-5` |
| `skip` | `3.b, 4.a` |
```

| Control | Values | Default | Description |
|---|---|---|---|
| `mode` | `execute`, `dry-run-only`, `yaml-only` | `execute` | `dry-run-only` validates YAML and does `--dry-run=client` but skips `oc create/apply`. `yaml-only` only checks YAML/JSON syntax |
| `steps` | Range (`1-5`), list (`1,3,5`), or `all` | `all` | Which top-level steps to include |
| `skip` | Comma-separated step labels | — | Steps to skip (reported as `[SKIP]`) |

Step labels use hierarchical numbering: `1`, `1.a`, `2.b.i`.

### Assertions

Define expected outcomes for specific steps.

```markdown
## Assertions

| Step | Type | Expected |
|---|---|---|
| `1.b` | `contains` | `namespace/openshift-ptp created` |
| `4` | `contains` | `Succeeded` |
| `4` | `not-contains` | `Failed` |
| `5.a` | `exit-code` | `0` |
| `6` | `regex` | `ptp-operator\.v4\.\d+\.\d+` |
```

| Type | Description |
|---|---|
| `contains` | stdout includes the string (case-sensitive) |
| `not-contains` | stdout does NOT include the string |
| `regex` | stdout matches the regex pattern |
| `exit-code` | command exited with this code (default is `0`) |

- A step can have multiple assertions — all must pass
- Assertion failures override exit-code pass/fail
- Steps without assertions use exit code only (existing behavior)

### Cleanup

Override default cleanup behavior.

```markdown
## Cleanup

### Preserve

- `namespace/openshift-ptp`
- `clusterrole/ptp-operator`

### Additional

```bash
oc delete project verify-test-ns --ignore-not-found
oc delete catalogsource custom-catalog -n openshift-marketplace --ignore-not-found
```
```

- **Preserve**: resources to NOT delete during cleanup
- **Additional**: extra cleanup commands run after standard tracked-resource deletion

## Complete example

```markdown
---
procedure: ~/openshift-docs/modules/networking/installing-ptp-operator.adoc
description: Verify PTP operator installation on SNO cluster
cluster: sno
timeout: 300
cleanup: auto
---

## Attributes

| Attribute | Value |
|---|---|
| `product-version` | `4.17` |

### Conditionals

| Attribute | Defined? |
|---|---|
| `openshift-enterprise` | yes |

## Substitutions

| Placeholder | Value | Notes |
|---|---|---|
| `<channel>` | `stable` | |

## Prerequisites

### Assumed state

- Cluster is reachable and user has cluster-admin

### Setup commands

```bash
oc adm policy add-cluster-role-to-user cluster-admin $(oc whoami) 2>/dev/null || true
```

## Scope

| Control | Value |
|---|---|
| `mode` | `execute` |
| `steps` | `all` |

## Assertions

| Step | Type | Expected |
|---|---|---|
| `1.b` | `contains` | `created` |
| `4` | `contains` | `Succeeded` |

## Cleanup

### Additional

```bash
oc delete project openshift-ptp --ignore-not-found
```
```
