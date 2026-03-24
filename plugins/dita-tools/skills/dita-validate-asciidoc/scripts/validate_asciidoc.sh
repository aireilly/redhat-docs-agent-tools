#!/bin/bash
#
# validate_asciidoc.sh - Run Vale AsciiDocDITA checks on AsciiDoc files
#
# Usage: validate_asciidoc.sh <file.adoc> [options]
#
# Options:
#   -l, --list-only   Only list files, don't run Vale
#   -h, --help        Show this help message
#
# The script discovers included files using dita-includes, runs vale sync,
# then runs Vale with AsciiDocDITA rules only.
#
# Output format (one issue per line):
#   file:line:column:severity:rule:message
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DITA_INCLUDES_SCRIPT="$SCRIPT_DIR/../../dita-includes/scripts/find_includes.sh"

LIST_ONLY=false

usage() {
    cat <<EOF
Usage: $(basename "$0") <file.adoc> [options]

Run Vale AsciiDocDITA checks on an AsciiDoc assembly and all included files.

Options:
  -l, --list-only   Only list files, don't run Vale
  -h, --help        Show this help message

Output format (one issue per line):
  file:line:column:severity:rule:message

Examples:
  $(basename "$0") assemblies/master.adoc
  $(basename "$0") guide.adoc --existing
  $(basename "$0") guide.adoc --list-only
EOF
    exit 0
}

error() {
    echo "Error: $1" >&2
    exit 1
}

# Check if Vale is installed
check_vale() {
    if ! command -v vale &> /dev/null; then
        error "Vale is not installed. See: https://vale.sh/docs/vale-cli/installation/"
    fi
}

# Create temporary Vale config for AsciiDocDITA only
# Args: $1 = config file path, $2 = "no-short-desc" (optional) to disable ShortDescription
create_temp_vale_config() {
    local temp_config="$1"
    local no_short_desc="${2:-}"

    cat > "$temp_config" <<'EOF'
StylesPath = .vale/styles

MinAlertLevel = warning

Packages = https://github.com/jhradilek/asciidoctor-dita-vale/releases/latest/download/AsciiDocDITA.zip

[*.adoc]
BasedOnStyles = AsciiDocDITA
EOF

    # Disable ShortDescription check for ASSEMBLY and SNIPPET types
    if [[ "$no_short_desc" == "no-short-desc" ]]; then
        echo "AsciiDocDITA.ShortDescription = NO" >> "$temp_config"
    fi
}

# Get content type from AsciiDoc file
# Returns: CONCEPT, PROCEDURE, REFERENCE, ASSEMBLY, SNIPPET, or empty
get_content_type() {
    local file="$1"
    grep -oP '(?<=:_mod-docs-content-type:\s).*' "$file" 2>/dev/null | head -1 | tr -d '[:space:]' || true
}

# Parse arguments
INPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -l|--list-only)
            LIST_ONLY=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        -*)
            error "Unknown option: $1"
            ;;
        *)
            if [[ -z "$INPUT_FILE" ]]; then
                INPUT_FILE="$1"
            else
                error "Multiple input files not supported. Use an assembly file."
            fi
            shift
            ;;
    esac
done

# Validate input
if [[ -z "$INPUT_FILE" ]]; then
    error "No input file specified. Use -h for help."
fi

if [[ ! -f "$INPUT_FILE" ]]; then
    error "File not found: $INPUT_FILE"
fi

# Check dita-includes script exists
if [[ ! -f "$DITA_INCLUDES_SCRIPT" ]]; then
    error "dita-includes script not found: $DITA_INCLUDES_SCRIPT"
fi

# Get list of files using dita-includes (only existing files)
FILES=$(bash "$DITA_INCLUDES_SCRIPT" "$INPUT_FILE" --existing)

# List-only mode
if [[ "$LIST_ONLY" == "true" ]]; then
    echo "$FILES"
    exit 0
fi

# Check Vale is available
check_vale

# Create temporary config directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf '$TEMP_DIR'" EXIT

# Create two Vale configs: standard and no-short-desc (for ASSEMBLY/SNIPPET)
create_temp_vale_config "$TEMP_DIR/.vale.ini" ""
create_temp_vale_config "$TEMP_DIR/.vale-no-short-desc.ini" "no-short-desc"

# Run vale sync in the temp directory to download AsciiDocDITA
cd "$TEMP_DIR"
vale sync >/dev/null 2>&1 || true
cd - >/dev/null

# Categorize files by content type
STANDARD_FILES=""
NO_SHORT_DESC_FILES=""

while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    content_type=$(get_content_type "$file")
    if [[ "$content_type" == "ASSEMBLY" || "$content_type" == "SNIPPET" ]]; then
        NO_SHORT_DESC_FILES+="$file"$'\n'
    else
        STANDARD_FILES+="$file"$'\n'
    fi
done <<< "$FILES"

# Run Vale on standard files (full rules)
# Output format: file:line:column:severity:rule:message
if [[ -n "$STANDARD_FILES" ]]; then
    echo -n "$STANDARD_FILES" | tr '\n' '\0' | xargs -0 vale --config="$TEMP_DIR/.vale.ini" --output=line 2>/dev/null || true
fi

# Run Vale on ASSEMBLY/SNIPPET files (ShortDescription disabled)
if [[ -n "$NO_SHORT_DESC_FILES" ]]; then
    echo -n "$NO_SHORT_DESC_FILES" | tr '\n' '\0' | xargs -0 vale --config="$TEMP_DIR/.vale-no-short-desc.ini" --output=line 2>/dev/null || true
fi
