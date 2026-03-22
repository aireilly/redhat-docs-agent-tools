#!/usr/bin/env python3
"""Resolve the full include tree from an AsciiDoc file.

Recursively follows include:: directives to build a complete list
of files included by a master.adoc or assembly file. Useful for
scoping CQA checks to only the files relevant to a specific guide
or assembly.

Usage:
    python3 resolve-includes.py <FILE>
    python3 resolve-includes.py master.adoc --base-dir /path/to/titles/admin_guide/
    python3 resolve-includes.py assembly_foo.adoc --format tree
    python3 resolve-includes.py master.adoc --format json --include-root

Exit codes:
    0 - All includes resolved
    1 - Some includes could not be resolved
    2 - Invalid arguments
"""

import argparse
import json
import os
import re
import sys
from collections import OrderedDict

# Regex to match AsciiDoc include directives.
# Captures:
#   group 1: optional ifdef/ifndef condition prefix (e.g., "ifdef::attr[]")
#   group 2: the include path
#   group 3: the attributes inside brackets (e.g., "leveloffset=+1")
INCLUDE_RE = re.compile(
    r'^'
    r'(?:(ifdef|ifndef)::([^\[]*)\[(?:\])?\s*)?'  # optional conditional prefix
    r'include::([^\[]+)'                           # include::PATH
    r'\[([^\]]*)\]'                                # [ATTRS]
    r'\s*$'
)

# Simpler patterns for separate detection
CONDITIONAL_RE = re.compile(r'^(ifdef|ifndef)::([^\[]+)\[')
INCLUDE_DIRECTIVE_RE = re.compile(r'include::([^\[]+)\[([^\]]*)\]')

# Matches AsciiDoc attribute references like {snippets-dir}, {prod-short}
ATTR_REF_RE = re.compile(r'\{[\w_][\w_-]*\}')


def parse_include_line(line):
    """Parse a single line for include directives.

    Returns a dict with keys:
        path: the raw include path
        attrs: the bracket attributes string
        conditional: None or (type, condition) tuple
        line_text: the original line

    Returns None if the line is not an include directive.
    """
    stripped = line.strip()
    if not stripped:
        return None

    # Skip AsciiDoc comments
    if stripped.startswith("//"):
        return None

    conditional = None

    # Check for conditional include (ifdef/ifndef wrapping an include)
    # Pattern: ifdef::ATTR[] \n include::PATH[] \n endif::[]
    # But also inline: ifdef::ATTR[include::PATH[]]
    cond_match = CONDITIONAL_RE.match(stripped)
    if cond_match:
        cond_type = cond_match.group(1)  # ifdef or ifndef
        cond_attr = cond_match.group(2)  # the condition attribute
        conditional = (cond_type, cond_attr)
        # Check if the include is on the same line (inline conditional)
        remaining = stripped[cond_match.end():]
        inc_match = INCLUDE_DIRECTIVE_RE.search(remaining)
        if inc_match:
            return {
                "path": inc_match.group(1),
                "attrs": inc_match.group(2),
                "conditional": conditional,
                "line_text": stripped,
            }
        # If no include on same line, this is just the conditional opener
        return None

    # Standard include directive
    inc_match = INCLUDE_DIRECTIVE_RE.match(stripped)
    if inc_match:
        return {
            "path": inc_match.group(1),
            "attrs": inc_match.group(2),
            "conditional": conditional,
            "line_text": stripped,
        }

    return None


def has_unresolved_attributes(path):
    """Check if a path contains unresolved AsciiDoc attribute references."""
    return bool(ATTR_REF_RE.search(path))


def resolve_include_path(include_path, current_file_dir, base_dir):
    """Resolve an include path to an absolute filesystem path.

    In Red Hat modular docs, include paths are relative to the file
    containing them. However, symlinks in titles/*/ directories
    (assemblies -> ../../assemblies, topics -> ../../topics, etc.)
    make paths resolve correctly through the symlink chain.

    Args:
        include_path: The raw path from the include:: directive
        current_file_dir: Directory of the file containing the include
        base_dir: The base directory for resolution (usually the title dir)

    Returns:
        Absolute path if resolved, None if not found
    """
    # First, try resolving relative to the current file's directory.
    # This handles the common case and works with symlinks.
    candidate = os.path.normpath(os.path.join(current_file_dir, include_path))
    if os.path.isfile(candidate):
        return os.path.realpath(candidate)

    # Second, try resolving relative to the base directory.
    # This handles cases where includes are written relative to the
    # title directory (e.g., include::topics/admin/foo.adoc[]).
    candidate = os.path.normpath(os.path.join(base_dir, include_path))
    if os.path.isfile(candidate):
        return os.path.realpath(candidate)

    return None


def resolve_includes(filepath, base_dir, visited=None, depth=0, results=None,
                     tree=None, warnings=None, conditional_context=None):
    """Recursively resolve all includes from a file.

    Args:
        filepath: Absolute path to the current file
        base_dir: Base directory for resolving include paths
        visited: Set of already-visited real paths (cycle detection)
        depth: Current recursion depth (for tree output)
        results: OrderedDict mapping real_path -> info dict
        tree: List of (depth, path, info) tuples for tree output
        warnings: List of warning messages
        conditional_context: Enclosing ifdef/ifndef context from parent

    Returns:
        (results, tree, warnings, has_errors)
    """
    if visited is None:
        visited = set()
    if results is None:
        results = OrderedDict()
    if tree is None:
        tree = []
    if warnings is None:
        warnings = []

    real_path = os.path.realpath(filepath)

    # Cycle detection
    if real_path in visited:
        return results, tree, warnings, False
    visited.add(real_path)

    # Read the file
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (IOError, UnicodeDecodeError) as e:
        warnings.append(f"Cannot read {filepath}: {e}")
        return results, tree, warnings, True

    current_dir = os.path.dirname(os.path.abspath(filepath))
    has_errors = False

    # Track ifdef/ifndef blocks for conditional context
    active_conditional = None

    for line in lines:
        stripped = line.strip()

        # Track conditional blocks
        cond_match = CONDITIONAL_RE.match(stripped)
        if cond_match and "include::" not in stripped:
            active_conditional = (cond_match.group(1), cond_match.group(2))
            continue

        if stripped.startswith("endif::"):
            active_conditional = None
            continue

        parsed = parse_include_line(line)
        if parsed is None:
            continue

        include_path = parsed["path"]
        conditional = parsed["conditional"] or active_conditional

        # Check for unresolved attributes in the path
        if has_unresolved_attributes(include_path):
            warnings.append(
                f"Unresolved attribute in include path: "
                f"include::{include_path}[] "
                f"(in {os.path.relpath(filepath, base_dir)})"
            )
            info = {
                "raw_path": include_path,
                "resolved": False,
                "conditional": conditional,
                "depth": depth + 1,
                "reason": "unresolved_attribute",
            }
            tree.append((depth + 1, include_path, info))
            has_errors = True
            continue

        # Resolve the path
        resolved = resolve_include_path(include_path, current_dir, base_dir)

        if resolved is None:
            warnings.append(
                f"Include not found: include::{include_path}[] "
                f"(in {os.path.relpath(filepath, base_dir)})"
            )
            info = {
                "raw_path": include_path,
                "resolved": False,
                "conditional": conditional,
                "depth": depth + 1,
                "reason": "file_not_found",
            }
            tree.append((depth + 1, include_path, info))
            has_errors = True
            continue

        rel_resolved = os.path.relpath(resolved, base_dir)

        info = {
            "raw_path": include_path,
            "resolved": True,
            "absolute_path": resolved,
            "relative_path": rel_resolved,
            "conditional": conditional,
            "depth": depth + 1,
        }

        tree.append((depth + 1, rel_resolved, info))

        # Add to results (avoid duplicates but keep first occurrence info)
        if resolved not in results:
            results[resolved] = info

        # Recurse into the included file
        _, _, _, child_errors = resolve_includes(
            resolved, base_dir, visited, depth + 1, results, tree,
            warnings, conditional
        )
        if child_errors:
            has_errors = True

    return results, tree, warnings, has_errors


def format_files(results, base_dir, include_root, root_file):
    """Format output as one file path per line, sorted."""
    paths = set()
    if include_root:
        paths.add(os.path.relpath(os.path.realpath(root_file), base_dir))
    for real_path, info in results.items():
        if info.get("resolved", False):
            paths.add(info["relative_path"])
    return "\n".join(sorted(paths))


def format_tree(tree_data, base_dir, include_root, root_file):
    """Format output as an indented tree showing nesting."""
    lines = []
    if include_root:
        root_rel = os.path.relpath(os.path.realpath(root_file), base_dir)
        lines.append(root_rel)

    for depth, path, info in tree_data:
        indent = "  " * depth
        conditional_marker = ""
        if info.get("conditional"):
            cond_type, cond_attr = info["conditional"]
            conditional_marker = f" [{cond_type}::{cond_attr}]"

        if not info.get("resolved", False):
            reason = info.get("reason", "unknown")
            if reason == "unresolved_attribute":
                lines.append(f"{indent}UNRESOLVED {path}{conditional_marker}")
            else:
                lines.append(f"{indent}MISSING {path}{conditional_marker}")
        else:
            lines.append(f"{indent}{path}{conditional_marker}")

    return "\n".join(lines)


def format_json(results, tree_data, warnings, base_dir, include_root,
                root_file, has_errors):
    """Format output as machine-readable JSON."""
    files = []
    if include_root:
        root_rel = os.path.relpath(os.path.realpath(root_file), base_dir)
        files.append({
            "path": root_rel,
            "resolved": True,
            "is_root": True,
            "depth": 0,
        })

    seen_paths = set()
    for real_path, info in results.items():
        rel = info.get("relative_path", info.get("raw_path"))
        if rel in seen_paths:
            continue
        seen_paths.add(rel)

        entry = {
            "path": rel,
            "resolved": info.get("resolved", False),
            "depth": info.get("depth", 0),
        }
        if info.get("conditional"):
            entry["conditional"] = {
                "type": info["conditional"][0],
                "attribute": info["conditional"][1],
            }
        if not info.get("resolved", False):
            entry["reason"] = info.get("reason", "unknown")
        files.append(entry)

    # Build the tree structure for JSON
    tree_entries = []
    for depth, path, info in tree_data:
        entry = {
            "path": path,
            "depth": depth,
            "resolved": info.get("resolved", False),
        }
        if info.get("conditional"):
            entry["conditional"] = {
                "type": info["conditional"][0],
                "attribute": info["conditional"][1],
            }
        if not info.get("resolved", False):
            entry["reason"] = info.get("reason", "unknown")
        tree_entries.append(entry)

    output = {
        "root_file": os.path.relpath(os.path.realpath(root_file), base_dir),
        "base_dir": os.path.abspath(base_dir),
        "total_files": len([f for f in files if f.get("resolved", False)]),
        "has_errors": has_errors,
        "files": sorted(
            [f for f in files if f.get("resolved", False)],
            key=lambda x: x["path"]
        ),
        "unresolved": [f for f in files if not f.get("resolved", False)],
        "tree": tree_entries,
        "warnings": warnings,
    }

    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Resolve the full include tree from an AsciiDoc file. "
            "Recursively follows include:: directives to list all files "
            "included by a master.adoc or assembly file."
        ),
        epilog=(
            "Examples:\n"
            "  %(prog)s master.adoc\n"
            "  %(prog)s master.adoc --base-dir titles/admin_guide/\n"
            "  %(prog)s assembly_foo.adoc --format tree\n"
            "  %(prog)s master.adoc --format json --include-root\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file",
        help="Path to the AsciiDoc file to resolve",
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help=(
            "Base directory for resolving paths and displaying relative "
            "paths. Defaults to the directory containing the input file."
        ),
    )
    parser.add_argument(
        "--format",
        choices=["files", "tree", "json"],
        default="files",
        dest="output_format",
        help="Output format (default: files)",
    )
    parser.add_argument(
        "--include-root",
        action="store_true",
        help="Also include the root file itself in the output",
    )

    args = parser.parse_args()

    # Validate input file
    input_file = os.path.abspath(args.file)
    if not os.path.isfile(input_file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(2)

    # Determine base directory
    if args.base_dir:
        base_dir = os.path.abspath(args.base_dir)
    else:
        base_dir = os.path.dirname(input_file)

    if not os.path.isdir(base_dir):
        print(f"Error: Base directory not found: {args.base_dir}",
              file=sys.stderr)
        sys.exit(2)

    # Resolve the include tree
    results, tree_data, warnings, has_errors = resolve_includes(
        input_file, base_dir
    )

    # Print warnings to stderr
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    # Format and print output
    if args.output_format == "files":
        output = format_files(results, base_dir, args.include_root, input_file)
    elif args.output_format == "tree":
        output = format_tree(
            tree_data, base_dir, args.include_root, input_file
        )
    elif args.output_format == "json":
        output = format_json(
            results, tree_data, warnings, base_dir, args.include_root,
            input_file, has_errors
        )

    if output:
        print(output)

    # Exit code
    if has_errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
