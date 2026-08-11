from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_extended_community_metadata_is_present():
    required = (
        "CITATION.cff",
        "SUPPORT.md",
        ".github/CODEOWNERS",
    )
    assert [path for path in required if not (ROOT / path).is_file()] == []


def test_citation_metadata_names_project_and_repository():
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "cff-version: 1.2.0" in text
    assert 'title: "arancel-mx"' in text
    assert "jccontrerasg08-cpu/arancel-mx" in text
    assert "Apache-2.0" in text


def test_codeowners_keeps_current_maintainer_as_owner():
    text = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert re.search(r"^\*\s+@jccontrerasg08-cpu\s*$", text, re.MULTILINE)
