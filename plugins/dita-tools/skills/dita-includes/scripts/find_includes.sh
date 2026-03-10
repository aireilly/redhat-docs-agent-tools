#!/bin/bash
#
# find_includes.sh - Recursively find all AsciiDoc include directives
#
# Usage: find_includes.sh <file.adoc> [options]
#
# Options:
#   -a, --absolute    Output absolute paths (default)
#   -r, --relative    Output paths relative to input file directory
#   -e, --existing    Only output files that exist
#   -h, --help        Show this help message
#
# The script parses include:: directives and recursively traverses all
# child includes, outputting a sorted, deduplicated list of referenced files.
#

set -euo pipefail

# Colors for output (disabled when not running in an interactive terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Global variables
declare -A VISITED_FILES
ABSOLUTE_PATHS=true
EXISTING_ONLY=false

usage() {
    cat <<EOF
Usage: $(basename "$0") <file.adoc> [options]

Recursively find all AsciiDoc files referenced via include directives.

Options:
  -a, --absolute    Output absolute paths (default)
  -r, --relative    Output paths relative to input file directory
  -e, --existing    Only output files that exist
  -h, --help        Show this help message

Examples:
  $(basename "$0") master.adoc
  $(basename "$0") docs/assembly.adoc --relative
  $(basename "$0") guide.adoc --existing
EOF
    exit 0
}

error() {
    echo -e "${RED}Error:${NC} $1" >&2
    exit 1
}

warn() {
    echo -e "${YELLOW}Warning:${NC} $1" >&2
}

# Extract include paths from a file
# Handles: include::path/to/file.adoc[] and include::path/to/file.adoc[leveloffset=+1]
extract_includes() {
    local file="$1"
    local base_dir
    base_dir=$(dirname "$file")

    # Extract include directives, handling various formats:
    # - include::path/file.adoc[]
    # - include::path/file.adoc[opts]
    # - include::{attribute}/file.adoc[]
    grep -oE 'include::[^\[]+' "$file" 2>/dev/null | \
        sed 's/include:://' | \
        while read -r include_path; do
            # Skip paths with unresolved attributes (contain {})
            if [[ "$include_path" == *"{"* ]]; then
                warn "Skipping unresolved attribute: $include_path"
                continue
            fi

            # Resolve relative path from the including file's directory
            if [[ "$include_path" != /* ]]; then
                include_path="$base_dir/$include_path"
            fi

            # Normalize the path (resolve . and ..)
            include_path=$(realpath -m "$include_path" 2>/dev/null || echo "$include_path")

            echo "$include_path"
        done
}

# Recursively find all includes
find_includes_recursive() {
    local file="$1"

    # Normalize the file path
    file=$(realpath -m "$file" 2>/dev/null || echo "$file")

    # Skip if already visited (prevent infinite loops)
    if [[ -n "${VISITED_FILES[$file]:-}" ]]; then
        return
    fi
    VISITED_FILES[$file]=1

    # Check if file exists
    if [[ ! -f "$file" ]]; then
        if [[ "$EXISTING_ONLY" == "false" ]]; then
            echo "$file"
        fi
        return
    fi

    # Output this file
    echo "$file"

    # Find and process includes in this file
    while IFS= read -r include_path; do
        [[ -z "$include_path" ]] && continue
        find_includes_recursive "$include_path"
    done < <(extract_includes "$file")
}

# Parse arguments
INPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -a|--absolute)
            ABSOLUTE_PATHS=true
            shift
            ;;
        -r|--relative)
            ABSOLUTE_PATHS=false
            shift
            ;;
        -e|--existing)
            EXISTING_ONLY=true
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
                error "Multiple input files not supported"
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

# Get the absolute path of the input file for consistent processing
INPUT_FILE=$(realpath "$INPUT_FILE")
INPUT_DIR=$(dirname "$INPUT_FILE")

# Find all includes recursively
ALL_INCLUDES=$(find_includes_recursive "$INPUT_FILE" | sort -u)

# Output results
while IFS= read -r file; do
    [[ -z "$file" ]] && continue

    # Filter non-existing files if requested
    if [[ "$EXISTING_ONLY" == "true" && ! -f "$file" ]]; then
        continue
    fi

    # Convert to relative path if not using absolute
    if [[ "$ABSOLUTE_PATHS" == "false" ]]; then
        file=$(realpath --relative-to="$INPUT_DIR" "$file" 2>/dev/null || echo "$file")
    fi

    echo "$file"
done <<< "$ALL_INCLUDES"
