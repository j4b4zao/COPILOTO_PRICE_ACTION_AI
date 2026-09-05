import json

from tools.profit_rtd_brooks_selection_ledger import build_ledger, inspect_report


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _report(*, produced=1, requested=1, eligible=1, rejected=0, mode="SELECTION", cutoff="2026-09-08T10:00:00"):
    return {
        "launcher": "BROOKS_SELECTION_LAUNCHER_V1",
        "mode": mode,
        "symbol": "WINV26",
        "requested_sessions": requested,
        "produced_session_files": produced,
        "manifest": {
            "eligible_sessions": eligible,
            "rejected_sessions": rejected,
            "selection_cutoff": cutoff,
        },
    }


def test_valid_selection_counts_as_evidence(tmp_path):
    path = _write(tmp_path, "brooks_selection_valid.json", _report())
    item = inspect_report(path)
    assert item["status"] == "VALID_SELECTION"
    assert item["counts_as_selection_evidence"] is True


def test_no_valid_source_never_counts_as_evidence(tmp_path):
    path = _write(tmp_path, "brooks_selection_closed.json", _report(produced=0, eligible=0, cutoff=None))
    item = inspect_report(path)
    assert item["status"] == "NO_VALID_SOURCE"
    assert item["counts_as_selection_evidence"] is False
    assert item["retry_when_real_source_active"] is True


def test_rejected_report_is_separated(tmp_path):
    path = _write(tmp_path, "brooks_selection_rejected.json", _report(rejected=1, eligible=0))
    ledger = build_ledger([path])
    assert ledger["rejected_reports"] == 1
    assert ledger["selection_evidence_sessions"] == 0


def test_incomplete_report_is_separated(tmp_path):
    path = _write(tmp_path, "brooks_selection_incomplete.json", _report(produced=1, requested=2, eligible=1))
    ledger = build_ledger([path])
    assert ledger["incomplete_reports"] == 1
    assert ledger["selection_evidence_sessions"] == 0


def test_unreadable_json_fails_closed(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")
    item = inspect_report(path)
    assert item["status"] == "REJECTED"
    assert item["counts_as_selection_evidence"] is False
    assert item["reason"] == "REPORT_UNREADABLE"


def test_ledger_aggregates_only_valid_selection_sessions(tmp_path):
    valid1 = _write(tmp_path, "a.json", _report(cutoff="2026-09-08T10:00:00"))
    closed = _write(tmp_path, "b.json", _report(produced=0, eligible=0, cutoff=None))
    valid2 = _write(tmp_path, "c.json", _report(cutoff="2026-09-08T11:00:00"))
    ledger = build_ledger([valid1, closed, valid2])
    assert ledger["report_count"] == 3
    assert ledger["valid_selection_reports"] == 2
    assert ledger["no_valid_source_reports"] == 1
    assert ledger["selection_evidence_sessions"] == 2
    assert ledger["latest_observed_selection_cutoff"] == "2026-09-08T11:00:00"


def test_ledger_never_defines_oos_cutoff(tmp_path):
    path = _write(tmp_path, "valid.json", _report())
    ledger = build_ledger([path])
    assert ledger["selection_cutoff_defined_for_oos"] is False
    assert ledger["oos_collection_allowed"] is False
    assert ledger["hypothesis_freeze_allowed"] is False


def test_operational_influence_remains_disabled(tmp_path):
    path = _write(tmp_path, "valid.json", _report())
    ledger = build_ledger([path])
    assert ledger["score_influence_allowed"] is False
    assert ledger["risk_influence_allowed"] is False
    assert ledger["decision_influence_allowed"] is False
    assert ledger["alert_influence_allowed"] is False
    assert ledger["order_execution_allowed"] is False
