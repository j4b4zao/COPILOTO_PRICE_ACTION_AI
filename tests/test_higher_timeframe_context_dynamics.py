from analysis.price_action.higher_timeframe_context_dynamics import HigherTimeframeContextDynamics


def test_full_alignment_buy():
    r = HigherTimeframeContextDynamics().analyze(
        daily={"direction": "BUY", "quality_score": 80},
        weekly={"direction": "BUY", "quality_score": 85},
        monthly={"direction": "BUY", "quality_score": 90},
    )
    assert r.status == "HIGHER_TIMEFRAME_FULL_ALIGNMENT"
    assert r.direction == "BUY"
    assert r.alignment_count == 3


def test_partial_alignment_with_missing_monthly():
    r = HigherTimeframeContextDynamics().analyze(
        daily="SELL",
        weekly="SELL",
        monthly=None,
    )
    assert r.status == "HIGHER_TIMEFRAME_PARTIAL_ALIGNMENT"
    assert r.direction == "SELL"
    assert r.alignment_count == 2


def test_mixed_context_keeps_majority_bias():
    r = HigherTimeframeContextDynamics().analyze(
        daily="BUY",
        weekly="BUY",
        monthly="SELL",
    )
    assert r.status == "HIGHER_TIMEFRAME_MIXED"
    assert r.direction == "BUY"
    assert r.conflict_count == 1


def test_neutral_context():
    r = HigherTimeframeContextDynamics().analyze(
        daily="NONE",
        weekly=None,
        monthly={"direction": "NONE"},
    )
    assert r.status == "HIGHER_TIMEFRAME_NEUTRAL"
    assert r.direction == "NONE"


def test_invalid_direction_is_ignored_and_single_valid_context_remains():
    r = HigherTimeframeContextDynamics().analyze(
        daily="SIDEWAYS",
        weekly="BUY",
        monthly=None,
    )
    assert r.status == "HIGHER_TIMEFRAME_SINGLE_CONTEXT"
    assert r.direction == "BUY"
    assert r.execution_allowed


def test_higher_timeframe_never_forces_execution_block():
    r = HigherTimeframeContextDynamics().analyze(
        daily="SELL",
        weekly="SELL",
        monthly="SELL",
    )
    assert r.execution_allowed is True
