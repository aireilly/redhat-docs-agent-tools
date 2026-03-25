#!/usr/bin/env python3
"""
Create PR/MR - Creates a pull request (GitHub) or merge request (GitLab)
in the docs repository with documentation changes.

Reads branch info and plan from the workflow output to construct the PR/MR
title and description. Auto-detects the platform (GitHub/GitLab) from the
git remote URL.

Usage:
    python create_pr.py \
        --base-path .claude/docs/my-service/a1b2c3d-e4f5g6h \
        --identifier my-service/a1b2c3d-e4f5g6h \
        [--remote upstream]

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
import subprocess
import sys
from urllib.parse import urlparse

# Import shared utilities from git_pr_reader
sys.path.insert(
    0,
    str(pathlib.Path(__file__).resolve().parent.parent.parent / "git-pr-reader" / "scripts"),
)
from git_pr_reader import load_env_file  # noqa: E402

try:
    from github import Github, Auth
except ImportError:
    Github = None  # type: ignore[assignment,misc]
    Auth = None  # type: ignore[assignment,misc]

try:
    from gitlab import Gitlab
except ImportError:
    Gitlab = None  # type: ignore[assignment,misc]


def detect_remote_url(remote: str = "upstream") -> str:
    """Detect the remote URL for the docs repository."""
    for r in [remote, "origin"]:
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", r],
                capture_output=True, text=True, check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            continue
    raise RuntimeError(f"No git remote found (tried '{remote}' and 'origin')")


def parse_remote_url(url: str) -> dict:
    """Parse a git remote URL into platform, owner, and repo."""
    # SSH format: git@github.com:owner/repo.git
    ssh_match = re.match(r"git@([^:]+):(.+?)(?:\.git)?$", url)
    if ssh_match:
        host = ssh_match.group(1)
        path = ssh_match.group(2)
    else:
        # HTTPS format
        parsed = urlparse(url)
        host = parsed.hostname or ""
        path = parsed.path.lstrip("/").removesuffix(".git")

    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from remote URL: {url}")

    owner = "/".join(parts[:-1])
    repo = parts[-1]

    if "github" in host:
        platform = "github"
    elif "gitlab" in host:
        platform = "gitlab"
    else:
        raise ValueError(f"Cannot determine platform from host: {host}")

    return {"platform": platform, "host": host, "owner": owner, "repo": repo}


def read_branch_info(base_path: str) -> dict:
    """Read branch info from the prepare-branch step output."""
    branch_file = os.path.join(base_path, "prepare-branch", "branch-info.md")
    if not os.path.exists(branch_file):
        raise FileNotFoundError(f"Branch info not found at {branch_file}")

    with open(branch_file) as f:
        content = f.read()

    # Extract branch name from the markdown
    branch_match = re.search(r"\*\*Branch\*\*:\s*`?([^\s`]+)`?", content)
    if not branch_match:
        # Try alternative format
        branch_match = re.search(r"branch[:\s]+`?([a-z0-9_/-]+)`?", content, re.IGNORECASE)

    if not branch_match:
        raise ValueError(f"Cannot extract branch name from {branch_file}")

    return {"branch": branch_match.group(1), "raw": content}


def read_plan(base_path: str) -> str:
    """Read the documentation plan for PR description content."""
    plan_file = os.path.join(base_path, "planning", "plan.md")
    if os.path.exists(plan_file):
        with open(plan_file) as f:
            return f.read()
    return ""


def read_requirements(base_path: str) -> str:
    """Read the requirements summary for PR description context."""
    req_file = os.path.join(base_path, "requirements", "requirements.md")
    if os.path.exists(req_file):
        with open(req_file) as f:
            content = f.read()
        # Extract just the summary section if present
        summary_match = re.search(
            r"## Summary\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL,
        )
        if summary_match:
            return summary_match.group(1).strip()
    return ""


def detect_default_branch(remote: str = "upstream") -> str:
    """Detect the default branch of the remote."""
    for r in [remote, "origin"]:
        try:
            result = subprocess.run(
                ["git", "remote", "show", r],
                capture_output=True, text=True, check=True,
            )
            match = re.search(r"HEAD branch:\s*(\S+)", result.stdout)
            if match:
                return match.group(1)
        except subprocess.CalledProcessError:
            continue
    return "main"


def build_pr_description(identifier: str, plan: str, requirements_summary: str) -> str:
    """Build the PR/MR description from workflow outputs."""
    lines = [
        "## Documentation changes",
        "",
        f"Generated by docs-workflow for `{identifier}`.",
        "",
    ]

    if requirements_summary:
        lines.extend([
            "### Requirements summary",
            "",
            requirements_summary,
            "",
        ])

    if plan:
        # Include the plan but truncate if very long
        max_plan_len = 3000
        if len(plan) > max_plan_len:
            plan = plan[:max_plan_len] + "\n\n*[Plan truncated — see full plan in workflow output]*"
        lines.extend([
            "### Documentation plan",
            "",
            plan,
            "",
        ])

    lines.extend([
        "---",
        "*This PR was created automatically by the docs-workflow pipeline.*",
    ])

    return "\n".join(lines)


def create_github_pr(
    owner: str, repo: str, branch: str, base: str,
    title: str, body: str,
) -> dict:
    """Create a GitHub pull request."""
    if Github is None:
        raise ImportError("PyGithub is required: python3 -m pip install PyGithub")

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set")

    g = Github(auth=Auth.Token(token))
    gh_repo = g.get_repo(f"{owner}/{repo}")
    pr = gh_repo.create_pull(title=title, body=body, head=branch, base=base)

    return {
        "platform": "github",
        "url": pr.html_url,
        "number": pr.number,
        "title": pr.title,
        "branch": branch,
        "base": base,
    }


def create_gitlab_mr(
    host: str, owner: str, repo: str, branch: str, base: str,
    title: str, body: str,
) -> dict:
    """Create a GitLab merge request."""
    if Gitlab is None:
        raise ImportError("python-gitlab is required: python3 -m pip install python-gitlab")

    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        raise RuntimeError("GITLAB_TOKEN not set")

    gl = Gitlab(f"https://{host}", private_token=token)
    project_path = f"{owner}/{repo}"
    project = gl.projects.get(project_path)
    mr = project.mergerequests.create({
        "source_branch": branch,
        "target_branch": base,
        "title": title,
        "description": body,
    })

    return {
        "platform": "gitlab",
        "url": mr.web_url,
        "number": mr.iid,
        "title": mr.title,
        "branch": branch,
        "base": base,
    }


def write_output(base_path: str, result: dict) -> str:
    """Write the PR/MR info to the output file."""
    output_dir = os.path.join(base_path, "create-pr")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "pr-info.md")

    platform_label = "Pull Request" if result["platform"] == "github" else "Merge Request"

    content = f"""# {platform_label} Created

**URL**: {result["url"]}
**Number**: #{result["number"]}
**Title**: {result["title"]}
**Branch**: `{result["branch"]}` -> `{result["base"]}`
**Platform**: {result["platform"]}
"""

    with open(output_file, "w") as f:
        f.write(content)

    return output_file


def main():
    parser = argparse.ArgumentParser(description="Create PR/MR for documentation changes")
    parser.add_argument("--base-path", required=True, help="Base output path")
    parser.add_argument("--identifier", required=True, help="Workflow identifier")
    parser.add_argument("--remote", default="upstream", help="Git remote name (default: upstream)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    load_env_file()

    # Read workflow outputs
    branch_info = read_branch_info(args.base_path)
    branch = branch_info["branch"]
    plan = read_plan(args.base_path)
    requirements_summary = read_requirements(args.base_path)

    # Detect remote and platform
    remote_url = detect_remote_url(args.remote)
    remote_info = parse_remote_url(remote_url)
    default_branch = detect_default_branch(args.remote)

    # Build PR content
    title = f"docs: {args.identifier}"
    body = build_pr_description(args.identifier, plan, requirements_summary)

    # Create PR/MR
    if remote_info["platform"] == "github":
        result = create_github_pr(
            owner=remote_info["owner"],
            repo=remote_info["repo"],
            branch=branch,
            base=default_branch,
            title=title,
            body=body,
        )
    else:
        result = create_gitlab_mr(
            host=remote_info["host"],
            owner=remote_info["owner"],
            repo=remote_info["repo"],
            branch=branch,
            base=default_branch,
            title=title,
            body=body,
        )

    # Write output
    output_file = write_output(args.base_path, result)

    if args.json:
        result["output_file"] = output_file
        print(json.dumps(result, indent=2))
    else:
        platform_label = "PR" if result["platform"] == "github" else "MR"
        print(f"{platform_label} created: {result['url']}")
        print(f"Output written to: {output_file}")


if __name__ == "__main__":
    main()
