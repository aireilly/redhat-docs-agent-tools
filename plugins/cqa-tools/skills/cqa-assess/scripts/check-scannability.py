#!/usr/bin/env python3
"""Check content scannability: sentence length and paragraph length.

Analyzes prose in AsciiDoc documentation for scannability issues:
- Flags sentences over 30 words
- Reports files with average sentence length over 22 words
- Flags paragraphs with more than 4 sentences

Properly handles AsciiDoc structure: each list item is treated as an
independent unit, code blocks are skipped, definition lists and table
content are excluded.

CQA parameters: Q1
Skill: cqa-editorial

Usage:
    python3 check-scannability.py <DOCS_DIR>

Exit codes:
    0 - No violations found
    1 - Violations found
    2 - Invalid arguments (e.g., docs_dir is not a directory)
"""

import argparse
import os
import re
import sys

# Directories to scan (relative to DOCS_DIR)
DEFAULT_SCAN_DIRS = ["assemblies", "modules", "topics"]

# Directories to skip
SKIP_DIRS = {"legacy-content-do-not-use"}

# Sentence length thresholds
HARD_LIMIT = 30
AVG_LIMIT = 22
MAX_PARAGRAPH_SENTENCES = 4

# Minimum sentences in a file to flag for high average
MIN_SENTENCES_FOR_AVG = 3

# AsciiDoc attribute word counts, populated at runtime from attributes.adoc.
# Fallback: attributes not in this dict are counted as 1 word.
ATTR_WORD_COUNTS = {}


def parse_attributes(docs_dir):
    """Parse attributes.adoc files from the common/ directory.

    Discovers any file ending with 'attributes.adoc' under DOCS_DIR/common/.
    Returns a dict mapping attribute names to raw (unresolved) values.
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
    Uses cycle detection to avoid infinite recursion.
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


def parse_attributes_for_word_counts(docs_dir):
    """Build ATTR_WORD_COUNTS from attributes.adoc.

    Parses all attribute files, resolves nested references, and counts
    words in each resolved value. Returns a dict mapping attribute names
    to word counts.
    """
    raw_attrs = parse_attributes(docs_dir)
    attr_word_counts = {}
    for attr_name, raw in raw_attrs.items():
        resolved = resolve_value(raw, raw_attrs)
        if "{" in resolved:
            continue  # still has unresolved refs — skip, fallback to 1
        words = resolved.split()
        count = len([w for w in words if w])
        if count > 0:
            attr_word_counts[attr_name] = count
    return attr_word_counts


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


def find_block_ranges(lines):
    """Return a set of line indices inside code/literal/passthrough blocks."""
    block_lines = set()
    in_block = False
    block_delim = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Check for block delimiters: ----, ...., ++++, |===, ,=== (CSV tables)
        # CSV/TSV table delimiters (,=== |===) have mixed chars, handle separately
        is_delim = False
        matched_key = None
        if re.match(r"^[,|]={3,}$", stripped):
            is_delim = True
            matched_key = stripped[0]  # ',' or '|'
        else:
            for delim in ("----", "....", "++++"):
                if stripped.startswith(delim) and all(c == delim[0] for c in stripped):
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
    """Check if a line should be skipped entirely (not prose)."""
    s = line.strip()
    if not s:
        return True
    # Comments
    if s.startswith("//"):
        return True
    # Attribute definitions
    if re.match(r"^:[\w_][\w_-]*:", s):
        return True
    # Block attributes/annotations: [source,...], [role=...], [id=...], etc.
    if s.startswith("["):
        return True
    # Include/image/ifdef directives
    if re.match(r"^(include|image|ifdef|ifndef|endif|ifeval)::", s):
        return True
    # Headings
    if re.match(r"^={1,5}\s", s):
        return True
    # Table delimiters and rows
    if s.startswith("|"):
        return True
    # Block delimiters (should be caught by find_block_ranges, but be safe)
    if re.match(r"^(-{4,}|\.{4,}|\+{4,}|\*{4,}|={4,})$", s):
        return True
    # List continuation marker
    if s == "+":
        return True
    # Block titles
    if re.match(r"^\.\w", s) and not s.startswith(".. "):
        return True
    # Standalone "or", "and", "where:" between code blocks
    if s in ("or", "and", "where:"):
        return True
    # Pass macros on their own line
    if s.startswith("pass:"):
        return True
    return False


def is_list_item(line):
    """Check if a line starts a new list item."""
    s = line.strip()
    # Unordered: *, **, ***
    if re.match(r"^\*{1,3}\s", s):
        return True
    # Ordered: ., .., ...
    if re.match(r"^\.{1,3}\s", s):
        return True
    return False


def is_definition_list(line):
    """Check if a line is a definition list entry (term:: description).

    Matches patterns like:
    - ``term``:: description
    - Term:: description
    - lowercase_term:: description
    Excludes AsciiDoc directives (include::, image::, ifdef::, etc.).
    """
    s = line.strip()
    if re.search(r"::\s*$", s) or re.search(r"::\s+\S", s):
        # Exclude AsciiDoc directives (include::, image::, ifdef::, etc.)
        if re.match(r"^(include|image|ifdef|ifndef|endif|ifeval)::", s):
            return False
        # Match backtick-quoted terms, uppercase terms, or any non-directive term
        if s.startswith("`") or re.match(r"^[A-Z]", s):
            return True
        # Also match lowercase definition list terms (e.g., "storage::")
        if re.match(r"^[a-z]", s):
            return True
    return False


def is_link_only_item(line):
    """Check if a list item contains only a link/xref (no prose to check).

    Uses fullmatch to ensure the entire content after the list marker is a
    single link or xref — items like ``* xref:foo[Install] to prepare``
    contain trailing prose and must NOT be skipped.
    """
    s = line.strip()
    # Remove unordered or ordered list markers
    content = re.sub(r"^(?:\*{1,3}|\.{1,3})\s+", "", s)
    # Require the entire remaining content to be a single link/xref
    if re.fullmatch(
        r"(?:xref:\S+\[[^\]]*\]|link:\S+\[[^\]]*\]|<<[^>]+>>)",
        content,
    ):
        return True
    return False


def count_words(text):
    """Count words in a prose string, accounting for AsciiDoc markup."""
    # Remove backtick literals (count as 1 word each)
    text = re.sub(r"`[^`]*`", "X", text)
    # Remove link/xref macros, keep link text only
    text = re.sub(r"link:\S+\[([^\]]*)\]", r"\1", text)
    text = re.sub(r"xref:\S+\[([^\]]*)\]", r"\1", text)
    # Remove pass macros
    text = re.sub(r"pass:\S+\[[^\]]*\]", "X", text)
    # Remove bold/italic markers
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)

    # Handle attributes: replace with appropriate word count
    def attr_replacer(m):
        attr_name = m.group(1)
        wc = ATTR_WORD_COUNTS.get(attr_name, 1)
        return " ".join(["W"] * wc)

    text = re.sub(r"\{([\w-]+)\}", attr_replacer, text)
    # Remove list markers
    text = re.sub(r"^\s*[\*\.]{1,3}\s+", "", text)
    # Remove admonition prefixes
    text = re.sub(r"^(NOTE|TIP|IMPORTANT|WARNING|CAUTION):\s*", "", text)
    # Split and count
    words = text.split()
    words = [w for w in words if re.search(r"[a-zA-Z0-9]", w)]
    return len(words)


def split_sentences(text):
    """Split text into sentences."""
    text = text.strip()
    if not text:
        return []
    # Split on sentence-ending punctuation followed by space + uppercase
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\{])", text)
    return [p.strip() for p in parts if p.strip()]


def check_file(filepath, rel_path):
    """Check a single file for scannability issues."""
    try:
        with open(filepath, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return {"long_sentences": [], "long_paragraphs": [], "all_counts": [], "file_avg": 0}

    block_lines = find_block_ranges(lines)
    long_sentences = []
    long_paragraphs = []
    all_counts = []

    # Process lines into prose units.
    # A prose unit is either: a standalone paragraph, or a single list item.
    # List items are independent — never concatenated.
    current_unit = []
    current_start = 0

    def process_unit(unit_lines, start_line):
        """Process a prose unit (paragraph or single list item)."""
        if not unit_lines:
            return
        text = " ".join(unit_lines)
        sentences = split_sentences(text)
        valid_sentences = []
        for sent in sentences:
            wc = count_words(sent)
            if wc < 3:
                continue
            valid_sentences.append((sent, wc))
            all_counts.append(wc)
            if wc > HARD_LIMIT:
                long_sentences.append(
                    {
                        "line": start_line + 1,
                        "words": wc,
                        "text": sent[:150] + ("..." if len(sent) > 150 else ""),
                    }
                )
        if len(valid_sentences) > MAX_PARAGRAPH_SENTENCES:
            long_paragraphs.append(
                {
                    "line": start_line + 1,
                    "sentences": len(valid_sentences),
                }
            )

    for i, line in enumerate(lines):
        # Skip block content
        if i in block_lines:
            process_unit(current_unit, current_start)
            current_unit = []
            continue

        # Skip non-prose lines
        if is_skip_line(line):
            process_unit(current_unit, current_start)
            current_unit = []
            continue

        # Skip definition list entries
        if is_definition_list(line):
            process_unit(current_unit, current_start)
            current_unit = []
            continue

        # Skip link-only list items
        if is_link_only_item(line):
            process_unit(current_unit, current_start)
            current_unit = []
            continue

        stripped = line.strip()

        # List items start a new unit (each item is independent)
        if is_list_item(line):
            process_unit(current_unit, current_start)
            current_unit = [stripped]
            current_start = i
            continue

        # Blank line ends current unit
        if not stripped:
            process_unit(current_unit, current_start)
            current_unit = []
            continue

        # Continuation of current unit
        if not current_unit:
            current_start = i
        current_unit.append(stripped)

    # Process any remaining unit
    process_unit(current_unit, current_start)

    total = len(all_counts)
    file_avg = sum(all_counts) / total if total else 0

    return {
        "long_sentences": long_sentences,
        "long_paragraphs": long_paragraphs,
        "all_counts": all_counts,
        "file_avg": file_avg,
        "total_sentences": total,
    }


def main():
    parser = argparse.ArgumentParser(description="Check content scannability in AsciiDoc docs.")
    parser.add_argument(
        "docs_dir",
        help="Path to the documentation repository root",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show high-average and long-paragraph details",
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
        help="File with paths to check (one per line, relative to docs_dir). Use '-' for stdin. Overrides --scan-dirs.",
    )
    args = parser.parse_args()

    docs_dir = os.path.abspath(args.docs_dir)
    if not os.path.isdir(docs_dir):
        print(f"Error: {docs_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    # Populate ATTR_WORD_COUNTS from attributes.adoc at runtime
    global ATTR_WORD_COUNTS
    ATTR_WORD_COUNTS = parse_attributes_for_word_counts(docs_dir)
    if not ATTR_WORD_COUNTS:
        print(
            "Warning: No attributes parsed from attributes.adoc — "
            "attribute word counts will default to 1",
            file=sys.stderr,
        )

    print("Content Scannability Check")
    print("=" * 60)
    print(f"Scanning: {docs_dir}")
    print(f"Directories: {', '.join(args.scan_dirs)}")
    print(
        f"Thresholds: sentence >{HARD_LIMIT} words, "
        f"avg >{AVG_LIMIT} words/sentence, "
        f"paragraph >{MAX_PARAGRAPH_SENTENCES} sentences"
    )
    print()

    if args.file_list:
        files = read_file_list(args.file_list, docs_dir)
    else:
        files = collect_adoc_files(docs_dir, args.scan_dirs)
    all_word_counts = []
    violations = []
    high_avg_files = []
    long_para_files = []

    for filepath, rel_path in files:
        result = check_file(filepath, rel_path)
        all_word_counts.extend(result["all_counts"])

        if result["long_sentences"]:
            violations.append((rel_path, result["long_sentences"]))

        if result["file_avg"] > AVG_LIMIT and result["total_sentences"] >= MIN_SENTENCES_FOR_AVG:
            high_avg_files.append((rel_path, result["file_avg"], result["total_sentences"]))

        if result["long_paragraphs"]:
            long_para_files.append((rel_path, result["long_paragraphs"]))

    # Report: Long sentences (violations)
    total_violations = sum(len(s) for _, s in violations)
    print(f"LONG SENTENCES (>{HARD_LIMIT} words): {total_violations}")
    if violations:
        for rel_path, sentences in violations:
            for s in sentences:
                print(f"  {rel_path}:{s['line']}  ({s['words']} words)")
                print(f"    {s['text']}")
                print()
    else:
        print("  (none)")
    print()

    # Report: High average (informational)
    print(
        f"HIGH AVERAGE (>{AVG_LIMIT} words/sentence, "
        f"min {MIN_SENTENCES_FOR_AVG} sentences): "
        f"{len(high_avg_files)} files"
    )
    if args.verbose and high_avg_files:
        high_avg_files.sort(key=lambda x: x[1], reverse=True)
        for rel_path, avg, count in high_avg_files:
            print(f"  {rel_path}  (avg {avg:.1f}, {count} sentences)")
    print()

    # Report: Long paragraphs (informational)
    total_long_paras = sum(len(p) for _, p in long_para_files)
    print(f"LONG PARAGRAPHS (>{MAX_PARAGRAPH_SENTENCES} sentences): " f"{total_long_paras}")
    if args.verbose and long_para_files:
        for rel_path, paragraphs in long_para_files:
            for p in paragraphs:
                print(f"  {rel_path}:{p['line']}  " f"({p['sentences']} sentences)")
    print()

    # Metrics
    total_sentences = len(all_word_counts)
    overall_avg = sum(all_word_counts) / total_sentences if total_sentences else 0
    under_target = sum(1 for w in all_word_counts if w <= AVG_LIMIT)
    pct_under = (under_target / total_sentences * 100) if total_sentences else 0

    print("-" * 60)
    print("METRICS:")
    print(f"  Files scanned:              {len(files)}")
    print(f"  Total sentences:            {total_sentences}")
    print(f"  Overall avg words/sentence: {overall_avg:.1f}")
    print(
        f"  Sentences <={AVG_LIMIT} words:      "
        f"{under_target}/{total_sentences} ({pct_under:.1f}%)"
    )
    print(f"  Sentences >{HARD_LIMIT} words:       {total_violations}")
    print(f"  Files with high avg:        {len(high_avg_files)}")
    print(f"  Long paragraphs:            {total_long_paras}")

    if total_violations > 0:
        print(f"\nResult: FAIL ({total_violations} sentences exceed " f"{HARD_LIMIT}-word limit)")
        sys.exit(1)
    else:
        print("\nResult: PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
