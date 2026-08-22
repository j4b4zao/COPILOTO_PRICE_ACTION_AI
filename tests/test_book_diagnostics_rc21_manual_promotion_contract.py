from types import SimpleNamespace

from analysis.replay.book_diagnostics_manual_promotion_contract import (
    BookDiagnosticsManualPromotionContractBuilder,
)


def _review(recommendation="ELIGIBLE_FOR_MANUAL_PROMOTION"):
    return SimpleNamespace(
        to_dict=lambda: {
            "book_state": "CLEAN_DIRECTIONAL_CONTEXT",
            "recommendation": recommendation,
        }
    )


def _expect_error(exc_type, fn):
    try:
        fn()
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def test_contract_starts_inactive_and_requires_manual_approval():
    contract = BookDiagnosticsManualPromotionContractBuilder().build(
        _review(),
        target_layer="EVIDENCE",
    )
    assert contract.status == "DRAFT_FOR_MANUAL_APPROVAL"
    assert contract.manual_approval_required is True
    assert contract.runtime_active is False


def test_non_eligible_review_is_blocked():
    builder = BookDiagnosticsManualPromotionContractBuilder()
    _expect_error(
        PermissionError,
        lambda: builder.build(
            _review("KEEP_SHADOW"),
            target_layer="CONTEXT",
        ),
    )


def test_target_weight_caps_are_enforced():
    builder = BookDiagnosticsManualPromotionContractBuilder()
    _expect_error(
        ValueError,
        lambda: builder.build(
            _review(),
            target_layer="RISK",
            initial_weight=0.11,
        ),
    )


def test_risk_target_uses_strict_default_cap():
    contract = BookDiagnosticsManualPromotionContractBuilder().build(
        _review(),
        target_layer="RISK",
    )
    assert contract.initial_weight == 0.10
    assert "RISK_TARGET_EXCEPTIONAL" in contract.reasons


def test_probation_minimum_is_enforced():
    builder = BookDiagnosticsManualPromotionContractBuilder(min_probation_samples=40)
    _expect_error(
        ValueError,
        lambda: builder.build(
            _review(),
            target_layer="CONTEXT",
            probation_samples=20,
        ),
    )


def test_rollback_not_triggered_before_probation():
    builder = BookDiagnosticsManualPromotionContractBuilder(min_probation_samples=40)
    contract = builder.build(_review(), target_layer="EVIDENCE")
    assert builder.rollback_required(
        contract,
        {
            "completed": 20,
            "avg_edge_r": -1.0,
            "stop_first_rate": 1.0,
            "direction_correct_rate": 0.0,
        },
    ) is False


def test_rollback_triggered_after_probation_on_edge_degradation():
    builder = BookDiagnosticsManualPromotionContractBuilder(min_probation_samples=40)
    contract = builder.build(_review(), target_layer="EVIDENCE")
    assert builder.rollback_required(
        contract,
        {
            "completed": 40,
            "avg_edge_r": -0.01,
            "stop_first_rate": 0.30,
            "direction_correct_rate": 0.60,
        },
    ) is True


def test_healthy_probation_metrics_do_not_trigger_rollback():
    builder = BookDiagnosticsManualPromotionContractBuilder(min_probation_samples=40)
    contract = builder.build(_review(), target_layer="CHECKLIST")
    assert builder.rollback_required(
        contract,
        {
            "completed": 50,
            "avg_edge_r": 0.30,
            "stop_first_rate": 0.35,
            "direction_correct_rate": 0.65,
        },
    ) is False
