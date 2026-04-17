"""End-to-end integration tests for the md2adoc.py + pandoc conversion pipeline.

Verifies that MkDocs Markdown fixtures convert to valid AsciiDoc with correct
structure, that code snippets are inlined (not left as include:: directives),
and that the final output passes asciidoctor validation.

Pipeline order: md2adoc.py (pre-process raw .md) -> pandoc (convert to .adoc)
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from md2adoc import process_file

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

FIXTURE_FILES = [
    "simple_frontmatter.md",
    "admonitions_and_snippets.md",
    "figure_and_tabs.md",
    "full_complexity.md",
]


def _has_pandoc() -> bool:
    """Return True if pandoc is available on PATH."""
    return shutil.which("pandoc") is not None


def _has_asciidoctor() -> bool:
    """Return True if asciidoctor is available on PATH."""
    return shutil.which("asciidoctor") is not None


requires_pandoc = pytest.mark.skipif(not _has_pandoc(), reason="pandoc not installed")
requires_asciidoctor = pytest.mark.skipif(
    not _has_asciidoctor(), reason="asciidoctor not installed"
)


def pandoc_convert(md_path: Path, output_path: Path) -> Path:
    """Run pandoc to convert Markdown to AsciiDoc."""
    subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "asciidoc", "-o", str(output_path), str(md_path)],
        check=True,
        capture_output=True,
    )
    return output_path


def asciidoctor_validate(adoc_path: Path) -> list[str]:
    """Run asciidoctor and return any warning/error lines."""
    result = subprocess.run(
        ["asciidoctor", "-o", "/dev/null", str(adoc_path)],
        capture_output=True,
        text=True,
    )
    issues = []
    for line in result.stderr.splitlines():
        if "WARNING" in line or "ERROR" in line:
            issues.append(line)
    return issues


def asciidoctor_render(adoc_path: Path, output_path: Path) -> str:
    """Render AsciiDoc to HTML and return the HTML content."""
    subprocess.run(
        ["asciidoctor", "-o", str(output_path), str(adoc_path)],
        check=True,
        capture_output=True,
    )
    return output_path.read_text(encoding="utf-8")


def _convert_prose_snippets(tmp_path: Path) -> None:
    """Convert prose .md snippet files to .adoc so include:: directives resolve."""
    prose_dir = tmp_path / "prose_snippets"
    if not prose_dir.is_dir():
        return
    for md_file in prose_dir.glob("*.md"):
        adoc_file = md_file.with_suffix(".adoc")
        process_file(str(md_file), base_path=tmp_path)
        pandoc_convert(md_file, adoc_file)


def convert_fixture(
    fixture_name: str,
    tmp_path: Path,
    base_path_override: Path | None = ...,
) -> Path:
    """Copy a fixture and its snippet sources to tmp_path, run the full pipeline.

    Pipeline: md2adoc.py pre-processes raw .md -> pandoc converts to .adoc.
    Returns the path to the converted .adoc file.

    base_path_override: pass None to skip base_path, or a Path to override.
    The sentinel ... means "use tmp_path" (the default).
    """
    shutil.copy2(FIXTURES_DIR / fixture_name, tmp_path / fixture_name)

    for subdir in ("code_snippets", "prose_snippets"):
        src_dir = FIXTURES_DIR / subdir
        if src_dir.is_dir():
            dst_dir = tmp_path / subdir
            if not dst_dir.exists():
                shutil.copytree(src_dir, dst_dir)

    md_path = tmp_path / fixture_name

    effective_base = tmp_path if base_path_override is ... else base_path_override
    process_file(str(md_path), base_path=effective_base)

    adoc_name = fixture_name.replace(".md", ".adoc")
    adoc_path = tmp_path / adoc_name
    pandoc_convert(md_path, adoc_path)

    _convert_prose_snippets(tmp_path)

    return adoc_path


class TestFullPipelineValidation:
    """Verify that each fixture produces valid AsciiDoc after the full pipeline."""

    @requires_pandoc
    @requires_asciidoctor
    @pytest.mark.parametrize("fixture", FIXTURE_FILES)
    def test_full_pipeline_produces_valid_asciidoc(self, fixture, tmp_path):
        """Each fixture converts without asciidoctor errors."""
        adoc_path = convert_fixture(fixture, tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, "Converted file should not be empty"
        issues = asciidoctor_validate(adoc_path)
        errors = [i for i in issues if "ERROR" in i]
        assert len(errors) == 0, f"asciidoctor errors: {errors}"

    @requires_pandoc
    @requires_asciidoctor
    def test_empty_file_produces_valid_asciidoc(self, tmp_path):
        """An empty Markdown file converts to valid (empty) AsciiDoc."""
        md_path = tmp_path / "empty.md"
        md_path.write_text("", encoding="utf-8")
        process_file(str(md_path), base_path=tmp_path)
        adoc_path = tmp_path / "empty.adoc"
        pandoc_convert(md_path, adoc_path)
        issues = asciidoctor_validate(adoc_path)
        assert len(issues) == 0


class TestFrontmatter:
    """Verify YAML frontmatter converts to AsciiDoc title and abstract."""

    @requires_pandoc
    def test_frontmatter_converts_to_title(self, tmp_path):
        """Title and description from frontmatter appear as AsciiDoc equivalents."""
        adoc_path = convert_fixture("simple_frontmatter.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert "Getting Started with RHIVOS" in content
        assert '[role="_abstract"]' in content or "abstract" in content.lower()
        lines = content.splitlines()
        assert not any(line.strip() == "---" for line in lines)


class TestAdmonitions:
    """Verify MkDocs admonition syntax converts to AsciiDoc admonition blocks."""

    @requires_pandoc
    def test_admonitions_convert_to_blocks(self, tmp_path):
        """All admonition types convert and no MkDocs markers remain."""
        adoc_path = convert_fixture("admonitions_and_snippets.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert "[IMPORTANT]" in content
        assert "[NOTE]" in content
        assert "[WARNING]" in content
        assert "[TIP]" in content
        assert "!!!" not in content
        assert "???" not in content


class TestFiguresAndTabs:
    """Verify figure captions, tabbed content, and code block titles convert."""

    @requires_pandoc
    def test_figures_get_captions(self, tmp_path):
        """Figure captions appear as AsciiDoc titles before image macros."""
        adoc_path = convert_fixture("figure_and_tabs.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert "/// figure-caption" not in content
        assert ".RHIVOS build pipeline overview" in content

    @requires_pandoc
    def test_tabs_convert_to_labeled_sections(self, tmp_path):
        """Tab titles appear as AsciiDoc block titles with no MkDocs tab syntax."""
        adoc_path = convert_fixture("figure_and_tabs.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert ".x86_64" in content
        assert ".aarch64" in content
        assert '=== "' not in content

    @requires_pandoc
    def test_code_block_titles_convert(self, tmp_path):
        """Titled code blocks produce AsciiDoc source blocks with .Title."""
        adoc_path = convert_fixture("figure_and_tabs.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert "----" in content
        assert 'title="' not in content
        assert ".x86-config.yml" in content or ".arm-config.yml" in content


class TestLinks:
    """Verify relative Markdown links convert to AsciiDoc xrefs."""

    @requires_pandoc
    def test_links_convert_to_xrefs(self, tmp_path):
        """Relative .md links become .adoc references."""
        adoc_path = convert_fixture("simple_frontmatter.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert ".adoc" in content
        assert "](../getting-started/proc_installing.md)" not in content


class TestCodeSnippetInlining:
    """Core tests: code files are inlined, not left as include:: directives."""

    @requires_pandoc
    def test_code_snippet_inlined_not_included(self, tmp_path):
        """Code file content appears inline with no include:: for code paths."""
        adoc_path = convert_fixture("admonitions_and_snippets.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert "CONFIG_MARKER_A1B2" in content
        assert "SERVICE_MARKER_C3D4" in content
        assert "SCRIPT_MARKER_E5F6" in content
        assert "include::code_snippets/" not in content

    @requires_pandoc
    def test_code_snippet_has_source_block(self, tmp_path):
        """Inlined content is wrapped in [source,lang] with ---- delimiters."""
        adoc_path = convert_fixture("admonitions_and_snippets.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert "[source,yaml]" in content
        assert "[source,bash]" in content
        assert "[source,ini]" in content
        # 4 code snippets x 2 delimiters each = 8 minimum
        assert content.count("----") >= 8

    @requires_pandoc
    def test_line_range_extraction(self, tmp_path):
        """Line-range syntax extracts only the specified lines."""
        adoc_path = convert_fixture("admonitions_and_snippets.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert "RANGE_START_MARKER" in content
        assert "RANGE_END_MARKER" in content
        assert "line_01" not in content
        assert "line_11" not in content
        assert "twentieth" not in content

    @requires_pandoc
    def test_prose_snippet_remains_as_include(self, tmp_path):
        """Prose .md snippets produce include:: directives, not inlined content."""
        adoc_path = convert_fixture("admonitions_and_snippets.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert "include::prose_snippets/disclaimer.adoc[]" in content
        assert "DISCLAIMER_MARKER_G7H8" not in content

    @requires_pandoc
    def test_snippet_path_extension_converted(self, tmp_path):
        """Prose snippet include paths use .adoc extension, not .md."""
        adoc_path = convert_fixture("admonitions_and_snippets.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert "disclaimer.adoc" in content
        assert "disclaimer.md" not in content


class TestSnippetContentVerification:
    """Full round-trip: prose includes resolve in asciidoctor with content visible."""

    @requires_pandoc
    @requires_asciidoctor
    def test_prose_include_resolves_in_asciidoctor(self, tmp_path):
        """Asciidoctor resolves the prose include without errors."""
        adoc_path = convert_fixture("admonitions_and_snippets.md", tmp_path)
        issues = asciidoctor_validate(adoc_path)
        include_issues = [i for i in issues if "disclaimer" in i.lower()]
        assert len(include_issues) == 0, f"Include resolution issues: {include_issues}"

    @requires_pandoc
    @requires_asciidoctor
    def test_prose_content_appears_in_rendered_output(self, tmp_path):
        """Rendered HTML contains the prose snippet marker text."""
        adoc_path = convert_fixture("admonitions_and_snippets.md", tmp_path)
        html_path = tmp_path / "output.html"
        html = asciidoctor_render(adoc_path, html_path)
        assert "DISCLAIMER_MARKER_G7H8" in html

    @requires_pandoc
    @requires_asciidoctor
    def test_code_content_appears_in_rendered_output(self, tmp_path):
        """Rendered HTML contains all code snippet markers."""
        adoc_path = convert_fixture("admonitions_and_snippets.md", tmp_path)
        html_path = tmp_path / "output.html"
        html = asciidoctor_render(adoc_path, html_path)
        assert "CONFIG_MARKER_A1B2" in html
        assert "SERVICE_MARKER_C3D4" in html
        assert "SCRIPT_MARKER_E5F6" in html


class TestMissingSnippetFallback:
    """Verify graceful handling of missing or unresolvable snippet sources."""

    @requires_pandoc
    def test_missing_snippet_produces_warning_comment(self, tmp_path):
        """A missing code file produces a WARNING comment and include:: fallback."""
        md_content = '# Test\n\n--8<-- "nonexistent/file.yml"\n'
        md_path = tmp_path / "missing_snippet.md"
        md_path.write_text(md_content, encoding="utf-8")
        process_file(str(md_path), base_path=tmp_path)
        content = md_path.read_text(encoding="utf-8")
        assert "// WARNING: snippet source not found" in content
        assert "include::nonexistent/file.yml[]" in content

    @requires_pandoc
    def test_no_base_path_falls_back_to_include(self, tmp_path):
        """Without base_path, code snippets produce include:: (backward compatible)."""
        md_content = '# Test\n\n--8<-- "code_snippets/sample_config.yml"\n'
        md_path = tmp_path / "no_base.md"
        md_path.write_text(md_content, encoding="utf-8")
        process_file(str(md_path), base_path=None)
        content = md_path.read_text(encoding="utf-8")
        assert "include::code_snippets/sample_config.yml[]" in content
        assert "CONFIG_MARKER_A1B2" not in content


class TestNoMkDocsSyntaxRemains:
    """Catch-all: no MkDocs or intermediate syntax survives the full pipeline."""

    @requires_pandoc
    def test_no_mkdocs_syntax_remains(self, tmp_path):
        """The full_complexity fixture has zero residual MkDocs markers."""
        adoc_path = convert_fixture("full_complexity.md", tmp_path)
        content = adoc_path.read_text(encoding="utf-8")
        assert "!!!" not in content
        assert "???" not in content
        assert "--8<--" not in content
        assert '=== "' not in content
        assert "/// figure-caption" not in content
        assert re.search(r'```\w+\s+title=', content) is None
        assert re.search(r'\]\([^)]+\.md\)', content) is None
        assert "```{=asciidoc}" not in content
