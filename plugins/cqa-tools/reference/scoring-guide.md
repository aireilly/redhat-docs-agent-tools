# CQA 2.1 Scoring Guide

## Score Definitions

| Score | Label | Meaning |
|-------|-------|---------|
| **4** | Meets criteria | Fully compliant. Zero issues found. |
| **3** | Mostly meets | Minor issues exist but do not block publishing. |
| **2** | Mostly does not meet | Significant issues that should be resolved before publishing. |
| **1** | Does not meet | Critical issues that block publishing. |

## Scoring Rules

- **Evidence-based only.** Every score must cite specific file counts, line numbers, or tool output. Never score based on impression.
- **Run the check before scoring.** If a check requires a tool (Vale, the docs repo's `validate-refs.py`), run it and paste the result.
- **Zero tolerance for "4".** A score of 4 means zero violations. One violation drops to 3.
- **Distinguish required vs important.** Required items that score 2 or below are blockers. Important items at 2 are flagged but not blocking.

## Assessment Levels

| Level | Label | Impact |
|-------|-------|--------|
| **Required** | Non-negotiable | Must score 3+ to pass. Score of 2 or below blocks publishing. |
| **Important** | Negotiable | Should score 3+. Score of 2 is flagged but may be accepted with justification. |

## Report Format

Each parameter assessment must include:

1. **Parameter name and number** (e.g., "P1: Vale DITA check")
2. **Level** (Required / Important)
3. **Score** (4 / 3 / 2 / 1)
4. **Evidence** — tool output, file counts, specific examples
5. **Files affected** — list of files with issues (if any)
6. **Fixes applied** — what was changed to resolve issues (if any)

## Tab Structure

### Pre-migration (19 parameters)

| # | Parameter | Level | Skill |
|---|-----------|-------|-------|
| P1 | Vale asciidoctor-dita-vale check | Required | `cqa-vale-check` (delegates to `dita-tools:dita-validate-asciidoc`) |
| P2 | Assembly structure (intro + includes only) | Required | `cqa-modularization` |
| P3 | Content is modularized | Required | `cqa-modularization` |
| P4 | Modules use official templates | Required | `cqa-modularization` |
| P5 | All required modular elements present | Required | `cqa-modularization` |
| P6 | Assemblies use official template | Required | `cqa-modularization` |
| P7 | Content not deeply nested (max 3 levels) | Important | `cqa-modularization` |
| P8 | Short descriptions clear and actionable | Required | `cqa-titles-descriptions` |
| P9 | Short descriptions: 50-300 chars, `[role="_abstract"]` | Required | `cqa-titles-descriptions` |
| P10 | Titles: short, long, and descriptive | Important | `cqa-titles-descriptions` |
| P11 | Titles: brief, complete, and descriptive | Required | `cqa-titles-descriptions` |
| P12 | Prerequisites: label, formatting, max 10 | Required | `cqa-procedures` |
| P13 | Grammatically correct, American English | Required | `cqa-editorial` |
| P14 | Correct content type per file | Required | `cqa-editorial` |
| P15 | No broken links | Required | `cqa-links` |
| P16 | Redirects work | Required | `cqa-links` |
| P17 | Interlinked within 3 clicks | Important | `cqa-links` |
| P18 | Official product names used | Required | `cqa-legal-branding` |
| P19 | Tech Preview/Developer Preview disclaimers | Required | `cqa-legal-branding` |

### Quality (25 parameters)

| # | Parameter | Level | Skill |
|---|-----------|-------|-------|
| Q1 | Content is scannable (sentences, paragraphs) | Required | `cqa-editorial` |
| Q2 | Content is clearly written | Important | `cqa-editorial` |
| Q3 | Content uses simple words | Important | `cqa-editorial` |
| Q4 | Readability score (11-12th grade) | Important | `cqa-editorial` |
| Q5 | Remove fluff (minimalism) | Important | `cqa-editorial` |
| Q6 | Content applies to target persona | Important | `cqa-user-focus` |
| Q7 | Content addresses user pain points | Important | `cqa-user-focus` |
| Q8 | Acronyms defined before use | Important | `cqa-user-focus` |
| Q9 | Additional resources with useful links | Important | `cqa-user-focus` |
| Q10 | Admonitions not overused | Important | `cqa-user-focus` |
| Q11 | Assembly intro targets audience | Important | `cqa-user-focus` |
| Q12 | Procedures <= 10 steps | Important | `cqa-procedures` |
| Q13 | Procedures include command examples | Important | `cqa-procedures` |
| Q14 | Optional/conditional steps formatted correctly | Important | `cqa-procedures` |
| Q15 | Procedures include verification steps | Important | `cqa-procedures` |
| Q16 | Procedures include Additional resources | Important | `cqa-procedures` |
| Q17 | Non-RH links acknowledged or disclaimed | Important | `cqa-legal-branding` |
| Q18 | Content follows style guide | Required | `cqa-editorial` |
| Q19 | No excessive screen images | Important | `cqa-tables-images` |
| Q20 | Appropriate conversational tone | Important | `cqa-editorial` |
| Q21 | Tables have captions | Important | `cqa-tables-images` |
| Q22 | Images have alt text | Important | `cqa-tables-images` |
| Q23 | Conscious language guidelines | Required | `cqa-legal-branding` |
| Q24 | Links to relevant content journey | Important | `cqa-links` |
| Q25 | Interlinked within 3 clicks | Important | `cqa-links` |

### Onboarding (10 parameters)

| # | Parameter | Level | Skill |
|---|-----------|-------|-------|
| O1 | RH brand and style guidelines | Required | `cqa-legal-branding` |
| O2 | Copyright and legal notices | Required | `cqa-legal-branding` |
| O3 | Official product names | Required | `cqa-legal-branding` |
| O4 | Conscious language | Required | `cqa-legal-branding` |
| O5 | Tech Preview disclaimers | Required | `cqa-legal-branding` |
| O6 | Supported content with disclaimers | Required | `cqa-onboarding` |
| O7 | Procedures tested by SME/QE | Required | `cqa-onboarding` |
| O8 | Source files in RH format | Required | `cqa-onboarding` |
| O9 | Content published through Pantheon | Required | `cqa-onboarding` |
| O10 | Content published to official RH site | Required | `cqa-onboarding` |
