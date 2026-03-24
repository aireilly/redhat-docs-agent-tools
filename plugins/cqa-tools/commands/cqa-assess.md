---
description: Run a CQA 2.1 content quality assessment against a Red Hat modular documentation repository
argument-hint: <docs-repo-path> [--scope repo|assembly|topic] [--mode assess|fix]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, Skill
---

## Name

cqa-tools:cqa-assess

## Synopsis

`/cqa-tools:cqa-assess <docs-repo-path> [--scope repo|assembly|topic] [--mode assess|fix]`

## Description

Run a CQA 2.1 content quality assessment against a Red Hat modular documentation repository. Covers all 54 parameters across three tabs — Pre-migration (P1-P19), Quality (Q1-Q25), and Onboarding (O1-O10).

The command follows a four-step workflow:

1. **Assess** — run automated scripts and AI-guided checks against 54 parameters
2. **Fix** — fix issues directly in source `.adoc` files (optional, based on mode)
3. **Score** — score each parameter (1-4) with evidence
4. **Report** — generate a before-and-after summary for JIRA tickets or MRs

## Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--scope` | `repo`, `assembly`, `topic` | `repo` | What to assess — entire repo, one assembly and its included topics, or one topic file |
| `--mode` | `assess`, `fix` | `assess` | Assess only (report issues, don't touch files) or assess and fix (fix issues, re-verify, then score) |

## Implementation

### Step 0: Parse arguments and ask for scope/mode

1. Validate that the docs repo path exists
2. If `--scope` is not provided, ask the user:
   - **Entire repo** — all files in the repository
   - **One assembly** — a specific assembly file and all topics it includes (resolve `include::` directives)
   - **One topic** — a single topic file
3. If `--mode` is not provided, ask the user:
   - **Assess only** — report issues and score, but do not modify any files
   - **Assess and fix** — report issues, fix them, re-verify, then score

### Steps 1-11: Run assessment guides in order

Run each skill in dependency order. Fixes in earlier steps prevent false positives in later ones.

| Step | Skill | Parameters |
|------|-------|------------|
| 1 | `cqa-tools:cqa-vale-check` | P1 |
| 2 | `cqa-tools:cqa-modularization` | P2-P7 |
| 3 | `cqa-tools:cqa-titles-descriptions` | P8-P11 |
| 4 | `cqa-tools:cqa-procedures` | P12, Q12-Q16 |
| 5 | `cqa-tools:cqa-editorial` | P13-P14, Q1-Q5, Q18, Q20 |
| 6 | `cqa-tools:cqa-links` | P15-P17, Q24-Q25 |
| 7 | `cqa-tools:cqa-legal-branding` | P18-P19, Q17, Q23, O1-O5 |
| 8 | `cqa-tools:cqa-user-focus` | Q6-Q11 |
| 9 | `cqa-tools:cqa-tables-images` | Q19, Q21-Q22 |
| 10 | `cqa-tools:cqa-onboarding` | O6-O10 |
| 11 | `cqa-tools:cqa-report` | Final report |

For each step:

1. Invoke the matching skill
2. Run the check — automated scripts where available, AI-guided review where needed
3. Apply to files within the user's chosen scope only
4. If fix mode: fix issues, re-run checks to verify 0 issues remain
5. Score the parameter (1-4) with evidence
6. Report results to the user

### Automation scripts

Ten Python scripts in `skills/cqa-assess/scripts/` automate repeatable checks. Run them against the docs repo:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/cqa-assess/scripts/check-product-names.py "$DOCS_REPO"
python3 ${CLAUDE_PLUGIN_ROOT}/skills/cqa-assess/scripts/check-scannability.py "$DOCS_REPO"
python3 ${CLAUDE_PLUGIN_ROOT}/skills/cqa-assess/scripts/check-readability.py "$DOCS_REPO"
```

Each script exits `0` (pass) or `1` (issues found). Python 3.9+ stdlib only.

## Usage Examples

```bash
# Full repo assessment (assess only)
/cqa-tools:cqa-assess /path/to/docs-repo

# Full repo assessment with fixes
/cqa-tools:cqa-assess /path/to/docs-repo --mode fix

# Assess one assembly and its topics
/cqa-tools:cqa-assess /path/to/docs-repo --scope assembly

# Assess one topic file
/cqa-tools:cqa-assess /path/to/docs-repo --scope topic
```

## Notes

- **Respect the user's chosen mode.** In assess mode, never modify files. In fix mode, fix everything before scoring.
- **Respect the user's chosen scope.** Only assess files within the scope.
- **0 errors, 0 warnings for automated checks.** Never suppress or ignore.
- **Evidence before claims.** Run the verification command, read the output, then state the score.
