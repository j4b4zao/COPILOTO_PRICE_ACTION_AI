import tools.profit_rtd_brooks_collection_preflight as preflight


def test_real_preflight_passes_offline():
    report = preflight.run_preflight(symbol="WINV26")
    assert report["status"] == "PASS"
    assert report["selection_launcher_allowed"] is True
    assert report["blockers"] == []


def test_preflight_only_releases_selection_command():
    report = preflight.run_preflight(symbol="WINV26")
    assert report["launcher_mode"] == "SELECTION"
    assert report["launcher_command"] == "python -m tools.profit_rtd_brooks_selection_launcher WINV26"
    assert report["oos_collection_allowed"] is False


def test_preflight_does_not_execute_or_claim_market_state():
    report = preflight.run_preflight()
    assert report["launcher_executed"] is False
    assert report["market_data_checked"] is False
    assert report["market_open_claimed"] is False


def test_preflight_preserves_operational_isolation():
    report = preflight.run_preflight()
    for flag in (
        "predictive_claim_allowed",
        "score_influence_allowed",
        "risk_influence_allowed",
        "decision_influence_allowed",
        "alert_influence_allowed",
        "order_execution_allowed",
        "promotion_allowed",
        "hypothesis_freeze_allowed",
    ):
        assert report[flag] is False


def test_integrity_failure_blocks_launcher(monkeypatch):
    monkeypatch.setattr(preflight, "run_integrity_gate", lambda: {"status": "FAIL"})
    report = preflight.run_preflight()
    assert report["status"] == "BLOCKED"
    assert report["selection_launcher_allowed"] is False
    assert report["launcher_command"] is None
    assert "INTEGRITY_GATE_FAILED" in report["blockers"]


def test_readiness_failure_blocks_launcher(monkeypatch):
    monkeypatch.setattr(preflight, "build_readiness_report", lambda **kwargs: {
        "offline_infrastructure_ready": False,
        "oos_collection_allowed": False,
        "next_command_mode": None,
        "status": "NOT_READY",
    })
    report = preflight.run_preflight()
    assert report["status"] == "BLOCKED"
    assert "READINESS_NOT_READY" in report["blockers"]


def test_invalid_oos_guard_blocks_launcher(monkeypatch):
    monkeypatch.setattr(preflight, "build_readiness_report", lambda **kwargs: {
        "offline_infrastructure_ready": True,
        "oos_collection_allowed": True,
        "next_command_mode": "SELECTION",
        "status": "READY_FOR_SELECTION_COLLECTION",
    })
    report = preflight.run_preflight()
    assert report["status"] == "BLOCKED"
    assert "OOS_GUARD_INVALID" in report["blockers"]


def test_non_selection_mode_blocks_launcher(monkeypatch):
    monkeypatch.setattr(preflight, "build_readiness_report", lambda **kwargs: {
        "offline_infrastructure_ready": True,
        "oos_collection_allowed": False,
        "next_command_mode": "OOS",
        "status": "READY_FOR_SELECTION_COLLECTION",
    })
    report = preflight.run_preflight()
    assert report["status"] == "BLOCKED"
    assert "SELECTION_MODE_NOT_ENFORCED" in report["blockers"]
