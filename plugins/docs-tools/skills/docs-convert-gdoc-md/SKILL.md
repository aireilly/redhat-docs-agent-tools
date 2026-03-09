---
name: docs-convert-gdoc-md
description: Read a Google Docs document, Google Slides presentation, or Google Sheets spreadsheet and output as Markdown, structured Markdown, or CSV. Use this skill when asked to read, fetch, import, or convert a Google Doc, Google Slides, or Google Sheets URL.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Read, Write
---

# Convert Google Docs, Slides, or Sheets

Export Google content using the `gcloud` CLI for authentication:

- **Google Docs** → Markdown (`.md`)
- **Google Slides** → Structured Markdown (`.md`) via PPTX with slide titles, bullet points, tables, and speaker notes
- **Google Sheets** → CSV (`.csv`)

## Prerequisites

- `gcloud` CLI must be installed
- User must be authenticated via `gcloud auth login --enable-gdrive-access`
- `python-pptx` must be installed for Slides export (`pip install python-pptx`)

## Instructions

1. The user provides a Google Docs, Slides, or Sheets URL.
2. Run the conversion script with the URL as the argument.
3. Read the output file and present the content to the user.

### Run the script

The script is at `plugins/docs-tools/skills/docs-convert-gdoc-md/scripts/gdoc2md.py`.

```bash
python3 plugins/docs-tools/skills/docs-convert-gdoc-md/scripts/gdoc2md.py <url> [output_file]
```

- The script auto-detects the URL type:
  - `/document/d/` → Google Docs → Markdown
  - `/presentation/d/` → Google Slides → Markdown (via PPTX)
  - `/spreadsheets/d/` → Google Sheets → CSV
- If no output file is specified, it defaults to `<id>.md` or `<id>.csv`.

### Error handling

- **401**: Authentication expired. Tell the user to run `gcloud auth login --enable-gdrive-access`.
- **403**: No permission. The user needs access to the document.
- **404**: Wrong URL or the document doesn't exist.
- **ImportError**: `python-pptx` not installed. Tell the user to run `pip install python-pptx`.
