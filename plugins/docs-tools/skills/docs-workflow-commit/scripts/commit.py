#!/usr/bin/env python3
"""Commit manifest-listed files and push the feature branch.

Usage: python3 commit.py <ticket-id> --base-path <path> [--repo-path <path>] [--draft]
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Git helper
# ---------------------------------------------------------------------------


def git(*args, repo_dir=None):
    """Run a git command and return stripped stdout."""
    cmd = ["git"]
    if repo_dir:
        cmd += ["-C", str(repo_dir)]
    cmd += list(args)
    result = subprocess.run(  # noqa: S603 S607
        cmd, capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ---------------------------------------------------------------------------
# JSON output helpers
# ---------------------------------------------------------------------------


def write_commit_info(output_dir, branch, commit_sha, files, platform, repo_url, pushed):
    path = output_dir / "commit-info.json"
    path.write_text(
        json.dumps(
            {
                "branch": branch or None,
                "commit_sha": commit_sha or None,
                "files_committed": files,
                "platform": platform or None,
                "repo_url": repo_url or None,
                "pushed": pushed,
            },
            indent=2,
        )
        + "\n"
    )


def write_step_result(output_dir, ticket, commit_sha, branch, pushed, skipped, skip_reason=None):
    path = output_dir / "step-result.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "step": "commit",
                "ticket": ticket,
                "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "commit_sha": commit_sha or None,
                "branch": branch or None,
                "pushed": pushed,
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


def detect_platform(repo_url):
    if not repo_url:
        return "unknown"
    url_lower = repo_url.lower()
    if "github.com" in url_lower:
        return "github"
    if "gitlab" in url_lower:
        return "gitlab"
    return "unknown"


def read_json(path):
    return json.loads(Path(path).read_text())


def read_manifest_from_sidecar(sidecar_path, repo_dir):
    """Extract file list from writing step-result.json."""
    sidecar = read_json(sidecar_path)
    repo_prefix = str(repo_dir)
    return [f for f in sidecar.get("files", []) if f.startswith(repo_prefix)]


def read_manifest_from_index(index_path, repo_dir):
    """Extract file paths from _index.md manifest table."""
    repo_prefix = re.escape(str(repo_dir))
    pattern = rf"\|\s*`?({repo_prefix}\S+?)`?\s*(?:\||$)"
    files = []
    for line in Path(index_path).read_text().splitlines():
        files.extend(re.findall(pattern, line))
    return files


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
    ticket_lower = args.ticket.lower()
    base_path = Path(args.base_path)
    output_dir = base_path / "commit"
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Draft mode: skip ---
    if args.draft:
        write_commit_info(output_dir, "", "", [], "", "", False)
        write_step_result(output_dir, ticket, "", "", False, True, "draft")
        print("Draft mode — skipped committing.")
        return

    # --- Resolve repo context ---
    resolve_dir = args.repo_path or None
    rc, _, _ = git("rev-parse", "--git-dir", repo_dir=resolve_dir)
    if rc != 0:
        msg = f"ERROR: {resolve_dir or 'current directory'} is not a git repository."
        print(msg, file=sys.stderr)
        sys.exit(1)

    rc, repo_dir, err = git("rev-parse", "--show-toplevel", repo_dir=resolve_dir)
    if rc != 0 or not repo_dir:
        print(f"ERROR: Could not determine repository root: {err}", file=sys.stderr)
        sys.exit(1)

    rc, branch, err = git("rev-parse", "--abbrev-ref", "HEAD", repo_dir=resolve_dir)
    if rc != 0 or not branch:
        print(f"ERROR: Could not determine current branch: {err}", file=sys.stderr)
        sys.exit(1)

    rc, repo_url, err = git("remote", "get-url", "origin", repo_dir=resolve_dir)
    if rc != 0 or not repo_url:
        print(f"ERROR: Could not get remote URL for 'origin': {err}", file=sys.stderr)
        sys.exit(1)

    platform = detect_platform(repo_url)

    print(f"Repo:     {repo_dir}")
    print(f"Branch:   {branch}")
    print(f"Platform: {platform}")
    print(f"Remote:   {repo_url}")

    # --- Safety checks ---
    if branch in ("main", "master"):
        print(
            f"ERROR: Refusing to push to '{branch}'. All pushes must go to feature branches.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Read manifest ---
    sidecar_path = base_path / "writing" / "step-result.json"
    manifest_path = base_path / "writing" / "_index.md"
    repo_dir_abs = str(Path(repo_dir).resolve())

    if sidecar_path.exists():
        print("Reading file list from step-result.json")
        manifest_files = read_manifest_from_sidecar(sidecar_path, repo_dir_abs)
    elif manifest_path.exists():
        print("Reading file list from manifest (no step-result.json found)")
        manifest_files = read_manifest_from_index(manifest_path, repo_dir_abs)
    else:
        print("No manifest or step-result.json found.")
        write_commit_info(output_dir, branch, "", [], platform, repo_url, False)
        write_step_result(output_dir, ticket, "", branch, False, True, "no_changes")
        return

    if not manifest_files:
        print(f"No files found in manifest under {repo_dir_abs}.")
        write_commit_info(output_dir, branch, "", [], platform, repo_url, False)
        write_step_result(output_dir, ticket, "", branch, False, True, "no_changes")
        return

    # --- Stage manifest files ---
    staged_files = []
    for filepath in manifest_files:
        if Path(filepath).is_file():
            rc, _, err = git("add", filepath, repo_dir=repo_dir_abs)
            if rc != 0:
                print(f"WARNING: failed to stage {filepath}: {err}", file=sys.stderr)
                continue
            prefix = repo_dir_abs + "/"
            rel = filepath.removeprefix(prefix) if filepath.startswith(prefix) else filepath
            staged_files.append(rel)
        else:
            print(
                f"WARNING: Manifest lists {filepath} but file does not exist. Skipping.",
                file=sys.stderr,
            )

    # Check if anything was actually staged
    rc, _, _ = git("diff", "--cached", "--quiet", repo_dir=repo_dir_abs)
    if not staged_files or rc == 0:
        print("No changes to commit.")
        write_commit_info(output_dir, branch, "", [], platform, repo_url, False)
        write_step_result(output_dir, ticket, "", branch, False, True, "no_changes")
        return

    # --- Commit ---
    files_block = "\n".join(f"  - {f}" for f in staged_files)
    commit_msg = (
        f"docs({ticket_lower}): add generated documentation\n\n"
        f"Files:\n{files_block}\n\n"
        f"Generated by docs-pipeline for {ticket}"
    )

    rc, out, err = git("commit", "-m", commit_msg, repo_dir=repo_dir_abs)
    if rc != 0:
        print(f"ERROR: git commit failed: {err}", file=sys.stderr)
        sys.exit(1)
    print(out)

    _, commit_sha, _ = git("rev-parse", "HEAD", repo_dir=repo_dir_abs)
    print(f"Committed: {commit_sha}")

    # --- Push ---
    git("fetch", "origin", branch, repo_dir=repo_dir_abs)

    rc, out, err = git("push", "--force-with-lease", "-u", "origin", branch, repo_dir=repo_dir_abs)
    if rc == 0:
        print(f"Pushed branch '{branch}' to origin")
        write_commit_info(output_dir, branch, commit_sha, staged_files, platform, repo_url, True)
        write_step_result(output_dir, ticket, commit_sha, branch, True, False)
    else:
        print(
            f"ERROR: Push failed. Branch committed locally but not pushed.\n{err}",
            file=sys.stderr,
        )
        write_commit_info(output_dir, branch, commit_sha, staged_files, platform, repo_url, False)
        write_step_result(output_dir, ticket, commit_sha, branch, False, False)
        sys.exit(1)

    print(f"Wrote {output_dir}/commit-info.json")


if __name__ == "__main__":
    main()
