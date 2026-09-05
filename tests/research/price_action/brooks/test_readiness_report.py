import tools.profit_rtd_brooks_readiness_report as readiness


def test_real_readiness_report_is_ready_offline():
    report = readiness.build_readiness_report(symbol="WINV26")
    assert report["status"] == "READY_FOR_SELECTION_COLLECTION"
    assert report["offline_infrastructure_ready"] is True
    assert report["selection_collection_allowed"] is True
    assert report["blockers"] == []


def test_readiness_does_not_claim_market_state_or_oos():
    report = readiness.build_readiness_report()
    assert report["market_data_checked"] is False
    assert report["market_open_claimed"] is False
    assert report["oos_collection_allowed"] is False
    assert report["selection_cutoff_defined"] is False


def test_readiness_preserves_operational_isolation():
    report = readiness.build_readiness_report()
    for flag in (
        "hypothesis_freeze_allowed",
        "promotion_allowed",
        "predictive_claim_allowed",
        "score_influence_allowed",
        "risk_influence_allowed",
        "decision_influence_allowed",
        "alert_influence_allowed",
        "order_execution_allowed",
    ):
        assert report[flag] is False


def test_registry_has_seven_families():
    report = readiness.build_readiness_report()
    assert report["registered_family_count"] == 7
    assert len(report["registered_families"]) == 7


def test_next_command_is_selection_launcher():
    report = readiness.build_readiness_report(symbol="WINV26")
    assert report["next_command"] == "python -m tools.profit_rtd_brooks_selection_launcher WINV26"
    assert report["next_command_mode"] == "SELECTION"


def test_integrity_failure_blocks_collection(monkeypatch):
    monkeypatch.setattr(readiness, "run_integrity_gate", lambda: {"status": "FAIL"})
    report = readiness.build_readiness_report()
    assert report["status"] == "NOT_READY"
    assert report["offline_infrastructure_ready"] is False
    assert report["selection_collection_allowed"] is False
    assert report["next_command"] is None
    assert "INTEGRITY_GATE_FAILED" in report["blockers"]


def test_write_report_round_trip(tmp_path):
    import json
    report = readiness.build_readiness_report()
    path = readiness.write_report(report, tmp_path / "readiness.json")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["report"] == readiness.REPORT_VERSION
    assert loaded["status"] == report["status"]
