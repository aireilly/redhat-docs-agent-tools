"""Tests for code_scanner.py extract and search features."""
import json
import sys
import pytest
from pathlib import Path

# Add code_scanner's directory to sys.path so we can import it
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "plugins" / "docs-tools" / "skills" / "docs-review-technical" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from code_scanner import (  # noqa: E402
    Extractor,
    classify_command_scope,
    detect_languages,
    discover_all_cli_args,
    discover_api_endpoints,
    discover_cli_definitions,
    discover_config_keys,
    discover_data_models,
    discover_env_vars,
    discover_schemas,
    compare_inventory_to_refs,
    search_commands,
    search_code_blocks,
    search_apis,
    search_configs,
    search_file_paths,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent
FAKE_REPO = str(FIXTURES_DIR / "fake-repo")
STALE_DOC = str(FIXTURES_DIR / "doc-with-stale-refs.adoc")
SAMPLE_CONCEPT = str(FIXTURES_DIR / "sample-concept.adoc")
SAMPLE_PROCEDURE = str(FIXTURES_DIR / "sample-procedure.adoc")
SAMPLE_REFERENCE = str(FIXTURES_DIR / "sample-reference.md")


# ═══════════════════════════════════════════════════════════════════════════
# Extract tests
# ═══════════════════════════════════════════════════════════════════════════


class TestExtract:
    """Test the Extractor class against fixture files."""

    def test_extract_stale_doc_commands(self):
        ext = Extractor()
        refs = ext.extract_files([STALE_DOC])
        commands = [c["command"] for c in refs["commands"]]
        # External commands from code blocks
        assert any("oc get pods" in c for c in commands)
        assert any("kubectl apply" in c for c in commands)
        assert any("sudo systemctl" in c for c in commands)
        # In-scope commands
        assert any("example-tool deploy --env" in c for c in commands)
        assert any("example-tool deploy --environment" in c for c in commands)

    def test_extract_stale_doc_configs(self):
        ext = Extractor()
        refs = ext.extract_files([STALE_DOC])
        configs = refs["configs"]
        assert len(configs) >= 2
        # YAML config keys
        yaml_cfg = [c for c in configs if c["format"] == "yaml"]
        assert len(yaml_cfg) >= 1
        yaml_keys = yaml_cfg[0]["keys"]
        assert "replicas" in yaml_keys
        assert "maxRetries" in yaml_keys
        # JSON config keys
        json_cfg = [c for c in configs if c["format"] == "json"]
        assert len(json_cfg) >= 1
        json_keys = json_cfg[0]["keys"]
        assert "host" in json_keys
        assert "pool_size" in json_keys

    def test_extract_stale_doc_apis(self):
        ext = Extractor()
        refs = ext.extract_files([STALE_DOC])
        # After fixing RE_API_ENDPOINT to require an HTTP method prefix,
        # bare file paths like /client and /processor should no longer
        # appear as endpoint-type APIs.
        endpoint_names = [a["name"] for a in refs["apis"] if a["type"] == "endpoint"]
        assert not any("/client" in n for n in endpoint_names)
        assert not any("/processor" in n for n in endpoint_names)

    def test_extract_stale_doc_file_paths(self):
        ext = Extractor()
        refs = ext.extract_files([STALE_DOC])
        paths = [f["path"] for f in refs["file_paths"]]
        assert "src/client.py" in paths
        assert "config/defaults.yaml" in paths
        assert "lib/processor.py" in paths
        assert "src/removed_module.py" in paths

    def test_extract_sample_procedure_commands(self):
        ext = Extractor()
        refs = ext.extract_files([SAMPLE_PROCEDURE])
        commands = [c["command"] for c in refs["commands"]]
        assert any("oc login" in c for c in commands)
        assert any("oc create namespace" in c for c in commands)

    def test_extract_sample_concept_configs(self):
        ext = Extractor()
        refs = ext.extract_files([SAMPLE_CONCEPT])
        configs = refs["configs"]
        assert len(configs) >= 1
        keys = configs[0]["keys"]
        assert "replicas" in keys
        assert "logLevel" in keys

    def test_extract_sample_reference_toml(self):
        ext = Extractor()
        refs = ext.extract_files([SAMPLE_REFERENCE])
        configs = refs["configs"]
        toml_cfg = [c for c in configs if c["format"] == "toml"]
        assert len(toml_cfg) >= 1
        keys = toml_cfg[0]["keys"]
        assert "host" in keys
        assert "port" in keys
        assert "pool_size" in keys

    def test_extract_directory(self):
        ext = Extractor()
        refs = ext.extract_files([str(FIXTURES_DIR)])
        # Should find refs from multiple files
        assert len(refs["commands"]) > 0
        assert len(refs["code_blocks"]) > 0
        assert len(refs["apis"]) > 0


# ═══════════════════════════════════════════════════════════════════════════
# Scope classification tests
# ═══════════════════════════════════════════════════════════════════════════


class TestScopeClassification:
    """Test classify_command_scope."""

    @pytest.mark.parametrize("cmd,expected", [
        ("oc get pods", "external"),
        ("kubectl apply -f manifest.yaml", "external"),
        ("sudo systemctl restart example", "external"),
        ("docker run nginx", "external"),
        ("git commit -m test", "external"),
        ("curl https://example.com", "external"),
    ])
    def test_external_commands(self, cmd, expected):
        assert classify_command_scope(cmd, [FAKE_REPO]) == expected

    def test_in_scope_command(self):
        # example-tool binary exists at fake-repo/cmd/example-tool/
        assert classify_command_scope("example-tool deploy --env prod", [FAKE_REPO]) == "in-scope"

    def test_unknown_command(self):
        assert classify_command_scope("nonexistent-tool run", [FAKE_REPO]) == "unknown"

    def test_empty_repo_list(self):
        assert classify_command_scope("example-tool deploy", []) == "unknown"


# ═══════════════════════════════════════════════════════════════════════════
# CLI validation tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCLIValidation:
    """Test discover_cli_definitions and CLI flag validation in search_commands."""

    def test_discover_argparse_flags(self):
        cli_def = discover_cli_definitions("example-tool", [FAKE_REPO])
        assert cli_def is not None
        assert cli_def["framework"] == "argparse"
        assert "name" in cli_def["known_flags"]
        assert "template" in cli_def["known_flags"]
        assert "env" in cli_def["known_flags"]
        assert "replicas" in cli_def["known_flags"]
        assert "timeout" in cli_def["known_flags"]
        assert "format" in cli_def["known_flags"]

    def test_unknown_binary_returns_none(self, tmp_path):
        # Use an empty repo so generic fallback files (main.py, cli.py)
        # from the real fake-repo don't produce a false match.
        assert discover_cli_definitions("nonexistent-tool", [str(tmp_path)]) is None

    def test_search_commands_valid_flags(self):
        commands = [{"command": "example-tool deploy --env staging --replicas 2",
                     "file": "test.adoc", "line": 1}]
        results, _ = search_commands(commands, [FAKE_REPO])
        assert len(results) == 1
        r = results[0]
        assert r["found"] is True
        assert r["scope"] == "in-scope"
        assert r["cli_validation"] is not None
        assert r["cli_validation"]["unknown_flags"] == []
        assert "env" in r["cli_validation"]["valid_flags"]
        assert "replicas" in r["cli_validation"]["valid_flags"]

    def test_search_commands_stale_flags(self):
        commands = [{"command": "example-tool deploy --environment production --count 5",
                     "file": "test.adoc", "line": 1}]
        results, _ = search_commands(commands, [FAKE_REPO])
        assert len(results) == 1
        r = results[0]
        assert r["cli_validation"] is not None
        assert "environment" in r["cli_validation"]["unknown_flags"]
        assert "count" in r["cli_validation"]["unknown_flags"]

    def test_search_commands_external_skips_validation(self):
        commands = [{"command": "oc get pods -n example",
                     "file": "test.adoc", "line": 1}]
        results, _ = search_commands(commands, [FAKE_REPO])
        assert len(results) == 1
        r = results[0]
        assert r["scope"] == "external"
        assert r["found"] is True
        assert r["cli_validation"] is None


# ═══════════════════════════════════════════════════════════════════════════
# Schema validation tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSchemaValidation:
    """Test discover_schemas and search_configs."""

    def test_discover_schemas_finds_yaml_and_json(self):
        schemas = discover_schemas([FAKE_REPO])
        assert len(schemas) >= 2
        formats = {s["format"] for s in schemas}
        assert "yaml" in formats
        assert "json" in formats

    def test_discover_schemas_yaml_keys(self):
        schemas = discover_schemas([FAKE_REPO])
        yaml_schemas = [s for s in schemas if s["format"] in ("yaml", "yml")]
        assert len(yaml_schemas) >= 1
        keys = yaml_schemas[0]["keys"]
        assert "replicas" in keys
        assert "logLevel" in keys

    def test_discover_schemas_json_keys(self):
        schemas = discover_schemas([FAKE_REPO])
        json_schemas = [s for s in schemas if s["format"] == "json"]
        assert len(json_schemas) >= 1
        keys = json_schemas[0]["keys"]
        assert "host" in keys
        assert "pool_size" in keys

    def test_search_configs_matching_keys(self):
        configs = [{"keys": ["host", "port", "pool_size", "workers"],
                    "file": "test.adoc", "line": 1, "format": "json"}]
        results, _ = search_configs(configs, [FAKE_REPO])
        assert len(results) == 1
        r = results[0]
        assert r["found"] is True
        assert r["schema_validation"] is not None
        assert r["schema_validation"]["overlap_ratio"] > 0.5

    def test_search_configs_stale_keys(self):
        configs = [{"keys": ["replicas", "logLevel", "maxRetries", "connectionTimeout"],
                    "file": "test.adoc", "line": 1, "format": "yaml"}]
        results, _ = search_configs(configs, [FAKE_REPO])
        assert len(results) == 1
        r = results[0]
        assert r["found"] is True
        sv = r["schema_validation"]
        assert "maxRetries" in sv["keys_only_in_doc"]
        assert "connectionTimeout" in sv["keys_only_in_doc"]

    def test_search_configs_no_match(self):
        configs = [{"keys": ["totallyFakeKey", "anotherFakeKey"],
                    "file": "test.adoc", "line": 1, "format": "yaml"}]
        results, _ = search_configs(configs, [FAKE_REPO])
        assert len(results) == 1
        assert results[0]["found"] is False


# ═══════════════════════════════════════════════════════════════════════════
# API search tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAPISearch:
    """Test search_apis."""

    def test_find_class_definition(self):
        apis = [{"name": "ExampleClient", "type": "class",
                 "file": "test.adoc", "line": 1}]
        results = search_apis(apis, [FAKE_REPO])
        assert len(results) == 1
        r = results[0]
        assert r["found"] is True
        assert any(m["type"] == "definition" for m in r["matches"])

    def test_find_function_definition(self):
        apis = [{"name": "list_resources", "type": "function",
                 "file": "test.adoc", "line": 1}]
        results = search_apis(apis, [FAKE_REPO])
        assert len(results) == 1
        assert results[0]["found"] is True

    def test_missing_api_not_found(self):
        apis = [{"name": "MissingWidget", "type": "class",
                 "file": "test.adoc", "line": 1}]
        results = search_apis(apis, [FAKE_REPO])
        assert len(results) == 1
        assert results[0]["found"] is False

    def test_missing_function_not_found(self):
        apis = [{"name": "deprecatedFunction", "type": "function",
                 "file": "test.adoc", "line": 1}]
        results = search_apis(apis, [FAKE_REPO])
        assert len(results) == 1
        assert results[0]["found"] is False


# ═══════════════════════════════════════════════════════════════════════════
# File path search tests
# ═══════════════════════════════════════════════════════════════════════════


class TestFilePathSearch:
    """Test search_file_paths."""

    def test_exact_match(self):
        paths = [{"path": "src/client.py", "file": "test.adoc", "line": 1}]
        results = search_file_paths(paths, [FAKE_REPO])
        assert len(results) == 1
        r = results[0]
        assert r["found"] is True
        assert any(m["type"] == "exact" for m in r["matches"])

    def test_basename_match(self):
        # lib/processor.py doesn't exist but src/processor.py does
        paths = [{"path": "lib/processor.py", "file": "test.adoc", "line": 1}]
        results = search_file_paths(paths, [FAKE_REPO])
        assert len(results) == 1
        r = results[0]
        assert r["found"] is True
        assert any(m["type"] == "basename" for m in r["matches"])

    def test_missing_path(self):
        paths = [{"path": "src/removed_module.py", "file": "test.adoc", "line": 1}]
        results = search_file_paths(paths, [FAKE_REPO])
        assert len(results) == 1
        assert results[0]["found"] is False

    def test_yaml_config_exact(self):
        paths = [{"path": "config/defaults.yaml", "file": "test.adoc", "line": 1}]
        results = search_file_paths(paths, [FAKE_REPO])
        assert len(results) == 1
        assert results[0]["found"] is True


# ═══════════════════════════════════════════════════════════════════════════
# Code block search tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCodeBlockSearch:
    """Test search_code_blocks."""

    def test_matching_code_block(self):
        blocks = [{
            "content": "class ExampleClient:\n    def __init__(self, endpoint, api_key):\n        self.endpoint = endpoint",
            "language": "python",
            "file": "test.adoc", "line": 1,
        }]
        results = search_code_blocks(blocks, [FAKE_REPO])
        assert len(results) == 1
        r = results[0]
        assert r["found"] is True
        assert len(r["matches"]) > 0
        assert "identifiers" in r

    def test_non_matching_code_block(self):
        blocks = [{
            "content": "class CompletelyFakeClass:\n    def nonexistent_method(self):\n        pass",
            "language": "python",
            "file": "test.adoc", "line": 1,
        }]
        results = search_code_blocks(blocks, [FAKE_REPO])
        assert len(results) == 1
        assert results[0]["found"] is False

    def test_empty_code_block(self):
        blocks = [{"content": "", "language": "python",
                   "file": "test.adoc", "line": 1}]
        results = search_code_blocks(blocks, [FAKE_REPO])
        assert len(results) == 1
        assert results[0]["found"] is False

    def test_identifiers_extracted(self):
        blocks = [{
            "content": "client = ExampleClient(endpoint=url, api_key=key)",
            "language": "python",
            "file": "test.adoc", "line": 1,
        }]
        results = search_code_blocks(blocks, [FAKE_REPO])
        assert len(results) == 1
        assert "ExampleClient" in results[0]["identifiers"]


# ═══════════════════════════════════════════════════════════════════════════
# End-to-end tests
# ═══════════════════════════════════════════════════════════════════════════


class TestEndToEnd:
    """Test extract + search pipeline end-to-end."""

    def test_extract_then_search_stale_doc(self):
        """Full pipeline: extract refs from stale doc, search against fake repo."""
        ext = Extractor()
        refs = ext.extract_files([STALE_DOC])

        # Search each category
        cmd_results, _ = search_commands(refs["commands"], [FAKE_REPO])
        cfg_results, _ = search_configs(refs["configs"], [FAKE_REPO])
        fp_results = search_file_paths(refs["file_paths"], [FAKE_REPO])

        # External commands should be found and scope=external
        external_cmds = [r for r in cmd_results if r["scope"] == "external"]
        assert len(external_cmds) >= 3  # oc, kubectl, sudo

        # In-scope commands with valid flags
        valid_cmds = [r for r in cmd_results
                      if r["scope"] == "in-scope"
                      and r.get("cli_validation")
                      and r["cli_validation"]["unknown_flags"] == []]
        assert len(valid_cmds) >= 1

        # In-scope commands with stale flags
        stale_cmds = [r for r in cmd_results
                      if r.get("cli_validation")
                      and len(r["cli_validation"]["unknown_flags"]) > 0]
        assert len(stale_cmds) >= 1
        stale_flags = stale_cmds[0]["cli_validation"]["unknown_flags"]
        assert "environment" in stale_flags or "count" in stale_flags

        # Config with stale keys
        stale_cfgs = [r for r in cfg_results
                      if r.get("schema_validation")
                      and len(r["schema_validation"]["keys_only_in_doc"]) > 0]
        assert len(stale_cfgs) >= 1

        # File paths: exact, basename, missing
        exact_fps = [r for r in fp_results
                     if r["found"] and any(m["type"] == "exact" for m in r["matches"])]
        basename_fps = [r for r in fp_results
                        if r["found"] and any(m["type"] == "basename" for m in r["matches"])]
        missing_fps = [r for r in fp_results if not r["found"]]
        assert len(exact_fps) >= 1
        assert len(basename_fps) >= 1
        assert len(missing_fps) >= 1

    def test_extract_then_search_concept_doc(self):
        """Extract from sample-concept which has code blocks with APIs."""
        ext = Extractor()
        refs = ext.extract_files([SAMPLE_CONCEPT])

        api_results = search_apis(refs["apis"], [FAKE_REPO])

        # ExampleClient and list_resources are extracted from the Python
        # code block in sample-concept.adoc and should be found in fake-repo
        found_apis = [r for r in api_results if r["found"]]
        found_names = [r["name"] for r in found_apis]
        # ExampleClient appears as a function-type call in the code block
        assert "ExampleClient" in found_names or "list_resources" in found_names

    def test_cli_output_structure(self, tmp_path):
        """Verify the JSON output structure matches expected schema."""
        ext = Extractor()
        refs = ext.extract_files([STALE_DOC])
        refs_file = tmp_path / "refs.json"
        refs_file.write_text(json.dumps({"references": refs}))

        # Simulate cmd_search by calling functions directly
        cmd_results, cli_defs = search_commands(refs["commands"], [FAKE_REPO])
        cfg_results, schemas = search_configs(refs["configs"], [FAKE_REPO])

        output = {
            "repos": [FAKE_REPO],
            "discovered_cli_definitions": cli_defs,
            "discovered_schemas": [{"file": s["file"], "format": s["format"],
                                    "key_count": len(s["keys"])} for s in schemas],
            "results": {
                "commands": cmd_results,
                "code_blocks": search_code_blocks(refs["code_blocks"], [FAKE_REPO]),
                "apis": search_apis(refs["apis"], [FAKE_REPO]),
                "configs": cfg_results,
                "file_paths": search_file_paths(refs["file_paths"], [FAKE_REPO]),
            },
        }

        # Verify top-level keys
        assert "repos" in output
        assert "discovered_cli_definitions" in output
        assert "discovered_schemas" in output
        assert "results" in output

        # Verify result categories
        for cat in ["commands", "code_blocks", "apis", "configs", "file_paths"]:
            assert cat in output["results"]

        # Verify command result structure
        for cmd in output["results"]["commands"]:
            assert "found" in cmd
            assert "scope" in cmd

        # Verify config result structure
        for cfg in output["results"]["configs"]:
            assert "found" in cfg

        # Verify CLI defs structure
        for cli_def in output["discovered_cli_definitions"]:
            assert "framework" in cli_def
            assert "known_flags" in cli_def
            assert "file" in cli_def


# ═══════════════════════════════════════════════════════════════════════════
# Discover tests
# ═══════════════════════════════════════════════════════════════════════════


class TestDiscover:
    """Test the discover subcommand functions."""

    def test_detect_languages_python(self):
        langs = detect_languages([FAKE_REPO])
        assert "python" in langs

    def test_detect_languages_empty_repo(self, tmp_path):
        langs = detect_languages([str(tmp_path)])
        assert langs == []

    def test_discover_env_vars(self):
        results = discover_env_vars([FAKE_REPO])
        names = {r["name"] for r in results}
        assert "API_HOST" in names
        assert "API_PORT" in names
        assert "DATABASE_URL" in names
        # Verify structure
        for r in results:
            assert "source_file" in r
            assert "source_line" in r
            assert "access_pattern" in r

    def test_discover_all_cli_args(self):
        results = discover_all_cli_args([FAKE_REPO])
        names = {r["name"] for r in results}
        # argparse flags from fake-repo/cmd/example-tool/main.py
        assert "env" in names or "name" in names
        for r in results:
            assert "framework" in r
            assert "source_file" in r

    def test_discover_config_keys(self):
        results = discover_config_keys([FAKE_REPO])
        key_paths = {r["key_path"] for r in results}
        # From schema files (existing discover_schemas)
        assert "replicas" in key_paths or "host" in key_paths
        # From code access patterns (config_loader.py)
        assert "database.host" in key_paths
        assert "database.port" in key_paths
        assert "server.timeout" in key_paths
        for r in results:
            assert "source_file" in r
            assert "format" in r
            assert "source" in r

    def test_discover_api_endpoints(self):
        results = discover_api_endpoints([FAKE_REPO])
        paths = {r["path"] for r in results}
        assert "/api/v1/resources" in paths
        # Verify structure
        for r in results:
            assert "method" in r
            assert "path" in r
            assert "source_file" in r
            assert "source_line" in r
            assert "framework" in r
        # Check methods
        methods = {(r["method"], r["path"]) for r in results}
        assert ("GET", "/api/v1/resources") in methods
        assert ("POST", "/api/v1/resources") in methods

    def test_discover_data_models(self):
        results = discover_data_models([FAKE_REPO])
        names = {r["name"] for r in results}
        assert "Resource" in names
        for r in results:
            assert "source_file" in r
            assert "type" in r

    def test_compare_inventory_undocumented(self):
        inventory = {
            "env_vars": [{"name": "API_HOST"}, {"name": "SECRET_KEY"}],
            "cli_args": [{"name": "verbose"}],
            "config_keys": [{"key_path": "db.host"}],
            "api_endpoints": [{"path": "/api/v1/resources"}],
            "data_models": [{"name": "Resource"}],
        }
        refs = {
            "code_blocks": [],
            "commands": [],
            "configs": [],
            "apis": [],
        }
        result = compare_inventory_to_refs(inventory, refs)
        # Everything should be undocumented since refs are empty
        assert "API_HOST" in result["undocumented"]["env_vars"]
        assert "SECRET_KEY" in result["undocumented"]["env_vars"]
        assert "verbose" in result["undocumented"]["cli_args"]

    def test_compare_inventory_doc_only(self):
        inventory = {
            "env_vars": [],
            "cli_args": [],
            "config_keys": [],
            "api_endpoints": [],
            "data_models": [],
        }
        refs = {
            "code_blocks": [{
                "content": 'DATABASE_URL = os.environ["DATABASE_URL"]',
            }],
            "commands": [{"command": "example-tool --verbose --debug"}],
            "configs": [{"keys": ["timeout", "retries"]}],
            "apis": [{"name": "/api/health", "type": "endpoint"}],
        }
        result = compare_inventory_to_refs(inventory, refs)
        # Documented items not in code should appear as doc_only
        assert "verbose" in result["doc_only"]["cli_args"]
        assert "debug" in result["doc_only"]["cli_args"]
        assert "timeout" in result["doc_only"]["config_keys"]
        assert "/api/health" in result["doc_only"]["api_endpoints"]

    def test_discover_e2e_output_schema(self, tmp_path):
        """Verify discover output JSON schema via cmd_discover."""
        import argparse
        from code_scanner import cmd_discover

        out_file = tmp_path / "inventory.json"
        args = argparse.Namespace(
            repos=[FAKE_REPO],
            refs_json=None,
            output=str(out_file),
            language=None,
        )
        cmd_discover(args)

        data = json.loads(out_file.read_text())
        assert "repos" in data
        assert "languages" in data
        assert "inventory" in data
        assert "summary" in data
        for cat in ["env_vars", "cli_args", "config_keys", "api_endpoints", "data_models"]:
            assert cat in data["inventory"]
            assert cat in data["summary"]
            assert isinstance(data["summary"][cat], int)
