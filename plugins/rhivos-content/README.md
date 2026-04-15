# rhivos-content

RHIVOS 2.0 Core documentation pipeline. Converts upstream CentOS Automotive SIG Markdown content into downstream Red Hat modular AsciiDoc, restructured using Jobs To Be Done (JTBD) principles and validated against Red Hat style governance.

## Skills

| Skill | Purpose |
|-------|---------|
| `rhivos-map-upstream` | Parse Google Doc ToC, map topics to upstream sig-docs files |
| `rhivos-fetch-convert` | Fetch upstream Markdown, convert to AsciiDoc with modular docs conventions |
| `rhivos-jtbd-restructure` | Restructure converted content according to JTBD principles |
| `rhivos-quality-review` | Run style governance (Red Hat SSG, IBM SG, Vale, modular docs) |
| `rhivos-workflow` | Orchestrator that chains the above with interactive review gates |

## Prerequisites

- `docs-tools`, `dita-tools`, `vale-tools`, and `jtbd-tools` plugins installed
- `pandoc` installed (`sudo dnf install pandoc` or equivalent)
- `gcloud` CLI authenticated with `--enable-gdrive-access`
- `python3` available

## Usage

### Full workflow (recommended)

```
/rhivos-workflow "<google-doc-url>" --title "RHIVOS Image Building"
```

Runs all stages with interactive review gates between each.

### Individual skills

Each skill can be run independently:

```
/rhivos-map-upstream "<google-doc-url>" --title "Doc Title"
/rhivos-fetch-convert artifacts/<doc-title-slug>/upstream-mapping.yaml
/rhivos-jtbd-restructure <doc-title-slug>
/rhivos-quality-review <doc-title-slug>
```

## Artifacts

All intermediate and final outputs are stored under `artifacts/<doc-title-slug>/` in the current working directory. Add `artifacts/` to `.gitignore`.
