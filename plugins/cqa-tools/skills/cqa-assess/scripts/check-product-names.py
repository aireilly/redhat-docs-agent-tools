#!/usr/bin/env python3
"""Check for hardcoded product names in AsciiDoc documentation.

Searches active content for hardcoded product names that should use
AsciiDoc attributes instead. Product names are auto-discovered from
the repo's common/attributes.adoc — no hardcoded product data.

Optionally verifies detected names against the Red Hat Official Product
List (OPL) API with --verify-opl (VPN required).

CQA parameters: P18, O1, O3
Skill: cqa-legal-branding

Usage:
    python3 check-product-names.py <DOCS_DIR>
    python3 check-product-names.py <DOCS_DIR> --verify-opl
    python3 check-product-names.py <DOCS_DIR> --config overrides.json

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
import urllib.parse
import urllib.request

# Directories to scan (relative to DOCS_DIR)
DEFAULT_SCAN_DIRS = ["assemblies", "modules", "topics", "snippets"]

# Directories to skip entirely
SKIP_DIRS = {"legacy-content-do-not-use"}

# OPL API (Official Product List) — shared read-only key
OPL_BASE = "https://opl-ui.apps.int.gpc.ocp-hub.prod.psi.redhat.com/api/v1"
OPL_KEY = "PW5pDaUCh-YMeZ0a-1FGW_0tZHm6IZCrT2qMiwJstkY"


# ── Attribute parsing ────────────────────────────────────────────────


def parse_attributes(docs_dir):
    """Parse attributes.adoc files from the common/ directory.

    Auto-discovers any file ending with 'attributes.adoc' under
    DOCS_DIR/common/ (handles attributes.adoc, _attributes.adoc, etc.).

    Returns a dict of {attr_name: raw_value}.
    """
    attr_values = {}
    common_dir = os.path.join(docs_dir, "common")
    if not os.path.isdir(common_dir):
        return attr_values
    for fname in sorted(os.listdir(common_dir)):
        if fname.endswith("attributes.adoc"):
            fpath = os.path.join(common_dir, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    for line in f:
                        m = re.match(r"^:([a-zA-Z][\w-]*):\s+(.+)$", line.strip())
                        if m:
                            attr_values[m.group(1)] = m.group(2).strip()
            except (OSError, UnicodeDecodeError):
                continue
    return attr_values


def resolve_value(raw, all_attrs, _seen=None):
    """Resolve nested attribute references and {nbsp}.

    Handles patterns like:
        :prod: Red Hat {prod-short}
        :RHEL: {RH} Enterprise{nbsp}Linux
    Detects cycles to prevent infinite recursion.
    """
    if _seen is None:
        _seen = set()

    def replacer(m):
        ref = m.group(1)
        if ref == "nbsp":
            return " "
        if ref in _seen or ref not in all_attrs:
            return m.group(0)  # leave unresolved
        return resolve_value(all_attrs[ref], all_attrs, _seen | {ref})

    return re.sub(r"\{([\w-]+)\}", replacer, raw)


def is_product_name(resolved_value):
    """Heuristic: is this resolved attribute value a product/brand name?

    Returns True if the value looks like a product name (contains
    capitalized words, is not a URL, version, path, or image ref).
    """
    v = resolved_value.strip()
    if not v:
        return False
    # Exclude URLs and macro-based values
    if re.match(r"^(https?://|link:|pass:|registry[./])", v, re.I):
        return False
    # Exclude pure version numbers (3.27, 4.19, 0.36.0)
    if re.match(r"^\d[\d.]*$", v):
        return False
    # Exclude paths and image references
    if "/" in v[1:]:
        return False
    # Exclude values with AsciiDoc formatting ('`oc`', etc.)
    if v.startswith("'") or v.startswith('"'):
        return False
    # Must contain at least one word starting with uppercase
    words = v.split()
    return any(w[0].isupper() for w in words if w and w[0].isalpha())


def build_product_names(docs_dir):
    """Build PRODUCT_NAMES entirely from attributes.adoc.

    Parses the repo's attribute files, resolves nested references,
    identifies product name values via heuristic, and returns a list
    of (resolved_name, "{attr-name}") tuples sorted longest-first.
    """
    raw_attrs = parse_attributes(docs_dir)
    if not raw_attrs:
        return [], raw_attrs

    product_names = []
    for attr_name, raw in raw_attrs.items():
        resolved = resolve_value(raw, raw_attrs)
        if "{" in resolved:
            continue  # still has unresolved refs
        if is_product_name(resolved):
            product_names.append((resolved, "{" + attr_name + "}"))

    # Sort longest-first for correct substring matching
    product_names.sort(key=lambda x: len(x[0]), reverse=True)
    return product_names, raw_attrs


def build_case_checks(product_names):
    """Auto-generate case-sensitivity checks from detected product names.

    Finds CamelCase words like "OpenShift", "DevWorkspace" and generates
    typo checks for common miscapitalizations ("Openshift", "Devworkspace").

    Returns list of (wrong_form, correct_form) tuples.
    """
    checks = []
    for name, _attr in product_names:
        for word in name.split():
            # Find words with internal capitals (CamelCase)
            if len(word) > 1 and any(c.isupper() for c in word[1:]):
                wrong = word.lower().capitalize()
                if wrong != word:
                    checks.append((wrong, word))
    return list(set(checks))


def collect_attribute_filenames(docs_dir):
    """Return a set of basenames for attribute files to skip during scan."""
    skip = set()
    common_dir = os.path.join(docs_dir, "common")
    if os.path.isdir(common_dir):
        for fname in os.listdir(common_dir):
            if fname.endswith("attributes.adoc"):
                skip.add(fname)
    return skip


# ── File collection ──────────────────────────────────────────────────


def collect_adoc_files(docs_dir, scan_dirs=None, skip_files=None):
    """Collect all .adoc files from scan directories, skipping exclusions."""
    if scan_dirs is None:
        scan_dirs = DEFAULT_SCAN_DIRS
    if skip_files is None:
        skip_files = set()
    files = []
    for scan_dir in scan_dirs:
        full_dir = os.path.join(docs_dir, scan_dir)
        if not os.path.isdir(full_dir):
            continue
        for root, dirs, filenames in os.walk(full_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in filenames:
                if fname.endswith(".adoc") and fname not in skip_files:
                    filepath = os.path.join(root, fname)
                    rel_path = os.path.relpath(filepath, docs_dir)
                    files.append((filepath, rel_path))
    return sorted(files, key=lambda x: x[1])


def read_file_list(file_list_path, docs_dir):
    """Read a file list from a file or stdin for guide-scoped scanning."""
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
        filepath = os.path.join(docs_dir, line)
        if os.path.isfile(filepath):
            files.append((filepath, line))
    return sorted(files, key=lambda x: x[1])


# ── Block parsing ────────────────────────────────────────────────────


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
            if (
                stripped.startswith(prefix)
                and len(stripped) >= 4
                and all(c == delim_char for c in stripped)
            ):
                matched_char = delim_char
                break

        if matched_char is not None and current_block in (None, matched_char):
            code_lines.add(i)
            current_block = None if current_block == matched_char else matched_char
            continue

        if current_block is not None:
            code_lines.add(i)
    return code_lines


# ── Match detection ──────────────────────────────────────────────────


def find_product_names(line, product_names, case_checks):
    """Find all hardcoded product names in a line, avoiding double-counting.

    Returns list of (position, matched_text, replacement) tuples.
    Processes patterns longest-first so shorter patterns don't match
    substrings already claimed by longer patterns.
    """
    matches = []
    consumed = set()

    for name, replacement in product_names:
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

    # Auto-generated case checks (e.g., "Openshift" → "OpenShift")
    for wrong, correct in case_checks:
        start = 0
        while True:
            idx = line.find(wrong, start)
            if idx == -1:
                break
            match_range = set(range(idx, idx + len(wrong)))
            if not match_range.intersection(consumed):
                matches.append((idx, wrong, correct))
                consumed.update(match_range)
            start = idx + 1

    return sorted(matches, key=lambda x: x[0])


# ── Match classification ─────────────────────────────────────────────


def is_inside_pattern(line, match_start, match_end, regex):
    """Check if position range falls inside a regex capture group."""
    for m in re.finditer(regex, line):
        bracket_start = m.start(1)
        bracket_end = m.end(1)
        if match_start >= bracket_start and match_end <= bracket_end:
            return True
    return False


def classify_match(line, match_start, matched_text, known_exceptions):
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
    for exc in known_exceptions:
        # Check every occurrence of the exception on this line
        for exc_match in re.finditer(re.escape(exc), line):
            if match_start >= exc_match.start() and match_end <= exc_match.end():
                return "KNOWN_EXCEPTION"

    # Inside backticks (UI label or command)
    in_backtick = False
    backtick_start = -1
    for i, ch in enumerate(line):
        if ch == "`":
            if in_backtick:
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


# ── File checking ────────────────────────────────────────────────────


def check_file(filepath, rel_path, product_names, case_checks, known_exceptions):
    """Check a single file for hardcoded product names.

    Returns (findings_list, error_string_or_None).
    """
    findings = []
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, OSError) as exc:
        return findings, f"{rel_path}: {exc}"

    lines = content.splitlines()
    code_lines = parse_code_block_lines(lines)

    for line_idx, line in enumerate(lines):
        if line_idx in code_lines:
            continue

        matches = find_product_names(line, product_names, case_checks)
        for pos, matched_text, replacement in matches:
            classification = classify_match(line, pos, matched_text, known_exceptions)
            findings.append(
                {
                    "file": rel_path,
                    "line_num": line_idx + 1,
                    "line": line.rstrip(),
                    "match": matched_text,
                    "replacement": replacement,
                    "classification": classification,
                }
            )

    return findings, None


# ── Auto-fix ─────────────────────────────────────────────────────────


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


def _is_exception_at(line, match_start, match_end, known_exceptions):
    """Check if a product name occurrence at the given position is an exception."""
    for exc in known_exceptions:
        for exc_match in re.finditer(re.escape(exc), line):
            if match_start >= exc_match.start() and match_end <= exc_match.end():
                return True

    if _is_inside_backticks(line, match_start, match_end):
        return True

    if is_inside_pattern(line, match_start, match_end, r"link:[^\[]*\[([^\]]*)\]"):
        return True

    if is_inside_pattern(line, match_start, match_end, r"xref:[^\[]*\[([^\]]*)\]"):
        return True

    return False


def _replace_name_in_line(line, name, attr, known_exceptions):
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
        if _is_exception_at(line, idx, match_end, known_exceptions):
            result += line[search_start:match_end]
        else:
            result += line[search_start:idx] + attr
            count += 1
        search_start = match_end
    return result, count


def _fix_file(abs_path, product_names, known_exceptions):
    """Apply product name replacements to a single file.

    Returns the number of replacements made.
    """
    try:
        with open(abs_path, encoding="utf-8") as fh:
            content = fh.read()
    except (UnicodeDecodeError, OSError):
        return 0

    lines = content.splitlines(True)  # keep line endings
    code_lines = parse_code_block_lines([line.rstrip("\n\r") for line in lines])

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
        for name, replacement in product_names:
            attr = replacement.split(" or ")[0].strip()
            modified_line, count = _replace_name_in_line(
                modified_line, name, attr, known_exceptions
            )
            replacements_made += count
        new_lines.append(modified_line)

    if replacements_made > 0:
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write("".join(new_lines))

    return replacements_made


def apply_fixes(findings, docs_dir, product_names, known_exceptions):
    """Apply automatic fixes for PROSE and IMAGE_ALT violations.

    Returns the total number of replacements made.
    """
    fixable = [f for f in findings if f["classification"] in ("PROSE", "IMAGE_ALT")]
    if not fixable:
        return 0

    file_paths = set()
    for f in fixable:
        file_paths.add(os.path.join(docs_dir, f["file"]))

    total_replacements = 0
    for abs_path in sorted(file_paths):
        total_replacements += _fix_file(abs_path, product_names, known_exceptions)

    return total_replacements


# ── OPL verification ─────────────────────────────────────────────────


def verify_with_opl(product_names):
    """Cross-check detected product names against the OPL API.

    Searches for the primary product name (longest detected value),
    retrieves its aliases, and reports:
    - Deprecated/previous names still in use
    - Unapproved aliases
    - Approved aliases missing from attributes.adoc
    """
    if not product_names:
        print("  OPL: No product names to verify.")
        return

    search_term = product_names[0][0]  # longest = most specific
    try:
        url = f"{OPL_BASE}/products" f"?q={urllib.parse.quote(search_term)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {OPL_KEY}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f"  OPL verification skipped: {e}", file=sys.stderr)
        print("  (Ensure VPN is connected for OPL access)", file=sys.stderr)
        return

    products = data.get("products", [])

    # Find best match: exact name first, then substring, then first result
    best = None
    for p in products:
        if p["product_name"].lower() == search_term.lower():
            best = p
            break
    if not best:
        for p in products:
            if search_term.lower() in p["product_name"].lower():
                best = p
                break
    if not best and products:
        best = products[0]
    if not best:
        print(f"  OPL: No products found matching '{search_term}'")
        return

    # Get aliases
    try:
        url = f"{OPL_BASE}/products/{best['product_id']}/aliases"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {OPL_KEY}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            aliases = json.loads(resp.read())
    except Exception as e:
        print(f"  OPL: Failed to fetch aliases: {e}", file=sys.stderr)
        return

    attr_values = {name for name, _ in product_names}
    print(f"\nOPL VERIFICATION (matched: {best['product_name']}):")
    print(f"  Product ID: {best['product_id']}")
    print(f"  Status: {best.get('product_status', 'unknown')}")

    issues = 0
    for alias in aliases:
        aname = alias["alias_name"]
        if aname in attr_values:
            if alias.get("previous_name"):
                print(f"  WARNING: '{aname}' is a deprecated/previous " f"name in OPL")
                issues += 1
            if not alias.get("alias_approved"):
                print(
                    f"  NOTE: '{aname}' is not an approved alias "
                    f"in OPL (type: {alias.get('alias_type', '?')})"
                )

    for alias in aliases:
        if alias.get("alias_approved") and alias["alias_name"] not in attr_values:
            print(
                f"  NOTE: OPL approved alias '{alias['alias_name']}' "
                f"not found in attributes.adoc"
            )

    if issues == 0:
        print("  All detected product names verified against OPL.")
    print()


# ── Main ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Check for hardcoded product names in AsciiDoc docs. "
        "Product names are auto-discovered from the repo's "
        "common/attributes.adoc."
    )
    parser.add_argument(
        "docs_dir",
        help="Path to the documentation repository root " "(must have common/*attributes.adoc)",
    )
    parser.add_argument(
        "--scan-dirs",
        nargs="+",
        default=DEFAULT_SCAN_DIRS,
        help=(
            "Directories to scan relative to docs_dir " f"(default: {' '.join(DEFAULT_SCAN_DIRS)})"
        ),
    )
    parser.add_argument(
        "--file-list",
        default=None,
        help="File with paths to check (one per line, relative to "
        "docs_dir). Use '-' for stdin. Overrides --scan-dirs.",
    )
    parser.add_argument(
        "--config",
        help="Path to a JSON config file for additional product names, "
        "exceptions, and skip patterns (merged with auto-detected)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix PROSE and IMAGE_ALT violations by replacing "
        "hardcoded product names with recommended attributes",
    )
    parser.add_argument(
        "--verify-opl",
        action="store_true",
        help="Cross-check detected product names against the Red Hat "
        "Official Product List API (VPN required)",
    )
    args = parser.parse_args()

    docs_dir = os.path.abspath(args.docs_dir)
    if not os.path.isdir(docs_dir):
        print(f"Error: {docs_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    # ── Build product names from attributes.adoc ──
    product_names, _ = build_product_names(docs_dir)
    case_checks = build_case_checks(product_names)
    known_exceptions = []
    skip_files = collect_attribute_filenames(docs_dir)

    if not product_names:
        print(
            "Error: no product name attributes found in " f"{docs_dir}/common/*attributes.adoc",
            file=sys.stderr,
        )
        print("Expected attribute files with product name definitions " "like:", file=sys.stderr)
        print("  :prod: Red Hat Product Name", file=sys.stderr)
        print("  :prod-short: Product Name", file=sys.stderr)
        sys.exit(2)

    # ── Apply config overrides (merge, not replace) ──
    if args.config:
        config_path = os.path.abspath(args.config)
        try:
            with open(config_path, encoding="utf-8") as cf:
                config = json.load(cf)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error: failed to read config file: {exc}", file=sys.stderr)
            sys.exit(2)
        if "product_names" in config:
            extra = [tuple(pair) for pair in config["product_names"]]
            product_names.extend(extra)
            product_names.sort(key=lambda x: len(x[0]), reverse=True)
        if "case_typos" in config:
            for pair in config["case_typos"]:
                case_checks.append(tuple(pair))
        if "known_exceptions" in config:
            known_exceptions.extend(config["known_exceptions"])
        if "skip_dirs" in config:
            SKIP_DIRS.update(config["skip_dirs"])
        if "skip_files" in config:
            skip_files.update(config["skip_files"])

    # ── Print header ──
    print("Product Name Check")
    print("=" * 60)
    print(f"Scanning: {docs_dir}")
    print(f"Directories: {', '.join(args.scan_dirs)}")
    print("Product names detected from attributes.adoc:")
    for name, attr in product_names:
        print(f'  {attr} = "{name}"')
    if case_checks:
        print(f"Case checks: {', '.join(w + ' → ' + c for w, c in case_checks)}")
    print()

    # ── Collect files ──
    if args.file_list:
        files = read_file_list(args.file_list, docs_dir)
    else:
        files = collect_adoc_files(docs_dir, scan_dirs=args.scan_dirs, skip_files=skip_files)
    if not files:
        print("Error: no .adoc files found under " f"{', '.join(args.scan_dirs)}", file=sys.stderr)
        sys.exit(2)

    # ── Check all files ──
    all_findings = []
    read_errors = []
    for filepath, rel_path in files:
        findings, error = check_file(
            filepath, rel_path, product_names, case_checks, known_exceptions
        )
        all_findings.extend(findings)
        if error is not None:
            read_errors.append(error)

    if read_errors:
        for error in read_errors:
            print(f"Error: failed to read {error}", file=sys.stderr)
        sys.exit(2)

    # ── Group by classification ──
    violations = [f for f in all_findings if f["classification"] == "PROSE"]
    image_alt = [f for f in all_findings if f["classification"] == "IMAGE_ALT"]
    exceptions = [
        f
        for f in all_findings
        if f["classification"] in ("KNOWN_EXCEPTION", "UI_LABEL", "LINK_TEXT", "XREF_TEXT")
    ]
    skipped = [f for f in all_findings if f["classification"] in ("COMMENT", "ATTRIBUTE_DEF")]

    # ── Report violations ──
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

    # ── Report image alt text issues ──
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

    # ── Report exceptions (informational) ──
    print("EXCEPTIONS (automatically excluded — no action needed):")
    if exceptions:
        for f in exceptions:
            print(f"  {f['file']}:{f['line_num']}  [{f['classification']}]")
            print(f"    \"{f['match']}\" in: {f['line'].strip()}")
        print()
    else:
        print("  (none)")
        print()

    # ── Summary ──
    total_issues = len(violations) + len(image_alt)
    print("-" * 60)
    print(
        f"Summary: {len(violations)} violations, "
        f"{len(image_alt)} image alt text issues, "
        f"{len(exceptions)} exceptions, "
        f"{len(skipped)} skipped (comments/attributes)"
    )
    print(f"Files scanned: {len(files)}")

    # ── Auto-fix ──
    if args.fix and total_issues > 0:
        num_fixed = apply_fixes(all_findings, docs_dir, product_names, known_exceptions)
        print(f"\n--fix: {num_fixed} replacements made across files.")

    # ── OPL verification ──
    if args.verify_opl:
        verify_with_opl(product_names)

    # ── Exit ──
    if total_issues > 0:
        print(f"\nResult: FAIL ({total_issues} issues found)")
        sys.exit(1)
    else:
        print("\nResult: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
