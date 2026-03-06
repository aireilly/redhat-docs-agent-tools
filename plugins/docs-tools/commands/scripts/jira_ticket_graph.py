#!/usr/bin/env python3
"""
JIRA Ticket Graph - Deterministic traversal of the JIRA ticket graph.

This script fetches a JIRA ticket and traverses its relationships (parent,
children, siblings, issue links, web links) to gather context for documentation
workflows. All traversal is bounded to 1 level deep from the primary ticket.

Output is always JSON.

Usage:
    python jira_ticket_graph.py PROJ-123
    python jira_ticket_graph.py PROJ-123 --max-children 10 --max-siblings 10

Authentication:
    Requires JIRA_AUTH_TOKEN environment variable or ~/.env file.
    Optionally set JIRA_URL to target a non-default instance (default: https://issues.redhat.com).

Exit codes:
    0 - Primary ticket fetched successfully (even with partial traversal failures)
    1 - Auth missing or primary ticket fetch failed
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from env_utils import load_env_file


def get_auth_token() -> str:
    """Get JIRA auth token from environment, with ~/.env fallback."""
    load_env_file()
    token = os.environ.get("JIRA_AUTH_TOKEN")
    if not token:
        print(
            "ERROR: JIRA_AUTH_TOKEN is not set.\n"
            "Set JIRA_AUTH_TOKEN in ~/.env file:\n"
            "  JIRA_AUTH_TOKEN=your_jira_token_here",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def get_jira_url() -> str:
    """Get JIRA base URL from environment or default."""
    return os.environ.get("JIRA_URL", "https://issues.redhat.com").rstrip("/")


def api_request(
    url: str, token: str
) -> Tuple[Optional[Any], Optional[str], Optional[int]]:
    """
    Make a JIRA REST API GET request.

    Returns:
        Tuple of (parsed_json, error_message, http_status_code).
        On success: (data, None, 200).
        On failure: (None, error_string, status_code).
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "jira-ticket-graph",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data, None, response.status
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()
        except Exception:
            pass
        return None, f"HTTP {e.code}: {body[:200]}", e.code
    except urllib.error.URLError as e:
        return None, f"URL error: {e.reason}", None
    except Exception as e:
        return None, str(e), None


def jql_search(
    jira_url: str,
    token: str,
    jql: str,
    fields: str,
    max_results: int,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Execute a JQL search query.

    Returns:
        Tuple of (search_response, error_message).
    """
    params = urllib.parse.urlencode(
        {"jql": jql, "maxResults": max_results, "fields": fields}
    )
    url = f"{jira_url}/rest/api/2/search?{params}"
    data, error, status = api_request(url, token)
    if error:
        return None, error
    return data, None


def discover_custom_fields(
    jira_url: str, token: str
) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Discover custom field IDs for 'Epic Link' and 'Parent Link'.

    Returns:
        Tuple of (epic_link_field_id, parent_link_field_id, errors).
    """
    errors: List[str] = []
    url = f"{jira_url}/rest/api/2/field"
    data, error, status = api_request(url, token)
    if error:
        errors.append(f"Failed to discover custom fields: {error}")
        return None, None, errors

    epic_link_id: Optional[str] = None
    parent_link_id: Optional[str] = None

    for field in data:
        name = field.get("name", "")
        if name == "Epic Link":
            epic_link_id = field["id"]
        elif name == "Parent Link":
            parent_link_id = field["id"]

    if epic_link_id:
        print(f"  Epic Link field: {epic_link_id}", file=sys.stderr)
    if parent_link_id:
        print(f"  Parent Link field: {parent_link_id}", file=sys.stderr)

    return epic_link_id, parent_link_id, errors


def fetch_primary_ticket(
    jira_url: str,
    token: str,
    ticket_key: str,
    parent_link_field: Optional[str],
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Fetch the primary ticket with relationship fields.

    Returns:
        Tuple of (ticket_data, error_message).
    """
    fields = "parent,subtasks,issuelinks,summary,status,issuetype,description,priority,assignee"
    if parent_link_field:
        fields += f",{parent_link_field}"
    url = f"{jira_url}/rest/api/2/issue/{ticket_key}?fields={fields}"
    data, error, status = api_request(url, token)
    if error:
        return None, error
    return data, None


def detect_parent(
    ticket_data: Dict, parent_link_field: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Detect the parent ticket key from the primary ticket response.

    Checks standard parent field first, then Parent Link custom field.

    Returns:
        Tuple of (parent_key, source) where source is 'parent_field' or 'parent_link_custom_field'.
    """
    fields = ticket_data.get("fields", {})

    # Check standard parent field
    parent = fields.get("parent")
    if parent and parent.get("key"):
        return parent["key"], "parent_field"

    # Check Parent Link custom field
    if parent_link_field:
        parent_link_value = fields.get(parent_link_field)
        if parent_link_value:
            # Parent Link can be a string key or an object with key
            if isinstance(parent_link_value, str):
                return parent_link_value, "parent_link_custom_field"
            elif isinstance(parent_link_value, dict) and parent_link_value.get("key"):
                return parent_link_value["key"], "parent_link_custom_field"

    return None, None


def fetch_parent_details(
    jira_url: str, token: str, parent_key: str, parent_source: str
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Fetch parent ticket details.

    Returns:
        Tuple of (parent_info_dict, error_message).
    """
    url = f"{jira_url}/rest/api/2/issue/{parent_key}?fields=summary,status,issuetype,description"
    data, error, status = api_request(url, token)
    if error:
        if status == 403:
            return {
                "key": parent_key,
                "summary": None,
                "status": None,
                "issuetype": None,
                "source": parent_source,
                "description": None,
                "error": f"exists but not accessible (HTTP 403)",
            }, None
        return None, f"Failed to fetch parent {parent_key}: {error}"

    fields = data.get("fields", {})
    return {
        "key": parent_key,
        "summary": fields.get("summary"),
        "status": (fields.get("status") or {}).get("name"),
        "issuetype": (fields.get("issuetype") or {}).get("name"),
        "source": parent_source,
        "description": fields.get("description"),
    }, None


def fetch_children(
    jira_url: str,
    token: str,
    ticket_key: str,
    epic_link_field: Optional[str],
    max_children: int,
) -> Tuple[Dict, List[str]]:
    """
    Fetch children via both parent = KEY and "Epic Link" = KEY JQL queries.

    Returns:
        Tuple of (children_result_dict, errors).
    """
    errors: List[str] = []
    seen_keys: set = set()
    issues: List[Dict] = []
    total_found = 0

    # Query 1: Standard parent field
    jql1 = f"parent = {ticket_key} ORDER BY status ASC, key ASC"
    fields = "summary,status,issuetype,priority,assignee"
    data, error = jql_search(jira_url, token, jql1, fields, max_children)
    if error:
        errors.append(f"Children query (parent field): {error}")
    elif data:
        total_found += data.get("total", 0)
        for issue in data.get("issues", []):
            key = issue.get("key")
            if key and key not in seen_keys:
                seen_keys.add(key)
                f = issue.get("fields", {})
                issues.append({
                    "key": key,
                    "summary": f.get("summary"),
                    "status": (f.get("status") or {}).get("name"),
                    "issuetype": (f.get("issuetype") or {}).get("name"),
                    "priority": (f.get("priority") or {}).get("name"),
                    "assignee": (f.get("assignee") or {}).get("displayName"),
                })

    # Query 2: Epic Link custom field
    if epic_link_field:
        jql2 = f'"Epic Link" = {ticket_key} ORDER BY status ASC, key ASC'
        data, error = jql_search(jira_url, token, jql2, fields, max_children)
        if error:
            errors.append(f"Children query (Epic Link): {error}")
        elif data:
            total_found += data.get("total", 0)
            for issue in data.get("issues", []):
                key = issue.get("key")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    f = issue.get("fields", {})
                    issues.append({
                        "key": key,
                        "summary": f.get("summary"),
                        "status": (f.get("status") or {}).get("name"),
                        "issuetype": (f.get("issuetype") or {}).get("name"),
                        "priority": (f.get("priority") or {}).get("name"),
                        "assignee": (f.get("assignee") or {}).get("displayName"),
                    })

    # Cap at max_children
    showing = len(issues)
    if showing > max_children:
        issues = issues[:max_children]
        showing = max_children

    skipped = max(0, len(seen_keys) - showing)

    return {
        "total": len(seen_keys),
        "showing": showing,
        "skipped": skipped,
        "issues": issues,
    }, errors


def fetch_siblings(
    jira_url: str,
    token: str,
    ticket_key: str,
    parent_key: str,
    parent_source: str,
    max_siblings: int,
) -> Tuple[Dict, List[str]]:
    """
    Fetch sibling tickets (active statuses only).

    Returns:
        Tuple of (siblings_result_dict, errors).
    """
    errors: List[str] = []

    # Choose JQL based on parent source
    if parent_source == "parent_link_custom_field":
        parent_clause = f'"Parent Link" = {parent_key}'
    else:
        parent_clause = f"parent = {parent_key}"

    active_statuses = 'Done, "In Progress", "In Review", "Code Review"'
    jql = (
        f'{parent_clause} AND key != {ticket_key} '
        f'AND status in ({active_statuses}) '
        f'ORDER BY status DESC, updated DESC'
    )

    fields = "summary,status,issuetype"
    data, error = jql_search(jira_url, token, jql, fields, max_siblings)

    if error:
        errors.append(f"Siblings query: {error}")
        return {"total": 0, "showing": 0, "skipped": 0, "issues": []}, errors

    issues: List[Dict] = []
    total = data.get("total", 0) if data else 0

    for issue in (data or {}).get("issues", []):
        f = issue.get("fields", {})
        issues.append({
            "key": issue.get("key"),
            "summary": f.get("summary"),
            "status": (f.get("status") or {}).get("name"),
            "issuetype": (f.get("issuetype") or {}).get("name"),
        })

    showing = len(issues)
    skipped = max(0, total - showing)

    return {
        "total": total,
        "showing": showing,
        "skipped": skipped,
        "issues": issues,
    }, errors


def extract_issue_links(ticket_data: Dict, max_links: int) -> Dict:
    """
    Extract issue link summaries from the primary ticket response.

    No additional API calls needed — data is embedded in the issuelinks field.

    Returns:
        Issue links result dict.
    """
    fields = ticket_data.get("fields", {})
    raw_links = fields.get("issuelinks", [])
    links: List[Dict] = []

    for link in raw_links:
        link_type = link.get("type", {})
        type_name = link_type.get("name", "")

        if "inwardIssue" in link:
            issue = link["inwardIssue"]
            direction = link_type.get("inward", "relates to")
        elif "outwardIssue" in link:
            issue = link["outwardIssue"]
            direction = link_type.get("outward", "relates to")
        else:
            continue

        f = issue.get("fields", {})
        links.append({
            "key": issue.get("key"),
            "direction": direction,
            "link_type": type_name,
            "summary": f.get("summary"),
            "status": (f.get("status") or {}).get("name"),
            "issuetype": (f.get("issuetype") or {}).get("name"),
        })

        if len(links) >= max_links:
            break

    total = len(raw_links)
    showing = len(links)
    skipped = max(0, total - showing)

    return {
        "total": total,
        "showing": showing,
        "skipped": skipped,
        "links": links,
    }


def fetch_remote_links(
    jira_url: str, token: str, ticket_key: str
) -> Tuple[Dict, Dict, List[str]]:
    """
    Fetch remote/web links from the ticket and classify URLs.

    Returns:
        Tuple of (web_links_result_dict, auto_discovered_urls_dict, errors).
        auto_discovered_urls_dict has 'pull_requests' and 'google_docs' lists.
    """
    errors: List[str] = []
    url = f"{jira_url}/rest/api/2/issue/{ticket_key}/remotelink"
    data, error, status = api_request(url, token)

    if error:
        errors.append(f"Remote links: {error}")
        empty_auto = {"pull_requests": [], "google_docs": []}
        return {"total": 0, "links": []}, empty_auto, errors

    links: List[Dict] = []
    pull_requests: List[str] = []
    google_docs: List[str] = []

    if isinstance(data, list):
        for item in data:
            obj = item.get("object", {})
            link_url = obj.get("url", "")
            title = obj.get("title", "")
            link_type = _classify_url(link_url)
            links.append({"title": title, "url": link_url, "type": link_type})
            if link_type == "pull_request":
                pull_requests.append(link_url)
            elif link_type == "google_doc":
                google_docs.append(link_url)

    web_links = {"total": len(links), "links": links}
    auto_discovered = {"pull_requests": pull_requests, "google_docs": google_docs}
    return web_links, auto_discovered, errors


def _classify_url(url: str) -> str:
    """Classify a URL as 'pull_request', 'google_doc', or 'other'."""
    if re.search(r"github\.com/.+/pull/\d+", url):
        return "pull_request"
    if re.search(r"gitlab\..+/-/merge_requests/\d+", url):
        return "pull_request"
    if re.search(r"docs\.google\.com/document/", url):
        return "google_doc"
    return "other"


def run(
    ticket_key: str,
    max_children: int = 25,
    max_siblings: int = 25,
    max_links: int = 15,
) -> int:
    """
    Main entry point: traverse the JIRA ticket graph and output results.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    token = get_auth_token()
    jira_url = get_jira_url()
    all_errors: List[str] = []

    print(f"Fetching ticket graph for {ticket_key}...", file=sys.stderr)
    print(f"JIRA URL: {jira_url}", file=sys.stderr)

    # Step 1: Discover custom fields
    print("  Discovering custom fields...", file=sys.stderr)
    epic_link_field, parent_link_field, errors = discover_custom_fields(
        jira_url, token
    )
    all_errors.extend(errors)

    # Step 2: Fetch primary ticket
    print(f"  Fetching primary ticket {ticket_key}...", file=sys.stderr)
    ticket_data, error = fetch_primary_ticket(
        jira_url, token, ticket_key, parent_link_field
    )
    if error:
        print(f"ERROR: Failed to fetch primary ticket: {error}", file=sys.stderr)
        print(json.dumps({"ticket": ticket_key, "error": error}, indent=2))
        return 1

    # Step 3: Detect parent
    print("  Detecting parent...", file=sys.stderr)
    parent_key, parent_source = detect_parent(ticket_data, parent_link_field)
    parent_info: Optional[Dict] = None

    if parent_key:
        print(f"  Fetching parent {parent_key} (via {parent_source})...", file=sys.stderr)
        parent_info, error = fetch_parent_details(
            jira_url, token, parent_key, parent_source
        )
        if error:
            all_errors.append(error)

    # Step 4: Fetch children
    print("  Fetching children...", file=sys.stderr)
    children, errors = fetch_children(
        jira_url, token, ticket_key, epic_link_field, max_children
    )
    all_errors.extend(errors)

    # Step 5: Fetch siblings (only if parent exists)
    siblings: Dict = {"total": 0, "showing": 0, "skipped": 0, "issues": []}
    if parent_key and parent_source:
        print("  Fetching siblings...", file=sys.stderr)
        siblings, errors = fetch_siblings(
            jira_url, token, ticket_key, parent_key, parent_source, max_siblings
        )
        all_errors.extend(errors)

    # Step 6: Extract issue links (no extra API calls)
    print("  Extracting issue links...", file=sys.stderr)
    issue_links = extract_issue_links(ticket_data, max_links)

    # Step 7: Fetch remote/web links and classify auto-discovered URLs
    print("  Fetching remote links...", file=sys.stderr)
    web_links, auto_discovered, errors = fetch_remote_links(jira_url, token, ticket_key)
    all_errors.extend(errors)

    # Build result
    result: Dict[str, Any] = {
        "ticket": ticket_key,
        "jira_url": jira_url,
        "parent": parent_info,
        "children": children,
        "siblings": siblings,
        "issue_links": issue_links,
        "web_links": web_links,
        "auto_discovered_urls": auto_discovered,
        "errors": all_errors,
    }

    print(json.dumps(result, indent=2))

    if all_errors:
        print(
            f"\n{len(all_errors)} traversal error(s) occurred (see above).",
            file=sys.stderr,
        )

    return 0


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="JIRA Ticket Graph - Traverse JIRA ticket relationships for documentation context",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s PROJ-123
  %(prog)s PROJ-123 --max-children 10 --max-siblings 10

Environment variables:
  JIRA_AUTH_TOKEN  JIRA personal access token (required)
  JIRA_URL         JIRA instance URL (default: https://issues.redhat.com)
""",
    )
    parser.add_argument("ticket", help="JIRA ticket key (e.g., PROJ-123)")
    parser.add_argument(
        "--max-children",
        type=int,
        default=25,
        help="Maximum number of children to fetch (default: 25)",
    )
    parser.add_argument(
        "--max-siblings",
        type=int,
        default=25,
        help="Maximum number of siblings to fetch (default: 25)",
    )
    parser.add_argument(
        "--max-links",
        type=int,
        default=15,
        help="Maximum number of issue links to extract (default: 15)",
    )

    args = parser.parse_args()
    sys.exit(
        run(
            ticket_key=args.ticket,
            max_children=args.max_children,
            max_siblings=args.max_siblings,
            max_links=args.max_links,
        )
    )


if __name__ == "__main__":
    main()
