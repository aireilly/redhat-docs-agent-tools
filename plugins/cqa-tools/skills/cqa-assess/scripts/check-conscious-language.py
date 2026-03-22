#!/usr/bin/env python3
"""Check for exclusionary or non-inclusive language in AsciiDoc documentation.

Searches active content for terms that violate Red Hat's conscious language
guidelines. Handles known exceptions (upstream GitHub URLs, code blocks,
technical identifiers).

CQA parameters: Q23, O4
Skill: cqa-legal-branding

Usage:
    python3 check-conscious-language.py <DOCS_DIR>

Exit codes:
    0 - No violations found
    1 - Violations found
    2 - Invalid arguments (e.g., docs_dir is not a directory)
"""

import argparse
import os
import re
import sys

# Terms to search for, with replacements.
# Each tuple: (term, [replacements], case_sensitive)
EXCLUSIONARY_TERMS = [
    ("slave", ["secondary", "replica", "standby"], False),
    ("whitelist", ["allowlist"], False),
    ("blacklist", ["blocklist", "denylist"], False),
    ("dummy", ["placeholder", "example", "sample"], False),
]

# "master" requires special handling due to many legitimate uses
MASTER_TERM = ("master", ["primary", "main", "source"], False)

# Directories to scan (relative to DOCS_DIR)
DEFAULT_SCAN_DIRS = ["assemblies", "modules", "topics", "snippets"]

# Directories to skip
SKIP_DIRS = {"legacy-content-do-not-use"}


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
    """Return a set of line indices inside code/literal blocks.

    Tracks a single block state so that delimiters nested inside another
    block type (e.g., ``----`` inside a ``....`` block) are treated as
    content rather than toggling a second block.
    """
    code_lines = set()
    current_block = None  # None, "source", or "literal"
    for i, line in enumerate(lines):
        stripped = line.strip()
        is_source_delim = (
            stripped.startswith("----") and len(stripped) >= 4
            and all(c == "-" for c in stripped)
        )
        is_literal_delim = (
            stripped.startswith("....") and len(stripped) >= 4
            and all(c == "." for c in stripped)
        )
        if is_source_delim and current_block in (None, "source"):
            code_lines.add(i)
            current_block = None if current_block == "source" else "source"
            continue
        if is_literal_delim and current_block in (None, "literal"):
            code_lines.add(i)
            current_block = None if current_block == "literal" else "literal"
            continue
        if current_block is not None:
            code_lines.add(i)
    return code_lines


def is_master_in_url(line, match_start):
    """Check if 'master' appears inside a URL (e.g., /blob/master/)."""
    # Find all URLs on the line
    for m in re.finditer(r'https?://\S+', line):
        if match_start >= m.start() and match_start < m.end():
            return True
    # Also check link: macro URLs
    for m in re.finditer(r'link:\S+\[', line):
        if match_start >= m.start() and match_start < m.end():
            return True
    return False


def is_master_legitimate(line, match_start, match_end):
    """Check if 'master' is a legitimate use (not exclusionary).

    Legitimate uses of 'master' include:
    - URLs (GitHub /blob/master/)
    - File paths (master.adoc)
    - Technical terms (master node — in Kubernetes context)
    - AsciiDoc comments
    """
    stripped = line.strip()

    # Comment line
    if stripped.startswith("//"):
        return True, "COMMENT"

    # Inside a URL
    if is_master_in_url(line, match_start):
        return True, "URL"

    # Part of a filename (master.adoc, master.xml)
    context = line[max(0, match_start - 1):match_end + 10]
    if re.search(r'master\.\w+', context):
        return True, "FILENAME"

    # Part of "master file" or "master document" (doc terminology)
    after = line[match_end:match_end + 15].strip().lower()
    if after.startswith(("file", "document", ".adoc", ".xml")):
        return True, "DOC_TERM"

    return False, None


def classify_term_match(line, match_start, match_end, term):
    """Classify a term match.

    Returns (classification, detail) where classification is:
        COMMENT       - inside a comment
        CODE_BLOCK    - inside a code block (handled before this function)
        URL           - inside a URL
        FILENAME      - part of a filename
        DOC_TERM      - legitimate documentation term
        ATTRIBUTE_DEF - attribute definition line
        PROSE         - body text (violation)
    """
    stripped = line.strip()

    # Comment
    if stripped.startswith("//"):
        return "COMMENT", None

    # Attribute definition
    if re.match(r"^:\w[\w-]*:", stripped):
        return "ATTRIBUTE_DEF", None

    # Special handling for "master"
    if term.lower() == "master":
        legitimate, reason = is_master_legitimate(line, match_start, match_end)
        if legitimate:
            return reason, None

    return "PROSE", None


def find_term_occurrences(line, term, case_sensitive=False):
    """Find all occurrences of a term in a line as whole words.

    Returns list of (start_position, matched_text) tuples.
    Uses word boundary matching to avoid partial matches
    (e.g., 'master' should not match 'webmaster' or 'mastery').
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = r'\b' + re.escape(term) + r'\b'
    matches = []
    for m in re.finditer(pattern, line, flags):
        matches.append((m.start(), m.group()))
    return matches


def check_file(filepath, rel_path):
    """Check a single file for exclusionary language."""
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return findings

    lines = content.splitlines()
    code_lines = parse_code_block_lines(lines)

    for line_idx, line in enumerate(lines):
        if line_idx in code_lines:
            continue

        # Check "master" with special handling
        term, replacements, case_sensitive = MASTER_TERM
        for pos, matched_text in find_term_occurrences(line, term, case_sensitive):
            classification, _ = classify_term_match(
                line, pos, pos + len(matched_text), term
            )
            findings.append({
                "file": rel_path,
                "line_num": line_idx + 1,
                "line": line.rstrip(),
                "term": matched_text,
                "replacements": replacements,
                "classification": classification,
            })

        # Check other exclusionary terms
        for term, replacements, case_sensitive in EXCLUSIONARY_TERMS:
            for pos, matched_text in find_term_occurrences(line, term, case_sensitive):
                classification, _ = classify_term_match(
                    line, pos, pos + len(matched_text), term
                )
                findings.append({
                    "file": rel_path,
                    "line_num": line_idx + 1,
                    "line": line.rstrip(),
                    "term": matched_text,
                    "replacements": replacements,
                    "classification": classification,
                })

    return findings


def main():
    parser = argparse.ArgumentParser(
        description="Check for exclusionary language in AsciiDoc docs."
    )
    parser.add_argument(
        "docs_dir",
        help="Path to the documentation repository root",
    )
    parser.add_argument(
        "--scan-dirs",
        nargs="+",
        default=DEFAULT_SCAN_DIRS,
        help=("Directories to scan relative to docs_dir "
              f"(default: {' '.join(DEFAULT_SCAN_DIRS)})"),
    )
    args = parser.parse_args()

    docs_dir = os.path.abspath(args.docs_dir)
    if not os.path.isdir(docs_dir):
        print(f"Error: {docs_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    print("Conscious Language Check")
    print("=" * 60)
    print(f"Scanning: {docs_dir}")
    print(f"Directories: {', '.join(args.scan_dirs)}")
    print(f"Excluding: {', '.join(SKIP_DIRS)}")
    print()

    files = collect_adoc_files(docs_dir, scan_dirs=args.scan_dirs)
    all_findings = []
    for filepath, rel_path in files:
        all_findings.extend(check_file(filepath, rel_path))

    # Group by classification
    violations = [f for f in all_findings if f["classification"] == "PROSE"]
    exceptions = [f for f in all_findings if f["classification"] != "PROSE"]

    # Report violations
    print("VIOLATIONS (exclusionary terms in prose):")
    if violations:
        for f in violations:
            replacements = ", ".join(f["replacements"])
            print(f"  {f['file']}:{f['line_num']}")
            print(f"    Found: \"{f['term']}\" -> use: {replacements}")
            print(f"    Line:  {f['line'].strip()}")
            print()
    else:
        print("  (none)")
    print()

    # Report exceptions (informational)
    print("EXCEPTIONS (automatically excluded):")
    if exceptions:
        # Group by classification type
        by_type = {}
        for f in exceptions:
            by_type.setdefault(f["classification"], []).append(f)
        for cls, items in sorted(by_type.items()):
            print(f"  [{cls}] ({len(items)} occurrences):")
            for f in items:
                print(f"    {f['file']}:{f['line_num']}  \"{f['term']}\"")
            print()
    else:
        print("  (none)")
        print()

    # Summary
    print("-" * 60)
    print(f"Summary: {len(violations)} violations, "
          f"{len(exceptions)} exceptions")
    print(f"Files scanned: {len(files)}")

    if violations:
        print(f"\nResult: FAIL ({len(violations)} violations)")
        sys.exit(1)
    else:
        print("\nResult: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
