"""Cross-workflow hardening contract, enforced on workflow text.

GitHub Actions YAML uses a bare `on:` key. A YAML 1.1 loader maps that key to
the boolean True, which is why this repo previously imported PyYAML. These
tests treat `on:` as a literal line instead. Loading still runs a stdlib
structural check so empty or malformed workflows fail before those text checks.
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
_STEP_ITEM = re.compile(r"^(\s+)-\s+\S")
_BASH_SHELL = re.compile(r"^\s+(?:-\s+)?shell:\s+bash\s*$", re.MULTILINE)
_USES = re.compile(
    r"^(?P<indent>[ \t]*)(?:-[ \t]+)?uses:[ \t]+(?P<ref>\S+)", re.MULTILINE
)
_REQUIRED_HEADERS = ("name:", "on:", "jobs:")


def _workflow_paths() -> list[Path]:
    return sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))


def _top_level_keys(text: str) -> list[str]:
    return [match.group(0)[:-1] for match in _TOP_LEVEL.finditer(text)]


def _assert_workflow_structure(name: str, text: str) -> None:
    assert text.strip(), f"{name} is empty"
    keys = _top_level_keys(text)
    assert keys, f"{name} has no top-level keys"
    seen: set[str] = set()
    for key in keys:
        assert key not in seen, f"{name} duplicates top-level key {key!r}"
        seen.add(key)
    for header in _REQUIRED_HEADERS:
        assert re.search(rf"^{re.escape(header)}", text, re.MULTILINE), (
            f"{name} missing {header}"
        )
    _job_blocks(text)


def _workflow_texts() -> dict[str, str]:
    paths = _workflow_paths()
    assert paths
    texts: dict[str, str] = {}
    for path in paths:
        text = path.read_text(encoding="utf-8")
        _assert_workflow_structure(path.name, text)
        texts[path.name] = text
    return texts


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
    names = [match.group(1) for match in keys]
    assert len(names) == len(set(names)), f"duplicate jobs: {names}"
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


def _step_blocks(block: str) -> list[str]:
    lines = block.splitlines()
    steps_at = next(
        (i for i, line in enumerate(lines) if re.match(r"^\s+steps:\s*$", line)),
        None,
    )
    if steps_at is None:
        return []
    starts: list[int] = []
    item_indent: int | None = None
    for i, line in enumerate(lines[steps_at + 1 :], start=steps_at + 1):
        match = _STEP_ITEM.match(line)
        if not match:
            continue
        indent = len(match.group(1))
        if item_indent is None:
            item_indent = indent
        if indent == item_indent:
            starts.append(i)
    return [
        "\n".join(lines[start : starts[i + 1] if i + 1 < len(starts) else len(lines)])
        for i, start in enumerate(starts)
    ]


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
        if indent < uses_indent:
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
    assert len(_step_blocks(block)) == 3


def test_following_with_block_skips_sibling_step_keys():
    lines = (
        "      - name: Check out\n"
        "        if: always()\n"
        "        uses: actions/checkout@deadbeef\n"
        "        with:\n"
        "          persist-credentials: false\n"
    ).splitlines()
    uses_index = next(i for i, line in enumerate(lines) if "uses:" in line)
    body = _following_with_block(lines, uses_index)
    assert "persist-credentials: false" in body


def test_workflow_structure_rejects_empty_and_malformed():
    valid = (
        "name: x\n"
        "on:\n"
        "  push:\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-latest\n"
    )
    _assert_workflow_structure("ok.yml", valid)
    cases = (
        ("empty.yml", ""),
        ("dup-key.yml", "name: a\nname: b\non:\n  push:\njobs:\n  test:\n    runs-on: ubuntu-latest\n"),
        ("no-name.yml", "on:\n  push:\njobs:\n  test:\n    runs-on: ubuntu-latest\n"),
        ("no-on.yml", "name: x\njobs:\n  test:\n    runs-on: ubuntu-latest\n"),
        ("no-jobs.yml", "name: x\non:\n  push:\n"),
        ("empty-jobs.yml", "name: x\non:\n  push:\njobs:\n"),
        (
            "dup-job.yml",
            "name: x\non:\n  push:\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
            "  test:\n    runs-on: ubuntu-latest\n",
        ),
    )
    for name, text in cases:
        try:
            _assert_workflow_structure(name, text)
        except AssertionError:
            continue
        raise AssertionError(f"{name} should fail structure check")


def test_pipefail_requires_shell_bash_on_the_piped_step():
    job = """\
  example:
    steps:
      - name: Unrelated
        shell: bash
        run: echo ok
      - name: Piped
        run: printf foo | cat
"""
    steps = _step_blocks(job)
    assert len(steps) == 2
    assert "shell: bash" in job
    piped = [step for step in steps if any("|" in script for script in _run_scripts(step))]
    assert len(piped) == 1
    assert _BASH_SHELL.search(piped[0]) is None


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
    for name, text in _workflow_texts().items():
        for match in _USES.finditer(text):
            uses = match.group("ref")
            assert _PINNED_USES.fullmatch(uses), f"{name} uses {uses}"
            line = text[match.start() :].splitlines()[0]
            assert f"uses: {uses} # v" in line, (
                f"{name} pins {uses} without a readable version comment"
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
            for step in _step_blocks(block):
                for script in _run_scripts(step):
                    if "|" not in script:
                        continue
                    label = f"{name}:{job_name}"
                    assert "set -euo pipefail" in script, f"{label} pipes without pipefail"
                    assert _BASH_SHELL.search(step), (
                        f"{label} pipes without shell: bash on that step"
                    )


def test_workflow_outputs_are_only_written_through_the_reviewed_boundary():
    for name, text in _workflow_texts().items():
        assert "GITHUB_OUTPUT" not in text, (
            f"{name} writes step outputs inline; use scripts.workflow_diagnostics "
            "so the values stay validated and single-line"
        )
