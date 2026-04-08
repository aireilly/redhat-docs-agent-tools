---
icon: lucide/puzzle
---

# Plugins and workflows

The Red Hat Docs Agent Tools repository organizes tools into six plugins. Each plugin groups related skills around a category of documentation work.

## docs-tools -- Review, writing, and workflow orchestration

The largest plugin (33 skills) covers the broadest range of documentation tasks. Writers use docs-tools skills to review files against the IBM Style Guide and the Red Hat Supplementary Style Guide, check modular documentation structure, read JIRA tickets and pull requests, extract content from web pages, and run multi-step documentation workflows that span requirements analysis, planning, writing, and review. The plugin also includes five specialized agents (docs-planner, docs-reviewer, docs-writer, requirements-analyst, and technical-reviewer) that Claude Code can dispatch as subagents.

## vale-tools -- Automated linting

Two skills wrap the Vale CLI for style-guide linting. One skill runs Vale against your files and reports violations. The other analyzes Vale output for false positives and can create a pull request to update the Vale at Red Hat rule set.

## dita-tools -- AsciiDoc cleanup for DITA conversion

Eighteen skills prepare AsciiDoc files for DITA conversion. The plugin handles callout transformation, entity reference replacement, short description rewrites, procedure formatting fixes, document ID generation, and full LLM-guided AsciiDoc rewrites. A validation skill runs Vale with DITA-specific rules to confirm conversion readiness.

## jtbd-tools -- Jobs-To-Be-Done analysis

Eight skills support documentation restructuring around user goals. The plugin extracts Jobs-To-Be-Done (JTBD) records from Markdown, AsciiDoc, and topic-map repositories, generates goal-oriented tables of contents, compares existing structure against the JTBD-based alternative, and produces consolidation reports for stakeholders.

## cqa-tools -- Content Quality Assessment

Twelve skills implement the CQA 2.1 assessment framework. The plugin scores documentation across 54 parameters organized into three categories: pre-migration readiness, content quality, and onboarding to docs.redhat.com. Individual skills target specific parameter groups such as modularization, editorial quality, procedures, links, and legal compliance.

## hello-world -- Reference plugin

A single-skill plugin that serves as a learning example. New contributors use hello-world to understand plugin structure before building their own.

## Common workflows

The following examples illustrate how documentation writers use agent tools in practice.

**Reviewing a file against the Red Hat Supplementary Style Guide.** Load one or more `rh-ssg-`* skills from docs-tools and point the assistant at your AsciiDoc file or files. The assistant checks formatting, grammar, structure, accessibility, and technical examples against the Red Hat Supplementary Style Guide and reports concrete issues with suggested fixes. You can then instruct the assistant to make the fixes, which you can then review file by file as diffs.

**Running an end-to-end documentation workflow from a JIRA ticket.** The docs-orchestrator skill in docs-tools drives a multi-step workflow: it reads requirements from a JIRA ticket, creates a documentation plan, writes drafts, runs a style review, and performs a technical accuracy check. Each step dispatches a specialized agent.

**Assessing content quality with CQA.** Load the cqa-assess skill and point it at a set of AsciiDoc modules. The assistant evaluates 54 parameters across pre-migration, quality, and onboarding categories, then generates a scored report with evidence and recommendations. After reviewing the report, you can instruct the assistant to make the changes so that you can review the output.

**Preparing AsciiDoc for DITA conversion.** Load dita-tools skills to fix callouts, replace entity references, add missing document IDs, rewrite short descriptions, and validate the result with DITA-specific Vale rules. The dita-asciidoc-rewrite skill can perform a comprehensive LLM-guided rewrite of an entire module.

## Next steps

Browse the [plugin catalog](../plugins.md) for full skill lists, or choose a getting-started guide for your editor:

- [Get started with Cursor](cursor.md)
- [Get started with Claude Code](claude-code.md)
