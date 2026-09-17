"""
tests/research/price_action/brooks/test_structural_trailing_diagnostics_v3.py

Isolated contract tests for Brooks Structural Trailing Diagnostics V3.
Research-only. No operational influence.
"""

from tools import profit_rtd_brooks_structural_trailing_diagnostics_v3 as v3


def test_stage_and_reference_contract():
    assert v3.STAGE == "BROOKS_STRUCTURAL_TRAILING_DIAGNOSTICS_V3"
    assert (
        v3.v2.STAGE
        == "BROOKS_STRUCTURAL_ADVANCE_GATE_DIAGNOSTICS_V2_1"
    )


def test_safety_contract_is_research_only():
    safety = v3._safety()

    assert safety["research_only"] is True
    assert safety["diagnostic_only"] is True
    assert safety["observational_only"] is True

    assert safety["source_session_validity_changed"] is False
    assert safety["selection_eligibility_changed"] is False
    assert safety["oos_eligibility_changed"] is False

    assert safety["predictive_claim_allowed"] is False
    assert safety["score_influence_allowed"] is False
    assert safety["risk_influence_allowed"] is False
    assert safety["decision_influence_allowed"] is False
    assert safety["alert_influence_allowed"] is False
    assert safety["order_execution_allowed"] is False

    assert safety["performance_validated"] is False
    assert safety["promotion_allowed"] is False
    assert safety["hypothesis_freeze_allowed"] is False


def test_buy_candidate_uses_reference_swing_minus_tick():
    assert v3._candidate("BUY", 100.0, 5.0) == 95.0


def test_sell_candidate_uses_reference_swing_plus_tick():
    assert v3._candidate("SELL", 100.0, 5.0) == 105.0


def test_candidate_none_when_reference_swing_missing():
    assert v3._candidate("BUY", None, 5.0) is None
    assert v3._candidate("SELL", None, 5.0) is None


def test_buy_candidate_relation():
    assert v3._relation("BUY", 101.0, 100.0) == "TIGHTER"
    assert v3._relation("BUY", 100.0, 100.0) == "EQUAL"
    assert v3._relation("BUY", 99.0, 100.0) == "LOOSER"


def test_sell_candidate_relation():
    assert v3._relation("SELL", 99.0, 100.0) == "TIGHTER"
    assert v3._relation("SELL", 100.0, 100.0) == "EQUAL"
    assert v3._relation("SELL", 101.0, 100.0) == "LOOSER"


def _all_gates_true():
    return {
        "history_ready": True,
        "pivot_any": True,
        "reference_swing_present": True,
        "prior_opposite_pivot_present": True,
        "later_opposite_pivot_present": True,
        "both_sides_present": True,
        "breakout_confirmed": True,
    }


def _engine_case(
    *,
    state,
    structural=True,
    improved=False,
    loosened=False,
):
    return {
        "state": state,
        "structural_advance_confirmed": structural,
        "stop_improved": improved,
        "stop_loosened": loosened,
    }


def test_blocked_reason_reports_structural_but_not_tighter():
    gates = _all_gates_true()
    engine = _engine_case(
        state="TRAILING_STOP_HOLD",
        structural=True,
        improved=False,
    )

    assert (
        v3._blocked(gates, engine)
        == "STRUCTURAL_ADVANCE_BUT_NO_TIGHTER_STOP"
    )


def test_blocked_reason_reports_advance_only_for_official_advance():
    gates = _all_gates_true()
    engine = _engine_case(
        state="TRAILING_STOP_ADVANCE",
        structural=True,
        improved=True,
    )

    assert v3._blocked(gates, engine) == "ADVANCE"


def test_blocked_reason_preserves_structural_gate_order():
    gates = _all_gates_true()
    gates["breakout_confirmed"] = False

    engine = _engine_case(
        state="PROTECTIVE_STOP_HOLD",
        structural=False,
        improved=False,
    )

    assert (
        v3._blocked(gates, engine)
        == "STRUCTURAL_BREAKOUT_NOT_CONFIRMED"
    )


def test_empty_payload_is_safe_and_has_no_advance():
    report = v3.diagnose_session(
        {"samples": []},
        tick_size=1.0,
    )

    assert report["raw_samples"] == 0
    assert report["exact_candles"] == 0
    assert report["eligible_entry_episodes"] == 0
    assert report["observation_count"] == 0
    assert report["structural_case_count"] == 0
    assert report["advance_case_count"] == 0
    assert report["mismatch_counts"] == {}
