import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TSCONFIG = ROOT / "website" / "tsconfig.json"


def test_docusaurus_tsconfig_handles_typescript_6_baseurl_deprecation() -> None:
    config = json.loads(TSCONFIG.read_text(encoding="utf-8"))
    compiler_options = config["compilerOptions"]

    assert compiler_options["baseUrl"] == "."
    assert compiler_options["ignoreDeprecations"] == "6.0"
