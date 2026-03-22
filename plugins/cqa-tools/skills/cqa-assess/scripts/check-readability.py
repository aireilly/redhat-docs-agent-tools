#!/usr/bin/env python3
"""Check content readability using Flesch-Kincaid Grade Level.

Computes the Flesch-Kincaid Grade Level for prose in AsciiDoc
documentation files. Reports overall grade, per-file grades, and
grade distribution.

The Flesch-Kincaid formula:
  FK Grade = 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59

Properly handles AsciiDoc structure: code blocks, tables, attributes,
definition lists, and other non-prose content are excluded.

CQA parameters: Q4
Skill: cqa-editorial

Usage:
    python3 check-readability.py <DOCS_DIR>

Exit codes:
    0 - Overall grade meets threshold (<=12)
    1 - Overall grade exceeds threshold (>12)
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

# Grade level thresholds
IDEAL_GRADE = 10       # Ideal target (9th-10th grade)
MIN_GRADE = 12         # Minimum requirement (11th-12th grade)

# Minimum sentences in a file to include in per-file analysis
MIN_SENTENCES = 10

# Known AsciiDoc attributes and their resolved text.
ATTR_RESOLVED = {
    "prod": "Red Hat OpenShift Dev Spaces",
    "prod-short": "OpenShift Dev Spaces",
    "prod-ver": "three",
    "prod-cli": "dsc",
    "orch-name": "OpenShift",
    "orch-cli": "oc",
    "orch-namespace": "project",
    "ocp": "OpenShift Container Platform",
    "kubernetes": "Kubernetes",
    "prod-namespace": "openshift-devspaces",
    "devworkspace": "Dev Workspace",
    "image-puller-name": "Kubernetes Image Puller",
    "docker-cli": "podman",
    "prod-id-short": "devspaces",
    "prod2": "Dev Spaces",
}

# Word counts for attributes (used by scannability-compatible counting)
ATTR_WORD_COUNTS = {
    "prod": 5,
    "prod-short": 3,
    "prod-ver": 1,
    "prod-cli": 1,
    "orch-name": 1,
    "orch-cli": 1,
    "orch-namespace": 1,
    "ocp": 3,
    "kubernetes": 1,
    "prod-namespace": 1,
    "devworkspace": 2,
    "image-puller-name": 3,
    "docker-cli": 1,
    "prod-id-short": 1,
    "prod2": 2,
}


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
    if s.startswith("//"):
        return True
    if re.match(r'^:[\w_][\w_-]*:', s):
        return True
    if s.startswith("["):
        return True
    if re.match(r'^(include|image|ifdef|ifndef|endif|ifeval)::', s):
        return True
    if re.match(r'^={1,5}\s', s):
        return True
    if s.startswith("|"):
        return True
    if re.match(r'^(-{4,}|\.{4,}|\+{4,}|\*{4,}|={4,})$', s):
        return True
    if s == "+":
        return True
    if re.match(r'^\.\w', s) and not s.startswith(".. "):
        return True
    if s in ("or", "and", "where:"):
        return True
    if s.startswith("pass:"):
        return True
    return False


def is_list_item(line):
    """Check if a line starts a new list item."""
    s = line.strip()
    if re.match(r'^\*{1,3}\s', s):
        return True
    if re.match(r'^\.{1,3}\s', s):
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
    if re.search(r'::\s*$', s) or re.search(r'::\s+\S', s):
        # Exclude AsciiDoc directives (include::, image::, ifdef::, etc.)
        if re.match(r'^(include|image|ifdef|ifndef|endif|ifeval)::', s):
            return False
        # Match backtick-quoted terms, uppercase terms, or any non-directive term
        if s.startswith("`") or re.match(r'^[A-Z]', s):
            return True
        # Also match lowercase definition list terms (e.g., "storage::")
        if re.match(r'^[a-z]', s):
            return True
    return False


def is_link_only_item(line):
    """Check if a list item contains only a link/xref (no prose to check)."""
    s = line.strip()
    # Remove unordered or ordered list markers
    content = re.sub(r'^(?:\*{1,3}|\.{1,3})\s+', '', s)
    # Require the entire remaining content to be a single link/xref
    if re.fullmatch(
        r'(?:xref:\S+\[[^\]]*\]|link:\S+\[[^\]]*\]|<<[^>]+>>)',
        content,
    ):
        return True
    return False


def count_words(text):
    """Count words in prose, accounting for AsciiDoc markup."""
    text = re.sub(r'`[^`]*`', 'X', text)
    text = re.sub(r'link:\S+\[([^\]]*)\]', r'\1', text)
    text = re.sub(r'xref:\S+\[([^\]]*)\]', r'\1', text)
    text = re.sub(r'pass:\S+\[[^\]]*\]', 'X', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)

    def attr_replacer(m):
        attr_name = m.group(1)
        wc = ATTR_WORD_COUNTS.get(attr_name, 1)
        return ' '.join(['W'] * wc)
    text = re.sub(r'\{([\w-]+)\}', attr_replacer, text)

    text = re.sub(r'^\s*[\*\.]{1,3}\s+', '', text)
    text = re.sub(r'^(NOTE|TIP|IMPORTANT|WARNING|CAUTION):\s*', '', text)
    words = text.split()
    words = [w for w in words if re.search(r'[a-zA-Z0-9]', w)]
    return len(words)


def split_sentences(text):
    """Split text into sentences."""
    text = text.strip()
    if not text:
        return []
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z\{])', text)
    return [p.strip() for p in parts if p.strip()]


def count_syllables(word):
    """Estimate syllable count for a word."""
    word = word.lower().strip()
    if not word or not re.search(r'[a-zA-Z]', word):
        return 0
    word = re.sub(r'[^a-z]', '', word)
    if len(word) <= 2:
        return 1
    # Count vowel groups
    count = len(re.findall(r'[aeiouy]+', word))
    # Silent e at end
    if word.endswith('e') and not word.endswith('le') and count > 1:
        count -= 1
    # Silent -ed ending
    if word.endswith('ed') and len(word) > 3 and count > 1:
        count -= 1
    return max(count, 1)


def resolve_for_syllables(text):
    """Clean AsciiDoc markup and resolve attributes for syllable counting."""
    # Replace backtick literals with a single word
    text = re.sub(r'`[^`]*`', 'code', text)
    # Replace link/xref macros with link text only
    text = re.sub(r'link:\S+\[([^\]]*)\]', r'\1', text)
    text = re.sub(r'xref:\S+\[([^\]]*)\]', r'\1', text)
    # Resolve attributes to their actual text
    def attr_rep(m):
        name = m.group(1)
        return ATTR_RESOLVED.get(name, 'word')
    text = re.sub(r'\{([\w-]+)\}', attr_rep, text)
    # Remove bold/italic markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    # Remove list markers
    text = re.sub(r'^\s*[\*\.]{1,3}\s+', '', text)
    # Remove admonition prefixes
    text = re.sub(r'^(NOTE|TIP|IMPORTANT|WARNING|CAUTION):\s*', '', text)
    # Extract words
    words = [w for w in text.split() if re.search(r'[a-zA-Z]', w)]
    return words


def check_file(filepath):
    """Analyze a single file for readability."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except (UnicodeDecodeError, IOError):
        return {"sentences": 0, "words": 0, "syllables": 0, "grade": 0}

    block_lines = find_block_ranges(lines)
    total_sentences = 0
    all_words = []
    current_unit = []

    def process_unit(unit_lines):
        nonlocal total_sentences
        if not unit_lines:
            return
        text = " ".join(unit_lines)
        sentences = split_sentences(text)
        for sent in sentences:
            wc = count_words(sent)
            if wc < 3:
                continue
            total_sentences += 1
            words = resolve_for_syllables(sent)
            all_words.extend(words)

    for i, line in enumerate(lines):
        if i in block_lines:
            process_unit(current_unit)
            current_unit = []
            continue
        if is_skip_line(line):
            process_unit(current_unit)
            current_unit = []
            continue
        if is_definition_list(line):
            process_unit(current_unit)
            current_unit = []
            continue
        if is_link_only_item(line):
            process_unit(current_unit)
            current_unit = []
            continue
        stripped = line.strip()
        if is_list_item(line):
            process_unit(current_unit)
            current_unit = [stripped]
            continue
        if not stripped:
            process_unit(current_unit)
            current_unit = []
            continue
        current_unit.append(stripped)

    process_unit(current_unit)

    total_words = len(all_words)
    total_syllables = sum(count_syllables(w) for w in all_words)

    if total_sentences > 0 and total_words > 0:
        grade = (0.39 * (total_words / total_sentences)
                 + 11.8 * (total_syllables / total_words)
                 - 15.59)
    else:
        grade = 0

    return {
        "sentences": total_sentences,
        "words": total_words,
        "syllables": total_syllables,
        "grade": grade,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Check readability (Flesch-Kincaid Grade Level) "
                    "in AsciiDoc docs."
    )
    parser.add_argument(
        "docs_dir",
        help="Path to the documentation repository root",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show per-file grades for all files",
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

    print("Readability Check (Flesch-Kincaid Grade Level)")
    print("=" * 60)
    print(f"Scanning: {docs_dir}")
    print(f"Directories: {', '.join(args.scan_dirs)}")
    print(f"Thresholds: ideal <={IDEAL_GRADE}, "
          f"minimum <={MIN_GRADE}")
    print()

    files = collect_adoc_files(docs_dir, args.scan_dirs)
    all_syllables = 0
    all_sentences = 0
    file_grades = []

    for filepath, rel_path in files:
        result = check_file(filepath)
        if result["sentences"] < MIN_SENTENCES:
            continue
        all_syllables += result["syllables"]
        all_sentences += result["sentences"]
        file_grades.append((
            rel_path, result["grade"],
            result["sentences"], result["words"]
        ))

    # Compute overall grade from totals
    total_words = sum(w for _, _, _, w in file_grades)
    if all_sentences > 0 and total_words > 0:
        overall_grade = (0.39 * (total_words / all_sentences)
                         + 11.8 * (all_syllables / total_words)
                         - 15.59)
    else:
        overall_grade = 0

    # Grade distribution
    buckets = {
        "<=8 (Easy)": [],
        "9-10 (Ideal)": [],
        "11-12 (Meets minimum)": [],
        ">12 (Advanced)": [],
    }
    for entry in file_grades:
        grade = entry[1]
        if grade <= 8:
            buckets["<=8 (Easy)"].append(entry)
        elif grade <= 10:
            buckets["9-10 (Ideal)"].append(entry)
        elif grade <= 12:
            buckets["11-12 (Meets minimum)"].append(entry)
        else:
            buckets[">12 (Advanced)"].append(entry)

    print("GRADE DISTRIBUTION:")
    for label, entries in buckets.items():
        pct = len(entries) / len(file_grades) * 100 if file_grades else 0
        print(f"  {label}: {len(entries)} files ({pct:.1f}%)")
    print()

    # Files above grade 12
    above_min = sorted(buckets[">12 (Advanced)"], key=lambda x: -x[1])
    print(f"FILES ABOVE GRADE {MIN_GRADE}: {len(above_min)}")
    if above_min:
        for rel_path, grade, sents, words in above_min:
            print(f"  {rel_path}  "
                  f"(grade {grade:.1f}, {sents} sentences, {words} words)")
    else:
        print("  (none)")
    print()

    # Verbose: show all files
    if args.verbose:
        print("ALL FILE GRADES:")
        for rel_path, grade, sents, _words in sorted(
            file_grades, key=lambda x: -x[1]
        ):
            marker = ""
            if grade > MIN_GRADE:
                marker = " [ABOVE MIN]"
            elif grade > IDEAL_GRADE:
                marker = ""
            else:
                marker = " [IDEAL]"
            print(f"  {rel_path}  "
                  f"(grade {grade:.1f}, {sents} sents){marker}")
        print()

    # Metrics
    avg_wps = total_words / all_sentences if all_sentences else 0
    avg_spw = all_syllables / total_words if total_words else 0
    meets_ideal = len(buckets["<=8 (Easy)"]) + len(buckets["9-10 (Ideal)"])
    meets_min = meets_ideal + len(buckets["11-12 (Meets minimum)"])

    print("-" * 60)
    print("METRICS:")
    print(f"  Files analyzed (>={MIN_SENTENCES} sentences): "
          f"{len(file_grades)}")
    print(f"  Total sentences:            {all_sentences}")
    print(f"  Total words:                {total_words}")
    print(f"  Avg words/sentence:         {avg_wps:.1f}")
    print(f"  Avg syllables/word:         {avg_spw:.2f}")
    print(f"  Overall FK Grade Level:     {overall_grade:.2f}")
    print(f"  Files at ideal (<=10):      "
          f"{meets_ideal}/{len(file_grades)} "
          f"({meets_ideal/len(file_grades)*100:.1f}%)"
          if file_grades else "")
    print(f"  Files meeting min (<=12):   "
          f"{meets_min}/{len(file_grades)} "
          f"({meets_min/len(file_grades)*100:.1f}%)"
          if file_grades else "")
    print(f"  Files above min (>12):      {len(above_min)}")

    if overall_grade > MIN_GRADE:
        print(f"\nResult: FAIL (overall grade {overall_grade:.2f} "
              f"exceeds {MIN_GRADE})")
        sys.exit(1)
    else:
        print(f"\nResult: PASS (overall grade {overall_grade:.2f})")
        sys.exit(0)


if __name__ == "__main__":
    main()
