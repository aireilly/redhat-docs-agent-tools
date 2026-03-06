#!/usr/bin/env python3
"""
Summarize Claude Code conversation JSONL files for a given repository.
Extracts user messages, assistant actions, and work topics from each session.
Produces a condensed, readable summary focused on actual documentation work.

Usage:
    python3 summarize_conversations.py --repo-path /path/to/repo --since 2026-01-01
    python3 summarize_conversations.py --repo-path /path/to/repo --days 30
    python3 summarize_conversations.py --repo-path /path/to/repo --since 2026-01-01 --output /tmp/summary.txt
"""

import argparse
import json
import os
import glob
import sys
from datetime import datetime, timedelta
from collections import Counter
from itertools import groupby


def get_claude_projects_dir(repo_path):
    """Derive the Claude projects directory from the repo path.

    Claude Code stores conversation JSONL files at:
    ~/.claude/projects/-<path-with-slashes-replaced-by-dashes>/

    For example, /home/user/my-repo becomes -home-user-my-repo
    """
    abs_path = os.path.abspath(repo_path)
    # Replace / with - to produce the directory name
    # The leading / becomes the leading - (e.g. /home/user -> -home-user)
    dir_name = abs_path.replace("/", "-")
    projects_dir = os.path.join(os.path.expanduser("~"), ".claude", "projects", dir_name)
    return projects_dir


def extract_text_from_content(content):
    """Extract text from message content which can be a string or list of objects."""
    if isinstance(content, str):
        return content.strip()
    elif isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        return " ".join(texts).strip()
    return ""


def is_noise(text):
    """Check if a message is noise: system prompts, caveats, or auto-generated."""
    if not text:
        return True
    indicators = [
        "<system-reminder>",
        "<claude_background_info>",
        "<fast_mode_info>",
        "gitStatus:",
        "<env>",
        "You are Claude Code",
        "IMPORTANT: this context may or may not be relevant",
        "# CLAUDE.md",
        "Caveat: The messages below were generated",
    ]
    first_500 = text[:500]
    for ind in indicators:
        if ind in first_500:
            return True
    stripped = text.strip()
    if stripped.startswith("<") and not stripped.startswith("<http"):
        return True
    return False


def is_substantive_message(text):
    """Check if a message is substantive."""
    if not text:
        return False
    if len(text) < 15:
        return False
    if is_noise(text):
        return False
    return True


def extract_files_worked_on(lines):
    """Extract unique files that were written or edited."""
    files = set()
    for line_str in lines:
        try:
            obj = json.loads(line_str.strip())
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "assistant":
            continue
        msg = obj.get("message", {})
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                name = item.get("name", "")
                inp = item.get("input", {})
                if name in ("Write", "Edit"):
                    fpath = inp.get("filePath", inp.get("file_path", ""))
                    if fpath:
                        files.add(fpath)
    return files


def extract_tool_counts(lines):
    """Extract tool usage counts from assistant messages."""
    counts = Counter()
    for line_str in lines:
        try:
            obj = json.loads(line_str.strip())
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "assistant":
            continue
        msg = obj.get("message", {})
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                counts[item.get("name", "unknown")] += 1
    return counts


def extract_assistant_first_snippet(lines):
    """Get the first substantive assistant text response."""
    for line_str in lines:
        try:
            obj = json.loads(line_str.strip())
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "assistant":
            continue
        msg = obj.get("message", {})
        content = msg.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "").strip()
                    if text and len(text) > 30:
                        return text[:250]
    return ""


def summarize_session(filepath, cutoff_date):
    """Summarize a single JSONL session file."""
    mtime = os.path.getmtime(filepath)
    mod_date = datetime.fromtimestamp(mtime)

    if mod_date < cutoff_date:
        return None

    session_id = os.path.basename(filepath).replace(".jsonl", "")

    with open(filepath, "r", errors="replace") as f:
        lines = f.readlines()

    if not lines:
        return None

    user_messages = []
    summary_text = ""
    total_user = 0
    total_assistant = 0

    for line_str in lines:
        try:
            obj = json.loads(line_str.strip())
        except json.JSONDecodeError:
            continue

        obj_type = obj.get("type")

        if obj_type == "summary":
            s = obj.get("summary", "")
            if s:
                summary_text = s

        if obj_type == "user":
            total_user += 1
            msg = obj.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content", "")
                text = extract_text_from_content(content)
            elif isinstance(msg, str):
                text = msg
            else:
                text = ""
            if is_substantive_message(text):
                user_messages.append(text)

        elif obj_type == "assistant":
            total_assistant += 1

    # Skip sessions with no real user interaction
    if not user_messages:
        return None

    # Skip sessions where the only messages are short or trivial
    if all(len(m) < 20 for m in user_messages):
        return None

    tool_counts = extract_tool_counts(lines)
    files_worked = extract_files_worked_on(lines)
    first_snippet = extract_assistant_first_snippet(lines)

    # If assistant never responded, low value session
    if total_assistant == 0 and not tool_counts:
        return None

    return {
        "date": mod_date,
        "session_id": session_id,
        "user_messages": user_messages,
        "tool_counts": dict(tool_counts),
        "files_worked": sorted(files_worked)[:10],
        "total_user": total_user,
        "total_assistant": total_assistant,
        "summary": summary_text,
        "first_snippet": first_snippet,
    }


def format_output(sessions, repo_path):
    """Format the session summaries into readable output."""
    output_lines = []

    def out(line=""):
        output_lines.append(line)

    repo_path_prefix = os.path.abspath(repo_path) + "/"

    out(f"Found sessions for repository: {repo_path}")
    out(f"Processed {len(sessions)} sessions with substantive work")
    out("=" * 100)

    def date_key(s):
        return s["date"].strftime("%Y-%m-%d")

    for date_str, group in groupby(sessions, key=date_key):
        group_list = list(group)
        out(f"\n{'='*100}")
        out(f"  DATE: {date_str} ({len(group_list)} session(s))")
        out(f"{'='*100}")

        for s in group_list:
            out(f"\n  [{s['date'].strftime('%H:%M')}] Session: {s['session_id'][:12]}...")
            tools_line = f"         Msgs: {s['total_user']}u/{s['total_assistant']}a | "
            if s["tool_counts"]:
                tc = ", ".join(
                    f"{k}:{v}"
                    for k, v in sorted(
                        s["tool_counts"].items(), key=lambda x: -x[1]
                    )[:5]
                )
                tools_line += f"Tools: {tc}"
            else:
                tools_line += "No tool calls"
            out(tools_line)

            if s["summary"]:
                out(f"         Summary: {s['summary'][:120]}")

            # Show first 3 substantive user messages, condensed
            for i, msg in enumerate(s["user_messages"][:3]):
                display = msg[:180].replace("\n", " ").strip()
                tag = ">>>" if i == 0 else "   "
                out(f"         {tag} {display}")
                if len(msg) > 180:
                    out(f"             ... ({len(msg)} chars)")

            remaining = len(s["user_messages"]) - 3
            if remaining > 0:
                out(f"         ... +{remaining} more messages")

            if s["files_worked"]:
                out("         Files modified:")
                for fp in s["files_worked"][:5]:
                    short = fp.replace(repo_path_prefix, "")
                    out(f"           - {short}")
                if len(s["files_worked"]) > 5:
                    out(f"           ... +{len(s['files_worked'])-5} more")

    # Overall statistics
    out(f"\n\n{'='*100}")
    out("OVERALL STATISTICS")
    out(f"{'='*100}")
    out(f"Total sessions analyzed: {len(sessions)}")
    if sessions:
        out(
            f"Date range: {sessions[0]['date'].strftime('%Y-%m-%d')} to "
            f"{sessions[-1]['date'].strftime('%Y-%m-%d')}"
        )

    overall_tools = Counter()
    all_files = Counter()
    for s in sessions:
        for k, v in s["tool_counts"].items():
            overall_tools[k] += v
        for fp in s["files_worked"]:
            short = fp.replace(repo_path_prefix, "")
            all_files[short] += 1

    out("\nTool usage totals:")
    for tool, count in overall_tools.most_common(10):
        out(f"  {tool}: {count}")

    out("\nMost frequently edited/written files:")
    for fp, count in all_files.most_common(15):
        out(f"  ({count}x) {fp}")

    # Daily activity timeline
    out(f"\n\nDAILY ACTIVITY TIMELINE:")
    out("-" * 80)
    for date_str, group in groupby(sessions, key=date_key):
        group_list = list(group)
        day_tools = Counter()
        day_summaries = []
        for s in group_list:
            for k, v in s["tool_counts"].items():
                day_tools[k] += v
            if s["summary"]:
                day_summaries.append(s["summary"][:80])

        writes = day_tools.get("Write", 0) + day_tools.get("Edit", 0)
        reads = day_tools.get("Read", 0)
        out(
            f"  {date_str}: {len(group_list)} sessions | "
            f"{writes} writes/edits, {reads} reads"
        )
        unique_summaries = list(dict.fromkeys(day_summaries))
        for summ in unique_summaries[:3]:
            out(f"    - {summ}")
        if len(unique_summaries) > 3:
            out(f"    ... +{len(unique_summaries)-3} more")

    return "\n".join(output_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Summarize Claude Code conversation sessions for a repository."
    )
    parser.add_argument(
        "--repo-path",
        required=True,
        help="Path to the git repository.",
    )
    parser.add_argument(
        "--since",
        help="Start date in YYYY-MM-DD format. Defaults to 30 days ago.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back. Ignored if --since is provided. Default: 30.",
    )
    parser.add_argument(
        "--output",
        help="Output file path. Defaults to stdout.",
    )

    args = parser.parse_args()

    # Calculate cutoff date
    if args.since:
        try:
            cutoff_date = datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            print(f"ERROR: Invalid date format '{args.since}'. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)
    else:
        cutoff_date = datetime.now() - timedelta(days=args.days)

    # Resolve repo path
    repo_path = os.path.abspath(args.repo_path)
    if not os.path.isdir(repo_path):
        print(f"ERROR: Repository path does not exist: {repo_path}", file=sys.stderr)
        sys.exit(1)

    # Find Claude projects directory
    projects_dir = get_claude_projects_dir(repo_path)
    if not os.path.isdir(projects_dir):
        print(f"ERROR: Claude projects directory not found: {projects_dir}", file=sys.stderr)
        print("No Claude Code conversation history exists for this repository.", file=sys.stderr)
        sys.exit(1)

    pattern = os.path.join(projects_dir, "*.jsonl")
    files = glob.glob(pattern)

    print(f"Found {len(files)} total JSONL files in {projects_dir}", file=sys.stderr)
    print(f"Filtering for files modified since {cutoff_date.strftime('%Y-%m-%d')}", file=sys.stderr)

    sessions = []
    skipped = 0

    for fpath in files:
        try:
            result = summarize_session(fpath, cutoff_date)
            if result:
                sessions.append(result)
            else:
                skipped += 1
        except Exception as e:
            print(f"ERROR processing {os.path.basename(fpath)}: {e}", file=sys.stderr)
            skipped += 1

    sessions.sort(key=lambda x: x["date"])

    print(
        f"Processed {len(sessions)} sessions with substantive work ({skipped} skipped)",
        file=sys.stderr,
    )

    output = format_output(sessions, repo_path)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output + "\n")
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
