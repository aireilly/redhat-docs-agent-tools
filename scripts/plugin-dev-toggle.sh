#!/usr/bin/env bash
# Toggle Claude Code plugins between production (cached) and local dev branch.
#
# Usage:
#   ./scripts/plugin-dev-toggle.sh dev     # Switch to local dev (current repo)
#   ./scripts/plugin-dev-toggle.sh prod    # Switch back to production
#   ./scripts/plugin-dev-toggle.sh status  # Show current state
#
# Works by replacing the marketplace clone with a symlink to this repo.
# Requires a new Claude Code session after switching.

set -euo pipefail

MARKETPLACE_NAME="redhat-docs-agent-tools"
MARKETPLACE_DIR="$HOME/.claude/plugins/marketplaces/$MARKETPLACE_NAME"
BACKUP_DIR="$HOME/.claude/plugins/marketplaces/$MARKETPLACE_NAME.prod-backup"

# Auto-detect repo root (directory containing .claude-plugin/marketplace.json)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$REPO_ROOT/.claude-plugin/marketplace.json" ]]; then
    echo "Error: Cannot find .claude-plugin/marketplace.json in $REPO_ROOT"
    exit 1
fi

usage() {
    echo "Usage: $(basename "$0") {dev|prod|status}"
    echo ""
    echo "  dev     Symlink plugins to local repo ($(basename "$REPO_ROOT"))"
    echo "  prod    Restore production plugins from git"
    echo "  status  Show current state"
    exit 1
}

show_status() {
    if [[ -L "$MARKETPLACE_DIR" ]]; then
        local target
        target="$(readlink "$MARKETPLACE_DIR")"
        echo "MODE: dev"
        echo "  Marketplace symlinked to: $target"
        echo "  Branch: $(git -C "$target" branch --show-current 2>/dev/null || echo 'unknown')"
    elif [[ -d "$MARKETPLACE_DIR" ]]; then
        echo "MODE: prod"
        echo "  Marketplace: $MARKETPLACE_DIR (git clone)"
        if [[ -d "$BACKUP_DIR" ]]; then
            echo "  Note: stale backup exists at $BACKUP_DIR"
        fi
    else
        echo "MODE: unknown"
        echo "  Marketplace directory not found at $MARKETPLACE_DIR"
    fi
}

switch_to_dev() {
    if [[ -L "$MARKETPLACE_DIR" ]]; then
        local current_target
        current_target="$(readlink "$MARKETPLACE_DIR")"
        if [[ "$current_target" == "$REPO_ROOT" ]]; then
            echo "Already in dev mode, pointing to $REPO_ROOT"
            exit 0
        fi
        echo "Removing existing symlink to $current_target"
        rm "$MARKETPLACE_DIR"
    elif [[ -d "$MARKETPLACE_DIR" ]]; then
        if [[ -d "$BACKUP_DIR" ]]; then
            echo "Error: Backup already exists at $BACKUP_DIR"
            echo "Run '$(basename "$0") prod' first to restore, or remove the backup manually."
            exit 1
        fi
        echo "Backing up production marketplace to $BACKUP_DIR"
        mv "$MARKETPLACE_DIR" "$BACKUP_DIR"
    fi

    echo "Symlinking $MARKETPLACE_DIR -> $REPO_ROOT"
    ln -s "$REPO_ROOT" "$MARKETPLACE_DIR"

    echo ""
    echo "Switched to dev mode."
    echo "  Repo:   $REPO_ROOT"
    echo "  Branch: $(git -C "$REPO_ROOT" branch --show-current)"
    echo ""
    echo "Start a new Claude Code session to pick up changes."
}

switch_to_prod() {
    if [[ -L "$MARKETPLACE_DIR" ]]; then
        echo "Removing dev symlink"
        rm "$MARKETPLACE_DIR"
    fi

    if [[ -d "$BACKUP_DIR" ]]; then
        echo "Restoring production marketplace from backup"
        mv "$BACKUP_DIR" "$MARKETPLACE_DIR"
        echo "Switched to prod mode."
    elif [[ -d "$MARKETPLACE_DIR" ]]; then
        echo "Already in prod mode."
    else
        echo "No backup found. Triggering a fresh clone by restarting Claude Code,"
        echo "or run: claude plugins update"
    fi

    echo ""
    echo "Start a new Claude Code session to pick up changes."
}

case "${1:-}" in
    dev)    switch_to_dev ;;
    prod)   switch_to_prod ;;
    status) show_status ;;
    *)      usage ;;
esac
