#!/usr/bin/env python3
"""Retrieve code evidence from a repository using hybrid search.

Wraps code-finder's Python API (claude_context.skills.evidence_retrieval)
so the skill can call a script instead of relying on a CLI entry point
being on $PATH.

Usage:
    python3 find_evidence.py --repo /path/to/repo --query "search query" \
        [--limit 5] [--filter-paths src/auth,src/config] [--reindex]
"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve code evidence from a repository"
    )
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--query", required=True, help="Natural language search query")
    parser.add_argument(
        "--limit", type=int, default=5, help="Max results (default: 5)"
    )
    parser.add_argument(
        "--filter-paths",
        help="Comma-separated directory prefixes to scope search (relative to repo)",
    )
    parser.add_argument(
        "--reindex", action="store_true", help="Force re-indexing"
    )
    args = parser.parse_args()

    try:
        from claude_context.skills.evidence_retrieval import retrieve_evidence
    except ImportError:
        print(
            "Error: code-finder is not installed. Run: python3 -m pip install code-finder",
            file=sys.stderr,
        )
        sys.exit(1)

    filter_paths = None
    if args.filter_paths:
        filter_paths = [p.strip() for p in args.filter_paths.split(",") if p.strip()]

    result = retrieve_evidence(
        repo_path=args.repo,
        query=args.query,
        limit=args.limit,
        filter_paths=filter_paths,
        reindex=args.reindex,
    )

    json.dump(result, sys.stdout, indent=2, default=str)


if __name__ == "__main__":
    main()
