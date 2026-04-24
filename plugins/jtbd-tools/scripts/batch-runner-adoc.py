#!/usr/bin/env python3
"""
Batch runner for jtbd-workflow-adoc skill.

Processes large lists of AsciiDoc documents by splitting them into groups
and invoking the Claude Code CLI for each group.

Usage:
    python batch-runner.py \
        --docs-file docs.txt \
        --variant self-managed \
        --research redhat-ai \
        --batch-size 5

The script:
- Reads the docs file and splits into groups of --batch-size
- Invokes `claude` with the /jtbd-workflow-adoc skill for each group
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

STATE_FILE = ".batch-runner-adoc-state.json"


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


def read_docs_file(docs_file: Path) -> list[str]:
    """Read document paths from file, one per line."""
    with open(docs_file) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def run_batch(
    docs: list[str], variant: str | None, research: str | None, output: str | None
) -> bool:
    """Run a single batch of docs through the workflow skill."""
    # Create a temporary docs file for this batch
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        for doc in docs:
            tmp.write(f"{doc}\n")
        tmp_path = tmp.name

    try:
        # Build the skill invocation
        cmd_parts = [
            "claude",
            "--print",
            "-p",
        ]

        skill_args = f"/jtbd-workflow-adoc --docs-file {tmp_path} --batch --batch-size {len(docs)}"
        if variant:
            skill_args += f" --variant {variant}"
        if research:
            skill_args += f" --research {research}"
        if output:
            skill_args += f" --output {output}"

        cmd_parts.append(skill_args)

        print(f"\n{'='*60}")
        print(f"Running batch: {len(docs)} documents")
        for doc in docs:
            print(f"  - {doc}")
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
        print("ERROR: Batch timed out after 1 hour")
        return False
    except FileNotFoundError:
        print("ERROR: 'claude' command not found. Ensure Claude Code CLI is installed.")
        sys.exit(1)
    finally:
        os.unlink(tmp_path)


def main():
    parser = argparse.ArgumentParser(description="Batch runner for jtbd-workflow-adoc skill")
    parser.add_argument(
        "--docs-file", required=True, help="File with paths to master.adoc files, one per line"
    )
    parser.add_argument("--variant", help="Conditional variant (e.g., self-managed, cloud-service)")
    parser.add_argument("--research", help="Research config name")
    parser.add_argument("--output", help="Output base directory")
    parser.add_argument("--batch-size", type=int, default=5, help="Docs per batch (default: 5)")
    parser.add_argument("--resume", action="store_true", help="Resume from previous state")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")

    args = parser.parse_args()

    docs_file = Path(args.docs_file)
    if not docs_file.exists():
        print(f"ERROR: Docs file not found: {docs_file}")
        sys.exit(1)

    all_docs = read_docs_file(docs_file)
    if not all_docs:
        print("ERROR: No documents found in docs file")
        sys.exit(1)

    batch_size = min(args.batch_size, 10)  # Cap at 10

    # Handle resume
    state_path = Path(STATE_FILE)
    if args.resume:
        state = load_state(state_path)
        completed = set(state["completed"])
        remaining = [d for d in all_docs if d not in completed]
        print(
            f"Resuming: {len(state['completed'])} completed, {len(state['failed'])} failed, {len(remaining)} remaining"
        )
    else:
        state = {"completed": [], "failed": [], "remaining": list(all_docs)}
        remaining = list(all_docs)

    # Split into batches
    batches = [remaining[i : i + batch_size] for i in range(0, len(remaining), batch_size)]

    print("\nBatch Plan:")
    print(f"  Total docs: {len(all_docs)}")
    print(f"  Already completed: {len(state['completed'])}")
    print(f"  Remaining: {len(remaining)}")
    print(f"  Batch size: {batch_size}")
    print(f"  Number of batches: {len(batches)}")
    print()

    for i, batch in enumerate(batches):
        print(f"  Batch {i+1}:")
        for doc in batch:
            print(f"    - {doc}")

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
        print(f"\n>>> Batch {i+1}/{len(batches)} ({len(batch)} docs)")

        success = run_batch(batch, args.variant, args.research, args.output)

        if success:
            state["completed"].extend(batch)
            state["remaining"] = [d for d in state["remaining"] if d not in batch]
            print(f"Batch {i+1} completed successfully")
        else:
            state["failed"].extend(batch)
            state["remaining"] = [d for d in state["remaining"] if d not in batch]
            print(f"Batch {i+1} FAILED")

        save_state(state_path, state)
        print(
            f"Progress: {len(state['completed'])}/{len(all_docs)} completed, {len(state['failed'])} failed"
        )

    # Final report
    print(f"\n{'='*60}")
    print("FINAL REPORT")
    print(f"{'='*60}")
    print(f"Completed: {len(state['completed'])}/{len(all_docs)}")
    if state["completed"]:
        for doc in state["completed"]:
            print(f"  - {doc}")
    if state["failed"]:
        print(f"Failed: {len(state['failed'])}")
        for doc in state["failed"]:
            print(f"  - {doc}")
        print(
            "\nTo retry failed docs, create a new docs file with the failed entries and run again."
        )

    # Clean up state file on full completion
    if not state["failed"] and not state["remaining"]:
        state_path.unlink(missing_ok=True)
        print("\nAll documents processed successfully. State file cleaned up.")
    else:
        print(f"\nState saved to {STATE_FILE}. Use --resume to continue.")


if __name__ == "__main__":
    main()
