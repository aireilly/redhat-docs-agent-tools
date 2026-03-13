#!/bin/bash
# xref-path-calculator.sh
#
# Calculates the correct xref climbing path adjustment when moving content
# from one AsciiDoc file to another at a different directory depth.
#
# Usage:
#   ./xref-path-calculator.sh <source-path> <destination-path>
#
# Examples:
#   ./xref-path-calculator.sh installing/installing_sno/master.adoc modules/about-installing-sno.adoc
#   ./xref-path-calculator.sh networking/ovn_kubernetes/master.adoc modules/configuring-ovn.adoc

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

usage() {
    echo "Usage: $0 <source-path> <destination-path>"
    echo
    echo "Calculates xref climbing path adjustments when moving content"
    echo "from a source file to a destination file at a different directory depth."
    echo
    echo "Arguments:"
    echo "  source-path       Relative path to the file content is moving FROM"
    echo "  destination-path  Relative path to the file content is moving TO"
    echo
    echo "Examples:"
    echo "  $0 installing/installing_sno/master.adoc modules/about-installing-sno.adoc"
    echo "  $0 networking/ovn_kubernetes/master.adoc modules/configuring-ovn.adoc"
    exit 1
}

if [[ $# -ne 2 ]]; then
    usage
fi

SOURCE_PATH="$1"
DEST_PATH="$2"

# --------------------------------------------------------------------------
# Calculate directory depth (number of directory components above the file)
# e.g. "installing/installing_sno/master.adoc" -> depth 2
#      "modules/about-installing-sno.adoc"     -> depth 1
# --------------------------------------------------------------------------
get_dir_depth() {
    local filepath="$1"
    local dir
    dir=$(dirname "$filepath")
    if [[ "$dir" == "." ]]; then
        echo 0
    else
        echo "$dir" | tr '/' '\n' | wc -l | tr -d ' '
    fi
}

SOURCE_DEPTH=$(get_dir_depth "$SOURCE_PATH")
DEST_DEPTH=$(get_dir_depth "$DEST_PATH")
DEPTH_DIFF=$((SOURCE_DEPTH - DEST_DEPTH))

echo -e "${BOLD}=== xref Path Calculator ===${RESET}"
echo
echo -e "${CYAN}Source file:${RESET}       $SOURCE_PATH"
echo -e "  Directory:       $(dirname "$SOURCE_PATH")"
echo -e "  Depth:           $SOURCE_DEPTH"
echo
echo -e "${CYAN}Destination file:${RESET} $DEST_PATH"
echo -e "  Directory:       $(dirname "$DEST_PATH")"
echo -e "  Depth:           $DEST_DEPTH"
echo
echo -e "${CYAN}Depth difference:${RESET}  $DEPTH_DIFF (source depth $SOURCE_DEPTH - destination depth $DEST_DEPTH)"
echo

# --------------------------------------------------------------------------
# Explain the adjustment
# --------------------------------------------------------------------------
if [[ $DEPTH_DIFF -gt 0 ]]; then
    echo -e "${YELLOW}Destination is shallower than source by $DEPTH_DIFF level(s).${RESET}"
    echo -e "Each xref climbing path needs ${RED}$DEPTH_DIFF fewer${RESET} '../' segments."
elif [[ $DEPTH_DIFF -lt 0 ]]; then
    ABS_DIFF=$(( -DEPTH_DIFF ))
    echo -e "${YELLOW}Destination is deeper than source by $ABS_DIFF level(s).${RESET}"
    echo -e "Each xref climbing path needs ${RED}$ABS_DIFF more${RESET} '../' segments."
else
    echo -e "${GREEN}Both files are at the same depth. No xref adjustment needed.${RESET}"
fi

# --------------------------------------------------------------------------
# If the source file exists, find xrefs and show before/after
# --------------------------------------------------------------------------
if [[ -f "$SOURCE_PATH" ]]; then
    echo
    echo -e "${BOLD}--- xrefs found in source file ---${RESET}"
    echo

    XREFS=$(grep -noP 'xref:(\.\./)+(.*?)\[' "$SOURCE_PATH" 2>/dev/null || true)

    if [[ -z "$XREFS" ]]; then
        echo -e "${GREEN}No relative xref paths found in $SOURCE_PATH${RESET}"
    else
        while IFS= read -r match; do
            LINE_NUM=$(echo "$match" | cut -d: -f1)
            XREF_FULL=$(echo "$match" | cut -d: -f2-)
            # Strip the 'xref:' prefix so we work with just the path
            XREF_FULL="${XREF_FULL#xref:}"

            # Count current ../ segments
            CURRENT_CLIMBS=$(echo "$XREF_FULL" | grep -oP '\.\.\/' | wc -l | tr -d ' ')

            # Calculate new climb count
            NEW_CLIMBS=$((CURRENT_CLIMBS - DEPTH_DIFF))

            # Build the non-climbing suffix (everything after the last ../)
            SUFFIX=$(echo "$XREF_FULL" | sed 's|\(\.\./\)*||')

            # Build old and new paths
            OLD_PREFIX=$(printf '../%.0s' $(seq 1 "$CURRENT_CLIMBS"))
            if [[ $NEW_CLIMBS -gt 0 ]]; then
                NEW_PREFIX=$(printf '../%.0s' $(seq 1 "$NEW_CLIMBS"))
            else
                NEW_PREFIX=""
            fi

            echo -e "  Line $LINE_NUM:"
            echo -e "    ${RED}Source (original):${RESET}      xref:${OLD_PREFIX}${SUFFIX}"
            if [[ $NEW_CLIMBS -lt 0 ]]; then
                echo -e "    ${RED}Destination (adjusted): ERROR - path would need negative climbs ($NEW_CLIMBS)${RESET}"
                echo -e "    ${YELLOW}This xref may not be valid even in the source file.${RESET}"
            elif [[ $NEW_CLIMBS -eq 0 ]]; then
                echo -e "    ${GREEN}Destination (adjusted):${RESET} xref:${SUFFIX}"
                echo -e "    ${YELLOW}(all climbing removed - target is at same level or below)${RESET}"
            else
                echo -e "    ${GREEN}Destination (adjusted):${RESET} xref:${NEW_PREFIX}${SUFFIX}"
            fi
            echo
        done <<< "$XREFS"
    fi
else
    echo
    echo -e "${YELLOW}Source file '$SOURCE_PATH' not found - skipping xref scan.${RESET}"
    echo "Showing formula only."
fi

# --------------------------------------------------------------------------
# Verification formula
# --------------------------------------------------------------------------
echo -e "${BOLD}--- Verification formula ---${RESET}"
echo
echo "  Given an xref with N '../' segments in the source file:"
echo "    new_climb_count = N - ($SOURCE_DEPTH - $DEST_DEPTH) = N - $DEPTH_DIFF"
echo
echo "  Example: if source has xref:../../foo/bar.adoc[]"
EXAMPLE_OLD=2
EXAMPLE_NEW=$((EXAMPLE_OLD - DEPTH_DIFF))
echo "    N = $EXAMPLE_OLD"
echo "    new_climb_count = $EXAMPLE_OLD - $DEPTH_DIFF = $EXAMPLE_NEW"
if [[ $EXAMPLE_NEW -gt 0 ]]; then
    EXAMPLE_PREFIX=$(printf '../%.0s' $(seq 1 "$EXAMPLE_NEW"))
    echo "    Result: xref:${EXAMPLE_PREFIX}foo/bar.adoc[]"
elif [[ $EXAMPLE_NEW -eq 0 ]]; then
    echo "    Result: xref:foo/bar.adoc[]"
else
    echo "    Result: ERROR (negative climb - check your paths)"
fi
