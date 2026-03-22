---
name: cqa-legal-branding
description: Use when assessing CQA parameters P18-P19, Q17, Q23, O1-O5 (legal, branding, and compliance). Checks product names, Tech Preview disclaimers, conscious language, non-RH link disclaimers, and copyright.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# CQA P18-P19, Q17, Q23, O1-O5: Legal and Branding

## Parameters

| # | Parameter | Level |
|---|-----------|-------|
| P18 | Official product names used (attributes, not hardcoded) | Required |
| P19 | Tech Preview/Developer Preview disclaimers present | Required |
| Q17 | Non-RH links acknowledged or disclaimed | Important |
| Q23 | Conscious language guidelines followed | Required |
| O1 | Content follows RH brand and style guidelines | Required |
| O2 | Copyright and legal notices present | Required |
| O3 | Official product names used | Required |
| O4 | Conscious language guidelines followed | Required |
| O5 | Tech Preview disclaimers present | Required |

## Automation scripts

This skill has automation scripts:

| Script | Parameters | What it checks |
|--------|-----------|----------------|
| `check-product-names.py` | P18, O1, O3 | Hardcoded product names in prose and image alt text |
| `check-tp-disclaimers.py` | P19, O5 | TP/DP mentions, snippet existence, disclaimer compliance |
| `check-external-links.py` | Q17 | External link categorization by domain |
| `check-conscious-language.py` | Q23, O4 | Exclusionary terms with exception handling |
| `check-legal-notices.py` | O2 | LICENSE file and docinfo.xml existence |

All scripts: Python 3.9+ stdlib only, no dependencies. Exit code 0 = pass, 1 = issues found.

## Step 1: Identify the docs repo

Ask the user for the path to their Red Hat modular documentation repository. Store as `DOCS_REPO`.

## Step 2: P18/O1/O3 — Official product names used

### Rule

All product and platform names must use AsciiDoc attributes instead of hardcoded strings. This ensures consistency and makes version/branding updates a single-line change in `common/attributes.adoc`.

### Automation

```bash
python3 ../cqa-assess/scripts/check-product-names.py "$DOCS_REPO"
```

Automatically skips code blocks, comments, attribute definitions, and known exceptions (UI labels, plugin names, link text). Reports violations with file:line and replacement suggestions.

### Check procedure

Search active content (exclude `legacy-content-do-not-use/`, `common/attributes.adoc` definition lines, code blocks, and YAML) for hardcoded names:

| Hardcoded string | Replace with | Search command |
|-----------------|-------------|----------------|
| `Red Hat OpenShift Dev Spaces` | `{prod}` | `grep -r "Red Hat OpenShift Dev Spaces" assemblies/ topics/ snippets/` |
| `OpenShift Dev Spaces` (in prose, not UI labels) | `{prod-short}` | `grep -r "OpenShift Dev Spaces" assemblies/ topics/ snippets/` |
| `Dev Spaces` (in prose, not UI labels) | `{prod-short}` or `{prod2}` | `grep -r "Dev Spaces" assemblies/ topics/ snippets/` |
| `OpenShift Container Platform` | `{ocp}` | `grep -r "OpenShift Container Platform" assemblies/ topics/ snippets/` |
| `Openshift` (lowercase S) | `OpenShift` | `grep -r "Openshift" assemblies/ topics/ snippets/` |

### Exceptions — do NOT replace

These are legitimate hardcoded uses:

| Context | Example | Why |
|---------|---------|-----|
| **UI button/menu labels** | `Connect to Dev Spaces` | Literal UI text the user must click |
| **Plugin/extension names** | `Gateway provider for OpenShift Dev Spaces` | Official third-party plugin name |
| **Link text for external URLs** | `link:https://plugins.jetbrains.com/...[OpenShift Dev Spaces plugin]` | Display text matching the linked resource |
| **Attribute definitions** | `:prod-short: OpenShift Dev Spaces` in `common/attributes.adoc` | Where attributes are defined |
| **Code blocks and YAML** | `image: devspaces/server` | Technical identifiers, not prose |

### Additional checks

1. **Image alt text** — search `image::` lines for hardcoded product names. Alt text should use attributes like prose does.
2. **Standalone "OpenShift"** — many uses are legitimate (e.g., "OpenShift web console", "OpenShift Route", version numbers like "OpenShift 4.15"). Only flag standalone "OpenShift" used as a generic platform reference that should be `{orch-name}`.

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | 0 hardcoded product names in prose or alt text; all legitimate exceptions documented |
| **3** | 1-3 hardcoded instances in non-critical locations (alt text, edge cases) |
| **2** | Multiple hardcoded product names in body prose |
| **1** | Widespread hardcoding with no attribute usage |

## Step 3: P19/O5 — Tech Preview and Developer Preview disclaimers

### Rule

Any feature declared as Technology Preview or Developer Preview must include a formal `[IMPORTANT]` admonition block with the standard Red Hat disclaimer text. The two programs have different support scopes and require different disclaimers.

### Support scope distinction

| Program | Support level | Key differences |
|---------|--------------|-----------------|
| **Technology Preview** | Limited — Severity 3-4 cases only | Not for production; not functionally complete; may change or be removed; no migration path guaranteed |
| **Developer Preview** | None — zero Red Hat support | Not for production; completely unsupported; subject to change or removal at any time; optional participation |

### Automation

```bash
python3 ../cqa-assess/scripts/check-tp-disclaimers.py "$DOCS_REPO"
```

Finds all TP/DP mentions, classifies them (prose, table, link text, comment, code block), verifies snippet files exist with correct content, and checks that files mentioning TP/DP in prose include the appropriate disclaimer.

### Check procedure

1. **Search for mentions** of "Technology Preview", "Tech Preview", "Developer Preview", "Dev Preview" in all active `.adoc` files (exclude `legacy-content-do-not-use/`)
2. **Verify disclaimer snippets exist** — the repo should have reusable snippet files:
   - `snip_technology-preview.adoc` — for TP features
   - `snip_developer-preview.adoc` — for DP features (create if missing and DP features exist)
3. **Verify disclaimer content** matches official Red Hat wording:
   - TP: "Technology Preview feature only. Not supported with Red Hat production SLAs..."
   - DP: "Developer Preview feature. Not supported in any way by Red Hat..."
4. **Verify link to support scope page**:
   - TP: `https://access.redhat.com/support/offerings/techpreview/`
   - DP: `https://access.redhat.com/support/offerings/devpreview/`
5. **Verify snippet usage** — every topic that declares a feature as TP or DP must include the appropriate snippet with `:FeatureName:` set
6. **Table labels** — maturity tables (e.g., supported languages) may use "Technology Preview" as a cell value without the full disclaimer, provided the full disclaimer appears where the feature is documented in detail

### Standard Technology Preview disclaimer text

```asciidoc
:FeatureName: The XYZ feature
include::snippets/snip_technology-preview.adoc[]
```

The snippet renders an `[IMPORTANT]` block:

> {FeatureName} is a Technology Preview feature only.
> Technology Preview features are not supported with Red Hat production service level agreements (SLAs) and might not be functionally complete.
> Red Hat does not recommend using them in production.
> These features provide early access to upcoming product features, enabling customers to test functionality and provide feedback during the development process.
>
> For more information about the support scope of Red Hat Technology Preview features, see https://access.redhat.com/support/offerings/techpreview/.

### Standard Developer Preview disclaimer text

If DP features are documented, create `snip_developer-preview.adoc` with:

```asciidoc
[IMPORTANT]
====
[subs="attributes+"]
{FeatureName} is available as a Developer Preview feature only.
Developer Preview features are not supported by Red Hat in any way and are not functionally complete or production-ready.
Do not use Developer Preview features for production or business-critical workloads.
Red Hat does not guarantee the stability of Developer Preview features, and they may be changed or removed at any time.

For more information about the support scope of Red Hat Developer Preview features, see https://access.redhat.com/support/offerings/devpreview/.
====
```

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All TP/DP features have proper disclaimers with correct wording and support scope links; reusable snippets exist |
| **3** | 1-2 features missing disclaimers or minor wording differences |
| **2** | Multiple features without disclaimers or wrong support scope referenced |
| **1** | No disclaimers or TP/DP features not identified |

## Step 4: Q17 — Non-RH link disclaimers

### Rule

External links to non-Red Hat sites should have appropriate disclaimers indicating Red Hat does not control the content.

### Automation

```bash
python3 ../cqa-assess/scripts/check-external-links.py "$DOCS_REPO"
# Add --details for per-URL breakdown by domain
```

Extracts all external URLs, categorizes domains (Red Hat, Upstream/Community, Authoritative, Third-party), filters placeholder/example URLs, and reports third-party links that may need disclaimers.

### Check procedure

1. Count all external `link:https://` URLs in active content
2. Categorize by domain (Red Hat, GitHub upstream, community, third-party)
3. Check for guide-level or per-link disclaimers

### Options for compliance

| Approach | Description |
|----------|-------------|
| **Guide-level disclaimer** | Single disclaimer in the guide front matter covering all external links |
| **Per-link disclaimer** | Disclaimer text adjacent to each external link |
| **Domain categorization** | Classify links as official upstream (supported), community (best-effort), or third-party |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All non-RH links have individual disclaimers |
| **3** | Guide-level disclaimer covers external links; authoritative domains documented |
| **2** | Some external links disclaimed, others not |
| **1** | No disclaimers on external links |

## Step 5: Q23/O4 — Conscious language

### Rule

Content must follow Red Hat's conscious language guidelines. Avoid terms with exclusionary or harmful connotations.

### Automation

```bash
python3 ../cqa-assess/scripts/check-conscious-language.py "$DOCS_REPO"
```

Searches for exclusionary terms using whole-word matching. Automatically excludes code blocks, URLs (GitHub `/blob/master/`), filenames, comments, and attribute definitions. Groups results by violation vs exception.

### Check procedure

**Tier 1 — "Do not use" (script-checked):**

| Term | Replacement | Exception |
|------|-------------|-----------|
| `master` (paired with slave) | `primary`, `main`, `source`, `control plane` | Upstream GitHub URLs where repo uses `master` as default branch with no `main` alternative. Acceptable for mastery of a skill. |
| `slave` | `secondary`, `replica`, `worker`, `standby` | None |
| `whitelist` | `allowlist` | None |
| `blacklist` | `blocklist`, `denylist` | None |
| `dummy` | `placeholder`, `example`, `sample` | None |
| `sanity check` / `sanity test` | `test`, `verify`, `confidence check` | None |
| `segregate` / `segregation` | `separate`, `segment` | None |
| `evangelist` / `evangelize` | `advocate`, `ambassador` | None |

**Tier 2 — "Do not use" (manual check):**

| Term | Replacement | Exception |
|------|-------------|-----------|
| `man hour` / `man day` | `person hour`, `labor hour` | None |
| `cripple` / `crippled` | `impacted`, `degraded`, `restricted` | None |
| `black hat` / `white hat` (hacker) | `attacker` / `ethical hacker` | None |
| `Chinese wall` | `ethical wall`, `firewall` | None |
| `fubar` | Do not publish | None |
| `squad` | `team`, `group` | None |

**Tier 3 — "Use with caution" (manual check):**

| Term | Guidance | Exception |
|------|----------|-----------|
| `abort` | Replace with `cancel`, `stop`, `end`, `fail` | OK if part of existing product/command terminology |
| `disabled` | Do not use to refer to a person | OK for interface elements ("the button is disabled") |
| `agnostic` | Replace with `independent`, `irrespective` | Standard in technical documentation for platform/vendor independence |
| `kill` | Rephrase when not referring to Unix command | OK for `podman kill`, `kill` process command |
| `master` (standalone) | Replace when possible with `main`, `primary` | OK for mastery of skill; OK in upstream URLs with no `main` alternative |
| `tribe` / `tribal` | Do not use metaphorically | OK when referring to actual Indigenous groups |
| `he or she` / `he/she` | Use `they` | None |

**Tier 4 — Avoid (manual check for broader terms):**

| Term | Guidance |
|------|----------|
| `crazy` / `insane` / `insanely` | Avoid neurodiversity bias; use precise alternatives |
| `guru` / `ninja` / `rockstar` | Avoid superlatives in job titles |
| `guys` | Use `team`, `folks`, `everyone` |
| `weaponize` / `boots on the ground` | Avoid militaristic language |
| `straw man` | Use `framework`, `rough draft` |
| `man-in-the-middle` | Use `adversary-in-the-middle` when possible |
| `handicap` | Use `limit`, `restrict` |

**Reference:** Full term list in `Red Hat Conscious Language Terms - Not for distribution outside Red Hat - Sheet1.csv` at workspace root. Sources: IBM Style, Red Hat corporate style guide, Red Hat Supplementary Style Guide, Inclusive Naming Initiative.

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | 0 violations across all tiers; all exceptions documented with justification; automated script passes |
| **3** | 0 Tier 1 violations; 1-3 Tier 2-4 violations or undocumented exceptions |
| **2** | Multiple violations across tiers |
| **1** | Widespread use of exclusionary terms |

## Step 6: O2 — Copyright and legal notices

### Rule

The repository must include appropriate copyright and licensing information.

> **Publishing pipeline note:** Some publishing pipelines (e.g., docs.redhat.com) inject legal notices at the platform level. If the repo relies on platform-injected legal notices instead of including them in source files, document this and adjust scoring accordingly. The script checks source-level compliance; platform behavior may satisfy the requirement even if the script reports issues.

### Automation

```bash
python3 ../cqa-assess/scripts/check-legal-notices.py "$DOCS_REPO"
# Use --repo-root if the docs directory is a subdirectory of the repo:
python3 ../cqa-assess/scripts/check-legal-notices.py "$DOCS_REPO/book-dir" --repo-root "$DOCS_REPO"
```

Checks LICENSE/LICENCE file existence (auto-detects repo root by walking up to `.git`), docinfo.xml presence in each `titles/*/` directory, and copyright year detection.

### Check procedure

1. Verify `LICENCE` or `LICENSE` file exists at repo root
2. Verify `docinfo.xml` exists in each `titles/*/` directory with document metadata
3. Check that copyright year is current or covers the publication period

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | License file present; docinfo.xml in all title directories; copyright current. (If publishing pipeline injects legal notices, note this as evidence.) |
| **3** | License and docinfo present but copyright year outdated |
| **2** | Missing docinfo in some title directories |
| **1** | No license file or copyright notices |

## Step 7: Verify

After fixing any violations, verify:

```bash
cd "$DOCS_REPO"
vale assemblies/ topics/ titles/administration_guide/master.adoc titles/user_guide/master.adoc
# validate-refs.py is the docs repo's own script, not a plugin script
python3 scripts/validate-refs.py

# Run all legal/branding automation scripts
python3 ../cqa-assess/scripts/check-product-names.py .
python3 ../cqa-assess/scripts/check-conscious-language.py .
python3 ../cqa-assess/scripts/check-tp-disclaimers.py .
python3 ../cqa-assess/scripts/check-external-links.py .
python3 ../cqa-assess/scripts/check-legal-notices.py .
```
