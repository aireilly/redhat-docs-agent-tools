#!/usr/bin/env python3
"""Create or find an existing MR/PR for the published docs branch.

Usage: python3 create_mr.py <ticket-id> --base-path <path> [--repo-path <path>] [--draft]
Dependencies: python-gitlab (for GitLab), PyGithub (for GitHub)
"""

import argparse
import configparser
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from github import Auth, Github, GithubException
except ImportError:
    Github = None  # type: ignore[assignment,misc]
    Auth = None  # type: ignore[assignment,misc]
    GithubException = Exception  # type: ignore[assignment,misc]

try:
    from gitlab import Gitlab
except ImportError:
    Gitlab = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


def load_env_file():
    """Load environment variables from ~/.env file."""
    env_file = Path.home() / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                    value = value[1:-1]
                os.environ.setdefault(key.strip(), value)


# ---------------------------------------------------------------------------
# JSON output helpers
# ---------------------------------------------------------------------------


def write_mr_info(output_dir, platform, url, action, title=None):
    path = output_dir / "mr-info.json"
    path.write_text(
        json.dumps(
            {
                "platform": platform,
                "url": url,
                "action": action,
                "title": title or None,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Wrote {path}")


def write_step_result(output_dir, ticket, url, action, platform, skipped, skip_reason=None):
    path = output_dir / "step-result.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "step": "create-mr",
                "ticket": ticket,
                "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "url": url,
                "action": action,
                "platform": platform,
                "skipped": skipped,
                "skip_reason": skip_reason or None,
            },
            indent=2,
        )
        + "\n"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_url(url):
    """Convert SSH git remote URLs to HTTPS."""
    m = re.match(r"ssh://(?:[^@]+@)?([^:/]+)(?::\d+)?/(.+?)(?:\.git)?$", url)
    if m:
        return f"https://{m.group(1)}/{m.group(2)}"
    m = re.match(r"git@([^:]+):(.+?)(?:\.git)?$", url)
    if m:
        return f"https://{m.group(1)}/{m.group(2)}"
    return re.sub(r"\.git$", "", url)


def read_json(path):
    return json.loads(Path(path).read_text())


def build_title(base_path, ticket):
    """Build MR/PR title from sidecar or requirements heading."""
    sidecar = base_path / "requirements" / "step-result.json"
    if sidecar.exists():
        title = read_json(sidecar).get("title", "")
        if title:
            return title[:80]

    req_file = base_path / "requirements" / "requirements.md"
    if req_file.exists():
        for line in req_file.read_text().splitlines():
            m = re.match(r"^#+\s+(.+)", line.strip())
            if m:
                heading = re.sub(
                    rf"^{re.escape(ticket)}\s*[-:]\s*",
                    "",
                    m.group(1),
                    flags=re.IGNORECASE,
                )
                if heading:
                    return heading[:80]

    return "generated documentation"


def detect_fork_local(project_path, repo_path):
    """Detect fork via local git remotes (no API call needed)."""
    resolve_dir = repo_path or os.getcwd()
    git_config = Path(resolve_dir) / ".git" / "config"
    if not git_config.exists():
        return ""
    try:
        cfg = configparser.ConfigParser()
        cfg.read(git_config)
        upstream_url = cfg.get('remote "upstream"', "url")
    except (configparser.NoSectionError, configparser.NoOptionError):
        return ""

    upstream_path = re.sub(r"https?://[^/]+/", "", normalize_url(upstream_url))
    if upstream_path and upstream_path != project_path:
        print(f"Detected fork via local remotes: origin={project_path}, upstream={upstream_path}")
        return upstream_path
    return ""


# ---------------------------------------------------------------------------
# GitLab backend
# ---------------------------------------------------------------------------


class GitLabBackend:
    def __init__(self, host, token):
        if Gitlab is None:
            print(
                "ERROR: python-gitlab is required. Install it with:\n"
                "  python3 -m pip install python-gitlab",
                file=sys.stderr,
            )
            sys.exit(1)
        if not token:
            print(
                "ERROR: GITLAB_TOKEN is required. Set it in ~/.env or your environment.",
                file=sys.stderr,
            )
            sys.exit(1)
        self.gl = Gitlab(url=host, private_token=token, ssl_verify=True)

    def detect_fork(self, project_path):
        """Query GitLab API for fork parent."""
        try:
            project = self.gl.projects.get(project_path)
            parent = getattr(project, "forked_from_project", None)
            if parent:
                upstream = parent["path_with_namespace"]
                print(f"Detected fork via API: {project_path} -> {upstream}")
                return upstream
        except Exception as e:
            print(f"WARNING: GitLab API fork detection failed: {e}", file=sys.stderr)
        return ""

    def find_existing_mr(self, project_path, branch, head_project=""):
        """Find an open MR from the given branch."""
        try:
            project = self.gl.projects.get(project_path)
            filters = {"source_branch": branch, "state": "opened"}
            if head_project:
                fork = self.gl.projects.get(head_project)
                filters["source_project_id"] = fork.id
            mrs = project.mergerequests.list(**filters)
            if mrs:
                return mrs[0].web_url
        except Exception as e:
            print(f"WARNING: Could not check for existing MRs: {e}", file=sys.stderr)
        return ""

    def create_mr(self, project_path, head_project, branch, default_branch, title, description):
        """Create a GitLab MR. For cross-fork, sets source_project_id."""
        upstream = self.gl.projects.get(project_path)
        mr_data = {
            "source_branch": branch,
            "target_branch": default_branch,
            "title": title,
            "description": description,
        }
        if head_project:
            fork = self.gl.projects.get(head_project)
            mr_data["source_project_id"] = fork.id
        mr = upstream.mergerequests.create(mr_data)
        return mr.web_url


# ---------------------------------------------------------------------------
# GitHub backend
# ---------------------------------------------------------------------------


class GitHubBackend:
    def __init__(self, token):
        if Github is None:
            print(
                "ERROR: PyGithub is required. Install it with:\n  python3 -m pip install PyGithub",
                file=sys.stderr,
            )
            sys.exit(1)
        if not token:
            print(
                "ERROR: GITHUB_TOKEN is required. Set it in ~/.env or your environment.",
                file=sys.stderr,
            )
            sys.exit(1)
        self.gh = Github(auth=Auth.Token(token))

    def find_existing_pr(self, owner_repo, branch):
        """Find an open PR from the given branch."""
        try:
            repo = self.gh.get_repo(owner_repo)
            if repo.fork and repo.parent:
                target = repo.parent
                head = f"{repo.owner.login}:{branch}"
            else:
                target = repo
                head = branch
            prs = target.get_pulls(head=head, state="open")
            for pr in prs:
                return pr.html_url
        except GithubException as e:
            print(f"WARNING: Could not check for existing PRs: {e}", file=sys.stderr)
        return ""

    def create_pr(self, owner_repo, branch, default_branch, title, description):
        """Create a GitHub PR. Handles fork relationships automatically."""
        repo = self.gh.get_repo(owner_repo)

        if repo.fork and repo.parent:
            upstream = repo.parent
            head = f"{repo.owner.login}:{branch}"
            print(f"Cross-fork PR: {repo.full_name} -> {upstream.full_name}")
            pr = upstream.create_pull(title=title, body=description, head=head, base=default_branch)
        else:
            pr = repo.create_pull(title=title, body=description, head=branch, base=default_branch)
        return pr.html_url


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticket", help="JIRA ticket ID")
    parser.add_argument("--base-path", required=True)
    parser.add_argument("--repo-path", default="")
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()

    ticket = args.ticket.upper()
    base_path = Path(args.base_path)
    output_dir = base_path / "create-mr"
    output_dir.mkdir(parents=True, exist_ok=True)
    platform = "unknown"

    # --- Draft mode: skip ---
    if args.draft:
        write_mr_info(output_dir, platform, None, "skipped")
        write_step_result(output_dir, ticket, None, "skipped", platform, True, "draft")
        print("Draft mode — skipped MR/PR creation.")
        return

    # --- Read commit-info.json ---
    commit_info_path = base_path / "commit" / "commit-info.json"
    if not commit_info_path.exists():
        print(f"No commit-info.json found at {commit_info_path}. Nothing to do.")
        write_mr_info(output_dir, platform, None, "skipped")
        write_step_result(output_dir, ticket, None, "skipped", platform, True, "not_pushed")
        return

    commit_info = read_json(commit_info_path)

    if not commit_info.get("pushed"):
        print("commit-info.json has pushed=false. Skipping MR/PR creation.")
        platform = commit_info.get("platform", "unknown")
        write_mr_info(output_dir, platform, None, "skipped")
        write_step_result(output_dir, ticket, None, "skipped", platform, True, "not_pushed")
        return

    # --- Resolve context ---
    branch = commit_info.get("branch", "")
    platform = commit_info.get("platform", "unknown")
    repo_url = commit_info.get("repo_url", "")
    default_branch = "main"

    repo_info_path = base_path / "repo-info.json"
    if repo_info_path.exists():
        default_branch = read_json(repo_info_path).get("default_branch", "main")

    if not repo_url or not branch:
        print(
            "ERROR: commit-info.json has pushed=true but is missing branch or repo_url.",
            file=sys.stderr,
        )
        sys.exit(1)

    repo_url = normalize_url(repo_url)
    print(f"Platform: {platform}")
    print(f"Repo URL: {repo_url}")
    print(f"Branch:   {branch} -> {default_branch}")

    # --- Load credentials ---
    load_env_file()

    # --- Build title and description ---
    summary = build_title(base_path, ticket)
    title = f"docs({ticket}): {summary}"

    files = commit_info.get("files_committed", [])
    files_block = "\n".join(f"- `{f}`" for f in files)

    description = (
        f"Documentation generated by the docs pipeline.\n\n"
        f"**JIRA ticket:** {ticket}\n"
        f"**Branch:** {branch}\n"
        f"**Target:** {default_branch}"
    )
    if files_block:
        description += f"\n\n**Files:**\n{files_block}"

    # --- Platform dispatch ---
    if platform == "gitlab":
        _handle_gitlab(
            args, output_dir, ticket, repo_url, branch, default_branch, title, description, platform
        )
    elif platform == "github":
        _handle_github(
            output_dir, ticket, repo_url, branch, default_branch, title, description, platform
        )
    else:
        print(f"ERROR: Unknown platform '{platform}'. Cannot create MR/PR.", file=sys.stderr)
        write_mr_info(output_dir, platform, None, "skipped")
        write_step_result(output_dir, ticket, None, "skipped", platform, True, "unknown_platform")
        sys.exit(1)


def _handle_gitlab(
    args, output_dir, ticket, repo_url, branch, default_branch, title, description, platform
):
    project_path = re.sub(r"https?://[^/]+/", "", repo_url)
    host_match = re.match(r"(https?://[^/]+)", repo_url)
    host = host_match.group(1) if host_match else "https://gitlab.com"
    token = os.environ.get("GITLAB_TOKEN")

    backend = GitLabBackend(host, token)

    # Fork detection: local remotes first, API fallback
    upstream = detect_fork_local(project_path, args.repo_path)
    if not upstream:
        upstream = backend.detect_fork(project_path)

    head_project = ""
    if upstream:
        head_project = project_path
        project_path = upstream
        print(f"Cross-fork MR: {head_project} -> {project_path}")

    # Check for existing MR
    existing = backend.find_existing_mr(project_path, branch, head_project)
    if existing:
        print(f"Found existing MR: {existing}")
        write_mr_info(output_dir, platform, existing, "found_existing", title)
        write_step_result(output_dir, ticket, existing, "found_existing", platform, False)
        return

    # Create MR
    try:
        mr_url = backend.create_mr(
            project_path, head_project, branch, default_branch, title, description
        )
    except Exception as e:
        print(f"ERROR: Failed to create MR: {e}", file=sys.stderr)
        write_mr_info(output_dir, platform, None, "skipped", title)
        write_step_result(output_dir, ticket, None, "skipped", platform, True, "create_failed")
        sys.exit(1)

    print(f"Created MR: {mr_url}")
    write_mr_info(output_dir, platform, mr_url, "created", title)
    write_step_result(output_dir, ticket, mr_url, "created", platform, False)


def _handle_github(
    output_dir, ticket, repo_url, branch, default_branch, title, description, platform
):
    owner_repo = re.sub(r"https?://github\.com/", "", repo_url)
    token = os.environ.get("GITHUB_TOKEN")

    backend = GitHubBackend(token)

    # Check for existing PR
    existing = backend.find_existing_pr(owner_repo, branch)
    if existing:
        print(f"Found existing PR: {existing}")
        write_mr_info(output_dir, platform, existing, "found_existing", title)
        write_step_result(output_dir, ticket, existing, "found_existing", platform, False)
        return

    # Create PR
    try:
        pr_url = backend.create_pr(owner_repo, branch, default_branch, title, description)
    except Exception as e:
        print(f"ERROR: Failed to create PR: {e}", file=sys.stderr)
        write_mr_info(output_dir, platform, None, "skipped", title)
        write_step_result(output_dir, ticket, None, "skipped", platform, True, "create_failed")
        sys.exit(1)

    print(f"Created PR: {pr_url}")
    write_mr_info(output_dir, platform, pr_url, "created", title)
    write_step_result(output_dir, ticket, pr_url, "created", platform, False)


if __name__ == "__main__":
    main()
