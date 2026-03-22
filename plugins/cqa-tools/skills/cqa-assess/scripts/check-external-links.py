#!/usr/bin/env python3
"""Categorize external links by domain in AsciiDoc documentation.

Extracts all external URLs (link:https://, bare https://) from active content,
categorizes them by domain, and identifies non-Red Hat domains that may need
disclaimers.

CQA parameters: Q17
Skill: cqa-legal-branding

Usage:
    python3 check-external-links.py <DOCS_DIR>

Exit codes:
    0 - Report generated (always succeeds — this is informational)
    2 - Invalid arguments (e.g., docs_dir is not a directory)
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from urllib.parse import urlparse

# Directories to scan
DEFAULT_SCAN_DIRS = ["assemblies", "modules", "topics", "snippets"]

# Directories to skip
SKIP_DIRS = {"legacy-content-do-not-use"}

# Red Hat domains (links to these don't need disclaimers)
RH_DOMAINS = {
    "access.redhat.com",
    "redhat.com",
    "www.redhat.com",
    "docs.redhat.com",
    "catalog.redhat.com",
    "console.redhat.com",
    "developers.redhat.com",
    "issues.redhat.com",
    "connect.redhat.com",
    "sso.redhat.com",
    "registry.redhat.io",
    "quay.io",  # Red Hat owned
    "red.ht",  # Red Hat URL shortener
    "docs.openshift.com",  # OpenShift documentation (Red Hat product)
    "workspaces.openshift.com",  # Red Hat Dev Spaces hosted service
}

# Upstream / community domains (related to the product)
UPSTREAM_DOMAINS = {
    "github.com",
    "eclipse.org",
    "www.eclipse.org",
    "kubernetes.io",
    "devfile.io",
    "che.eclipse.org",
}

# Well-known authoritative domains
AUTHORITATIVE_DOMAINS = {
    "docs.github.com",
    "kubernetes.io",
    "docs.docker.com",
    "www.jetbrains.com",
    "plugins.jetbrains.com",
    "code.visualstudio.com",
    "marketplace.visualstudio.com",
    "docs.microsoft.com",
    "learn.microsoft.com",
    "tools.ietf.org",
    "www.rfc-editor.org",
    "yaml.org",
    "www.yaml.org",
    "json-schema.org",
    "semver.org",
    "oauth.net",
    "openid.net",
    "www.openapis.org",
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


def extract_urls(filepath, rel_path):
    """Extract all external URLs from a file.

    Returns list of dicts with url, domain, file, line_num, context.
    """
    urls = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, IOError):
        return urls

    lines = content.splitlines()
    code_lines = parse_code_block_lines(lines)

    for line_idx, line in enumerate(lines):
        if line_idx in code_lines:
            continue
        stripped = line.strip()
        if stripped.startswith("//"):
            continue

        # Find all URLs: link:https://...[text], bare https://...
        for m in re.finditer(r'https?://[^\s\[\]<>"]+', line):
            url = m.group().rstrip(".,;:!?)")  # Strip trailing punctuation
            # Strip trailing backticks (AsciiDoc inline code artifacts)
            url = url.rstrip("`")
            # Remove AsciiDoc macro syntax trailing brackets
            url = re.sub(r'\[.*$', '', url)
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                if not domain:
                    continue
                # Skip placeholder/example URLs
                if domain in ("example.com", "www.example.com",
                              "some-extension-url"):
                    continue
                # Skip URLs with unresolved AsciiDoc attributes
                if "{" in domain or "}" in domain:
                    continue
                # Skip placeholder-only URLs (e.g., https://__)
                if all(c in "_-." for c in domain):
                    continue
                urls.append({
                    "url": url,
                    "domain": domain,
                    "file": rel_path,
                    "line_num": line_idx + 1,
                })
            except ValueError:
                pass

    return urls


def categorize_domain(domain):
    """Categorize a domain as RH, upstream, authoritative, or third-party."""
    # Check exact match first
    if domain in RH_DOMAINS:
        return "Red Hat"

    # Check if subdomain of a Red Hat domain
    for rh in RH_DOMAINS:
        if domain.endswith("." + rh):
            return "Red Hat"

    if domain in UPSTREAM_DOMAINS:
        return "Upstream/Community"
    for up in UPSTREAM_DOMAINS:
        if domain.endswith("." + up):
            return "Upstream/Community"

    if domain in AUTHORITATIVE_DOMAINS:
        return "Authoritative"
    for auth in AUTHORITATIVE_DOMAINS:
        if domain.endswith("." + auth):
            return "Authoritative"

    return "Third-party"


def main():
    parser = argparse.ArgumentParser(
        description="Categorize external links by domain in AsciiDoc docs."
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
        "--details",
        action="store_true",
        help="Show individual URL details for each domain",
    )
    args = parser.parse_args()

    docs_dir = os.path.abspath(args.docs_dir)
    if not os.path.isdir(docs_dir):
        print(f"Error: {docs_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    print("External Link Categorization")
    print("=" * 60)
    print(f"Scanning: {docs_dir}")
    print(f"Directories: {', '.join(args.scan_dirs)}")
    print()

    files = collect_adoc_files(docs_dir, scan_dirs=args.scan_dirs)
    all_urls = []
    for filepath, rel_path in files:
        all_urls.extend(extract_urls(filepath, rel_path))

    # Categorize
    by_category = defaultdict(list)
    by_domain = defaultdict(list)

    for url_info in all_urls:
        category = categorize_domain(url_info["domain"])
        url_info["category"] = category
        by_category[category].append(url_info)
        by_domain[url_info["domain"]].append(url_info)

    # Unique URLs
    unique_urls = set(u["url"] for u in all_urls)

    # Report by category
    print("Summary by category:")
    for category in ["Red Hat", "Upstream/Community", "Authoritative", "Third-party"]:
        items = by_category.get(category, [])
        unique_in_cat = set(u["url"] for u in items)
        domains_in_cat = set(u["domain"] for u in items)
        print(f"  {category}: {len(unique_in_cat)} unique URLs across {len(domains_in_cat)} domains")
    print()

    # Report domains by category
    for category in ["Red Hat", "Upstream/Community", "Authoritative", "Third-party"]:
        items = by_category.get(category, [])
        if not items:
            continue
        domains = defaultdict(int)
        for u in items:
            domains[u["domain"]] += 1
        print(f"{category} domains:")
        for domain, count in sorted(domains.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {domain}: {count} link(s)")
        print()

    # Detail for third-party (most relevant for disclaimers)
    third_party = by_category.get("Third-party", [])
    if third_party:
        print("Third-party link details (may need disclaimers):")
        current_domain = None
        for u in sorted(third_party, key=lambda x: (x["domain"], x["file"], x["line_num"])):
            if u["domain"] != current_domain:
                current_domain = u["domain"]
                print(f"\n  [{current_domain}]")
            print(f"    {u['file']}:{u['line_num']}")
            print(f"      {u['url']}")
        print()

    if args.details:
        print("\nAll URLs by domain:")
        for domain in sorted(by_domain.keys()):
            category = categorize_domain(domain)
            urls = by_domain[domain]
            print(f"\n  {domain} [{category}]:")
            for u in sorted(urls, key=lambda x: (x["file"], x["line_num"])):
                print(f"    {u['file']}:{u['line_num']}  {u['url']}")

    # Summary
    print("-" * 60)
    print(f"Total external links: {len(all_urls)} ({len(unique_urls)} unique URLs)")
    print(f"Total domains: {len(by_domain)}")
    print(f"  Red Hat: {len(set(u['domain'] for u in by_category.get('Red Hat', [])))}")
    print(f"  Upstream/Community: {len(set(u['domain'] for u in by_category.get('Upstream/Community', [])))}")
    print(f"  Authoritative: {len(set(u['domain'] for u in by_category.get('Authoritative', [])))}")
    tp_count = len(set(u['domain'] for u in by_category.get('Third-party', [])))
    print(f"  Third-party: {tp_count}")
    print(f"Files scanned: {len(files)}")

    # This is informational — always exits 0
    print("\nResult: REPORT COMPLETE")
    sys.exit(0)


if __name__ == "__main__":
    main()
