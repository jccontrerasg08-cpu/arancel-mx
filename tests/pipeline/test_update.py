import json
from pathlib import Path

from arancel_mx.pipeline.update import UpdateConfig, check_for_updates, run_update, update_status


FIXTURE = Path(__file__).parents[1] / "fixtures" / "diputados" / "ligie_2022.html"


class Response:
    text = FIXTURE.read_text(encoding="utf-8")

    def raise_for_status(self):
        return None


class Client:
    def get(self, url, timeout):
        return Response()


class Runner:
    def __init__(self):
        self.jobs = []

    def run_domain(self, name):
        self.jobs.append(name)


def test_changed_update_runs_each_selected_job_once_and_writes_state(tmp_path):
    config = UpdateConfig(state_path=tmp_path / "state.json")
    runner = Runner()

    result = run_update(config, client=Client(), job_runner=runner)

    assert result.status == "updated"
    assert runner.jobs == list(result.jobs)
    assert len(runner.jobs) == len(set(runner.jobs))
    assert runner.jobs.count("canonical_rebuild") == 1
    assert update_status(config)["status"] == "ready"


def test_no_change_skips_jobs_and_preserves_machine_readable_status(tmp_path):
    config = UpdateConfig(state_path=tmp_path / "state.json")
    first = check_for_updates(config, Client())
    config.state_path.write_text(json.dumps(first.snapshot), encoding="utf-8")
    runner = Runner()

    result = run_update(config, client=Client(), job_runner=runner)

    assert result.to_dict() == {"status": "no_change", "jobs": [], "events": []}
    assert runner.jobs == []
