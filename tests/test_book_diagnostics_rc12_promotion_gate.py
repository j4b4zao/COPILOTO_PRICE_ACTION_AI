from analysis.replay.book_diagnostics_promotion_gate import (
    BookDiagnosticsPromotionGate,
)


def good_metrics(samples=80):
    return {
        "directional_samples": samples,
        "edge_r": 0.35,
        "book_target_first_rate": 0.62,
        "book_stop_first_rate": 0.28,
        "future_direction_alignment_rate": 0.64,
    }


def stable_session(edge=0.20, target=0.60, stop=0.30):
    return {
        "directional_samples": 20,
        "edge_r": edge,
        "book_target_first_rate": target,
        "book_stop_first_rate": stop,
    }


def test_candidate_requires_sample_quality_and_session_stability():
    gate = BookDiagnosticsPromotionGate()
    result = gate.evaluate(
        good_metrics(),
        [stable_session(), stable_session(), stable_session()],
    )

    assert result.status == "CANDIDATE_FOR_PROMOTION"
    assert result.eligible is True
    assert result.stability_rate == 1.0
    assert "MANUAL_REVIEW_REQUIRED" in result.reasons
    assert "OUT_OF_SAMPLE_VALIDATION_REQUIRED" in result.reasons


def test_small_sample_keeps_observing_even_when_metrics_look_good():
    gate = BookDiagnosticsPromotionGate()
    result = gate.evaluate(
        good_metrics(samples=12),
        [stable_session(), stable_session(), stable_session()],
    )

    assert result.status == "KEEP_OBSERVING"
    assert result.eligible is False
    assert "INSUFFICIENT_SAMPLE" in result.reasons


def test_non_positive_edge_is_rejected_after_minimum_sample():
    gate = BookDiagnosticsPromotionGate()
    metrics = good_metrics(samples=45)
    metrics["edge_r"] = -0.05

    result = gate.evaluate(
        metrics,
        [stable_session(), stable_session(), stable_session()],
    )

    assert result.status == "REJECTED"
    assert "NON_POSITIVE_EDGE" in result.reasons


def test_high_stop_first_rate_is_rejected():
    gate = BookDiagnosticsPromotionGate()
    metrics = good_metrics(samples=60)
    metrics["book_stop_first_rate"] = 0.58

    result = gate.evaluate(
        metrics,
        [stable_session(), stable_session(), stable_session()],
    )

    assert result.status == "REJECTED"
    assert "STOP_FIRST_RATE_TOO_HIGH" in result.reasons


def test_unstable_sessions_keep_observing_not_promote():
    gate = BookDiagnosticsPromotionGate()
    unstable = stable_session(edge=-0.10, target=0.40, stop=0.60)

    result = gate.evaluate(
        good_metrics(),
        [stable_session(), unstable, unstable],
    )

    assert result.status == "KEEP_OBSERVING"
    assert result.eligible is False
    assert result.stability_rate < gate.min_stability_rate
    assert "SESSION_STABILITY_BELOW_THRESHOLD" in result.reasons


def test_gate_never_implies_automatic_runtime_promotion():
    gate = BookDiagnosticsPromotionGate()
    result = gate.evaluate(
        good_metrics(),
        [stable_session(), stable_session(), stable_session()],
    )

    assert result.status == "CANDIDATE_FOR_PROMOTION"
    assert "MANUAL_REVIEW_REQUIRED" in result.reasons
    assert not hasattr(result, "apply_to_score")
    assert not hasattr(result, "apply_to_risk")
    assert not hasattr(result, "apply_to_decision")
