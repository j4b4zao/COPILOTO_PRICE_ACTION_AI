from analysis.order_flow import OrderFlow
from core.analysis_context import AnalysisContext
from core.order_flow_state import OrderFlowState


def _state_from_deltas(deltas):
    state = OrderFlowState()
    buy = 1000.0
    sell = 1000.0
    state.update(buy, sell, price=100.0)
    price = 100.0
    for delta in deltas:
        if delta >= 0:
            buy += float(delta)
        else:
            sell += abs(float(delta))
        price += 1.0 if delta > 0 else -1.0 if delta < 0 else 0.0
        state.update(buy, sell, price=price)
    return state


def _run(deltas):
    context = AnalysisContext()
    context.order_flow_state = _state_from_deltas(deltas)
    before = context.decision.direction
    OrderFlow().executar(context)
    return context, before


def test_delta_persistence_for_consistent_buying():
    state = _state_from_deltas([10, 20, 30, 40, 50, 60])
    assert state.delta_persistence == 1.0


def test_delta_persistence_for_mixed_flow_is_lower():
    state = _state_from_deltas([10, -10, 10, -10, 10, -10])
    assert state.delta_persistence < 0.70


def test_delta_acceleration_positive_when_buying_strengthens():
    state = _state_from_deltas([10, 15, 20, 30, 40, 50])
    assert state.delta_acceleration > 0
    assert state.delta_impulse_ratio > 0


def test_delta_acceleration_negative_when_buying_fades():
    state = _state_from_deltas([30, 30, 30, 10, 10, 10])
    assert state.delta_acceleration < 0


def test_engine_classifies_accelerating_buy():
    context, _ = _run([10, 15, 20, 30, 40, 50])
    assert context.order_flow.flow_momentum == "ACCELERATING_BUY"


def test_engine_classifies_accelerating_sell():
    context, _ = _run([-10, -15, -20, -30, -40, -50])
    assert context.order_flow.flow_momentum == "ACCELERATING_SELL"


def test_engine_classifies_fading_buy():
    context, _ = _run([30, 30, 30, 10, 10, 10])
    assert context.order_flow.flow_momentum == "FADING_BUY"


def test_engine_classifies_mixed_flow():
    context, _ = _run([10, -10, 10, -10, 10, -10])
    assert context.order_flow.flow_momentum == "MIXED"


def test_insufficient_history_keeps_dynamics_pending():
    context, _ = _run([10, 20, 30])
    assert context.order_flow.flow_momentum == "INSUFFICIENT_DATA"
    assert "ORDER_FLOW_DYNAMICS_HISTORY_PENDING" in context.order_flow.reasons


def test_order_flow_dynamics_remains_observational():
    context, before = _run([10, 15, 20, 30, 40, 50])
    assert context.decision.direction == before
