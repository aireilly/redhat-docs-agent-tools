---
name: cqa-onboarding
description: Use when assessing CQA parameters O6-O10 (onboarding to docs.redhat.com). Checks support disclaimers, SME verification, source format, Pantheon publishing, and official site publication.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# CQA O6-O10: Onboarding

## Parameters

| # | Parameter | Level |
|---|-----------|-------|
| O6 | Content supported or clear disclaimers about support level | Required |
| O7 | Procedures tested and verified by SME or QE | Required |
| O8 | Source files in RH prescribed format (AsciiDoc) | Required |
| O9 | Content published through Pantheon | Required |
| O10 | Content published to official Red Hat site | Required |

## Directory note

Some repos use `modules/` instead of `topics/` for content files. All `topics/` references in this skill apply equally to `modules/`. The automation scripts accept `--scan-dirs` to override the default scan directories.

## Cross-references

- **O6 (support disclaimers)** overlaps with P19/O5 in `cqa-tools:cqa-legal-branding`. Use the cqa-legal-branding TP/DP disclaimer results as evidence for O6 compliance. O6 adds the community-supported component and unsupported configuration checks.
- **O7 (SME/QE verification)** can use Q15 evidence from `cqa-tools:cqa-procedures` — a high percentage of procedures with `.Verification` sections is supporting evidence of testability.

## Step 1: Identify the docs repo

Ask the user for the path to their Red Hat modular documentation repository. Store as `DOCS_REPO`.

## Step 2: O6 — Support disclaimers

### Rule

All content must be clearly identified as supported, Technology Preview, or Developer Preview. Community-supported components and unsupported configurations must have explicit disclaimers.

### Check procedure

1. **Technology Preview features**: Verify all TP features have the standard `[IMPORTANT]` disclaimer via `snip_technology-preview.adoc`. Cross-reference with the P19/O5 check in `cqa-tools:cqa-legal-branding`.

2. **Developer Preview features**: Verify all DP features have the standard DP disclaimer. DP features receive zero Red Hat support.

3. **Community-supported components**: Identify any components that are community-supported rather than Red Hat-supported (e.g., upstream Eclipse Che components, community plugins). These must have disclaimers.

4. **Unsupported configurations**: Check for documented configurations that are explicitly NOT supported (e.g., non-OpenShift Kubernetes distributions, specific cloud provider limitations). These must have `[WARNING]` or `[IMPORTANT]` blocks stating the support boundary.

5. **Support scope consistency**: Verify that support level claims are consistent across the guide. A feature cannot be "fully supported" in one topic and "Technology Preview" in another.

### What to search for

```bash
# Find all support-related disclaimers
grep -rn -i 'technology preview\|tech preview\|developer preview\|not supported\|unsupported\|community' topics/ modules/ assemblies/ --include='*.adoc'

# Find TP/DP snippet includes
grep -rn 'snip_technology-preview\|snip_developer-preview' topics/ modules/ assemblies/ --include='*.adoc'
```

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All TP/DP features have proper disclaimers. Community components identified. Unsupported configurations disclaimed. Support levels consistent across guides. |
| **3** | Most disclaimers in place. 1-2 features missing TP/DP disclaimer. Minor consistency issues. |
| **2** | Multiple features lack required disclaimers. Community components not identified. Inconsistent support claims. |
| **1** | No support-level identification. Missing disclaimers on TP/DP features. |

## Step 3: O7 — SME/QE verification

### Rule

All procedures must be tested and verified by a Subject Matter Expert (SME) or Quality Engineering (QE) team member before publication. This ensures technical accuracy and that documented steps produce the expected results.

### Check procedure

This parameter requires human confirmation and cannot be fully assessed through static analysis. Evaluate the following evidence:

1. **Merge request review process**: Check the repository's merge request (MR) workflow:
   - Do MRs require SME approval?
   - Is there a QE review step?
   - Check `.gitlab-ci.yml` for automated validation (Vale, reference checks)

2. **SME contribution history**: Check git log for commits from engineering team members:
   ```bash
   git log --format="%an" --since="1 year ago" | sort | uniq -c | sort -rn
   ```

3. **CI/CD pipeline validation**: Verify the pipeline runs automated checks that catch technical issues:
   - Vale DITA linting
   - Cross-reference validation (the docs repo's own `scripts/validate-refs.py`)
   - Build validation (ccutil compile)

4. **SME merge requests**: Check for recent MRs from SMEs that update technical content:
   ```bash
   git log --oneline --since="6 months ago" --grep="SME\|fix\|update\|correct"
   ```

5. **Verification sections**: Procedures with `.Verification` sections provide a built-in testing path. A high percentage of procedures with verification sections is evidence of testability.

### Evidence types

| Evidence | Strength |
|----------|----------|
| SME-authored MRs with technical content updates | Strong — direct SME involvement |
| QE team sign-off on MRs (GitLab approvals) | Strong — formal verification |
| CI pipeline with automated validation | Medium — catches structural issues but not technical accuracy |
| `.Verification` sections in procedures | Medium — enables testing but does not confirm it was done |
| Git history showing engineering contributors | Weak — presence does not guarantee testing |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | MR workflow requires SME/QE approval. Recent SME MRs demonstrate active involvement. CI pipeline validates content. Verification sections in critical procedures. |
| **3** | SME involvement confirmed for most content. CI pipeline in place. Some procedures lack formal verification. |
| **2** | Limited SME involvement. No formal review process. CI pipeline missing or incomplete. |
| **1** | No evidence of SME/QE testing. No review process. No CI validation. |

## Step 4: O8 — Source files in Red Hat prescribed format

### Rule

All source content files must be in AsciiDoc (`.adoc`) format following the Red Hat modular documentation framework. The repository structure must conform to Red Hat documentation standards.

### Check procedure

1. **File format verification**:
   ```bash
   # Count all content files by extension
   find "$DOCS_REPO/topics" "$DOCS_REPO/modules" "$DOCS_REPO/assemblies" "$DOCS_REPO/snippets" -type f 2>/dev/null | sed 's/.*\.//' | sort | uniq -c | sort -rn
   ```
   All content files must be `.adoc`. No `.md` (Markdown), `.xml` (DocBook), `.dita`, or `.html` source files.

2. **Encoding verification**:
   ```bash
   # Check for non-UTF-8 files in all content directories
   file "$DOCS_REPO/topics/"**/*.adoc "$DOCS_REPO/modules/"**/*.adoc "$DOCS_REPO/assemblies/"**/*.adoc "$DOCS_REPO/snippets/"**/*.adoc 2>/dev/null | grep -v "UTF-8\|ASCII"
   ```
   All files must be UTF-8 encoded.

3. **Line endings**:
   ```bash
   # Check for Windows line endings (CRLF)
   grep -rPl '\r\n' "$DOCS_REPO/topics/" "$DOCS_REPO/modules/" "$DOCS_REPO/assemblies/" "$DOCS_REPO/snippets/" --include='*.adoc' 2>/dev/null | head -5
   ```
   All files must use LF (Unix) line endings, not CRLF (Windows).

4. **Directory structure**: Verify the repo follows Red Hat modular docs layout:
   - `titles/` — publishable guide entry points with `master.adoc`
   - `assemblies/` — assembly files (collections of topics)
   - `topics/` (or `modules/`) — individual content modules
   - `snippets/` — reusable inline fragments
   - `common/` — shared attributes and metadata
   - `images/` — image assets

5. **`.editorconfig` presence**: Check for `.editorconfig` enforcing UTF-8, LF, consistent indentation:
   ```bash
   cat "$DOCS_REPO/.editorconfig"
   ```

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All content files are `.adoc`. UTF-8 encoding. LF line endings. Standard Red Hat modular docs directory structure. `.editorconfig` present. |
| **3** | All files are `.adoc` with correct encoding. Minor structure deviations (e.g., missing `.editorconfig`). |
| **2** | Mixed file formats. Some non-UTF-8 files. Non-standard directory structure. |
| **1** | Content not in AsciiDoc or no standard structure. |

## Step 5: O9 — Content published through Pantheon

### Rule

Content must be publishable through Pantheon, Red Hat's documentation publishing platform. This requires ccutil compatibility and proper build configuration.

### Check procedure

1. **Pantheon directory structure**: Verify the `pantheon/` directory exists with symlinks to `titles/`:
   ```bash
   ls -la "$DOCS_REPO/pantheon/"
   ```
   Each subdirectory should symlink to a `titles/*/` directory.

2. **ccutil build configuration**: Verify `tools/ccutil.sh` exists and is functional:
   ```bash
   cat "$DOCS_REPO/tools/ccutil.sh"
   ```

3. **ccutil compile test**: Run a test build (requires podman or the ccutil container):
   ```bash
   cd "$DOCS_REPO"
   bash tools/ccutil.sh
   ```
   The build must complete without errors. Warnings should be reviewed.

4. **docinfo.xml**: Verify `docinfo.xml` exists in each `titles/*/` directory:
   ```bash
   ls "$DOCS_REPO/titles/"*/docinfo.xml
   ```

5. **master.adoc entry points**: Verify each guide has a `master.adoc` entry point:
   ```bash
   ls "$DOCS_REPO/titles/"*/master.adoc
   ```

6. **CI pipeline ccutil job**: Verify the CI pipeline includes a ccutil build job:
   ```bash
   grep -A 10 'ccutil' "$DOCS_REPO/.gitlab-ci.yml"
   ```

### Build output formats

ccutil should produce these formats:
- `html-single` — single-page HTML (primary format for Pantheon)
- `html` — multi-page HTML
- `pdf` — PDF output
- `epub` — EPUB output

### Common ccutil build issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Duplicate ID errors | Same `[id="..."]` in files included by multiple assemblies | Remove duplicate includes or use unique IDs |
| Unresolved attributes | Attribute not defined in `common/attributes.adoc` | Add attribute definition |
| Missing include files | `include::` path does not resolve via symlinks | Fix symlink or include path |
| Bare language source blocks | `[bash,...]` instead of `[source,bash]` | Add `source,` prefix |
| Nested `====` delimiters | Example block inside admonition block | Restructure to avoid nesting |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | `pantheon/` directory configured. ccutil build completes with 0 errors. CI pipeline includes ccutil job. All output formats generated. |
| **3** | ccutil builds with minor warnings. CI pipeline present. 1-2 output format issues. |
| **2** | ccutil build fails. Missing `pantheon/` configuration. No CI pipeline. |
| **1** | No Pantheon publishing infrastructure or not assessed. |

## Step 6: O10 — Content published to official Red Hat site

### Rule

Content must be published to the official Red Hat documentation site (`docs.redhat.com`) and accessible to customers.

### Check procedure

1. **Stage branch existence**: Verify stage branches exist for the current and previous releases:
   ```bash
   git -C "$DOCS_REPO" branch -r | grep 'stage'
   ```

2. **Stage branch pipeline**: Verify the stage branch triggers the Pantheon publishing pipeline. The pipeline should have:
   - `single_source` — assembles content from Antora sources
   - `ccutil` — validates and compiles the assembled content
   - `git_push` — pushes generated Pantheon files back to the branch

3. **Published URL verification**: If you have access, verify the content is accessible at the published URL. The URL pattern is typically:
   - `https://docs.redhat.com/en/documentation/__<product_slug>__/__<version>__/html-single/__<guide_name>__/`
   - Replace the placeholders with the product's actual values from its `common/attributes.adoc`.

4. **Version coverage**: Verify that published documentation covers the current supported versions.

5. **Content freshness**: Check that the most recent stage branch reflects the latest content updates:
   ```bash
   git -C "$DOCS_REPO" log --oneline -5 origin/<product>-<X.Y>-stage
   ```

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | Content published to docs.redhat.com. Stage branches exist and pipeline works. Current and previous versions covered. Content is fresh. |
| **3** | Published to docs.redhat.com. Stage branches exist. Minor delays in content freshness. |
| **2** | Published but with significant gaps. Stage pipeline has issues. Not all versions covered. |
| **1** | Content not published to docs.redhat.com or publishing infrastructure not in place. |

## Step 7: Verify

After assessing all parameters, compile the evidence:

```bash
# Summary checks
ls "$DOCS_REPO/pantheon/"
ls "$DOCS_REPO/titles/"*/master.adoc
ls "$DOCS_REPO/titles/"*/docinfo.xml
ls "$DOCS_REPO/.editorconfig"
git -C "$DOCS_REPO" branch -r | grep 'stage'
```
