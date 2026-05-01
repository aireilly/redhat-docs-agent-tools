"""Tests for extract_refs.py — the standalone doc reference extractor."""
import sys
from pathlib import Path

# Add extract_refs's directory to sys.path so we can import it
_SCRIPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "plugins" / "docs-tools" / "skills" / "docs-review-technical" / "scripts"
)
sys.path.insert(0, str(_SCRIPTS_DIR))

from extract_refs import Extractor  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent
STALE_DOC = str(FIXTURES_DIR / "doc-with-stale-refs.adoc")
SAMPLE_CONCEPT = str(FIXTURES_DIR / "sample-concept.adoc")
SAMPLE_PROCEDURE = str(FIXTURES_DIR / "sample-procedure.adoc")
SAMPLE_REFERENCE = str(FIXTURES_DIR / "sample-reference.md")


class TestExtract:
    """Test the Extractor class against fixture files."""

    def test_extract_stale_doc_commands(self):
        ext = Extractor()
        refs = ext.extract_files([STALE_DOC])
        commands = [c["command"] for c in refs["commands"]]
        assert any("oc get pods" in c for c in commands)
        assert any("kubectl apply" in c for c in commands)
        assert any("sudo systemctl" in c for c in commands)
        assert any("example-tool deploy --env" in c for c in commands)
        assert any("example-tool deploy --environment" in c for c in commands)

    def test_extract_stale_doc_configs(self):
        ext = Extractor()
        refs = ext.extract_files([STALE_DOC])
        configs = refs["configs"]
        assert len(configs) >= 2
        yaml_cfg = [c for c in configs if c["format"] == "yaml"]
        assert len(yaml_cfg) >= 1
        yaml_keys = yaml_cfg[0]["keys"]
        assert "replicas" in yaml_keys
        assert "maxRetries" in yaml_keys
        json_cfg = [c for c in configs if c["format"] == "json"]
        assert len(json_cfg) >= 1
        json_keys = json_cfg[0]["keys"]
        assert "host" in json_keys
        assert "pool_size" in json_keys

    def test_extract_stale_doc_apis(self):
        ext = Extractor()
        refs = ext.extract_files([STALE_DOC])
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
        assert len(refs["commands"]) > 0
        assert len(refs["code_blocks"]) > 0
        assert len(refs["apis"]) > 0

    def test_output_schema(self):
        """Verify the JSON output structure matches expected schema."""
        ext = Extractor()
        refs = ext.extract_files([STALE_DOC])
        output = {
            "summary": {k: len(v) for k, v in refs.items()},
            "references": refs,
        }
        assert "summary" in output
        assert "references" in output
        for cat in ["commands", "code_blocks", "apis", "configs", "file_paths"]:
            assert cat in output["summary"]
            assert cat in output["references"]
            assert isinstance(output["summary"][cat], int)
