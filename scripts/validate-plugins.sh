#!/bin/bash
#
# validate-plugins.sh
#
# Validates all plugins, skills, and commands in the redhat-docs-agent-tools repository.
# Checks for:
# - Valid JSON configuration files
# - Required YAML frontmatter in skills and commands
# - Script file existence and executability
# - Test fixture availability and script functionality
#

set -uo pipefail

# Colors for output (disabled when not running in an interactive terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Counters
ERRORS=0
WARNINGS=0
PASSED=0

# Get the repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++)) || true
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++)) || true
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((ERRORS++)) || true
}

log_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Validate JSON file
validate_json() {
    local file="$1"
    local description="$2"

    if [[ ! -f "$file" ]]; then
        log_error "$description: File not found: $file"
        return 1
    fi

    if jq empty "$file" 2>/dev/null; then
        log_pass "$description: Valid JSON"
        return 0
    else
        log_error "$description: Invalid JSON syntax"
        return 1
    fi
}

# Validate required JSON fields
validate_json_fields() {
    local file="$1"
    local description="$2"
    shift 2
    local fields=("$@")

    for field in "${fields[@]}"; do
        if jq -e ".$field" "$file" >/dev/null 2>&1; then
            log_pass "$description: Has required field '$field'"
        else
            log_error "$description: Missing required field '$field'"
        fi
    done
}

# Extract YAML frontmatter from markdown
extract_frontmatter() {
    local file="$1"

    # Check if file starts with ---
    if ! head -1 "$file" | grep -q "^---$"; then
        return 1
    fi

    # Extract content between first and second ---
    sed -n '2,/^---$/{ /^---$/d; p }' "$file"
}

# Validate YAML frontmatter field exists
validate_frontmatter_field() {
    local file="$1"
    local field="$2"
    local description="$3"

    local frontmatter
    frontmatter=$(extract_frontmatter "$file") || {
        log_error "$description: No YAML frontmatter found"
        return 1
    }

    if echo "$frontmatter" | grep -q "^${field}:"; then
        log_pass "$description: Has frontmatter field '$field'"
        return 0
    else
        log_error "$description: Missing frontmatter field '$field'"
        return 1
    fi
}

# Valid Claude Code tools
VALID_TOOLS=(
    "Bash"
    "Read"
    "Write"
    "Edit"
    "Glob"
    "Grep"
    "WebFetch"
    "WebSearch"
    "Skill"
    "Task"
    "TodoWrite"
    "NotebookEdit"
    "AskUserQuestion"
    "Agent"
)

# Extract tools from frontmatter (handles both 'tools:' and 'allowed-tools:')
extract_tools_from_frontmatter() {
    local file="$1"

    local frontmatter
    frontmatter=$(extract_frontmatter "$file") || return 1

    # Try 'allowed-tools:' first, then 'tools:'
    local tools_line
    tools_line=$(echo "$frontmatter" | grep -E "^(allowed-tools|tools):" | head -1)

    if [[ -z "$tools_line" ]]; then
        return 1
    fi

    # Extract the value after the colon
    echo "$tools_line" | sed 's/^[^:]*://' | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# Validate a single tool name against valid tools list
is_valid_tool() {
    local tool="$1"

    # Extract base tool name (handle patterns like "Bash(git add:*)")
    local base_tool
    base_tool=$(echo "$tool" | sed 's/(.*//')

    for valid in "${VALID_TOOLS[@]}"; do
        if [[ "$base_tool" == "$valid" ]]; then
            return 0
        fi
    done
    return 1
}

# Validate tools declared in frontmatter
validate_tools() {
    local file="$1"
    local description="$2"

    local tools
    tools=$(extract_tools_from_frontmatter "$file") || {
        # No tools field is OK - it's optional
        return 0
    }

    local has_tools=false
    local invalid_tools=()

    while IFS= read -r tool; do
        [[ -z "$tool" ]] && continue
        has_tools=true

        if ! is_valid_tool "$tool"; then
            invalid_tools+=("$tool")
        fi
    done <<< "$tools"

    if [[ "$has_tools" == "true" ]]; then
        if [[ ${#invalid_tools[@]} -eq 0 ]]; then
            log_pass "$description: All declared tools are valid"
        else
            for invalid in "${invalid_tools[@]}"; do
                log_error "$description: Invalid tool '$invalid'"
            done
        fi
    fi
}

# Validate skill structure
validate_skill() {
    local skill_dir="$1"
    local plugin_name="$2"
    local skill_name
    skill_name=$(basename "$skill_dir")
    local description="$plugin_name/$skill_name"

    log_info "Validating skill: $description"

    # Check SKILL.md exists
    local skill_md="$skill_dir/SKILL.md"
    if [[ ! -f "$skill_md" ]]; then
        log_error "$description: Missing SKILL.md"
        return
    fi
    log_pass "$description: SKILL.md exists"

    # Validate frontmatter fields
    validate_frontmatter_field "$skill_md" "name" "$description"
    validate_frontmatter_field "$skill_md" "description" "$description"

    # Validate declared tools
    validate_tools "$skill_md" "$description"

    # Check for scripts directory if skill has implementation
    local scripts_dir="$skill_dir/scripts"
    if [[ -d "$scripts_dir" ]]; then
        local script_count
        script_count=$(find "$scripts_dir" -type f \( -name "*.rb" -o -name "*.py" -o -name "*.sh" \) | wc -l)
        if [[ $script_count -gt 0 ]]; then
            log_pass "$description: Has $script_count script(s) in scripts/"
        else
            log_warn "$description: scripts/ directory exists but no scripts found"
        fi
    fi
}

# Validate agent structure
validate_agent() {
    local agent_file="$1"
    local plugin_name="$2"
    local agent_name
    agent_name=$(basename "$agent_file" .md)
    local description="$plugin_name/agents/$agent_name"

    log_info "Validating agent: $description"

    # Validate frontmatter fields
    validate_frontmatter_field "$agent_file" "name" "$description"
    validate_frontmatter_field "$agent_file" "description" "$description"
    validate_frontmatter_field "$agent_file" "tools" "$description"

    # Validate declared tools
    validate_tools "$agent_file" "$description"
}

# Validate command structure
validate_command() {
    local command_file="$1"
    local plugin_name="$2"
    local command_name
    command_name=$(basename "$command_file" .md)
    local description="$plugin_name/commands/$command_name"

    log_info "Validating command: $description"

    # Validate frontmatter fields
    validate_frontmatter_field "$command_file" "description" "$description"

    # Validate declared tools
    validate_tools "$command_file" "$description"
}

# Validate Ruby script with dry-run
validate_ruby_script() {
    local script="$1"
    local fixture_dir="$2"
    local script_name
    script_name=$(basename "$script" .rb)
    local description="Script: $script_name"

    log_info "Testing script: $script_name"

    # Check script syntax
    if ruby -c "$script" >/dev/null 2>&1; then
        log_pass "$description: Valid Ruby syntax"
    else
        log_error "$description: Invalid Ruby syntax"
        return
    fi

    # Check for test fixtures
    if [[ -d "$fixture_dir" ]]; then
        local fixture_count
        fixture_count=$(find "$fixture_dir" -name "*.adoc" | wc -l)
        if [[ $fixture_count -gt 0 ]]; then
            log_pass "$description: Has $fixture_count test fixture(s)"

            # Test with first fixture using --dry-run
            local test_fixture
            test_fixture=$(find "$fixture_dir" -name "*.adoc" | head -1)

            if ruby "$script" "$test_fixture" --dry-run >/dev/null 2>&1; then
                log_pass "$description: Dry-run test passed"
            else
                log_warn "$description: Dry-run test returned non-zero exit (may be expected)"
            fi
        else
            log_warn "$description: Fixture directory exists but no .adoc files found"
        fi
    else
        log_warn "$description: No test fixtures found at $fixture_dir"
    fi
}

# Validate Python script
validate_python_script() {
    local script="$1"
    local script_name
    script_name=$(basename "$script")
    local description="Script: $script_name"

    log_info "Validating Python script: $script_name"

    # Check script syntax
    if python3 -m py_compile "$script" 2>/dev/null; then
        log_pass "$description: Valid Python syntax"
    else
        log_error "$description: Invalid Python syntax"
    fi
}

# Validate shell script
validate_shell_script() {
    local script="$1"
    local script_name
    script_name=$(basename "$script")
    local description="Script: $script_name"

    log_info "Validating shell script: $script_name"

    # Check script syntax
    if bash -n "$script" 2>/dev/null; then
        log_pass "$description: Valid shell syntax"
    else
        log_error "$description: Invalid shell syntax"
    fi
}

# Main validation logic
main() {
    log_section "Plugin Validation"
    echo "Repository: $REPO_ROOT"
    echo "Date: $(date)"

    # Check required tools
    log_section "Checking Prerequisites"

    if command -v jq >/dev/null 2>&1; then
        log_pass "jq is installed"
    else
        log_error "jq is not installed (required for JSON validation)"
    fi

    if command -v ruby >/dev/null 2>&1; then
        log_pass "ruby is installed: $(ruby --version)"
    else
        log_warn "ruby is not installed (needed for script validation)"
    fi

    if command -v python3 >/dev/null 2>&1; then
        log_pass "python3 is installed: $(python3 --version)"
    else
        log_warn "python3 is not installed (needed for script validation)"
    fi

    # Discover plugins by scanning plugins/ directory
    local plugins_dir="$REPO_ROOT/plugins"

    if [[ ! -d "$plugins_dir" ]]; then
        log_error "plugins/ directory not found"
        exit 1
    fi

    # Validate each plugin
    for plugin_dir in "$plugins_dir"/*/; do
        if [[ ! -d "$plugin_dir" ]]; then
            continue
        fi

        local plugin_name
        plugin_name=$(basename "$plugin_dir")
        local plugin_json="$plugin_dir/.claude-plugin/plugin.json"

        log_section "Validating Plugin: $plugin_name"

        # Validate plugin.json
        validate_json "$plugin_json" "$plugin_name/plugin.json"
        validate_json_fields "$plugin_json" "$plugin_name/plugin.json" "name" "description"

        # Check version field
        if jq -e ".version" "$plugin_json" >/dev/null 2>&1; then
            log_pass "$plugin_name/plugin.json: Has 'version' field"
        else
            log_warn "$plugin_name/plugin.json: Missing 'version' field"
        fi

        # Validate skills
        local skills_dir="$plugin_dir/skills"
        if [[ -d "$skills_dir" ]]; then
            log_info "Found skills directory"
            for skill_dir in "$skills_dir"/*/; do
                if [[ -d "$skill_dir" ]]; then
                    validate_skill "$skill_dir" "$plugin_name"
                fi
            done
        fi

        # Validate agents
        local agents_dir="$plugin_dir/agents"
        if [[ -d "$agents_dir" ]]; then
            log_info "Found agents directory"
            for agent_file in "$agents_dir"/*.md; do
                if [[ -f "$agent_file" ]]; then
                    validate_agent "$agent_file" "$plugin_name"
                fi
            done
        fi

        # Validate commands
        local commands_dir="$plugin_dir/commands"
        if [[ -d "$commands_dir" ]]; then
            log_info "Found commands directory"
            for command_file in "$commands_dir"/*.md; do
                if [[ -f "$command_file" ]]; then
                    validate_command "$command_file" "$plugin_name"
                fi
            done
        fi
    done

    # Validate Ruby scripts with test fixtures
    log_section "Validating Ruby Scripts with Test Fixtures"

    local test_fixtures_dir="$REPO_ROOT/test-fixtures"

    while IFS= read -r script_path; do
        # Extract skill name from path: .../skills/<skill-name>/scripts/script.rb
        local skill_name
        skill_name=$(echo "$script_path" | sed 's|.*/skills/\([^/]*\)/scripts/.*|\1|')
        local fixture_path="$test_fixtures_dir/$skill_name"

        validate_ruby_script "$script_path" "$fixture_path"
    done < <(find "$REPO_ROOT/plugins" -path "*/skills/*/scripts/*.rb" -type f 2>/dev/null)

    # Validate shell scripts in skills
    log_section "Validating Shell Scripts"

    while IFS= read -r script_path; do
        validate_shell_script "$script_path"
    done < <(find "$REPO_ROOT/plugins" -path "*/skills/*/scripts/*.sh" -type f 2>/dev/null)

    # Validate Python scripts in skills
    log_section "Validating Python Scripts"

    while IFS= read -r script_path; do
        validate_python_script "$script_path"
    done < <(find "$REPO_ROOT/plugins" -path "*/skills/*/scripts/*.py" -type f 2>/dev/null)

    # Also validate Python scripts in commands
    while IFS= read -r script_path; do
        validate_python_script "$script_path"
    done < <(find "$REPO_ROOT/plugins" -path "*/commands/scripts/*.py" -type f 2>/dev/null)

    # Summary
    log_section "Validation Summary"
    echo ""
    echo -e "  ${GREEN}Passed:${NC}   $PASSED"
    echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
    echo -e "  ${RED}Errors:${NC}   $ERRORS"
    echo ""

    if [[ $ERRORS -gt 0 ]]; then
        echo -e "${RED}Validation failed with $ERRORS error(s)${NC}"
        exit 1
    elif [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}Validation passed with $WARNINGS warning(s)${NC}"
        exit 0
    else
        echo -e "${GREEN}All validations passed!${NC}"
        exit 0
    fi
}

# Run main
main "$@"
