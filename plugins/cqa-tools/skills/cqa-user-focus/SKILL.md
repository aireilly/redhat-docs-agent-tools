---
name: cqa-user-focus
description: Use when assessing CQA parameters Q6-Q11 (user focus). Checks persona targeting, pain point coverage, acronym expansion, Additional resources quality, admonition density, and assembly introduction audience targeting.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# CQA Q6-Q11: User Focus

## Parameters

| # | Parameter | Level |
|---|-----------|-------|
| Q6 | Content applies to target persona (admin vs developer) | Important |
| Q7 | Content addresses user pain points | Important |
| Q8 | New terms and acronyms defined before use | Important |
| Q9 | Additional resources include useful links across RH sites | Important |
| Q10 | Admonitions not overused (max 3-4 per file) | Important |
| Q11 | Assembly introductions target audience and persona | Important |

## Directory note

Some repos use `modules/` instead of `topics/` for content files. All `topics/` references in this skill apply equally to `modules/`. The automation scripts accept `--scan-dirs` to override the default scan directories.

## Checks

### Q6: Persona targeting

Content must be written for and placed in the guide that matches the target persona. The Dev Spaces documentation targets these Red Hat baseline personas:

**Administration Guide personas:**
- **Cloud Administrator** — Cloud administration, container management, infrastructure
- **Platform Engineer** — Developer platforms, CI/CD pipeline delivery, backing services
- **SRE** — Observability, reliability, automated remediation, root cause analysis
- **SysAdmin** — Infrastructure management, virtualization, software upgrades

**User Guide personas:**
- **Developer** — APIs, containers, Kubernetes, cloud-native app development, IDE usage
- **Platform Engineer** (secondary) — Devfile configuration, workspace customization for teams

#### What to check

1. **Guide-level separation**: Admin Guide content targets cluster administrators and platform operators. User Guide content targets developers and end users.
2. **No misplaced content between guides**: Procedures requiring only devfile or repository-level changes (no admin privileges) belong in the User Guide. Procedures requiring cluster-admin access, CheCluster CR modifications, or namespace-wide configuration belong in the Admin Guide.
3. **Knowledge assumptions match persona**: Admin Guide assumes OpenShift, Kubernetes, RBAC, and infrastructure knowledge. User Guide assumes Git, IDE, and development workflow knowledge.
4. **Cross-guide references are appropriate**: User Guide may reference admin-configured features ("Your administrator sets up OAuth..."). Admin Guide may reference developer workflows to explain the purpose of a configuration. These cross-references are expected and not misplacement.
5. **Content voice and perspective**: Admin content uses imperative voice for cluster operations. User content addresses developers with workspace and development-oriented language.

#### Red flags for misplacement

- **Developer content in Admin Guide**: Procedures that modify devfiles, `.code-workspace` files, or repository-level configuration without requiring admin access
- **Admin content in User Guide**: Procedures that require `cluster-admin` RBAC, CheCluster CR edits, or operator-level configuration
- **Mixed persona assemblies**: Assemblies where the majority of included topics target a different persona than the guide
- **Admin-only tips/notes in user procedures**: Detailed CheCluster field paths or admin commands embedded in user-facing content (should be cross-references instead)

#### Scoring rubric

| Score | Criteria |
|-------|----------|
| 4 (Meets) | All content correctly persona-targeted. No misplaced topics between guides. Cross-references used appropriately for cross-persona information. |
| 3 (Mostly meets) | Clear guide-level persona separation. Minor misplacements exist (≤5 topics) but overall structure is sound. Knowledge assumptions are appropriate. |
| 2 (Mostly does not meet) | Significant misplacements (>5 topics). Mixed persona content throughout. No clear guide-level separation strategy. |
| 1 (Does not meet) | No persona targeting. Admin and developer content mixed randomly. No structural separation. |

### Q7: Pain points

Documentation must address the pain points users are likely to encounter when accomplishing their goals. Pain point coverage includes both proactive prevention (warnings, prerequisites, verification) and reactive resolution (troubleshooting, workarounds, known issues).

#### What to check

**Proactive pain prevention:**
1. **WARNING and IMPORTANT admonitions** warn about common mistakes, data loss risks, compatibility issues, and security implications before the user encounters them
2. **Prerequisites** ensure users meet required conditions before starting a procedure, preventing mid-procedure failures
3. **Verification sections** confirm that a procedure succeeded, catching errors before they cascade

**Reactive pain resolution:**
4. **Troubleshooting content** addresses common failure scenarios with error-to-solution mappings
5. **Known issues and limitations** are documented with workarounds where available
6. **`.Troubleshooting` block titles** in procedures provide inline troubleshooting for steps that commonly fail

#### Common Dev Spaces pain points to verify

| Pain point | Expected coverage |
|-----------|-------------------|
| Workspace fails to start | Error-to-solution mapping, log inspection guidance |
| Slow workspace performance | Image caching, storage type, resource allocation |
| Git authentication failures | OAuth setup, token refresh, SSH key configuration |
| TLS/certificate errors | Certificate import procedures with verification |
| Storage/persistence issues | Strategy configuration, PV warnings, size limits |
| IDE extension problems | Installation, trust configuration, log debugging |
| Network connectivity | Proxy, firewall, WebSocket, DNS troubleshooting |
| Resource limits/quotas | Scaling guidance, per-user limits, sizing |
| Upgrade failures | Upgrade procedures, rollback, breaking changes |
| Custom devfile issues | Validation errors, version compatibility |

#### Scoring rubric

| Score | Criteria |
|-------|----------|
| 4 (Meets) | All common pain points covered. Both proactive (admonitions, prerequisites, verification) and reactive (troubleshooting, workarounds, known issues) coverage. Troubleshooting in both guides. |
| 3 (Mostly meets) | Most pain points covered proactively. Troubleshooting exists but has gaps. Some common failure scenarios lack error-to-solution content. |
| 2 (Mostly does not meet) | Limited pain point coverage. Few admonitions or prerequisites. Minimal troubleshooting content. Major gaps in common failure scenarios. |
| 1 (Does not meet) | No pain point coverage. No troubleshooting content. No warnings or prerequisites. |

### Q8: Acronyms

First use of each acronym per guide must be expanded. This is a representative subset of common acronyms — check the product's glossary or style guide for a complete list:
CLI, TLS, OAuth, DNS, API, HTTP, SSH, RBAC, OLM, PVC, UDI, CRD, CR, FQDN, IDE, OIDC, CA, CORS

### Q9: Additional resources quality

Additional resources sections must include links to appropriate and useful content across Red Hat sites, upstream documentation, and authoritative third-party sources.

#### What to check

1. **Coverage**: Every procedure file (`proc_`) must have an `[role="_additional-resources"]` `.Additional resources` section. Concept and reference files should have one when related content exists elsewhere.
2. **Link format consistency**: All external URLs must use the `link:` macro (`link:https://...[link text]`). Bare URLs without the `link:` macro are inconsistent with AsciiDoc best practices.
3. **Cross-guide links**: Links between Admin Guide and User Guide must use `{prod-ag-url}` or `{prod-ug-url}` attributes — not legacy aliases like `{administration-guide-url}`. The link target must match the actual `[id="..."]` declared in the target file.
4. **Link text**: All links must have descriptive link text. Empty link text for `link:` macros (`link:https://...[  ]`) is not acceptable. `xref:` with empty `[]` is standard (auto-generates from title).
5. **Domain quality**: Links should point to authoritative sources:
   - **Red Hat sites**: `docs.redhat.com`, `access.redhat.com`, `docs.openshift.com` — primary
   - **Upstream/community**: `github.com/eclipse-che`, `github.com/devfile`, `github.com/che-incubator` — expected for open-source references
   - **Authoritative third-party**: `kubernetes.io`, `docs.github.com`, `jetbrains.com`, `code.visualstudio.com` — acceptable for vendor-specific documentation
6. **Link relevance**: Links must be relevant to the topic. Avoid generic "learn more" links that don't add value. Each link should help the user accomplish a next step, understand a related concept, or find deeper technical detail.
7. **No broken links**: URLs must point to valid, accessible resources. Version-parameterized URLs (using `{ocp4-ver}`, `{prod-ver}`) must resolve correctly.
8. **Red Hat content breadth**: At least 80% of files with Additional resources should include at least one link to Red Hat-hosted content (docs, knowledge base, or product pages).

#### Red flags

- Bare URLs without `link:` macro in Additional resources sections
- Legacy attribute names (`{administration-guide-url}`) instead of standard ones (`{prod-ag-url}`)
- Cross-guide links with incorrect target IDs (missing or extra prefix)
- Malformed URLs (concatenated paths, mixed hardcoded versions with attributes)
- Missing Additional resources in procedure files
- Links to deprecated or removed content

#### Automation

```sh
python3 ../cqa-assess/scripts/check-external-links.py "$DOCS_REPO"
```

Extracts and categorizes all external URLs by domain type. Does not check link liveness but identifies domain distribution and placeholder URLs.

#### Scoring rubric

| Score | Criteria |
|-------|----------|
| 4 (Meets) | 100% proc files have Additional resources. All links use correct `link:` macro format. Cross-guide links use standard attributes with correct target IDs. ≥80% of files link to Red Hat content. No legacy attributes in active content. |
| 3 (Mostly meets) | ≥90% proc files have Additional resources. Minor formatting issues (≤5 bare URLs or legacy attributes). Cross-guide links mostly correct. Good domain diversity. |
| 2 (Mostly does not meet) | <90% proc files have Additional resources. Significant formatting issues (>5 bare URLs). Legacy attributes still in use. Poor link relevance. |
| 1 (Does not meet) | Most files lack Additional resources. No consistent link formatting. Broken cross-guide links. No Red Hat content links. |

### Q10: Admonition density and quality

Admonitions should draw the reader's attention to certain information. Keep admonitions to a minimum and avoid placing multiple admonitions close to one another.

#### Valid admonition types

| Type | Purpose |
|------|---------|
| NOTE | Additional guidance or advice that improves product configuration, performance, or supportability |
| IMPORTANT | Advisory information essential to the completion of a task. Users must not disregard this information |
| WARNING | Information about potential system damage, data loss, or a support-related issue |
| TIP | Alternative methods that might not be obvious. Not essential to using the product |

**CAUTION is NOT supported** by the Red Hat Customer Portal. Do not use this admonition type.

#### What to check

1. **Density**: Maximum 3-4 admonitions per file. Flag files exceeding this threshold.
2. **Block format**: All admonitions must use proper block format (`[TYPE]` + `====` delimiters). Inline admonitions (`NOTE: text`) must be converted to block format.
3. **No CAUTION**: CAUTION admonitions are not supported by the Red Hat Customer Portal. Convert to IMPORTANT or WARNING.
4. **No procedures in admonitions**: Admonitions must not contain ordered list steps (`. Step one`, `. Step two`). Extract procedures into `.Troubleshooting` sections or separate topics.
5. **Type correctness**: Content must match the admonition type. NOTEs about errors/damage should be WARNINGs. WARNINGs about informational content should be NOTEs.
6. **Conciseness**: Admonitions should be short and concise. Flag admonitions exceeding 5 lines of content (excluding source blocks that are necessary for context).
7. **No plural labels**: Only individual admonitions are allowed (e.g., `[NOTE]`, not `[NOTES]`).
8. **Proximity**: Avoid placing multiple admonitions close to one another. If multiple admonitions are necessary, consider restructuring — move less-important statements into the main content flow.
9. **Placement in procedures**: Place admonitions before the step to which they apply, not after.

#### Red flags

- Files with 5+ admonitions
- Inline admonitions (`NOTE: text` instead of block format)
- CAUTION admonitions (unsupported type)
- Ordered list steps inside admonition blocks
- Three or more consecutive admonitions with no content between them
- WARNING used for informational content (should be NOTE)
- NOTE used for damage/data loss warnings (should be WARNING)
- Admonitions longer than one paragraph

#### Scoring rubric

| Score | Criteria |
|-------|----------|
| 4 (Meets) | All files within 3-4 admonition limit. All admonitions use block format. No CAUTION type. No procedures inside admonitions. Correct type usage. Concise content. |
| 3 (Mostly meets) | Most files within limit (≤3 files at 4). Minor formatting issues (≤5 inline admonitions). No CAUTION. Occasional type mismatches. |
| 2 (Mostly does not meet) | Multiple files exceed limit. Inline admonitions widespread. CAUTION used. Procedures inside admonitions. Significant type mismatches. |
| 1 (Does not meet) | No admonition discipline. Mixed inline/block. Procedures in admonitions. CAUTION used. No adherence to type definitions. |

### Q11: Assembly introduction audience targeting

Assembly introductions must consider the target audience and apply to a specific persona or skill level. The introduction explains what the user accomplishes by working through the assembled modules.

#### What to check

1. **User story framing**: The introduction should be the user story reworded. It must explain what the user will accomplish (the goal), not just describe what the assembly contains.
2. **Audience identification**: The introduction should identify or imply the target persona/audience. Admin Guide assemblies target cluster administrators and platform engineers. User Guide assemblies target developers. This can be implicit through guide placement.
3. **WHAT + WHY**: The introduction must state both WHAT the user will do and WHY it matters (the benefit or purpose). Introductions stating only WHAT without WHY are adequate but not ideal.
4. **Concise scope**: The introduction should be 1-3 sentences providing context for the assembly. Avoid embedding concept-level detail, reference material (field descriptions, option lists), or procedural content in the introduction. If the introduction exceeds ~5 lines of rendered content, it likely contains material that belongs in a topic module.
5. **Title alignment**: The assembly title form must match its content — gerund phrase for task-based assemblies (containing procedures), noun phrase for non-procedural assemblies.
6. **No self-referential language**: Do not use "This section describes...", "This chapter contains...", or "The following modules cover...".
7. **No rendered text between includes**: DITA maps do not accept rendered text between module includes. All text must appear in the introductory section before the first `include::`.
8. **Additional resources DITA compliance**: If the assembly has an Additional resources section, it must contain only links — no non-link text.
9. **Attribute usage in prose**: Use product attributes (`{prod-short}`, `{orch-name}`) instead of hardcoded product names in the introduction text.

#### Quality levels for assembly introductions

| Level | Criteria | Example |
|-------|----------|---------|
| Excellent | Multi-sentence, states WHAT + WHY + HOW/context, implies persona | "Configure OAuth to allow {prod-short} users to interact with remote Git repositories without re-entering credentials." |
| Good | States WHAT + WHY or WHAT + scope clearly | "Configure networking for {prod-short} to secure communications, enable custom routing, and support restricted environments." |
| Adequate | States WHAT only, single sentence, no WHY | "Configure storage for {prod-short} workspaces, including storage classes, strategies, and sizes." |
| Poor | Title repetition with "You can" prefix, or missing | — |

#### Scoring rubric

| Score | Criteria |
|-------|----------|
| 4 (Meets) | All assemblies have substantive introductions. All state WHAT the user accomplishes. ≥75% are good-to-excellent quality (WHAT + WHY). No self-referential language. No rendered text between includes. Titles match content form. No concept/reference material in intros. |
| 3 (Mostly meets) | All assemblies have introductions. Most state WHAT. Some lack WHY. 1-2 overly-long intros with concept material. Minor title issues. |
| 2 (Mostly does not meet) | Multiple assemblies lack introductions or have title-repetition intros. Rendered text between includes. Widespread title form violations. |
| 1 (Does not meet) | Missing introductions. No audience awareness. Rendered text between includes. Titles do not follow conventions. |

## Scoring

See [scoring-guide.md](../../reference/scoring-guide.md).
