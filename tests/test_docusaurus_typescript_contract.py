import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TSCONFIG = ROOT / "website" / "tsconfig.json"
PACKAGE_JSON = ROOT / "website" / "package.json"


def test_docusaurus_tsconfig_handles_typescript_6_baseurl_deprecation() -> None:
    config = json.loads(TSCONFIG.read_text(encoding="utf-8"))
    compiler_options = config["compilerOptions"]

    assert compiler_options["baseUrl"] == "."
    assert compiler_options["ignoreDeprecations"] == "6.0"


def test_docusaurus_faster_dependency_matches_core_version() -> None:
    package = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    dependencies = package["dependencies"]

    assert dependencies["@docusaurus/faster"] == dependencies["@docusaurus/core"]
