---
name: git-pr-reader
description: Extract code changes from GitHub Pull Requests and GitLab Merge Requests. Automatically detects GitHub vs GitLab from URL, fetches PR/MR title, description, and file diffs, and filters out irrelevant files (tests, configs, lock files, generated code). Supports pagination for large PRs/MRs. Use this skill when you need to analyze code changes from Git repositories to understand what was modified, added, or fixed for documentation purposes.
author: Gabriel McGoldrick (gmcgoldr@redhat.com)
allowed-tools: Read, Bash, Grep, Glob
---

# Git PR Reader Skill

Extract and analyze code changes from GitHub Pull Requests and GitLab Merge Requests for release note generation.

## Capabilities

- **Auto-detect Git platform**: Automatically identifies GitHub vs GitLab from URL
- **Extract PR/MR metadata**: Fetch title, description, and file-level diffs
- **Smart filtering**: Exclude irrelevant files using configurable patterns:
  - Test files (test/, *_test.go, *.spec.ts, etc.)
  - Lock files (package-lock.json, *.lock, Pipfile.lock, etc.)
  - CI/CD configs (.gitlab-ci.yml, .github/workflows/, Dockerfile, etc.)
  - Build artifacts (dist/, build/, target/, *.class, etc.)
  - Generated code (*.pb.go, *.gen.go, etc.)
  - Vendor directories (node_modules/, vendor/, etc.)
  - Images and binaries (*.png, *.jpg, *.svg, etc.)
- **Pagination support**: Handle PRs/MRs with hundreds of changed files
- **Structured output**: JSON format optimized for LLM consumption

## Usage

### Basic Usage

**GitHub Pull Request:**
```bash
python3 scripts/git_pr_reader.py --url "https://github.com/owner/repo/pull/123"
```

**GitLab Merge Request:**
```bash
python3 scripts/git_pr_reader.py --url "https://gitlab.com/group/project/-/merge_requests/456"
```

### Authentication

Set in `~/.env` (see docs-tools README for setup):

```bash
GITHUB_TOKEN=your-github-pat    # required scope: "repo" for private, "public_repo" for public
GITLAB_TOKEN=your-gitlab-pat    # required scope: "api"
```

### Command Line Options

- `--url URL`: GitHub PR or GitLab MR URL (required)
- `--no-filter`: Disable file filtering (include all files)
- `--max-files N`: Limit number of files to process (default: no limit)
- `--include-stats`: Include statistics about filtered files
- `--format {json,markdown}`: Output format (default: json)

### Output Formats

**JSON (default):**
```json
{
  "git_type": "github",
  "url": "https://github.com/owner/repo/pull/123",
  "title": "Fix authentication bug in user service",
  "description": "This PR fixes the authentication issue...",
  "diffs": [
    {
      "filename": "src/auth/service.py",
      "diff": "@@ -45,7 +45,7 @@\n def authenticate(user):\n-    return user.password == hash(input)\n+    return secure_compare(user.password, hash(input))\n"
    }
  ],
  "stats": {
    "total_files": 45,
    "filtered_files": 12,
    "included_files": 33
  }
}
```

**Markdown:**
```markdown
# Fix authentication bug in user service

**Source:** https://github.com/owner/repo/pull/123
**Type:** GitHub Pull Request

## Description

This PR fixes the authentication issue...

## Changed Files (33 of 45 total)

### src/auth/service.py
```diff
@@ -45,7 +45,7 @@
 def authenticate(user):
-    return user.password == hash(input)
+    return secure_compare(user.password, hash(input))
```
```

## Configuration

File filtering patterns are defined in `config/git_filters.yaml`. You can customize these patterns for your specific needs.

## Dependencies

Install required Python packages:

```bash
python3 -m pip install PyGithub python-gitlab pyyaml
```

## Use Cases

1. **Release Note Generation**: Extract code changes to understand what was modified for release notes
2. **Code Review Analysis**: Analyze PR/MR changes without navigating the web UI
3. **Documentation Updates**: Identify changes that need documentation
4. **Change Impact Assessment**: Understand scope of changes across codebase

## Performance

- **GitHub PRs**: Handles up to 1000 files per PR with pagination
- **GitLab MRs**: Efficiently fetches all changes in single API call
- **Filtering**: Typically reduces file count by 60-80% (tests, configs, generated code)

## Limitations

- GitHub API rate limits: 60 requests/hour (unauthenticated), 5000/hour (authenticated)
- GitLab API rate limits: 10 requests/second
- Only fetches file-level diffs, not commit-level history
- Requires public PRs/MRs unless authentication tokens are provided

## Integration with Other Skills

This skill works well with:
- **docs-tools:jira-reader**: Combine JIRA issue context with Git code changes
- **docs-tools:jira-writer**: Generate release notes from JIRA + Git data, then push back to JIRA

## Example Workflow

```bash
# 1. Get JIRA issue details
python3 scripts/jira_reader.py --issue COO-1145

# 2. Extract Git PR/MR changes from links in JIRA
python3 scripts/git_pr_reader.py --url "https://github.com/org/repo/pull/789"

# 3. Use both outputs to generate comprehensive release notes
```
