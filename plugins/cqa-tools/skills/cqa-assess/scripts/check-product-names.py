#!/usr/bin/env python3
"""Check for hardcoded product names in AsciiDoc documentation.

Searches active content for hardcoded product names that should use
AsciiDoc attributes instead. Handles known exceptions (UI labels,
plugin names, link text, code blocks, attribute definitions).

CQA parameters: P18, O1, O3
Skill: cqa-legal-branding

Usage:
    python3 check-product-names.py <DOCS_DIR>

Exit codes:
    0 - No violations found
    1 - Violations found
    2 - Invalid arguments (e.g., docs_dir is not a directory)
"""

import argparse
import json
import os
import re
import sys

# Product names to search for, ordered longest-first to avoid double-counting.
# Each tuple: (hardcoded_string, recommended_attribute)
PRODUCT_NAMES = [
    ("Red Hat OpenShift Dev Spaces", "{prod}"),
    ("OpenShift Container Platform", "{ocp}"),
    ("OpenShift Dev Spaces", "{prod-short}"),
    ("Dev Spaces", "{prod-short} or {prod2}"),
]

# Separate capitalization check
CASE_TYPO = ("Openshift", "OpenShift")

# Known legitimate hardcoded uses — exact substrings that are exceptions.
# UI button labels, plugin names, extension names.
KNOWN_EXCEPTIONS = [
    "Connect to Dev Spaces",
    "Gateway provider for OpenShift Dev Spaces",
    "OpenShift Dev Spaces plugin",
    "OpenShift Dev Spaces extension",
]

# Directories to scan (relative to DOCS_DIR)
DEFAULT_SCAN_DIRS = ["assemblies", "modules", "topics", "snippets"]

# Directories to skip entirely
SKIP_DIRS = {"legacy-content-do-not-use"}

# Files to skip (basename)
SKIP_FILES = {"attributes.adoc"}


def collect_adoc_files(docs_dir, scan_dirs=None):
    """Collect all .adoc files from scan directories, skipping exclusions."""
    if scan_dirs is None:
        scan_dirs = DEFAULT_SCAN_DIRS
    files = []
    for scan_dir in scan_dirs:
        full_dir = os.path.join(docs_dir, scan_dir)
        if not os.path.isdir(full_dir):
            continue
        for root, dirs, filenames in os.walk(full_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in filenames:
                if fname.endswith(".adoc") and fname not in SKIP_FILES:
                    filepath = os.path.join(root, fname)
                    rel_path = os.path.relpath(filepath, docs_dir)
                    files.append((filepath, rel_path))
    return sorted(files, key=lambda x: x[1])


def parse_code_block_lines(lines):
    """Return a set of line indices inside code, literal, passthrough, or comment blocks.

    Tracks a single block state so that delimiters nested inside another
    block type are treated as content rather than toggling a second block.
    Handles: ---- (source), .... (literal), ++++ (passthrough), //// (comment).
    """
    code_lines = set()
    current_block = None  # None, "-", ".", "+", "/"

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Detect block delimiters: ---- .... ++++ ////
        matched_char = None
        for delim_char in ("-", ".", "+", "/"):
            prefix = delim_char * 4
            if (stripped.startswith(prefix) and len(stripped) >= 4
                    and all(c == delim_char for c in stripped)):
                matched_char = delim_char
                break

        if matched_char is not None and current_block in (None, matched_char):
            code_lines.add(i)
            current_block = None if current_block == matched_char else matched_char
            continue

        if current_block is not None:
            code_lines.add(i)
    return code_lines


def find_product_names(line):
    """Find all hardcoded product names in a line, avoiding double-counting.

    Returns list of (position, matched_text, replacement) tuples.
    Processes patterns longest-first so shorter patterns don't match
    substrings already claimed by longer patterns.
    """
    matches = []
    consumed = set()

    for name, replacement in PRODUCT_NAMES:
        start = 0
        while True:
            idx = line.find(name, start)
            if idx == -1:
                break
            match_range = set(range(idx, idx + len(name)))
            if not match_range.intersection(consumed):
                matches.append((idx, name, replacement))
                consumed.update(match_range)
            start = idx + 1

    # Separate check for "Openshift" (lowercase S) typo
    start = 0
    while True:
        idx = line.find(CASE_TYPO[0], start)
        if idx == -1:
            break
        match_range = set(range(idx, idx + len(CASE_TYPO[0])))
        if not match_range.intersection(consumed):
            matches.append((idx, CASE_TYPO[0], CASE_TYPO[1]))
            consumed.update(match_range)
        start = idx + 1

    return sorted(matches, key=lambda x: x[0])


def is_inside_pattern(line, match_start, match_end, regex):
    """Check if position range falls inside a regex capture group."""
    for m in re.finditer(regex, line):
        bracket_start = m.start(1)
        bracket_end = m.end(1)
        if match_start >= bracket_start and match_end <= bracket_end:
            return True
    return False


def classify_match(line, match_start, matched_text):
    """Classify a match as a violation or an exception.

    Returns one of:
        COMMENT        - inside an AsciiDoc comment
        ATTRIBUTE_DEF  - attribute definition line
        KNOWN_EXCEPTION - matches a known UI label/plugin name
        UI_LABEL       - inside backtick delimiters
        LINK_TEXT      - inside link:...[text] brackets
        XREF_TEXT      - inside xref:...[text] brackets
        IMAGE_ALT      - inside image::[alt] brackets (should use attributes)
        PROSE          - body text (violation)
    """
    stripped = line.strip()
    match_end = match_start + len(matched_text)

    # Comment line
    if stripped.startswith("//"):
        return "COMMENT"

    # Attribute definition (e.g., :prod-short: OpenShift Dev Spaces)
    if re.match(r"^:\w[\w-]*:", stripped):
        return "ATTRIBUTE_DEF"

    # Known exception (UI label, plugin name)
    for exc in KNOWN_EXCEPTIONS:
        # Check every occurrence of the exception on this line
        for exc_match in re.finditer(re.escape(exc), line):
            if match_start >= exc_match.start() and match_end <= exc_match.end():
                return "KNOWN_EXCEPTION"

    # Inside backticks (UI label or command)
    # Find all backtick-delimited regions
    in_backtick = False
    backtick_start = -1
    for i, ch in enumerate(line):
        if ch == "`":
            if in_backtick:
                # Closing backtick — check if match falls within
                if match_start > backtick_start and match_end <= i:
                    return "UI_LABEL"
                in_backtick = False
            else:
                in_backtick = True
                backtick_start = i

    # Inside link text: link:URL[text]
    if is_inside_pattern(line, match_start, match_end, r"link:[^\[]*\[([^\]]*)\]"):
        return "LINK_TEXT"

    # Inside xref text: xref:id[text]
    if is_inside_pattern(line, match_start, match_end, r"xref:[^\[]*\[([^\]]*)\]"):
        return "XREF_TEXT"

    # Inside image alt text: image::path[alt text]
    if is_inside_pattern(line, match_start, match_end, r"image::[^\[]*\[([^\]]*)\]"):
        return "IMAGE_ALT"

    # Everything else is prose
    return "PROSE"


def check_file(filepath, rel_path):
    """Check a single file for hardcoded product names.

    Returns (findings_list, error_string_or_None).
    """
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, OSError) as exc:
        return findings, f"{rel_path}: {exc}"

    lines = content.splitlines()
    code_lines = parse_code_block_lines(lines)

    for line_idx, line in enumerate(lines):
        if line_idx in code_lines:
            continue

        matches = find_product_names(line)
        for pos, matched_text, replacement in matches:
            classification = classify_match(line, pos, matched_text)
            findings.append({
                "file": rel_path,
                "line_num": line_idx + 1,
                "line": line.rstrip(),
                "match": matched_text,
                "replacement": replacement,
                "classification": classification,
            })

    return findings, None


def _is_inside_backticks(line, match_start, match_end):
    """Check if a match range falls inside backtick-delimited text."""
    in_backtick = False
    backtick_start = -1
    for ci, ch in enumerate(line):
        if ch != "`":
            continue
        if in_backtick:
            if match_start > backtick_start and match_end <= ci:
                return True
            in_backtick = False
        else:
            in_backtick = True
            backtick_start = ci
    return False


def _is_exception_at(line, match_start, match_end):
    """Check if a product name occurrence at the given position is an exception.

    Returns True if the occurrence is inside a known exception string,
    backtick-delimited text, link text, or xref text.
    """
    # Known exception strings (UI labels, plugin names)
    for exc in KNOWN_EXCEPTIONS:
        for exc_match in re.finditer(re.escape(exc), line):
            if match_start >= exc_match.start() and match_end <= exc_match.end():
                return True

    if _is_inside_backticks(line, match_start, match_end):
        return True

    if is_inside_pattern(line, match_start, match_end,
                         r"link:[^\[]*\[([^\]]*)\]"):
        return True

    if is_inside_pattern(line, match_start, match_end,
                         r"xref:[^\[]*\[([^\]]*)\]"):
        return True

    return False


def _replace_name_in_line(line, name, attr):
    """Replace all non-exception occurrences of a product name in a line.

    Returns (modified_line, replacement_count).
    """
    if name not in line:
        return line, 0

    result = ""
    search_start = 0
    count = 0
    while True:
        idx = line.find(name, search_start)
        if idx == -1:
            result += line[search_start:]
            break
        match_end = idx + len(name)
        if _is_exception_at(line, idx, match_end):
            result += line[search_start:match_end]
        else:
            result += line[search_start:idx] + attr
            count += 1
        search_start = match_end
    return result, count


def _fix_file(abs_path):
    """Apply product name replacements to a single file.

    Returns the number of replacements made, or 0 if the file could not
    be read or had no replaceable occurrences.
    """
    try:
        with open(abs_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except (UnicodeDecodeError, OSError):
        return 0

    lines = content.splitlines(True)  # keep line endings
    code_lines = parse_code_block_lines([l.rstrip("\n\r") for l in lines])

    new_lines = []
    replacements_made = 0

    for line_idx, line in enumerate(lines):
        if line_idx in code_lines:
            new_lines.append(line)
            continue
        stripped = line.strip()
        if stripped.startswith("//") or re.match(r"^:\w[\w-]*:", stripped):
            new_lines.append(line)
            continue

        modified_line = line
        for name, replacement in PRODUCT_NAMES:
            attr = replacement.split(" or ")[0].strip()
            modified_line, count = _replace_name_in_line(modified_line, name, attr)
            replacements_made += count
        new_lines.append(modified_line)

    if replacements_made > 0:
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write("".join(new_lines))

    return replacements_made


def apply_fixes(findings, docs_dir):
    """Apply automatic fixes for PROSE and IMAGE_ALT violations.

    Replaces hardcoded product names with recommended attributes in-place.
    Processes replacements longest-match-first within each line to avoid
    double-replacing overlapping matches.

    Returns the total number of replacements made.
    """
    fixable = [f for f in findings if f["classification"] in ("PROSE", "IMAGE_ALT")]
    if not fixable:
        return 0

    # Collect unique file paths that have fixable findings
    file_paths = set()
    for f in fixable:
        file_paths.add(os.path.join(docs_dir, f["file"]))

    total_replacements = 0
    for abs_path in sorted(file_paths):
        total_replacements += _fix_file(abs_path)

    return total_replacements


def main():
    parser = argparse.ArgumentParser(
        description="Check for hardcoded product names in AsciiDoc docs."
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
    parser.add_argument(
        "--config",
        help="Path to a JSON config file for customizing product names, "
             "exceptions, and skip patterns per repository",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix PROSE and IMAGE_ALT violations by replacing "
             "hardcoded product names with recommended attributes",
    )
    args = parser.parse_args()

    docs_dir = os.path.abspath(args.docs_dir)
    if not os.path.isdir(docs_dir):
        print(f"Error: {docs_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    # Apply config overrides if provided
    global PRODUCT_NAMES, CASE_TYPO, KNOWN_EXCEPTIONS, SKIP_DIRS, SKIP_FILES
    if args.config:
        config_path = os.path.abspath(args.config)
        try:
            with open(config_path, "r", encoding="utf-8") as cf:
                config = json.load(cf)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error: failed to read config file: {exc}", file=sys.stderr)
            sys.exit(2)
        if "product_names" in config:
            PRODUCT_NAMES = [tuple(pair) for pair in config["product_names"]]
        if "case_typos" in config:
            CASE_TYPO = tuple(config["case_typos"][0]) if config["case_typos"] else None
        if "known_exceptions" in config:
            KNOWN_EXCEPTIONS = list(config["known_exceptions"])
        if "skip_dirs" in config:
            SKIP_DIRS = set(config["skip_dirs"])
        if "skip_files" in config:
            SKIP_FILES = set(config["skip_files"])

    print("Product Name Check")
    print("=" * 60)
    print(f"Scanning: {docs_dir}")
    print(f"Directories: {', '.join(args.scan_dirs)}")
    print(f"Excluding: {', '.join(SKIP_DIRS)}, {', '.join(SKIP_FILES)}")
    print()

    files = collect_adoc_files(docs_dir, scan_dirs=args.scan_dirs)
    if not files:
        print("Error: no .adoc files found under "
              f"{', '.join(args.scan_dirs)}", file=sys.stderr)
        sys.exit(2)

    all_findings = []
    read_errors = []
    for filepath, rel_path in files:
        findings, error = check_file(filepath, rel_path)
        all_findings.extend(findings)
        if error is not None:
            read_errors.append(error)

    if read_errors:
        for error in read_errors:
            print(f"Error: failed to read {error}", file=sys.stderr)
        sys.exit(2)

    # Group by classification
    violations = [f for f in all_findings if f["classification"] == "PROSE"]
    image_alt = [f for f in all_findings if f["classification"] == "IMAGE_ALT"]
    exceptions = [f for f in all_findings if f["classification"] in (
        "KNOWN_EXCEPTION", "UI_LABEL", "LINK_TEXT", "XREF_TEXT"
    )]
    skipped = [f for f in all_findings if f["classification"] in (
        "COMMENT", "ATTRIBUTE_DEF"
    )]

    # Report violations
    print("VIOLATIONS (hardcoded product names in prose):")
    if violations:
        for f in violations:
            print(f"  {f['file']}:{f['line_num']}")
            print(f"    Found: \"{f['match']}\" -> use {f['replacement']}")
            print(f"    Line:  {f['line']}")
            print()
    else:
        print("  (none)")
    print()

    # Report image alt text issues
    print("IMAGE ALT TEXT (should use attributes):")
    if image_alt:
        for f in image_alt:
            print(f"  {f['file']}:{f['line_num']}")
            print(f"    Found: \"{f['match']}\" -> use {f['replacement']}")
            print(f"    Line:  {f['line']}")
            print()
    else:
        print("  (none)")
    print()

    # Report exceptions (informational)
    print("EXCEPTIONS (automatically excluded — no action needed):")
    if exceptions:
        for f in exceptions:
            print(f"  {f['file']}:{f['line_num']}  [{f['classification']}]")
            print(f"    \"{f['match']}\" in: {f['line'].strip()}")
        print()
    else:
        print("  (none)")
        print()

    # Summary
    total_issues = len(violations) + len(image_alt)
    print("-" * 60)
    print(f"Summary: {len(violations)} violations, "
          f"{len(image_alt)} image alt text issues, "
          f"{len(exceptions)} exceptions, "
          f"{len(skipped)} skipped (comments/attributes)")
    print(f"Files scanned: {len(files)}")

    if args.fix and total_issues > 0:
        num_fixed = apply_fixes(all_findings, docs_dir)
        print(f"\n--fix: {num_fixed} replacements made across files.")

    if total_issues > 0:
        print(f"\nResult: FAIL ({total_issues} issues found)")
        sys.exit(1)
    else:
        print("\nResult: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
