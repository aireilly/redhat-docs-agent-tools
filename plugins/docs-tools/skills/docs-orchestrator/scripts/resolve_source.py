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

3. JIRA ticket discovery (auto-discover repo from ticket git links):
    python3 resolve_source.py --base-path .claude/docs/proj-123 \
        --ticket PROJ-123 --plugin-root /path/to/docs-tools

4. Scan requirements.md for PR URLs (post-requirements discovery):
    python3 resolve_source.py --base-path .claude/docs/proj-123 --scan-requirements

Output: JSON to stdout with the resolved source info, or an error status.

Exit codes:
    0 — success (source resolved, JSON on stdout)
    1 — error (message on stderr)
    2 — no source found (not an error; JSON with status "no_source" on stdout)

Prerequisites:
    - gh CLI (for GitHub PR resolution)
    - glab CLI (for GitLab MR resolution)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# PR/MR URL patterns
GITHUB_PR_RE = re.compile(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)")
GITLAB_MR_RE = re.compile(r"https?://gitlab\.[^/]+/(.+?)/-/merge_requests/(\d+)")

# Repo URL extraction patterns (for git_links that aren't PRs)
GITHUB_REPO_RE = re.compile(r"https?://github\.com/([^/]+/[^/]+?)(?:\.git)?(?:/.*)?$")
GITLAB_REPO_RE = re.compile(r"(https?://gitlab\.[^/]+/.+?)(?:\.git)?(?:/-/.*)?$")


def _is_remote_url(value):
    """Check if a value is a remote git URL (not a local path)."""
    return value.startswith(("https://", "git@", "ssh://"))


def _run_git(args, cwd=None, check=True):
    """Run a git command and return stdout."""
    result = subprocess.run(  # noqa: S603
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
    result = subprocess.run(  # noqa: S603
        ["gh"] + args,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, ["gh"] + args, result.stdout, result.stderr
        )
    return result.stdout.strip()


def _run_glab(args, check=True):
    """Run a glab CLI command and return stdout."""
    result = subprocess.run(  # noqa: S603
        ["glab"] + args,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, ["glab"] + args, result.stdout, result.stderr
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


def _repo_name_from_url(url):
    """Extract the repository name from a git URL."""
    return _normalize_git_url(url).split("/")[-1]


def _resolve_pr_info(pr_url):
    """Extract repo URL and branch from a GitHub PR or GitLab MR URL.

    Dispatches to gh CLI for GitHub PRs and glab CLI for GitLab MRs.
    Derives the clone URL from the PR/MR URL (base repo), not the
    head/source repository (which may be a fork).
    """
    if GITLAB_MR_RE.match(pr_url):
        return _resolve_mr_info(pr_url)

    match = GITHUB_PR_RE.match(pr_url)
    if match:
        repo_slug = match.group(1)
        repo_url = f"https://github.com/{repo_slug}.git"
    else:
        repo_url = _run_gh(
            [
                "pr",
                "view",
                pr_url,
                "--json",
                "url",
                "--jq",
                '.url | split("/pull/")[0] + ".git"',
            ]
        )

    pr_branch = _run_gh(
        [
            "pr",
            "view",
            pr_url,
            "--json",
            "headRefName",
            "--jq",
            ".headRefName",
        ]
    )
    return repo_url, pr_branch


def _resolve_mr_info(mr_url):
    """Extract repo URL and branch from a GitLab MR URL using glab CLI.

    Parses the project path and MR number from the URL, then uses
    glab mr view <number> -R <project> with GITLAB_HOST set for the
    correct instance.
    """
    import os
    from urllib.parse import urlparse

    match = GITLAB_MR_RE.match(mr_url)
    if not match:
        raise ValueError(f"Not a valid GitLab MR URL: {mr_url}")
    project_path = match.group(1)
    mr_number = match.group(2)
    hostname = urlparse(mr_url).hostname

    prev_host = os.environ.get("GITLAB_HOST")
    os.environ["GITLAB_HOST"] = f"https://{hostname}"
    try:
        mr_json = _run_glab(
            [
                "mr",
                "view",
                mr_number,
                "-R",
                project_path,
                "--output",
                "json",
            ]
        )
    finally:
        if prev_host is None:
            os.environ.pop("GITLAB_HOST", None)
        else:
            os.environ["GITLAB_HOST"] = prev_host

    mr_data = json.loads(mr_json)
    source_branch = mr_data.get("source_branch", "")

    base_url = mr_url.split("/-/merge_requests/")[0]
    repo_url = f"{base_url}.git"

    return repo_url, source_branch


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
        repos.setdefault(repo_slug, []).append(
            {
                "url": url,
                "number": int(pr_num),
                "type": "github",
            }
        )

    for match in GITLAB_MR_RE.finditer(content):
        repo_slug = match.group(1)
        mr_num = match.group(2)
        url = match.group(0)
        repos.setdefault(repo_slug, []).append(
            {
                "url": url,
                "number": int(mr_num),
                "type": "gitlab",
            }
        )

    return repos


def _extract_repo_url(link_url):
    """Extract a normalized repo URL from a GitHub/GitLab link.

    Handles PR URLs, commit URLs, file URLs, tree URLs, and plain repo URLs.
    Returns a normalized https repo URL (without .git), or None if unrecognized.
    """
    # GitHub PR
    match = GITHUB_PR_RE.match(link_url)
    if match:
        return f"https://github.com/{match.group(1)}"

    # GitLab MR
    match = GITLAB_MR_RE.match(link_url)
    if match:
        base = link_url.split("/-/merge_requests/")[0]
        return _normalize_git_url(base)

    # GitLab other paths (commits, tree, blob, etc.)
    match = GITLAB_REPO_RE.match(link_url)
    if match:
        return _normalize_git_url(match.group(1))

    # GitHub other paths (commits, tree, blob, actions, etc.)
    match = GITHUB_REPO_RE.match(link_url)
    if match:
        slug = match.group(1)
        # Exclude non-repo GitHub pages
        if slug.split("/")[0] in ("orgs", "settings", "marketplace", "topics"):
            return None
        return f"https://github.com/{slug}"

    return None


def _discover_from_jira(ticket, base_path, plugin_root):
    """Discover source repo(s) from JIRA ticket git_links and auto-discovered PRs.

    Calls jira_reader.py to fetch the ticket's remote links, extracts repo URLs,
    groups by repo, and selects the primary repo by reference count.

    Returns a result dict (same contract as resolve()).
    """
    jira_script = Path(plugin_root) / "skills" / "jira-reader" / "scripts" / "jira_reader.py"
    if not jira_script.exists():
        return {
            "status": "error",
            "message": f"jira_reader.py not found at {jira_script}",
        }

    # Fetch git_links from --issue
    git_links = []
    try:
        result = subprocess.run(  # noqa: S603
            ["python3", str(jira_script), "--issue", ticket],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            issue_data = json.loads(result.stdout)
            if isinstance(issue_data, list):
                issue_data = issue_data[0]
            git_links = issue_data.get("git_links", [])
    except (json.JSONDecodeError, subprocess.TimeoutExpired, IndexError):
        pass

    # Fetch auto_discovered_urls.pull_requests from --graph
    auto_prs = []
    try:
        result = subprocess.run(  # noqa: S603
            ["python3", str(jira_script), "--graph", ticket],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            graph_data = json.loads(result.stdout)
            auto_prs = graph_data.get("auto_discovered_urls", {}).get("pull_requests", [])
    except (json.JSONDecodeError, subprocess.TimeoutExpired):
        pass

    # Combine all discovered URLs (dedup)
    all_urls = list(dict.fromkeys(git_links + auto_prs))
    if not all_urls:
        return {"status": "no_source"}

    # Group by normalized repo URL and count references
    repo_counts = {}  # normalized_url -> {"url": canonical_url, "count": N, "pr_urls": [...]}
    for url in all_urls:
        repo_url = _extract_repo_url(url)
        if not repo_url:
            continue
        normalized = _normalize_git_url(repo_url)
        if normalized not in repo_counts:
            repo_counts[normalized] = {"url": repo_url, "count": 0, "pr_urls": []}
        repo_counts[normalized]["count"] += 1
        if GITHUB_PR_RE.match(url) or GITLAB_MR_RE.match(url):
            repo_counts[normalized]["pr_urls"].append(url)

    if not repo_counts:
        return {"status": "no_source"}

    # Sort by count descending
    ranked = sorted(repo_counts.values(), key=lambda r: r["count"], reverse=True)

    if len(ranked) == 1:
        winner = ranked[0]
    elif ranked[0]["count"] > ranked[1]["count"]:
        winner = ranked[0]
    else:
        # Tie — fail with candidates
        tied = [r for r in ranked if r["count"] == ranked[0]["count"]]
        candidates = ", ".join(r["url"] for r in tied)
        return {
            "status": "error",
            "message": (
                f"Multiple source repos discovered from JIRA ticket {ticket} "
                f"with equal reference counts ({ranked[0]['count']} each): {candidates}. "
                "Pass --source-code-repo <url> to select one."
            ),
        }

    # Resolve the winner
    if winner["pr_urls"]:
        result = _resolve_multiple_prs(winner["pr_urls"], base_path)
    else:
        result = _resolve_explicit_repos([winner["url"]], [], base_path)

    # Include all discovered repos in the result for logging
    if len(ranked) > 1 and result.get("status") == "resolved":
        result["discovered_repos"] = {
            _normalize_git_url(r["url"]): r["count"] for r in ranked
        }

    return result


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
            ["remote", "get-url", "origin"],
            cwd=str(clone_dir),
            check=False,
        )
        if origin.returncode != 0:
            return False
        if _normalize_git_url(origin.stdout.strip()) != _normalize_git_url(expected_repo_url):
            return False

    if ref:
        current = _run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(clone_dir),
            check=False,
        )
        current_branch = current.stdout.strip()
        if current_branch != ref:
            fetch = _run_git(
                ["fetch", "origin", ref],
                cwd=str(clone_dir),
                check=False,
            )
            if fetch.returncode != 0:
                return False
            checkout = _run_git(
                ["checkout", ref],
                cwd=str(clone_dir),
                check=False,
            )
            if checkout.returncode != 0:
                fallback = _run_git(
                    ["checkout", "FETCH_HEAD"],
                    cwd=str(clone_dir),
                    check=False,
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


def _resolve_multiple_prs(pr_urls, base_path):
    """Resolve and clone repos from a list of PR/MR URLs.

    Groups PRs by repo, clones each into code-repo/<repo_name>/,
    and returns a success result with primary + additional repos.
    """
    # Group PRs by normalized repo URL
    repo_groups = {}
    for url in pr_urls:
        try:
            repo_url, branch = _resolve_pr_info(url)
        except subprocess.CalledProcessError:
            continue
        normalized = _normalize_git_url(repo_url)
        if normalized not in repo_groups:
            repo_groups[normalized] = {"repo_url": repo_url, "ref": branch, "urls": []}
        repo_groups[normalized]["urls"].append(url)

    if not repo_groups:
        return {
            "status": "error",
            "message": "Cannot resolve repo from any of the provided PRs.",
        }

    resolved_repos = []
    errors = []
    for normalized, info in repo_groups.items():
        repo_url = info["repo_url"]
        ref = info["ref"]

        repo_name = _repo_name_from_url(repo_url)
        repo_clone_dir = base_path / "code-repo" / repo_name

        if repo_clone_dir.exists():
            if not _verify_existing_clone(repo_clone_dir, ref, expected_repo_url=repo_url):
                errors.append(f"Existing clone at {repo_clone_dir} is invalid.")
                continue
        else:
            if not _clone_repo(repo_url, repo_clone_dir, ref):
                errors.append(f"Could not clone {repo_url}.")
                continue

        resolved_repos.append(
            {
                "repo_path": str(repo_clone_dir),
                "repo_url": repo_url,
                "ref": ref,
            }
        )

    if not resolved_repos:
        return {
            "status": "error",
            "message": f"Could not clone any repos. Errors: {'; '.join(errors)}",
        }

    primary = resolved_repos[0]
    _write_source_yaml(base_path, primary["repo_url"], primary["ref"])

    discovered = {
        _normalize_git_url(info["repo_url"]): len(info["urls"]) for info in repo_groups.values()
    }

    result = _success(
        primary["repo_path"],
        repo_url=primary["repo_url"],
        ref=primary["ref"],
        discovered_repos=discovered if len(repo_groups) > 1 else None,
    )
    if len(resolved_repos) > 1:
        result["additional_repos"] = resolved_repos[1:]
    if errors:
        result["warnings"] = errors
    return result


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


def _resolve_explicit_repos(repo_values, pr_urls, base_path):
    """Resolve one or more explicit --repo values.

    Clones each remote repo into code-repo/<repo_name>/.
    For a single repo with PRs, the first PR's branch is checked out.
    Returns primary + additional repos when multiple are given.
    """
    resolved_repos = []
    errors = []

    for i, repo_value in enumerate(repo_values):
        ref = None

        if _is_remote_url(repo_value):
            clone_dir = base_path / "code-repo" / _repo_name_from_url(repo_value)

            # First repo gets the PR branch (if any)
            if i == 0 and pr_urls:
                try:
                    _, pr_branch = _resolve_pr_info(pr_urls[0])
                    ref = pr_branch
                except subprocess.CalledProcessError as e:
                    print(
                        f"WARNING: Could not resolve PR branch from {pr_urls[0]}: {e.stderr}",
                        file=sys.stderr,
                    )

            if clone_dir.exists():
                if not _verify_existing_clone(clone_dir, ref, expected_repo_url=repo_value):
                    errors.append(
                        f"Existing clone at {clone_dir} is invalid "
                        "or points to a different repo."
                    )
                    continue
            else:
                if not _clone_repo(repo_value, clone_dir, ref):
                    errors.append(
                        f"Cannot clone {repo_value}. "
                        "For private repos, ensure gh is authenticated."
                    )
                    continue

            resolved_repos.append({
                "repo_path": str(clone_dir),
                "repo_url": repo_value,
                "ref": ref,
            })
        else:
            local = Path(repo_value)
            if not local.exists() or not local.is_dir():
                errors.append(f"Source repo path does not exist: {repo_value}")
                continue
            resolved_repos.append({
                "repo_path": str(local),
                "repo_url": None,
                "ref": None,
            })

    if not resolved_repos:
        return {
            "status": "error",
            "message": f"Could not resolve any repos. Errors: {'; '.join(errors)}",
        }

    primary = resolved_repos[0]
    _write_source_yaml(base_path, primary.get("repo_url") or primary["repo_path"], primary["ref"])

    result = _success(
        primary["repo_path"],
        repo_url=primary.get("repo_url"),
        ref=primary["ref"],
    )
    if len(resolved_repos) > 1:
        result["additional_repos"] = resolved_repos[1:]
    if errors:
        result["warnings"] = errors
    return result


def resolve(args):
    """Main resolution logic. Returns a result dict."""
    base_path = Path(args.base_path)

    # Collect PR URLs from args
    pr_urls = args.pr or []

    # --- Priority 1: Explicit --repo flag ---
    if args.repo:
        return _resolve_explicit_repos(args.repo, pr_urls, base_path)

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
            clone_dir = base_path / "code-repo" / _repo_name_from_url(repo_value)
            if clone_dir.exists():
                if not _verify_existing_clone(clone_dir, ref, expected_repo_url=repo_value):
                    return {
                        "status": "error",
                        "message": (
                            f"Existing clone at {clone_dir} is invalid "
                            "or points to a different repo."
                        ),
                    }
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
                return {
                    "status": "error",
                    "message": f"Source repo path does not exist: {repo_value}",
                }
            return _success(local, repo_url=repo_value, ref=ref, scope=scope)

    # --- Priority 3: PR-derived (--pr without --repo) ---
    if pr_urls:
        return _resolve_multiple_prs(pr_urls, base_path)

    # --- Priority 4: JIRA ticket discovery ---
    ticket = getattr(args, "ticket", None)
    plugin_root = getattr(args, "plugin_root", None)
    if ticket and plugin_root:
        result = _discover_from_jira(ticket, base_path, plugin_root)
        if result["status"] != "no_source":
            return result

    # --- Priority 5: Scan requirements for PRs ---
    if args.scan_requirements:
        repos = _scan_requirements_for_prs(base_path)

        if not repos:
            return {"status": "no_source"}

        # Collect first PR URL from each discovered repo
        all_pr_urls = [prs[0]["url"] for prs in repos.values()]
        return _resolve_multiple_prs(all_pr_urls, base_path)

    # --- Priority 6: No source ---
    return {"status": "no_source"}


def main():
    parser = argparse.ArgumentParser(
        description="Resolve and clone/verify a source code repository"
    )
    parser.add_argument(
        "--base-path",
        required=True,
        help="Base output path (e.g., .claude/docs/proj-123)",
    )
    parser.add_argument(
        "--repo",
        nargs="+",
        help="Source repo URL(s) or local path(s), space-delimited",
    )
    parser.add_argument(
        "--pr",
        nargs="+",
        help="PR/MR URL(s), space-delimited",
    )
    parser.add_argument(
        "--ticket",
        help="JIRA ticket ID for auto-discovery of source repo from git links",
    )
    parser.add_argument(
        "--plugin-root",
        help="Plugin root directory (for locating jira_reader.py)",
    )
    parser.add_argument(
        "--scan-requirements",
        action="store_true",
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
