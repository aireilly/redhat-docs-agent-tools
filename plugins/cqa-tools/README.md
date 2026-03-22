# CQA Tools

Assess, fix, and score Red Hat modular documentation against all 54 CQA 2.1 parameters.

```text
                         ┌─────────┐
                         │  Assess  │  Run checks against your docs
                         └────┬─────┘
                              │
                         ┌────▼─────┐
                         │   Fix    │  Fix issues found (optional)
                         └────┬─────┘
                              │
                         ┌────▼─────┐
                         │  Score   │  Score each parameter (1-4) with evidence
                         └────┬─────┘
                              │
                         ┌────▼─────┐
                         │  Report  │  Before-and-after summary for JIRA/MRs
                         └──────────┘
```

**What it checks**: 54 parameters across three CQA tabs — Pre-migration (P1-P19), Quality (Q1-Q25), and Onboarding (O1-O10) to docs.redhat.com.

**Choose your scope**: entire docs repo, a single assembly and its topics, or one topic file.

**Choose your mode**: assess only (report issues, don't touch files) or assess and fix (fix issues, re-verify, then score).

## Quick start

```bash
# Full assessment
/cqa-tools:cqa-assess /path/to/docs-repo

# Assess and fix
/cqa-tools:cqa-assess /path/to/docs-repo --mode fix

# Assess one assembly and its topics
/cqa-tools:cqa-assess /path/to/docs-repo --scope assembly
```

Or invoke individual skills:

```bash
/cqa-tools:cqa-vale-check        # P1: Vale DITA linting
/cqa-tools:cqa-modularization    # P2-P7: Module structure
/cqa-tools:cqa-editorial         # Q1-Q5, Q18, Q20: Writing quality
```

## Prerequisites

| Requirement | Version | Used by |
|-------------|---------|---------|
| Python | 3.9+ | Automation scripts (stdlib only, no pip install needed) |
| [Vale](https://vale.sh/) | v3.x+ | P1: Vale DITA linting |
| [asciidoctor-dita-vale](https://github.com/redhat-documentation/vale-at-red-hat) styles | Latest | P1: Vale DITA linting |

## Command

| Command | Description |
|---------|-------------|
| `cqa-assess` | Run a full CQA 2.1 assessment — walks through all 54 parameters in dependency order |

## Skills

| Order | Skill | Parameters | What it assesses |
|-------|-------|------------|------------------|
| 1 | `cqa-tools:cqa-vale-check` | P1 | Vale DITA linting — foundational, fixes here affect all other checks |
| 2 | `cqa-tools:cqa-modularization` | P2-P7 | Assembly structure, module prefixes, content types, nesting rules |
| 3 | `cqa-tools:cqa-titles-descriptions` | P8-P11 | Title quality, short descriptions, DITA abstracts |
| 4 | `cqa-tools:cqa-procedures` | P12, Q12-Q16 | Prerequisites, step count, command examples, verification sections |
| 5 | `cqa-tools:cqa-editorial` | P13-P14, Q1-Q5, Q18, Q20 | Scannability, readability, complex words, fluff, tone, style guide |
| 6 | `cqa-tools:cqa-links` | P15-P17, Q24-Q25 | Broken xrefs, missing includes, dead URLs, content journey |
| 7 | `cqa-tools:cqa-legal-branding` | P18-P19, Q17, Q23, O1-O5 | Product names, TP/DP disclaimers, conscious language, legal notices |
| 8 | `cqa-tools:cqa-user-focus` | Q6-Q11 | Persona targeting, acronym expansion, admonition density |
| 9 | `cqa-tools:cqa-tables-images` | Q19, Q21-Q22 | Screenshots, table captions and headers, image alt text |
| 10 | `cqa-tools:cqa-onboarding` | O6-O10 | Support disclaimers, SME verification, Pantheon publishing |
| 11 | `cqa-tools:cqa-report` | Final | Before-and-after summary report with scores and evidence |

## Automation scripts

Ten check scripts and one utility in `skills/cqa-assess/scripts/` automate repeatable checks. The `cqa-assess` command runs them automatically. Each script accepts a docs repo path, prints structured output, and exits `0` (pass), `1` (issues found), or `2` (invalid arguments). Python 3.9+ stdlib only, no pip install needed.

**Directory support:** All scripts scan `assemblies/`, `modules/`, `topics/`, and `snippets/` by default. Repos using `modules/` instead of `topics/` work without configuration. Use `--scan-dirs` to override.

| Script | Parameters | What it checks | Extra flags |
|--------|-----------|----------------|-------------|
| `check-product-names.py` | P18, O1, O3 | Hardcoded product names in prose and image alt text | `--config`, `--fix` |
| `check-conscious-language.py` | Q23, O4 | Exclusionary terms (master, slave, whitelist, blacklist, dummy) | |
| `check-content-types.py` | P3, P4, P5 | Filename prefix vs content type declaration, required elements | `--no-prefix-check` |
| `check-tp-disclaimers.py` | P19, O5 | Technology Preview and Developer Preview disclaimer compliance | |
| `check-external-links.py` | Q17 | External URL extraction and domain categorization | `--details` |
| `check-legal-notices.py` | O2 | LICENSE file and docinfo.xml existence | `--repo-root` |
| `check-scannability.py` | Q1 | Sentence length, paragraph length, list conversion opportunities | |
| `check-simple-words.py` | Q3 | Complex word patterns (utilize, leverage, in order to, etc.) | |
| `check-readability.py` | Q4 | Flesch-Kincaid Grade Level per file and overall | |
| `check-fluff.py` | Q5 | Self-referential patterns, forward-referencing, filler phrases | |
| `resolve-includes.py` | (utility) | Recursively resolve `include::` tree from any `.adoc` file | `--format`, `--include-root` |

### Common flags

| Flag | Scripts | Description |
|------|---------|-------------|
| `--scan-dirs` | All `check-*` scripts except `check-legal-notices.py` | Override default scan directories (e.g., `--scan-dirs topics assemblies`) |
| `--config FILE` | `check-product-names.py` | JSON config for repo-specific product names and attributes |
| `--fix` | `check-product-names.py` | Auto-replace hardcoded product names with attributes |
| `--no-prefix-check` | `check-content-types.py` | Detect content type from `:_mod-docs-content-type:` instead of filename prefix |
| `--repo-root DIR` | `check-legal-notices.py` | Repo root for LICENSE file check (auto-detects `.git` if omitted) |
| `--details` | `check-external-links.py` | Show per-URL breakdown by domain |
| `--format` | `resolve-includes.py` | Output format: `files` (default), `tree`, or `json` |
| `--include-root` | `resolve-includes.py` | Include the root file itself in the output |

## Scoring

| Score | Label | Meaning |
|-------|-------|---------|
| **4** | Meets criteria | Zero issues found |
| **3** | Mostly meets | Minor issues, not blocking publication |
| **2** | Mostly does not meet | Significant issues requiring remediation |
| **1** | Does not meet | Critical blockers preventing publication |

## References

- [`reference/scoring-guide.md`](reference/scoring-guide.md) — Scoring rules and parameter-to-skill mapping
- [`reference/checklist.md`](reference/checklist.md) — Full 54-parameter CQA 2.1 checklist
- [Red Hat modular docs guide](https://redhat-documentation.github.io/modular-docs/)
- [DITA 1.3 spec](https://docs.oasis-open.org/dita/dita/v1.3/dita-v1.3-part3-all-inclusive.html)
