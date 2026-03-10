# dita-tools

**Important:** Always run Claude Code from a terminal in the root of the documentation repository you are working on. The dita-tools command operates on the current working directory, reading local files, checking git branches, and writing output relative to the repo root.

## Prerequisites

- Configure the [Red Hat Docs Agent Tools marketplace](https://redhat-documentation.github.io/redhat-docs-agent-tools/install/)

- Install Ruby and required gems

    ```bash
    # RHEL/Fedora
    sudo dnf install ruby

    gem install asciidoctor
    ```

- [Install Vale CLI](https://vale.sh/docs/vale-cli/installation/)

    ```bash
    # Fedora/RHEL
    sudo dnf copr enable mczernek/vale && sudo dnf install vale
    
    # macOS
    brew install vale
    ```

- Install review mode dependencies (required for `--review`)

    ```bash
    sudo dnf install python3
    gem install asciidoctor-reducer
    python3 -m pip install html2text
    ```
