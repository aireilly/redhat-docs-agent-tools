---
name: docs-convert-gdoc-md
description: Read a Google Docs (gdoc) document or Google Slides presentation and output it as Markdown or plain text. Use this skill when asked to read, fetch, import, or convert a Google Doc or Google Slides URL.
model: claude-haiku-4-5@20251001
allowed-tools: Bash, Read, Write
---

# Convert Google Docs or Slides to Markdown

Export a Google Doc to Markdown or a Google Slides presentation to plain text using the `gcloud` CLI for authentication.

## Prerequisites

- `gcloud` CLI must be installed
- User must be authenticated via `gcloud auth login --enable-gdrive-access`

## Instructions

1. The user provides a Google Docs or Google Slides URL.
2. Run the conversion script with the URL as the argument.
3. Read the output file and present the content to the user.

### Run the script

The script is at `plugins/docs-tools/skills/docs-convert-gdoc-md/scripts/gdoc2md.py`.

```bash
python3 plugins/docs-tools/skills/docs-convert-gdoc-md/scripts/gdoc2md.py <url> [output_file]
```

- The script auto-detects whether the URL is a Doc (`/document/d/`) or Slides (`/presentation/d/`).
- If no output file is specified, it defaults to `<id>.md` for Docs or `<id>.txt` for Slides.

### Error handling

- **401**: Authentication expired. Tell the user to run `gcloud auth login --enable-gdrive-access`.
- **403**: No permission. The user needs access to the document.
- **404**: Wrong URL or the document doesn't exist.
