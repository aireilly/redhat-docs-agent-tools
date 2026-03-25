#!/usr/bin/env python3
"""Search and retrieve Red Hat Documentation support cases.

Uses two APIs:
  - Hydra Search (POST /search/v2/cases) - full-text search with facets
  - Support REST  (GET  /support/cases)  - list, get single case, comments

Prerequisites:
  - REDHAT_API_TOKEN in ~/.env (offline token from https://access.redhat.com/management/api)

Usage:
  case_search.py <query> [options]           # full-text search
  case_search.py --get <case-number>         # get single case details
  case_search.py --comments <case-number>    # get case comments
  case_search.py --list [options]            # list cases (REST API)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
import requests

HYDRA_SEARCH_URL = "https://access.redhat.com/hydra/rest/search/v2/cases"
REST_BASE_URL = "https://api.access.redhat.com/support"
SSO_TOKEN_URL = "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"
CASE_URL = "https://access.redhat.com/support/cases"
DEFAULT_TYPE = "Usage / Documentation Help"

REQUEST_TIMEOUT = 30


def _request(client, method, url, **kwargs):
    """Make an HTTP request with timeout, status check, and JSON error handling."""
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    try:
        resp = client.request(method, url, **kwargs)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    try:
        return resp.json()
    except ValueError:
        print("Error: API returned non-JSON response.", file=sys.stderr)
        sys.exit(1)


FIELD_LIST = ",".join([
    "case_createdDate", "case_lastModifiedDate",
    "id", "uri", "case_summary", "case_status",
    "case_product", "case_version", "case_number",
    "case_severity",
    "case_last_public_update_date",
    "case_customer_escalation", "case_folderName", "case_alternate_id",
    "case_type", "case_closedDate",
])


# ── Authentication ────────────────────────────────────────────────────────────

_bearer_token_cache = None


def load_env():
    """Load REDHAT_API_TOKEN from ~/.env if not already set."""
    if os.environ.get("REDHAT_API_TOKEN"):
        return
    env_file = Path.home() / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def _scrub_env(*keys):
    """Remove sensitive env vars after reading so they don't leak via subprocesses or /proc."""
    for key in keys:
        os.environ.pop(key, None)


def get_bearer_token():
    """Exchange offline token for a bearer token (cached per session)."""
    global _bearer_token_cache
    if _bearer_token_cache:
        return _bearer_token_cache

    offline_token = os.environ.get("REDHAT_API_TOKEN")
    if not offline_token:
        print("Error: No authentication configured.", file=sys.stderr)
        print("Set REDHAT_API_TOKEN in ~/.env (https://access.redhat.com/management/api)", file=sys.stderr)
        sys.exit(1)

    # Scrub the offline token from env before making any network calls
    _scrub_env("REDHAT_API_TOKEN")

    data = _request(requests, "POST", SSO_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": "rhsm-api",
        "refresh_token": offline_token,
    })
    # Clear the offline token from memory
    del offline_token
    token = data.get("access_token")
    if not token:
        # Sanitize error output — never echo back token values
        err = data.get("error_description") or data.get("error") or "Unknown error"
        print(f"Error: Failed to exchange offline token: {err}", file=sys.stderr)
        sys.exit(1)

    _bearer_token_cache = token
    return token


def auth_session():
    """Return a requests.Session with bearer auth configured."""
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {get_bearer_token()}"
    return s


# ── Formatting helpers ────────────────────────────────────────────────────────

def fmt_date(value):
    """Extract date portion from ISO datetime string."""
    if value:
        return str(value).split("T")[0]
    return "n/a"


def safe(obj, *keys, default="n/a"):
    """Safely traverse nested dicts/objects."""
    current = obj
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return default
        if current is None:
            return default
    return current


# ── PII redaction ─────────────────────────────────────────────────────────────

# Hydra field names that contain PII
_HYDRA_PII_FIELDS = {
    "case_contactName", "case_createdByName", "case_lastModifiedByName",
    "case_last_public_update_by", "case_accountNumber", "case_owner",
}

# REST API field names / nested paths that contain PII
_REST_PII_FIELDS = {
    "contactName", "contactEmail", "accountNumber", "createdByName",
    "lastModifiedByName", "createdBy",
}
_REST_PII_NESTED = {"contact", "account", "caseOwner"}

REDACTED = "[REDACTED]"


def redact_hydra_doc(doc):
    """Return a copy of a Hydra doc with PII fields replaced."""
    out = dict(doc)
    for field in _HYDRA_PII_FIELDS:
        if field in out:
            out[field] = REDACTED
    return out


def redact_rest_case(case):
    """Return a copy of a REST API case dict with PII fields replaced."""
    out = dict(case)
    for field in _REST_PII_FIELDS:
        if field in out:
            out[field] = REDACTED
    for field in _REST_PII_NESTED:
        if field in out and isinstance(out[field], dict):
            out[field] = {k: REDACTED for k in out[field]}
    return out


# ── Text scrubbing (URLs, IPs, MACs) ─────────────────────────────────────────

_URL_RE = re.compile(r'\b(?:https?://)?(?:www\.)?[^\s]+\.[a-zA-Z]{2,3}\b')

_ALLOWED_URLS_EXACT = {
    "redhat.com", "hostname", "example.com", "example.net", "example.org",
    "access.redhat.com", "server.log", "www.redhat.com", "bugzilla.redhat.com",
    "config.get", "www.example.com", "agent.log", "rhqctl.log",
    "rhq-storage.log", "rhq-client.log",
    "http://access.redhat.com", "https://access.redhat.com",
    "https://www.redhat.com", "http://www.redhat.com",
    "http://www.example.com", "https://www.example.com",
}

_ALLOWED_URL_PREFIXES = (
    "http://access.redhat.com", "https://access.redhat.com",
    "https://www.redhat.com", "http://www.redhat.com",
    "http://www.example.com", "https://www.example.com",
)

_ALLOWED_DOMAIN_SUFFIXES = (".redhat.com", ".redhat.io", ".openshift.com")

_ALLOWED_FILE_EXTENSIONS = {
    ".log", ".img", ".out", ".bin", ".cfg", ".png", ".gif", ".jpg",
    ".rhq", ".jar", ".msc", ".txt", ".pdf", ".tar", ".gz", ".java",
    ".yml", ".xml", ".csv", ".py", ".zip", ".jpeg", ".doc", ".docx",
    ".xls", ".xlsx", ".ppt", ".pps", ".odt", ".ods", ".odp", ".tgz",
    ".bz", ".cpp", ".bz2", ".sh", ".stp", ".rtf", ".sql",
}


def _is_url_allowed(match):
    url = match.group(0)
    if url in _ALLOWED_URLS_EXACT:
        return True
    for prefix in _ALLOWED_URL_PREFIXES:
        if url.startswith(prefix):
            return True
    for suffix in _ALLOWED_DOMAIN_SUFFIXES:
        if url.endswith(suffix):
            return True
    # node*.example.com
    bare = re.sub(r'^https?://', '', url)
    if bare.startswith("node") and bare.endswith(".example.com"):
        return True
    for ext in _ALLOWED_FILE_EXTENSIONS:
        if url.endswith(ext):
            return True
    return False


_IP_RE = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')

_ALLOWED_IP_EXACT = {"10.0.0.0", "192.0.2.0", "198.51.100.0", "203.0.113.0"}
_ALLOWED_IP_FIRST_OCTET = {"127", "0", "224", "255"}


def _is_ip_allowed(match):
    ip = match.group(0)
    if ip in _ALLOWED_IP_EXACT:
        return True
    first_octet = ip.split(".")[0]
    return first_octet in _ALLOWED_IP_FIRST_OCTET


_MAC_RE = re.compile(
    r'[a-fA-F\d]{2}:[a-fA-F\d]{2}:[a-fA-F\d]{2}:[a-fA-F\d]{2}:[a-fA-F\d]{2}:[a-fA-F\d]{2}'
    r'|[a-fA-F\d]{2}-[a-fA-F\d]{2}-[a-fA-F\d]{2}-[a-fA-F\d]{2}-[a-fA-F\d]{2}-[a-fA-F\d]{2}'
    r'|[a-fA-F\d]{2}\.[a-fA-F\d]{2}\.[a-fA-F\d]{2}\.[a-fA-F\d]{2}\.[a-fA-F\d]{2}\.[a-fA-F\d]{2}'
)

_ALLOWED_MACS = {
    "00:00:00:00:00:aa", "00:00:00:00:00:bb",
    "00-00-00-00-00-aa", "00-00-00-00-00-bb",
    "00.00.00.00.00.aa", "00.00.00.00.00.bb",
}


def scrub_text(text):
    """Scrub URLs, IP addresses, and MAC addresses from free-text fields."""
    if not text:
        return text
    # MACs first (dot-separated MACs overlap with IP regex)
    text = _MAC_RE.sub(lambda m: m.group(0) if m.group(0).lower() in _ALLOWED_MACS else "<REDACTED_MAC>", text)
    # IPs
    text = _IP_RE.sub(lambda m: m.group(0) if _is_ip_allowed(m) else "<REDACTED_IP>", text)
    # URLs / domains / filenames
    text = _URL_RE.sub(lambda m: m.group(0) if _is_url_allowed(m) else "<REDACTED_URL>", text)
    return text


# ── Single case / comments (REST API) ────────────────────────────────────────

def cmd_get(args):
    """Get full details for a single case."""
    s = auth_session()
    c = redact_rest_case(_request(s, "GET", f"{REST_BASE_URL}/cases/{args.case_number}"))

    if args.raw:
        print(json.dumps(c, indent=2))
        return

    product = f"{c.get('product', 'n/a')} {c.get('version', '')}".strip()

    lines = [
        f"Case #{c.get('caseNumber', '?')}",
        "═" * 51,
        f"Subject:     {c.get('subject', 'n/a')}",
        f"Status:      {c.get('status', 'n/a')}",
        f"Severity:    {c.get('severity', 'n/a')}",
        f"Product:     {product}",
        f"SBR Group:   {c.get('sbrGroup', 'n/a')}",
        f"Type:        {c.get('caseType', 'n/a')}",
        f"Created:     {fmt_date(c.get('createdDate'))}",
        f"Modified:    {fmt_date(c.get('lastModifiedDate'))}",
    ]
    if c.get("closedDate"):
        lines.append(f"Closed:      {fmt_date(c['closedDate'])}")
    if c.get("customerEscalation"):
        lines.append("** ESCALATED **")
    lines.append(f"URL:         {CASE_URL}/{c.get('caseNumber', '')}")
    lines.append("")
    lines.append("── Description ──")
    lines.append(scrub_text(c.get("description") or "No description"))

    print("\n".join(lines))


def cmd_comments(args):
    """Get comments for a case."""
    s = auth_session()
    comments = _request(s, "GET", f"{REST_BASE_URL}/cases/{args.case_number}/comments")

    if args.raw:
        print(json.dumps(comments, indent=2))
        return

    if not isinstance(comments, list):
        print("Unexpected response format", file=sys.stderr)
        return

    print(f"{len(comments)} comments on case {args.case_number}\n")
    for c in comments:
        date = fmt_date(c.get("createdDate"))
        print(f"── {date} ──")
        if c.get("public") is False:
            print("[PRIVATE]")
        print(scrub_text(c.get("text") or c.get("body") or "(empty)"))
        print()


# ── List cases (REST API) ────────────────────────────────────────────────────

def cmd_list(args):
    """List cases via the REST API."""
    s = auth_session()
    params = {"count": args.rows}
    if args.start > 0:
        params["start"] = args.start

    if args.status:
        params["status"] = args.status

    cases = _request(s, "GET", f"{REST_BASE_URL}/cases", params=params)

    if args.raw:
        print(json.dumps(cases, indent=2))
        return

    if not isinstance(cases, list):
        print("Unexpected response format", file=sys.stderr)
        return

    print(f"Listing {len(cases)} cases\n")
    for c in cases:
        c = redact_rest_case(c)
        print(f"  #{c.get('caseNumber', '?')}  [{c.get('severity', 'n/a')}]  {c.get('status', 'n/a')}")
        print(f"  {c.get('subject', 'No subject')}")
        print(f"  Product: {c.get('product', 'n/a')} {c.get('version', '')}")
        print(f"  Modified: {fmt_date(c.get('lastModifiedDate'))}")
        print()


# ── Full-text search (Hydra) ─────────────────────────────────────────────────

def _solr_escape(value):
    """Escape quotes in a value for safe interpolation into Solr fq clauses."""
    return value.replace('\\', '\\\\').replace('"', '\\"')


def build_expression(product=None, severity=None, status=None, case_type=None,
                     exclude_closed=True):
    """Build the Solr expression string for Hydra search."""
    parts = [
        "sort=case_severity asc,case_lastModifiedDate desc",
        "facet=true",
        "facet.mincount=0",
        "facet.pivot.mincount=0",
        "facet.sort=index",
        "f.case_product.facet.limit=-1",
        "f.case_version.facet.pivot.limit=-1",
        "f.case_version.facet.pivot.mincount=1",
        f"fl={FIELD_LIST}",
        # Facet fields (with exclusion tags)
        "facet.field={!ex=c_product}case_product",
        "facet.field={!ex=c_severity}case_severity",
        "facet.field={!ex=c_status}case_status",
        "facet.field={!ex=c_type}case_type",
        "facet.pivot={!ex=c_product}case_product,case_version",
    ]

    # Filter queries
    if product:
        parts.append(f'fq={{!tag=c_product}}case_product:"{_solr_escape(product)}"')
    else:
        parts.append("fq={!tag=c_product}*:*")

    if severity:
        parts.append(f'fq={{!tag=c_severity}}case_severity:"{_solr_escape(severity)}"')
    if status:
        parts.append(f'fq={{!tag=c_status}}case_status:"{_solr_escape(status)}"')
    elif exclude_closed:
        parts.append('fq={!tag=c_status}-case_status:"Closed"')
    if case_type:
        parts.append(f'fq={{!tag=c_type}}case_type:"{_solr_escape(case_type)}"')

    return "&".join(parts)


def format_case_text(doc, source="hydra"):
    """Format a single case as text lines. Works with both Hydra and REST API responses."""
    lines = []
    if source == "hydra":
        case_num = doc.get("case_number", "?")
        sev = doc.get("case_severity", "n/a")
        status = doc.get("case_status", "n/a")
        summary = doc.get("case_summary", "No summary")
        product = doc.get("case_product", "n/a")
        if isinstance(product, list):
            product = ", ".join(product)
        version = doc.get("case_version", "")
        modified = fmt_date(doc.get("case_lastModifiedDate"))
        created = fmt_date(doc.get("case_createdDate"))
        escalated = doc.get("case_customer_escalation") in (True, "true")
    else:
        case_num = doc.get("caseNumber", "?")
        sev = doc.get("severity", "n/a")
        status = doc.get("status", "n/a")
        summary = doc.get("subject", "No summary")
        product = doc.get("product", "n/a")
        version = doc.get("version", "")
        modified = fmt_date(doc.get("lastModifiedDate"))
        created = fmt_date(doc.get("createdDate"))
        escalated = doc.get("customerEscalation") is True

    lines.append(f"  #{case_num}  [{sev}]  {status}")
    lines.append(f"  {summary}")
    lines.append(f"  Product: {product} {version}")
    lines.append(f"  Modified: {modified}  |  Created: {created}")
    lines.append(f"  URL: {CASE_URL}/{case_num}")
    if escalated:
        lines.append("  ** ESCALATED **")
    lines.append("")
    return lines


def format_search_results(data):
    """Format Hydra search response for display."""
    response = data.get("response", {})
    num_found = response.get("numFound", 0)
    start = response.get("start", 0)
    docs = response.get("docs", [])

    print(f"Found {num_found} cases (showing {start + 1}-{start + len(docs)})\n")

    for doc in docs:
        for line in format_case_text(doc, source="hydra"):
            print(line)

    # Facet breakdowns
    facets = data.get("facet_counts", {}).get("facet_fields", {})
    for field, label in [("case_severity", "Severity"), ("case_status", "Status")]:
        values = facets.get(field, [])
        if not values:
            continue
        pairs = [(k, v) for k, v in zip(values[0::2], values[1::2]) if v > 0]
        if pairs:
            print(f"── {label} breakdown ──")
            for name, count in pairs:
                print(f"  {name}: {count}")
            print()


def _fetch_case_detail(session, case_number):
    """Fetch full case details (includes description) from REST API."""
    try:
        data = _request(session, "GET", f"{REST_BASE_URL}/cases/{case_number}")
        return redact_rest_case(data)
    except Exception:
        return {}


def _fetch_case_comments(session, case_number):
    """Fetch comments for a case from REST API."""
    try:
        data = _request(session, "GET", f"{REST_BASE_URL}/cases/{case_number}/comments")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def write_output(output_dir, data, args, session):
    """Write search results to output directory for orchestrator integration.

    Creates:
      <output_dir>/cases.json       — raw case docs array
      <output_dir>/cases.md         — human-readable Markdown summary with description and comments
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    response = data.get("response", {})
    docs = response.get("docs", [])
    num_found = response.get("numFound", 0)

    # cases.json — machine-readable
    (out / "cases.json").write_text(json.dumps(docs, indent=2) + "\n")

    # cases.md — human-readable Markdown
    lines = [
        "# Case Search Results",
        "",
        f"**Query:** `{args.query}`  ",
        f"**Type:** {args.type}  ",
    ]
    if args.product:
        lines.append(f"**Product:** {args.product}  ")
    if args.severity:
        lines.append(f"**Severity:** {args.severity}  ")
    if args.status:
        lines.append(f"**Status:** {args.status}  ")
    lines.append(f"**Total matches:** {num_found}  ")
    lines.append(f"**Showing:** {len(docs)} cases  ")
    lines.append("")

    for doc in docs:
        case_num = doc.get("case_number", "?")
        sev = doc.get("case_severity", "n/a")
        case_status = doc.get("case_status", "n/a")
        summary = doc.get("case_summary", "No summary")
        product = doc.get("case_product", "n/a")
        if isinstance(product, list):
            product = ", ".join(product)
        version = doc.get("case_version", "")
        modified = fmt_date(doc.get("case_lastModifiedDate"))
        created = fmt_date(doc.get("case_createdDate"))
        escalated = doc.get("case_customer_escalation") in (True, "true")

        lines.append(f"## Case #{case_num}")
        lines.append("")
        lines.append(f"- **Summary:** {scrub_text(summary)}")
        lines.append(f"- **Severity:** {sev}")
        lines.append(f"- **Status:** {case_status}")
        lines.append(f"- **Product:** {product} {version}")
        lines.append(f"- **Created:** {created}")
        lines.append(f"- **Modified:** {modified}")
        lines.append(f"- **URL:** {CASE_URL}/{case_num}")
        if escalated:
            lines.append("- **ESCALATED**")
        lines.append("")

        # Fetch and append description
        detail = _fetch_case_detail(session, case_num)
        description = detail.get("description") or "No description available"
        lines.append("### Description")
        lines.append("")
        lines.append(scrub_text(description))
        lines.append("")

        # Fetch and append comments
        comments = _fetch_case_comments(session, case_num)
        if comments:
            lines.append(f"### Comments ({len(comments)})")
            lines.append("")
            for comment in comments:
                date = fmt_date(comment.get("createdDate"))
                is_public = comment.get("public", True)
                visibility = "" if is_public else " [PRIVATE]"
                text = comment.get("text") or comment.get("body") or "(empty)"
                lines.append(f"**{date}**{visibility}")
                lines.append("")
                lines.append(scrub_text(text))
                lines.append("")
        lines.append("---")
        lines.append("")

    # Facet summary
    facets = data.get("facet_counts", {}).get("facet_fields", {})
    for field, label in [("case_severity", "Severity"), ("case_status", "Status")]:
        values = facets.get(field, [])
        if not values:
            continue
        pairs = [(k, v) for k, v in zip(values[0::2], values[1::2]) if v > 0]
        if pairs:
            lines.append(f"### {label} breakdown")
            lines.append("")
            for name, count in pairs:
                lines.append(f"- {name}: {count}")
            lines.append("")

    (out / "cases.md").write_text("\n".join(lines) + "\n")

    print(f"Wrote {len(docs)} cases to {out}/")
    print(f"  {out}/cases.json")
    print(f"  {out}/cases.md")


def cmd_search(args):
    """Full-text search via Hydra."""
    s = auth_session()

    expression = build_expression(
        product=args.product,
        severity=args.severity,
        status=args.status,
        case_type=args.type,
        exclude_closed=not args.include_closed,
    )

    payload = {
        "q": args.query,
        "start": args.start,
        "rows": args.rows,
        "partnerSearch": False,
        "expression": expression,
    }

    data = _request(s, "POST", HYDRA_SEARCH_URL, json=payload)

    if "error" in data or "message" in data:
        err = data.get("error") or data.get("message")
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    # Redact PII from all response docs
    docs = data.get("response", {}).get("docs", [])
    data["response"]["docs"] = [redact_hydra_doc(d) for d in docs]

    if args.raw:
        print(json.dumps(data, indent=2))
        return

    if args.json:
        print(json.dumps(data["response"]["docs"], indent=2))
        return

    if args.output_dir:
        write_output(args.output_dir, data, args, session=s)
        return

    format_search_results(data)


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description="Search and retrieve Red Hat customer support cases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s "vllm*"
  %(prog)s "kernel panic" --product "Red Hat Enterprise Linux" --severity "1 (Urgent)"
  %(prog)s "openshift" --status Closed --rows 5
  %(prog)s --get 04394864
  %(prog)s --comments 04394864
  %(prog)s --list --rows 5
""",
    )
    # ── search (default, positional) ──
    parser.add_argument("query", nargs="?", help="Search query (supports wildcards like vllm*)")
    parser.add_argument("--product", help="Filter by product name")
    parser.add_argument("--severity", help='Filter by severity (e.g., "1 (Urgent)")')
    parser.add_argument("--status", help='Filter by status (e.g., "Closed")')
    parser.add_argument("--type", default=DEFAULT_TYPE,
                        help=f'Filter by case type (default: "{DEFAULT_TYPE}")')
    parser.add_argument("--start", type=int, default=0, help="Pagination offset (default: 0)")
    parser.add_argument("--rows", type=int, default=10, help="Results per page (default: 10)")
    parser.add_argument("--include-closed", action="store_true",
                        help="Include closed cases (excluded by default)")
    parser.add_argument("--output-dir", help="Write results to directory (cases.json + cases.md)")
    parser.add_argument("--raw", action="store_true", help="Output raw JSON response")
    parser.add_argument("--json", action="store_true", help="Output cases as JSON array")

    # ── get ──
    parser.add_argument("--get", metavar="CASE_NUMBER", help="Get full details for a single case")

    # ── comments ──
    parser.add_argument("--comments", metavar="CASE_NUMBER", help="Get comments for a case")

    # ── list ──
    parser.add_argument("--list", action="store_true", help="List cases via REST API")

    return parser


def main():
    load_env()
    parser = build_parser()
    args = parser.parse_args()

    if args.get:
        args.case_number = args.get
        cmd_get(args)
    elif args.comments:
        args.case_number = args.comments
        cmd_comments(args)
    elif args.list:
        cmd_list(args)
    elif args.query:
        cmd_search(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
