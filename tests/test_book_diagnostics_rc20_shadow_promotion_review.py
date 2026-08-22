from types import SimpleNamespace

from analysis.replay.book_diagnostics_shadow_promotion_review import (
    BookDiagnosticsShadowPromotionReviewer,
)


STATE = "CLEAN_DIRECTIONAL_CONTEXT"


def _metrics(
    *,
    completed=100,
    target=0.60,
    stop=0.30,
    direction=0.65,
    edge=0.40,
):
    return {
        "book_state": STATE,
        "completed": completed,
        "target_first_rate": target,
        "stop_first_rate": stop,
        "direction_correct_rate": direction,
        "avg_mfe_r": 1.10,
        "avg_mae_r": 0.70,
        "avg_edge_r": edge,
    }


def _record(status="APPROVED_FOR_SHADOW", state=STATE):
    return SimpleNamespace(book_state=state, status=status)


def test_strong_shadow_evidence_is_eligible_for_manual_promotion():
    reviewer = BookDiagnosticsShadowPromotionReviewer(
        min_samples=10,
        promotion_samples=20,
    )
    review = reviewer.evaluate(_metrics(completed=25), registry_record=_record())

    assert review.recommendation == "ELIGIBLE_FOR_MANUAL_PROMOTION"
    assert review.manual_review_required is True
    assert "NO_AUTOMATIC_RUNTIME_PROMOTION" in review.reasons


def test_small_sample_keeps_candidate_in_shadow():
    reviewer = BookDiagnosticsShadowPromotionReviewer(min_samples=30)
    review = reviewer.evaluate(_metrics(completed=12), registry_record=_record())

    assert review.recommendation == "KEEP_SHADOW"
    assert "SHADOW_SAMPLE_TOO_SMALL" in review.reasons


def test_negative_edge_rejects_candidate_after_minimum_sample():
    reviewer = BookDiagnosticsShadowPromotionReviewer(min_samples=20)
    review = reviewer.evaluate(
        _metrics(completed=40, edge=-0.20),
        registry_record=_record(),
    )

    assert review.recommendation == "REJECT_CANDIDATE"
    assert "NEGATIVE_SHADOW_EDGE" in review.reasons


def test_excessive_stop_rate_rejects_candidate():
    reviewer = BookDiagnosticsShadowPromotionReviewer(min_samples=20)
    review = reviewer.evaluate(
        _metrics(completed=40, stop=0.70),
        registry_record=_record(),
    )

    assert review.recommendation == "REJECT_CANDIDATE"
    assert "EXCESSIVE_SHADOW_STOP_RATE" in review.reasons


def test_mediocre_shadow_results_return_to_research():
    reviewer = BookDiagnosticsShadowPromotionReviewer(min_samples=20)
    review = reviewer.evaluate(
        _metrics(completed=50, target=0.45, stop=0.45, direction=0.45, edge=0.05),
        registry_record=_record(),
    )

    assert review.recommendation == "RETURN_TO_RESEARCH"
    assert "SHADOW_EDGE_BELOW_THRESHOLD" in review.reasons


def test_good_quality_without_promotion_sample_keeps_shadow():
    reviewer = BookDiagnosticsShadowPromotionReviewer(
        min_samples=10,
        promotion_samples=50,
    )
    review = reviewer.evaluate(_metrics(completed=30), registry_record=_record())

    assert review.recommendation == "KEEP_SHADOW"
    assert "QUALITY_CONFIRMED_BUT_PROMOTION_SAMPLE_NOT_REACHED" in review.reasons


def test_non_shadow_candidate_cannot_be_reviewed():
    reviewer = BookDiagnosticsShadowPromotionReviewer()
    try:
        reviewer.evaluate(_metrics(), registry_record=_record("RESEARCHING"))
    except PermissionError:
        pass
    else:
        raise AssertionError("expected PermissionError")


def test_registry_state_must_match_metrics_state():
    reviewer = BookDiagnosticsShadowPromotionReviewer()
    try:
        reviewer.evaluate(_metrics(), registry_record=_record(state="OTHER"))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
