#!/bin/bash
# setup-hooks.sh
#
# Install the workflow completion Stop hook into .claude/settings.json.
# Safe to run multiple times — skips if already installed.

set -e

SETTINGS_FILE=".claude/settings.json"
HOOKS_SRC="${CLAUDE_PLUGIN_ROOT}/skills/docs-orchestrator/hooks"

# Copy hook script into the project
mkdir -p .claude/hooks
cp "$HOOKS_SRC/workflow-completion-check.sh" .claude/hooks/
chmod +x .claude/hooks/workflow-completion-check.sh

# Create settings file if missing
if [ ! -f "$SETTINGS_FILE" ]; then
  echo '{}' > "$SETTINGS_FILE"
fi

# Install Stop hook (skip if already present)
HAS_WORKFLOW_HOOK=$(jq '[(.hooks.Stop // []) | .[] | select(.command? | contains("workflow-completion-check"))] | length' "$SETTINGS_FILE" 2>/dev/null || echo 0)

if [ "$HAS_WORKFLOW_HOOK" -gt 0 ]; then
  echo "Workflow completion hook already installed."
else
  jq '.hooks.Stop = (.hooks.Stop // []) + [{
    "type": "command",
    "command": "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/workflow-completion-check.sh",
    "timeout": 10
  }]' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
  echo "Installed workflow completion Stop hook."
fi

echo ""
echo "Setup complete. Hook installed in $SETTINGS_FILE"
echo "Run /hooks in Claude Code to verify."
