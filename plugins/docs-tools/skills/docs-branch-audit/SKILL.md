---
name: docs-branch-audit
description: Audit which files from a PR, commit, or file list exist on target enterprise branches. Use this skill to plan cherry-pick backports by identifying which modules are applicable to each release.
author: Keith Quinn (kquinn@redhat.com)
allowed-tools: Bash, Read
---

# Branch audit skill

Audit file existence and content compatibility across enterprise branches to support intelligent cherry-pick backporting.

Given a source (PR URL, commit SHA, or file list) and one or more target branches, this skill reports which files exist on each branch and which would need to be excluded from a backport.

## Usage

```bash
# Audit a PR against target branches
bash ${SKILL_DIR}/scripts/branch_audit.sh \
  --pr https://github.com/openshift/openshift-docs/pull/106280 \
  --branches enterprise-4.17,enterprise-4.16

# Audit a commit
bash ${SKILL_DIR}/scripts/branch_audit.sh \
  --commit abc123def \
  --branches enterprise-4.17

# Audit from a file list
bash ${SKILL_DIR}/scripts/branch_audit.sh \
  --files /tmp/files-to-check.txt \
  --branches enterprise-4.17,enterprise-4.16

# JSON output for programmatic use
bash ${SKILL_DIR}/scripts/branch_audit.sh \
  --pr https://github.com/openshift/openshift-docs/pull/106280 \
  --branches enterprise-4.17 \
  --json

# Deep audit — check content compatibility for included files
bash ${SKILL_DIR}/scripts/branch_audit.sh \
  --pr https://github.com/openshift/openshift-docs/pull/106280 \
  --branches enterprise-4.17 \
  --deep
```

## Options

| Option | Description |
|--------|-------------|
| `--pr <url>` | GitHub PR URL to get file list from |
| `--commit <sha>` | Git commit SHA to get file list from |
| `--files <path>` | Text file with one file path per line |
| `--branches <list>` | Comma-separated list of target branches (required) |
| `--deep` | Run deep content comparison for included files (confidence levels, conditionals, structural differences) |
| `--json` | Output results as JSON |
| `--dry-run` | Show what would be checked without fetching branches |

## Output

### Text format (default)

```
=== Branch Audit: enterprise-4.17 ===

Include (22 files):
  modules/cnf-about-collecting-ptp-data.adoc
  modules/cnf-configuring-fifo-priority-scheduling-for-ptp.adoc
  ...

Exclude (5 files — not on branch):
  modules/cnf-configuring-enhanced-log-filtering-for-linuxptp.adoc
  modules/nw-ptp-t-bc-t-tsc-holdover.adoc
  ...

Summary: 22/27 files applicable to enterprise-4.17
```

### Deep audit output

```
=== Deep Audit: enterprise-4.17 ===

[HIGH] modules/cnf-about-collecting-ptp-data.adoc
    files-identical: File is identical on both branches

[MEDIUM] modules/nw-ptp-installing-operator-web-console.adoc
    moderate-divergence: 78 lines differ between branches
    conditionals: 2 conditional directive(s) found

[NEEDS-REVIEW] modules/nw-ptp-configuring-linuxptp-services-as-grandmaster-clock.adoc
    large-divergence: 245 lines differ between branches
    structure: heading count differs (source: 5, target: 3)

=== Deep Audit Summary ===

  Total files:  23
  High:         18 (changes will apply cleanly)
  Medium:       3 (likely applies, review recommended)
  Needs review: 2 (conflicts or large divergence expected)
```

## Confidence levels

| Level | Meaning | Action |
|-------|---------|--------|
| **HIGH** | File identical or < 20 lines differ | Cherry-pick will apply cleanly |
| **MEDIUM** | 20-99 lines differ, or conditionals present | Likely applies, minor conflicts possible |
| **NEEDS-REVIEW** | 100+ lines differ, structural changes | Conflicts expected, manual review needed |

## Prerequisites

- Must be run from within a git repository that has the target branches available (e.g., `openshift-docs`)
- For PR mode: requires `GITHUB_TOKEN` environment variable
- For commit mode: the commit must exist in the local repository
