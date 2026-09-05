import tools.profit_rtd_brooks_smoke_report as smoke


def test_real_smoke_report_passes():
    report = smoke.build_smoke_report(symbol="WINV26")
    assert report["status"] == "PASS"
    assert report["offline_stack_ready"] is True
    assert report["blockers"] == []


def test_registry_and_evidence_cover_same_seven_families():
    report = smoke.build_smoke_report()
    assert report["registered_family_count"] == 7
    assert report["evidence_family_count"] == 7
    assert set(report["registered_families"]) == set(report["evidence_families"])


def test_smoke_report_preserves_selection_only_boundary():
    report = smoke.build_smoke_report(symbol="WINV26")
    assert report["selection_only"] is True
    assert report["oos_collection_allowed"] is False
    assert report["next_command"] == "python -m tools.profit_rtd_brooks_selection_launcher WINV26"


def test_smoke_report_does_not_touch_market_or_launcher():
    report = smoke.build_smoke_report()
    assert report["market_data_checked"] is False
    assert report["market_open_claimed"] is False
    assert report["launcher_executed"] is False


def test_smoke_report_preserves_operational_isolation():
    report = smoke.build_smoke_report()
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


def test_integrity_failure_fails_smoke(monkeypatch):
    monkeypatch.setattr(smoke, "run_integrity_gate", lambda: {"status": "FAIL"})
    report = smoke.build_smoke_report()
    assert report["status"] == "FAIL"
    assert report["offline_stack_ready"] is False
    assert "INTEGRITY_GATE_FAILED" in report["blockers"]
    assert report["next_command"] is None


def test_readiness_failure_fails_smoke(monkeypatch):
    monkeypatch.setattr(smoke, "build_readiness_report", lambda **kwargs: {
        "offline_infrastructure_ready": False,
        "status": "NOT_READY",
    })
    report = smoke.build_smoke_report()
    assert report["status"] == "FAIL"
    assert "READINESS_NOT_READY" in report["blockers"]


def test_preflight_failure_fails_smoke(monkeypatch):
    monkeypatch.setattr(smoke, "run_preflight", lambda **kwargs: {
        "selection_launcher_allowed": False,
        "status": "BLOCKED",
        "launcher_command": None,
    })
    report = smoke.build_smoke_report()
    assert report["status"] == "FAIL"
    assert "PREFLIGHT_BLOCKED" in report["blockers"]


def test_family_mismatch_fails_smoke(monkeypatch):
    class FakeRegistry:
        @classmethod
        def entries(cls):
            return ()
    monkeypatch.setattr(smoke, "BrooksResearchRegistry", FakeRegistry)
    report = smoke.build_smoke_report()
    assert report["status"] == "FAIL"
    assert "REGISTRY_COUNT_INVALID" in report["blockers"]
    assert "REGISTRY_EVIDENCE_FAMILY_MISMATCH" in report["blockers"]
