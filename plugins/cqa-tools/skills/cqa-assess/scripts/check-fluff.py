#!/usr/bin/env python3
"""Check for fluff patterns in documentation.

Scans prose in AsciiDoc documentation for self-referential,
forward-referencing, and unnecessarily wordy patterns that add
no value for the reader.

Properly handles AsciiDoc structure: code blocks, comments, attribute
definitions, and table content are excluded from checks.

CQA parameters: Q5
Skill: cqa-editorial

Usage:
    python3 check-fluff.py <DOCS_DIR>

Exit codes:
    0 - No violations found
    1 - Violations found
"""

import argparse
import os
import re
import sys

# Directories to scan (relative to DOCS_DIR)
DEFAULT_SCAN_DIRS = ["assemblies", "modules", "topics", "snippets"]

# Directories to skip
SKIP_DIRS = {"legacy-content-do-not-use"}

# Fluff patterns: (compiled regex, display pattern, fix guidance)
FLUFF_PATTERNS = [
    # Self-referential
    (re.compile(r'\b[Tt]his section (describes|provides|covers|explains)\b'),
     "This section describes/provides/covers",
     "State the content directly"),
    (re.compile(r'\b[Tt]his topic (describes|provides|covers|explains)\b'),
     "This topic describes/provides/covers",
     "State the content directly"),
    (re.compile(r'\b[Tt]his (procedure|document) (describes|provides|explains|shows)\b'),
     "This procedure/document describes",
     "State the action directly"),
    (re.compile(r'\b[Ii]n this (chapter|section|topic)\b'),
     "In this chapter/section/topic",
     "Remove self-reference"),
    # Forward-referencing
    (re.compile(r'\b[Tt]he following (describes|provides|explains|lists|shows)\b'),
     "The following describes/shows",
     "State the content directly"),
    # Filler phrases
    (re.compile(r'\b[Ii]t is important to note that\b'),
     "It is important to note that",
     "State the fact directly"),
    (re.compile(r'\b[Pp]lease note that\b'),
     "Please note that",
     "Remove or state directly"),
    # Learning-oriented (not action-oriented)
    (re.compile(r'\b[Ll]earn how to\b'),
     "Learn how to",
     "Use action-oriented language"),
    (re.compile(r'\b[Ll]earn about\b'),
     "Learn about",
     "State what the content covers directly"),
    (re.compile(r'\b[Ll]earn more about\b'),
     "Learn more about",
     "Replace with 'See' or direct xref"),
    # As mentioned
    (re.compile(r'\b[Aa]s mentioned (above|below|earlier|previously)\b'),
     "As mentioned above/below",
     "Remove or provide a direct xref"),
]


def collect_adoc_files(docs_dir, scan_dirs=None):
    """Collect all .adoc files from scan directories."""
    if scan_dirs is None:
        scan_dirs = DEFAULT_SCAN_DIRS
    files = []
    for scan_dir in scan_dirs:
        full_dir = os.path.join(docs_dir, scan_dir)
        if not os.path.isdir(full_dir):
            continue
        for root, dirs, filenames in os.walk(full_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in filenames:
                if fname.endswith(".adoc"):
                    filepath = os.path.join(root, fname)
                    rel_path = os.path.relpath(filepath, docs_dir)
                    files.append((filepath, rel_path))
    return sorted(files, key=lambda x: x[1])


def find_block_ranges(lines):
    """Return a set of line indices inside code/literal/passthrough blocks."""
    block_lines = set()
    in_block = False
    block_delim = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        is_delim = False
        matched_key = None
        if re.match(r'^[,|]={3,}$', stripped):
            is_delim = True
            matched_key = stripped[0]
        else:
            for delim in ("----", "....", "++++"):
                if stripped.startswith(delim) and all(
                    c == delim[0] for c in stripped
                ):
                    is_delim = True
                    matched_key = delim[0]
                    break
        if is_delim:
            if not in_block:
                in_block = True
                block_delim = matched_key
                block_lines.add(i)
            elif stripped[0] == block_delim:
                block_lines.add(i)
                in_block = False
                block_delim = None
        else:
            if in_block:
                block_lines.add(i)
    return block_lines


def is_skip_line(line):
    """Check if a line should be skipped (not prose)."""
    s = line.strip()
    if not s:
        return True
    # Comments
    if s.startswith("//"):
        return True
    # Attribute definitions
    if re.match(r'^:[\w_][\w_-]*:', s):
        return True
    # Block attributes/annotations
    if s.startswith("["):
        return True
    # Include/image/ifdef directives
    if re.match(r'^(include|image|ifdef|ifndef|endif|ifeval)::', s):
        return True
    # Headings
    if re.match(r'^={1,5}\s', s):
        return True
    # Table delimiters and rows
    if s.startswith("|"):
        return True
    # Block delimiters
    if re.match(r'^(-{4,}|\.{4,}|\+{4,}|\*{4,}|={4,})$', s):
        return True
    # List continuation marker
    if s == "+":
        return True
    # Block titles
    if re.match(r'^\.\w', s) and not s.startswith(".. "):
        return True
    # Pass macros on their own line
    if s.startswith("pass:"):
        return True
    return False


def check_file(filepath, rel_path):
    """Check a single file for fluff patterns."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except (UnicodeDecodeError, IOError):
        return []

    block_lines = find_block_ranges(lines)
    violations = []

    for i, line in enumerate(lines):
        if i in block_lines:
            continue
        if is_skip_line(line):
            continue

        for pattern, display, fix in FLUFF_PATTERNS:
            for match in pattern.finditer(line):
                matched_text = match.group()
                start = max(0, match.start() - 20)
                end = min(len(line), match.end() + 40)
                context = line[start:end].strip()
                if start > 0:
                    context = "..." + context
                if end < len(line):
                    context = context + "..."

                violations.append({
                    "line": i + 1,
                    "pattern": display,
                    "matched": matched_text,
                    "fix": fix,
                    "context": context,
                })

    return violations


def main():
    parser = argparse.ArgumentParser(
        description="Check for fluff patterns in AsciiDoc docs."
    )
    parser.add_argument(
        "docs_dir",
        help="Path to the documentation repository root",
    )
    parser.add_argument(
        "--scan-dirs",
        nargs="+",
        default=DEFAULT_SCAN_DIRS,
        help="Directories to scan (default: %(default)s)",
    )
    args = parser.parse_args()

    docs_dir = os.path.abspath(args.docs_dir)
    if not os.path.isdir(docs_dir):
        print(f"Error: {docs_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    print("Fluff Pattern Check")
    print("=" * 60)
    print(f"Scanning: {docs_dir}")
    print(f"Directories: {', '.join(args.scan_dirs)}")
    print(f"Patterns: {len(FLUFF_PATTERNS)} fluff patterns")
    print()

    files = collect_adoc_files(docs_dir, args.scan_dirs)
    all_violations = []

    for filepath, rel_path in files:
        violations = check_file(filepath, rel_path)
        if violations:
            all_violations.append((rel_path, violations))

    # Report
    total = sum(len(v) for _, v in all_violations)
    print(f"FLUFF PATTERNS FOUND: {total}")
    if all_violations:
        for rel_path, violations in all_violations:
            for v in violations:
                print(f"  {rel_path}:{v['line']}  "
                      f"\"{v['matched']}\"")
                print(f"    Fix: {v['fix']}")
                print(f"    {v['context']}")
                print()
    else:
        print("  (none)")
    print()

    # Per-pattern summary
    print("PER-PATTERN SUMMARY:")
    for _, display, _ in FLUFF_PATTERNS:
        count = sum(
            1 for _, vs in all_violations
            for v in vs if v["pattern"] == display
        )
        status = "PASS" if count == 0 else f"FAIL ({count})"
        print(f"  \"{display}\": {status}")
    print()

    # Metrics
    print("-" * 60)
    print("METRICS:")
    print(f"  Files scanned:     {len(files)}")
    print(f"  Total violations:  {total}")
    print(f"  Files with issues: {len(all_violations)}")

    if total > 0:
        print(f"\nResult: FAIL ({total} fluff patterns found)")
        sys.exit(1)
    else:
        print("\nResult: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
