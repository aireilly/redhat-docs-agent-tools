#!/usr/bin/env python3
"""
Git Commit Reader - CLI for analyzing commits on GitHub and GitLab repositories.

Provides commit-level operations for documentation impact analysis:
- Listing commits on a branch since a given SHA
- Fetching diffs for individual commits or commit ranges
- Listing files changed in commits or commit ranges
- YAML-based file filtering (reuses git_filters.yaml from git-pr-reader)

Usage:
    python git_commit_reader.py list <repo-url> --since <sha> [--branch main] [--json]
    python git_commit_reader.py diff <repo-url> <sha> [--json]
    python git_commit_reader.py range-diff <repo-url> <from-sha> <to-sha> [--json]
    python git_commit_reader.py files <repo-url> <sha> [--json]
    python git_commit_reader.py range-files <repo-url> <from-sha> <to-sha> [--json]

Authentication:
    Requires tokens in ~/.env:
    - GitHub: GITHUB_TOKEN environment variable
    - GitLab: GITLAB_TOKEN environment variable
"""

import argparse
import json
import os
import pathlib
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Import shared utilities from git_pr_reader
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from git_pr_reader import load_env_file, load_filters  # noqa: E402

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

try:
    from github import Github, Auth
except ImportError:
    Github = None  # type: ignore[assignment,misc]
    Auth = None  # type: ignore[assignment,misc]

try:
    from gitlab import Gitlab
except ImportError:
    Gitlab = None  # type: ignore[assignment,misc]


# =============================================================================
# Repository URL parsing
# =============================================================================


def parse_repo_url(url: str) -> Dict[str, str]:
    """
    Parse a repository URL to extract platform, owner, and repo name.

    Supports:
      - https://github.com/owner/repo
      - https://gitlab.com/group/project
      - https://gitlab.example.com/group/subgroup/project

    Returns:
        Dict with keys: platform, host, owner, repo, owner_repo
    """
    parsed = urlparse(url.rstrip("/"))
    host = parsed.netloc.lower()
    path_parts = parsed.path.strip("/").split("/")

    if len(path_parts) < 2:
        raise ValueError(f"Cannot parse repository URL: {url}")

    if "github.com" in host:
        platform = "github"
        owner = path_parts[0]
        repo = path_parts[1].removesuffix(".git")
        owner_repo = f"{owner}/{repo}"
    elif "gitlab" in host:
        platform = "gitlab"
        # GitLab supports nested groups: group/subgroup/project
        repo = path_parts[-1].removesuffix(".git")
        owner = "/".join(path_parts[:-1])
        owner_repo = f"{owner}/{repo}"
    else:
        raise ValueError(
            f"Cannot determine platform from URL: {url}\n"
            "Supported: github.com, gitlab.com (or self-hosted GitLab)"
        )

    return {
        "platform": platform,
        "host": host,
        "owner": owner,
        "repo": repo,
        "owner_repo": owner_repo,
    }


def repo_slug(url: str) -> str:
    """Derive a filesystem-safe slug from a repo URL."""
    parsed = urlparse(url.rstrip("/"))
    host = parsed.netloc.lower()
    path = parsed.path.strip("/").removesuffix(".git")
    return re.sub(r"[^a-z0-9]", "-", f"{host}-{path}".lower()).strip("-")


# =============================================================================
# File filtering
# =============================================================================


def should_include_file(filename: str, filters: List[re.Pattern]) -> bool:
    """Check if a file should be included based on filter patterns."""
    if not filters:
        return True
    return not any(regex.search(filename) for regex in filters)


# =============================================================================
# GitHub implementation
# =============================================================================


class GitHubCommitReader:
    """Read commits from GitHub repositories using PyGithub."""

    def __init__(self, repo_url: str):
        if Github is None or Auth is None:
            raise ImportError(
                "PyGithub not installed. Run: python3 -m pip install PyGithub"
            )
        load_env_file()
        info = parse_repo_url(repo_url)
        self.owner_repo = info["owner_repo"]
        self.repo_name = info["repo"]

        token = os.environ.get("GITHUB_TOKEN")
        if token:
            self._github = Github(auth=Auth.Token(token))
        else:
            self._github = Github()

        self._repo = self._github.get_repo(self.owner_repo)

    @property
    def default_branch(self) -> str:
        """Return the repository's default branch name."""
        return self._repo.default_branch

    def list_commits(
        self,
        branch: str = "main",
        since_sha: Optional[str] = None,
        max_commits: int = 50,
        no_merges: bool = False,
    ) -> List[Dict[str, Any]]:
        """List commits on a branch, optionally since a given SHA."""
        kwargs: Dict[str, Any] = {"sha": branch}
        commits_iter = self._repo.get_commits(**kwargs)

        results = []
        found_since = since_sha is None
        collected = 0

        for commit in commits_iter:
            if collected >= max_commits and since_sha is None:
                break

            if since_sha and commit.sha == since_sha:
                break
            if since_sha and commit.sha.startswith(since_sha):
                break

            if no_merges and len(commit.parents) > 1:
                continue

            results.append({
                "sha": commit.sha,
                "short_sha": commit.sha[:7],
                "message": commit.commit.message,
                "author": commit.commit.author.name if commit.commit.author else "unknown",
                "date": commit.commit.author.date.isoformat() if commit.commit.author else None,
                "parents": [p.sha for p in commit.parents],
                "files_changed": commit.stats.total if commit.stats else 0,
                "additions": commit.stats.additions if commit.stats else 0,
                "deletions": commit.stats.deletions if commit.stats else 0,
            })
            collected += 1

        # Reverse so oldest is first
        results.reverse()
        return results

    def get_commit_files(self, sha: str) -> List[Dict[str, Any]]:
        """Get files changed in a single commit."""
        commit = self._repo.get_commit(sha)
        files = []
        for f in commit.files:
            files.append({
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "changes": f.changes,
                "patch": f.patch or "",
            })
        return files

    def get_commit_diff(self, sha: str) -> str:
        """Get the unified diff for a single commit."""
        commit = self._repo.get_commit(sha)
        parts = []
        for f in commit.files:
            if f.patch:
                parts.append(f"diff --git a/{f.filename} b/{f.filename}")
                parts.append(f.patch)
        return "\n".join(parts)

    def get_range_files(
        self, from_sha: str, to_sha: str, branch: str = "main"
    ) -> List[Dict[str, Any]]:
        """Get all files changed across a commit range."""
        comparison = self._repo.compare(from_sha, to_sha)
        files = []
        for f in comparison.files:
            files.append({
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "changes": f.changes,
                "patch": f.patch or "",
            })
        return files

    def get_range_diff(self, from_sha: str, to_sha: str) -> str:
        """Get the combined diff for a commit range."""
        comparison = self._repo.compare(from_sha, to_sha)
        parts = []
        for f in comparison.files:
            if f.patch:
                parts.append(f"diff --git a/{f.filename} b/{f.filename}")
                parts.append(f.patch)
        return "\n".join(parts)


# =============================================================================
# GitLab implementation
# =============================================================================


class GitLabCommitReader:
    """Read commits from GitLab repositories using python-gitlab."""

    def __init__(self, repo_url: str):
        if Gitlab is None:
            raise ImportError(
                "python-gitlab not installed. Run: python3 -m pip install python-gitlab"
            )
        load_env_file()
        info = parse_repo_url(repo_url)
        self.owner_repo = info["owner_repo"]
        self.repo_name = info["repo"]

        token = os.environ.get("GITLAB_TOKEN")
        gitlab_url = f"https://{info['host']}"

        if token:
            self._gitlab = Gitlab(gitlab_url, private_token=token)
        else:
            self._gitlab = Gitlab(gitlab_url)

        self._project = self._gitlab.projects.get(self.owner_repo)

    @property
    def default_branch(self) -> str:
        """Return the repository's default branch name."""
        return self._project.default_branch

    def list_commits(
        self,
        branch: str = "main",
        since_sha: Optional[str] = None,
        max_commits: int = 50,
        no_merges: bool = False,
    ) -> List[Dict[str, Any]]:
        """List commits on a branch, optionally since a given SHA."""
        kwargs: Dict[str, Any] = {
            "ref_name": branch,
            "per_page": max_commits,
        }

        commits = self._project.commits.list(**kwargs, get_all=False)

        results = []
        for commit in commits:
            if since_sha and (commit.id == since_sha or commit.id.startswith(since_sha)):
                break

            if no_merges and len(commit.parent_ids) > 1:
                continue

            results.append({
                "sha": commit.id,
                "short_sha": commit.short_id,
                "message": commit.message,
                "author": commit.author_name,
                "date": commit.authored_date,
                "parents": commit.parent_ids,
                "files_changed": 0,  # GitLab doesn't provide this in list
                "additions": 0,
                "deletions": 0,
            })

        # Reverse so oldest is first
        results.reverse()
        return results

    def get_commit_files(self, sha: str) -> List[Dict[str, Any]]:
        """Get files changed in a single commit."""
        commit = self._project.commits.get(sha)
        diffs = commit.diff()
        files = []
        for d in diffs:
            files.append({
                "filename": d["new_path"],
                "status": "added" if d["new_file"] else "deleted" if d["deleted_file"] else "modified",
                "additions": 0,
                "deletions": 0,
                "changes": 0,
                "patch": d.get("diff", ""),
            })
        return files

    def get_commit_diff(self, sha: str) -> str:
        """Get the unified diff for a single commit."""
        commit = self._project.commits.get(sha)
        diffs = commit.diff()
        parts = []
        for d in diffs:
            if d.get("diff"):
                parts.append(f"diff --git a/{d['old_path']} b/{d['new_path']}")
                parts.append(d["diff"])
        return "\n".join(parts)

    def get_range_files(
        self, from_sha: str, to_sha: str, branch: str = "main"
    ) -> List[Dict[str, Any]]:
        """Get all files changed across a commit range."""
        comparison = self._project.repository_compare(from_sha, to_sha)
        files = []
        for d in comparison.get("diffs", []):
            files.append({
                "filename": d["new_path"],
                "status": "added" if d["new_file"] else "deleted" if d["deleted_file"] else "modified",
                "additions": 0,
                "deletions": 0,
                "changes": 0,
                "patch": d.get("diff", ""),
            })
        return files

    def get_range_diff(self, from_sha: str, to_sha: str) -> str:
        """Get the combined diff for a commit range."""
        comparison = self._project.repository_compare(from_sha, to_sha)
        parts = []
        for d in comparison.get("diffs", []):
            if d.get("diff"):
                parts.append(f"diff --git a/{d['old_path']} b/{d['new_path']}")
                parts.append(d["diff"])
        return "\n".join(parts)


# =============================================================================
# Factory
# =============================================================================


def create_reader(repo_url: str):
    """Create the appropriate reader based on the repo URL."""
    info = parse_repo_url(repo_url)
    if info["platform"] == "github":
        return GitHubCommitReader(repo_url)
    elif info["platform"] == "gitlab":
        return GitLabCommitReader(repo_url)
    else:
        raise ValueError(f"Unsupported platform: {info['platform']}")


# =============================================================================
# CLI command handlers
# =============================================================================


def cmd_list(args) -> int:
    """Handle the 'list' subcommand."""
    reader = create_reader(args.repo_url)
    filters = load_filters()

    # Auto-detect default branch if not specified
    branch = args.branch or reader.default_branch

    commits = reader.list_commits(
        branch=branch,
        since_sha=args.since,
        max_commits=args.max,
        no_merges=args.no_merges,
    )

    # Enrich with relevant file counts if possible
    total_files = 0
    relevant_files = 0
    for c in commits:
        try:
            files = reader.get_commit_files(c["sha"])
            all_count = len(files)
            rel_count = sum(1 for f in files if should_include_file(f["filename"], filters))
            c["files_changed"] = all_count
            c["relevant_files_changed"] = rel_count
            total_files += all_count
            relevant_files += rel_count
        except Exception as exc:
            print(f"Warning: failed to fetch files for {c['sha'][:7]}: {exc}", file=sys.stderr)
            c["files_changed"] = c.get("files_changed", 0)
            c["relevant_files_changed"] = c.get("files_changed", 0)

    # Drop commits with no relevant files after filtering
    dropped_empty = 0
    if getattr(args, "drop_empty", False):
        dropped = [c for c in commits if c.get("relevant_files_changed", 1) == 0]
        dropped_empty = len(dropped)
        commits = [c for c in commits if c.get("relevant_files_changed", 1) > 0]

    output = {
        "repository": args.repo_url,
        "branch": branch,
        "since": args.since,
        "total": len(commits),
        "commits": commits,
        "filtered_stats": {
            "total_files": total_files,
            "relevant_files": relevant_files,
            "excluded_files": total_files - relevant_files,
        },
        "dropped_empty": dropped_empty,
    }

    if args.json:
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"Repository: {args.repo_url}")
        print(f"Branch: {branch}")
        print(f"Commits since {args.since or 'beginning'}: {len(commits)}")
        print(f"Files: {relevant_files} relevant / {total_files} total")
        print()
        for c in commits:
            first_line = c["message"].split("\n")[0]
            print(f"  {c['short_sha']}  {first_line}")

    return 0


def cmd_diff(args) -> int:
    """Handle the 'diff' subcommand."""
    reader = create_reader(args.repo_url)
    filters = load_filters()

    diff_text = reader.get_commit_diff(args.sha)

    if args.json:
        # Filter and structure
        files = reader.get_commit_files(args.sha)
        filtered = [f for f in files if should_include_file(f["filename"], filters)]
        output = {
            "repository": args.repo_url,
            "sha": args.sha,
            "files": [{
                "filename": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
                "patch": f["patch"],
            } for f in filtered],
        }
        print(json.dumps(output, indent=2))
    else:
        print(diff_text)

    return 0


def cmd_range_diff(args) -> int:
    """Handle the 'range-diff' subcommand."""
    reader = create_reader(args.repo_url)
    filters = load_filters()

    if args.json:
        files = reader.get_range_files(args.from_sha, args.to_sha)
        filtered = [f for f in files if should_include_file(f["filename"], filters)]
        output = {
            "repository": args.repo_url,
            "from_sha": args.from_sha,
            "to_sha": args.to_sha,
            "total_files": len(files),
            "relevant_files": len(filtered),
            "files": [{
                "filename": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
                "patch": f["patch"],
            } for f in filtered],
        }
        print(json.dumps(output, indent=2))
    else:
        diff_text = reader.get_range_diff(args.from_sha, args.to_sha)
        print(diff_text)

    return 0


def cmd_files(args) -> int:
    """Handle the 'files' subcommand."""
    reader = create_reader(args.repo_url)
    filters = load_filters()

    files = reader.get_commit_files(args.sha)
    filtered = [f for f in files if should_include_file(f["filename"], filters)]

    if args.json:
        output = {
            "repository": args.repo_url,
            "sha": args.sha,
            "total": len(files),
            "relevant": len(filtered),
            "excluded": len(files) - len(filtered),
            "files": [{
                "filename": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
            } for f in filtered],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Files changed in {args.sha[:7]} ({len(filtered)}/{len(files)} relevant):")
        for f in filtered:
            status_char = {"added": "A", "modified": "M", "deleted": "D", "renamed": "R"}.get(f["status"], "?")
            print(f"  {status_char} {f['filename']} (+{f['additions']}/-{f['deletions']})")

    return 0


def cmd_range_files(args) -> int:
    """Handle the 'range-files' subcommand."""
    reader = create_reader(args.repo_url)
    filters = load_filters()

    files = reader.get_range_files(args.from_sha, args.to_sha)
    filtered = [f for f in files if should_include_file(f["filename"], filters)]

    if args.json:
        output = {
            "repository": args.repo_url,
            "from_sha": args.from_sha,
            "to_sha": args.to_sha,
            "total": len(files),
            "relevant": len(filtered),
            "excluded": len(files) - len(filtered),
            "files": [{
                "filename": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
            } for f in filtered],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Files changed {args.from_sha[:7]}..{args.to_sha[:7]} ({len(filtered)}/{len(files)} relevant):")
        for f in filtered:
            status_char = {"added": "A", "modified": "M", "deleted": "D", "renamed": "R"}.get(f["status"], "?")
            print(f"  {status_char} {f['filename']} (+{f['additions']}/-{f['deletions']})")

    return 0


# =============================================================================
# CLI entry point
# =============================================================================


def main():
    """Main CLI entry point with subcommands."""
    parser = argparse.ArgumentParser(
        description="Git Commit Reader - Analyze commits on GitHub and GitLab repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List commits since a SHA
  %(prog)s list https://github.com/owner/repo --since abc1234 --json

  # Get diff for a single commit
  %(prog)s diff https://github.com/owner/repo def5678 --json

  # Get combined diff for a commit range
  %(prog)s range-diff https://github.com/owner/repo abc1234 def5678 --json

  # List files changed in a commit
  %(prog)s files https://github.com/owner/repo def5678 --json

  # List files changed across a commit range
  %(prog)s range-files https://github.com/owner/repo abc1234 def5678 --json
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -- list subcommand
    list_parser = subparsers.add_parser("list", help="List commits on a branch since a SHA")
    list_parser.add_argument("repo_url", help="Repository URL (GitHub or GitLab)")
    list_parser.add_argument("--since", help="List commits after this SHA")
    list_parser.add_argument("--branch", default=None, help="Branch name (default: auto-detect from repository)")
    list_parser.add_argument("--max", type=int, default=50, help="Max commits to return (default: 50)")
    list_parser.add_argument("--no-merges", action="store_true", help="Exclude merge commits")
    list_parser.add_argument("--drop-empty", action="store_true", help="Exclude commits with zero relevant files after filtering")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # -- diff subcommand
    diff_parser = subparsers.add_parser("diff", help="Get diff for a single commit")
    diff_parser.add_argument("repo_url", help="Repository URL")
    diff_parser.add_argument("sha", help="Commit SHA")
    diff_parser.add_argument("--json", action="store_true", help="Output as JSON with file filtering")

    # -- range-diff subcommand
    range_diff_parser = subparsers.add_parser("range-diff", help="Get combined diff for a commit range")
    range_diff_parser.add_argument("repo_url", help="Repository URL")
    range_diff_parser.add_argument("from_sha", help="Start commit SHA (exclusive)")
    range_diff_parser.add_argument("to_sha", help="End commit SHA (inclusive)")
    range_diff_parser.add_argument("--json", action="store_true", help="Output as JSON with file filtering")

    # -- files subcommand
    files_parser = subparsers.add_parser("files", help="List files changed in a commit")
    files_parser.add_argument("repo_url", help="Repository URL")
    files_parser.add_argument("sha", help="Commit SHA")
    files_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # -- range-files subcommand
    range_files_parser = subparsers.add_parser("range-files", help="List files changed across a commit range")
    range_files_parser.add_argument("repo_url", help="Repository URL")
    range_files_parser.add_argument("from_sha", help="Start commit SHA (exclusive)")
    range_files_parser.add_argument("to_sha", help="End commit SHA (inclusive)")
    range_files_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # -- parse and dispatch
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    handlers = {
        "list": cmd_list,
        "diff": cmd_diff,
        "range-diff": cmd_range_diff,
        "files": cmd_files,
        "range-files": cmd_range_files,
    }

    handler = handlers.get(args.command)
    if handler:
        try:
            sys.exit(handler(args))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
