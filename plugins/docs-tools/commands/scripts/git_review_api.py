#!/usr/bin/env python3
"""
Git Review API - Python library for GitHub PRs and GitLab MRs.

This module provides a unified API for:
- Fetching PR/MR information (title, description, changed files)
- Fetching review comments and discussions
- Posting inline review comments to GitHub PRs and GitLab MRs
- Extracting line numbers from PR/MR diffs for accurate comment placement
- Validating comments against actual diff content

Usage:
    from git_review_api import GitReviewAPI

    api = GitReviewAPI.from_url("https://github.com/owner/repo/pull/123")

    # Get PR info
    info = api.get_pr_info()

    # Get changed files
    files = api.get_changed_files()

    # Get review comments
    comments = api.get_review_comments()

    # Post comments
    api.post_comments([
        {"file": "path/to/file.adoc", "line": 42, "message": "Issue description"}
    ])

Authentication:
    Requires tokens in ~/.env:
    - GitHub: GITHUB_TOKEN environment variable
    - GitLab: GITLAB_TOKEN environment variable
"""

import json
import os
import re
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from env_utils import load_env_file

# Terminal colors removed - script runs inside Claude Code where escape codes
# are not rendered and interfere with output capture
RED = ''
GREEN = ''
YELLOW = ''
NC = ''


def color_print(color: str, prefix: str, message: str) -> None:
    """Print output to terminal."""
    print(f"  {prefix}: {message}")


@dataclass
class ReviewComment:
    """Represents a single review comment to post."""
    file: str
    line: int
    message: str
    severity: str = "suggestion"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "severity": self.severity
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ReviewComment":
        """Create from dictionary."""
        return cls(
            file=data.get("file", ""),
            line=int(data.get("line", 0)),
            message=data.get("message", ""),
            severity=data.get("severity", "suggestion")
        )


@dataclass
class DiffLine:
    """Represents a line from a diff with its file line number."""
    file_line: int
    content: str
    is_added: bool = True


@dataclass
class PostResult:
    """Result of posting comments."""
    posted: int = 0
    skipped: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "posted": self.posted,
            "skipped": self.skipped,
            "failed": self.failed,
            "errors": self.errors
        }


class GitReviewAPI(ABC):
    """
    Abstract base class for Git review APIs (GitHub/GitLab).

    Provides common functionality for posting review comments,
    extracting line numbers from diffs, and validating comments.
    """

    def __init__(self, url: str):
        """
        Initialize the API with a PR/MR URL.

        Args:
            url: The full URL to the PR or MR
        """
        self.url = url
        self._pr_info: Optional[Dict] = None
        self._diff_cache: Dict[str, str] = {}

    @classmethod
    def from_url(cls, url: str) -> "GitReviewAPI":
        """
        Factory method to create the appropriate API instance from a URL.

        Args:
            url: GitHub PR or GitLab MR URL

        Returns:
            GitHubReviewAPI or GitLabReviewAPI instance

        Raises:
            ValueError: If URL format is not recognized
        """
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        if "github.com" in host:
            return GitHubReviewAPI(url)
        elif "gitlab" in host:
            return GitLabReviewAPI(url)
        else:
            raise ValueError(
                f"Unable to determine platform from URL: {url}\n"
                "Supported formats:\n"
                "  GitHub: https://github.com/owner/repo/pull/123\n"
                "  GitLab: https://gitlab.com/group/project/-/merge_requests/123"
            )

    @abstractmethod
    def get_pr_info(self) -> Dict:
        """
        Fetch PR/MR information.

        Returns:
            Dictionary with at least 'head_sha' and platform-specific info
        """
        pass

    @abstractmethod
    def get_diff(self, file_path: Optional[str] = None) -> str:
        """
        Fetch the diff for the PR/MR.

        Args:
            file_path: Optional file path to get diff for specific file

        Returns:
            Unified diff as string
        """
        pass

    @abstractmethod
    def get_existing_comments(self) -> List[str]:
        """
        Get existing review comments as "file:line" strings.

        Returns:
            List of "file:line" strings for existing comments
        """
        pass

    @abstractmethod
    def post_inline_comment(self, comment: ReviewComment) -> Tuple[bool, str]:
        """
        Post an inline comment on a specific line.

        Args:
            comment: ReviewComment to post

        Returns:
            Tuple of (success, error_message)
        """
        pass

    @abstractmethod
    def post_pr_comment(self, file: str, line: int, body: str) -> Tuple[bool, str]:
        """
        Post a general PR/MR comment (not inline).

        Args:
            file: File path for context
            line: Line number for context
            body: Comment body

        Returns:
            Tuple of (success, error_message)
        """
        pass

    @abstractmethod
    def get_changed_files(self) -> List[Dict]:
        """
        Get list of changed files in the PR/MR.

        Returns:
            List of dicts with 'path', 'status' (added/modified/deleted), 'additions', 'deletions'
        """
        pass

    @abstractmethod
    def get_review_comments(self, include_resolved: bool = False) -> List[Dict]:
        """
        Get review comments/discussions on the PR/MR.

        Args:
            include_resolved: If True, include resolved comments

        Returns:
            List of comment dicts with 'id', 'path', 'line', 'body', 'author', 'resolved'
        """
        pass

    def extract_line_numbers(self, file_path: str) -> List[DiffLine]:
        """
        Extract line numbers for added/modified lines from diff.

        Args:
            file_path: Path to file in the PR/MR

        Returns:
            List of DiffLine objects with file line numbers and content
        """
        diff = self.get_diff()
        return self._parse_diff_for_file(diff, file_path)

    def _parse_diff_for_file(self, diff: str, target_file: str) -> List[DiffLine]:
        """
        Parse unified diff to extract added lines with their file line numbers.

        This ports the AWK logic from extract-line-numbers.sh to Python.

        Args:
            diff: Unified diff content
            target_file: File path to extract lines for

        Returns:
            List of DiffLine objects
        """
        lines = diff.split('\n')
        result = []
        in_file = False
        file_line = 0

        for line in lines:
            # Match file header: diff --git a/path b/path
            if line.startswith('diff --git'):
                in_file = f"b/{target_file}" in line
                continue

            # Skip other diff headers
            if line.startswith('---') or line.startswith('+++') or \
               line.startswith('index') or line.startswith('new file') or \
               line.startswith('deleted file'):
                continue

            # Match hunk header: @@ -old,count +new,count @@
            if line.startswith('@@') and in_file:
                # Parse +new,count or +new from hunk header
                match = re.search(r'\+(\d+)', line)
                if match:
                    file_line = int(match.group(1)) - 1  # Will be incremented
                continue

            # Process content lines only if we're in the target file
            if in_file:
                if line.startswith('-'):
                    # Deleted line - do not increment file_line
                    continue
                elif line.startswith('+'):
                    # Added line
                    file_line += 1
                    content = line[1:]  # Remove leading +
                    result.append(DiffLine(
                        file_line=file_line,
                        content=content,
                        is_added=True
                    ))
                elif line.startswith(' ') or line == '':
                    # Context line or empty - increment but don't add
                    file_line += 1

        return result

    def find_line_for_pattern(self, file_path: str, pattern: str) -> Optional[int]:
        """
        Find the line number for a pattern in a file's diff.

        Args:
            file_path: Path to file in the PR/MR
            pattern: Pattern to search for

        Returns:
            Line number if found, None otherwise
        """
        diff_lines = self.extract_line_numbers(file_path)

        for diff_line in diff_lines:
            if pattern in diff_line.content:
                return diff_line.file_line

        return None

    def validate_comments(self, comments: List[Dict]) -> List[Dict]:
        """
        Validate comments against the actual diff.

        Args:
            comments: List of comment dictionaries

        Returns:
            List of validation results with 'valid' and 'content' fields
        """
        results = []

        # Build a lookup of all diff lines by file
        diff = self.get_diff()
        all_files = set()

        # Find all files in diff
        for line in diff.split('\n'):
            if line.startswith('diff --git'):
                match = re.search(r'b/(.+)$', line)
                if match:
                    all_files.add(match.group(1))

        for comment in comments:
            file_path = comment.get('file', '')
            line_num = int(comment.get('line', 0))

            diff_lines = self.extract_line_numbers(file_path)
            line_lookup = {dl.file_line: dl.content for dl in diff_lines}

            if line_num in line_lookup:
                results.append({
                    'file': file_path,
                    'line': line_num,
                    'valid': True,
                    'content': line_lookup[line_num][:60]
                })
            else:
                results.append({
                    'file': file_path,
                    'line': line_num,
                    'valid': False,
                    'content': None,
                    'reason': 'Line not in diff (may be context-only)'
                })

        return results

    def post_comments(self, comments: List[Dict], dry_run: bool = False) -> PostResult:
        """
        Post multiple review comments.

        Args:
            comments: List of comment dictionaries
            dry_run: If True, don't actually post comments

        Returns:
            PostResult with counts and errors
        """
        result = PostResult()

        # Get PR info and existing comments
        try:
            self.get_pr_info()
            existing = self.get_existing_comments()
        except Exception as e:
            result.failed = len(comments)
            result.errors.append(f"Failed to get PR info: {str(e)}")
            return result

        print("\nPosting comments...")

        for comment_dict in comments:
            comment = ReviewComment.from_dict(comment_dict)
            key = f"{comment.file}:{comment.line}"

            # Check for duplicates
            if key in existing:
                color_print(YELLOW, "Skip", f"{key} (comment exists)")
                result.skipped += 1
                continue

            if dry_run:
                color_print(GREEN, "Would post", key)
                result.posted += 1
                continue

            # Format the comment body
            body = f"{comment.message}\n\n\U0001F916 RHAI docs Claude Code review"

            # Try inline comment first
            success, error = self.post_inline_comment(comment)

            if success:
                color_print(GREEN, "Posted", key)
                result.posted += 1
            else:
                # Try as PR-level comment
                color_print(YELLOW, "Warning", f"Could not post inline at {key}")
                print(f"    Reason: {error}")
                print(f"    Fallback: Posting as PR comment...")

                success, error = self.post_pr_comment(comment.file, comment.line, body)

                if success:
                    color_print(GREEN, "Posted", f"{key} (as PR comment)")
                    result.posted += 1
                else:
                    color_print(RED, "Failed", key)
                    result.failed += 1
                    result.errors.append(f"{key}: {error}")

            # Rate limiting
            time.sleep(0.3)

        print(f"\nPosted: {result.posted}, Skipped: {result.skipped}, Failed: {result.failed}")
        return result


class GitHubReviewAPI(GitReviewAPI):
    """GitHub-specific implementation of the review API."""

    def __init__(self, url: str):
        """Initialize GitHub API with PR URL."""
        super().__init__(url)
        self._parse_url()
        self._init_auth()

    def _parse_url(self) -> None:
        """Parse GitHub PR URL to extract owner, repo, and PR number."""
        parsed = urlparse(self.url)
        parts = parsed.path.strip('/').split('/')

        if len(parts) < 4 or parts[2] != 'pull':
            raise ValueError(f"Invalid GitHub PR URL format: {self.url}")

        self.owner = parts[0]
        self.repo = parts[1]
        self.pr_number = int(parts[3])
        self.owner_repo = f"{self.owner}/{self.repo}"

    def _init_auth(self) -> None:
        """Initialize authentication - requires GITHUB_TOKEN."""
        load_env_file()
        self.token = os.environ.get('GITHUB_TOKEN')

        if not self.token:
            raise RuntimeError(
                "GitHub authentication required.\n"
                "Set GITHUB_TOKEN in ~/.env file:\n"
                "  GITHUB_TOKEN=your_personal_access_token\n"
                "Token requires 'repo' scope for private repos or 'public_repo' for public."
            )

        print("Using GITHUB_TOKEN for GitHub API")

    def _api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a GitHub API request."""
        import urllib.request

        url = f"https://api.github.com/{endpoint}"
        headers = {
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'git-review-api'
        }

        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        body = json.dumps(data).encode() if data else None
        if body:
            headers['Content-Type'] = 'application/json'

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            try:
                error_json = json.loads(error_body)
                return error_json
            except json.JSONDecodeError:
                return {"error": error_body}

    def _api(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make API request."""
        return self._api_request(method, endpoint, data)

    def get_pr_info(self) -> Dict:
        """Fetch PR information including head SHA."""
        if self._pr_info:
            return self._pr_info

        print(f"Repository: {self.owner_repo}")
        print(f"PR Number: {self.pr_number}")

        response = self._api('GET', f"repos/{self.owner_repo}/pulls/{self.pr_number}")

        if 'error' in response or not response.get('head'):
            raise RuntimeError(f"Failed to fetch PR info: {response.get('error', 'Unknown error')}")

        self._pr_info = {
            'head_sha': response['head']['sha'],
            'title': response.get('title', ''),
            'body': response.get('body', ''),
            'base_ref': response.get('base', {}).get('ref', 'main')
        }

        print(f"Head SHA: {self._pr_info['head_sha']}")
        return self._pr_info

    def get_diff(self, file_path: Optional[str] = None) -> str:
        """Fetch the diff for the PR."""
        import urllib.request

        cache_key = file_path or '_all_'
        if cache_key in self._diff_cache:
            return self._diff_cache[cache_key]

        url = f"https://api.github.com/repos/{self.owner_repo}/pulls/{self.pr_number}"
        headers = {
            'Accept': 'application/vnd.github.diff',
            'Authorization': f'Bearer {self.token}',
            'User-Agent': 'git-review-api'
        }

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            diff = response.read().decode()

        self._diff_cache[cache_key] = diff
        return diff

    def get_existing_comments(self) -> List[str]:
        """Get existing review comments as file:line strings."""
        response = self._api('GET', f"repos/{self.owner_repo}/pulls/{self.pr_number}/comments")

        if isinstance(response, dict) and 'error' in response:
            return []

        existing = []
        for comment in response:
            path = comment.get('path', '')
            line = comment.get('line') or comment.get('original_line')
            if path and line:
                existing.append(f"{path}:{line}")

        return existing

    def post_inline_comment(self, comment: ReviewComment) -> Tuple[bool, str]:
        """Post an inline comment on a specific line."""
        pr_info = self.get_pr_info()

        body = f"{comment.message}\n\n\U0001F916 RHAI docs Claude Code review"

        data = {
            'body': body,
            'commit_id': pr_info['head_sha'],
            'path': comment.file,
            'line': comment.line,
            'side': 'RIGHT'
        }

        response = self._api(
            'POST',
            f"repos/{self.owner_repo}/pulls/{self.pr_number}/comments",
            data
        )

        if response.get('id'):
            return True, ""
        else:
            return False, response.get('message', response.get('error', 'Unknown error'))

    def post_pr_comment(self, file: str, line: int, body: str) -> Tuple[bool, str]:
        """Post a general PR comment (not inline)."""
        note_body = f"**{file}:{line}**\n\n{body}"

        response = self._api(
            'POST',
            f"repos/{self.owner_repo}/issues/{self.pr_number}/comments",
            {'body': note_body}
        )

        if response.get('id'):
            return True, ""
        else:
            return False, response.get('message', response.get('error', 'Unknown error'))

    def get_changed_files(self) -> List[Dict]:
        """Get list of changed files in the PR."""
        response = self._api('GET', f"repos/{self.owner_repo}/pulls/{self.pr_number}/files")

        if isinstance(response, dict) and 'error' in response:
            raise RuntimeError(f"Failed to fetch changed files: {response.get('error')}")

        files = []
        for f in response:
            files.append({
                'path': f.get('filename', ''),
                'status': f.get('status', 'modified'),
                'additions': f.get('additions', 0),
                'deletions': f.get('deletions', 0),
                'changes': f.get('changes', 0)
            })

        return files

    def get_review_comments(self, include_resolved: bool = False) -> List[Dict]:
        """
        Get review comments on the PR.

        GitHub doesn't have a 'resolved' concept for review comments,
        but we filter by in_reply_to_id to get top-level comments only.
        """
        # Bot patterns to filter out
        bot_patterns = ['bot', 'gemini', 'mergify', 'github-actions', 'dependabot']

        response = self._api('GET', f"repos/{self.owner_repo}/pulls/{self.pr_number}/comments")

        if isinstance(response, dict) and 'error' in response:
            return []

        comments = []
        for c in response:
            # Skip replies (only get top-level comments)
            if c.get('in_reply_to_id'):
                continue

            author = c.get('user', {}).get('login', '')

            # Skip bot comments
            if any(pattern in author.lower() for pattern in bot_patterns):
                continue

            comments.append({
                'id': c.get('id'),
                'path': c.get('path', ''),
                'line': c.get('line') or c.get('original_line'),
                'body': c.get('body', ''),
                'author': author,
                'resolved': False,  # GitHub doesn't track resolution
                'created_at': c.get('created_at', ''),
                'url': c.get('html_url', '')
            })

        return comments


class GitLabReviewAPI(GitReviewAPI):
    """GitLab-specific implementation of the review API."""

    def __init__(self, url: str):
        """Initialize GitLab API with MR URL."""
        super().__init__(url)
        self._parse_url()
        self._init_auth()
        self._version_info: Optional[Dict] = None

    def _parse_url(self) -> None:
        """Parse GitLab MR URL to extract host, project, and MR ID."""
        parsed = urlparse(self.url)
        self.host = parsed.netloc
        path = parsed.path.strip('/')

        # Handle /-/merge_requests/123 format
        if '/-/merge_requests/' in path:
            parts = path.split('/-/merge_requests/')
            self.project_path = parts[0]
            self.mr_id = int(parts[1].split('/')[0].split('?')[0])
        else:
            raise ValueError(f"Invalid GitLab MR URL format: {self.url}")

        # URL-encode project path for API calls
        self.project_encoded = self.project_path.replace('/', '%2F')

    def _init_auth(self) -> None:
        """Initialize authentication - requires GITLAB_TOKEN."""
        load_env_file()
        self.token = os.environ.get('GITLAB_TOKEN')

        if not self.token:
            raise RuntimeError(
                f"GitLab authentication required.\n"
                f"Set GITLAB_TOKEN in ~/.env file:\n"
                f"  GITLAB_TOKEN=your_personal_access_token\n"
                f"Token requires 'api' scope for full API access."
            )

        print(f"Using GITLAB_TOKEN for GitLab API ({self.host})")

    def _api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a GitLab API request."""
        import urllib.request

        url = f"https://{self.host}/api/v4/{endpoint}"
        headers = {
            'User-Agent': 'git-review-api'
        }

        if self.token:
            headers['PRIVATE-TOKEN'] = self.token

        body = json.dumps(data).encode() if data else None
        if body:
            headers['Content-Type'] = 'application/json'

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            try:
                error_json = json.loads(error_body)
                return {"error": error_json.get('message', error_body)}
            except json.JSONDecodeError:
                return {"error": error_body}

    def _api(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make API request."""
        return self._api_request(method, endpoint, data)

    def _get_version_info(self) -> Dict:
        """Get MR version info for position objects."""
        if self._version_info:
            return self._version_info

        response = self._api(
            'GET',
            f"projects/{self.project_encoded}/merge_requests/{self.mr_id}/versions"
        )

        if isinstance(response, dict) and 'error' in response:
            raise RuntimeError(f"Failed to fetch MR versions: {response['error']}")

        if not response or not isinstance(response, list):
            raise RuntimeError("Failed to fetch MR versions: empty response")

        self._version_info = {
            'base_sha': response[0].get('base_commit_sha'),
            'head_sha': response[0].get('head_commit_sha'),
            'start_sha': response[0].get('start_commit_sha')
        }

        return self._version_info

    def get_pr_info(self) -> Dict:
        """Fetch MR information including version SHAs."""
        if self._pr_info:
            return self._pr_info

        print(f"GitLab Host: {self.host}")
        print(f"Project: {self.project_path}")
        print(f"MR ID: {self.mr_id}")

        version_info = self._get_version_info()

        self._pr_info = {
            'head_sha': version_info['head_sha'],
            'base_sha': version_info['base_sha'],
            'start_sha': version_info['start_sha']
        }

        print(f"Base SHA: {self._pr_info['base_sha']}")
        print(f"Head SHA: {self._pr_info['head_sha']}")

        return self._pr_info

    def get_diff(self, file_path: Optional[str] = None) -> str:
        """Fetch the diff for the MR."""
        cache_key = file_path or '_all_'
        if cache_key in self._diff_cache:
            return self._diff_cache[cache_key]

        response = self._api(
            'GET',
            f"projects/{self.project_encoded}/merge_requests/{self.mr_id}/changes"
        )

        if isinstance(response, dict) and 'error' in response:
            raise RuntimeError(f"Failed to fetch MR changes: {response['error']}")

        changes = response.get('changes', [])

        # Build unified diff format
        diff_parts = []
        for change in changes:
            old_path = change.get('old_path', '')
            new_path = change.get('new_path', '')
            diff_content = change.get('diff', '')

            diff_parts.append(f"diff --git a/{old_path} b/{new_path}")
            diff_parts.append(diff_content)

        diff = '\n'.join(diff_parts)
        self._diff_cache[cache_key] = diff
        return diff

    def get_existing_comments(self) -> List[str]:
        """Get existing discussion comments as file:line strings."""
        response = self._api(
            'GET',
            f"projects/{self.project_encoded}/merge_requests/{self.mr_id}/discussions"
        )

        if isinstance(response, dict) and 'error' in response:
            return []

        existing = []
        for discussion in response:
            notes = discussion.get('notes', [])
            if notes:
                note = notes[0]
                position = note.get('position')
                if position and position.get('new_line'):
                    path = position.get('new_path', '')
                    line = position.get('new_line')
                    if path and line:
                        existing.append(f"{path}:{line}")

        return existing

    def post_inline_comment(self, comment: ReviewComment) -> Tuple[bool, str]:
        """Post an inline comment on a specific line."""
        pr_info = self.get_pr_info()

        body = f"{comment.message}\n\n\U0001F916 RHAI docs Claude Code review"

        position = {
            'base_sha': pr_info['base_sha'],
            'head_sha': pr_info['head_sha'],
            'start_sha': pr_info['start_sha'],
            'old_path': comment.file,
            'new_path': comment.file,
            'new_line': comment.line,
            'position_type': 'text'
        }

        data = {
            'body': body,
            'position': position
        }

        response = self._api(
            'POST',
            f"projects/{self.project_encoded}/merge_requests/{self.mr_id}/discussions",
            data
        )

        if response.get('id'):
            return True, ""
        else:
            return False, response.get('message', response.get('error', 'Unknown error'))

    def post_pr_comment(self, file: str, line: int, body: str) -> Tuple[bool, str]:
        """Post a general MR note (not inline)."""
        note_body = f"**{file}:{line}**\n\n{body}"

        response = self._api(
            'POST',
            f"projects/{self.project_encoded}/merge_requests/{self.mr_id}/notes",
            {'body': note_body}
        )

        if response.get('id'):
            return True, ""
        else:
            return False, response.get('message', response.get('error', 'Unknown error'))

    def get_changed_files(self) -> List[Dict]:
        """Get list of changed files in the MR."""
        response = self._api(
            'GET',
            f"projects/{self.project_encoded}/merge_requests/{self.mr_id}/changes"
        )

        if isinstance(response, dict) and 'error' in response:
            raise RuntimeError(f"Failed to fetch changed files: {response.get('error')}")

        changes = response.get('changes', [])
        files = []
        for c in changes:
            # Count additions and deletions from diff
            diff = c.get('diff', '')
            additions = diff.count('\n+') - diff.count('\n+++')
            deletions = diff.count('\n-') - diff.count('\n---')

            files.append({
                'path': c.get('new_path', c.get('old_path', '')),
                'status': 'added' if c.get('new_file') else ('deleted' if c.get('deleted_file') else 'modified'),
                'additions': max(0, additions),
                'deletions': max(0, deletions),
                'changes': max(0, additions) + max(0, deletions)
            })

        return files

    def get_review_comments(self, include_resolved: bool = False) -> List[Dict]:
        """Get review comments/discussions on the MR."""
        # Bot patterns to filter out
        bot_patterns = ['bot', 'gemini', 'mergify', 'gitlab-actions']

        response = self._api(
            'GET',
            f"projects/{self.project_encoded}/merge_requests/{self.mr_id}/discussions"
        )

        if isinstance(response, dict) and 'error' in response:
            return []

        comments = []
        for discussion in response:
            notes = discussion.get('notes', [])
            if not notes:
                continue

            # Get first note (the main comment)
            note = notes[0]

            # Skip system notes
            if note.get('system'):
                continue

            # Check if resolvable and resolved
            resolvable = note.get('resolvable', False)
            resolved = note.get('resolved', False)

            # Skip resolved if not including them
            if resolvable and resolved and not include_resolved:
                continue

            author = note.get('author', {}).get('username', '')

            # Skip bot comments
            if any(pattern in author.lower() for pattern in bot_patterns):
                continue

            # Get position info for inline comments
            position = note.get('position')
            path = ''
            line = None
            if position:
                path = position.get('new_path', '')
                line = position.get('new_line')

            comments.append({
                'id': note.get('id'),
                'discussion_id': discussion.get('id'),
                'path': path,
                'line': line,
                'body': note.get('body', ''),
                'author': author,
                'resolved': resolved,
                'resolvable': resolvable,
                'created_at': note.get('created_at', ''),
                'url': note.get('web_url', '')
            })

        return comments


def load_comments_file(file_path: str) -> List[Dict]:
    """
    Load and validate a comments JSON file.

    Args:
        file_path: Path to JSON file containing comments

    Returns:
        List of comment dictionaries

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid or empty
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Comments file not found: {file_path}")

    with open(file_path) as f:
        try:
            comments = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in comments file: {e}")

    if not isinstance(comments, list):
        raise ValueError("Comments file must contain a JSON array")

    return comments


# =============================================================================
# CLI Interface
# =============================================================================

def cmd_post(args) -> int:
    """Handle 'post' subcommand."""
    try:
        comments = load_comments_file(args.comments_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"{RED}Error: {e}{NC}")
        return 1

    if len(comments) == 0:
        print("No comments to post")
        return 0

    print(f"Processing {len(comments)} review comments...")

    try:
        api = GitReviewAPI.from_url(args.pr_url)
    except (ValueError, RuntimeError) as e:
        print(f"{RED}Error: {e}{NC}")
        return 1

    try:
        result = api.post_comments(comments, dry_run=args.dry_run)
    except Exception as e:
        print(f"{RED}Error posting comments: {e}{NC}")
        return 1

    print()
    if args.dry_run:
        print(f"{GREEN}Dry run completed{NC}")
    else:
        print(f"{GREEN}Review comments completed{NC}")

    if result.errors:
        print(f"\nErrors: {json.dumps(result.errors)}")

    return 1 if result.failed > 0 else 0


def cmd_extract(args) -> int:
    """Handle 'extract' subcommand."""
    try:
        api = GitReviewAPI.from_url(args.pr_url)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.dump:
        # Dump mode - show all lines
        print(f"# Lines added/modified in: {args.file_path}")
        print("# Format: LINE_NUMBER<tab>CONTENT")
        print()

        diff_lines = api.extract_line_numbers(args.file_path)
        for dl in diff_lines:
            print(f"{dl.file_line}\t{dl.content}")
        return 0

    elif args.validate:
        # Validate mode - check comments JSON
        try:
            comments = load_comments_file(args.file_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        print("Validating comments against PR diff...")
        print()

        results = api.validate_comments(comments)
        errors = 0
        validated = 0

        for i, result in enumerate(results):
            file_path = result['file']
            line = result['line']

            if result['valid']:
                content = result.get('content', '')
                print(f"{GREEN}OK{NC}: {file_path}:{line} -> {content}")
                validated += 1
            else:
                reason = result.get('reason', 'Unknown')
                print(f"{YELLOW}WARN{NC}: {file_path}:{line} - {reason}")
                errors += 1

        print()
        print("\u2501" * 78)
        print(f"Validated: {validated}, Issues: {errors}")

        return 1 if errors > 0 else 0

    else:
        # Find mode - search for pattern
        if not args.pattern:
            print("Error: pattern is required in find mode", file=sys.stderr)
            return 1

        line_num = api.find_line_for_pattern(args.file_path, args.pattern)

        if line_num is None:
            print(f"Error: Pattern not found in diff for {args.file_path}: {args.pattern}", file=sys.stderr)
            return 1

        print(line_num)
        return 0


def cmd_info(args) -> int:
    """Handle 'info' subcommand - get PR/MR info."""
    try:
        api = GitReviewAPI.from_url(args.pr_url)
    except (ValueError, RuntimeError) as e:
        print(f"{RED}Error: {e}{NC}")
        return 1

    try:
        info = api.get_pr_info()
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            print(f"Title: {info.get('title', 'N/A')}")
            print(f"Base: {info.get('base_ref', 'N/A')}")
            print(f"Head SHA: {info.get('head_sha', 'N/A')}")
            if info.get('body'):
                print(f"\nDescription:\n{info.get('body', '')[:500]}")
    except Exception as e:
        print(f"{RED}Error: {e}{NC}")
        return 1

    return 0


def cmd_files(args) -> int:
    """Handle 'files' subcommand - list changed files."""
    try:
        api = GitReviewAPI.from_url(args.pr_url)
    except (ValueError, RuntimeError) as e:
        print(f"{RED}Error: {e}{NC}")
        return 1

    try:
        files = api.get_changed_files()

        # Filter by pattern if provided
        if args.filter:
            import fnmatch
            files = [f for f in files if fnmatch.fnmatch(f['path'], args.filter)]

        if args.json:
            print(json.dumps(files, indent=2))
        else:
            print(f"Changed files: {len(files)}")
            print()
            for f in files:
                status_char = {'added': 'A', 'modified': 'M', 'deleted': 'D'}.get(f['status'], '?')
                print(f"  {status_char} {f['path']} (+{f['additions']}/-{f['deletions']})")
    except Exception as e:
        print(f"{RED}Error: {e}{NC}")
        return 1

    return 0


def cmd_comments(args) -> int:
    """Handle 'comments' subcommand - list review comments."""
    try:
        api = GitReviewAPI.from_url(args.pr_url)
    except (ValueError, RuntimeError) as e:
        print(f"{RED}Error: {e}{NC}")
        return 1

    try:
        comments = api.get_review_comments(include_resolved=args.include_resolved)

        if args.json:
            print(json.dumps(comments, indent=2))
        else:
            if not comments:
                print("No unresolved review comments found.")
                return 0

            print(f"Review comments: {len(comments)}")
            print()
            for c in comments:
                location = f"{c['path']}:{c['line']}" if c['path'] and c['line'] else "(general)"
                resolved_marker = " [RESOLVED]" if c.get('resolved') else ""
                print(f"  @{c['author']} on {location}{resolved_marker}")
                # Truncate long comments
                body = c['body'][:200] + "..." if len(c['body']) > 200 else c['body']
                for line in body.split('\n')[:3]:
                    print(f"    > {line}")
                print()
    except Exception as e:
        print(f"{RED}Error: {e}{NC}")
        return 1

    return 0


def cmd_diff(args) -> int:
    """Handle 'diff' subcommand - get PR/MR diff."""
    try:
        api = GitReviewAPI.from_url(args.pr_url)
    except (ValueError, RuntimeError) as e:
        print(f"{RED}Error: {e}{NC}")
        return 1

    try:
        diff = api.get_diff()
        print(diff)
    except Exception as e:
        print(f"{RED}Error: {e}{NC}")
        return 1

    return 0


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Git Review API - Unified interface for GitHub PRs and GitLab MRs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get PR/MR info
  %(prog)s info https://github.com/owner/repo/pull/123
  %(prog)s info https://github.com/owner/repo/pull/123 --json

  # List changed files
  %(prog)s files https://github.com/owner/repo/pull/123
  %(prog)s files https://github.com/owner/repo/pull/123 --filter "*.adoc"
  %(prog)s files https://github.com/owner/repo/pull/123 --json

  # List review comments
  %(prog)s comments https://github.com/owner/repo/pull/123
  %(prog)s comments https://github.com/owner/repo/pull/123 --include-resolved
  %(prog)s comments https://github.com/owner/repo/pull/123 --json

  # Get diff
  %(prog)s diff https://github.com/owner/repo/pull/123

  # Post review comments
  %(prog)s post https://github.com/owner/repo/pull/123 comments.json
  %(prog)s post https://github.com/owner/repo/pull/123 comments.json --dry-run

  # Extract line numbers
  %(prog)s extract https://github.com/owner/repo/pull/123 path/to/file.adoc "pattern"
  %(prog)s extract --dump https://github.com/owner/repo/pull/123 path/to/file.adoc
  %(prog)s extract --validate https://github.com/owner/repo/pull/123 comments.json
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Info subcommand
    info_parser = subparsers.add_parser(
        'info',
        help='Get PR/MR information (title, description, base branch)'
    )
    info_parser.add_argument('pr_url', help='GitHub PR or GitLab MR URL')
    info_parser.add_argument('--json', action='store_true',
                            help='Output as JSON')

    # Files subcommand
    files_parser = subparsers.add_parser(
        'files',
        help='List changed files in the PR/MR'
    )
    files_parser.add_argument('pr_url', help='GitHub PR or GitLab MR URL')
    files_parser.add_argument('--filter', metavar='PATTERN',
                             help='Filter files by glob pattern (e.g., "*.adoc")')
    files_parser.add_argument('--json', action='store_true',
                             help='Output as JSON')

    # Comments subcommand
    comments_parser = subparsers.add_parser(
        'comments',
        help='List review comments on the PR/MR'
    )
    comments_parser.add_argument('pr_url', help='GitHub PR or GitLab MR URL')
    comments_parser.add_argument('--include-resolved', action='store_true',
                                help='Include resolved comments')
    comments_parser.add_argument('--json', action='store_true',
                                help='Output as JSON')

    # Diff subcommand
    diff_parser = subparsers.add_parser(
        'diff',
        help='Get the unified diff for the PR/MR'
    )
    diff_parser.add_argument('pr_url', help='GitHub PR or GitLab MR URL')

    # Post subcommand
    post_parser = subparsers.add_parser(
        'post',
        help='Post review comments to a PR/MR'
    )
    post_parser.add_argument('pr_url', help='GitHub PR or GitLab MR URL')
    post_parser.add_argument('comments_file', help='Path to JSON file containing comments')
    post_parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be posted without actually posting')

    # Extract subcommand
    extract_parser = subparsers.add_parser(
        'extract',
        help='Extract line numbers from PR/MR diff'
    )
    extract_parser.add_argument('--dump', action='store_true',
                               help='Dump all added/modified lines with their file line numbers')
    extract_parser.add_argument('--validate', action='store_true',
                               help='Validate a comments JSON file against the actual diff')
    extract_parser.add_argument('pr_url', help='GitHub PR or GitLab MR URL')
    extract_parser.add_argument('file_path',
                               help='File path (for find/dump) or comments JSON file (for validate)')
    extract_parser.add_argument('pattern', nargs='?',
                               help='Pattern to search for (required in find mode)')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == 'info':
        sys.exit(cmd_info(args))
    elif args.command == 'files':
        sys.exit(cmd_files(args))
    elif args.command == 'comments':
        sys.exit(cmd_comments(args))
    elif args.command == 'diff':
        sys.exit(cmd_diff(args))
    elif args.command == 'post':
        sys.exit(cmd_post(args))
    elif args.command == 'extract':
        sys.exit(cmd_extract(args))


if __name__ == "__main__":
    main()
