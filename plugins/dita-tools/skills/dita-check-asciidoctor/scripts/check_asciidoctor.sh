#!/bin/bash
#
# check_asciidoctor.sh - Run asciidoctor to check AsciiDoc files for errors
#
# Usage: check_asciidoctor.sh <file.adoc>
#
# The script runs asciidoctor on the input file, captures warnings and errors,
# saves them to a timestamped log in /tmp, and reports the results.
#
# Exit codes:
#   0 - No warnings or errors
#   1 - Warnings found (file may have issues)
#   2 - Errors found (file is broken)
#

set -uo pipefail

usage() {
    cat <<EOF
Usage: $(basename "$0") <file.adoc>

Run asciidoctor to check an AsciiDoc file for syntax errors and warnings.

The output is saved to a timestamped log file in /tmp.

Exit codes:
  0 - No warnings or errors
  1 - Warnings found
  2 - Errors found (file is broken)

Examples:
  $(basename "$0") master.adoc
  $(basename "$0") modules/con-overview.adoc
EOF
    exit 0
}

error() {
    echo "Error: $1" >&2
    exit 2
}

# Check if asciidoctor is installed
check_asciidoctor() {
    if ! command -v asciidoctor &> /dev/null; then
        error "asciidoctor is not installed. Install with: gem install asciidoctor"
    fi
}

# Parse arguments
if [[ $# -eq 0 ]]; then
    error "No input file specified. Use -h for help."
fi

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
fi

INPUT_FILE="$1"

# Validate input
if [[ ! -f "$INPUT_FILE" ]]; then
    error "File not found: $INPUT_FILE"
fi

# Check asciidoctor is available
check_asciidoctor

# Create timestamped output files
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BASENAME=$(basename "$INPUT_FILE" .adoc)
OUTPUT_HTML="/tmp/asciidoctor-check-${BASENAME}-${TIMESTAMP}.html"
OUTPUT_LOG="/tmp/asciidoctor-check-${BASENAME}-${TIMESTAMP}.log"

# Get absolute path for display
ABS_INPUT=$(realpath "$INPUT_FILE")

echo "Checking: $ABS_INPUT"
echo "HTML output: $OUTPUT_HTML"
echo "Log output: $OUTPUT_LOG"
echo ""

# Run asciidoctor with stderr redirected to log file
# -a source-highlighter=rouge: use rouge for syntax highlighting
# -a icons!: disable icons to avoid external dependencies
# -o: output HTML to timestamped file in /tmp
# -v: verbose mode
# --failure-level WARN: exit non-zero on warnings
# --trace: show backtrace on errors
asciidoctor "$INPUT_FILE" \
    -a source-highlighter=rouge \
    -a icons! \
    -o "$OUTPUT_HTML" \
    -v \
    --failure-level WARN \
    --trace 2>"$OUTPUT_LOG" || true

# Add header to log file
{
    echo "Asciidoctor Check Report"
    echo "========================"
    echo "File: $ABS_INPUT"
    echo "Date: $(date)"
    echo "HTML: $OUTPUT_HTML"
    echo ""
    cat "$OUTPUT_LOG"
} > "${OUTPUT_LOG}.tmp" && mv "${OUTPUT_LOG}.tmp" "$OUTPUT_LOG"

# Count errors and warnings from log
ERROR_COUNT=$(grep -ci "error" "$OUTPUT_LOG" || true)
WARNING_COUNT=$(grep -ci "warning" "$OUTPUT_LOG" || true)

# Report results
if [[ $ERROR_COUNT -gt 0 ]]; then
    echo "RESULT: BROKEN ($ERROR_COUNT errors, $WARNING_COUNT warnings)"
    echo ""
    echo "See log for details: $OUTPUT_LOG"
    echo ""
    cat "$OUTPUT_LOG"
    exit 2
elif [[ $WARNING_COUNT -gt 0 ]]; then
    echo "RESULT: OK with warnings ($WARNING_COUNT warnings)"
    echo ""
    echo "See log for details: $OUTPUT_LOG"
    echo ""
    cat "$OUTPUT_LOG"
    exit 1
else
    echo "RESULT: OK (no warnings or errors)"
    exit 0
fi
