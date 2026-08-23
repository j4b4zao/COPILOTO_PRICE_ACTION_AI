from types import SimpleNamespace

import pytest

from ai.score_engine_rc13_2 import ScoreEngine


def _mtf(*, valid=True, alignment="BUY", bias="BUY", compatible=True):
    return SimpleNamespace(
        valid=valid,
        alignment=alignment,
        bias=bias,
        regime_compatible=compatible,
    )


def test_confirmation_buy_gets_full_positive_adjustment():
    value = ScoreEngine._contextual_adjustment(
        score_bias="BUY",
        multi_timeframe=_mtf(),
        weight=3.0,
    )
    assert value == 3.0


def test_confirmation_sell_gets_full_positive_adjustment():
    value = ScoreEngine._contextual_adjustment(
        score_bias="SELL",
        multi_timeframe=_mtf(alignment="SELL", bias="SELL"),
        weight=3.0,
    )
    assert value == 3.0


def test_regime_conflict_gets_full_negative_adjustment():
    value = ScoreEngine._contextual_adjustment(
        score_bias="BUY",
        multi_timeframe=_mtf(alignment="CONFLICT_REGIME", compatible=False),
        weight=3.0,
    )
    assert value == -3.0


def test_m5_conflict_gets_intermediate_penalty():
    value = ScoreEngine._contextual_adjustment(
        score_bias="BUY",
        multi_timeframe=_mtf(alignment="CONFLICT_M5", compatible=True),
        weight=4.0,
    )
    assert value == -3.0


def test_m1_conflict_gets_intermediate_penalty():
    value = ScoreEngine._contextual_adjustment(
        score_bias="SELL",
        multi_timeframe=_mtf(alignment="CONFLICT_M1", bias="SELL"),
        weight=4.0,
    )
    assert value == -3.0


def test_wait_regime_gets_half_penalty():
    value = ScoreEngine._contextual_adjustment(
        score_bias="BUY",
        multi_timeframe=_mtf(alignment="WAIT_REGIME", compatible=False),
        weight=4.0,
    )
    assert value == -2.0


def test_wait_trigger_is_neutral():
    value = ScoreEngine._contextual_adjustment(
        score_bias="BUY",
        multi_timeframe=_mtf(alignment="WAIT_TRIGGER", compatible=True),
        weight=3.0,
    )
    assert value == 0.0


def test_invalid_mtf_is_neutral():
    value = ScoreEngine._contextual_adjustment(
        score_bias="BUY",
        multi_timeframe=_mtf(valid=False),
        weight=3.0,
    )
    assert value == 0.0


def test_none_bias_is_neutral():
    value = ScoreEngine._contextual_adjustment(
        score_bias="NONE",
        multi_timeframe=_mtf(),
        weight=3.0,
    )
    assert value == 0.0


def test_constructor_rejects_weight_above_five():
    with pytest.raises(ValueError, match="entre 0 e 5"):
        ScoreEngine(
            enable_order_flow=False,
            order_flow_weight=0.0,
            enable_regime_mtf=True,
            regime_mtf_weight=5.1,
        )
