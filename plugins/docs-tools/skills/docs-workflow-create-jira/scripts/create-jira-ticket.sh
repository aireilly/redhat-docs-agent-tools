#!/bin/bash
# create-jira-ticket.sh
#
# Create a linked JIRA documentation ticket from a planning output file.
#
# Usage: create-jira-ticket.sh <TICKET> <PROJECT> <PLAN_FILE>
# Requires: curl, jq, python3
# Environment: JIRA_AUTH_TOKEN, JIRA_EMAIL

set -euo pipefail

TICKET="${1:?Usage: create-jira-ticket.sh <TICKET> <PROJECT> <PLAN_FILE>}"
PROJECT="${2:?Missing PROJECT argument}"
PLAN_FILE="${3:?Missing PLAN_FILE argument}"

JIRA_URL="https://redhat.atlassian.net"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ -z "${JIRA_AUTH_TOKEN:-}" || -z "${JIRA_EMAIL:-}" ]]; then
    echo "Error: JIRA_AUTH_TOKEN and JIRA_EMAIL must be set" >&2
    exit 1
fi

if [[ ! -f "$PLAN_FILE" ]]; then
    echo "Error: Plan file not found: $PLAN_FILE" >&2
    exit 1
fi

# --- Check for existing Document link ---
LINKS_JSON=$(curl -s \
  -u "${JIRA_EMAIL}:${JIRA_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  "${JIRA_URL}/rest/api/2/issue/${TICKET}?fields=issuelinks")

HAS_DOC_LINK=$(echo "$LINKS_JSON" | jq -r '
  .fields.issuelinks[]? |
  select(.type.name == "Document" and .inwardIssue != null) |
  .type.name' | head -1)

if [[ -n "$HAS_DOC_LINK" ]]; then
    LINKED_KEY=$(echo "$LINKS_JSON" | jq -r '
      .fields.issuelinks[] |
      select(.type.name == "Document" and .inwardIssue != null) |
      .inwardIssue.key' | head -1)
    echo "A documentation ticket (${LINKED_KEY}) already exists for ${TICKET}."
    echo "Skipping JIRA creation."
    exit 0
fi

# --- Check if project is public or private ---
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Content-Type: application/json" \
  "${JIRA_URL}/rest/api/2/project/${PROJECT}")

if [[ "$HTTP_STATUS" == "200" ]]; then
    PROJECT_IS_PUBLIC=true
else
    PROJECT_IS_PUBLIC=false
fi

# --- Extract description from plan ---
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

VISIBILITY="private"
if [[ "$PROJECT_IS_PUBLIC" == "true" ]]; then
    VISIBILITY="public"
fi

python3 "${SCRIPT_DIR}/extract-description.py" \
  "$PLAN_FILE" \
  "$TMPDIR/jira_description_raw.txt" \
  "$VISIBILITY"

# --- Convert markdown to JIRA wiki markup ---
python3 "${SCRIPT_DIR}/md2wiki.py" \
  "$TMPDIR/jira_description_raw.txt" \
  "$TMPDIR/jira_description_wiki.txt"

# --- Create the JIRA ticket ---
PARENT_SUMMARY=$(curl -s \
  -u "${JIRA_EMAIL}:${JIRA_AUTH_TOKEN}" \
  "${JIRA_URL}/rest/api/2/issue/${TICKET}?fields=summary" | jq -r '.fields.summary')

python3 "${SCRIPT_DIR}/build-payload.py" \
  "$TMPDIR/jira_description_wiki.txt" \
  "$TMPDIR/jira_create_payload.json" \
  "$PROJECT" \
  "$PARENT_SUMMARY"

RESPONSE=$(curl -s -X POST \
  -u "${JIRA_EMAIL}:${JIRA_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  --data @"${TMPDIR}/jira_create_payload.json" \
  "${JIRA_URL}/rest/api/2/issue")

NEW_ISSUE_KEY=$(echo "$RESPONSE" | jq -r '.key')

if [[ -z "$NEW_ISSUE_KEY" || "$NEW_ISSUE_KEY" == "null" ]]; then
    echo "Error: Failed to create JIRA ticket" >&2
    echo "$RESPONSE" >&2
    exit 1
fi

# --- Link new ticket to parent (link type is "Document", not "Documents") ---
curl -s -X POST \
  -u "${JIRA_EMAIL}:${JIRA_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "{
    \"type\": { \"name\": \"Document\" },
    \"outwardIssue\": { \"key\": \"${TICKET}\" },
    \"inwardIssue\": { \"key\": \"${NEW_ISSUE_KEY}\" }
  }" \
  "${JIRA_URL}/rest/api/2/issueLink"

# --- Attach plan file (private projects only) ---
if [[ "$PROJECT_IS_PUBLIC" != "true" ]]; then
    curl -s -X POST \
      -u "${JIRA_EMAIL}:${JIRA_AUTH_TOKEN}" \
      -H "X-Atlassian-Token: no-check" \
      -F "file=@${PLAN_FILE}" \
      "${JIRA_URL}/rest/api/2/issue/${NEW_ISSUE_KEY}/attachments"
fi

# --- Print the new ticket URL ---
echo "${JIRA_URL}/browse/${NEW_ISSUE_KEY}"
