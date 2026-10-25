import json
from pathlib import Path

from scripts.build_static_pages import write_host_files


def test_pages_tree_disables_jekyll_and_vercel_builds(tmp_path: Path) -> None:
    write_host_files(tmp_path)

    assert (tmp_path / ".nojekyll").read_text(encoding="utf-8") == ""
    config = json.loads((tmp_path / "vercel.json").read_text(encoding="utf-8"))
    assert config == {"git": {"deploymentEnabled": False}}
