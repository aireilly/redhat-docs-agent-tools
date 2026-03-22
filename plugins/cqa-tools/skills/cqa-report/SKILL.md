---
name: cqa-report
description: Use when all CQA parameters have been assessed and you need to generate the final CQA 2.1 assessment report with scores, evidence, and summary tables.
allowed-tools: Read, Glob, Grep, Write
---

# CQA Report Generation

## Overview

Generate the final CQA 2.1 Content Quality Assessment report after all parameters have been assessed and scored.

## Report Structure

### Header

```markdown
# CQA 2.1 Content Quality Assessment Report -- [Product Name]

**Content location**: `<repo-path>/` (assemblies/, topics/, snippets/)
**Date of review**: YYYY-MM-DD
**Files analyzed**: N (X assemblies + Y topics) + Z snippets
**Tools used**: Vale asciidoctor-dita-vale, docs repo's validate-refs.py, cqa-audit.py
```

### Per-tab tables

For each tab (Pre-migration, Quality, Onboarding), create a table:

```markdown
| # | Requirement | Level | Score | Evidence |
|---|-------------|-------|-------|----------|
| 1 | Parameter description | Required/Important | **4/3/2/1** | Specific evidence |
```

### Tab summaries

```markdown
| Category | Items | Avg Score |
|----------|-------|-----------|
| Required | N | X.X |
| Important | N | X.X |
| **Overall** | **N** | **X.X** |
```

### Overall summary

```markdown
| Tab | Items Scored | Average Score | Rating |
|-----|-------------|---------------|--------|
| Pre-migration | 19 | X.X | Rating |
| Quality | 25 | X.X | Rating |
| Onboarding | 10 | X.X | Rating |
| **Overall** | **54** | **X.X** | **Rating** |
```

### Rating thresholds

Individual parameters are scored as integers (4, 3, 2, or 1). The **average score** across all parameters in a tab determines the tab's overall rating:

- 3.5+ = "Meets criteria"
- 3.0-3.4 = "Mostly meets"
- 2.5-2.9 = "Mostly does not meet"
- Below 2.5 = "Does not meet"

The overall assessment rating uses the same thresholds applied to the average across all 54 parameters.

### Issues list

Prioritized list of remaining issues:
1. High Priority (blockers)
2. Medium Priority (quality improvements)
3. Low Priority (cleanup)

### Files changed

Consolidated list of all files modified during the assessment.

## Output

Write the report to `CQA-2.1-Assessment-Report.md` in the workspace root.
