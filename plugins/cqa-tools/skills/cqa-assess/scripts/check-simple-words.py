#!/usr/bin/env python3
"""Check for complex words that should be replaced with simpler alternatives.

Scans prose in AsciiDoc documentation for unnecessarily complex words
and phrases, flagging each occurrence with its location and suggested
replacement.

Properly handles AsciiDoc structure: code blocks, comments, attribute
definitions, and table content are excluded from checks.

CQA parameters: Q3
Skill: cqa-editorial

Usage:
    python3 check-simple-words.py <DOCS_DIR>

Exit codes:
    0 - No violations found
    1 - Violations found
    2 - Invalid arguments (e.g., docs_dir is not a directory)
"""

import argparse
import os
import re
import sys

# NOTE: find_block_ranges() and is_skip_line() are intentionally duplicated
# from check-fluff.py to keep each script standalone with no extra imports
# beyond the standard library.

# Directories to scan (relative to DOCS_DIR)
DEFAULT_SCAN_DIRS = ["assemblies", "modules", "topics"]

# Directories to skip
SKIP_DIRS = {"legacy-content-do-not-use"}

# Complex words/phrases and their simpler replacements.
# Each entry: (compiled regex, display pattern, replacement)
COMPLEX_WORDS = [
    (re.compile(r'\butilize[sd]?\b', re.IGNORECASE),
     "utilize", "use"),
    (re.compile(r'\bleverage[sd]?\b', re.IGNORECASE),
     "leverage", "use"),
    (re.compile(r'\bin order to\b', re.IGNORECASE),
     "in order to", "to"),
    (re.compile(r'\bprior to\b', re.IGNORECASE),
     "prior to", "before"),
    (re.compile(r'\bsubsequent to\b', re.IGNORECASE),
     "subsequent to", "after"),
    (re.compile(r'\bcommence[sd]?\b', re.IGNORECASE),
     "commence", "start"),
    (re.compile(r'\bterminate[sd]?\b', re.IGNORECASE),
     "terminate", "stop"),
    (re.compile(r'\bfacilitate[sd]?\b', re.IGNORECASE),
     "facilitate", "help"),
    (re.compile(r'\baforementioned\b', re.IGNORECASE),
     "aforementioned", "name the thing directly"),
    (re.compile(r'\bin the event that\b', re.IGNORECASE),
     "in the event that", "if"),
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
    """Check a single file for complex word usage."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except (UnicodeDecodeError, IOError):
        return []

    block_lines = find_block_ranges(lines)
    violations = []

    for i, line in enumerate(lines):
        # Skip block content
        if i in block_lines:
            continue
        # Skip non-prose lines
        if is_skip_line(line):
            continue

        # Check each complex word pattern
        for pattern, display, replacement in COMPLEX_WORDS:
            for match in pattern.finditer(line):
                matched_text = match.group()
                # Get surrounding context (up to 80 chars around match)
                start = max(0, match.start() - 30)
                end = min(len(line), match.end() + 30)
                context = line[start:end].strip()
                if start > 0:
                    context = "..." + context
                if end < len(line):
                    context = context + "..."

                violations.append({
                    "line": i + 1,
                    "word": matched_text,
                    "display": display,
                    "replacement": replacement,
                    "context": context,
                })

    return violations


def main():
    parser = argparse.ArgumentParser(
        description="Check for complex words in AsciiDoc docs."
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

    print("Simple Words Check")
    print("=" * 60)
    print(f"Scanning: {docs_dir}")
    print(f"Directories: {', '.join(args.scan_dirs)}")
    print(f"Patterns: {len(COMPLEX_WORDS)} complex word/phrase patterns")
    print()

    files = collect_adoc_files(docs_dir, args.scan_dirs)
    all_violations = []

    for filepath, rel_path in files:
        violations = check_file(filepath, rel_path)
        if violations:
            all_violations.append((rel_path, violations))

    # Report
    total = sum(len(v) for _, v in all_violations)
    print(f"COMPLEX WORDS FOUND: {total}")
    if all_violations:
        for rel_path, violations in all_violations:
            for v in violations:
                print(f"  {rel_path}:{v['line']}  "
                      f"\"{v['word']}\" -> \"{v['replacement']}\"")
                print(f"    {v['context']}")
                print()
    else:
        print("  (none)")
    print()

    # Per-pattern summary
    print("PER-PATTERN SUMMARY:")
    for _, display, replacement in COMPLEX_WORDS:
        count = sum(
            1 for _, vs in all_violations
            for v in vs if v["display"] == display
        )
        status = "PASS" if count == 0 else f"FAIL ({count})"
        print(f"  \"{display}\" -> \"{replacement}\": {status}")
    print()

    # Metrics
    print("-" * 60)
    print("METRICS:")
    print(f"  Files scanned:     {len(files)}")
    print(f"  Total violations:  {total}")
    print(f"  Files with issues: {len(all_violations)}")

    if total > 0:
        print(f"\nResult: FAIL ({total} complex words found)")
        sys.exit(1)
    else:
        print("\nResult: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
