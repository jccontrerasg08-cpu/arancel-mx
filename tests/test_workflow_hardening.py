"""Cross-workflow hardening contract, enforced on workflow text.

GitHub Actions YAML uses a bare `on:` key. A YAML 1.1 loader maps that key to
the boolean True, which is why this repo previously imported PyYAML. These
tests treat `on:` as a literal line instead.
"""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CHECKOUTS_KEEPING_CREDENTIALS = frozenset()
MAX_TIMEOUT_MINUTES = 60
_HOSTED_RUNNERS = frozenset({"ubuntu-latest", "windows-latest", "macos-latest"})
_PINNED_USES = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
_INTERPOLATION = re.compile(r"\$\{\{")
_TOP_LEVEL = re.compile(r"^[a-zA-Z_][\w-]*:", re.MULTILINE)
_JOB_KEY = re.compile(r"^  ([\w-]+):$", re.MULTILINE)
_USES = re.compile(
    r"^(?P<indent>[ \t]*)(?:-[ \t]+)?uses:[ \t]+(?P<ref>\S+)", re.MULTILINE
)


def _workflow_paths() -> list[Path]:
    return sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))


def _workflow_texts() -> dict[str, str]:
    paths = _workflow_paths()
    assert paths
    return {path.name: path.read_text(encoding="utf-8") for path in paths}


def _block_after(text: str, header: str) -> str:
    match = re.search(rf"^{re.escape(header)}\n", text, re.MULTILINE)
    assert match is not None, header
    start = match.end()
    nxt = _TOP_LEVEL.search(text, start)
    return text[start : nxt.start() if nxt else len(text)]


def _job_blocks(text: str) -> dict[str, str]:
    jobs_match = re.search(r"^jobs:\n", text, re.MULTILINE)
    assert jobs_match is not None
    jobs_text = text[jobs_match.end() :]
    keys = list(_JOB_KEY.finditer(jobs_text))
    assert keys
    blocks: dict[str, str] = {}
    for i, match in enumerate(keys):
        end = keys[i + 1].start() if i + 1 < len(keys) else len(jobs_text)
        blocks[match.group(1)] = jobs_text[match.start() : end]
    return blocks


def _run_scripts(block: str) -> list[str]:
    scripts: list[str] = []
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        folded = re.match(r"^(\s+)(?:-\s+)?run:\s+[|>]-?\s*$", lines[i])
        if folded:
            indent = len(folded.group(1))
            body: list[str] = []
            i += 1
            while i < len(lines) and (
                not lines[i].strip()
                or len(lines[i]) - len(lines[i].lstrip(" ")) > indent
            ):
                body.append(lines[i])
                i += 1
            scripts.append("\n".join(body))
            continue
        inline = re.match(r"^\s+(?:-\s+)?run:\s+(\S.*)$", lines[i])
        if inline:
            scripts.append(inline.group(1))
        i += 1
    return scripts


def _following_with_block(lines: list[str], uses_index: int) -> str:
    uses_indent = lines[uses_index].index("uses:")
    for i in range(uses_index + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if _USES.match(line) or (
            re.match(r"^\s*-\s+", line) and indent < uses_indent
        ):
            break
        if not stripped or stripped.startswith("#"):
            continue
        if indent == uses_indent and stripped == "with:":
            body: list[str] = []
            for candidate in lines[i + 1 :]:
                candidate_indent = len(candidate) - len(candidate.lstrip(" "))
                if candidate.strip() and candidate_indent <= indent:
                    break
                body.append(candidate)
            return "\n".join(body)
        if indent <= uses_indent:
            break
    return ""


def test_run_script_extraction_covers_list_items_and_folded_blocks():
    block = """\
  example:
    steps:
      - run: echo "${{ github.ref }}"
      - run: >
          printf foo |
          cat
      - name: Folded mapping-key script
        run: >-
          printf bar | cat
"""
    assert _run_scripts(block) == [
        'echo "${{ github.ref }}"',
        "          printf foo |\n          cat",
        "          printf bar | cat",
    ]


def test_action_extraction_covers_list_items_and_mapping_keys():
    text = """\
      - uses: owner/list-item@v1
        uses: owner/mapping@v2
"""
    assert [match.group("ref") for match in _USES.finditer(text)] == [
        "owner/list-item@v1",
        "owner/mapping@v2",
    ]


def test_checkout_credentials_are_read_from_the_checkout_with_block():
    lines = """\
      - uses: actions/checkout@0000000000000000000000000000000000000000
        with:
          fetch-depth: 0
      - uses: actions/setup-python@0000000000000000000000000000000000000000
        with:
          persist-credentials: false
""".splitlines()
    assert "persist-credentials: false" not in _following_with_block(lines, 0)


def test_every_workflow_parses_and_declares_bounded_triggers():
    for name, text in _workflow_texts().items():
        triggers = _block_after(text, "on:")
        assert "pull_request_target:" not in triggers, name
        if "pull_request:" in triggers:
            assert name == "ci.yml", f"{name} must not build from untrusted pull requests"


def test_no_workflow_grants_write_permissions_outside_a_job():
    for name, text in _workflow_texts().items():
        permissions = _block_after(text, "permissions:")
        assert ": write" not in permissions, f"{name} grants workflow-level write"


def test_every_job_is_least_privilege_bounded_and_hosted_by_github():
    for name, text in _workflow_texts().items():
        for job_name, block in _job_blocks(text).items():
            label = f"{name}:{job_name}"
            assert re.search(r"^    permissions:\n", block, re.MULTILINE), (
                f"{label} inherits permissions"
            )
            timeout = re.search(
                r"^    timeout-minutes: (\d+)\s*$", block, re.MULTILINE
            )
            assert timeout, f"{label} has no timeout"
            assert 0 < int(timeout.group(1)) <= MAX_TIMEOUT_MINUTES, label
            if "${{ matrix.os }}" in block:
                oss = re.search(r"os:\s*\[([^\]]+)\]", block)
                assert oss, label
                names = {item.strip().strip("\"'") for item in oss.group(1).split(",")}
                assert names <= _HOSTED_RUNNERS, label
            else:
                assert re.search(
                    r"^    runs-on: ubuntu-latest\s*$", block, re.MULTILINE
                ), label


def test_every_workflow_serializes_concurrent_runs():
    for name, text in _workflow_texts().items():
        concurrency = _block_after(text, "concurrency:")
        assert "group:" in concurrency, name
        assert "cancel-in-progress:" in concurrency, name


def test_every_action_is_pinned_to_a_commit_sha_with_a_readable_version_comment():
    for path in _workflow_paths():
        text = path.read_text(encoding="utf-8")
        for match in _USES.finditer(text):
            uses = match.group("ref")
            assert _PINNED_USES.fullmatch(uses), f"{path.name} uses {uses}"
            line = text[match.start() :].splitlines()[0]
            assert f"uses: {uses} # v" in line, (
                f"{path.name} pins {uses} without a readable version comment"
            )


def test_checkout_credentials_are_an_explicit_and_justified_decision():
    for name, text in _workflow_texts().items():
        if name in CHECKOUTS_KEEPING_CREDENTIALS:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            match = _USES.match(line)
            if not match or not match.group("ref").startswith("actions/checkout@"):
                continue
            with_block = _following_with_block(lines, i)
            assert re.search(
                r"^\s+persist-credentials:\s*false\s*(?:#.*)?$",
                with_block,
                re.MULTILINE,
            ), f"{name} keeps a checkout credential without persist-credentials: false"


def test_no_shell_script_interpolates_workflow_expressions():
    for name, text in _workflow_texts().items():
        for job_name, block in _job_blocks(text).items():
            for script in _run_scripts(block):
                assert not _INTERPOLATION.search(script), (
                    f"{name}:{job_name} interpolates an expression into a shell script; "
                    "pass the value through env: instead"
                )


def test_piped_shell_scripts_opt_into_pipefail():
    for name, text in _workflow_texts().items():
        for job_name, block in _job_blocks(text).items():
            for script in _run_scripts(block):
                if "|" not in script:
                    continue
                assert "set -euo pipefail" in script, (
                    f"{name}:{job_name} pipes without pipefail"
                )
                assert "shell: bash" in block, f"{name}:{job_name} pipes without shell: bash"


def test_workflow_outputs_are_only_written_through_the_reviewed_boundary():
    for path in _workflow_paths():
        text = path.read_text(encoding="utf-8")
        assert "GITHUB_OUTPUT" not in text, (
            f"{path.name} writes step outputs inline; use scripts.workflow_diagnostics "
            "so the values stay validated and single-line"
        )
