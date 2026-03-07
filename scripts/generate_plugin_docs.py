#!/usr/bin/env python3
"""Generate docs pages from plugin metadata and commands."""

import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"
DOCS_DIR = REPO_ROOT / "docs"


def parse_frontmatter(text: str) -> dict:
    """Parse YAML-style frontmatter from a markdown file."""
    meta = {}
    if not text.startswith("---"):
        return meta
    end = text.find("---", 3)
    if end == -1:
        return meta
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip().strip('"')
    return meta


def load_plugins() -> list[dict]:
    """Scan plugins/ and return metadata for each plugin."""
    plugins = []
    if not PLUGINS_DIR.is_dir():
        return plugins

    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
        if not plugin_json.is_file():
            continue

        with open(plugin_json) as f:
            meta = json.load(f)

        commands = []
        commands_dir = plugin_dir / "commands"
        if commands_dir.is_dir():
            for cmd_file in sorted(commands_dir.glob("*.md")):
                cmd_text = cmd_file.read_text()
                fm = parse_frontmatter(cmd_text)
                commands.append({
                    "name": cmd_file.stem,
                    "description": fm.get("description", ""),
                    "argument_hint": fm.get("argument-hint", ""),
                })

        skills = []
        skills_dir = plugin_dir / "skills"
        if skills_dir.is_dir():
            # Support both flat skills/*.md and subdirectory skills/<name>/SKILL.md
            for skill_file in sorted(skills_dir.glob("*.md")):
                skill_text = skill_file.read_text()
                fm = parse_frontmatter(skill_text)
                skills.append({
                    "name": skill_file.stem,
                    "description": fm.get("description", ""),
                })
            for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
                skill_text = skill_file.read_text()
                fm = parse_frontmatter(skill_text)
                skills.append({
                    "name": skill_file.parent.name,
                    "description": fm.get("description", fm.get("name", "")),
                })

        agents = []
        agents_dir = plugin_dir / "agents"
        if agents_dir.is_dir():
            for agent_file in sorted(agents_dir.glob("*.md")):
                agent_text = agent_file.read_text()
                fm = parse_frontmatter(agent_text)
                agents.append({
                    "name": fm.get("name", agent_file.stem),
                    "description": fm.get("description", ""),
                })

        plugins.append({
            "name": meta.get("name", plugin_dir.name),
            "version": meta.get("version", "0.0.0"),
            "description": meta.get("description", ""),
            "commands": commands,
            "skills": skills,
            "agents": agents,
        })

    return plugins



def generate_plugin_detail_page(plugin: dict) -> str:
    """Generate a per-plugin detail page at docs/plugins/<name>.md."""
    p = plugin
    lines = [
        "---",
        f"subtitle: v{p['version']}",
        "---",
        "",
        f"# {p['name']}",
        f"**v{p['version']}**{{ .subtitle }}",
        "",
        p["description"],
        "",
        "## Install",
        "",
        "```bash",
        f"/plugin install {p['name']}@redhat-docs-agent-tools",
        "```",
        "",
        "## Update",
        "",
        "```bash",
        "/plugin marketplace update redhat-docs-agent-tools",
        "```",
        "",
    ]

    if p["commands"]:
        lines.append("## Commands")
        lines.append("")
        for cmd in p["commands"]:
            hint = f" {cmd['argument_hint']}" if cmd["argument_hint"] else ""
            lines.append("```bash")
            lines.append(f"/{p['name']}:{cmd['name']}{hint}")
            lines.append("```")
            lines.append("")
            lines.append(cmd["description"])
            lines.append("")

    if p.get("agents"):
        lines.append("## Agents")
        lines.append("")
        lines.append("| Agent | Description |")
        lines.append("|-------|-------------|")
        for agent in p["agents"]:
            lines.append(f"| `{agent['name']}` | {agent['description']} |")
        lines.append("")

    if p["skills"]:
        lines.append("## Skills")
        lines.append("")
        lines.append("| Skill | Description |")
        lines.append("|-------|-------------|")
        for skill in p["skills"]:
            lines.append(f"| `{skill['name']}` | {skill['description']} |")
        lines.append("")

    return "\n".join(lines)


def generate_docs_plugins_index(plugins: list[dict]) -> str:
    """Generate the docs/plugins.md card grid index page."""
    lines = [
        "# Plugins",
        "",
        "Browse available plugins. Click a card to view installation and usage details.",
        "",
        '!!! note',
        '    This page is auto-generated.',
        "",
        '<div class="grid cards" markdown>',
        "",
    ]

    for p in plugins:
        cmd_count = len(p["commands"])
        skill_count = len(p["skills"])
        agent_count = len(p.get("agents", []))
        summary_parts = []
        if cmd_count:
            summary_parts.append(f"{cmd_count} command{'s' if cmd_count != 1 else ''}")
        if agent_count:
            summary_parts.append(f"{agent_count} agent{'s' if agent_count != 1 else ''}")
        if skill_count:
            summary_parts.append(f"{skill_count} skill{'s' if skill_count != 1 else ''}")
        summary = " | ".join(summary_parts) if summary_parts else "Plugin"

        lines.append(f"-   :material-puzzle-outline:{{ .lg .middle }} **{p['name']}**")
        lines.append("")
        lines.append("    ---")
        lines.append("")
        lines.append(f"    {p['description']}")
        lines.append("")
        lines.append(f"    **v{p['version']}** | {summary}")
        lines.append("")
        lines.append(f"    [:octicons-arrow-right-24: Details](plugins/{p['name']}.md)")
        lines.append("")

    lines.append("</div>")

    return "\n".join(lines)


def generate_installation_page(plugins: list[dict]) -> str:
    """Generate the docs/installation.md page."""
    lines = [
        "# Install Claude Code and plugins",
        "",
        '!!! note',
        '    This page is auto-generated.',
        "",
        "## Prerequisites",
        "",
        "- Install [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI",
        "",
        "## Install plugins from the marketplace",
        "",
        "Add the plugin marketplace to your Claude Code configuration:",
        "",
        "```bash",
        "/plugin marketplace add https://github.com/redhat-documentation/redhat-docs-agent-tools.git",
        "```",
        "",
        "Then install any plugin:",
        "",
        "```bash",
        "/plugin install <plugin-name>@redhat-docs-agent-tools",
        "```",
        "",
        "## Available plugins",
        "",
        "| Plugin | Version | Description |",
        "|--------|---------|-------------|",
    ]

    for p in plugins:
        lines.append(f"| {p['name']} | {p['version']} | {p['description']} |")

    lines.append("")
    lines.append("## Update plugins")
    lines.append("")
    lines.append("```bash")
    lines.append("/plugin marketplace update redhat-docs-agent-tools")
    lines.append("```")

    return "\n".join(lines)


def main():
    plugins = load_plugins()

    # Write docs pages
    DOCS_DIR.mkdir(exist_ok=True)

    # Card grid index page
    (DOCS_DIR / "plugins.md").write_text(generate_docs_plugins_index(plugins))
    print("Generated docs/plugins.md (card grid)")

    # Per-plugin detail pages
    plugins_pages_dir = DOCS_DIR / "plugins"
    plugins_pages_dir.mkdir(exist_ok=True)
    for p in plugins:
        page_path = plugins_pages_dir / f"{p['name']}.md"
        page_path.write_text(generate_plugin_detail_page(p))
        print(f"Generated docs/plugins/{p['name']}.md")

    installing_dir = DOCS_DIR / "install"
    installing_dir.mkdir(exist_ok=True)
    (installing_dir / "index.md").write_text(generate_installation_page(plugins))
    print("Generated docs/install/index.md")

    # Update zensical.toml with version status entries and nav
    update_zensical_config(plugins)


def update_zensical_config(plugins: list[dict]) -> None:
    """Update zensical.toml with version status entries and plugin nav entries."""
    config_path = REPO_ROOT / "zensical.toml"
    if not config_path.is_file():
        return

    content = config_path.read_text()
    content = _update_nav_plugins(content, plugins)
    config_path.write_text(content)



def _update_nav_plugins(content: str, plugins: list[dict]) -> str:
    """Update the Plugins nav section to include plugin detail pages."""
    # Match the Plugins nav block and replace it with updated entries
    # Pattern: {"Plugins" = [\n        ...\n    ]}
    pattern = r'(\{"Plugins" = \[)\s*\n(.*?)\n(\s*\]\})'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return content

    indent = "        "
    nav_lines = [f'{indent}{{"Browse plugins" = "plugins.md"}},']
    for p in plugins:
        nav_lines.append(f'{indent}{{"{p["name"]}" = "plugins/{p["name"]}.md"}},')

    replacement = f'{match.group(1)}\n' + "\n".join(nav_lines) + f'\n{match.group(3)}'
    result = content[:match.start()] + replacement + content[match.end():]
    print(f"Updated zensical.toml nav with {len(plugins)} plugin page(s)")
    return result


if __name__ == "__main__":
    main()
