#!/usr/bin/env bash
set -euo pipefail

MARKETPLACE_DIR="$HOME/.claude/plugins/marketplaces/redhat-docs-agent-tools"
CACHE_DIR="$HOME/.claude/plugins/cache/redhat-docs-agent-tools"
INSTALLED_PLUGINS="$HOME/.claude/plugins/installed_plugins.json"
MARKETPLACE_NAME="redhat-docs-agent-tools"

usage() {
    echo "Usage: $(basename "$0") [--branch <branch>] [--plugin <plugin>] [--reset]"
    echo "For example:"
    echo "scripts/test-upstream-plugin.sh"
    echo "scripts/test-upstream-plugin.sh --branch feat/fanout-subagents-per-requirement"
    echo
    echo "Checkout an upstream branch and clear the plugin cache."
    echo
    echo "Options:"
    echo "  --branch <branch>   Remote branch to fetch and checkout (default: current branch)"
    echo "  --plugin <plugin>   Plugin name whose cache to delete (default: docs-tools)"
    echo "  --reset             Reset the marketplace repo to upstream main and clear"
    echo "                      the plugin cache. Requires --plugin; --branch is ignored."
    echo "  -h, --help          Show this help"
    exit 1
}

update_installed_plugins() {
    local plug="$1"
    local plugin_json="$MARKETPLACE_DIR/plugins/$plug/.claude-plugin/plugin.json"
    if [[ ! -f "$plugin_json" ]]; then
        echo "Warning: $plugin_json not found — cannot update installed_plugins.json"
        return
    fi

    local new_version
    new_version=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" "$plugin_json")
    local new_sha
    new_sha=$(cd "$MARKETPLACE_DIR" && git rev-parse HEAD)
    local key="${plug}@${MARKETPLACE_NAME}"
    local new_install_path="$CACHE_DIR/$plug/$new_version"
    local now
    now=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")

    if [[ ! -f "$INSTALLED_PLUGINS" ]]; then
        echo "Warning: $INSTALLED_PLUGINS not found — skipping registry update"
        return
    fi

    python3 -c "
import json, sys

path = sys.argv[1]
key = sys.argv[2]
new_version = sys.argv[3]
new_install_path = sys.argv[4]
new_sha = sys.argv[5]
now = sys.argv[6]

with open(path) as f:
    data = json.load(f)

entries = data.get('plugins', {}).get(key, [])
if entries:
    entries[0]['version'] = new_version
    entries[0]['installPath'] = new_install_path
    entries[0]['gitCommitSha'] = new_sha
    entries[0]['lastUpdated'] = now
else:
    print(f'Warning: no entry for {key} in installed_plugins.json')
    sys.exit(0)

with open(path, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')

print(f'Updated {key}: version={new_version}, sha={new_sha[:8]}')
" "$INSTALLED_PLUGINS" "$key" "$new_version" "$new_install_path" "$new_sha" "$now"
}

branch=""
plugin="docs-tools"
reset=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --branch) branch="$2"; shift 2 ;;
        --plugin) plugin="$2"; shift 2 ;;
        --reset) reset=true; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

if [[ "$reset" == true ]]; then
    if [[ -z "$plugin" ]]; then
        echo "Error: --plugin <plugin> is required with --reset."
        echo
        usage
    fi

    plugin_cache="$CACHE_DIR/$plugin"
    if [[ -d "$plugin_cache" ]]; then
        echo "Deleting plugin cache: $plugin_cache"
        rm -rf "$plugin_cache"
        echo "Cache deleted."
    else
        echo "Warning: cache directory does not exist: $plugin_cache"
    fi

    cd "$MARKETPLACE_DIR"
    echo "Fetching origin/main ..."
    git fetch origin main
    echo "Checking out main and resetting to origin/main ..."
    git checkout main
    git reset --hard origin/main
    update_installed_plugins "$plugin"
    echo
    echo "Done. Reset to origin/main."
    echo "Branch: $(git branch --show-current)"
    exit 0
fi

if [[ -z "$branch" ]]; then
    branch=$(git branch --show-current 2>/dev/null || true)
    if [[ -z "$branch" ]]; then
        echo "Error: --branch <branch> is required (could not detect current branch)."
        echo
        usage
    fi
    echo "Using current branch: $branch"
fi

plugin_cache="$CACHE_DIR/$plugin"
if [[ -d "$plugin_cache" ]]; then
    echo "Deleting plugin cache: $plugin_cache"
    rm -rf "$plugin_cache"
    echo "Cache deleted."
else
    echo "Warning: cache directory does not exist: $plugin_cache"
fi

cd "$MARKETPLACE_DIR"

echo "Fetching origin/$branch ..."
git fetch origin "$branch":"refs/remotes/origin/$branch"

current_branch=$(git branch --show-current)
if [[ "$current_branch" == "$branch" ]]; then
    echo "Already on $branch — pulling latest."
    git pull origin "$branch"
else
    if git show-ref --verify --quiet "refs/heads/$branch" 2>/dev/null; then
        echo "Local branch $branch exists — switching and pulling."
        git checkout "$branch"
        git pull origin "$branch"
    else
        echo "Creating local branch $branch tracking origin/$branch."
        git checkout -b "$branch" "origin/$branch"
    fi
fi

update_installed_plugins "$plugin"

echo
echo "Done. Branch: $(git branch --show-current)"
echo "Cache cleared: $plugin_cache"
