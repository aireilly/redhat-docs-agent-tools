---
name: jtbd-harvest
description: Harvest technical documentation from a URL using the existing CLI. Wraps the jtbd harvest command which handles async crawling, content extraction, and markdown conversion.
argument-hint: [landing-url] --project [name]
allowed-tools: Bash, Read, Glob
---

# Harvest Documentation

Download and convert technical documentation from a URL to local markdown files for JTBD analysis.

## Usage

```bash
/jtbd-harvest https://docs.example.com/guide --project myproject
```

## Arguments

- **URL** (required): The landing page URL to harvest from
- **--project** (required): Project name for organizing output files

## What This Skill Does

1. **Parses the URL and project name** from `$ARGUMENTS`
2. **Executes the CLI harvest command**: `jtbd harvest "$URL" --name "$PROJECT"`
3. **Reports progress** as pages are downloaded
4. **Lists created files** in `docs_raw/<project>/`
5. **Suggests next step**: `/jtbd-analyze docs_raw/<project>/<doc>.md`

## Execution Steps

### Step 1: Parse Arguments

Extract the URL and project name from the arguments:
- URL is the first positional argument
- Project name follows `--project` or `--name` flag

### Step 2: Run Harvest Command

Execute via Bash:

```bash
jtbd harvest "$URL" --name "$PROJECT"
```

Monitor the output for:
- Progress indicators (pages fetched)
- Any errors or warnings
- Completion summary

### Step 3: Verify Results

After completion:
1. List files in `docs_raw/<project>/`
2. Report count of harvested documents
3. Show sample filenames

### Step 4: Suggest Next Steps

Provide guidance on continuing the workflow:

```
Harvested X documents to docs_raw/<project>/

Next steps:
1. Analyze a document: /jtbd-analyze docs_raw/<project>/<doc>.md
2. Analyze all documents: Run /jtbd-analyze for each file
```

## Output Location

Files are saved to:
```
docs_raw/<project>/
├── <doc1>.md
├── <doc2>.md
└── ...
```

Each markdown file includes:
- YAML frontmatter with source URL and title
- Cleaned content (navigation, footers removed)
- Preserved heading structure

## Requirements

- `jtbd` CLI must be installed: `pip install -e .`
- No `ANTHROPIC_API_KEY` required (harvest doesn't use LLM)
- Network access to target documentation

## Error Handling

If the harvest command fails:
1. Check if the URL is accessible
2. Verify the project name is valid (no special characters)
3. Ensure network connectivity
4. Check if the CLI is installed: `pip install -e .`

## Examples

### Harvest Red Hat OpenShift AI docs

```bash
/jtbd-harvest https://docs.redhat.com/en/documentation/red_hat_openshift_ai/latest --project rhoai
```

### Harvest a single guide

```bash
/jtbd-harvest https://docs.example.com/guide/single-page.html --project myguide
```

### After harvesting

```bash
# List harvested files
ls docs_raw/<project>/

# Start analysis
/jtbd-analyze docs_raw/<project>/<doc>.md
```
