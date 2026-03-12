#!/usr/bin/env python3
"""
Batch runner for jtbd-workflow-topicmap skill.

Processes large lists of books by splitting them into groups
and invoking the Claude Code CLI for each group.

Usage:
    python batch-runner.py \
        --repo ~/Documents/openshift-docs \
        --books-file books.txt \
        --distro openshift-enterprise \
        --batch-size 5

The script:
- Reads the books file and splits into groups of --batch-size
- Invokes `claude` with the /jtbd-workflow-topicmap skill for each group
- Tracks progress in a state file for resume capability
- Reports results at the end
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


STATE_FILE = ".batch-runner-topicmap-state.json"


def load_state(state_path: Path) -> dict:
    """Load existing state or return empty state."""
    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)
    return {"completed": [], "failed": [], "remaining": []}


def save_state(state_path: Path, state: dict):
    """Save current state for resume capability."""
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def read_books_file(books_file: Path) -> list[str]:
    """Read book directory names from file, one per line."""
    with open(books_file) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def run_batch(repo: str, books: list[str], distro: str | None, output: str | None) -> bool:
    """Run a single batch of books through the workflow skill."""
    # Create a temporary books file for this batch
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        for book in books:
            tmp.write(f"{book}\n")
        tmp_path = tmp.name

    try:
        # Build the skill invocation
        cmd_parts = [
            "claude",
            "--print",
            "-p",
        ]

        skill_args = f"/jtbd-workflow-topicmap {repo} --books-file {tmp_path} --batch --batch-size {len(books)}"
        if distro:
            skill_args += f" --distro {distro}"
        if output:
            skill_args += f" --output {output}"

        cmd_parts.append(skill_args)

        print(f"\n{'='*60}")
        print(f"Running batch: {', '.join(books)}")
        print(f"Command: {' '.join(cmd_parts)}")
        print(f"{'='*60}\n")

        result = subprocess.run(
            cmd_parts,
            capture_output=False,
            text=True,
            timeout=3600,  # 1 hour timeout per batch
        )

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"ERROR: Batch timed out after 1 hour")
        return False
    except FileNotFoundError:
        print("ERROR: 'claude' command not found. Ensure Claude Code CLI is installed.")
        sys.exit(1)
    finally:
        os.unlink(tmp_path)


def main():
    parser = argparse.ArgumentParser(
        description="Batch runner for jtbd-workflow-topicmap skill"
    )
    parser.add_argument("--repo", required=True, help="Path to repo root")
    parser.add_argument("--books-file", required=True, help="File with book dir names, one per line")
    parser.add_argument("--distro", help="Filter by distro")
    parser.add_argument("--output", help="Output base directory")
    parser.add_argument("--batch-size", type=int, default=5, help="Books per batch (default: 5)")
    parser.add_argument("--resume", action="store_true", help="Resume from previous state")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")

    args = parser.parse_args()

    books_file = Path(args.books_file)
    if not books_file.exists():
        print(f"ERROR: Books file not found: {books_file}")
        sys.exit(1)

    repo = Path(args.repo)
    if not repo.exists():
        print(f"ERROR: Repo not found: {repo}")
        sys.exit(1)

    all_books = read_books_file(books_file)
    if not all_books:
        print("ERROR: No books found in books file")
        sys.exit(1)

    batch_size = min(args.batch_size, 10)  # Cap at 10

    # Handle resume
    state_path = Path(STATE_FILE)
    if args.resume:
        state = load_state(state_path)
        completed = set(state["completed"])
        remaining = [b for b in all_books if b not in completed]
        print(f"Resuming: {len(state['completed'])} completed, {len(state['failed'])} failed, {len(remaining)} remaining")
    else:
        state = {"completed": [], "failed": [], "remaining": list(all_books)}
        remaining = list(all_books)

    # Split into batches
    batches = [remaining[i:i + batch_size] for i in range(0, len(remaining), batch_size)]

    print(f"\nBatch Plan:")
    print(f"  Total books: {len(all_books)}")
    print(f"  Already completed: {len(state['completed'])}")
    print(f"  Remaining: {len(remaining)}")
    print(f"  Batch size: {batch_size}")
    print(f"  Number of batches: {len(batches)}")
    print()

    for i, batch in enumerate(batches):
        print(f"  Batch {i+1}: {', '.join(batch)}")

    if args.dry_run:
        print("\n[Dry run — no batches executed]")
        return

    print()
    response = input("Proceed? [y/N] ")
    if response.lower() != "y":
        print("Aborted.")
        return

    # Execute batches
    for i, batch in enumerate(batches):
        print(f"\n>>> Batch {i+1}/{len(batches)} ({len(batch)} books)")

        success = run_batch(str(repo), batch, args.distro, args.output)

        if success:
            state["completed"].extend(batch)
            state["remaining"] = [b for b in state["remaining"] if b not in batch]
            print(f"Batch {i+1} completed successfully")
        else:
            state["failed"].extend(batch)
            state["remaining"] = [b for b in state["remaining"] if b not in batch]
            print(f"Batch {i+1} FAILED for: {', '.join(batch)}")

        save_state(state_path, state)
        print(f"Progress: {len(state['completed'])}/{len(all_books)} completed, {len(state['failed'])} failed")

    # Final report
    print(f"\n{'='*60}")
    print("FINAL REPORT")
    print(f"{'='*60}")
    print(f"Completed: {len(state['completed'])}/{len(all_books)}")
    if state["completed"]:
        print(f"  Books: {', '.join(state['completed'])}")
    if state["failed"]:
        print(f"Failed: {len(state['failed'])}")
        print(f"  Books: {', '.join(state['failed'])}")
        print(f"\nTo retry failed books, create a new books file with the failed entries and run again.")

    # Clean up state file on full completion
    if not state["failed"] and not state["remaining"]:
        state_path.unlink(missing_ok=True)
        print("\nAll books processed successfully. State file cleaned up.")
    else:
        print(f"\nState saved to {STATE_FILE}. Use --resume to continue.")


if __name__ == "__main__":
    main()
