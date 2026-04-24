#!/usr/bin/env python3
"""Validate AsciiDoc cross-references, includes, and image references.

Checks performed:
  1. Broken xrefs    — every xref target must match a declared [id="..."]
  2. Missing includes — every include::path[] must resolve to an existing file
  3. Missing images   — every image::path[] must resolve to an existing file
  4. Duplicate IDs    — no two files should declare the same [id="..."]

Supports both {context}-suffixed and plain IDs, file-based xrefs
(xref:file.adoc#anchor[]), and auto-discovers :imagesdir: from
attributes.adoc.

CQA parameters: P12
Skill: cqa-links

Usage:
    python3 validate-refs.py <DOCS_DIR> [--scan-dirs DIR...]

Exit codes:
    0  All checks passed
    1  Validation errors found
    2  Invalid arguments
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_SCAN_DIRS = ["assemblies", "modules", "topics", "snippets", "titles"]

# Regex patterns — broad to handle all Red Hat docs conventions
ID_PATTERN = re.compile(r'\[id="(.+?)"\]')
XREF_PATTERN = re.compile(r"xref:([^\[]+)\[")
INCLUDE_PATTERN = re.compile(r"include::([^\[]+)\[")
IMAGE_BLOCK_PATTERN = re.compile(r"image::([^\[]+)\[")


def find_imagesdir(docs_dir):
    """Find :imagesdir: from attributes.adoc, default to 'images'."""
    common_dir = os.path.join(docs_dir, "common")
    if os.path.isdir(common_dir):
        for fname in sorted(os.listdir(common_dir)):
            if fname.endswith("attributes.adoc"):
                fpath = os.path.join(common_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        for line in f:
                            m = re.match(r"^:imagesdir:\s+(.+)$", line.strip())
                            if m:
                                return m.group(1).strip()
                except (OSError, UnicodeDecodeError):
                    continue
    return "images"


def collect_adoc_files(docs_dir, scan_dirs):
    """Collect all .adoc files from scan directories."""
    files = []
    seen = set()
    for d in scan_dirs:
        dirpath = Path(docs_dir) / d
        if not dirpath.exists():
            continue
        for fpath in sorted(dirpath.rglob("*.adoc")):
            # Resolve symlinks to avoid double-counting
            resolved = fpath.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append(fpath)
    return files


def read_file_list(file_list_path, docs_dir):
    """Read a file list from a file or stdin."""
    if file_list_path == "-":
        lines = sys.stdin.read().splitlines()
    else:
        with open(file_list_path) as f:
            lines = f.read().splitlines()
    files = []
    for line in lines:
        line = line.strip()
        if not line or not line.endswith(".adoc"):
            continue
        filepath = Path(docs_dir) / line
        if filepath.is_file():
            files.append(filepath)
    return sorted(files)


def rel(filepath, docs_dir):
    """Return a display-friendly path relative to docs_dir."""
    try:
        return str(Path(filepath).relative_to(docs_dir))
    except ValueError:
        return str(filepath)


def is_comment(line):
    """Check if a line is an AsciiDoc comment."""
    return line.lstrip().startswith("//")


def collect_ids(files):
    """Collect all [id="..."] declarations.

    Returns dict mapping full ID string to list of (filepath, lineno).
    A list is used to detect duplicates.
    """
    ids = defaultdict(list)
    for filepath in files:
        try:
            with open(filepath, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    if is_comment(line):
                        continue
                    for m in ID_PATTERN.finditer(line):
                        ids[m.group(1)].append((filepath, lineno))
        except (OSError, UnicodeDecodeError):
            pass
    return ids


def collect_xrefs(files):
    """Collect all xref:TARGET[] references.

    Returns list of (target, filepath, lineno).
    Handles both plain xrefs and file-based xrefs (xref:file.adoc#anchor[]).
    Skips targets with unresolved attributes (except {context}).
    """
    xrefs = []
    for filepath in files:
        try:
            with open(filepath, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    if is_comment(line):
                        continue
                    for m in XREF_PATTERN.finditer(line):
                        target = m.group(1)
                        # Skip targets with unresolved attributes
                        # (but allow {context} which is intentional)
                        cleaned = target.replace("{context}", "")
                        if "{" in cleaned or "}" in cleaned:
                            continue
                        xrefs.append((target, filepath, lineno))
        except (OSError, UnicodeDecodeError):
            pass
    return xrefs


def check_xrefs(xrefs, ids, docs_dir):
    """Check xrefs against declared IDs.

    Handles:
    - Direct ID match: xref:some-id_{context}[] -> [id="some-id_{context}"]
    - File-based: xref:file.adoc#anchor[] -> file exists AND anchor is an ID
    - Plain: xref:some-id[] -> [id="some-id"]
    """
    broken = []

    for target, filepath, lineno in xrefs:
        # File-based xref: xref:file.adoc#anchor[...]
        if ".adoc#" in target:
            file_part, anchor = target.split("#", 1)
            # Try resolving the file relative to the referencing file's dir
            ref_dir = Path(filepath).parent
            resolved_file = (ref_dir / file_part).resolve()
            if not resolved_file.is_file():
                # Try relative to docs_dir
                resolved_file = (Path(docs_dir) / file_part).resolve()
            if not resolved_file.is_file():
                broken.append((filepath, lineno, target, "referenced file not found"))
                continue
            # Check anchor exists as an ID (if anchor is provided)
            if anchor and anchor not in ids:
                broken.append(
                    (filepath, lineno, target, f"anchor '{anchor}' not found in {file_part}")
                )
            continue

        # File-based xref without anchor: xref:file.adoc[...]
        if target.endswith(".adoc"):
            ref_dir = Path(filepath).parent
            resolved_file = (ref_dir / target).resolve()
            if not resolved_file.is_file():
                resolved_file = (Path(docs_dir) / target).resolve()
            if not resolved_file.is_file():
                broken.append((filepath, lineno, target, "referenced file not found"))
            continue

        # Standard ID-based xref
        if target not in ids:
            broken.append((filepath, lineno, target, "no matching [id] found"))

    return broken


def check_includes(files, docs_dir):
    """Verify every include:: target resolves to an existing file.

    Tries resolving relative to the including file's directory first,
    then relative to docs_dir.
    """
    errors = []
    for filepath in files:
        file_dir = Path(filepath).parent
        try:
            with open(filepath, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    if is_comment(line):
                        continue
                    m = INCLUDE_PATTERN.search(line)
                    if not m:
                        continue
                    inc_path = m.group(1)
                    # Skip attribute-based paths
                    if "{" in inc_path:
                        continue
                    # Try relative to file directory (follows symlinks)
                    resolved = (file_dir / inc_path).resolve()
                    if resolved.is_file():
                        continue
                    # Try relative to docs_dir
                    resolved2 = (Path(docs_dir) / inc_path).resolve()
                    if resolved2.is_file():
                        continue
                    errors.append((filepath, lineno, inc_path))
        except (OSError, UnicodeDecodeError):
            pass
    return errors


def check_images(files, docs_dir, imagesdir):
    """Verify every image:: target resolves to an existing file."""
    errors = []
    images_path = Path(docs_dir) / imagesdir
    for filepath in files:
        file_dir = Path(filepath).parent
        try:
            with open(filepath, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    if is_comment(line):
                        continue
                    m = IMAGE_BLOCK_PATTERN.search(line)
                    if not m:
                        continue
                    img_path = m.group(1)
                    # Skip attribute-based paths
                    if "{" in img_path:
                        continue
                    # Try under imagesdir at docs root
                    resolved = images_path / img_path
                    if resolved.is_file():
                        continue
                    # Try relative to file directory (for symlinked titles/)
                    resolved2 = file_dir / imagesdir / img_path
                    if resolved2.is_file():
                        continue
                    errors.append((filepath, lineno, img_path))
        except (OSError, UnicodeDecodeError):
            pass
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate AsciiDoc cross-references, includes, " "and images."
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
    parser.add_argument(
        "--file-list",
        default=None,
        help="File with paths to check (one per line, relative to "
        "docs_dir). Use '-' for stdin. Overrides --scan-dirs.",
    )
    args = parser.parse_args()

    docs_dir = os.path.abspath(args.docs_dir)
    if not os.path.isdir(docs_dir):
        print(f"Error: {docs_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    # Auto-discover imagesdir from attributes.adoc
    imagesdir = find_imagesdir(docs_dir)

    if args.file_list:
        adoc_files = read_file_list(args.file_list, docs_dir)
    else:
        adoc_files = collect_adoc_files(docs_dir, args.scan_dirs)

    print(f"Scanning {len(adoc_files)} AsciiDoc files in {docs_dir} ...")
    print("  Scan dirs: {}".format(", ".join(args.scan_dirs)))
    print(f"  Images dir: {imagesdir}")
    print()

    total_errors = 0

    # --- Check 1: Broken cross-references ---
    ids = collect_ids(adoc_files)
    xrefs = collect_xrefs(adoc_files)
    broken_xrefs = check_xrefs(xrefs, ids, docs_dir)

    if broken_xrefs:
        print(f"BROKEN XREFS ({len(broken_xrefs)})")
        print("-" * 60)
        for filepath, lineno, target, reason in sorted(broken_xrefs):
            print(f"  {rel(filepath, docs_dir)}:{lineno}")
            print(f"    xref:{target}[] — {reason}")
        print()
    total_errors += len(broken_xrefs)

    # --- Check 2: Missing includes ---
    missing_includes = check_includes(adoc_files, docs_dir)

    if missing_includes:
        print(f"MISSING INCLUDES ({len(missing_includes)})")
        print("-" * 60)
        for filepath, lineno, inc_path in sorted(missing_includes):
            print(f"  {rel(filepath, docs_dir)}:{lineno}")
            print(f"    include::{inc_path} — file not found")
        print()
    total_errors += len(missing_includes)

    # --- Check 3: Missing images ---
    missing_images = check_images(adoc_files, docs_dir, imagesdir)

    if missing_images:
        print(f"MISSING IMAGES ({len(missing_images)})")
        print("-" * 60)
        for filepath, lineno, img_path in sorted(missing_images):
            print(f"  {rel(filepath, docs_dir)}:{lineno}")
            print(f"    image::{img_path} — file not found under {imagesdir}/")
        print()
    total_errors += len(missing_images)

    # --- Check 4: Duplicate IDs ---
    duplicates = {k: v for k, v in ids.items() if len(v) > 1}

    if duplicates:
        print(f"DUPLICATE IDS ({len(duplicates)})")
        print("-" * 60)
        for id_val, locations in sorted(duplicates.items()):
            print(f'  [id="{id_val}"] declared in:')
            for filepath, lineno in locations:
                print(f"    {rel(filepath, docs_dir)}:{lineno}")
        print()
    total_errors += len(duplicates)

    # --- Summary ---
    print("=" * 60)
    print(f"  Files scanned:      {len(adoc_files)}")
    print(f"  IDs declared:       {len(ids)}")
    print(f"  Xrefs checked:      {len(xrefs)}")
    print(f"  Broken xrefs:       {len(broken_xrefs)}")
    print(f"  Missing includes:   {len(missing_includes)}")
    print(f"  Missing images:     {len(missing_images)}")
    print(f"  Duplicate IDs:      {len(duplicates)}")
    print("=" * 60)

    if total_errors > 0:
        print(f"\n  FAILED — {total_errors} error(s) found\n")
        return 1
    else:
        print("\n  PASSED — all references valid\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
