# cqa-tools

Assess, fix, and score Red Hat modular documentation against all 54 CQA 2.1 parameters.

!!! tip

    Always run Claude Code from a terminal in the root of the documentation repository you are working on. The CQA tools command and skills operate on the current working directory, reading local `.adoc` files and writing output relative to the repo root.

## Prerequisites

- Install the [Red Hat Docs Agent Tools marketplace](https://redhat-documentation.github.io/redhat-docs-agent-tools/install/)

- Install system dependencies

    ```bash
    # RHEL/Fedora
    sudo dnf install python3
    ```

    Python 3.9+ is required. Scripts use only the standard library — no `pip install` needed.

- [Install Vale CLI](https://vale.sh/docs/vale-cli/installation/) (required for P1: Vale DITA linting)

    ```bash
    # Fedora/RHEL
    sudo dnf copr enable mczernek/vale && sudo dnf install vale

    # macOS
    brew install vale
    ```

## Usage

```bash
# Full assessment
/cqa-tools:cqa-assess /path/to/docs-repo

# Assess and fix
/cqa-tools:cqa-assess /path/to/docs-repo --mode fix

# Assess one assembly and its topics
/cqa-tools:cqa-assess /path/to/docs-repo --scope assembly
```

## References

- [`reference/scoring-guide.md`](reference/scoring-guide.md) — Scoring rules and parameter-to-skill mapping
- [`reference/checklist.md`](reference/checklist.md) — Full 54-parameter CQA 2.1 checklist
- [Red Hat modular docs guide](https://redhat-documentation.github.io/modular-docs/)
- [DITA 1.3 spec](https://docs.oasis-open.org/dita/dita/v1.3/dita-v1.3-part3-all-inclusive.html)
