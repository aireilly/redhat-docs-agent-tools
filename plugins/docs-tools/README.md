# docs-tools

**Important:** Always run Claude Code from a terminal in the root of the documentation repository you are working on. The docs-tools commands and agents operate on the current working directory, they read local files, check git branches, and write output relative to the repo root.

## Prerequisites

- Configure the [Red Hat Docs Agent Tools marketplace](https://redhat-documentation.github.io/redhat-docs-agent-tools/install/)

- [Install GitHub CLI (`gh`)](https://cli.github.com/)

    ```bash
    gh auth login
    ```

- [Install gcloud CLI](https://cloud.google.com/sdk/docs/install)

    ```bash
    gcloud auth login --enable-gdrive-access
    ```

- Install Python packages

    ```bash
    python3 -m pip install python-pptx
    ```

    The `python-pptx` package is only required for Google Slides conversion. Google Docs and Sheets conversion has no extra dependencies.
