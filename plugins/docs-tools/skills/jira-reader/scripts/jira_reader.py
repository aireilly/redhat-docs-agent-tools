#!/usr/bin/env python3
"""
JIRA Reader Script for Claude Code Skill

This script provides read-only access to JIRA issues on Red Hat Issue Tracker.
It fetches issue details, comments, custom fields, related Git links, and
traverses the ticket graph (parent, children, siblings, issue links, web links).

Usage:
    python jira_reader.py --issue INFERENG-5233
    python jira_reader.py --issue INFERENG-5233 --include-comments
    python jira_reader.py --jql "project=INFERENG AND fixVersion='3.4'"
    python jira_reader.py --graph INFERENG-5233
"""

import os
import re
import sys
import json
import argparse
import urllib3
from datetime import datetime
from ratelimit import limits, sleep_and_retry

try:
    from jira import JIRA
except ImportError:
    print(json.dumps({"error": "jira package not installed. Run: python3 -m pip install jira"}))
    sys.exit(1)


def load_env_file():
    """Load environment variables from ~/.env file."""
    env_file = os.path.expanduser("~/.env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


class JiraReader:
    """Read-only JIRA client for fetching, analyzing, and traversing issues."""

    def __init__(self, server=None):
        """Initialize JIRA connection with appropriate authentication."""
        load_env_file()

        token = os.environ.get('JIRA_API_TOKEN') or os.environ.get('JIRA_AUTH_TOKEN')
        if not token:
            raise ValueError("JIRA_API_TOKEN environment variable not set. Add it to ~/.env")

        server = server or os.environ.get('JIRA_URL', 'https://redhat.atlassian.net')

        if 'atlassian.net' in server:
            email = os.environ.get('JIRA_EMAIL')
            if not email:
                raise ValueError("JIRA_EMAIL environment variable not set. Required for Atlassian Cloud. Add it to ~/.env")
            self.jira = JIRA(server=server, basic_auth=(email, token))
        else:
            self.jira = JIRA(server=server, token_auth=token)

        self.server = server
        self._epic_link_field = None
        self._parent_link_field = None
        self._custom_fields_discovered = False

    def process_comments(self, comments):
        """
        Process JIRA comments into anonymized threaded format.

        Args:
            comments: List of JIRA comment objects

        Returns:
            List of dictionaries with anonymized comment data
        """
        if not comments:
            return []

        # Create user mapping for anonymization
        user_mapping = {}
        participant_counter = 0

        # Sort comments by creation date
        sorted_comments = sorted(comments, key=lambda x: x.created)

        processed_comments = []

        for comment in sorted_comments:
            # Get or create anonymous participant label
            author_key = comment.author.key if hasattr(comment.author, 'key') else str(comment.author)
            if author_key not in user_mapping:
                participant_counter += 1
                user_mapping[author_key] = f"Participant {chr(64 + participant_counter)}"  # A, B, C, etc.

            participant = user_mapping[author_key]

            # Format timestamp
            try:
                timestamp = datetime.strptime(comment.created[:19], '%Y-%m-%dT%H:%M:%S')
                formatted_time = timestamp.strftime('%Y-%m-%d %H:%M')
            except:
                formatted_time = comment.created[:16].replace('T', ' ')

            # Clean comment body
            comment_body = comment.body.strip() if comment.body else ""

            if comment_body:
                processed_comments.append({
                    "participant": participant,
                    "timestamp": formatted_time,
                    "body": comment_body
                })

        return processed_comments

    def extract_git_links(self, links, git_link_types="all"):
        """
        Extract Git-related links (GitHub/GitLab) from JIRA remote links.

        Args:
            links: List of JIRA remote link objects
            git_link_types: Filter for "github", "gitlab", or "all"

        Returns:
            List of Git URLs
        """
        links_list = []

        if git_link_types == "github":
            prefix = ("github", "www.github")
        elif git_link_types == "gitlab":
            prefix = ("gitlab",)
        else:
            prefix = ("github", "www.github", "gitlab")

        for link in links:
            try:
                host = urllib3.util.parse_url(link.object.url).host
                if host and host.startswith(prefix):
                    links_list.append(link.object.url)
            except:
                continue

        return links_list

    def categorize_issue_type(self, issue_type):
        """
        Categorize issue type into standard categories.

        Args:
            issue_type: JIRA issue type string

        Returns:
            Standardized category
        """
        issue_type_lower = issue_type.lower()

        if issue_type_lower == "bug":
            return "Bug"
        elif issue_type_lower == "vulnerability":
            return "CVE"
        elif issue_type_lower in ["story", "feature"]:
            return "Feature/Story"
        elif issue_type_lower == "epic":
            return "Epic"
        elif issue_type_lower == "task":
            return "Task"
        else:
            return issue_type

    @sleep_and_retry
    @limits(calls=2, period=5)
    def get_issue_data(self, jira_id, include_comments=False, git_link_types="all"):
        """
        Fetch comprehensive data for a JIRA issue.

        Args:
            jira_id: JIRA issue key (e.g., "INFERENG-5233")
            include_comments: Whether to fetch and process comments
            git_link_types: Filter for Git links ("github", "gitlab", or "all")

        Returns:
            Dictionary with issue data
        """
        try:
            issue = self.jira.issue(jira_id)
            links = self.jira.remote_links(jira_id)

            # Get comments if requested
            comments_data = []
            if include_comments:
                comments = self.jira.comments(jira_id)
                comments_data = self.process_comments(comments)

            # Extract Git links
            git_links = self.extract_git_links(links, git_link_types)

            # Extract custom fields
            custom_fields = {}

            # Release Note Type (customfield_10785)
            if hasattr(issue.fields, 'customfield_10785') and issue.fields.customfield_10785:
                release_note_type = issue.fields.customfield_10785.value
                # Normalize "Feature" to "Enhancement"
                release_note_type = "Enhancement" if release_note_type == "Feature" else release_note_type
                custom_fields['release_note_type'] = release_note_type

            # Fix Versions
            if issue.fields.fixVersions:
                custom_fields['fix_versions'] = [v.name for v in issue.fields.fixVersions]

            # Extract assignee safely
            assignee = None
            if issue.fields.assignee:
                assignee = issue.fields.assignee.displayName if hasattr(issue.fields.assignee, 'displayName') else str(issue.fields.assignee)

            # Build response
            return {
                "issue_key": issue.key,
                "issue_type": str(issue.fields.issuetype),
                "issue_category": self.categorize_issue_type(str(issue.fields.issuetype)),
                "priority": str(issue.fields.priority) if issue.fields.priority else "Undefined",
                "status": str(issue.fields.status),
                "assignee": assignee,
                "summary": issue.fields.summary,
                "description": issue.fields.description or "",
                "created": issue.fields.created,
                "updated": issue.fields.updated,
                "comments": comments_data,
                "custom_fields": custom_fields,
                "git_links": git_links,
                "url": f"{self.server}/browse/{issue.key}"
            }

        except Exception as e:
            return {
                "error": f"Failed to fetch issue {jira_id}: {str(e)}",
                "issue_key": jira_id
            }

    @sleep_and_retry
    @limits(calls=2, period=5)
    def search_issues(self, jql, max_results=50, fetch_details=False):
        """
        Search JIRA issues using JQL (JIRA Query Language).

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return
            fetch_details: If True, return issue keys for detailed fetching; if False, return summary info

        Returns:
            List of issue keys (if fetch_details=True) or list of issue summaries (if fetch_details=False)
        """
        try:
            issues = self.jira.search_issues(jql, maxResults=max_results)

            if not fetch_details:
                # Return basic info from search results without additional API calls (FAST)
                summaries = []
                for issue in issues:
                    assignee = None
                    if issue.fields.assignee:
                        assignee = issue.fields.assignee.displayName if hasattr(issue.fields.assignee, 'displayName') else str(issue.fields.assignee)

                    # Extract fix versions
                    fix_versions = []
                    if issue.fields.fixVersions:
                        fix_versions = [v.name for v in issue.fields.fixVersions]

                    summaries.append({
                        "issue_key": issue.key,
                        "issue_type": str(issue.fields.issuetype),
                        "issue_category": self.categorize_issue_type(str(issue.fields.issuetype)),
                        "priority": str(issue.fields.priority) if issue.fields.priority else "Undefined",
                        "status": str(issue.fields.status),
                        "assignee": assignee,
                        "summary": issue.fields.summary,
                        "fix_versions": fix_versions,
                        "url": f"{self.server}/browse/{issue.key}"
                    })
                return summaries
            else:
                # Return issue keys for detailed fetching (SLOW but comprehensive)
                return [issue.key for issue in issues]
        except Exception as e:
            return {"error": f"JQL search failed: {str(e)}"}

    # --- Ticket graph traversal methods ---

    def _discover_custom_fields(self):
        """Discover custom field IDs for 'Epic Link' and 'Parent Link'."""
        if self._custom_fields_discovered:
            return

        try:
            fields = self.jira.fields()
            for field in fields:
                name = field.get("name", "")
                if name == "Epic Link":
                    self._epic_link_field = field["id"]
                elif name == "Parent Link":
                    self._parent_link_field = field["id"]
        except Exception:
            pass

        self._custom_fields_discovered = True

    def _detect_parent(self, issue):
        """
        Detect the parent ticket key from an issue.

        Returns:
            Tuple of (parent_key, source) where source describes how parent was found.
        """
        # Check standard parent field
        if hasattr(issue.fields, 'parent') and issue.fields.parent:
            return issue.fields.parent.key, "parent_field"

        # Check Parent Link custom field
        if self._parent_link_field:
            parent_link = getattr(issue.fields, self._parent_link_field, None)
            if parent_link:
                if isinstance(parent_link, str):
                    return parent_link, "parent_link_custom_field"
                elif hasattr(parent_link, 'key'):
                    return parent_link.key, "parent_link_custom_field"

        return None, None

    @sleep_and_retry
    @limits(calls=2, period=5)
    def _fetch_issue_summary(self, jira_id):
        """Fetch basic summary fields for an issue."""
        try:
            issue = self.jira.issue(jira_id, fields="summary,status,issuetype,description,priority,assignee")
            fields = issue.fields
            return {
                "key": issue.key,
                "summary": fields.summary,
                "status": str(fields.status) if fields.status else None,
                "issuetype": str(fields.issuetype) if fields.issuetype else None,
                "priority": str(fields.priority) if fields.priority else None,
                "assignee": fields.assignee.displayName if fields.assignee and hasattr(fields.assignee, 'displayName') else None,
                "description": fields.description or "",
            }
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                return {
                    "key": jira_id,
                    "summary": None,
                    "status": None,
                    "issuetype": None,
                    "error": "exists but not accessible (HTTP 403)",
                }
            return {"key": jira_id, "error": str(e)}

    def _fetch_children(self, ticket_key, max_children=25):
        """
        Fetch children via parent = KEY and "Epic Link" = KEY JQL queries.

        Returns:
            Dictionary with total, showing, skipped, and issues list.
        """
        errors = []
        seen_keys = set()
        issues = []

        # Query 1: Standard parent field
        jql1 = f"parent = {ticket_key} ORDER BY status ASC, key ASC"
        try:
            results = self.jira.search_issues(jql1, maxResults=max_children)
            for issue in results:
                if issue.key not in seen_keys:
                    seen_keys.add(issue.key)
                    f = issue.fields
                    issues.append({
                        "key": issue.key,
                        "summary": f.summary,
                        "status": str(f.status) if f.status else None,
                        "issuetype": str(f.issuetype) if f.issuetype else None,
                        "priority": str(f.priority) if f.priority else None,
                        "assignee": f.assignee.displayName if f.assignee and hasattr(f.assignee, 'displayName') else None,
                    })
        except Exception as e:
            errors.append(f"Children query (parent field): {e}")

        # Query 2: Epic Link custom field
        if self._epic_link_field:
            jql2 = f'"Epic Link" = {ticket_key} ORDER BY status ASC, key ASC'
            try:
                results = self.jira.search_issues(jql2, maxResults=max_children)
                for issue in results:
                    if issue.key not in seen_keys:
                        seen_keys.add(issue.key)
                        f = issue.fields
                        issues.append({
                            "key": issue.key,
                            "summary": f.summary,
                            "status": str(f.status) if f.status else None,
                            "issuetype": str(f.issuetype) if f.issuetype else None,
                            "priority": str(f.priority) if f.priority else None,
                            "assignee": f.assignee.displayName if f.assignee and hasattr(f.assignee, 'displayName') else None,
                        })
            except Exception as e:
                errors.append(f"Children query (Epic Link): {e}")

        showing = min(len(issues), max_children)
        issues = issues[:max_children]

        return {
            "total": len(seen_keys),
            "showing": showing,
            "skipped": max(0, len(seen_keys) - showing),
            "issues": issues,
        }, errors

    def _fetch_siblings(self, ticket_key, parent_key, parent_source, max_siblings=25):
        """
        Fetch sibling tickets (active statuses only).

        Returns:
            Dictionary with total, showing, skipped, and issues list.
        """
        errors = []

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

        try:
            results = self.jira.search_issues(jql, maxResults=max_siblings)
            issues = []
            for issue in results:
                f = issue.fields
                issues.append({
                    "key": issue.key,
                    "summary": f.summary,
                    "status": str(f.status) if f.status else None,
                    "issuetype": str(f.issuetype) if f.issuetype else None,
                })

            total = results.total if hasattr(results, 'total') else len(issues)
            showing = len(issues)
            return {
                "total": total,
                "showing": showing,
                "skipped": max(0, total - showing),
                "issues": issues,
            }, errors
        except Exception as e:
            errors.append(f"Siblings query: {e}")
            return {"total": 0, "showing": 0, "skipped": 0, "issues": []}, errors

    def _extract_issue_links(self, issue, max_links=15):
        """
        Extract issue link summaries from an issue object.

        No additional API calls needed — data is embedded in the issuelinks field.
        """
        raw_links = issue.fields.issuelinks if hasattr(issue.fields, 'issuelinks') else []
        links = []

        for link in raw_links:
            link_type = link.type

            if hasattr(link, 'inwardIssue') and link.inwardIssue:
                linked_issue = link.inwardIssue
                direction = link_type.inward
            elif hasattr(link, 'outwardIssue') and link.outwardIssue:
                linked_issue = link.outwardIssue
                direction = link_type.outward
            else:
                continue

            links.append({
                "key": linked_issue.key,
                "direction": direction,
                "link_type": link_type.name,
                "summary": linked_issue.fields.summary if hasattr(linked_issue.fields, 'summary') else None,
                "status": str(linked_issue.fields.status) if hasattr(linked_issue.fields, 'status') and linked_issue.fields.status else None,
                "issuetype": str(linked_issue.fields.issuetype) if hasattr(linked_issue.fields, 'issuetype') and linked_issue.fields.issuetype else None,
            })

            if len(links) >= max_links:
                break

        total = len(raw_links)
        showing = len(links)
        return {
            "total": total,
            "showing": showing,
            "skipped": max(0, total - showing),
            "links": links,
        }

    def _classify_url(self, url):
        """Classify a URL as 'pull_request', 'google_doc', or 'other'."""
        if re.search(r"github\.com/.+/pull/\d+", url):
            return "pull_request"
        if re.search(r"gitlab\..+/-/merge_requests/\d+", url):
            return "pull_request"
        if re.search(r"docs\.google\.com/document/", url):
            return "google_doc"
        return "other"

    def _fetch_remote_links(self, ticket_key):
        """
        Fetch remote/web links from the ticket and classify URLs.

        Returns:
            Tuple of (web_links_dict, auto_discovered_urls_dict, errors).
        """
        errors = []
        try:
            remote_links = self.jira.remote_links(ticket_key)
        except Exception as e:
            errors.append(f"Remote links: {e}")
            return {"total": 0, "links": []}, {"pull_requests": [], "google_docs": []}, errors

        links = []
        pull_requests = []
        google_docs = []

        for item in remote_links:
            try:
                link_url = item.object.url if hasattr(item.object, 'url') else ""
                title = item.object.title if hasattr(item.object, 'title') else ""
                link_type = self._classify_url(link_url)
                links.append({"title": title, "url": link_url, "type": link_type})
                if link_type == "pull_request":
                    pull_requests.append(link_url)
                elif link_type == "google_doc":
                    google_docs.append(link_url)
            except Exception:
                continue

        web_links = {"total": len(links), "links": links}
        auto_discovered = {"pull_requests": pull_requests, "google_docs": google_docs}
        return web_links, auto_discovered, errors

    def get_ticket_graph(self, ticket_key, max_children=25, max_siblings=25, max_links=15):
        """
        Traverse the JIRA ticket graph: parent, children, siblings, issue links, web links.

        All traversal is bounded to 1 level deep from the primary ticket.

        Args:
            ticket_key: JIRA issue key (e.g., "INFERENG-5233")
            max_children: Maximum children to fetch
            max_siblings: Maximum siblings to fetch
            max_links: Maximum issue links to extract

        Returns:
            Dictionary with full graph traversal results
        """
        all_errors = []

        # Step 1: Discover custom fields
        self._discover_custom_fields()

        # Step 2: Fetch primary ticket
        try:
            issue = self.jira.issue(ticket_key)
        except Exception as e:
            return {"ticket": ticket_key, "error": f"Failed to fetch primary ticket: {e}"}

        # Step 3: Detect parent
        parent_key, parent_source = self._detect_parent(issue)
        parent_info = None

        if parent_key:
            parent_info = self._fetch_issue_summary(parent_key)
            if parent_info and "error" not in parent_info:
                parent_info["source"] = parent_source
            elif parent_info:
                parent_info["source"] = parent_source

        # Step 4: Fetch children
        children, errors = self._fetch_children(ticket_key, max_children)
        all_errors.extend(errors)

        # Step 5: Fetch siblings (only if parent exists)
        siblings = {"total": 0, "showing": 0, "skipped": 0, "issues": []}
        if parent_key and parent_source:
            siblings, errors = self._fetch_siblings(ticket_key, parent_key, parent_source, max_siblings)
            all_errors.extend(errors)

        # Step 6: Extract issue links (no extra API calls)
        issue_links = self._extract_issue_links(issue, max_links)

        # Step 7: Fetch remote/web links and classify URLs
        web_links, auto_discovered, errors = self._fetch_remote_links(ticket_key)
        all_errors.extend(errors)

        return {
            "ticket": ticket_key,
            "jira_url": self.server,
            "parent": parent_info,
            "children": children,
            "siblings": siblings,
            "issue_links": issue_links,
            "web_links": web_links,
            "auto_discovered_urls": auto_discovered,
            "errors": all_errors,
        }


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Fetch and analyze JIRA issues from Red Hat Issue Tracker"
    )
    parser.add_argument(
        '--issue',
        action='append',
        help='JIRA issue key (e.g., INFERENG-5233). Can be specified multiple times.'
    )
    parser.add_argument(
        '--jql',
        help='JQL query to search for issues'
    )
    parser.add_argument(
        '--graph',
        help='Traverse the ticket graph for a JIRA issue key (parent, children, siblings, links)'
    )
    parser.add_argument(
        '--include-comments',
        action='store_true',
        help='Include anonymized comment threads'
    )
    parser.add_argument(
        '--git-links',
        choices=['github', 'gitlab', 'all'],
        default='all',
        help='Filter Git links by type'
    )
    parser.add_argument(
        '--max-results',
        type=int,
        default=50,
        help='Maximum number of results for JQL search (default: 50)'
    )
    parser.add_argument(
        '--fetch-details',
        action='store_true',
        help='Fetch full details for each issue (slow). By default, JQL searches return fast summaries only.'
    )
    parser.add_argument(
        '--max-children',
        type=int,
        default=25,
        help='Maximum children to fetch in graph mode (default: 25)'
    )
    parser.add_argument(
        '--max-siblings',
        type=int,
        default=25,
        help='Maximum siblings to fetch in graph mode (default: 25)'
    )
    parser.add_argument(
        '--max-links',
        type=int,
        default=15,
        help='Maximum issue links to extract in graph mode (default: 15)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.issue and not args.jql and not args.graph:
        parser.error("Must specify --issue, --jql, or --graph")

    try:
        reader = JiraReader()

        # Handle graph traversal
        if args.graph:
            result = reader.get_ticket_graph(
                args.graph,
                max_children=args.max_children,
                max_siblings=args.max_siblings,
                max_links=args.max_links,
            )
            print(json.dumps(result, indent=2))
            if result.get("error"):
                sys.exit(1)
            return

        results = []

        # Handle JQL search
        if args.jql:
            search_results = reader.search_issues(args.jql, args.max_results, fetch_details=args.fetch_details)
            if isinstance(search_results, dict) and 'error' in search_results:
                print(json.dumps(search_results, indent=2))
                sys.exit(1)

            if args.fetch_details:
                # search_results contains issue keys, fetch details for each
                for issue_key in search_results:
                    issue_data = reader.get_issue_data(
                        issue_key,
                        include_comments=args.include_comments,
                        git_link_types=args.git_links
                    )
                    results.append(issue_data)
            else:
                # search_results already contains summaries, use directly
                results = search_results

        # Handle individual issue requests
        elif args.issue:
            for issue_key in args.issue:
                issue_data = reader.get_issue_data(
                    issue_key,
                    include_comments=args.include_comments,
                    git_link_types=args.git_links
                )
                results.append(issue_data)

        # Output results as JSON
        if len(results) == 1:
            print(json.dumps(results[0], indent=2))
        else:
            print(json.dumps(results, indent=2))

    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
