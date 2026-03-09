# docs-tools

Documentation tools for converting and working with Google Docs, Slides, and Sheets.

## Skills

### docs-convert-gdoc-md

Export Google content using the `gcloud` CLI for authentication:

- **Google Docs** → Markdown (`.md`)
- **Google Slides** → Structured Markdown (`.md`) via PPTX with slide titles, bullet points, tables, and speaker notes
- **Google Sheets** → CSV (`.csv`)

## Prerequisites

### System dependencies

```bash
# Install gcloud CLI: https://cloud.google.com/sdk/docs/install
gcloud auth login --enable-gdrive-access
```

### Python packages

```bash
pip install python-pptx
```

The `python-pptx` package is only required for Google Slides conversion. Google Docs and Sheets conversion has no extra dependencies.
