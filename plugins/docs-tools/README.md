# docs-tools

!!! tip

    Always run Claude Code from a terminal in the root of the documentation repository you are working on. The docs-tools commands and agents operate on the current working directory, they read local files, check git branches, and write output relative to the repo root.

## Prerequisites

- Install the [Red Hat Docs Agent Tools marketplace](https://redhat-documentation.github.io/redhat-docs-agent-tools/install/)

- [Install GitHub CLI (`gh`)](https://cli.github.com/)

    ```bash
    gh auth login
    ```

- Install system dependencies

    ```bash
    # RHEL/Fedora
    sudo dnf install python3 jq curl
    ```

- [Install gcloud CLI](https://cloud.google.com/sdk/docs/install)

    ```bash
    gcloud auth login --enable-gdrive-access
    ```

- Install Python packages

    ```bash
    python3 -m pip install python-pptx PyGithub python-gitlab jira pyyaml ratelimit requests beautifulsoup4 html2text pip-system-certs
    ```

    The `python-pptx` package is only required for Google Slides conversion. Google Docs and Sheets conversion has no extra dependencies.

- Create an `~/.env` file with your tokens:

    ```bash
    JIRA_AUTH_TOKEN=your_jira_api_token
    # Required for Atlassian Cloud authentication
    JIRA_EMAIL=you@redhat.com
    # Optional: defaults to https://redhat.atlassian.net if not set
    JIRA_URL=https://redhat.atlassian.net
    # Required scopes: "repo" for private repos, "public_repo" for public repos
    GITHUB_TOKEN=your_github_pat
    # Required scope: "api"
    GITLAB_TOKEN=your_gitlab_pat
    ```
    
- Add the following to the end of your `~/.bashrc` (Linux) or `~/.zshrc` (macOS):
    
    ```bash
    if [ -f ~/.env ]; then
        set -a
        source ~/.env
        set +a
    fi
    ```

    Restart your terminal and Claude Code for changes to take effect.

