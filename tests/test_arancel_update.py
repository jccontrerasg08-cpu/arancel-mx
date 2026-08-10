import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from comex import main
from src.comex.arancel_update import LocalJobRunner, UpdateConfig, UpdatePlan, check_for_updates, run_legal_update


class Response:
    def __init__(self, text): self.text = text
    def raise_for_status(self): return None


class Client:
    def __init__(self, html): self.html = html
    def get(self, url, timeout=None): return Response(self.html)


class Runner:
    def __init__(self): self.domain_calls = []; self.publish_calls = []
    def run_domain(self, job, plan): self.domain_calls.append(job)
    def publish(self, plan): self.publish_calls.append(plan)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.html = Path("tests/fixtures/diputados/ligie_2022.html").read_text("utf-8")
        self.config = UpdateConfig(state_path=self.root / "ledger.json")

    def tearDown(self): self.temp.cleanup()

    def test_no_change_does_not_run_domain_jobs_or_write_release(self):
        first = check_for_updates(self.config, client=Client(self.html))
        self.config.state_path.write_text(json.dumps(first.snapshot), encoding="utf-8")
        runner = Runner()
        result = run_legal_update(self.config, client=Client(self.html), job_runner=runner)
        self.assertEqual(result.status, "no_change")
        self.assertEqual(runner.domain_calls, [])
        self.assertEqual(runner.publish_calls, [])

    def test_multi_event_update_runs_union_then_publishes_once(self):
        runner = Runner()
        result = run_legal_update(self.config, client=Client(self.html), job_runner=runner)
        self.assertEqual(result.status, "published")
        self.assertEqual(len(runner.publish_calls), 1)
        self.assertEqual(len(runner.domain_calls), len(set(runner.domain_calls)))
        self.assertTrue(self.config.state_path.exists())

    def test_local_runner_materializes_canonical_rebuild_once(self):
        raw = self.root / "raw"
        releases = self.root / "releases"
        embedded = self.root / "embedded"
        runner = LocalJobRunner(raw_root=raw, release_root=releases, embedded_root=embedded)
        plan = UpdatePlan("changed", (), ("diputados_capture", "canonical_rebuild"), {"page_sha256": "a" * 64})

        def fake_build(source_dir, output_dir, dataset_version, effective_as_of, timeout_s=None):
            output_dir.mkdir(parents=True)
            (output_dir / "arancel_mx.duckdb").write_bytes(b"db")
            (output_dir / "manifest.json").write_text('{"validation_status":"passed"}', encoding="utf-8")
            return {"validation_status": "passed"}

        with patch("src.comex.arancel_update.build_arancel_release", side_effect=fake_build) as build:
            for job in plan.jobs:
                runner.run_domain(job, plan)
            runner.publish(plan)
        self.assertEqual(build.call_count, 1)
        self.assertEqual((embedded / "arancel_mx.duckdb").read_bytes(), b"db")


class CliTests(unittest.TestCase):
    def test_arancel_check_prints_machine_readable_plan(self):
        plan = type("Plan", (), {"to_dict": lambda self: {"status": "changed", "jobs": ["canonical_rebuild"]}})()
        with patch("comex.check_for_updates", return_value=plan), patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(main(["arancel-check"]), 0)
        self.assertEqual(json.loads(out.getvalue())["status"], "changed")


if __name__ == "__main__": unittest.main()
