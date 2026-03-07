"""
Export a Google Doc to Markdown, or Slides to plain text.

Requires gcloud CLI

python gdoc2md.py <google-doc-or-slides-url> [output]
"""

import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def check_dependencies():
    result = subprocess.run(
        ["gcloud", "version"], capture_output=True,
    )
    if result.returncode != 0:
        print("Error: gcloud CLI is not installed.", file=sys.stderr)
        install = "https://cloud.google.com/sdk/docs/install"
        print(f"  Install: {install}", file=sys.stderr)
        sys.exit(1)


def parse_args():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <google-doc-or-slides-url> [output]")
        sys.exit(1)

    url = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else ""
    mode = "slides" if "/presentation/d/" in url else "doc"
    return url, output, mode


def extract_id(url, output, mode):
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        print(f"Error: Could not extract ID from URL: {url}", file=sys.stderr)
        sys.exit(1)

    file_id = match.group(1)
    if not output:
        output = f"{file_id}.txt" if mode == "slides" else f"{file_id}.md"

    return file_id, output


def authenticate():
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return
    print("Authenticating with Google...")
    subprocess.run(
        ["gcloud", "auth", "login", "--enable-gdrive-access"],
        check=True,
    )


def fetch(file_id, output, mode):
    token = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    base = "https://docs.google.com"
    if mode == "slides":
        export_url = f"{base}/presentation/d/{file_id}/export?format=txt"
    else:
        export_url = f"{base}/document/d/{file_id}/export?format=md"

    req = Request(
        export_url,
        headers={"Authorization": f"Bearer {token}"},
    )
    output_path = Path(output)

    try:
        with urlopen(req) as resp:
            output_path.write_bytes(resp.read())
        print(f"Saved to {output}")
    except HTTPError as e:
        output_path.unlink(missing_ok=True)
        messages = {
            401: "Authentication failed (401). "
                 "Try: gcloud auth login "
                 "--enable-gdrive-access",
            403: "Access denied (403). "
                 "Check you have permission.",
            404: "Not found (404). "
                 "Check the URL is correct.",
        }
        msg = messages.get(e.code, f"HTTP {e.code}")
        print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)


def main():
    url, output, mode = parse_args()
    check_dependencies()
    file_id, output = extract_id(url, output, mode)
    authenticate()
    fetch(file_id, output, mode)


if __name__ == "__main__":
    main()
