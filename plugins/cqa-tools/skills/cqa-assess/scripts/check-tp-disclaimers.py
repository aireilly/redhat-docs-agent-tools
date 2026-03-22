#!/usr/bin/env python3
"""Check Technology Preview and Developer Preview disclaimer compliance.

Finds all mentions of Technology Preview (TP) and Developer Preview (DP)
in active content, verifies that reusable disclaimer snippets exist, and
checks whether files that mention TP/DP features include the appropriate
disclaimer snippet.

CQA parameters: P19, O5
Skill: cqa-legal-branding

Usage:
    python3 check-tp-disclaimers.py <DOCS_DIR>

Exit codes:
    0 - No issues found
    1 - Issues found
    2 - Invalid arguments (e.g., docs_dir is not a directory)
"""

import argparse
import os
import re
import sys

# Patterns that indicate TP/DP features
TP_PATTERNS = [
    re.compile(r'\bTechnology Preview\b', re.IGNORECASE),
    re.compile(r'\bTech Preview\b', re.IGNORECASE),
]

DP_PATTERNS = [
    re.compile(r'\bDeveloper Preview\b', re.IGNORECASE),
    re.compile(r'\bDev Preview\b', re.IGNORECASE),
]

# Expected snippet filenames
TP_SNIPPET = "snip_technology-preview.adoc"
DP_SNIPPET = "snip_developer-preview.adoc"

# Required content in TP disclaimer
TP_REQUIRED_PHRASES = [
    "Technology Preview feature only",
    "not supported with Red Hat production service level agreements",
    "Red Hat does not recommend using them in production",
    "access.redhat.com/support/offerings/techpreview",
]

# Required content in DP disclaimer
DP_REQUIRED_PHRASES = [
    "Developer Preview",
    "not supported by Red Hat",
    "not functionally complete or production-ready",
    "access.redhat.com/support/offerings/devpreview",
]

# Directories to scan (default; overridable via --scan-dirs)
DEFAULT_SCAN_DIRS = ["assemblies", "modules", "topics", "snippets"]
SNIPPET_DIR = "snippets"

# Directories to skip
SKIP_DIRS = {"legacy-content-do-not-use"}

# Contexts where TP/DP labels are acceptable without full disclaimer
# (e.g., maturity tables with "Technology Preview" as cell value)
TABLE_CONTEXT_PATTERNS = [
    re.compile(r'^\|'),  # Table row
    re.compile(r'^\.Supported'),  # Table caption
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


def parse_code_block_lines(lines):
    """Return a set of line indices inside code/literal blocks."""
    code_lines = set()
    in_source = False
    in_literal = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("----") and len(stripped) >= 4 and all(c == "-" for c in stripped):
            if in_source:
                code_lines.add(i)
            in_source = not in_source
            if in_source:
                code_lines.add(i)
            continue
        if stripped.startswith("....") and len(stripped) >= 4 and all(c == "." for c in stripped):
            if in_literal:
                code_lines.add(i)
            in_literal = not in_literal
            if in_literal:
                code_lines.add(i)
            continue
        if in_source or in_literal:
            code_lines.add(i)
    return code_lines


def is_table_context(line):
    """Check if a line is inside a table (where TP/DP labels are acceptable)."""
    for pattern in TABLE_CONTEXT_PATTERNS:
        if pattern.search(line):
            return True
    return False


def is_inside_link_text(line, match_start, match_end):
    """Check if a match position falls inside link:...[text] brackets."""
    for m in re.finditer(r'link:[^\[]*\[([^\]]*)\]', line):
        bracket_start = m.start(1)
        bracket_end = m.end(1)
        if match_start >= bracket_start and match_end <= bracket_end:
            return True
    return False


def check_snippet_exists(docs_dir, snippet_name):
    """Check if a disclaimer snippet file exists."""
    snippet_path = os.path.join(docs_dir, SNIPPET_DIR, snippet_name)
    return os.path.isfile(snippet_path), snippet_path


def check_snippet_content(snippet_path, required_phrases):
    """Verify a snippet contains the required disclaimer text."""
    try:
        with open(snippet_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return False, ["Could not read file"]

    missing = []
    for phrase in required_phrases:
        if phrase.lower() not in content.lower():
            missing.append(phrase)
    return len(missing) == 0, missing


def file_includes_snippet(filepath, snippet_name):
    """Check if a file includes the given snippet via an actual include:: directive.

    Matches patterns like:
        include::snippets/snip_technology-preview.adoc[]
        include::snippets/snip_developer-preview.adoc[]
    A bare mention of the snippet filename (e.g., in a comment or prose)
    does not count as including the disclaimer.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return False

    # Check for an actual include:: directive referencing the snippet
    include_pattern = re.compile(
        r'^include::.*' + re.escape(snippet_name) + r'\b',
        re.MULTILINE,
    )
    return bool(include_pattern.search(content))


def find_tp_dp_mentions(filepath, rel_path):
    """Find all TP/DP mentions in a file.

    Returns list of finding dicts with classification:
        PROSE      - TP/DP mentioned in body text (needs disclaimer)
        TABLE      - TP/DP mentioned in a table cell (acceptable label)
        LINK_TEXT  - TP/DP mentioned inside link:[text] (informational reference)
        COMMENT    - Inside a comment
        CODE_BLOCK - Inside a code block
    """
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return findings

    lines = content.splitlines()
    code_lines = parse_code_block_lines(lines)

    for line_idx, line in enumerate(lines):
        stripped = line.strip()

        # Determine classification
        if line_idx in code_lines:
            classification = "CODE_BLOCK"
        elif stripped.startswith("//"):
            classification = "COMMENT"
        elif is_table_context(line):
            classification = "TABLE"
        else:
            classification = "PROSE"

        # Check TP patterns
        for pattern in TP_PATTERNS:
            for m in pattern.finditer(line):
                # Refine classification: check if match is inside link text
                cls = classification
                if cls == "PROSE" and is_inside_link_text(line, m.start(), m.end()):
                    cls = "LINK_TEXT"
                findings.append({
                    "file": rel_path,
                    "line_num": line_idx + 1,
                    "line": line.rstrip(),
                    "match": m.group(),
                    "type": "TP",
                    "classification": cls,
                })

        # Check DP patterns
        for pattern in DP_PATTERNS:
            for m in pattern.finditer(line):
                cls = classification
                if cls == "PROSE" and is_inside_link_text(line, m.start(), m.end()):
                    cls = "LINK_TEXT"
                findings.append({
                    "file": rel_path,
                    "line_num": line_idx + 1,
                    "line": line.rstrip(),
                    "match": m.group(),
                    "type": "DP",
                    "classification": cls,
                })

    return findings


def main():
    parser = argparse.ArgumentParser(
        description="Check Technology Preview and Developer Preview disclaimer compliance."
    )
    parser.add_argument(
        "docs_dir",
        help="Path to the documentation repository root",
    )
    parser.add_argument(
        "--scan-dirs",
        nargs="+",
        default=DEFAULT_SCAN_DIRS,
        metavar="DIR",
        help=f"Directories to scan (default: {' '.join(DEFAULT_SCAN_DIRS)})",
    )
    args = parser.parse_args()

    docs_dir = os.path.abspath(args.docs_dir)
    if not os.path.isdir(docs_dir):
        print(f"Error: {docs_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    print("Technology Preview / Developer Preview Disclaimer Check")
    print("=" * 60)
    print(f"Scanning: {docs_dir}")
    print(f"Directories: {', '.join(args.scan_dirs)}")
    print()

    issues = []

    # 1. Check snippet files exist
    print("1. Snippet file existence:")
    tp_exists, tp_path = check_snippet_exists(docs_dir, TP_SNIPPET)
    print(f"   {TP_SNIPPET}: {'FOUND' if tp_exists else 'MISSING'}")
    if tp_exists:
        tp_valid, tp_missing = check_snippet_content(tp_path, TP_REQUIRED_PHRASES)
        if tp_valid:
            print("   Content: Valid (all required phrases present)")
        else:
            print(f"   Content: INCOMPLETE — missing: {', '.join(tp_missing)}")
            issues.append(f"{TP_SNIPPET} missing required phrases: {', '.join(tp_missing)}")
    else:
        issues.append(f"{TP_SNIPPET} not found")

    dp_exists, dp_path = check_snippet_exists(docs_dir, DP_SNIPPET)
    print(f"   {DP_SNIPPET}: {'FOUND' if dp_exists else 'NOT FOUND (OK if no DP features)'}")
    if dp_exists:
        dp_valid, dp_missing = check_snippet_content(dp_path, DP_REQUIRED_PHRASES)
        if dp_valid:
            print("   Content: Valid")
        else:
            print(f"   Content: INCOMPLETE — missing: {', '.join(dp_missing)}")
            issues.append(f"{DP_SNIPPET} missing required phrases: {', '.join(dp_missing)}")
    print()

    # 2. Find all TP/DP mentions
    files = collect_adoc_files(docs_dir, scan_dirs=args.scan_dirs)
    all_findings = []
    for filepath, rel_path in files:
        all_findings.extend(find_tp_dp_mentions(filepath, rel_path))

    # Group by file and type
    tp_prose_files = set()
    dp_prose_files = set()
    for f in all_findings:
        if f["classification"] == "PROSE":
            if f["type"] == "TP":
                tp_prose_files.add(f["file"])
            elif f["type"] == "DP":
                dp_prose_files.add(f["file"])

    # 3. Report mentions
    print("2. TP/DP mentions in active content:")
    tp_findings = [f for f in all_findings if f["type"] == "TP"]
    dp_findings = [f for f in all_findings if f["type"] == "DP"]

    print(f"   Technology Preview mentions: {len(tp_findings)}")
    for cls in ["PROSE", "TABLE", "LINK_TEXT", "COMMENT", "CODE_BLOCK"]:
        count = len([f for f in tp_findings if f["classification"] == cls])
        if count > 0:
            print(f"     {cls}: {count}")

    print(f"   Developer Preview mentions: {len(dp_findings)}")
    for cls in ["PROSE", "TABLE", "LINK_TEXT", "COMMENT", "CODE_BLOCK"]:
        count = len([f for f in dp_findings if f["classification"] == cls])
        if count > 0:
            print(f"     {cls}: {count}")
    print()

    # 4. Check disclaimer inclusion for prose mentions
    print("3. Disclaimer compliance (prose mentions):")
    if tp_prose_files:
        print(f"   Files mentioning TP in prose ({len(tp_prose_files)}):")
        for rel_path in sorted(tp_prose_files):
            filepath = os.path.join(docs_dir, rel_path)
            has_snippet = file_includes_snippet(filepath, TP_SNIPPET)
            # Also check for inline [IMPORTANT] blocks with TP text
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                has_inline = "Technology Preview feature only" in content
            except (UnicodeDecodeError, IOError):
                has_inline = False

            if has_snippet:
                status = "OK (includes snippet)"
            elif has_inline:
                status = "OK (has inline disclaimer)"
            else:
                status = "NEEDS DISCLAIMER"
                issues.append(f"{rel_path}: mentions TP but has no disclaimer")
            print(f"     {rel_path}: {status}")
    else:
        print("   No files mention TP in prose.")
    print()

    if dp_prose_files:
        print(f"   Files mentioning DP in prose ({len(dp_prose_files)}):")
        for rel_path in sorted(dp_prose_files):
            filepath = os.path.join(docs_dir, rel_path)
            if dp_exists:
                has_snippet = file_includes_snippet(filepath, DP_SNIPPET)
            else:
                has_snippet = False
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                has_inline = "Developer Preview" in content and "not supported" in content.lower()
            except (UnicodeDecodeError, IOError):
                has_inline = False

            if has_snippet:
                status = "OK (includes snippet)"
            elif has_inline:
                status = "OK (has inline disclaimer)"
            else:
                status = "NEEDS DISCLAIMER"
                issues.append(f"{rel_path}: mentions DP but has no disclaimer")
            print(f"     {rel_path}: {status}")
    else:
        print("   No files mention DP in prose.")
    print()

    # 5. Check that DP snippet exists if DP features are documented
    if dp_prose_files and not dp_exists:
        issues.append(f"DP features documented but {DP_SNIPPET} does not exist")

    # 6. Detail all mentions
    print("4. Detailed mention list:")
    if all_findings:
        current_file = None
        for f in sorted(all_findings, key=lambda x: (x["file"], x["line_num"])):
            if f["file"] != current_file:
                current_file = f["file"]
                print(f"   {current_file}:")
            print(f"     :{f['line_num']}  [{f['classification']}] {f['match']}")
            print(f"         {f['line'].strip()}")
    else:
        print("   No TP/DP mentions found.")
    print()

    # Summary
    print("-" * 60)
    print(f"Summary: {len(issues)} issues")
    print(f"  TP mentions: {len(tp_findings)} ({len(tp_prose_files)} files in prose)")
    print(f"  DP mentions: {len(dp_findings)} ({len(dp_prose_files)} files in prose)")
    print(f"  Files scanned: {len(files)}")

    if issues:
        print(f"\nIssues:")
        for issue in issues:
            print(f"  - {issue}")
        print(f"\nResult: FAIL ({len(issues)} issues)")
        sys.exit(1)
    else:
        print("\nResult: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
