#!/usr/bin/env python3
"""Pre-process MkDocs Markdown before pandoc conversion to AsciiDoc.

Handles Material for MkDocs extensions that pandoc cannot convert:
- YAML frontmatter title/description
- Admonitions (!!! note/warning/tip/important/caution)
- Collapsible admonitions (??? note)
- Tabbed content (=== "Tab title")
- Snippet inclusions (--8<-- "path") with code file inlining
- Figure captions (/// figure-caption)
- Code block titles (```lang title="Title")
- Relative Markdown links (.md -> .adoc)

Usage:
    python3 md2adoc.py [--base-path <dir>] <file.md>

Converts MkDocs extensions in-place. Injected AsciiDoc is wrapped in
pandoc raw blocks (```{=asciidoc}) so that pandoc passes it through
verbatim during Markdown-to-AsciiDoc conversion.
"""

import argparse
import re
import sys
from pathlib import Path

EXTENSION_LANGUAGE_MAP = {
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".py": "python",
    ".sh": "bash",
    ".toml": "toml",
    ".container": "ini",
    ".conf": "ini",
}

RAW_OPEN = "```{=asciidoc}"
RAW_CLOSE = "```"


def _raw_block(asciidoc_lines: list[str]) -> list[str]:
    """Wrap AsciiDoc lines in a pandoc raw block for pass-through."""
    return [RAW_OPEN, *asciidoc_lines, "", RAW_CLOSE]


def _unwrap_raw_blocks(lines: list[str]) -> list[str]:
    """Strip raw block open/close markers, keeping the AsciiDoc content within."""
    return [line for line in lines if line != RAW_OPEN and line != RAW_CLOSE]


def convert_admonitions(lines: list[str]) -> list[str]:
    """Convert MkDocs admonitions to AsciiDoc admonition blocks.

    Input:  !!! note "Optional title"
                Content indented by 4 spaces

    Output (wrapped in raw block):
            [NOTE]
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

            inner = []
            i += 1
            while i < len(lines) and (
                lines[i].startswith("    ") or lines[i].strip() == ""
            ):
                if lines[i].strip() == "":
                    inner.append("")
                else:
                    inner.append(lines[i][4:])
                i += 1

            inner = _unwrap_raw_blocks(inner)

            block = [f"[{asciidoc_type}]"]
            if title:
                block.append(f".{title}")
            block.append("====")
            block.extend(inner)
            block.append("====")
            result.extend(_raw_block(block))
            result.append("")
        else:
            result.append(lines[i])
            i += 1

    return result


def convert_tabbed_content(lines: list[str]) -> list[str]:
    """Convert MkDocs tabbed content to AsciiDoc labeled sections.

    Input:  === "Tab title"
                Content indented by 4 spaces

    Output (wrapped in raw block):
            .Tab title
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
            inner = []

            i += 1
            while i < len(lines) and (
                lines[i].startswith("    ") or lines[i].strip() == ""
            ):
                if lines[i].strip() == "":
                    inner.append("")
                else:
                    inner.append(lines[i][4:])
                i += 1

            inner = _unwrap_raw_blocks(inner)

            block = [f".{title}", "--"]
            block.extend(inner)
            block.append("--")
            result.extend(_raw_block(block))
            result.append("")
        else:
            result.append(lines[i])
            i += 1

    return result


def _read_snippet_lines(file_path: Path, start: int | None, end: int | None) -> list[str]:
    """Read lines from a file, optionally extracting a 1-indexed inclusive range."""
    all_lines = file_path.read_text(encoding="utf-8").splitlines()
    if start is not None and end is not None:
        if start < 1 or end < start:
            return all_lines
        return all_lines[start - 1 : end]
    return all_lines


def _lang_for_extension(suffix: str) -> str | None:
    """Return the AsciiDoc source language tag for a file extension, or None."""
    return EXTENSION_LANGUAGE_MAP.get(suffix)


def _emit_snippet(result: list[str], block: list[str], indent: str) -> None:
    """Append snippet AsciiDoc to result, indented or raw-block-wrapped.

    Indented snippets (inside admonitions/tabs) preserve their indent so the
    container's content collector still recognizes them. Container transforms
    strip raw block markers later via _unwrap_raw_blocks. Standalone snippets
    are wrapped in raw blocks for pandoc pass-through.
    """
    if indent:
        for line in block:
            result.append(indent + line if line else "")
    else:
        result.extend(_raw_block(block))


def convert_snippets(lines: list[str], base_path: Path | None = None) -> list[str]:
    """Convert MkDocs snippet inclusions.

    Prose .md files become include:: directives (extension swapped to .adoc).
    Code files are inlined as AsciiDoc source blocks when base_path is set
    and the source file exists. Supports line-range syntax ("file:start:end").

    Standalone snippets are wrapped in raw blocks for pandoc pass-through.
    Indented snippets (inside containers) preserve their indent so that
    admonition/tab collectors can still gather them.
    """
    snippet_re = re.compile(r'^(?P<indent>\s*)--8<--\s+"(?P<ref>[^"]+)"\s*$')
    range_re = re.compile(r"^(?P<path>.+):(?P<start>\d+):(?P<end>\d+)$")
    result = []

    for line in lines:
        match = snippet_re.match(line)
        if not match:
            result.append(line)
            continue

        indent = match.group("indent")
        ref = match.group("ref")

        range_match = range_re.match(ref)
        if range_match:
            file_ref = range_match.group("path")
            start = int(range_match.group("start"))
            end = int(range_match.group("end"))
        else:
            file_ref = ref
            start = None
            end = None

        suffix = Path(file_ref).suffix.lower()

        if suffix == ".md":
            adoc_path = file_ref[:-3] + ".adoc"
            _emit_snippet(result, [f"include::{adoc_path}[]"], indent)
            continue

        if base_path is None:
            _emit_snippet(result, [f"include::{file_ref}[]"], indent)
            continue

        base_root = base_path.resolve()
        resolved = (base_path / file_ref).resolve()
        if not resolved.is_relative_to(base_root):
            _emit_snippet(result, [
                f"// WARNING: snippet path escapes base path: {file_ref}",
                f"include::{file_ref}[]",
            ], indent)
            continue

        if not resolved.is_file():
            _emit_snippet(result, [
                f"// WARNING: snippet source not found: {file_ref}",
                f"include::{file_ref}[]",
            ], indent)
            continue

        content_lines = _read_snippet_lines(resolved, start, end)
        lang = _lang_for_extension(suffix)
        block = []
        if lang:
            block.append(f"[source,{lang}]")
        else:
            block.append("[source]")
        block.append("----")
        block.extend(content_lines)
        block.append("----")
        _emit_snippet(result, block, indent)

    return result


def convert_figure_captions(lines: list[str]) -> list[str]:
    """Convert MkDocs figure captions to AsciiDoc image titles.

    Looks for /// figure-caption blocks after Markdown images and converts
    to AsciiDoc image macros with title.
    """
    result = []
    i = 0
    md_img_re = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")

    while i < len(lines):
        img_match = md_img_re.match(lines[i])
        if img_match:
            alt = img_match.group(1)
            src = img_match.group(2)
            if (
                i + 1 < len(lines)
                and lines[i + 1].strip() == "/// figure-caption"
            ):
                caption_lines = []
                i += 2
                while i < len(lines) and lines[i].strip() != "///":
                    caption_lines.append(lines[i].strip())
                    i += 1
                if i < len(lines):
                    i += 1
                caption = " ".join(caption_lines)
                result.extend(_raw_block([f".{caption}", f"image::{src}[{alt}]"]))
            else:
                result.extend(_raw_block([f"image::{src}[{alt}]"]))
                i += 1
        elif lines[i].strip() == "/// figure-caption":
            caption_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != "///":
                caption_lines.append(lines[i].strip())
                i += 1
            if i < len(lines):
                i += 1
            caption = " ".join(caption_lines)
            for j in range(len(result) - 1, -1, -1):
                if "image::" in result[j] or result[j].startswith("image:"):
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

    Output (wrapped in raw block for standalone, or indented for container context):
            .my-manifest.yaml
            [source,yaml]
            ----
            content
            ----
    """
    result = []
    i = 0
    title_re = re.compile(r"^(?P<indent>\s*)```(\w*)\s+title=\"([^\"]+)\"\s*$")

    while i < len(lines):
        match = title_re.match(lines[i])
        if match:
            indent = match.group("indent")
            lang = match.group(2)
            title = match.group(3)
            block = [f".{title}"]
            if lang:
                block.append(f"[source,{lang}]")
            block.append("----")
            i += 1
            close_re = re.compile(r"^" + re.escape(indent) + r"```\s*$")
            while i < len(lines) and not close_re.match(lines[i]):
                line = lines[i]
                if indent and line.startswith(indent):
                    line = line[len(indent):]
                block.append(line)
                i += 1
            block.append("----")
            if i < len(lines):
                i += 1
            if indent:
                for line in block:
                    result.append(indent + line if line else "")
            else:
                result.extend(_raw_block(block))
        else:
            result.append(lines[i])
            i += 1

    return result


def convert_markdown_links(lines: list[str]) -> list[str]:
    """Convert relative Markdown links to AsciiDoc cross-references.

    Input:  [link text](../path/to/file.md)
    Output: xref:../path/to/file.adoc[link text]

    Leaves external URLs and raw-block fences unchanged.
    """
    result = []
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    in_raw_block = False

    for line in lines:
        if line == RAW_OPEN:
            in_raw_block = True
            result.append(line)
            continue
        if line == RAW_CLOSE:
            in_raw_block = False
            result.append(line)
            continue
        if in_raw_block:
            result.append(line)
            continue

        def replace_link(m):
            text = m.group(1)
            target = m.group(2)
            if target.startswith(("http://", "https://", "mailto:")):
                return m.group(0)
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

    Output (wrapped in raw block):
            = My Title

            [role="_abstract"]
            A description.
    """
    if not lines or lines[0].strip() != "---":
        return lines

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
    block = []
    if title:
        block.append(f"= {title}")
        block.append("")
    if description:
        block.append('[role="_abstract"]')
        block.append(description)
        block.append("")

    if block:
        result.extend(_raw_block(block))

    result.extend(lines[end + 1 :])
    return result


def process_file(filepath: str, base_path: Path | None = None) -> None:
    """Pre-process a Markdown file to convert MkDocs extensions in-place.

    Must be run on the raw .md file BEFORE pandoc conversion. AsciiDoc
    content is wrapped in pandoc raw blocks so pandoc passes it through
    verbatim during the subsequent Markdown-to-AsciiDoc conversion.
    """
    path = Path(filepath)
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    lines = convert_frontmatter(lines)
    lines = convert_snippets(lines, base_path=base_path)
    lines = convert_code_block_titles(lines)
    lines = convert_figure_captions(lines)
    lines = convert_markdown_links(lines)
    lines = convert_admonitions(lines)
    lines = convert_tabbed_content(lines)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """CLI entry point: parse arguments and run the pre-processor."""
    parser = argparse.ArgumentParser(
        description="Pre-process MkDocs Markdown for pandoc conversion to AsciiDoc"
    )
    parser.add_argument("file", help="Markdown file to process in place")
    parser.add_argument(
        "--base-path",
        type=Path,
        default=None,
        help="Root directory for resolving snippet source files",
    )
    args = parser.parse_args()

    if not Path(args.file).exists():
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    process_file(args.file, base_path=args.base_path)
    print(f"Pre-processed: {args.file}")


if __name__ == "__main__":
    main()
