from pathlib import Path

from market_data.order_flow_observational_context import OrderFlowObservationalContextBuilder


def test_rc30_context_safety_flags_remain_blocked():
    class Delta:
        status = "VALID"
        recent_delta = 120.0
        recent_total_aggression = 500.0
        dominance = 0.25
        persistence = 0.40
        acceleration = 0.10

    class Book:
        status = "VALID"
        imbalance = 0.20
        spread = 15.0
        levels_bid = 50
        levels_ask = 50

    ctx = OrderFlowObservationalContextBuilder.build(delta_report=Delta(), book_report=Book(), symbol="WINV26")
    assert ctx.status == "READY"
    assert ctx.directional_alignment == "BULLISH_ALIGNED"
    assert ctx.observational_only is True
    assert ctx.score_influence_allowed is False
    assert ctx.decision_influence_allowed is False
    assert ctx.order_execution_allowed is False


def test_rc30_tool_declares_execute_gate_and_output():
    text = Path("tools/profit_rtd_order_flow_combined_session.py").read_text(encoding="utf-8")
    assert "EXECUTE_FLAG_REQUIRED" in text
    assert "ORDER_FLOW_SCORE_MUST_REMAIN_DISABLED" in text
    assert "PROFIT_RTD_ORDER_FLOW_COMBINED=" in text
    assert "score_influence_allowed=False" in text
    assert "decision_influence_allowed=False" in text
    assert "order_execution_allowed=False" in text
