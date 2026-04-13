#!/usr/bin/env python3
"""Resolve and clone/verify a source code repository for a docs workflow.

Extracts the deterministic repo-resolution logic from the orchestrator skill
into a standalone script. The orchestrator calls this script and makes
decisions (user prompts, deferred step management) based on the JSON output.

Modes:

1. Explicit source (--repo and/or --pr):
    python3 resolve_source.py --base-path .claude/docs/proj-123 \
        --repo https://github.com/org/repo.git --pr https://github.com/org/repo/pull/42

2. From existing source.yaml:
    python3 resolve_source.py --base-path .claude/docs/proj-123

3. Scan requirements.md for PR URLs (post-requirements discovery):
    python3 resolve_source.py --base-path .claude/docs/proj-123 --scan-requirements

Output: JSON to stdout with the resolved source info, or an error status.

Exit codes:
    0 — success (source resolved, JSON on stdout)
    1 — error (message on stderr)
    2 — no source found (not an error; JSON with status "no_source" on stdout)

Limitations:
    - GitLab MR resolution is not yet supported. MRs are discovered during
      requirements scanning but cannot be resolved automatically (gh CLI is
      GitHub-only). Users must provide --repo manually for GitLab repos.
      Future work: add glab CLI support or GitLab API integration.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# PR/MR URL patterns
GITHUB_PR_RE = re.compile(
    r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)"
)
GITLAB_MR_RE = re.compile(
    r"https?://gitlab\.[^/]+/(.+?)/-/merge_requests/(\d+)"
)


def _is_remote_url(value):
    """Check if a value is a remote git URL (not a local path)."""
    return value.startswith(("https://", "git@", "ssh://"))


def _run_git(args, cwd=None, check=True):
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, ["git"] + args, result.stdout, result.stderr
        )
    return result


def _run_gh(args, check=True):
    """Run a gh CLI command and return stdout."""
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, ["gh"] + args, result.stdout, result.stderr
        )
    return result.stdout.strip()


def _read_source_yaml(base_path):
    """Read source.yaml if it exists. Returns dict or None."""
    source_file = Path(base_path) / "source.yaml"
    if not source_file.exists():
        return None
    try:
        import yaml
    except ImportError:
        # Fall back to basic parsing for simple YAML
        return _parse_simple_yaml(source_file)
    with open(source_file) as f:
        return yaml.safe_load(f)


def _parse_simple_yaml(path):
    """Parse a simple key-value YAML without PyYAML dependency.

    Handles the source.yaml schema: top-level scalars (repo, ref) and a
    nested scope dict with include/exclude lists. Indentation determines
    nesting — indented keys belong to the most recent top-level mapping key.
    """
    result = {}
    # parent_key tracks the current top-level mapping key (e.g., "scope")
    parent_key = None
    current_list = None

    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip())

            # Handle list items under a nested key
            if stripped.startswith("- ") and current_list is not None:
                value = stripped[2:].strip().strip('"').strip("'")
                current_list.append(value)
                continue

            if ":" not in stripped:
                continue

            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()

            if indent == 0:
                # Top-level key
                if value:
                    result[key] = value.strip('"').strip("'")
                    parent_key = None
                    current_list = None
                else:
                    # Mapping parent (e.g., "scope:")
                    result[key] = {}
                    parent_key = key
                    current_list = None
            elif parent_key and indent > 0:
                # Nested key under parent (e.g., "include:" under "scope:")
                if value:
                    result[parent_key][key] = value.strip('"').strip("'")
                    current_list = None
                else:
                    # List parent (e.g., "include:" with no value)
                    result[parent_key][key] = []
                    current_list = result[parent_key][key]

    return result


def _normalize_git_url(url):
    """Normalize a git URL for comparison (strip .git suffix and trailing slash)."""
    return url.rstrip("/").removesuffix(".git")


def _resolve_pr_info(pr_url):
    """Extract repo URL and branch from a GitHub PR URL using gh CLI.

    Derives the clone URL from the PR URL (base repo), not headRepository
    (which may be a fork).
    """
    # Extract base repo slug from PR URL: https://github.com/org/repo/pull/N
    match = GITHUB_PR_RE.match(pr_url)
    if match:
        repo_slug = match.group(1)
        repo_url = f"https://github.com/{repo_slug}.git"
    else:
        # Fallback for non-standard URLs — ask gh for the PR's base repo
        repo_url = _run_gh([
            "pr", "view", pr_url,
            "--json", "url",
            "--jq", '.url | split("/pull/")[0] + ".git"',
        ])

    pr_branch = _run_gh([
        "pr", "view", pr_url,
        "--json", "headRefName",
        "--jq", ".headRefName",
    ])
    return repo_url, pr_branch


def _scan_requirements_for_prs(base_path):
    """Scan requirements.md for PR/MR URLs and group by repo."""
    req_file = Path(base_path) / "requirements" / "requirements.md"
    if not req_file.exists():
        return {}

    content = req_file.read_text()
    repos = {}

    for match in GITHUB_PR_RE.finditer(content):
        repo_slug = match.group(1)
        pr_num = match.group(2)
        url = match.group(0)
        repos.setdefault(repo_slug, []).append({
            "url": url,
            "number": int(pr_num),
            "type": "github",
        })

    for match in GITLAB_MR_RE.finditer(content):
        repo_slug = match.group(1)
        mr_num = match.group(2)
        url = match.group(0)
        repos.setdefault(repo_slug, []).append({
            "url": url,
            "number": int(mr_num),
            "type": "gitlab",
        })

    return repos


def _clone_repo(repo_url, clone_dir, ref=None):
    """Clone a repo to clone_dir. Returns True on success."""
    clone_dir = str(clone_dir)

    if ref:
        # Try cloning at the specific branch first
        result = _run_git(
            ["clone", "--depth", "1", "--branch", ref, repo_url, clone_dir],
            check=False,
        )
        if result.returncode == 0:
            return True

        # Fallback: clone default branch, then fetch and checkout the ref
        result = _run_git(
            ["clone", "--depth", "1", repo_url, clone_dir],
            check=False,
        )
        if result.returncode != 0:
            return False

        fetch = _run_git(["fetch", "origin", ref], cwd=clone_dir, check=False)
        if fetch.returncode != 0:
            return False

        checkout = _run_git(["checkout", "FETCH_HEAD"], cwd=clone_dir, check=False)
        return checkout.returncode == 0

    result = _run_git(
        ["clone", "--depth", "1", repo_url, clone_dir],
        check=False,
    )
    return result.returncode == 0


def _verify_existing_clone(clone_dir, ref=None, expected_repo_url=None):
    """Verify an existing clone is valid. Optionally checkout a different ref.

    Assumes the remote is named "origin". This is always true for repos cloned
    by this script. For user-provided local paths where the remote was renamed,
    the origin check will fail gracefully (returns False).
    """
    result = _run_git(["rev-parse", "HEAD"], cwd=str(clone_dir), check=False)
    if result.returncode != 0:
        return False

    if expected_repo_url:
        origin = _run_git(
            ["remote", "get-url", "origin"], cwd=str(clone_dir), check=False,
        )
        if origin.returncode != 0:
            return False
        if _normalize_git_url(origin.stdout.strip()) != _normalize_git_url(expected_repo_url):
            return False

    if ref:
        current = _run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(clone_dir), check=False,
        )
        current_branch = current.stdout.strip()
        if current_branch != ref:
            fetch = _run_git(
                ["fetch", "origin", ref], cwd=str(clone_dir), check=False,
            )
            if fetch.returncode != 0:
                return False
            checkout = _run_git(
                ["checkout", ref], cwd=str(clone_dir), check=False,
            )
            if checkout.returncode != 0:
                fallback = _run_git(
                    ["checkout", "FETCH_HEAD"], cwd=str(clone_dir), check=False,
                )
                if fallback.returncode != 0:
                    return False
    return True


def _write_source_yaml(base_path, repo, ref):
    """Write source.yaml for workflow resume."""
    source_file = Path(base_path) / "source.yaml"
    if source_file.exists():
        return  # Don't overwrite existing config
    lines = [f"repo: {repo}"]
    if ref:
        lines.append(f"ref: {ref}")
    source_file.write_text("\n".join(lines) + "\n")


def _success(repo_path, repo_url=None, ref=None, scope=None, discovered_repos=None):
    """Build a success result dict."""
    result = {
        "status": "resolved",
        "repo_path": str(repo_path),
        "repo_url": repo_url,
        "ref": ref,
        "scope": scope,
    }
    if discovered_repos:
        result["discovered_repos"] = discovered_repos
    return result


def resolve(args):
    """Main resolution logic. Returns a result dict."""
    base_path = Path(args.base_path)
    clone_dir = base_path / "code-repo"

    # Collect PR URLs from args
    pr_urls = args.pr or []

    # --- Priority 1: Explicit --repo flag ---
    if args.repo:
        repo_value = args.repo
        ref = None
        scope = None

        if _is_remote_url(repo_value):
            # If PRs provided, get the branch from the first PR
            if pr_urls:
                try:
                    _, pr_branch = _resolve_pr_info(pr_urls[0])
                    ref = pr_branch
                except subprocess.CalledProcessError as e:
                    print(
                        f"WARNING: Could not resolve PR branch from {pr_urls[0]}: {e.stderr}",
                        file=sys.stderr,
                    )

            # Clone or verify
            if clone_dir.exists():
                if not _verify_existing_clone(clone_dir, ref, expected_repo_url=repo_value):
                    return {"status": "error", "message": f"Existing clone at {clone_dir} is invalid or points to a different repo."}
            else:
                if not _clone_repo(repo_value, clone_dir, ref):
                    return {
                        "status": "error",
                        "message": f"Cannot clone {repo_value}. For private repos, ensure gh is authenticated.",
                    }

            _write_source_yaml(base_path, repo_value, ref)
            return _success(clone_dir, repo_url=repo_value, ref=ref, scope=scope)
        else:
            # Local path
            local = Path(repo_value)
            if not local.exists() or not local.is_dir():
                return {"status": "error", "message": f"Source repo path does not exist: {repo_value}"}
            return _success(local, ref=ref, scope=scope)

    # --- Priority 2: source.yaml ---
    source_config = _read_source_yaml(base_path)
    if source_config and source_config.get("repo"):
        repo_value = source_config["repo"]
        ref = source_config.get("ref")
        scope = source_config.get("scope")

        # PR overrides ref only
        if pr_urls:
            try:
                _, pr_branch = _resolve_pr_info(pr_urls[0])
                ref = pr_branch
            except subprocess.CalledProcessError:
                pass

        if _is_remote_url(repo_value):
            if clone_dir.exists():
                if not _verify_existing_clone(clone_dir, ref, expected_repo_url=repo_value):
                    return {"status": "error", "message": f"Existing clone at {clone_dir} is invalid or points to a different repo."}
            else:
                if not _clone_repo(repo_value, clone_dir, ref):
                    return {
                        "status": "error",
                        "message": f"Cannot clone {repo_value}.",
                    }
            return _success(clone_dir, repo_url=repo_value, ref=ref, scope=scope)
        else:
            local = Path(repo_value)
            if not local.exists() or not local.is_dir():
                return {"status": "error", "message": f"Source repo path does not exist: {repo_value}"}
            return _success(local, repo_url=repo_value, ref=ref, scope=scope)

    # --- Priority 3: PR-derived (--pr without --repo) ---
    if pr_urls:
        try:
            repo_url, pr_branch = _resolve_pr_info(pr_urls[0])
        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "message": f"Cannot resolve repo from PR {pr_urls[0]}: {e.stderr}",
            }

        if clone_dir.exists():
            if not _verify_existing_clone(clone_dir, pr_branch, expected_repo_url=repo_url):
                return {"status": "error", "message": f"Existing clone at {clone_dir} is invalid or points to a different repo."}
        else:
            if not _clone_repo(repo_url, clone_dir, pr_branch):
                return {
                    "status": "error",
                    "message": f"Cannot clone {repo_url}.",
                }

        _write_source_yaml(base_path, repo_url, pr_branch)
        return _success(clone_dir, repo_url=repo_url, ref=pr_branch)

    # --- Priority 4: Scan requirements for PRs ---
    if args.scan_requirements:
        repos = _scan_requirements_for_prs(base_path)

        if not repos:
            return {"status": "no_source"}

        # Select repo with most GitHub PRs (GitLab MRs require glab, not yet supported)
        github_repos = {
            slug: [pr for pr in prs if pr["type"] == "github"]
            for slug, prs in repos.items()
        }
        github_repos = {slug: prs for slug, prs in github_repos.items() if prs}

        if not github_repos:
            # Only GitLab MRs found — cannot resolve via gh CLI
            gitlab_slugs = list(repos.keys())
            return {
                "status": "no_source",
                "message": f"Only GitLab MRs found ({', '.join(gitlab_slugs)}). GitLab resolution not yet supported. Provide --repo manually.",
            }

        selected_slug = max(github_repos, key=lambda k: len(github_repos[k]))
        selected_prs = github_repos[selected_slug]
        first_pr_url = selected_prs[0]["url"]

        # Build discovered_repos summary for orchestrator logging (all providers)
        discovered = {slug: len(prs) for slug, prs in repos.items()}

        try:
            repo_url, pr_branch = _resolve_pr_info(first_pr_url)
        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "message": f"Cannot resolve repo from discovered PR {first_pr_url}: {e.stderr}",
            }

        if clone_dir.exists():
            if not _verify_existing_clone(clone_dir, pr_branch, expected_repo_url=repo_url):
                return {"status": "error", "message": f"Existing clone at {clone_dir} is invalid or points to a different repo."}
        else:
            if not _clone_repo(repo_url, clone_dir, pr_branch):
                return {
                    "status": "clone_failed",
                    "message": f"Could not clone {repo_url}. Code-evidence will be skipped.",
                    "repo_url": repo_url,
                }

        _write_source_yaml(base_path, repo_url, pr_branch)
        return _success(
            clone_dir, repo_url=repo_url, ref=pr_branch,
            discovered_repos=discovered,
        )

    # --- Priority 5: No source ---
    return {"status": "no_source"}


def main():
    parser = argparse.ArgumentParser(
        description="Resolve and clone/verify a source code repository"
    )
    parser.add_argument(
        "--base-path", required=True,
        help="Base output path (e.g., .claude/docs/proj-123)",
    )
    parser.add_argument(
        "--repo",
        help="Source repo URL or local path",
    )
    parser.add_argument(
        "--pr", action="append",
        help="PR/MR URL (repeatable)",
    )
    parser.add_argument(
        "--scan-requirements", action="store_true",
        help="Scan requirements.md for PR URLs (post-requirements discovery)",
    )
    args = parser.parse_args()

    result = resolve(args)

    json.dump(result, sys.stdout, indent=2)
    print()

    if result["status"] in ("error", "clone_failed"):
        sys.exit(1)
    elif result["status"] == "no_source":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
