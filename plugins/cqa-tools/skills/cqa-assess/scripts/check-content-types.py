#!/usr/bin/env python3
"""Validate content type compliance in AsciiDoc modular documentation.

Checks that every module file has:
1. Correct filename prefix matching :_mod-docs-content-type:
2. Required structural elements ([role="_abstract"], [id="..._{context}"])
3. No invalid block titles for the content type
4. No == subsections in PROCEDURE files

CQA parameters: P2, P3, P4, P5, P6, P7
Skill: cqa-modularization

Usage:
    python3 check-content-types.py <DOCS_DIR>

Exit codes:
    0 - No issues found
    1 - Issues found
    2 - Invalid arguments (e.g., docs_dir is not a directory)
"""

import argparse
import os
import re
import sys

# Mapping from filename prefix to expected content type
PREFIX_TO_TYPE = {
    "assembly_": "ASSEMBLY",
    "con_": "CONCEPT",
    "proc_": "PROCEDURE",
    "ref_": "REFERENCE",
    "snip_": "SNIPPET",
}

# Block titles that are PROCEDURE-only
PROCEDURE_ONLY_TITLES = {
    ".Prerequisites", ".Prerequisite",
    ".Procedure",
    ".Verification", ".Results", ".Result",
    ".Troubleshooting", ".Troubleshooting steps", ".Troubleshooting step",
    ".Next steps", ".Next step",
}

# Directories to scan (default; overridable via --scan-dirs)
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
                    files.append((filepath, rel_path, fname))
    return sorted(files, key=lambda x: x[1])


def get_prefix(filename):
    """Extract the content type prefix from a filename."""
    for prefix in PREFIX_TO_TYPE:
        if filename.startswith(prefix):
            return prefix
    return None


def parse_code_block_lines(lines):
    """Return a set of line indices inside code/literal/example blocks."""
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


def check_file(filepath, rel_path, filename, skip_prefix_check=False):
    """Check a single file for content type compliance.

    Args:
        filepath: Absolute path to the file.
        rel_path: Path relative to docs_dir.
        filename: Basename of the file.
        skip_prefix_check: If True, skip the PREFIX check and fall back to
            detecting the content type from :_mod-docs-content-type:.

    Returns a list of issue dicts.
    """
    issues = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return issues

    lines = content.splitlines()
    code_lines = parse_code_block_lines(lines)

    # 1. Check filename prefix
    prefix = get_prefix(filename)
    if prefix is None:
        if skip_prefix_check:
            # Try to detect content type from :_mod-docs-content-type: attribute
            declared_type = None
            for line in lines:
                m = re.match(r'^:_mod-docs-content-type:\s*(\S+)', line)
                if m:
                    declared_type = m.group(1).upper()
                    break
            if declared_type is None:
                # Neither prefix nor declared type — skip this file entirely
                return issues
            expected_type = declared_type
        else:
            issues.append({
                "file": rel_path,
                "check": "PREFIX",
                "message": f"No recognized prefix. Expected one of: {', '.join(PREFIX_TO_TYPE.keys())}",
            })
            # Cannot do further checks without knowing expected type
            return issues
    else:
        expected_type = PREFIX_TO_TYPE[prefix]

    # 2. Check :_mod-docs-content-type: attribute
    # When prefix was None and skip_prefix_check is True, declared_type was
    # already read in the fallback path above — no need to re-read or check
    # for mismatch (there is no prefix to mismatch against).
    if prefix is not None:
        declared_type = None
        for line in lines:
            m = re.match(r'^:_mod-docs-content-type:\s*(\S+)', line)
            if m:
                declared_type = m.group(1).upper()
                break

        if declared_type is None:
            issues.append({
                "file": rel_path,
                "check": "CONTENT_TYPE_MISSING",
                "message": f"Missing :_mod-docs-content-type: attribute. Expected: {expected_type}",
            })
        elif declared_type != expected_type:
            issues.append({
                "file": rel_path,
                "check": "CONTENT_TYPE_MISMATCH",
                "message": f"Prefix '{prefix}' expects {expected_type} but declared {declared_type}",
            })

    # Snippets have fewer requirements — skip remaining checks
    if expected_type == "SNIPPET":
        return issues

    # 3. Check for [role="_abstract"]
    has_abstract = False
    for line in lines:
        if '[role="_abstract"]' in line:
            has_abstract = True
            break
    if not has_abstract:
        issues.append({
            "file": rel_path,
            "check": "ABSTRACT_MISSING",
            "message": "Missing [role=\"_abstract\"] annotation",
        })

    # 4. Check for [id="..._{context}"]
    has_id = False
    for line in lines:
        if re.search(r'\[id="[^"]+_\{context\}"\]', line):
            has_id = True
            break
    if not has_id:
        issues.append({
            "file": rel_path,
            "check": "ID_MISSING",
            "message": "Missing [id=\"..._{context}\"] anchor",
        })

    # 5. Check for procedure-only block titles in non-procedure files
    if expected_type != "PROCEDURE":
        for i, line in enumerate(lines):
            if i in code_lines:
                continue
            stripped = line.strip()
            for title in PROCEDURE_ONLY_TITLES:
                if stripped == title:
                    issues.append({
                        "file": rel_path,
                        "check": "INVALID_BLOCK_TITLE",
                        "message": f"Line {i + 1}: '{title}' is only allowed in PROCEDURE files",
                        "line_num": i + 1,
                    })

    # 6. Check for == subsections in PROCEDURE files
    if expected_type == "PROCEDURE":
        for i, line in enumerate(lines):
            if i in code_lines:
                continue
            stripped = line.strip()
            if stripped.startswith("== "):
                issues.append({
                    "file": rel_path,
                    "check": "PROC_SUBSECTION",
                    "message": f"Line {i + 1}: '== ' subsections are not allowed in PROCEDURE files",
                    "line_num": i + 1,
                })

    # 7. Check that .Procedure has ordered list items (not unordered)
    if expected_type == "PROCEDURE":
        in_procedure = False
        found_procedure = False
        for i, line in enumerate(lines):
            if i in code_lines:
                continue
            stripped = line.strip()
            if stripped == ".Procedure":
                in_procedure = True
                found_procedure = True
                continue
            if in_procedure:
                # Skip blank lines and continuations
                if stripped == "" or stripped == "+":
                    continue
                # Skip comments
                if stripped.startswith("//"):
                    continue
                # First content line after .Procedure must start with ". "
                if not stripped.startswith(". "):
                    # Could be a role annotation or attribute — skip those
                    if stripped.startswith("[") or stripped.startswith(":"):
                        continue
                    issues.append({
                        "file": rel_path,
                        "check": "PROC_NOT_ORDERED",
                        "message": f"Line {i + 1}: Content after .Procedure should use ordered list ('. ')",
                        "line_num": i + 1,
                    })
                in_procedure = False  # Only check first content line

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Validate content type compliance in modular docs."
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
    parser.add_argument(
        "--no-prefix-check",
        action="store_true",
        default=False,
        help="Skip filename prefix check. Detect content type from "
             ":_mod-docs-content-type: attribute instead.",
    )
    args = parser.parse_args()

    docs_dir = os.path.abspath(args.docs_dir)
    if not os.path.isdir(docs_dir):
        print(f"Error: {docs_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    print("Content Type Compliance Check")
    print("=" * 60)
    print(f"Scanning: {docs_dir}")
    print(f"Directories: {', '.join(args.scan_dirs)}")
    print(f"Excluding: {', '.join(SKIP_DIRS)}")
    if args.no_prefix_check:
        print("Prefix check: DISABLED (using :_mod-docs-content-type: fallback)")
    print()

    files = collect_adoc_files(docs_dir, scan_dirs=args.scan_dirs)
    all_issues = []
    for filepath, rel_path, filename in files:
        all_issues.extend(check_file(filepath, rel_path, filename,
                                     skip_prefix_check=args.no_prefix_check))

    # Group by check type
    by_check = {}
    for issue in all_issues:
        by_check.setdefault(issue["check"], []).append(issue)

    # Report by category
    check_order = [
        ("PREFIX", "Filename prefix issues"),
        ("CONTENT_TYPE_MISSING", "Missing :_mod-docs-content-type:"),
        ("CONTENT_TYPE_MISMATCH", "Content type mismatches (prefix vs declared)"),
        ("ABSTRACT_MISSING", "Missing [role=\"_abstract\"]"),
        ("ID_MISSING", "Missing [id=\"..._{context}\"]"),
        ("INVALID_BLOCK_TITLE", "Procedure-only block titles in wrong file type"),
        ("PROC_SUBSECTION", "== subsections in PROCEDURE files"),
        ("PROC_NOT_ORDERED", "Non-ordered list after .Procedure"),
    ]

    for check_key, label in check_order:
        items = by_check.get(check_key, [])
        print(f"{label}:")
        if items:
            for item in items:
                line_info = f":{item['line_num']}" if "line_num" in item else ""
                print(f"  {item['file']}{line_info}")
                print(f"    {item['message']}")
            print()
        else:
            print("  (none)")
            print()

    # Summary
    print("-" * 60)
    print(f"Summary: {len(all_issues)} issues across {len(files)} files")

    if all_issues:
        # Count by type
        for check_key, label in check_order:
            count = len(by_check.get(check_key, []))
            if count > 0:
                print(f"  {label}: {count}")
        print(f"\nResult: FAIL ({len(all_issues)} issues)")
        sys.exit(1)
    else:
        print("\nResult: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
