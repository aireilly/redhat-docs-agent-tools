#!/usr/bin/env python3
"""Scan plugin scripts for software dependencies and output structured JSON."""

import ast
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"
OUTPUT_FILE = REPO_ROOT / "scripts" / "deps.json"

# Python stdlib top-level module names (3.9+).
# Generated via sorted(sys.stdlib_module_names) and trimmed to public names.
# Update when bumping the minimum Python version.
STDLIB_MODULES = {
    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
    "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
    "binhex", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb",
    "chunk", "cmath", "cmd", "code", "codecs", "codeop", "collections",
    "colorsys", "compileall", "concurrent", "configparser", "contextlib",
    "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv",
    "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
    "difflib", "dis", "distutils", "doctest", "email", "encodings",
    "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
    "fnmatch", "fractions", "ftplib", "functools", "gc", "getopt",
    "getpass", "gettext", "glob", "grp", "gzip", "hashlib", "heapq",
    "hmac", "html", "http", "idlelib", "imaplib", "imghdr", "imp",
    "importlib", "inspect", "io", "ipaddress", "itertools", "json",
    "keyword", "lib2to3", "linecache", "locale", "logging", "lzma",
    "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
    "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
    "numbers", "operator", "optparse", "os", "ossaudiodev", "pathlib",
    "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
    "plistlib", "poplib", "posix", "posixpath", "pprint", "profile",
    "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc",
    "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
    "selectors", "shelve", "shlex", "shutil", "signal", "site",
    "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
    "sqlite3", "sre_compile", "sre_constants", "sre_parse", "ssl",
    "stat", "statistics", "string", "stringprep", "struct", "subprocess",
    "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
    "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
    "threading", "time", "timeit", "tkinter", "token", "tokenize",
    "tomllib", "trace", "traceback", "tracemalloc", "tty", "turtle",
    "turtledemo", "types", "typing", "unicodedata", "unittest", "urllib",
    "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
    "zipapp", "zipfile", "zipimport", "zlib",
    # common internal/private prefixes to skip
    "_thread", "__future__",
}

# Maps Python import names to pip package names where they differ.
IMPORT_TO_PACKAGE = {
    "bs4": "beautifulsoup4",
    "html2text": "html2text",
    "jira": "jira",
    "github": "PyGithub",
    "gitlab": "python-gitlab",
    "yaml": "pyyaml",
    "pptx": "python-pptx",
    "ratelimit": "ratelimit",
    "requests": "requests",
    "urllib3": "urllib3",
}

# Ruby gems detected by CLI command name in shell scripts or require in .rb files.
KNOWN_GEMS = {
    "asciidoctor": "asciidoctor",
    "asciidoctor-reducer": "asciidoctor-reducer",
}

# Ruby stdlib modules to ignore when scanning require statements.
RUBY_STDLIB = {
    "abbrev", "base64", "benchmark", "bigdecimal", "cgi", "csv", "date",
    "delegate", "digest", "drb", "English", "erb", "etc", "fcntl", "fiddle",
    "fileutils", "find", "forwardable", "io/console", "io/nonblock",
    "io/wait", "ipaddr", "json", "logger", "monitor", "mutex_m", "net/http",
    "net/https", "net/pop", "net/smtp", "nkf", "observer", "open-uri",
    "open3", "openssl", "optparse", "ostruct", "pathname", "pp", "prettyprint",
    "pstore", "psych", "readline", "reline", "resolv", "rexml", "rinda",
    "securerandom", "set", "shellwords", "singleton", "socket", "stringio",
    "strscan", "tempfile", "time", "timeout", "tmpdir", "tsort", "un",
    "uri", "weakref", "yaml", "zlib",
}

# System tools detected by command name in shell scripts.
KNOWN_SYSTEM_TOOLS = {"vale", "jq", "curl", "gcloud", "gh", "glab"}

# System tools that are always included even if not detected in scripts.
# These are user-facing prerequisites used via Python libraries or CLI.
ALWAYS_INCLUDE_SYSTEM = {"gcloud", "gh", "glab"}


def scan_python_imports(filepath: Path) -> set[str]:
    """Parse a Python file with ast and return top-level import names."""
    try:
        tree = ast.parse(filepath.read_text(), filename=str(filepath))
    except SyntaxError:
        print(f"WARNING: syntax error in {filepath}, skipping", file=sys.stderr)
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


def scan_ruby_requires(filepath: Path) -> set[str]:
    """Scan a Ruby file for require statements that match known gems."""
    content = filepath.read_text()
    found = set()
    for match in re.finditer(r"require\s+['\"]([^'\"]+)['\"]", content):
        mod = match.group(1)
        if mod in RUBY_STDLIB:
            continue
        # Check if the required module maps to a known gem
        for gem_cmd, gem_name in KNOWN_GEMS.items():
            if mod == gem_cmd or mod.startswith(gem_cmd + "/"):
                found.add(gem_name)
    return found


def scan_shell_gems(filepath: Path) -> set[str]:
    """Scan a shell script for Ruby gem invocations."""
    content = filepath.read_text()
    found = set()
    for cmd, gem_name in KNOWN_GEMS.items():
        # Match command invocations: at start of line, after &&, after |, after $( , or after !
        if re.search(rf'(?:^|&&|\||\$\(|!)\s*{re.escape(cmd)}\b', content, re.MULTILINE):
            found.add(gem_name)
        # Also match gem install commands
        if re.search(rf'gem\s+install\s+.*\b{re.escape(gem_name)}\b', content):
            found.add(gem_name)
    return found


def scan_shell_system_tools(filepath: Path) -> set[str]:
    """Scan a shell script for known system tool invocations."""
    content = filepath.read_text()
    found = set()
    for tool in KNOWN_SYSTEM_TOOLS:
        # Match tool invocations (not inside strings or comments on same line heuristically)
        if re.search(rf'(?:^|&&|\||\$\(|!)\s*{re.escape(tool)}\b', content, re.MULTILINE):
            found.add(tool)
    return found


def relative_path(filepath: Path) -> str:
    """Return a repo-relative POSIX path string."""
    return str(filepath.relative_to(REPO_ROOT))


def scan_all() -> dict:
    """Walk plugins/ and collect all dependencies."""
    python_deps: dict[str, list[str]] = {}   # package_name -> [found_in paths]
    ruby_deps: dict[str, list[str]] = {}     # gem_name -> [found_in paths]
    system_deps: dict[str, list[str]] = {}   # tool_name -> [found_in paths]

    # Seed always-included system tools (user-facing prerequisites)
    for tool in ALWAYS_INCLUDE_SYSTEM:
        system_deps.setdefault(tool, [])

    if not PLUGINS_DIR.is_dir():
        print("WARNING: plugins/ directory not found", file=sys.stderr)
        return {"python": [], "ruby": [], "system": []}

    for py_file in sorted(PLUGINS_DIR.rglob("*.py")):
        imports = scan_python_imports(py_file)
        for imp in imports:
            if imp.startswith("_") or imp in STDLIB_MODULES:
                continue
            if imp in IMPORT_TO_PACKAGE:
                pkg = IMPORT_TO_PACKAGE[imp]
                python_deps.setdefault(pkg, []).append(relative_path(py_file))
            else:
                print(f"WARNING: unknown import '{imp}' in {py_file}, skipping", file=sys.stderr)

    for rb_file in sorted(PLUGINS_DIR.rglob("*.rb")):
        rel = relative_path(rb_file)
        for gem in scan_ruby_requires(rb_file):
            ruby_deps.setdefault(gem, []).append(rel)

    for sh_file in sorted(PLUGINS_DIR.rglob("*.sh")):
        rel = relative_path(sh_file)
        for gem in scan_shell_gems(sh_file):
            ruby_deps.setdefault(gem, []).append(rel)
        for tool in scan_shell_system_tools(sh_file):
            system_deps.setdefault(tool, []).append(rel)

    # Build sorted output
    result = {
        "python": sorted(
            [{"package": pkg, "import_name": next(
                (k for k, v in IMPORT_TO_PACKAGE.items() if v == pkg), pkg
            ), "found_in": sorted(paths)} for pkg, paths in python_deps.items()],
            key=lambda x: x["package"].lower(),
        ),
        "ruby": sorted(
            [{"gem": gem, "found_in": sorted(paths)} for gem, paths in ruby_deps.items()],
            key=lambda x: x["gem"],
        ),
        "system": sorted(
            [{"tool": tool, "found_in": sorted(paths)} for tool, paths in system_deps.items()],
            key=lambda x: x["tool"],
        ),
    }
    return result


def main():
    result = scan_all()
    OUTPUT_FILE.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {OUTPUT_FILE}")
    print(f"  Python packages: {len(result['python'])}")
    print(f"  Ruby gems:       {len(result['ruby'])}")
    print(f"  System tools:    {len(result['system'])}")


if __name__ == "__main__":
    main()
