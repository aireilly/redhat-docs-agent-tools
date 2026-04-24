#!/usr/bin/env python3
"""
code_scanner.py — Extract technical references from documentation files.

Parses AsciiDoc and Markdown files to identify commands, code blocks,
API references, configuration keys, and file paths. Outputs structured
JSON for use by review agents.

Usage:
    python3 code_scanner.py extract <doc files...> [--output refs.json]
"""

import argparse
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("code_scanner")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKIP_FUNCTIONS = frozenset(
    "if for while print return len map set get new int str list dict type "
    "var let const def end do nil true false else case break next puts echo "
    "test eval".split()
)

EXTERNAL_COMMANDS = frozenset(
    "sudo grep egrep fgrep sed awk cat head tail less more wc sort uniq cut "
    "tr tee xargs find ls cp mv rm mkdir rmdir chmod chown ln touch "
    "echo printf read export source set unset "
    "git svn hg "
    "curl wget ssh scp rsync nc telnet "
    "docker podman buildah skopeo "
    "oc kubectl helm kustomize "
    "dnf yum rpm apt dpkg pacman zypper brew pip pip3 gem npm yarn "
    "systemctl journalctl service chkconfig "
    "ansible ansible-playbook terraform "
    "make cmake gcc g++ javac python python3 ruby node go rustc cargo "
    "tar gzip gunzip zip unzip bzip2 xz "
    "ps kill top htop df du free mount umount "
    "cd pwd env which whereis file stat date cal man info".split()
)

# ---------------------------------------------------------------------------
# Discovery patterns — used by the `discover` subcommand
# ---------------------------------------------------------------------------

LANGUAGE_SIGNATURES = {
    "python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"],
    "go": ["go.mod", "go.sum"],
    "javascript": ["package.json"],
    "typescript": ["tsconfig.json"],
    "rust": ["Cargo.toml"],
    "ruby": ["Gemfile"],
    "java": ["pom.xml", "build.gradle"],
}

ENV_VAR_PATTERNS = {
    "python": re.compile(r"""os\.(?:environ(?:\[['"]|\.get\(['"])(\w+)|getenv\(['"](\w+))"""),
    "go": re.compile(r"""os\.Getenv\(['"](\w+)['"]"""),
    "javascript": re.compile(r"""process\.env\.([A-Z_][A-Z0-9_]*)"""),
    "java": re.compile(r"""System\.getenv\(['"](\w+)['"]"""),
    "ruby": re.compile(r"""ENV\[['"](\w+)['"]"""),
    "rust": re.compile(r"""(?:std::)?env::var\(['"](\w+)['"]"""),
}

ENV_VAR_FILE_EXTENSIONS = {
    "python": ["*.py"],
    "go": ["*.go"],
    "javascript": ["*.js", "*.ts"],
    "java": ["*.java"],
    "ruby": ["*.rb"],
    "rust": ["*.rs"],
}

CLI_FRAMEWORK_PATTERNS = {
    "argparse": {
        "pattern": re.compile(r"""add_argument\(['"]-{1,2}([a-zA-Z0-9_-]+)"""),
        "globs": ["**/*.py"],
    },
    "click": {
        "pattern": re.compile(r"""@click\.(?:option|argument)\(['"]-{1,2}([a-zA-Z0-9_-]+)"""),
        "globs": ["**/*.py"],
    },
    "cobra": {
        "pattern": re.compile(
            r"""Flags\(\)\.(?:String|Bool|Int|Duration)\w*\(['"]([a-zA-Z0-9_-]+)"""
        ),
        "globs": ["**/*.go"],
    },
    "clap": {"pattern": re.compile(r"""Arg::new\(['"]([a-zA-Z0-9_-]+)"""), "globs": ["**/*.rs"]},
    "commander": {
        "pattern": re.compile(r"""\.option\(['"]-{1,2}([a-zA-Z0-9_-]+)"""),
        "globs": ["**/*.js", "**/*.ts"],
    },
}

API_ROUTE_PATTERNS = {
    "flask": {
        "pattern": re.compile(r"""@\w+\.route\(['"]([^'"]+)['"](?:.*methods=\[['"](\w+))"""),
        "globs": ["**/*.py"],
    },
    "fastapi": {
        "pattern": re.compile(r"""@\w+\.(get|post|put|patch|delete)\(['"]([^'"]+)['"]"""),
        "globs": ["**/*.py"],
    },
    "express": {
        "pattern": re.compile(r"""(?:app|router)\.(get|post|put|patch|delete)\(['"]([^'"]+)['"]"""),
        "globs": ["**/*.js", "**/*.ts"],
    },
    "go_net_http": {
        "pattern": re.compile(r"""(?:HandleFunc|Handle)\(['"]([^'"]+)['"]"""),
        "globs": ["**/*.go"],
    },
    "gin": {
        "pattern": re.compile(r"""\w+\.(GET|POST|PUT|PATCH|DELETE)\(['"]([^'"]+)['"]"""),
        "globs": ["**/*.go"],
    },
    "spring": {
        "pattern": re.compile(r"""@(Get|Post|Put|Patch|Delete)Mapping\(['"]([^'"]+)['"]"""),
        "globs": ["**/*.java"],
    },
}

CONFIG_ACCESS_PATTERNS = {
    "viper": {
        "pattern": re.compile(r"""viper\.(?:Get\w*)\(['"]([a-zA-Z0-9._-]+)['"]"""),
        "globs": ["**/*.go"],
    },
    "python_config": {
        "pattern": re.compile(r"""config\.get\(['"]([a-zA-Z0-9._-]+)['"]"""),
        "globs": ["**/*.py"],
    },
    "python_settings": {
        "pattern": re.compile(r"""settings\.([A-Z_][A-Z0-9_]*)"""),
        "globs": ["**/*.py"],
    },
}

DATA_MODEL_PATTERNS = {
    "sqlalchemy": {
        "pattern": re.compile(r"""class\s+(\w+)\(\s*(?:db\.Model|Base)\s*\)"""),
        "globs": ["**/*.py"],
    },
    "django": {"pattern": re.compile(r"""class\s+(\w+)\(models\.Model\)"""), "globs": ["**/*.py"]},
    "go_struct": {"pattern": re.compile(r"""type\s+(\w+)\s+struct\s*\{"""), "globs": ["**/*.go"]},
}

# Directories to skip during discovery scans
_SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "vendor",
        "__pycache__",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".eggs",
        "site-packages",
        "dist",
        "build",
        ".bundle",
    }
)

# Regex patterns for AsciiDoc / Markdown parsing
RE_SOURCE_BLOCK = re.compile(r"^\[source(?:,\s*([a-z0-9+\-_]+))?(?:,\s*(.+))?\]\s*$", re.I)
RE_CODE_FENCE = re.compile(r"^```\s*([a-z0-9+\-_]+)?\s*$", re.I)
RE_CODE_DELIM = re.compile(r"^-{4,}\s*$")
RE_LITERAL_DELIM = re.compile(r"^\.{4,}\s*$")
RE_LISTING_BLOCK = re.compile(r"^\[listing\]\s*$", re.I)
RE_HEADING_ADOC = re.compile(r"^(=+)\s+(.+)$")
RE_HEADING_MD = re.compile(r"^(#{1,6})\s+(.+)$")
RE_BLOCK_TITLE = re.compile(r"^\.([A-Za-z][^\n]*?)\s*$")
RE_COMMAND_LINE = re.compile(r"^\$\s+(.+)$")
RE_COMMAND_LINE_CODE = re.compile(r"^[\$#]\s+(.+)$")
RE_INLINE_CODE_PATH = re.compile(r"`([a-zA-Z0-9_\-.\/]+\.[a-z]{2,})`")
RE_FUNCTION_CALL = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
RE_CLASS_DEF = re.compile(r"\b(?:class|interface|struct)\s+([A-Z][a-zA-Z0-9_]*)")
RE_API_ENDPOINT = re.compile(r"(?:GET|POST|PUT|PATCH|DELETE)\s+(/[a-z0-9/_\-{}]+)")
RE_COMMENT_LINE = re.compile(r"^//($|[^/].*)$")
RE_COMMENT_BLOCK = re.compile(r"^/{4,}\s*$")


# ═══════════════════════════════════════════════════════════════════════════
# Extractor
# ═══════════════════════════════════════════════════════════════════════════


class Extractor:
    """Extract technical references from AsciiDoc / Markdown files."""

    def __init__(self):
        self.refs = {
            "commands": [],
            "code_blocks": [],
            "apis": [],
            "configs": [],
            "file_paths": [],
        }

    def extract_files(self, paths: list[str]) -> dict:
        for p in paths:
            path = Path(p)
            if path.is_dir():
                for f in sorted(path.rglob("*")):
                    if f.suffix in (".adoc", ".md"):
                        self._extract_file(f)
            elif path.is_file():
                self._extract_file(path)
            else:
                log.warning("Not found: %s", p)
        return self.refs

    def _extract_file(self, path: Path):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception as exc:
            log.warning("Cannot read %s: %s", path, exc)
            return

        fpath = str(path)
        in_code = False
        code_delim = None
        block = None
        heading = None
        block_title = None
        in_comment = False
        comment_delim = None
        skip_next = False

        for idx, line in enumerate(lines):
            line_num = idx + 1

            if skip_next:
                skip_next = False
                continue

            # Comment blocks
            if RE_COMMENT_BLOCK.match(line):
                if in_comment and line == comment_delim:
                    in_comment = False
                    comment_delim = None
                else:
                    in_comment = True
                    comment_delim = line
                continue
            if in_comment or RE_COMMENT_LINE.match(line):
                continue

            # Headings (outside code blocks)
            if not in_code:
                m = RE_HEADING_ADOC.match(line) or RE_HEADING_MD.match(line)
                if m:
                    heading = m.group(2).strip()
                    continue

            # Block titles
            if RE_BLOCK_TITLE.match(line) and not in_code:
                block_title = line[1:].strip()
                continue

            # Code block start
            if not in_code:
                lang = None
                delim = None

                m = RE_SOURCE_BLOCK.match(line)
                if m:
                    lang = m.group(1) or "text"
                    if idx + 1 < len(lines):
                        nxt = lines[idx + 1]
                        if RE_CODE_DELIM.match(nxt) or RE_LITERAL_DELIM.match(nxt):
                            delim = nxt
                            skip_next = True
                    in_code = True
                    code_delim = delim
                    block = {
                        "file": fpath,
                        "line": line_num,
                        "content_start_line": line_num + (2 if skip_next else 1),
                        "language": lang,
                        "content": [],
                        "context": block_title or heading,
                    }
                    continue

                if RE_LISTING_BLOCK.match(line):
                    lang = "text"
                    if idx + 1 < len(lines):
                        nxt = lines[idx + 1]
                        if RE_CODE_DELIM.match(nxt) or RE_LITERAL_DELIM.match(nxt):
                            delim = nxt
                            skip_next = True
                    in_code = True
                    code_delim = delim
                    block = {
                        "file": fpath,
                        "line": line_num,
                        "content_start_line": line_num + (2 if skip_next else 1),
                        "language": lang,
                        "content": [],
                        "context": block_title or heading,
                    }
                    continue

                m = RE_CODE_FENCE.match(line)
                if m:
                    lang = m.group(1) or "text"
                    in_code = True
                    code_delim = "```"
                    block = {
                        "file": fpath,
                        "line": line_num,
                        "content_start_line": line_num + 1,
                        "language": lang,
                        "content": [],
                        "context": block_title or heading,
                    }
                    continue

                if RE_CODE_DELIM.match(line):
                    in_code = True
                    code_delim = line
                    block = {
                        "file": fpath,
                        "line": line_num,
                        "content_start_line": line_num + 1,
                        "language": "text",
                        "content": [],
                        "context": block_title or heading,
                    }
                    continue
            else:
                # Inside code block — check for end
                is_end = False
                if code_delim == "```" and line == "```":
                    is_end = True
                elif code_delim and line == code_delim:
                    is_end = True
                elif code_delim is None:
                    if (
                        not line.strip()
                        or RE_SOURCE_BLOCK.match(line)
                        or RE_LISTING_BLOCK.match(line)
                        or RE_HEADING_ADOC.match(line)
                    ):
                        is_end = True

                if is_end and block is not None:
                    block["content"] = "\n".join(block["content"])
                    self.refs["code_blocks"].append(block)
                    self._extract_from_code_block(block, fpath)
                    in_code = False
                    code_delim = None
                    block = None
                    block_title = None
                elif block is not None:
                    block["content"].append(line)
                continue

            # Outside code block — inline references
            # A block title only applies to the immediately following block.
            # If we reach here, the line is not a code block opener, so clear it.
            block_title = None

            # Commands ($ command)
            m = RE_COMMAND_LINE.match(line)
            if m:
                self.refs["commands"].append(
                    {
                        "file": fpath,
                        "line": line_num,
                        "command": m.group(1).strip(),
                        "context": block_title or heading,
                    }
                )

            # Inline code paths
            for m in RE_INLINE_CODE_PATH.finditer(line):
                self.refs["file_paths"].append(
                    {
                        "file": fpath,
                        "line": line_num,
                        "path": m.group(1),
                        "context": heading,
                    }
                )

            # API endpoints
            m = RE_API_ENDPOINT.search(line)
            if m:
                self.refs["apis"].append(
                    {
                        "file": fpath,
                        "line": line_num,
                        "type": "endpoint",
                        "name": m.group(1),
                        "context": heading,
                    }
                )

        # Handle unclosed block
        if in_code and block:
            block["content"] = "\n".join(block["content"])
            self.refs["code_blocks"].append(block)
            self._extract_from_code_block(block, fpath)
            log.warning("Unclosed code block in %s at line %d", fpath, block["line"])

    def _extract_from_code_block(self, block: dict, fpath: str):
        content = block["content"]
        lang = block.get("language", "text")
        ctx = block.get("context")
        content_start = block.get("content_start_line", block["line"])
        content_lines = content.splitlines()

        # Commands from code block lines
        for offset, cline in enumerate(content_lines):
            m = RE_COMMAND_LINE_CODE.match(cline.strip())
            if m:
                prompt = "root" if cline.lstrip().startswith("#") else "user"
                self.refs["commands"].append(
                    {
                        "file": fpath,
                        "line": content_start + offset,
                        "command": m.group(1).strip(),
                        "prompt_type": prompt,
                        "context": ctx,
                    }
                )

        # Function calls
        for m in RE_FUNCTION_CALL.finditer(content):
            name = m.group(1)
            if len(name) < 3 or name.lower() in SKIP_FUNCTIONS:
                continue
            hit_offset = content[: m.start()].count("\n")
            self.refs["apis"].append(
                {
                    "file": fpath,
                    "line": content_start + hit_offset,
                    "type": "function",
                    "name": name,
                    "language": lang,
                    "context": ctx,
                }
            )

        # Class definitions
        for m in RE_CLASS_DEF.finditer(content):
            hit_offset = content[: m.start()].count("\n")
            self.refs["apis"].append(
                {
                    "file": fpath,
                    "line": content_start + hit_offset,
                    "type": "class",
                    "name": m.group(1),
                    "language": lang,
                    "context": ctx,
                }
            )

        # Config keys from YAML/JSON/TOML
        if lang.lower() in ("yaml", "yml", "json", "toml"):
            self._extract_config_keys(content, fpath, content_start, lang, ctx)

    def _extract_config_keys(self, content: str, fpath: str, line_num: int, fmt: str, ctx):
        keys = []
        fl = fmt.lower()
        if fl in ("yaml", "yml"):
            keys = [
                m.group(1) for m in re.finditer(r"^\s*([a-zA-Z_][a-zA-Z0-9_-]*):", content, re.M)
            ]
        elif fl == "json":
            keys = [m.group(1) for m in re.finditer(r'"([a-zA-Z_][a-zA-Z0-9_-]*)"\s*:', content)]
        elif fl == "toml":
            keys = [
                m.group(1) for m in re.finditer(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*=", content, re.M)
            ]

        keys = list(dict.fromkeys(keys))  # dedupe preserving order
        if keys:
            self.refs["configs"].append(
                {
                    "file": fpath,
                    "line": line_num,
                    "format": fmt,
                    "keys": keys,
                    "context": ctx,
                }
            )


# ═══════════════════════════════════════════════════════════════════════════
# Search — validate extracted references against code repositories
# ═══════════════════════════════════════════════════════════════════════════


def classify_command_scope(cmd: str, repo_paths: list[str]) -> str:
    """Classify a command as external, in-scope, or unknown."""
    binary = cmd.split()[0].split("/")[-1]
    if binary in EXTERNAL_COMMANDS:
        return "external"
    for rp in repo_paths:
        repo = Path(rp)
        for pattern in [f"**/{binary}", f"**/bin/{binary}", f"**/cmd/{binary}/**"]:
            if list(repo.glob(pattern)):
                return "in-scope"
    return "unknown"


def git_log_search(term: str, repo_path: str, max_results: int = 5) -> list[str]:
    """Search git log for mentions of a term (renames, deprecations)."""
    try:
        result = subprocess.run(
            ["git", "log", "--all", "--oneline", f"--grep={term}", f"-{max_results}"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return []


def find_files_matching(pattern: str, repo_paths: list[str]) -> list[str]:
    """Find files matching a glob pattern across repos."""
    matches = []
    for rp in repo_paths:
        matches.extend(str(p) for p in Path(rp).rglob(pattern) if p.is_file())
    return matches


def discover_cli_definitions(binary: str, repo_paths: list[str]) -> dict | None:
    """Find argparse/click/cobra CLI definitions for a binary."""
    patterns_by_framework = {
        "argparse": r"add_argument\(['\"]--?([a-zA-Z0-9_-]+)",
        "click": r"@click\.(?:option|argument)\(['\"]--?([a-zA-Z0-9_-]+)",
        "cobra": r"Flags\(\)\.(?:String|Bool|Int|StringVar|BoolVar)\w*\(['\"]([a-zA-Z0-9_-]+)",
    }
    for rp in repo_paths:
        repo = Path(rp)
        candidates = []
        for pat in [
            f"{binary}.py",
            f"{binary}/**/*.py",
            f"cmd/{binary}/*.go",
            "cli.py",
            "main.py",
            "cli/*.py",
            "__main__.py",
        ]:
            candidates.extend(repo.rglob(pat))

        for cand in candidates[:10]:
            try:
                src = cand.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for framework, pattern in patterns_by_framework.items():
                flags = re.findall(pattern, src)
                if flags:
                    return {
                        "framework": framework,
                        "file": str(cand),
                        "known_flags": sorted(set(flags)),
                    }
    return None


def discover_schemas(repo_paths: list[str]) -> list[dict]:
    """Find schema/config files in repos."""
    schemas = []
    schema_patterns = [
        "*.schema.json",
        "schema.json",
        "config.schema.*",
        "*-schema.yaml",
        "*-schema.yml",
        "values.yaml",
        "default.yaml",
        "defaults.yaml",
        "config.yaml",
        "config.yml",
        "config.json",
        "example.yaml",
        "example.yml",
        "example.json",
    ]
    for rp in repo_paths:
        repo = Path(rp)
        for pat in schema_patterns:
            for match in repo.rglob(pat):
                if match.is_file() and ".git" not in match.parts:
                    try:
                        content = match.read_text(encoding="utf-8", errors="replace")
                        keys = []
                        suffix = match.suffix.lower()
                        if suffix in (".yaml", ".yml"):
                            keys = re.findall(r"^\s*([a-zA-Z_][a-zA-Z0-9_-]*):", content, re.M)
                        elif suffix == ".json":
                            keys = re.findall(r'"([a-zA-Z_][a-zA-Z0-9_-]*)"\s*:', content)
                        elif suffix == ".toml":
                            keys = re.findall(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*=", content, re.M)
                        keys = list(dict.fromkeys(keys))
                        if keys:
                            schemas.append(
                                {
                                    "file": str(match),
                                    "format": suffix.lstrip("."),
                                    "keys": keys,
                                }
                            )
                    except Exception:
                        continue
    return schemas


def search_commands(commands: list[dict], repo_paths: list[str]) -> tuple[list[dict], list[dict]]:
    """Search repos for command references. Returns (results, discovered_cli_defs)."""
    results = []
    cli_cache = {}
    discovered_cli_defs = []

    for cmd_ref in commands:
        cmd = cmd_ref.get("command", "")
        parts = cmd.split()
        if not parts:
            continue

        binary = parts[0].split("/")[-1]
        scope = classify_command_scope(cmd, repo_paths)

        result = {
            **cmd_ref,
            "found": False,
            "scope": scope,
            "cli_validation": None,
            "git_evidence": [],
        }

        if scope == "external":
            result["found"] = True
            results.append(result)
            continue

        # Check if binary exists in repo
        for rp in repo_paths:
            matches = list(Path(rp).rglob(binary))
            if matches:
                result["found"] = True
                break

        # CLI flag validation
        flags = [p for p in parts[1:] if p.startswith("-")]
        if flags:
            if binary not in cli_cache:
                cli_cache[binary] = discover_cli_definitions(binary, repo_paths)
            cli_def = cli_cache[binary]
            if cli_def:
                known = set(cli_def["known_flags"])
                doc_flags = set(f.lstrip("-") for f in flags)
                unknown = sorted(doc_flags - known)
                valid = sorted(doc_flags & known)
                result["cli_validation"] = {
                    "unknown_flags": unknown,
                    "valid_flags": valid,
                    "known_flags": cli_def["known_flags"],
                    "framework": cli_def["framework"],
                    "definition_file": cli_def["file"],
                }

        # Git evidence for not-found or unknown scope
        if not result["found"] or scope == "unknown":
            for rp in repo_paths:
                evidence = git_log_search(binary, rp)
                if evidence:
                    result["git_evidence"].extend(evidence)

        results.append(result)

    # Collect unique CLI definitions discovered
    for cli_def in cli_cache.values():
        if cli_def:
            discovered_cli_defs.append(cli_def)

    return results, discovered_cli_defs


def search_code_blocks(code_blocks: list[dict], repo_paths: list[str]) -> list[dict]:
    """Search repos for code block content matches."""
    results = []
    for block in code_blocks:
        content = block.get("content", "")
        lines = [
            ln.strip()
            for ln in content.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if not lines:
            results.append({**block, "found": False, "matches": []})
            continue

        first_line = lines[0]
        if first_line.startswith(("$ ", "# ")):
            first_line = first_line[2:]

        matches = []
        for rp in repo_paths:
            try:
                result = subprocess.run(
                    [
                        "grep",
                        "-rl",
                        "--include=*.py",
                        "--include=*.go",
                        "--include=*.java",
                        "--include=*.rb",
                        "--include=*.js",
                        "--include=*.ts",
                        "--include=*.yaml",
                        "--include=*.yml",
                        "--include=*.json",
                        "-F",
                        first_line[:80],
                        rp,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.stdout.strip():
                    for f in result.stdout.strip().splitlines()[:5]:
                        matches.append({"file": f, "type": "first_line"})
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        identifiers = set()
        for ln in lines:
            identifiers.update(re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b", ln))
        identifiers -= SKIP_FUNCTIONS

        results.append(
            {
                **block,
                "found": len(matches) > 0,
                "matches": matches,
                "identifiers": sorted(identifiers)[:20],
            }
        )

    return results


def search_apis(apis: list[dict], repo_paths: list[str]) -> list[dict]:
    """Search repos for API/function/class/endpoint references."""
    results = []
    for api_ref in apis:
        name = api_ref.get("name", "")
        api_type = api_ref.get("type", "function")
        matches = []

        for rp in repo_paths:
            if api_type == "class":
                patterns = [f"class {name}", f"type {name} struct"]
            elif api_type == "endpoint":
                patterns = [name]
            else:
                patterns = [
                    f"def {name}",
                    f"func {name}",
                    f"function {name}",
                    f"fn {name}",
                    f"void {name}",
                ]

            for pattern in patterns:
                try:
                    result = subprocess.run(
                        [
                            "grep",
                            "-rn",
                            "--include=*.py",
                            "--include=*.go",
                            "--include=*.java",
                            "--include=*.rb",
                            "--include=*.js",
                            "--include=*.ts",
                            "--include=*.rs",
                            "-F" if api_type == "endpoint" else "-E",
                            pattern,
                            rp,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.stdout.strip():
                        for line in result.stdout.strip().splitlines()[:3]:
                            if api_type == "endpoint":
                                match_type = "endpoint"
                            elif any(kw in pattern for kw in ["def ", "func ", "class ", "type "]):
                                match_type = "definition"
                            else:
                                match_type = "usage"
                            matches.append({"match": line.strip(), "type": match_type})
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

        git_evidence = []
        if not matches:
            for rp in repo_paths:
                git_evidence.extend(git_log_search(name, rp))

        results.append(
            {
                **api_ref,
                "found": len(matches) > 0,
                "matches": matches[:5],
                "git_evidence": git_evidence,
            }
        )

    return results


def search_configs(configs: list[dict], repo_paths: list[str]) -> tuple[list[dict], list[dict]]:
    """Search repos for configuration key references. Returns (results, discovered_schemas)."""
    schemas = discover_schemas(repo_paths)
    results = []

    for cfg_ref in configs:
        doc_keys = set(cfg_ref.get("keys", []))
        result = {
            **cfg_ref,
            "found": False,
            "schema_validation": None,
            "git_evidence": [],
        }

        best_match = None
        best_overlap = 0.0
        for schema in schemas:
            schema_keys = set(schema["keys"])
            overlap = len(doc_keys & schema_keys)
            if overlap > 0:
                ratio = overlap / max(len(doc_keys), 1)
                if ratio > best_overlap:
                    best_overlap = ratio
                    best_match = schema

        if best_match:
            result["found"] = True
            schema_keys = set(best_match["keys"])
            result["schema_validation"] = {
                "matched_schema": best_match["file"],
                "keys_only_in_doc": sorted(doc_keys - schema_keys),
                "keys_only_in_schema": sorted(schema_keys - doc_keys)[:20],
                "overlap_ratio": round(best_overlap, 2),
            }

        if not result["found"]:
            for key in list(doc_keys)[:5]:
                for rp in repo_paths:
                    evidence = git_log_search(key, rp, max_results=3)
                    if evidence:
                        result["git_evidence"].extend(evidence)

        results.append(result)

    return results, schemas


def search_file_paths(file_paths: list[dict], repo_paths: list[str]) -> list[dict]:
    """Search repos for referenced file paths."""
    results = []
    for fp_ref in file_paths:
        ref_path = fp_ref.get("path", "")
        matches = []
        basename = Path(ref_path).name

        for rp in repo_paths:
            repo = Path(rp)
            exact = repo / ref_path
            if exact.exists():
                matches.append({"file": str(exact), "type": "exact"})
                continue
            for m in repo.rglob(basename):
                if m.is_file() and ".git" not in m.parts:
                    matches.append({"file": str(m), "type": "basename"})

        git_evidence = []
        if not matches:
            for rp in repo_paths:
                git_evidence.extend(git_log_search(basename, rp, max_results=3))

        results.append(
            {
                **fp_ref,
                "found": len(matches) > 0,
                "matches": matches[:5],
                "git_evidence": git_evidence,
            }
        )

    return results


def cmd_search(args):
    """Search code repositories for extracted references."""
    refs_path = Path(args.refs_json)
    if not refs_path.exists():
        print(f"ERROR: refs file not found: {args.refs_json}", file=sys.stderr)
        sys.exit(1)

    refs_data = json.loads(refs_path.read_text(encoding="utf-8"))
    refs = refs_data.get("references", refs_data)
    repo_paths = args.repos

    for rp in repo_paths:
        if not Path(rp).is_dir():
            log.warning("Repo path not found: %s", rp)

    cmd_results, discovered_cli_defs = search_commands(refs.get("commands", []), repo_paths)
    cfg_results, discovered_schemas = search_configs(refs.get("configs", []), repo_paths)

    results = {
        "repos": repo_paths,
        "discovered_cli_definitions": discovered_cli_defs,
        "discovered_schemas": [
            {"file": s["file"], "format": s["format"], "key_count": len(s["keys"])}
            for s in discovered_schemas
        ],
        "results": {
            "commands": cmd_results,
            "code_blocks": search_code_blocks(refs.get("code_blocks", []), repo_paths),
            "apis": search_apis(refs.get("apis", []), repo_paths),
            "configs": cfg_results,
            "file_paths": search_file_paths(refs.get("file_paths", []), repo_paths),
        },
    }

    text = json.dumps(results, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Search results written to {args.output}")
        for cat, items in results["results"].items():
            found_count = sum(1 for i in items if i.get("found"))
            print(f"  {cat}: {len(items)} checked, {found_count} found")
    else:
        print(text)


# ═══════════════════════════════════════════════════════════════════════════
# Discover — scan code repos to build feature inventory
# ═══════════════════════════════════════════════════════════════════════════


def detect_languages(repo_paths: list[str]) -> list[str]:
    """Detect programming languages in repos by signature files."""
    found = set()
    for rp in repo_paths:
        repo = Path(rp)
        for lang, signatures in LANGUAGE_SIGNATURES.items():
            for sig in signatures:
                if list(repo.glob(sig)):
                    found.add(lang)
                    break
        # Fallback: check for source files directly
        ext_to_lang = {
            ".py": "python",
            ".go": "go",
            ".js": "javascript",
            ".ts": "typescript",
            ".rs": "rust",
            ".rb": "ruby",
            ".java": "java",
        }
        for ext, lang in ext_to_lang.items():
            if lang not in found:
                for fpath in repo.rglob(f"*{ext}"):
                    if not (_SKIP_DIRS & set(fpath.parts)):
                        found.add(lang)
                        break
    return sorted(found)


def discover_env_vars(repo_paths: list[str]) -> list[dict]:
    """Discover environment variable access in source code."""
    results = []
    seen = set()
    for rp in repo_paths:
        repo = Path(rp)
        for lang, pattern in ENV_VAR_PATTERNS.items():
            for ext in ENV_VAR_FILE_EXTENSIONS.get(lang, []):
                for fpath in repo.rglob(ext):
                    if _SKIP_DIRS & set(fpath.parts):
                        continue
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    for line_idx, line in enumerate(content.splitlines()):
                        if line.lstrip().startswith(("#", "//", "*", "/*")):
                            continue
                        for m in pattern.finditer(line):
                            name = next((g for g in m.groups() if g), None)
                            if not name:
                                continue
                            key = (name, str(fpath), line_idx + 1)
                            if key in seen:
                                continue
                            seen.add(key)
                            results.append(
                                {
                                    "name": name,
                                    "source_file": str(fpath),
                                    "source_line": line_idx + 1,
                                    "access_pattern": lang,
                                }
                            )
    return results


def discover_all_cli_args(repo_paths: list[str]) -> list[dict]:
    """Discover CLI arguments across all entry points in repos."""
    results = []
    seen = set()
    for rp in repo_paths:
        repo = Path(rp)
        for framework, spec in CLI_FRAMEWORK_PATTERNS.items():
            pattern = spec["pattern"]
            for glob_pat in spec["globs"]:
                for fpath in repo.rglob(glob_pat):
                    if _SKIP_DIRS & set(fpath.parts):
                        continue
                    try:
                        src = fpath.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    for m in pattern.finditer(src):
                        name = m.group(1)
                        key = (name, framework)
                        if key in seen:
                            continue
                        seen.add(key)
                        results.append(
                            {
                                "name": name,
                                "source_file": str(fpath),
                                "framework": framework,
                            }
                        )
    return results


def discover_config_keys(repo_paths: list[str]) -> list[dict]:
    """Discover config keys from schema files and code access patterns."""
    results = []
    seen = set()

    # Reuse existing schema discovery
    schemas = discover_schemas(repo_paths)
    for schema in schemas:
        for key in schema["keys"]:
            k = (key, schema["file"])
            if k not in seen:
                seen.add(k)
                results.append(
                    {
                        "key_path": key,
                        "source_file": schema["file"],
                        "format": schema["format"],
                        "source": "schema_file",
                    }
                )

    # Code access patterns
    for rp in repo_paths:
        repo = Path(rp)
        for framework, spec in CONFIG_ACCESS_PATTERNS.items():
            pattern = spec["pattern"]
            for glob_pat in spec["globs"]:
                for fpath in repo.rglob(glob_pat):
                    if _SKIP_DIRS & set(fpath.parts):
                        continue
                    try:
                        src = fpath.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    for m in pattern.finditer(src):
                        key_path = m.group(1)
                        k = (key_path, str(fpath))
                        if k not in seen:
                            seen.add(k)
                            results.append(
                                {
                                    "key_path": key_path,
                                    "source_file": str(fpath),
                                    "format": framework,
                                    "source": "code_access",
                                }
                            )
    return results


def discover_api_endpoints(repo_paths: list[str]) -> list[dict]:
    """Discover API route/endpoint definitions in source code."""
    results = []
    seen = set()
    for rp in repo_paths:
        repo = Path(rp)
        for framework, spec in API_ROUTE_PATTERNS.items():
            pattern = spec["pattern"]
            for glob_pat in spec["globs"]:
                for fpath in repo.rglob(glob_pat):
                    if _SKIP_DIRS & set(fpath.parts):
                        continue
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    for line_idx, line in enumerate(content.splitlines()):
                        m = pattern.search(line)
                        if not m:
                            continue
                        groups = m.groups()
                        # Patterns capture either (path,) or (method, path) or (path, method)
                        if framework in ("flask",):
                            path = groups[0]
                            method = groups[1].upper() if groups[1] else "GET"
                        elif framework in ("fastapi", "express", "gin", "spring"):
                            method = groups[0].upper()
                            path = groups[1]
                        else:  # go_net_http
                            path = groups[0]
                            method = "ANY"
                        key = (method, path, str(fpath))
                        if key in seen:
                            continue
                        seen.add(key)
                        results.append(
                            {
                                "method": method,
                                "path": path,
                                "source_file": str(fpath),
                                "source_line": line_idx + 1,
                                "framework": framework,
                            }
                        )
    return results


def discover_data_models(repo_paths: list[str]) -> list[dict]:
    """Discover ORM/struct/CRD model definitions in source code."""
    results = []
    seen = set()
    for rp in repo_paths:
        repo = Path(rp)
        for model_type, spec in DATA_MODEL_PATTERNS.items():
            pattern = spec["pattern"]
            for glob_pat in spec["globs"]:
                for fpath in repo.rglob(glob_pat):
                    if _SKIP_DIRS & set(fpath.parts):
                        continue
                    try:
                        src = fpath.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    for m in pattern.finditer(src):
                        name = m.group(1)
                        key = (name, str(fpath))
                        if key in seen:
                            continue
                        seen.add(key)
                        results.append(
                            {
                                "name": name,
                                "source_file": str(fpath),
                                "type": model_type,
                            }
                        )
    return results


def compare_inventory_to_refs(inventory: dict, refs: dict) -> dict:
    """Compare discovered inventory against extracted doc references."""
    comparison = {"undocumented": {}, "doc_only": {}}

    # Collect documented names from refs
    doc_env_vars = set()
    for block in refs.get("code_blocks", []):
        content = block.get("content", "")
        for pat in ENV_VAR_PATTERNS.values():
            for m in pat.finditer(content):
                name = next((g for g in m.groups() if g), None)
                if name:
                    doc_env_vars.add(name)

    doc_cli_flags = set()
    for cmd in refs.get("commands", []):
        for part in cmd.get("command", "").split():
            if part.startswith("-"):
                doc_cli_flags.add(part.lstrip("-"))

    doc_config_keys = set()
    for cfg in refs.get("configs", []):
        doc_config_keys.update(cfg.get("keys", []))

    doc_endpoints = set()
    for api in refs.get("apis", []):
        if api.get("type") == "endpoint":
            doc_endpoints.add(api.get("name", ""))

    doc_classes = set()
    for api in refs.get("apis", []):
        if api.get("type") in ("class", "function"):
            doc_classes.add(api.get("name", ""))

    # Inventory names
    inv_env = {item["name"] for item in inventory.get("env_vars", [])}
    inv_cli = {item["name"] for item in inventory.get("cli_args", [])}
    inv_cfg = {item["key_path"] for item in inventory.get("config_keys", [])}
    inv_endpoints = {item["path"] for item in inventory.get("api_endpoints", [])}
    inv_models = {item["name"] for item in inventory.get("data_models", [])}

    # Undocumented = in code but not in docs
    comparison["undocumented"]["env_vars"] = sorted(inv_env - doc_env_vars)
    comparison["undocumented"]["cli_args"] = sorted(inv_cli - doc_cli_flags)
    comparison["undocumented"]["config_keys"] = sorted(inv_cfg - doc_config_keys)
    comparison["undocumented"]["api_endpoints"] = sorted(inv_endpoints - doc_endpoints)
    comparison["undocumented"]["data_models"] = sorted(inv_models - doc_classes)

    # Doc-only = in docs but not in code inventory
    comparison["doc_only"]["env_vars"] = sorted(doc_env_vars - inv_env)
    comparison["doc_only"]["cli_args"] = sorted(doc_cli_flags - inv_cli)
    comparison["doc_only"]["config_keys"] = sorted(doc_config_keys - inv_cfg)
    comparison["doc_only"]["api_endpoints"] = sorted(doc_endpoints - inv_endpoints)
    comparison["doc_only"]["data_models"] = sorted(doc_classes - inv_models)

    return comparison


def cmd_discover(args):
    """Discover features in code repositories and build inventory."""
    repo_paths = args.repos
    for rp in repo_paths:
        if not Path(rp).is_dir():
            log.warning("Repo path not found: %s", rp)

    languages = detect_languages(repo_paths)
    if args.language:
        languages = [lang for lang in args.language.split(",") if lang in languages]

    inventory = {
        "env_vars": discover_env_vars(repo_paths),
        "cli_args": discover_all_cli_args(repo_paths),
        "config_keys": discover_config_keys(repo_paths),
        "api_endpoints": discover_api_endpoints(repo_paths),
        "data_models": discover_data_models(repo_paths),
    }

    output = {
        "repos": repo_paths,
        "languages": languages,
        "inventory": inventory,
        "summary": {k: len(v) for k, v in inventory.items()},
    }

    # Optional comparison against extracted doc refs
    if args.refs_json:
        refs_path = Path(args.refs_json)
        if refs_path.exists():
            refs_data = json.loads(refs_path.read_text(encoding="utf-8"))
            refs = refs_data.get("references", refs_data)
            output["comparison"] = compare_inventory_to_refs(inventory, refs)
        else:
            log.warning("Refs file not found: %s", args.refs_json)

    text = json.dumps(output, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Inventory written to {args.output}")
        for k, v in inventory.items():
            print(f"  {k}: {len(v)}")
        if "comparison" in output:
            undoc = output["comparison"]["undocumented"]
            total = sum(len(v) for v in undoc.values())
            print(f"  undocumented features: {total}")
    else:
        print(text)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def cmd_extract(args):
    extractor = Extractor()
    refs = extractor.extract_files(args.files)
    output = {
        "summary": {k: len(v) for k, v in refs.items()},
        "references": refs,
    }
    text = json.dumps(output, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Extracted references to {args.output}")
        for k, v in refs.items():
            print(f"  {k}: {len(v)}")
    else:
        print(text)


def main():
    parser = argparse.ArgumentParser(
        description="Extract technical references from documentation files.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # extract
    p_ext = sub.add_parser("extract", help="Extract technical references from doc files")
    p_ext.add_argument("files", nargs="+", help="AsciiDoc/Markdown files or directories")
    p_ext.add_argument("-o", "--output", help="Write JSON to file instead of stdout")

    # search
    p_search = sub.add_parser("search", help="Search code repos for extracted references")
    p_search.add_argument("refs_json", help="Path to extracted refs JSON (from extract)")
    p_search.add_argument("repos", nargs="+", help="Paths to cloned code repositories")
    p_search.add_argument("-o", "--output", help="Write JSON to file instead of stdout")

    # discover
    p_discover = sub.add_parser("discover", help="Discover features in code repos")
    p_discover.add_argument("repos", nargs="+", help="Paths to code repositories")
    p_discover.add_argument("--refs-json", help="Extracted refs JSON for comparison")
    p_discover.add_argument("-o", "--output", help="Write JSON to file instead of stdout")
    p_discover.add_argument("--language", help="Comma-separated language filter")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "discover":
        cmd_discover(args)


if __name__ == "__main__":
    main()
