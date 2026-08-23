from analysis.market_regime import MarketRegime
from models.regime_result import RegimeResult
from enums.trend import Trend


def _result(regime: str, trend: Trend = Trend.SIDEWAYS) -> RegimeResult:
    result = RegimeResult()
    result.regime = regime
    result.trend = trend
    result.strength = 0.80
    result.confidence = 0.85
    return result


def test_rc3_version():
    assert MarketRegime.VERSION == "RC3.0-TRANSITION-CONFIRMATION"
    assert MarketRegime.CHANGE_CONFIRMATIONS_REQUIRED == 2


def test_first_stable_regime_establishes_baseline():
    engine = MarketRegime()
    result = _result("TREND_UP", Trend.UP)
    engine._confirm_regime_change(result)
    assert result.regime == "TREND_UP"
    assert result.previous_regime == "TREND_UP"
    assert result.regime_changed is False


def test_first_different_candidate_becomes_transition():
    engine = MarketRegime()
    engine._confirm_regime_change(_result("TREND_UP", Trend.UP))

    result = _result("RANGE")
    engine._confirm_regime_change(result)

    assert result.regime == "TRANSITION"
    assert result.previous_regime == "TREND_UP"
    assert result.pending_regime == "RANGE"
    assert result.confirmation_count == 1
    assert result.regime_changed is False
    assert result.trend == Trend.SIDEWAYS


def test_second_same_candidate_confirms_change():
    engine = MarketRegime()
    engine._confirm_regime_change(_result("TREND_UP", Trend.UP))
    engine._confirm_regime_change(_result("RANGE"))

    result = _result("RANGE")
    engine._confirm_regime_change(result)

    assert result.regime == "RANGE"
    assert result.previous_regime == "TREND_UP"
    assert result.pending_regime == "UNKNOWN"
    assert result.confirmation_count == 2
    assert result.regime_changed is True


def test_pending_candidate_resets_when_confirmed_regime_returns():
    engine = MarketRegime()
    engine._confirm_regime_change(_result("TREND_UP", Trend.UP))
    engine._confirm_regime_change(_result("RANGE"))

    result = _result("TREND_UP", Trend.UP)
    engine._confirm_regime_change(result)

    assert result.regime == "TREND_UP"
    assert result.pending_regime == "UNKNOWN"
    assert result.confirmation_count == 0
    assert result.regime_changed is False


def test_raw_transition_does_not_replace_confirmed_regime():
    engine = MarketRegime()
    engine._confirm_regime_change(_result("TREND_DOWN", Trend.DOWN))

    result = _result("TRANSITION")
    engine._confirm_regime_change(result)

    assert result.regime == "TRANSITION"
    assert result.previous_regime == "TREND_DOWN"
    assert result.pending_regime == "UNKNOWN"
    assert result.regime_changed is False


def test_direct_reversal_also_requires_two_confirmations():
    engine = MarketRegime()
    engine._confirm_regime_change(_result("TREND_UP", Trend.UP))

    first = _result("TREND_DOWN", Trend.DOWN)
    engine._confirm_regime_change(first)
    assert first.regime == "TRANSITION"
    assert first.pending_regime == "TREND_DOWN"

    second = _result("TREND_DOWN", Trend.DOWN)
    engine._confirm_regime_change(second)
    assert second.regime == "TREND_DOWN"
    assert second.regime_changed is True
    assert second.previous_regime == "TREND_UP"


def test_transition_caps_strength_and_confidence_while_pending():
    engine = MarketRegime()
    engine._confirm_regime_change(_result("RANGE"))

    result = _result("TREND_UP", Trend.UP)
    engine._confirm_regime_change(result)

    assert result.regime == "TRANSITION"
    assert result.strength <= 0.60
    assert result.confidence <= 0.65


def test_regime_result_clear_resets_confirmation_metadata():
    result = RegimeResult(
        previous_regime="TREND_UP",
        pending_regime="RANGE",
        confirmation_count=1,
        regime_changed=True,
    )
    result.clear()
    assert result.previous_regime == "UNKNOWN"
    assert result.pending_regime == "UNKNOWN"
    assert result.confirmation_count == 0
    assert result.regime_changed is False


def test_market_regime_instances_do_not_share_confirmation_memory():
    first_engine = MarketRegime()
    second_engine = MarketRegime()

    first_engine._confirm_regime_change(_result("TREND_UP", Trend.UP))
    result = _result("RANGE")
    second_engine._confirm_regime_change(result)

    assert result.regime == "RANGE"
    assert result.previous_regime == "RANGE"
    assert result.confirmation_count == 0
