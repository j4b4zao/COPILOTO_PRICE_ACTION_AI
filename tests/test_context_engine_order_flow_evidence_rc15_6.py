from types import SimpleNamespace

from brain.context_engine import ContextEngine
from models.market_narrative import MarketNarrative
from models.trade_checklist import TradeChecklist


def _order_flow(
    *,
    valid=True,
    momentum="ACCELERATING_BUY",
    persistence=0.8,
    acceleration=10.0,
    impulse=0.4,
):
    return SimpleNamespace(
        valid=valid,
        flow_momentum=momentum,
        delta_persistence=persistence,
        delta_acceleration=acceleration,
        delta_impulse_ratio=impulse,
    )


def _apply(bias, order_flow):
    result = SimpleNamespace(bias=bias)
    checklist = TradeChecklist()
    narrative = MarketNarrative()
    ContextEngine._append_order_flow_evidence(
        result, checklist, order_flow, narrative
    )
    return checklist, narrative


def test_accelerating_buy_aligns_with_buy_context():
    checklist, narrative = _apply("BUY", _order_flow())
    assert checklist.order_flow_status == "ALIGNED"
    assert checklist.order_flow_aligned is True
    assert any("Order Flow confirma" in text for text in narrative.strengths)


def test_persistent_sell_aligns_with_sell_context():
    checklist, _ = _apply(
        "SELL", _order_flow(momentum="PERSISTENT_SELL", acceleration=-3.0)
    )
    assert checklist.order_flow_status == "ALIGNED"
    assert checklist.order_flow_aligned is True


def test_buy_context_conflicts_with_sustained_sell_flow():
    checklist, narrative = _apply(
        "BUY", _order_flow(momentum="ACCELERATING_SELL", acceleration=-12.0)
    )
    assert checklist.order_flow_status == "CONFLICT"
    assert checklist.order_flow_conflict is True
    assert any("conflita" in text for text in narrative.weaknesses)


def test_sell_context_conflicts_with_sustained_buy_flow():
    checklist, _ = _apply("SELL", _order_flow(momentum="PERSISTENT_BUY"))
    assert checklist.order_flow_status == "CONFLICT"
    assert checklist.order_flow_conflict is True


def test_fading_flow_is_informational_weakness():
    checklist, narrative = _apply("BUY", _order_flow(momentum="FADING_BUY"))
    assert checklist.order_flow_status == "FADING"
    assert checklist.order_flow_aligned is False
    assert any("enfraquecimento" in text for text in narrative.weaknesses)


def test_mixed_flow_is_not_alignment_or_conflict():
    checklist, _ = _apply("BUY", _order_flow(momentum="MIXED"))
    assert checklist.order_flow_status == "MIXED"
    assert checklist.order_flow_aligned is False
    assert checklist.order_flow_conflict is False


def test_invalid_order_flow_is_unavailable():
    checklist, _ = _apply("BUY", _order_flow(valid=False))
    assert checklist.order_flow_ready is False
    assert checklist.order_flow_status == "UNAVAILABLE"


def test_order_flow_metrics_are_clamped_for_observation():
    checklist, _ = _apply(
        "BUY",
        _order_flow(persistence=4.0, acceleration=99.0, impulse=-2.0),
    )
    assert checklist.order_flow_delta_persistence == 1.0
    assert checklist.order_flow_delta_impulse_ratio == 0.0
    assert checklist.order_flow_delta_acceleration == 99.0


def test_order_flow_fields_do_not_change_checklist_score_or_completion():
    checklist = TradeChecklist()
    baseline_score = checklist.score
    baseline_completion = checklist.completion
    result = SimpleNamespace(bias="BUY")
    narrative = MarketNarrative()
    ContextEngine._append_order_flow_evidence(
        result, checklist, _order_flow(), narrative
    )
    assert checklist.score == baseline_score
    assert checklist.completion == baseline_completion


def test_clear_resets_all_order_flow_observational_fields():
    checklist, _ = _apply("BUY", _order_flow())
    checklist.clear()
    assert checklist.order_flow_ready is False
    assert checklist.order_flow_aligned is False
    assert checklist.order_flow_conflict is False
    assert checklist.order_flow_status == "UNAVAILABLE"
    assert checklist.order_flow_momentum == "INSUFFICIENT_DATA"
    assert checklist.order_flow_delta_persistence == 0.0
    assert checklist.order_flow_delta_acceleration == 0.0
    assert checklist.order_flow_delta_impulse_ratio == 0.0
