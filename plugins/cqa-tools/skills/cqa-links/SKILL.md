---
name: cqa-links
description: Use when assessing CQA parameters P15-P17, Q24-Q25 (links and URLs). Checks for broken xrefs, missing includes, missing images, redirect integrity, and content interlinking.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# CQA P15-P17, Q24-Q25: Links and URLs

## Parameters

| # | Parameter | Level |
|---|-----------|-------|
| P15 | No broken links (xrefs, includes, images) | Required |
| P16 | Redirects work correctly | Required |
| P17 | Content interlinked within 3 clicks of domain home | Important |
| Q24 | Content includes links to relevant content journey | Important |
| Q25 | Pages interlinked within 3 clicks | Important |

## Directory note

Some repos use `modules/` instead of `topics/` for content files. All `topics/` references in this skill apply equally to `modules/`. The automation scripts accept `--scan-dirs` to override the default scan directories.

## Step 1: Identify the docs repo

Ask the user for the path to their Red Hat modular documentation repository. Store as `DOCS_REPO`.

## Step 2: P15 — No broken links

### Rule

Every cross-reference, include directive, and image reference must resolve to an existing target. No duplicate IDs are allowed.

### Check procedure

Run the docs repo's own reference validation script (this is not a plugin script — it lives in the docs repo at `$DOCS_REPO/scripts/validate-refs.py`):
```bash
cd "$DOCS_REPO"
python3 scripts/validate-refs.py
```

This checks 4 things:
1. **Broken xrefs** — every `xref:ID_{context}[]` must have a matching `[id="ID_{context}"]` declared in any `.adoc` file
2. **Missing includes** — every `include::path[]` must resolve to an existing file on disk (paths resolve relative to the file via symlinks in `titles/*/`)
3. **Missing images** — every `image::path[]` must resolve to a file under `images/` (`:imagesdir:` is set in `common/attributes.adoc`)
4. **Duplicate IDs** — no two files should declare the same `[id="..."]` anchor

### Common causes of broken references

| Cause | Example | Fix |
|-------|---------|-----|
| File renamed without updating xrefs | `xref:old-name_{context}[]` → file now has `[id="new-name_{context}"]` | Update xref to match actual ID |
| File deleted without removing xrefs/includes | `xref:deleted-topic_{context}[]` | Remove the xref or redirect to replacement content |
| ID in file doesn't match filename prefix | File `proc_foo.adoc` has `[id="foo_{context}"]` (no `proc_` prefix) | Xref must match declared ID, not filename |
| Typo in image path | `image::architectre/diagram.png[]` | Fix spelling to match actual path |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | 0 broken xrefs, 0 missing includes, 0 missing images, 0 duplicate IDs |
| **3** | 1-3 broken references (minor oversights) |
| **2** | Multiple broken references across different files |
| **1** | Widespread broken references or not checked |

## Step 3: P16 — Redirects work correctly

### Rule

When content is renamed, moved, or restructured, old URLs must continue to resolve. The redirect mechanism depends on the publishing platform.

### Check procedure

1. **Identify the publishing platform** — Pantheon (ccutil), GitLab Pages, or other
2. **Check for redirect configuration** — search for `_redirects`, redirect maps, or platform-specific redirect config
3. **Identify recently changed IDs** — compare current `[id="..."]` anchors against any published version to find renamed/deleted pages

### Platform-specific notes

| Platform | Redirect mechanism | Repo responsibility |
|----------|-------------------|---------------------|
| **Pantheon** (ccutil) | Managed at CCS publishing infrastructure level | Repo maintains correct IDs; redirect requests filed with CCS publishing team during stage branch process |
| **GitLab Pages** | `_redirects` file in repo root | Repo must maintain redirect file |
| **Antora** | `page-aliases` attribute in page headers | Repo must set aliases |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | Redirects managed at platform level OR redirect configuration in place and verified; no Antora module prefixes in links; cross-guide links use `link:` not `xref:` |
| **3** | Minor redirect gaps (1-2 recently renamed pages without redirects) |
| **2** | Multiple broken URLs from recent restructuring with no redirect plan |
| **1** | No redirect strategy or widespread broken published URLs |

## Step 4: P17/Q24/Q25 — Content interlinking

### Rule

Content should be interlinked so that users can navigate between related topics. Every topic should be reachable within 3 clicks from the guide's domain home page. The content journey must guide users through related content — concepts link to procedures, procedures link to related concepts and other procedures, and cross-guide links connect admin and user workflows.

### Check procedure

#### 4a. Assembly navigation and topic grouping

1. **Read both master files** (`titles/administration_guide/master.adoc`, `titles/user_guide/master.adoc`) to understand the full guide structure
2. **Verify logical topic ordering** within each assembly — information flow should follow dependency order (concept → procedure → reference)
3. **Check standalone topics** included directly from master — verify they are strategically positioned (e.g., foundational concepts early, decommissioning late) and not orphaned
4. **Verify click depth** — all topics must be reachable in ≤2 clicks from master (master → assembly → topic), with cross-references providing additional 3rd-click navigation

#### 4b. Concept-procedure bidirectional linking

1. **Concept files with Additional resources**: Check whether concept files link to related procedures via xref
2. **Procedure files with Additional resources**: Check whether procedures link back to related concepts
3. **Flag concept files without Additional resources**: Concepts without any navigation exits reduce content journey discoverability
4. **Check for isolated topics**: Topics not referenced by any xref and without their own Additional resources are dead ends in the content journey

#### 4c. Cross-guide links

1. **Admin → User Guide links**: Search for `{prod-ug-url}` in admin guide topics and assemblies
2. **User → Admin Guide links**: Search for `{prod-ag-url}` in user guide topics and assemblies
3. **Link format verification**:
   - Cross-guide links must use `link:` not `xref:` (guides are built separately)
   - All `link:` macros must have descriptive link text (not empty `[]`)
   - No legacy Antora module prefixes (`administration-guide:`, `user-guide:`)
4. **Target ID verification**: Cross-guide link target IDs must match actual `[id="..."]` declared in the target guide's files. Legacy anchor names from the pre-modularization era may not resolve in the current format.
5. **Anchor context resolution** (**critical**): Cross-guide `link:` macros must NOT use `_{context}` in the anchor fragment. The `{context}` attribute resolves to the **source** guide's context value, not the target guide's. For example, `link:{prod-ag-url}some-id_{context}[...]` in a user guide file resolves `{context}` to `user_guide`, producing the anchor `some-id_user_guide` — but the actual anchor in the admin guide HTML is `some-id_administration_guide`. The anchor must hardcode the target guide's context string directly.
6. **Missing cross-guide opportunities**: Check if topics in one guide clearly relate to topics in the other guide but lack cross-references (e.g., admin OAuth setup ↔ user credential usage, admin storage config ↔ user storage concepts)

#### Anchor context verification procedure

Cross-guide anchors are **not validated** by `validate-refs.py` (which only checks within-guide `xref:` targets). These must be checked manually:

1. **Find `{context}` in cross-guide anchors** — these are always wrong:
   ```bash
   # Links to admin guide with {context} in anchor (in user guide files)
   grep -rn 'link:{prod-ag-url}.*_{context}' topics/user_guide/ assemblies/user_guide/ --include='*.adoc'

   # Links to user guide with {context} in anchor (in admin guide files)
   grep -rn 'link:{prod-ug-url}.*_{context}' topics/administration_guide/ assemblies/administration_guide/ --include='*.adoc'
   ```
   Any matches are broken. Replace `_{context}` with the target guide's hardcoded context string (`_administration_guide` or `_user_guide`).

2. **Verify all cross-guide anchors match declared IDs** — for each `link:{prod-ag-url}ANCHOR[...]` or `link:{prod-ug-url}ANCHOR[...]`:
   - Extract the anchor fragment (everything between the URL attribute and `[`)
   - Search for a matching `[id="ANCHOR"]` in the target guide's files (with `_{context}` appended to the declared ID pattern)
   - The anchor in the link must equal the ID base + `_` + target guide's context value

3. **Context values** — determined by the `:context:` attribute set in each guide's `master.adoc`:
   - Admin guide: `:context: administration_guide` → anchors end with `_administration_guide`
   - User guide: `:context: user_guide` → anchors end with `_user_guide`

#### Common cross-guide link issues

| Issue | Example | Fix |
|-------|---------|-----|
| `{context}` in cross-guide anchor | `link:{prod-ag-url}some-id_{context}[...]` in user guide | Replace `_{context}` with `_administration_guide` (admin targets) or `_user_guide` (user targets) |
| Empty link text on `link:` macro | `link:{prod-ag-url}target-id[]` | Add descriptive text: `link:{prod-ag-url}target-id[Configuring feature]` |
| Legacy target ID | `link:{prod-ug-url}old-section-name[...]` | Update to match current `[id="..."]` in target file |
| Non-existent target | `link:{prod-ug-url}removed-content[...]` | Remove link or redirect to replacement content |
| Antora module prefix | `link:{prod-ag-url}administration-guide:section[...]` | Remove `administration-guide:` prefix |
| `xref:` across guides | `xref:admin-topic_{context}[]` in user guide | Change to `link:{prod-ag-url}admin-topic_{context}[...]` |

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All topics reachable within 3 clicks; concepts link to procedures and vice versa; cross-guide links where relevant; all cross-guide links have descriptive text and valid targets |
| **3** | Most topics interlinked; a few isolated topics without cross-references; minor cross-guide link issues (≤3 empty link texts or legacy targets) |
| **2** | Significant sections with no cross-references to related content; multiple broken cross-guide links |
| **1** | Content is siloed with minimal interlinking; no cross-guide links; broken navigation paths |

## Step 5: Usability — Link currency and version consistency

### Rule

All external links must be current and use version attributes where applicable. OpenShift documentation URLs must use `{ocp4-ver}` attribute instead of hardcoded version numbers or `/latest/`. Hardcoded versions that describe feature availability thresholds (e.g., "available on OpenShift 4.20 and later") are acceptable.

### What to check

1. **Hardcoded OCP versions in URLs** — Search for `container-platform/X.Y/` where X.Y is NOT `{ocp4-ver}`. These should use the attribute.
2. **`/latest/` in OCP URLs** — Search for `container-platform/latest/`. These should use `{ocp4-ver}` for consistent version pinning.
3. **Version consistency in attributes.adoc** — Link attributes defined in `common/attributes.adoc` must also use `{ocp4-ver}`, not `/latest/` or hardcoded versions.
4. **Feature availability thresholds** — Hardcoded versions in prose that describe when a feature became available (e.g., "This feature is available on OpenShift 4.20 and later") are acceptable. These are historical facts.
5. **Devfile documentation versions** — Links to `devfile.io/docs/` should use a consistent version across all files.
6. **Deprecated service warnings** — Check if any linked services have deprecation notices (e.g., Azure DevOps OAuth deprecation).

### Common patterns

```bash
# Find hardcoded OCP versions in links
grep -rn 'container-platform/[0-9]' topics/ modules/ assemblies/ --include='*.adoc' 2>/dev/null

# Find /latest/ links
grep -rn 'container-platform/latest/' topics/ modules/ assemblies/ common/ --include='*.adoc' 2>/dev/null
```

### Scoring

| Score | Criteria |
|-------|----------|
| **4** | All OCP links use `{ocp4-ver}` attribute. No `/latest/` in active content. Link attributes in `attributes.adoc` use `{ocp4-ver}`. |
| **3** | 1-5 instances of `/latest/` or hardcoded versions. Attribute links updated. |
| **2** | Widespread hardcoded versions or `/latest/` usage (>5 instances). Inconsistent. |
| **1** | No version management strategy. Hardcoded versions throughout. |

## Step 6: Verify

After fixing any violations, re-run the reference validation:

```bash
cd "$DOCS_REPO"
python3 scripts/validate-refs.py
```

Then run Vale to ensure no new warnings were introduced:

```bash
# Adjust directory names to match your repo structure (topics/ or modules/)
vale assemblies/ topics/ titles/administration_guide/master.adoc titles/user_guide/master.adoc
```
