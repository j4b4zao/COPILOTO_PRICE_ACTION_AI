from tools.profit_rtd_brooks_failed_breakout_audit import _opposite_choch


def _row(*, choch, trend):
    return {"structure": {"choch": choch, "trend": trend}}


def test_up_breakout_is_invalidated_by_boolean_choch_with_down_trend():
    assert _opposite_choch(_row(choch=True, trend="DOWN"), "UP") is True


def test_down_breakout_is_invalidated_by_boolean_choch_with_up_trend():
    assert _opposite_choch(_row(choch=True, trend="UP"), "DOWN") is True


def test_same_direction_choch_does_not_invalidate_up_breakout():
    assert _opposite_choch(_row(choch=True, trend="UP"), "UP") is False


def test_same_direction_choch_does_not_invalidate_down_breakout():
    assert _opposite_choch(_row(choch=True, trend="DOWN"), "DOWN") is False


def test_false_choch_never_invalidates():
    assert _opposite_choch(_row(choch=False, trend="DOWN"), "UP") is False
    assert _opposite_choch(_row(choch=False, trend="UP"), "DOWN") is False


def test_direction_aliases_follow_producer_semantics():
    assert _opposite_choch(_row(choch=True, trend="BEARISH"), "UP") is True
    assert _opposite_choch(_row(choch=True, trend="BULLISH"), "DOWN") is True
