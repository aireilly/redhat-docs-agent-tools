---
name: cqa-assess
description: Use when starting or continuing a full CQA 2.1 content quality assessment. Guides through all three tabs (Pre-migration, Quality, Onboarding) parameter by parameter.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# CQA 2.1 Content Quality Assessment

## Overview

Run a complete CQA 2.1 assessment against a Red Hat modular documentation repository. The assessment covers three tabs with 54 total parameters across Pre-migration, Quality, and Onboarding.

See [scoring-guide.md](../../reference/scoring-guide.md) for score definitions and [checklist.md](../../reference/checklist.md) for the full parameter list.

## Workflow

### Step 0: Ask the user for scope and mode

Before starting any checks, ask the user two questions:

**Scope** — what to assess:
- **Entire repo** — all files in the repository
- **One assembly** — a specific assembly file and all topics it includes (use `resolve-includes.py` to build the file list — see Include-tree resolution below)
- **One topic** — a single topic file
- **One parameter group** — a specific skill (e.g., editorial only) across the chosen file scope

**Mode** — what to do with issues:
- **Assess only** — report issues and score, but do not modify any files
- **Assess and fix** — report issues, fix them, re-verify, then score

**Severity filtering** — which parameters to run:
- **All** (default) — run all parameters in dependency order
- **Required only** — run only Required-level parameters (blockers). Skip Important-level parameters.
- **One skill** — run only the specified skill (e.g., `cqa-legal-branding`). Use the Skill Map below to identify which parameters are covered.
- **Skip list** — run all parameters except the specified ones (e.g., skip O9, O10 if Pantheon is not used)

### Steps 1-8: For each parameter

1. **Pick a parameter** from the checklist (or let the user specify one)
2. **Invoke the matching skill** for that parameter group
3. **Run the check** — automated where possible, manual review where needed. Apply to the files within the user's chosen scope only.
4. **If assess-and-fix mode**: fix issues found during the check, then re-run the check to confirm 0 issues
5. **Score the parameter** with evidence
6. **Report results** to the user: score, evidence, files changed (if any)
7. **Mark parameter complete** on the checklist
8. **Repeat** for the next parameter

## Skill Map

| Skill | Parameters Covered |
|-------|-------------------|
| `cqa-tools:cqa-vale-check` | P1 |
| `cqa-tools:cqa-modularization` | P2, P3, P4, P5, P6, P7 |
| `cqa-tools:cqa-titles-descriptions` | P8, P9, P10, P11 |
| `cqa-tools:cqa-procedures` | P12, Q12, Q13, Q14, Q15, Q16 |
| `cqa-tools:cqa-editorial` | P13, P14, Q1, Q2, Q3, Q4, Q5, Q18, Q20 |
| `cqa-tools:cqa-links` | P15, P16, P17, Q24, Q25 |
| `cqa-tools:cqa-legal-branding` | P18, P19, Q17, Q23, O1, O2, O3, O4, O5 |
| `cqa-tools:cqa-user-focus` | Q6, Q7, Q8, Q9, Q10, Q11 |
| `cqa-tools:cqa-tables-images` | Q19, Q21, Q22 |
| `cqa-tools:cqa-onboarding` | O6, O7, O8, O9, O10 |
| `cqa-tools:cqa-report` | Final report generation |

## Assessment Order

Recommended order (dependencies flow downward):

1. `cqa-tools:cqa-vale-check` — foundational; fixes here affect other checks
2. `cqa-tools:cqa-modularization` — structural compliance
3. `cqa-tools:cqa-titles-descriptions` — metadata quality
4. `cqa-tools:cqa-procedures` — procedure structure
5. `cqa-tools:cqa-editorial` — writing quality
6. `cqa-tools:cqa-links` — cross-references and URLs
7. `cqa-tools:cqa-legal-branding` — compliance
8. `cqa-tools:cqa-user-focus` — content quality
9. `cqa-tools:cqa-tables-images` — visual elements
10. `cqa-tools:cqa-onboarding` — publishing readiness
11. `cqa-tools:cqa-report` — final summary

## Include-tree resolution

When the user chooses "One assembly" scope, use `resolve-includes.py` to build the exact file list before running any checks. This prevents scope leakage (scanning files outside the assembly's include tree).

```bash
# List all files included by an assembly (recursively follows include:: directives)
python3 scripts/resolve-includes.py "$DOCS_REPO/assemblies/admin/assembly_installing.adoc" --base-dir "$DOCS_REPO"

# Tree view showing the include hierarchy
python3 scripts/resolve-includes.py "$DOCS_REPO/assemblies/admin/assembly_installing.adoc" --base-dir "$DOCS_REPO" --format tree

# JSON output for programmatic use
python3 scripts/resolve-includes.py "$DOCS_REPO/assemblies/admin/assembly_installing.adoc" --base-dir "$DOCS_REPO" --format json

# Include the root file itself in the output
python3 scripts/resolve-includes.py "$DOCS_REPO/assemblies/admin/assembly_installing.adoc" --base-dir "$DOCS_REPO" --include-root
```

The script handles symlinks, attribute placeholders in paths, circular includes, and conditional includes (`ifdef`/`ifndef`). Exit codes: 0 (all resolved), 1 (some unresolved), 2 (invalid arguments).

**Scoping workflow:**

1. Run `resolve-includes.py` to get the file list for the assembly
2. Pass only those files to each check script via `--scan-dirs` or by filtering output
3. Score based only on issues within the scoped files

## Automation Scripts

Reusable scripts in `skills/cqa-assess/scripts/` automate repetitive checks. Each script accepts a docs repo path and exits 0 (pass), 1 (issues found), or 2 (invalid arguments). Python 3.9+ stdlib only.

All check scripts (except `check-legal-notices.py`) scan `assemblies/`, `modules/`, `topics/`, and `snippets/` by default. Use `--scan-dirs` to override (e.g., `--scan-dirs topics assemblies` to skip snippets). `check-legal-notices.py` checks `titles/*/` for docinfo.xml and the repo root for LICENSE — use `--repo-root` to specify the repo root when the docs directory is a subdirectory.

| Script | Skill | Parameters | Extra flags |
|--------|-------|-----------|-------------|
| `check-product-names.py` | `cqa-tools:cqa-legal-branding` | P18, O1, O3 | `--config`, `--fix` |
| `check-conscious-language.py` | `cqa-tools:cqa-legal-branding` | Q23, O4 | |
| `check-content-types.py` | `cqa-tools:cqa-modularization` | P3, P4, P5 | `--no-prefix-check` |
| `check-tp-disclaimers.py` | `cqa-tools:cqa-legal-branding` | P19, O5 | |
| `check-external-links.py` | `cqa-tools:cqa-legal-branding` | Q17 | `--details` |
| `check-legal-notices.py` | `cqa-tools:cqa-legal-branding` | O2 | `--repo-root` |
| `check-scannability.py` | `cqa-tools:cqa-editorial` | Q1 | |
| `check-simple-words.py` | `cqa-tools:cqa-editorial` | Q3 | |
| `check-readability.py` | `cqa-tools:cqa-editorial` | Q4 | |
| `check-fluff.py` | `cqa-tools:cqa-editorial` | Q5 | |
| `resolve-includes.py` | (utility) | — | `--format`, `--include-root` |

Run all check scripts at once:

```bash
for script in scripts/check-*.py; do
  python3 "$script" "$DOCS_REPO"
  echo "---"
done
```

## Important Rules

- **Respect the user's chosen mode.** In assess-only mode, never modify files. In assess-and-fix mode, fix everything before scoring.
- **Respect the user's chosen scope.** Only assess files within the scope (repo, assembly + its topics, or single topic). Do not scan files outside the scope. For assembly scope, use `resolve-includes.py` to determine the exact file list.
- **Respect severity filtering.** If the user selected "Required only" or provided a skip list, only run the applicable parameters.
- **0 errors, 0 warnings for automated checks.** Never suppress or ignore.
- **Evidence before claims.** Run the verification command, read the output, then state the score.
- **Cross-reference awareness.** Some parameters overlap across skills (e.g., P12 prerequisites in both cqa-procedures and cqa-modularization). When both skills run, use the canonical skill's result and skip the duplicate. See each skill's Cross-references section.
- **Update project rules** with any new rules discovered during the assessment.
