from types import SimpleNamespace

from brain.context_engine import ContextEngine
from enums.trend import Trend
from models.market_narrative import MarketNarrative
from models.trade_checklist import TradeChecklist


def _result(bias="BUY"):
    return SimpleNamespace(bias=bias)


def _regime(regime="TREND_UP", trend=Trend.UP, volatility="NORMAL", pending="UNKNOWN"):
    return SimpleNamespace(
        valid=True,
        regime=regime,
        trend=trend,
        volatility=volatility,
        pending_regime=pending,
    )


def _mtf(alignment, bias="BUY", aligned=False, conflict=False, valid=True):
    return SimpleNamespace(
        valid=valid,
        alignment=alignment,
        bias=bias,
        aligned=aligned,
        conflict=conflict,
    )


def test_version_is_rc15_4():
    assert ContextEngine.VERSION == "RC15.4-REGIME-MTF-EVIDENCE"


def test_transition_regime_is_reported_with_pending_candidate():
    narrative = MarketNarrative()
    ContextEngine._append_regime_evidence(
        _result(),
        _regime("TRANSITION", Trend.SIDEWAYS, pending="TREND_UP"),
        narrative,
    )
    assert any("transição" in item for item in narrative.weaknesses)
    assert any("TREND_UP" in item for item in narrative.weaknesses)


def test_range_regime_is_explicit_weakness():
    narrative = MarketNarrative()
    ContextEngine._append_regime_evidence(
        _result(), _regime("RANGE", Trend.SIDEWAYS), narrative
    )
    assert "Regime de mercado em range." in narrative.weaknesses


def test_regime_direction_confirmation_is_strength():
    narrative = MarketNarrative()
    ContextEngine._append_regime_evidence(
        _result("BUY"), _regime("TREND_UP", Trend.UP), narrative
    )
    assert "Regime de mercado confirma direção." in narrative.strengths


def test_conflict_regime_marks_mtf_conflict():
    narrative = MarketNarrative()
    checklist = TradeChecklist()
    ContextEngine._append_multi_timeframe_evidence(
        _result(), checklist, _mtf("CONFLICT_REGIME", conflict=True), narrative
    )
    assert checklist.multi_timeframe_conflict is True
    assert any("regime de mercado" in item for item in narrative.weaknesses)


def test_wait_regime_is_not_marked_as_conflict():
    narrative = MarketNarrative()
    checklist = TradeChecklist()
    ContextEngine._append_multi_timeframe_evidence(
        _result(), checklist, _mtf("WAIT_REGIME", bias="BUY"), narrative
    )
    assert checklist.multi_timeframe_conflict is False
    assert any("aguarda confirmação do regime" in item for item in narrative.weaknesses)


def test_conflict_m5_is_explicit():
    narrative = MarketNarrative()
    checklist = TradeChecklist()
    ContextEngine._append_multi_timeframe_evidence(
        _result(), checklist, _mtf("CONFLICT_M5", conflict=True), narrative
    )
    assert checklist.multi_timeframe_conflict is True
    assert any("M5 contradiz" in item for item in narrative.weaknesses)


def test_wait_trigger_is_explicit_without_conflict():
    narrative = MarketNarrative()
    checklist = TradeChecklist()
    ContextEngine._append_multi_timeframe_evidence(
        _result(), checklist, _mtf("WAIT_TRIGGER", bias="BUY"), narrative
    )
    assert checklist.multi_timeframe_conflict is False
    assert any("M1 ainda aguarda gatilho" in item for item in narrative.weaknesses)


def test_aligned_mtf_confirming_operational_bias_is_strength():
    narrative = MarketNarrative()
    checklist = TradeChecklist()
    ContextEngine._append_multi_timeframe_evidence(
        _result("SELL"),
        checklist,
        _mtf("SELL", bias="SELL", aligned=True),
        narrative,
    )
    assert checklist.multi_timeframe_aligned is True
    assert "Multi-timeframe confirma direção operacional." in narrative.strengths


def test_insufficient_mtf_data_stays_informative_only():
    narrative = MarketNarrative()
    checklist = TradeChecklist()
    ContextEngine._append_multi_timeframe_evidence(
        _result(),
        checklist,
        _mtf("INSUFFICIENT_DATA", valid=False),
        narrative,
    )
    assert checklist.multi_timeframe_ready is False
    assert checklist.ready is False
    assert any("dados insuficientes" in item for item in narrative.weaknesses)
