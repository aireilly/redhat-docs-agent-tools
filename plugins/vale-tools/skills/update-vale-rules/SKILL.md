---
name: update-vale-rules
description: Run Vale against a documentation repository, analyze output for false positives, and create a PR to update Vale-at-Red-Hat rules. Use this skill when asked to improve Vale rules, find false positives, or update the Vale at Red Hat style guide.
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Glob, Read, Edit, Write, Grep
---

# Update Vale Rules skill

Automate the detection and removal of false positives from Vale at Red Hat rules by analyzing documentation repositories.

## Workflow

This skill runs the `vale-rules-review.py` script which performs the following steps:

1. **Clone repository**: Clones a documentation repository to analyze
2. **Run Vale**: Executes Vale with RedHat rules against all documentation files (adoc by default)
3. **Deduplicate errors**: Identifies unique false positives across all files
4. **Review with Claude**: Uses Claude CLI to review each error and determine if it's a false positive
5. **Update rules**: Modifies Vale rule files and test fixtures to exclude false positives
6. **Create PR**: Submits a pull request to the vale-at-red-hat repository with the improvements from the users fork of the repo.

## Prerequisites

- Python 3.x
- Vale CLI installed (`brew install vale` or `dnf install vale`)
- Git and GitHub CLI (`gh`) configured
- Clone of the vale-at-red-hat repository as working directory
- Claude CLI installed

## Usage

Run the script from within a clone of the vale-at-red-hat repository:

```bash
# Basic usage - analyze a repository (adoc files by default)
python vale-tools/skills/update-vale-rules/scripts/vale-rules-review.py https://github.com/openshift/openshift-docs

# Specify file types to analyze
python vale-tools/skills/update-vale-rules/scripts/vale-rules-review.py https://github.com/example/repo -t adoc,md

# Control parallel workers
python vale-tools/skills/update-vale-rules/scripts/vale-rules-review.py https://github.com/example/repo -j 8

# Force fresh Vale run (ignore cached results)
python vale-tools/skills/update-vale-rules/scripts/vale-rules-review.py https://github.com/example/repo --force-vale
```

## Command line options

| Option | Description |
|--------|-------------|
| `repo_url` | URL of the documentation repository to analyze (required) |
| `-t, --file-types` | Comma-separated file extensions to process (default: `adoc`) |
| `-j, --jobs` | Number of parallel workers (default: min(16, CPU count)) |
| `--force-vale` | Force new Vale run even if cached results exist |

## Example invocations

- "Update Vale rules based on openshift-docs"
- "Find false positives in the RHEL documentation"
- "Improve Vale at Red Hat rules using the CRC docs"
- "Analyze vale errors in a repo and create a PR to fix them"
- "Run the vale rules review against quarkus docs"

## Output

The script produces:
- `tmp/<repo-name>/` - Cloned repository
- `tmp/vale-<repo-name>.json` - Raw Vale output
- `tmp/vale-<repo-name>-deduplicated.json` - Unique errors by rule
- Modified files in `.vale/styles/RedHat/` - Updated rules
- Modified files in `.vale/fixtures/RedHat/` - Updated test fixtures
- A GitHub pull request with all changes

## How false positives are identified

The script uses Claude to review each unique error and determine if it's a genuine style violation or a false positive. False positives are identified when:

- The matched text is a valid technical term or proper noun
- The context makes the usage acceptable
- The rule is too broad for the specific domain

When false positives are found, Claude:
1. Updates the rule YAML file to exclude the false positive
