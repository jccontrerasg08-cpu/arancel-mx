import json
from pathlib import Path

from arancel_mx.pipeline.update import UpdateConfig, check_for_updates


FIXTURE = Path(__file__).parents[1] / "fixtures" / "diputados" / "ligie_2022.html"


class Response:
    text = FIXTURE.read_text(encoding="utf-8")

    def raise_for_status(self):
        return None


class Client:
    def get(self, url, timeout):
        return Response()


def test_changed_ledger_reports_rebuild_job(tmp_path):
    config = UpdateConfig(state_path=tmp_path / "state.json")

    plan = check_for_updates(config, client=Client())

    assert plan.status == "changed"
    assert "canonical_rebuild" in plan.jobs
    assert len(plan.jobs) == len(set(plan.jobs))


def test_matching_state_reports_no_change(tmp_path):
    config = UpdateConfig(state_path=tmp_path / "state.json")
    first = check_for_updates(config, Client())
    config.state_path.write_text(json.dumps(first.snapshot), encoding="utf-8")

    plan = check_for_updates(config, Client())

    assert plan.status == "no_change"
    assert plan.jobs == ()
