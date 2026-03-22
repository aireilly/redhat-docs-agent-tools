#!/usr/bin/env python3
"""Check copyright and legal notice compliance in a documentation repository.

Verifies:
1. LICENSE or LICENCE file exists at repo root
2. docinfo.xml exists in each titles/*/ directory
3. Copyright year is current or covers the publication period

CQA parameters: O2
Skill: cqa-legal-branding

Usage:
    python3 check-legal-notices.py <DOCS_DIR>

Exit codes:
    0 - All checks pass
    1 - Issues found
    2 - Invalid arguments (e.g., docs_dir is not a directory)
"""

import argparse
import os
import re
import sys
from datetime import datetime


def find_repo_root(start_dir):
    """Walk up from start_dir looking for a .git directory.

    Returns the parent directory containing .git, or None if not found.
    """
    current = os.path.abspath(start_dir)
    while True:
        if os.path.isdir(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            # Reached filesystem root without finding .git
            return None
        current = parent


def check_license_file(docs_dir):
    """Check that a LICENSE or LICENCE file exists at the repo root."""
    for name in ["LICENSE", "LICENCE", "LICENSE.md", "LICENSE.txt"]:
        path = os.path.join(docs_dir, name)
        if os.path.isfile(path):
            return True, name, path
    return False, None, None


def find_title_dirs(docs_dir):
    """Find all titles/*/ directories."""
    titles_dir = os.path.join(docs_dir, "titles")
    if not os.path.isdir(titles_dir):
        return []
    result = []
    for entry in sorted(os.listdir(titles_dir)):
        full_path = os.path.join(titles_dir, entry)
        if os.path.isdir(full_path):
            result.append((entry, full_path))
    return result


def check_docinfo(title_dir, title_name):
    """Check docinfo.xml in a title directory.

    Returns (exists, has_copyright, copyright_year, path)
    """
    docinfo_path = os.path.join(title_dir, "docinfo.xml")
    if not os.path.isfile(docinfo_path):
        return False, False, None, docinfo_path

    try:
        with open(docinfo_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return True, False, None, docinfo_path

    # Look for copyright year patterns
    # Common patterns: <year>2024</year>, Copyright 2024, (c) 2024
    year_match = re.search(r'<year>(\d{4})</year>', content)
    if year_match:
        return True, True, int(year_match.group(1)), docinfo_path

    # Year range with copyright context: Copyright 2020-2024 / © 2020–2024
    # Check ranges BEFORE single-year to avoid matching only the first year.
    year_match = re.search(
        r'(?:Copyright|©|\(c\)|All rights reserved)[^\n]{0,80}?(\d{4})\s*[-\u2013]\s*(\d{4})',
        content,
        re.IGNORECASE,
    )
    if year_match:
        return True, True, int(year_match.group(2)), docinfo_path

    year_match = re.search(r'(?:Copyright|©|\(c\))\s*(\d{4})', content, re.IGNORECASE)
    if year_match:
        return True, True, int(year_match.group(1)), docinfo_path

    return True, False, None, docinfo_path


def main():
    parser = argparse.ArgumentParser(
        description="Check copyright and legal notice compliance."
    )
    parser.add_argument(
        "docs_dir",
        help="Path to the documentation directory (or repository root)",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root where LICENSE file should be found. "
             "If not specified, auto-detects by walking up from docs_dir "
             "looking for a .git directory. Falls back to docs_dir.",
    )
    args = parser.parse_args()

    docs_dir = os.path.abspath(args.docs_dir)
    if not os.path.isdir(docs_dir):
        print(f"Error: {docs_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    # Determine the repo root for the LICENSE check
    if args.repo_root is not None:
        repo_root = os.path.abspath(args.repo_root)
    else:
        detected = find_repo_root(docs_dir)
        repo_root = detected if detected is not None else docs_dir

    current_year = datetime.now().year

    print("Copyright and Legal Notice Check")
    print("=" * 60)
    print(f"Scanning: {docs_dir}")
    if repo_root != docs_dir:
        print(f"Repo root (for LICENSE): {repo_root}")
    print(f"Current year: {current_year}")
    print()

    issues = []

    # 1. Check LICENSE file (uses repo_root, not docs_dir)
    print("1. License file:")
    found, name, path = check_license_file(repo_root)
    if found:
        print(f"   FOUND: {name}")
        # Check if it's non-empty
        if os.path.getsize(path) == 0:
            print("   WARNING: File is empty")
            issues.append(f"License file {name} is empty")
    else:
        print("   MISSING: No LICENSE or LICENCE file found at repo root")
        issues.append("No LICENSE/LICENCE file at repo root")
    print()

    # 2. Check docinfo.xml in each title directory
    print("2. Document metadata (docinfo.xml):")
    titles_path = os.path.join(docs_dir, "titles")
    title_dirs = find_title_dirs(docs_dir)
    if not os.path.isdir(titles_path):
        print("   No titles/ directory found")
        issues.append("No titles/ directory found")
    elif not title_dirs:
        print("   titles/ directory exists but contains no title subdirectories")
        issues.append("titles/ directory exists but contains no title subdirectories")
    else:
        for title_name, title_dir in title_dirs:
            exists, has_copyright, year, docinfo_path = check_docinfo(title_dir, title_name)
            rel_path = os.path.relpath(docinfo_path, docs_dir)

            if not exists:
                print(f"   {title_name}/: MISSING docinfo.xml")
                issues.append(f"Missing docinfo.xml in titles/{title_name}/")
            elif not has_copyright:
                print(f"   {title_name}/: docinfo.xml found but no copyright year detected")
                issues.append(f"No copyright year in {rel_path}")
            elif year < current_year:
                print(f"   {title_name}/: docinfo.xml found, copyright year {year} (current: {current_year})")
                # Outdated year is a warning, not a hard failure
                # The year might be correct if the guide was last published that year
                print(f"   NOTE: Copyright year may need updating to {current_year}")
            else:
                print(f"   {title_name}/: docinfo.xml found, copyright year {year}")
    print()

    # Summary
    print("-" * 60)
    print(f"Summary: {len(issues)} issues")
    if issues:
        for issue in issues:
            print(f"  - {issue}")
        print(f"\nResult: FAIL ({len(issues)} issues)")
        sys.exit(1)
    else:
        print("\nResult: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
