#!/usr/bin/env bash
# Sync .claude/skills/, .claude/agents/, and .claude/reference/ symlinks
# to match plugin directories. Adds missing symlinks, removes stale ones,
# and leaves non-symlink entries untouched.
#
# Usage: ./scripts/sync-claude-symlinks.sh [--check]
#   --check   Report what would change without modifying anything (exit 1 if out of sync)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHECK_ONLY=false
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=true

added=0
removed=0
errors=0

# --- Sync a single category (skills, agents, reference) ---
sync_category() {
  local category="$1"    # skills | agents | reference
  local target_dir="${REPO_ROOT}/.claude/${category}"
  mkdir -p "$target_dir"

  # Build set of expected symlinks from plugins
  declare -A expected
  for plugin_dir in "${REPO_ROOT}"/plugins/*/; do
    local source_dir="${plugin_dir}${category}"
    [ -d "$source_dir" ] || continue

    if [[ "$category" == "skills" ]]; then
      # Skills are directories containing SKILL.md
      for entry in "${source_dir}"/*/; do
        [ -f "${entry}SKILL.md" ] || continue
        local name
        name="$(basename "$entry")"
        expected["$name"]="$entry"
      done
    else
      # Agents and reference are individual .md files
      for entry in "${source_dir}"/*.md; do
        [ -f "$entry" ] || continue
        local name
        name="$(basename "$entry")"
        expected["$name"]="$entry"
      done
    fi
  done

  # Add missing symlinks
  for name in "${!expected[@]}"; do
    local source="${expected[$name]}"
    local link="${target_dir}/${name}"

    if [ -e "$link" ] && [ ! -L "$link" ]; then
      # Real directory/file — skip
      continue
    fi

    if [ ! -e "$link" ]; then
      local rel_path
      rel_path="$(realpath --relative-to="$target_dir" "$source")"
      if $CHECK_ONLY; then
        echo "  ADD: ${category}/${name} -> ${rel_path}"
      else
        ln -sfn "$rel_path" "$link"
        echo "  Added: ${category}/${name}"
      fi
      added=$((added + 1))
    fi
  done

  # Remove stale symlinks (symlinks whose target no longer exists)
  if [[ "$category" == "skills" ]]; then
    for link in "${target_dir}"/*/; do
      [ -L "${link%/}" ] || continue
      local name
      name="$(basename "$link")"
      if [ ! -f "${link}SKILL.md" ]; then
        if $CHECK_ONLY; then
          echo "  REMOVE: ${category}/${name} (broken or stale)"
        else
          rm "$target_dir/$name"
          echo "  Removed: ${category}/${name} (stale)"
        fi
        removed=$((removed + 1))
      fi
    done
  else
    for link in "${target_dir}"/*.md; do
      [ -L "$link" ] || continue
      if [ ! -e "$link" ]; then
        local name
        name="$(basename "$link")"
        if $CHECK_ONLY; then
          echo "  REMOVE: ${category}/${name} (broken)"
        else
          rm "$link"
          echo "  Removed: ${category}/${name} (broken)"
        fi
        removed=$((removed + 1))
      fi
    done
  fi
}

echo "Syncing .claude/ symlinks..."
echo
echo "Skills:"
sync_category skills
echo
echo "Agents:"
sync_category agents
echo
echo "Reference:"
sync_category reference

total=$((added + removed))
if [ "$total" -eq 0 ]; then
  echo
  echo "All symlinks are in sync."
  exit 0
else
  echo
  if $CHECK_ONLY; then
    echo "Out of sync: ${added} to add, ${removed} to remove."
    exit 1
  else
    echo "Done: ${added} added, ${removed} removed."
    exit 0
  fi
fi
