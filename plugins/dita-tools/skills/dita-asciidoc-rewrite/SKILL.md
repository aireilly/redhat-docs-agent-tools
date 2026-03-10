---
name: dita-asciidoc-rewrite
description: Refactor AsciiDoc files for DITA conversion compatibility using LLM-guided analysis. Use this skill to fix Vale issues, prepare files for DITA conversion, or comprehensively rewrite AsciiDoc modules and assemblies following Red Hat modular documentation standards.
model: claude-opus-4-5@20251101
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Skill
---

# DITA AsciiDoc Rewrite Skill

Refactor AsciiDoc files for DITA conversion compatibility using careful LLM-guided analysis and the comprehensive fixing instructions in the reference file.

## Overview

This skill provides detailed instructions for fixing AsciiDoc issues that prevent clean DITA conversion. Use these instructions when applying LLM-guided refactoring to fix Vale AsciiDocDITA issues.

For the complete workflow including Vale linting, git branches, commits, and PR/MR creation, use the **/dita-tools:dita-rework --rewrite** command instead.

## Fixing Instructions

Read and follow the fixing instructions in:

@plugins/dita-tools/reference/dita-rewrite-fixing-instructions.md
