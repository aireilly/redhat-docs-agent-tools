#!/usr/bin/env python3
"""Post-process pandoc AsciiDoc output to handle Material for MkDocs extensions.

Handles syntactic conversions that pandoc does not support:
- Tabbed content (=== "Tab title")
- Admonitions (!!! note/warning/tip/important/caution)
- Snippet inclusions (--8<-- "path")
- Figure captions (/// figure-caption)
- Code block titles (```lang title="Title")
- Relative Markdown links -> AsciiDoc xrefs
- YAML frontmatter title/description

Usage:
    python3 md2adoc.py <file.adoc>

Modifies the file in place.
"""

import re
import sys
from pathlib import Path


def convert_admonitions(lines: list[str]) -> list[str]:
    """Convert MkDocs admonitions to AsciiDoc admonition blocks.

    Input:  !!! note "Optional title"
                Content indented by 4 spaces

    Output: [NOTE]
            .Optional title
            ====
            Content
            ====
    """
    result = []
    i = 0
    admonition_map = {
        "note": "NOTE",
        "warning": "WARNING",
        "danger": "WARNING",
        "tip": "TIP",
        "hint": "TIP",
        "important": "IMPORTANT",
        "caution": "CAUTION",
        "abstract": "NOTE",
        "info": "NOTE",
        "example": "NOTE",
    }

    while i < len(lines):
        match = re.match(
            r'^(!{3}|\?{3})\s+([\w]+)(?:\s+"([^"]*)")?\s*$', lines[i]
        )
        if match:
            admon_type = match.group(2).lower()
            title = match.group(3)
            asciidoc_type = admonition_map.get(admon_type, "NOTE")

            # Collapsible admonitions (???) map the same way
            result.append(f"[{asciidoc_type}]")
            if title:
                result.append(f".{title}")
            result.append("====")

            # Collect indented content
            i += 1
            while i < len(lines) and (
                lines[i].startswith("    ") or lines[i].strip() == ""
            ):
                if lines[i].strip() == "":
                    result.append("")
                else:
                    result.append(lines[i][4:])  # Remove 4-space indent
                i += 1

            result.append("====")
            result.append("")
        else:
            result.append(lines[i])
            i += 1

    return result


def convert_tabbed_content(lines: list[str]) -> list[str]:
    """Convert MkDocs tabbed content to AsciiDoc labeled sections.

    Input:  === "Tab title"
                Content indented by 4 spaces

    Output: .Tab title
            --
            Content
            --
    """
    result = []
    i = 0

    while i < len(lines):
        match = re.match(r'^===\s+"([^"]+)"\s*$', lines[i])
        if match:
            title = match.group(1)
            result.append(f".{title}")
            result.append("--")

            # Collect indented content
            i += 1
            while i < len(lines) and (
                lines[i].startswith("    ") or lines[i].strip() == ""
            ):
                if lines[i].strip() == "":
                    result.append("")
                else:
                    result.append(lines[i][4:])
                i += 1

            result.append("--")
            result.append("")
        else:
            result.append(lines[i])
            i += 1

    return result


def convert_snippets(lines: list[str]) -> list[str]:
    """Convert MkDocs snippet inclusions to AsciiDoc includes.

    Input:  --8<-- "path/to/file.md"
    Output: include::path/to/file.adoc[]
    """
    result = []
    for line in lines:
        match = re.match(r'^--8<--\s+"([^"]+)"\s*$', line)
        if match:
            path = match.group(1)
            # Change .md extension to .adoc
            if path.endswith(".md"):
                path = path[:-3] + ".adoc"
            result.append(f"include::{path}[]")
        else:
            result.append(line)
    return result


def convert_figure_captions(lines: list[str]) -> list[str]:
    """Convert MkDocs figure captions to AsciiDoc image titles.

    Input:  ![alt](image.png)
            /// figure-caption
            Caption text
            ///

    Output: .Caption text
            image::image.png[alt]
    """
    result = []
    i = 0

    while i < len(lines):
        # Look for figure-caption blocks after images
        if i + 2 < len(lines) and lines[i].strip() == "/// figure-caption":
            # Collect caption text
            caption_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != "///":
                caption_lines.append(lines[i].strip())
                i += 1
            if i < len(lines):
                i += 1  # Skip closing ///

            caption = " ".join(caption_lines)

            # Find the preceding image in result and prepend the caption
            for j in range(len(result) - 1, -1, -1):
                if result[j].startswith("image::"):
                    result.insert(j, f".{caption}")
                    break
        else:
            result.append(lines[i])
            i += 1

    return result


def convert_code_block_titles(lines: list[str]) -> list[str]:
    """Convert fenced code blocks with title= to AsciiDoc source blocks with .Title.

    Input:  ```yaml title="my-manifest.yaml"
            content
            ```

    Output: .my-manifest.yaml
            [source,yaml]
            ----
            content
            ----
    """
    result = []
    i = 0

    while i < len(lines):
        match = re.match(r"^```(\w*)\s+title=\"([^\"]+)\"\s*$", lines[i])
        if match:
            lang = match.group(1)
            title = match.group(2)
            result.append(f".{title}")
            if lang:
                result.append(f"[source,{lang}]")
            result.append("----")
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                result.append(lines[i])
                i += 1
            result.append("----")
            if i < len(lines):
                i += 1  # Skip closing ```
        else:
            result.append(lines[i])
            i += 1

    return result


def convert_markdown_links(lines: list[str]) -> list[str]:
    """Convert relative Markdown links to AsciiDoc cross-references.

    Input:  [link text](../path/to/file.md)
    Output: xref:../path/to/file.adoc[link text]

    Leaves external URLs unchanged.
    """
    result = []
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for line in lines:

        def replace_link(m):
            text = m.group(1)
            target = m.group(2)
            # Skip external URLs
            if target.startswith(("http://", "https://", "mailto:")):
                return m.group(0)
            # Convert .md to .adoc
            if target.endswith(".md"):
                target = target[:-3] + ".adoc"
            return f"xref:{target}[{text}]"

        result.append(link_pattern.sub(replace_link, line))
    return result


def convert_frontmatter(lines: list[str]) -> list[str]:
    """Convert YAML frontmatter title/description to AsciiDoc equivalents.

    Input:  ---
            title: My Title
            description: A description.
            ---

    Output: = My Title

            [role="_abstract"]
            A description.
    """
    if not lines or lines[0].strip() != "---":
        return lines

    # Find closing ---
    end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break

    if end == -1:
        return lines

    title = None
    description = None

    for i in range(1, end):
        line = lines[i]
        if line.startswith("title:"):
            title = line[len("title:") :].strip().strip("\"'")
        elif line.startswith("description:"):
            description = line[len("description:") :].strip().strip("\"'")

    result = []
    if title:
        result.append(f"= {title}")
        result.append("")
    if description:
        result.append('[role="_abstract"]')
        result.append(description)
        result.append("")

    # Append remaining content after frontmatter
    result.extend(lines[end + 1 :])
    return result


def process_file(filepath: str) -> None:
    """Apply all conversions to a file in place."""
    path = Path(filepath)
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Apply conversions in order
    lines = convert_frontmatter(lines)
    lines = convert_admonitions(lines)
    lines = convert_tabbed_content(lines)
    lines = convert_snippets(lines)
    lines = convert_code_block_titles(lines)
    lines = convert_figure_captions(lines)
    lines = convert_markdown_links(lines)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file.adoc>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    if not Path(filepath).exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    process_file(filepath)
    print(f"Post-processed: {filepath}")


if __name__ == "__main__":
    main()
