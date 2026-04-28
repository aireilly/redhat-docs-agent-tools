#!/usr/bin/env python3
"""Prepare a clean git branch from the latest upstream default branch.

Usage: python3 prepare_branch.py <ticket-id> --base-path <path> [--draft] [--repo-path <path>]
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)  # noqa: S603 S607
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticket", help="JIRA ticket ID")
    parser.add_argument("--base-path", required=True)
    parser.add_argument("--repo-path", default="")
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()

    ticket = args.ticket.upper()
    base = Path(args.base_path)
    out = base / "prepare-branch"
    out.mkdir(parents=True, exist_ok=True)
    cwd = args.repo_path or None

    def step_result(branch=None, based_on=None, skipped=False, reason=None):
        return {
            "schema_version": 1,
            "step": "prepare-branch",
            "ticket": ticket,
            "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "branch": branch,
            "based_on": based_on,
            "skipped": skipped,
            "skip_reason": reason,
        }

    def fatal(msg, branch=None, based_on=None):
        print(f"ERROR: {msg}", file=sys.stderr)
        write_json(out / "step-result.json", step_result(branch=branch, based_on=based_on))
        sys.exit(1)

    # Draft mode — skip
    if args.draft:
        (out / "branch-info.md").write_text(
            "# Branch Preparation — Skipped\nDraft mode: no branch created.\n"
        )
        write_json(out / "step-result.json", step_result(skipped=True, reason="draft"))
        print("Draft mode — skipped branch creation.")
        return

    # Repo-path mode — skip (branch managed externally)
    if args.repo_path:
        (out / "branch-info.md").write_text(
            "# Branch Preparation — Skipped\nRepo-path mode: branch managed externally.\n"
        )
        write_json(out / "step-result.json", step_result(skipped=True, reason="repo-path"))
        print("Repo-path mode — skipped branch creation.")
        return

    # Detect default remote (prefer upstream for fork workflows)
    rc, remotes_out, _ = git("remote", cwd=cwd)
    if rc != 0 or not remotes_out:
        fatal("No git remotes found.")

    remotes = remotes_out.splitlines()
    default_remote = "upstream" if "upstream" in remotes else remotes[0]

    # Detect default branch locally (no network call)
    default_branch = None
    for candidate in ("main", "master"):
        rc, _, _ = git("rev-parse", "--verify", f"{default_remote}/{candidate}", cwd=cwd)
        if rc == 0:
            default_branch = candidate
            break

    if default_branch is None:
        rc, ref, _ = git("symbolic-ref", f"refs/remotes/{default_remote}/HEAD", cwd=cwd)
        if rc == 0 and ref:
            default_branch = ref.rsplit("/", 1)[-1]

    if default_branch is None:
        fatal(f"Could not detect default branch for '{default_remote}'.")

    # Check for uncommitted changes
    rc, _, _ = git("diff-index", "--quiet", "HEAD", "--", cwd=cwd)
    if rc != 0:
        fatal("Working tree has uncommitted changes. Stash or commit them first.")

    # Fetch latest from remote
    rc, _, err = git("fetch", default_remote, default_branch, cwd=cwd)
    if rc != 0:
        print(f"WARNING: git fetch failed ({err}). Continuing with local copy.", file=sys.stderr)

    # Create or switch to branch
    branch_name = ticket.lower()
    based_on = f"{default_remote}/{default_branch}"

    rc, _, _ = git("rev-parse", "--verify", f"refs/heads/{branch_name}", cwd=cwd)
    if rc == 0:
        print(f"Branch '{branch_name}' already exists — switching to it.")
        rc, _, err = git("checkout", branch_name, cwd=cwd)
        if rc != 0:
            fatal(
                f"git checkout {branch_name} failed: {err}", branch=branch_name, based_on=based_on
            )
    else:
        print(f"Creating branch '{branch_name}' from '{based_on}'.")
        rc, _, err = git("checkout", "-b", branch_name, based_on, cwd=cwd)
        if rc != 0:
            fatal(f"git checkout -b failed: {err}", based_on=based_on)

    # Write outputs
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (out / "branch-info.md").write_text(
        f"# Branch Preparation\n\n"
        f"- **Branch**: `{branch_name}`\n"
        f"- **Based on**: `{based_on}`\n"
        f"- **Created at**: {timestamp}\n"
    )
    write_json(out / "step-result.json", step_result(branch=branch_name, based_on=based_on))
    print(f"Branch prepared: {branch_name} from {based_on}")


if __name__ == "__main__":
    main()
