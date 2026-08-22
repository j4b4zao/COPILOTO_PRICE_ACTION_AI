from types import SimpleNamespace

from analysis.replay.book_diagnostics_probation_runtime_adapter import (
    BookDiagnosticsProbationRuntimeAdapter,
)


def _contract(**overrides):
    data = {
        "book_state": "CLEAN_DIRECTIONAL_CONTEXT",
        "target_layer": "EVIDENCE",
        "initial_weight": 0.2,
        "probation_samples": 40,
        "rollback_edge_r": 0.0,
        "rollback_stop_first_rate": 0.5,
        "rollback_direction_correct_rate": 0.5,
        "runtime_active": False,
        "status": "DRAFT_FOR_MANUAL_APPROVAL",
    }
    data.update(overrides)
    return SimpleNamespace(to_dict=lambda: dict(data))


def _approval(**overrides):
    data = {
        "book_state": "CLEAN_DIRECTIONAL_CONTEXT",
        "target_layer": "EVIDENCE",
        "status": "APPROVED_FOR_PROBATION",
        "runtime_active": False,
    }
    data.update(overrides)
    return SimpleNamespace(to_dict=lambda: dict(data))


def _metrics(completed, *, edge=0.2, stop=0.3, direction=0.6):
    return {
        "completed": completed,
        "avg_edge_r": edge,
        "stop_first_rate": stop,
        "direction_correct_rate": direction,
    }


def _raises(exc_type, fn):
    try:
        fn()
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def test_requires_rc22_probation_approval():
    _raises(
        PermissionError,
        lambda: BookDiagnosticsProbationRuntimeAdapter(
            _contract(),
            _approval(status="PENDING_MANUAL_APPROVAL"),
        ),
    )


def test_activation_is_explicit_and_identified():
    adapter = BookDiagnosticsProbationRuntimeAdapter(_contract(), _approval())
    assert adapter.state.runtime_active is False

    _raises(ValueError, lambda: adapter.activate(activated_by=""))
    state = adapter.activate(activated_by="manual-reviewer")

    assert state.runtime_active is True
    assert state.status == "PROBATION_ACTIVE"
    assert state.activated_by == "manual-reviewer"


def test_contribution_respects_contract_weight():
    adapter = BookDiagnosticsProbationRuntimeAdapter(_contract(initial_weight=0.15), _approval())
    adapter.activate(activated_by="reviewer")

    contribution = adapter.contribution(80.0, metadata={"signal": "BUY"})

    assert contribution["weighted_value"] == 12.0
    assert contribution["weight"] == 0.15
    assert contribution["probation_only"] is True


def test_guardrail_violation_rolls_back_immediately_after_probation_threshold():
    adapter = BookDiagnosticsProbationRuntimeAdapter(_contract(probation_samples=40), _approval())
    adapter.activate(activated_by="reviewer")

    state = adapter.record_metrics(_metrics(40, edge=-0.1))

    assert state.status == "ROLLED_BACK"
    assert state.runtime_active is False
    assert state.rollback_triggered is True
    assert state.rollback_reason == "RC21_GUARDRAIL_VIOLATION"


def test_probation_completes_without_automatic_promotion():
    adapter = BookDiagnosticsProbationRuntimeAdapter(_contract(probation_samples=40), _approval())
    adapter.activate(activated_by="reviewer")

    state = adapter.record_metrics(_metrics(40, edge=0.3, stop=0.2, direction=0.7))

    assert state.status == "PROBATION_COMPLETE_AWAITING_REVIEW"
    assert state.runtime_active is False
    assert state.rollback_triggered is False


def test_metrics_below_probation_threshold_keep_runtime_active():
    adapter = BookDiagnosticsProbationRuntimeAdapter(_contract(probation_samples=40), _approval())
    adapter.activate(activated_by="reviewer")

    state = adapter.record_metrics(_metrics(20, edge=-0.3, stop=0.8, direction=0.2))

    assert state.status == "PROBATION_ACTIVE"
    assert state.runtime_active is True
    assert state.rollback_triggered is False


def test_manual_stop_disables_runtime_without_rollback():
    adapter = BookDiagnosticsProbationRuntimeAdapter(_contract(), _approval())
    adapter.activate(activated_by="reviewer")

    state = adapter.manual_stop(note="session ended")

    assert state.status == "PROBATION_STOPPED_MANUALLY"
    assert state.runtime_active is False
    assert state.rollback_triggered is False


def test_contract_and_approval_must_match():
    _raises(
        ValueError,
        lambda: BookDiagnosticsProbationRuntimeAdapter(
            _contract(target_layer="CONTEXT"),
            _approval(target_layer="EVIDENCE"),
        ),
    )
