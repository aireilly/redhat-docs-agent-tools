#!/usr/bin/env python3
"""
code_scanner.py — Extract technical references from documentation files and
validate them against cloned code repositories.

Replaces extract_tech_references.rb + search_tech_references.rb with a single
Python script.  Two subcommands:

    python3 code_scanner.py extract <files...> --output refs.json
    python3 code_scanner.py search  refs.json <repo_paths...> --output results.json
"""

import argparse
import json
import logging
import re
import shlex
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
    "sudo su dnf yum rpm apt dpkg pip pip3 npm yarn gem bundle cargo "
    "systemctl journalctl firewall-cmd nmcli ip ss curl wget scp ssh rsync "
    "cat head tail grep sed awk find xargs sort uniq wc tee tr cut "
    "cp mv rm mkdir chmod chown ln tar gzip gunzip zip unzip "
    "git svn docker podman buildah skopeo "
    "oc kubectl helm kustomize "
    "ansible ansible-playbook ansible-galaxy "
    "make cmake gcc g++ javac python python3 ruby node go rustc "
    "cd ls echo printf export source test set unset read "
    "openssl keytool certbot "
    "mount umount fdisk parted lsblk blkid "
    "useradd usermod groupadd passwd chpasswd "
    "crontab at "
    "vi vim nano emacs "
    "man info help "
    "less more pg "
    "ps kill top htop "
    "nc nmap tcpdump "
    "date cal uptime hostname uname whoami id "
    "env printenv "
    "true false exit "
    "subscription-manager yum-config-manager dnf5 "
    "virsh virt-install qemu-img qemu-system-x86_64 "
    "ssh-keygen ssh-copy-id ssh-add "
    "jq yq xmllint "
    "base64 sha256sum md5sum "
    "diff patch "
    "systemd-analyze loginctl timedatectl localectl hostnamectl".split()
)

SKIP_DIRS = frozenset(
    ".git node_modules vendor __pycache__ .tox .eggs dist build".split()
)

CONFIG_EXTENSIONS = (".yaml", ".yml", ".json", ".toml", ".conf", ".cfg", ".ini", ".properties")

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
RE_API_ENDPOINT = re.compile(r"(?:GET|POST|PUT|PATCH|DELETE)?\s*(/[a-z0-9/_\-{}]+)")
RE_COMMENT_LINE = re.compile(r"^//($|[^/].*)$")
RE_COMMENT_BLOCK = re.compile(r"^/{4,}\s*$")

# CLI definition patterns
FUNC_DEF_PATTERNS = [
    r"\bdef\s+{name}\b",
    r"\bfunc\s+{name}\b",
    r"\bfunction\s+{name}\b",
    r"\b{name}\s*=\s*(?:function|=>|\()",
    r"\b(?:async\s+)?(?:def|fn)\s+{name}\b",
]
CLASS_DEF_PATTERNS = [
    r"\bclass\s+{name}\b",
    r"\binterface\s+{name}\b",
    r"\bstruct\s+{name}\b",
    r"\btype\s+{name}\b",
    r"\benum\s+{name}\b",
]


# ═══════════════════════════════════════════════════════════════════════════
# Extract subcommand
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
                        "file": fpath, "line": line_num,
                        "language": lang, "content": [],
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
                        "file": fpath, "line": line_num,
                        "language": lang, "content": [],
                        "context": block_title or heading,
                    }
                    continue

                m = RE_CODE_FENCE.match(line)
                if m:
                    lang = m.group(1) or "text"
                    in_code = True
                    code_delim = "```"
                    block = {
                        "file": fpath, "line": line_num,
                        "language": lang, "content": [],
                        "context": block_title or heading,
                    }
                    continue

                if RE_CODE_DELIM.match(line):
                    in_code = True
                    code_delim = line
                    block = {
                        "file": fpath, "line": line_num,
                        "language": "text", "content": [],
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
                    if not line.strip() or RE_SOURCE_BLOCK.match(line) or RE_LISTING_BLOCK.match(line) or RE_HEADING_ADOC.match(line):
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

            # Commands ($ command)
            m = RE_COMMAND_LINE.match(line)
            if m:
                self.refs["commands"].append({
                    "file": fpath, "line": line_num,
                    "command": m.group(1).strip(),
                    "context": block_title or heading,
                })

            # Inline code paths
            for m in RE_INLINE_CODE_PATH.finditer(line):
                self.refs["file_paths"].append({
                    "file": fpath, "line": line_num,
                    "path": m.group(1), "context": heading,
                })

            # API endpoints
            m = RE_API_ENDPOINT.search(line)
            if m:
                self.refs["apis"].append({
                    "file": fpath, "line": line_num,
                    "type": "endpoint", "name": m.group(1),
                    "context": heading,
                })

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
        line_num = block["line"]

        # Commands from code block lines
        for cline in content.splitlines():
            m = RE_COMMAND_LINE_CODE.match(cline.strip())
            if m:
                prompt = "root" if cline.lstrip().startswith("#") else "user"
                self.refs["commands"].append({
                    "file": fpath, "line": line_num,
                    "command": m.group(1).strip(),
                    "prompt_type": prompt, "context": ctx,
                })

        # Function calls
        for m in RE_FUNCTION_CALL.finditer(content):
            name = m.group(1)
            if len(name) < 3 or name.lower() in SKIP_FUNCTIONS:
                continue
            self.refs["apis"].append({
                "file": fpath, "line": line_num,
                "type": "function", "name": name,
                "language": lang, "context": ctx,
            })

        # Class definitions
        for m in RE_CLASS_DEF.finditer(content):
            self.refs["apis"].append({
                "file": fpath, "line": line_num,
                "type": "class", "name": m.group(1),
                "language": lang, "context": ctx,
            })

        # Config keys from YAML/JSON/TOML
        if lang.lower() in ("yaml", "yml", "json", "toml"):
            self._extract_config_keys(content, fpath, line_num, lang, ctx)

    def _extract_config_keys(self, content: str, fpath: str, line_num: int, fmt: str, ctx):
        keys = []
        fl = fmt.lower()
        if fl in ("yaml", "yml"):
            keys = [m.group(1) for m in re.finditer(r"^\s*([a-zA-Z_][a-zA-Z0-9_-]*):", content, re.M)]
        elif fl == "json":
            keys = [m.group(1) for m in re.finditer(r'"([a-zA-Z_][a-zA-Z0-9_-]*)"\s*:', content)]
        elif fl == "toml":
            keys = [m.group(1) for m in re.finditer(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*=", content, re.M)]

        keys = list(dict.fromkeys(keys))  # dedupe preserving order
        if keys:
            self.refs["configs"].append({
                "file": fpath, "line": line_num,
                "format": fmt, "keys": keys, "context": ctx,
            })


# ═══════════════════════════════════════════════════════════════════════════
# Search subcommand
# ═══════════════════════════════════════════════════════════════════════════


class Searcher:
    """Search cloned repos for evidence matching extracted references."""

    def __init__(self):
        self.results = []
        self.counters = {"total": 0, "found": 0, "not_found": 0}
        self.schemas: dict = {}
        self.cli_defs: dict = {}

    def search(self, refs_data: dict, repo_paths: list[Path]) -> dict:
        references = refs_data.get("references", {})

        self.schemas = self._discover_schemas(repo_paths)
        self.cli_defs = self._discover_cli_definitions(repo_paths)
        log.info("Discovered %d schema files, %d CLI entry points", len(self.schemas), len(self.cli_defs))

        self._search_commands(references.get("commands", []), repo_paths)
        self._search_code_blocks(references.get("code_blocks", []), repo_paths)
        self._search_apis(references.get("apis", []), repo_paths)
        self._search_configs(references.get("configs", []), repo_paths)
        self._search_file_paths(references.get("file_paths", []), repo_paths)

        return {
            "search_results": self.results,
            "summary": self.counters,
            "discovered_schemas": list(self.schemas.keys()),
            "discovered_cli_definitions": [
                {"binary": k, "file": v["file"], "subcommands": list(v["subcommands"].keys())}
                for k, v in self.cli_defs.items()
            ],
        }

    # --- Commands -----------------------------------------------------------

    def _search_commands(self, commands: list, repo_paths: list[Path]):
        for idx, cmd in enumerate(commands):
            self.counters["total"] += 1
            ref_id = f"cmd-{idx + 1}"
            raw = cmd.get("command", "")
            log.debug("Searching command: %s", raw)

            try:
                parts = shlex.split(raw, posix=True) if raw else []
            except ValueError:
                parts = raw.split() if raw else []
            if parts and parts[0] == "sudo":
                parts.pop(0)
            binary = parts[0] if parts else ""
            flags = [p for p in parts if p.startswith("-")]

            scope = self._classify_scope(binary, repo_paths)
            matches, git_evidence, flags_checked, cli_validation = [], [], {}, None

            if scope != "external":
                for repo in repo_paths:
                    if not repo.is_dir():
                        continue
                    escaped = re.escape(binary)

                    for p in self._find_by_name(repo, binary):
                        matches.append({"repo": str(repo), "path": p, "type": "binary", "context": f"Binary found: {p}"})

                    for hit in self._grep_repo(repo, rf"\b{escaped}\b", max_results=10):
                        matches.append({"repo": str(repo), "path": hit["path"], "type": "grep", "context": hit["context"]})

                    for entry in self._git_log_search(repo, binary):
                        git_evidence.append({"repo": str(repo), "type": "log", "context": entry})

                    for flag in flags:
                        if len(flag) < 2:
                            continue
                        hits = self._grep_repo(repo, re.escape(flag), max_results=3)
                        flags_checked[flag] = bool(hits)

                if binary in self.cli_defs:
                    cli_validation = self._validate_cli(parts[1:], self.cli_defs[binary])

            found = bool(matches)
            self.counters["found" if found else "not_found"] += 1
            self.results.append({
                "ref_id": ref_id, "category": "command", "scope": scope,
                "reference": cmd,
                "results": {
                    "found": found, "matches": matches,
                    "git_evidence": git_evidence,
                    "flags_checked": flags_checked,
                    "cli_validation": cli_validation,
                },
            })

    # --- Code blocks --------------------------------------------------------

    def _search_code_blocks(self, blocks: list, repo_paths: list[Path]):
        for idx, block in enumerate(blocks):
            self.counters["total"] += 1
            ref_id = f"code-{idx + 1}"
            content = block.get("content", "")
            block_lines = [l.strip() for l in content.splitlines() if l.strip()]
            if not block_lines:
                continue

            first_line = block_lines[0]
            identifiers = self._extract_identifiers(content)
            matches = []

            for repo in repo_paths:
                if not repo.is_dir():
                    continue

                if first_line:
                    for hit in self._grep_repo(repo, re.escape(first_line), max_results=5):
                        matches.append({"repo": str(repo), "path": hit["path"], "type": "first_line", "context": hit["context"]})

                if identifiers:
                    found_ids, missing_ids = [], []
                    for ident in identifiers:
                        hits = self._grep_repo(repo, rf"\b{re.escape(ident)}\b", max_results=1)
                        (found_ids if hits else missing_ids).append(ident)
                    total = len(identifiers)
                    ratio = round(len(found_ids) / total, 2) if total else 0.0
                    matches.append({
                        "repo": str(repo), "path": None, "type": "identifier_ratio",
                        "context": f"{len(found_ids)}/{total} identifiers found ({ratio})",
                        "found_identifiers": found_ids, "missing_identifiers": missing_ids,
                    })

            found = any(m["type"] != "identifier_ratio" for m in matches) or any("/" in (m.get("context") or "") for m in matches if m["type"] == "identifier_ratio")
            self.counters["found" if found else "not_found"] += 1
            self.results.append({
                "ref_id": ref_id, "category": "code_block",
                "reference": block,
                "results": {"found": found, "matches": matches, "git_evidence": []},
            })

    # --- APIs ---------------------------------------------------------------

    def _search_apis(self, apis: list, repo_paths: list[Path]):
        for idx, api in enumerate(apis):
            self.counters["total"] += 1
            ref_id = f"api-{idx + 1}"
            api_type = api.get("type", "function")
            name = api.get("name", "")
            if not name or len(name) < 2:
                continue

            matches, git_evidence = [], []

            for repo in repo_paths:
                if not repo.is_dir():
                    continue

                if api_type == "function":
                    for pat_tmpl in FUNC_DEF_PATTERNS:
                        pat = pat_tmpl.replace("{name}", re.escape(name))
                        for hit in self._grep_repo(repo, pat, max_results=5):
                            matches.append({"repo": str(repo), "path": hit["path"], "type": "definition", "context": hit["context"]})
                    for hit in self._grep_repo(repo, rf"\b{re.escape(name)}\b", max_results=5):
                        matches.append({"repo": str(repo), "path": hit["path"], "type": "usage", "context": hit["context"]})

                elif api_type == "class":
                    for pat_tmpl in CLASS_DEF_PATTERNS:
                        pat = pat_tmpl.replace("{name}", re.escape(name))
                        for hit in self._grep_repo(repo, pat, max_results=5):
                            matches.append({"repo": str(repo), "path": hit["path"], "type": "definition", "context": hit["context"]})

                elif api_type == "endpoint":
                    for hit in self._grep_repo(repo, re.escape(name), max_results=10):
                        matches.append({"repo": str(repo), "path": hit["path"], "type": "endpoint", "context": hit["context"]})

                for entry in self._git_log_search(repo, name):
                    git_evidence.append({"repo": str(repo), "type": "log", "context": entry})

            found = any(m["type"] in ("definition", "endpoint") for m in matches) or bool(matches)
            self.counters["found" if found else "not_found"] += 1
            self.results.append({
                "ref_id": ref_id, "category": "api", "reference": api,
                "results": {"found": found, "matches": matches, "git_evidence": git_evidence},
            })

    # --- Configs ------------------------------------------------------------

    def _search_configs(self, configs: list, repo_paths: list[Path]):
        for idx, config in enumerate(configs):
            self.counters["total"] += 1
            ref_id = f"cfg-{idx + 1}"
            keys = config.get("keys", [])
            fmt = config.get("format", "yaml")

            matches, git_evidence, keys_found = [], [], {}

            exts = self._config_exts(fmt)

            for repo in repo_paths:
                if not repo.is_dir():
                    continue

                cfg_files = []
                for ext in exts:
                    cfg_files.extend(f for f in repo.rglob(f"*{ext}") if not any(d in f.parts for d in SKIP_DIRS))

                for key in keys:
                    key_hit = False
                    for cf in cfg_files:
                        try:
                            if key in cf.read_text(encoding="utf-8", errors="replace"):
                                key_hit = True
                                matches.append({"repo": str(repo), "path": str(cf.relative_to(repo)), "type": "config_key", "key": key, "context": str(cf.name)})
                        except Exception:
                            continue

                    if not key_hit:
                        for hit in self._grep_repo(repo, rf"\b{re.escape(key)}\b", max_results=3):
                            key_hit = True
                            matches.append({"repo": str(repo), "path": hit["path"], "type": "config_key_broad", "key": key, "context": hit["context"]})

                    keys_found[key] = key_hit

                for key in keys:
                    if not keys_found.get(key):
                        for entry in self._git_log_search(repo, key):
                            git_evidence.append({"repo": str(repo), "key": key, "type": "log", "context": entry})

            schema_validation = None
            if self.schemas:
                schema_validation = self._validate_config_schemas(keys)

            found = any(keys_found.values())
            self.counters["found" if found else "not_found"] += 1
            self.results.append({
                "ref_id": ref_id, "category": "config", "reference": config,
                "results": {
                    "found": found, "matches": matches,
                    "git_evidence": git_evidence,
                    "keys_checked": keys_found,
                    "schema_validation": schema_validation,
                },
            })

    # --- File paths ---------------------------------------------------------

    def _search_file_paths(self, paths: list, repo_paths: list[Path]):
        for idx, fp in enumerate(paths):
            self.counters["total"] += 1
            ref_id = f"path-{idx + 1}"
            fpath = fp.get("path", "")
            if not fpath:
                continue

            matches = []
            for repo in repo_paths:
                if not repo.is_dir():
                    continue
                exact = repo / fpath
                if exact.exists():
                    matches.append({"repo": str(repo), "path": fpath, "type": "exact", "context": f"Exact path exists: {fpath}"})
                    continue
                basename = Path(fpath).name
                for found in self._find_by_name(repo, basename):
                    matches.append({"repo": str(repo), "path": found, "type": "basename", "context": f"Found by basename at: {found}"})

            found = bool(matches)
            self.counters["found" if found else "not_found"] += 1
            self.results.append({
                "ref_id": ref_id, "category": "file_path", "reference": fp,
                "results": {"found": found, "matches": matches, "git_evidence": []},
            })

    # --- Scope classification -----------------------------------------------

    def _classify_scope(self, binary: str, repo_paths: list[Path]) -> str:
        if not binary or binary in EXTERNAL_COMMANDS:
            return "external"
        for repo in repo_paths:
            for ep_file in ("pyproject.toml", "setup.cfg", "setup.py", "Cargo.toml", "package.json"):
                ep = repo / ep_file
                if ep.exists():
                    try:
                        if binary in ep.read_text(encoding="utf-8", errors="replace"):
                            return "in-scope"
                    except Exception:
                        continue
        return "unknown"

    # --- Schema discovery ---------------------------------------------------

    def _discover_schemas(self, repo_paths: list[Path]) -> dict:
        schemas = {}
        patterns = ("*schema*.yaml", "*schema*.yml", "*schema*.json", "*_schema.*", "*.schema.*", "*-schema.*")
        for repo in repo_paths:
            if not repo.is_dir():
                continue
            for pat in patterns:
                for sf in repo.rglob(pat):
                    if any(d in sf.parts for d in SKIP_DIRS):
                        continue
                    try:
                        content = sf.read_text(encoding="utf-8", errors="replace")
                        keys = self._extract_all_keys(content, sf.suffix)
                        rel = str(sf.relative_to(repo))
                        schemas[rel] = {"repo": str(repo), "full_path": str(sf), "keys": keys}
                    except Exception:
                        continue
        return schemas

    def _extract_all_keys(self, content: str, ext: str) -> list[str]:
        if ext in (".yaml", ".yml"):
            return list(dict.fromkeys(m.group(1) for m in re.finditer(r"^\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*:", content, re.M)))
        if ext == ".json":
            return list(dict.fromkeys(m.group(1) for m in re.finditer(r'"([a-zA-Z_][a-zA-Z0-9_-]*)"\s*:', content)))
        return []

    def _validate_config_schemas(self, doc_keys: list[str]) -> dict:
        matched = []
        for schema_path, info in self.schemas.items():
            schema_keys = info["keys"]
            if not schema_keys:
                continue
            common = [k for k in doc_keys if k in schema_keys]
            doc_only = [k for k in doc_keys if k not in schema_keys]
            schema_only = [k for k in schema_keys if k not in doc_keys]
            ratio = round(len(common) / len(doc_keys), 2) if doc_keys else 0.0
            if ratio < 0.3:
                continue
            matched.append({
                "schema_file": schema_path, "overlap_ratio": ratio,
                "keys_in_both": common, "keys_only_in_doc": doc_only,
                "keys_only_in_schema": schema_only,
            })
        return {"matched_schemas": sorted(matched, key=lambda s: -s["overlap_ratio"])}

    # --- CLI definition discovery -------------------------------------------

    def _discover_cli_definitions(self, repo_paths: list[Path]) -> dict:
        cli_defs: dict = {}
        for repo in repo_paths:
            if not repo.is_dir():
                continue
            binary_name = self._determine_binary(repo)
            if not binary_name:
                continue

            # Python argparse / click
            for hit in self._grep_repo(repo, r"argparse|add_argument|click\.command|click\.option|click\.argument", max_results=30):
                fpath = repo / hit["path"]
                if not fpath.exists():
                    continue
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                defs = self._extract_python_cli(content, hit["path"])
                if defs:
                    self._merge_cli_defs(cli_defs, binary_name, defs, hit["path"])

            # Go cobra
            for hit in self._grep_repo(repo, r"cobra\.Command|pflag|flag\.String|flag\.Bool", max_results=20):
                fpath = repo / hit["path"]
                if not fpath.exists():
                    continue
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                defs = self._extract_go_cobra(content, hit["path"])
                if defs:
                    self._merge_cli_defs(cli_defs, binary_name, defs, hit["path"])

        return cli_defs

    @staticmethod
    def _merge_cli_defs(cli_defs: dict, binary: str, defs: dict, rel_path: str):
        if binary in cli_defs:
            cli_defs[binary]["subcommands"].update(defs["subcommands"])
            existing = set(cli_defs[binary]["flags"])
            cli_defs[binary]["flags"].extend(f for f in defs["flags"] if f not in existing)
        else:
            cli_defs[binary] = {**defs, "file": rel_path}

    @staticmethod
    def _extract_python_cli(content: str, fpath: str) -> dict | None:
        flags, subcmds = [], {}

        for m in re.finditer(r"add_argument\(\s*['\"](-{1,2}[a-zA-Z0-9_-]+)['\"]", content):
            flags.append(m.group(1))
        for m in re.finditer(r"add_argument\(\s*['\"](-[a-zA-Z])['\"],\s*['\"](-{2}[a-zA-Z0-9_-]+)['\"]", content):
            flags.extend([m.group(1), m.group(2)])
        for m in re.finditer(r"add_parser\(\s*['\"]([a-zA-Z0-9_-]+)['\"]", content):
            subcmds[m.group(1)] = {"source": fpath}
        for m in re.finditer(r"@click\.option\(\s*['\"](-{1,2}[a-zA-Z0-9_-]+)['\"]", content):
            flags.append(m.group(1))
        for m in re.finditer(r"@click\.argument\(\s*['\"]([a-zA-Z0-9_-]+)['\"]", content):
            subcmds[m.group(1)] = {"source": fpath, "type": "argument"}
        for m in re.finditer(r"@(?:click\.command|click\.group)\(\s*(?:name\s*=\s*)?['\"]([a-zA-Z0-9_-]+)['\"]", content):
            subcmds[m.group(1)] = {"source": fpath}

        if not flags and not subcmds:
            return None
        return {"flags": list(dict.fromkeys(flags)), "subcommands": subcmds}

    @staticmethod
    def _extract_go_cobra(content: str, fpath: str) -> dict | None:
        flags, subcmds = [], {}

        for m in re.finditer(
            r"\.(?:Flags|PersistentFlags)\(\)\.(?:String|Bool|Int|Float|Duration|StringSlice)(?:Var|VarP|P)?\(\s*(?:&\w+,\s*)?[\"']([a-zA-Z0-9_-]+)[\"']",
            content,
        ):
            flags.append(f"--{m.group(1)}")
        for m in re.finditer(r'Use:\s*["\']([a-zA-Z0-9_-]+)', content):
            subcmds[m.group(1)] = {"source": fpath}

        if not flags and not subcmds:
            return None
        return {"flags": list(dict.fromkeys(flags)), "subcommands": subcmds}

    def _determine_binary(self, repo: Path) -> str | None:
        # pyproject.toml [project.scripts]
        pyproject = repo / "pyproject.toml"
        if pyproject.exists():
            try:
                in_scripts = False
                for line in pyproject.read_text(encoding="utf-8").splitlines():
                    s = line.strip()
                    if re.match(r"^\[(?:project\.scripts|tool\.poetry\.scripts)\]", s):
                        in_scripts = True
                        continue
                    if s.startswith("[") and in_scripts:
                        in_scripts = False
                        continue
                    if in_scripts:
                        m = re.match(r'^["\']?([a-zA-Z0-9_-]+)["\']?\s*=\s*["\']', s)
                        if m:
                            return m.group(1)
            except Exception:
                pass

        # setup.cfg
        setup_cfg = repo / "setup.cfg"
        if setup_cfg.exists():
            try:
                in_ep, in_cs = False, False
                for line in setup_cfg.read_text(encoding="utf-8").splitlines():
                    s = line.strip()
                    if s == "[options.entry_points]":
                        in_ep = True
                        continue
                    if s.startswith("[") and in_ep:
                        in_ep = in_cs = False
                        continue
                    if in_ep and s == "console_scripts =":
                        in_cs = True
                        continue
                    if in_cs:
                        m = re.match(r"^([a-zA-Z0-9_-]+)\s*=", s)
                        if m:
                            return m.group(1)
            except Exception:
                pass

        # Go cmd/*/main.go
        cmd_dir = repo / "cmd"
        if cmd_dir.is_dir():
            for main_go in cmd_dir.glob("*/main.go"):
                return main_go.parent.name

        return repo.name

    def _validate_cli(self, args: list[str], cli_def: dict) -> dict:
        known_flags = cli_def.get("flags", [])
        known_subcmds = cli_def.get("subcommands", {})

        doc_flags = [a for a in args if a.startswith("-")]
        doc_positionals = [a for a in args if not a.startswith("-")]

        valid_flags, unknown_flags = [], []
        for flag in doc_flags:
            norm = flag.split("=")[0]
            (valid_flags if norm in known_flags else unknown_flags).append(norm)

        subcmd_check = None
        first = doc_positionals[0] if doc_positionals else None
        if first and "/" not in first and "." not in first and "<" not in first and not first.startswith(("$", "{")) and known_subcmds:
            subcmd_check = {"name": first, "valid": first in known_subcmds}
            if not subcmd_check["valid"]:
                subcmd_check["known_subcommands"] = list(known_subcmds.keys())

        return {
            "valid": not unknown_flags,
            "known_flags": known_flags, "valid_flags": valid_flags,
            "unknown_flags": unknown_flags, "subcommand_check": subcmd_check,
            "cli_source": cli_def.get("file"),
        }

    # --- Helpers ------------------------------------------------------------

    @staticmethod
    def _grep_repo(repo: Path, pattern: str, max_results: int = 10) -> list[dict]:
        exclude = []
        for d in SKIP_DIRS:
            exclude.extend(["--exclude-dir", d])
        try:
            r = subprocess.run(
                ["grep", "-rnE", *exclude, pattern, str(repo)],
                capture_output=True, text=True, timeout=15,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        hits = []
        for line in (r.stdout or "").splitlines():
            m = re.match(r"^(.+?):(\d+):(.*)$", line)
            if m:
                rel = m.group(1).replace(f"{repo}/", "", 1)
                hits.append({"path": rel, "line": int(m.group(2)), "context": m.group(3).strip()})
                if len(hits) >= max_results:
                    break
        return hits

    @staticmethod
    def _git_log_search(repo: Path, term: str, max_results: int = 5) -> list[str]:
        if not (repo / ".git").is_dir():
            return []
        try:
            r = subprocess.run(
                ["git", "-C", str(repo), "log", "--oneline", "--all", f"-n{max_results}", f"--grep={term}"],
                capture_output=True, text=True, timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
        return [l.strip() for l in (r.stdout or "").splitlines() if l.strip()][:max_results]

    @staticmethod
    def _find_by_name(repo: Path, name: str) -> list[str]:
        if not name:
            return []
        try:
            r = subprocess.run(
                ["find", str(repo), "-name", name,
                 "-not", "-path", "*/.git/*",
                 "-not", "-path", "*/node_modules/*",
                 "-not", "-path", "*/vendor/*"],
                capture_output=True, text=True, timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
        return [l.replace(f"{repo}/", "", 1).strip() for l in (r.stdout or "").splitlines() if l.strip()][:10]

    @staticmethod
    def _extract_identifiers(content: str) -> list[str]:
        ids = []
        for m in re.finditer(r"\b([a-zA-Z_][a-zA-Z0-9_]{2,})\s*\(", content):
            ids.append(m.group(1))
        for m in re.finditer(r"\b(?:class|struct|interface|type)\s+([A-Z][a-zA-Z0-9_]+)", content):
            ids.append(m.group(1))
        for m in re.finditer(r"(?:import|from|require|use)\s+['\"]?([a-zA-Z0-9_.\/\-]+)", content):
            ids.append(m.group(1))
        return list(dict.fromkeys(ids))[:20]

    @staticmethod
    def _config_exts(fmt: str) -> tuple:
        fl = fmt.lower()
        if fl in ("yaml", "yml"):
            return (".yaml", ".yml")
        if fl == "json":
            return (".json",)
        if fl == "toml":
            return (".toml",)
        return CONFIG_EXTENSIONS


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


def cmd_search(args):
    refs_path = Path(args.refs_file)
    if not refs_path.exists():
        print(f"ERROR: References file not found: {args.refs_file}", file=sys.stderr)
        sys.exit(1)
    try:
        refs_data = json.loads(refs_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {args.refs_file}: {e}", file=sys.stderr)
        sys.exit(1)

    repo_paths = [Path(r) for r in args.repo_paths]
    valid = [r for r in repo_paths if r.is_dir()]
    if not valid:
        print("ERROR: No valid repository paths found", file=sys.stderr)
        sys.exit(1)

    searcher = Searcher()
    results = searcher.search(refs_data, valid)
    text = json.dumps(results, indent=2)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        s = results["summary"]
        print(f"Search completed: {args.output}")
        print(f"  Total: {s['total']}  Found: {s['found']}  Not found: {s['not_found']}")
    else:
        print(text)


def main():
    parser = argparse.ArgumentParser(
        description="Extract and validate technical references in documentation against code repositories.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # extract
    p_ext = sub.add_parser("extract", help="Extract technical references from doc files")
    p_ext.add_argument("files", nargs="+", help="AsciiDoc/Markdown files or directories")
    p_ext.add_argument("-o", "--output", help="Write JSON to file instead of stdout")

    # search
    p_search = sub.add_parser("search", help="Search code repos for extracted references")
    p_search.add_argument("refs_file", help="JSON file from extract subcommand")
    p_search.add_argument("repo_paths", nargs="+", help="Cloned repository paths")
    p_search.add_argument("-o", "--output", help="Write JSON to file instead of stdout")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "search":
        cmd_search(args)


if __name__ == "__main__":
    main()
