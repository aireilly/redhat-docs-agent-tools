# docs-tools

**Important:** Always run Claude Code from a terminal in the root of the documentation repository you are working on. The docs-tools commands and agents operate on the current working directory, they read local files, check git branches, and write output relative to the repo root.

## Prerequisites

- Configure the [Red Hat Docs Agent Tools marketplace](https://redhat-documentation.github.io/redhat-docs-agent-tools/install/)

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
    python3 -m pip install python-pptx install PyGithub python-gitlab jira pyyaml ratelimit requests beautifulsoup4 html2text
    ```

    The `python-pptx` package is only required for Google Slides conversion. Google Docs and Sheets conversion has no extra dependencies.

- Create an `~/.env` file with your tokens:

    ```bash
    JIRA_AUTH_TOKEN=your_jira_token
    JIRA_URL=https://issues.redhat.com          # optional: override default JIRA instance
    GITHUB_TOKEN=your_github_pat                # repo scope for private, public_repo for public
    GITLAB_TOKEN=your_gitlab_pat                # api scope
    ```
    
- Add the following to the end of your `~/.bashrc` (Linux default) or `~/.zshrc` (Apple OSX default):
    
    ```bash
    if [ -f ~/.env ]; then
        set -a
        source ~/.env
        set +a
    fi
    ```

    Restart your terminal and Claude Code for changes to take effect.

## Required related plugins

The `requirements-analyst` agent references skills from these companion plugins. Add the marketplace first, then install the plugins:

```bash
# Add the related marketplace
/plugin marketplace add https://gitlab.cee.redhat.com/aireilly/marketplace.git

# Install JIRA and Red Hat docs plugins
/plugin install docs-rh-plugins@redhat-docs-marketplace
/plugin install pr-plugins@redhat-docs-marketplace
```

| Plugin | Skills used |
|--------|-------------|
| pr-plugins | `jira-reader`, `git-pr-reader` |
| docs-rh-plugins | `article-extractor`, `redhat-docs-toc` |
