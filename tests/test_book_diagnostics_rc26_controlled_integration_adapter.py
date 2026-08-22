from types import SimpleNamespace

from analysis.replay.book_diagnostics_controlled_integration_adapter import (
    BookDiagnosticsControlledIntegrationAdapter,
)


def _record(**overrides):
    data = {
        "book_state": "CLEAN_DIRECTIONAL_CONTEXT",
        "target_layer": "CONTEXT",
        "approved_weight": 0.15,
        "source_version": "RC25",
        "rollback_plan": {
            "min_avg_edge_r": 0.05,
            "max_stop_first_rate": 0.50,
            "min_direction_correct_rate": 0.55,
        },
        "status": "APPROVED_FOR_INTEGRATION",
        "runtime_active": False,
    }
    data.update(overrides)
    return SimpleNamespace(to_dict=lambda: dict(data))


def _raises(exc, fn):
    try:
        fn()
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


def test_requires_final_approval():
    _raises(
        PermissionError,
        lambda: BookDiagnosticsControlledIntegrationAdapter(
            _record(status="PENDING_FINAL_APPROVAL")
        ),
    )


def test_risk_is_blocked_in_rc26():
    _raises(
        PermissionError,
        lambda: BookDiagnosticsControlledIntegrationAdapter(_record(target_layer="RISK")),
    )


def test_activation_is_explicit_and_weight_is_preserved():
    adapter = BookDiagnosticsControlledIntegrationAdapter(_record())
    assert adapter.state.runtime_active is False
    _raises(ValueError, lambda: adapter.activate(activated_by=""))

    state = adapter.activate(activated_by="manual-reviewer")
    assert state.runtime_active is True
    event = adapter.contribution(10.0, metadata={"cycle": 1})
    assert event["weighted_value"] == 1.5
    assert event["weight"] == 0.15
    assert event["controlled_integration"] is True


def test_guardrail_violation_rolls_back_immediately():
    adapter = BookDiagnosticsControlledIntegrationAdapter(_record())
    adapter.activate(activated_by="manual-reviewer")
    state = adapter.evaluate_rollback({
        "avg_edge_r": -0.10,
        "stop_first_rate": 0.60,
        "direction_correct_rate": 0.40,
    })
    assert state.status == "ROLLED_BACK"
    assert state.runtime_active is False
    assert state.rollback_triggered is True
    _raises(PermissionError, lambda: adapter.activate(activated_by="manual-reviewer"))


def test_healthy_metrics_keep_integration_active():
    adapter = BookDiagnosticsControlledIntegrationAdapter(_record())
    adapter.activate(activated_by="manual-reviewer")
    state = adapter.evaluate_rollback({
        "avg_edge_r": 0.25,
        "stop_first_rate": 0.30,
        "direction_correct_rate": 0.70,
    })
    assert state.status == "INTEGRATION_ACTIVE"
    assert state.runtime_active is True


def test_manual_stop_disables_runtime():
    adapter = BookDiagnosticsControlledIntegrationAdapter(_record(target_layer="CHECKLIST"))
    adapter.activate(activated_by="manual-reviewer")
    state = adapter.manual_stop(note="maintenance")
    assert state.status == "STOPPED_MANUALLY"
    assert state.runtime_active is False


def test_runtime_active_final_record_is_rejected():
    _raises(
        PermissionError,
        lambda: BookDiagnosticsControlledIntegrationAdapter(_record(runtime_active=True)),
    )


if __name__ == "__main__":
    test_requires_final_approval()
    test_risk_is_blocked_in_rc26()
    test_activation_is_explicit_and_weight_is_preserved()
    test_guardrail_violation_rolls_back_immediately()
    test_healthy_metrics_keep_integration_active()
    test_manual_stop_disables_runtime()
    test_runtime_active_final_record_is_rejected()
    print("RC26 controlled integration adapter tests: OK")
