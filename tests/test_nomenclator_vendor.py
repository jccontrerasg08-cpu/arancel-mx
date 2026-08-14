from __future__ import annotations

from pathlib import Path

from arancel_mx.cli import build_parser, main


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "third_party" / "nomenclator"


def test_nomenclator_package_and_upstream_snapshot_are_complete() -> None:
    required = (
        ROOT / "src" / "nomenclator" / "agent.py",
        ROOT / "src" / "nomenclator" / "cli.py",
        ROOT / "src" / "nomenclator" / "exceptions.py",
        ROOT / "src" / "nomenclator" / "usage.py",
        ROOT / "src" / "nomenclator" / "py.typed",
        ROOT / "src" / "nomenclator" / "models" / "classification.py",
        ROOT / "src" / "nomenclator" / "models" / "navigation.py",
        ROOT / "src" / "nomenclator" / "models" / "product_facts.py",
        ROOT / "src" / "nomenclator" / "nomenclature" / "client.py",
        ROOT / "src" / "nomenclator" / "nomenclature" / "parser.py",
        ROOT / "src" / "nomenclator" / "nomenclature" / "urls.py",
        ROOT / "src" / "nomenclator" / "nomenclature" / "tree.py",
        ROOT / "src" / "nomenclator" / "nomenclature" / "chapter.py",
        ROOT / "src" / "nomenclator" / "nomenclature" / "notes.py",
        ROOT / "src" / "nomenclator" / "nomenclature" / "rules.py",
        ROOT / "src" / "nomenclator" / "nomenclature" / "utils.py",
        ROOT / "src" / "nomenclator" / "retrieval" / "hybrid.py",
        ROOT / "src" / "nomenclator" / "retrieval" / "dense.py",
        ROOT / "src" / "nomenclator" / "retrieval" / "embeddings.py",
        ROOT / "src" / "nomenclator" / "tasks" / "product_analyst.py",
        ROOT / "src" / "nomenclator" / "tasks" / "research_analyst.py",
        ROOT / "src" / "nomenclator" / "tasks" / "classification_analyst.py",
        ROOT / "tests" / "nomenclator" / "conftest.py",
        ROOT / "tests" / "nomenclator" / "unit" / "test_agent.py",
        ROOT / "tests" / "nomenclator" / "unit" / "test_context.py",
        ROOT / "tests" / "nomenclator" / "unit" / "test_nomenclature_client.py",
        ROOT / "tests" / "nomenclator" / "unit" / "test_retrieval.py",
        ROOT / "tests" / "nomenclator" / "unit" / "test_retriever.py",
        ROOT / "tests" / "nomenclator" / "unit" / "test_usage.py",
        ROOT / "tests" / "nomenclator" / "integration" / "test_hs_classification_agent.py",
        ROOT / "tests" / "nomenclator" / "integration" / "test_hs_tree_navigation.py",
        ROOT / "tests" / "nomenclator" / "integration" / "test_wco_2022_nomenclature.py",
        VENDOR / "README.md",
        VENDOR / "ARCHITECTURE.md",
        VENDOR / "AGENTS.md",
        VENDOR / "LICENSE",
        VENDOR / "pyproject.toml",
        VENDOR / "poetry.lock",
        VENDOR / "VENDOR.md",
        VENDOR / "UPSTREAM_COMMIT",
        VENDOR / ".github" / "workflows" / "ci.yaml",
        VENDOR / "vscode.settings.json",
    )
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    assert missing == []
    assert (VENDOR / "UPSTREAM_URL").read_text(encoding="utf-8").strip() == (
        "https://github.com/talmago/nomenclator.git"
    )
    assert "MIT" in (VENDOR / "LICENSE").read_text(encoding="utf-8")
    assert "nomenclator" in (ROOT / "NOTICE").read_text(encoding="utf-8").lower()


def test_nomenclator_subcommand_is_listed_and_fail_closed_without_extra() -> None:
    help_text = build_parser().format_help()
    assert "nomenclator" in help_text
    assert main(["nomenclator", "fresh bananas"]) == 2
