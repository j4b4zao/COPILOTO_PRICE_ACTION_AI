from types import SimpleNamespace

from analysis.replay.book_diagnostics_post_probation_review import (
    BookDiagnosticsPostProbationReviewer,
)


STATE = "CLEAN_DIRECTIONAL_CONTEXT"


def _contract(**overrides):
    data = {
        "book_state": STATE,
        "target_layer": "CONTEXT",
        "probation_samples": 40,
        "rollback_edge_r": 0.0,
        "rollback_stop_first_rate": 0.50,
        "rollback_direction_correct_rate": 0.50,
    }
    data.update(overrides)
    return SimpleNamespace(to_dict=lambda: dict(data))


def _runtime(**overrides):
    data = {
        "book_state": STATE,
        "target_layer": "CONTEXT",
        "status": "PROBATION_COMPLETE_AWAITING_REVIEW",
        "runtime_active": False,
        "samples_seen": 40,
        "rollback_triggered": False,
    }
    data.update(overrides)
    return SimpleNamespace(to_dict=lambda: dict(data))


def test_strong_completed_probation_is_promote_candidate():
    review = BookDiagnosticsPostProbationReviewer().evaluate(
        _runtime(),
        _contract(),
        {
            "completed": 40,
            "avg_edge_r": 0.25,
            "stop_first_rate": 0.35,
            "direction_correct_rate": 0.65,
        },
    )
    assert review.recommendation == "PROMOTE"
    assert review.manual_approval_required is True
    assert review.runtime_active is False
    assert "NO_AUTOMATIC_RUNTIME_PROMOTION" in review.reasons


def test_incomplete_probation_extends():
    review = BookDiagnosticsPostProbationReviewer().evaluate(
        _runtime(status="PROBATION_ACTIVE", runtime_active=True, samples_seen=20),
        _contract(),
        {
            "completed": 20,
            "avg_edge_r": 0.30,
            "stop_first_rate": 0.20,
            "direction_correct_rate": 0.70,
        },
    )
    assert review.recommendation == "EXTEND_PROBATION"
    assert review.manual_approval_required is False


def test_rolled_back_probation_stays_rollback():
    review = BookDiagnosticsPostProbationReviewer().evaluate(
        _runtime(status="ROLLED_BACK", rollback_triggered=True),
        _contract(),
        {
            "completed": 40,
            "avg_edge_r": -0.20,
            "stop_first_rate": 0.70,
            "direction_correct_rate": 0.35,
        },
    )
    assert review.recommendation == "ROLLBACK"


def test_manual_stop_returns_to_research():
    review = BookDiagnosticsPostProbationReviewer().evaluate(
        _runtime(status="PROBATION_STOPPED_MANUALLY"),
        _contract(),
        {
            "completed": 15,
            "avg_edge_r": 0.10,
            "stop_first_rate": 0.40,
            "direction_correct_rate": 0.55,
        },
    )
    assert review.recommendation == "RETURN_TO_RESEARCH"


def test_safe_but_not_strong_enough_extends_probation():
    review = BookDiagnosticsPostProbationReviewer().evaluate(
        _runtime(),
        _contract(),
        {
            "completed": 40,
            "avg_edge_r": 0.05,
            "stop_first_rate": 0.48,
            "direction_correct_rate": 0.52,
        },
    )
    assert review.recommendation == "EXTEND_PROBATION"


def test_contract_guardrail_violation_rolls_back():
    review = BookDiagnosticsPostProbationReviewer().evaluate(
        _runtime(),
        _contract(),
        {
            "completed": 40,
            "avg_edge_r": -0.01,
            "stop_first_rate": 0.40,
            "direction_correct_rate": 0.60,
        },
    )
    assert review.recommendation == "ROLLBACK"


def test_mismatched_contract_is_rejected():
    try:
        BookDiagnosticsPostProbationReviewer().evaluate(
            _runtime(),
            _contract(book_state="OTHER"),
            {"completed": 40},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched contract should fail")
