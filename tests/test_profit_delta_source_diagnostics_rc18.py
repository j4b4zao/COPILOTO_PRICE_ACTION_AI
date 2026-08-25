from core.order_flow_state import OrderFlowState
from market_data.profit_delta_source_diagnostics import ProfitDeltaSourceDiagnostics
from market_data.profit_source_integrity import SourceIntegrityDecision


def _decision(*, symbol="WINV26", duplicate=False, symbol_changed=False):
    return SourceIntegrityDecision(
        symbol=symbol,
        duplicate=duplicate,
        symbol_changed=symbol_changed,
        fingerprint=(),
    )


def test_no_data_status():
    diagnostics = ProfitDeltaSourceDiagnostics()
    assert diagnostics.snapshot.status == "NO_DATA"


def test_aggression_unavailable_status():
    diagnostics = ProfitDeltaSourceDiagnostics()
    diagnostics.observe(
        integrity=_decision(),
        aggression_buy=None,
        aggression_sell=None,
        order_flow=OrderFlowState(),
    )
    assert diagnostics.snapshot.status == "AGGRESSION_UNAVAILABLE"


def test_initializing_before_enough_fresh_samples():
    diagnostics = ProfitDeltaSourceDiagnostics()
    flow = OrderFlowState()
    flow.update(100, 80, 100000)
    diagnostics.observe(
        integrity=_decision(), aggression_buy=100, aggression_sell=80, order_flow=flow
    )
    assert diagnostics.snapshot.status == "INITIALIZING"


def test_ready_after_fresh_samples_and_real_delta():
    diagnostics = ProfitDeltaSourceDiagnostics()
    flow = OrderFlowState()
    values = [(100, 80), (120, 90), (140, 100)]
    for buy, sell in values:
        flow.update(buy, sell, 100000)
        diagnostics.observe(
            integrity=_decision(), aggression_buy=buy, aggression_sell=sell, order_flow=flow
        )
    assert diagnostics.snapshot.status == "READY"
    assert diagnostics.snapshot.order_flow_samples == 2


def test_duplicate_snapshots_are_counted():
    diagnostics = ProfitDeltaSourceDiagnostics()
    flow = OrderFlowState()
    diagnostics.observe(
        integrity=_decision(duplicate=True),
        aggression_buy=100,
        aggression_sell=80,
        order_flow=flow,
    )
    assert diagnostics.snapshot.duplicate_snapshots == 1
    assert diagnostics.snapshot.fresh_snapshots == 0


def test_high_duplicate_rate_is_degraded():
    diagnostics = ProfitDeltaSourceDiagnostics()
    flow = OrderFlowState()
    for index in range(5):
        diagnostics.observe(
            integrity=_decision(duplicate=index > 0),
            aggression_buy=100,
            aggression_sell=80,
            order_flow=flow,
        )
    assert diagnostics.snapshot.status == "DEGRADED"


def test_symbol_change_is_counted_and_rebaselines_accumulators():
    diagnostics = ProfitDeltaSourceDiagnostics()
    flow = OrderFlowState()
    diagnostics.observe(
        integrity=_decision(symbol="WINV26"),
        aggression_buy=100,
        aggression_sell=80,
        order_flow=flow,
    )
    diagnostics.observe(
        integrity=_decision(symbol="WINZ26", symbol_changed=True),
        aggression_buy=10,
        aggression_sell=8,
        order_flow=flow,
    )
    snapshot = diagnostics.snapshot
    assert snapshot.symbol_changes == 1
    assert snapshot.accumulator_resets == 0
    assert snapshot.last_buy == 10.0


def test_accumulator_reset_is_detected_same_symbol():
    diagnostics = ProfitDeltaSourceDiagnostics()
    flow = OrderFlowState()
    diagnostics.observe(
        integrity=_decision(), aggression_buy=100, aggression_sell=80, order_flow=flow
    )
    diagnostics.observe(
        integrity=_decision(), aggression_buy=20, aggression_sell=10, order_flow=flow
    )
    assert diagnostics.snapshot.accumulator_resets == 1


def test_availability_rate_is_calculated():
    diagnostics = ProfitDeltaSourceDiagnostics()
    flow = OrderFlowState()
    diagnostics.observe(
        integrity=_decision(), aggression_buy=100, aggression_sell=80, order_flow=flow
    )
    diagnostics.observe(
        integrity=_decision(), aggression_buy=None, aggression_sell=None, order_flow=flow
    )
    assert diagnostics.snapshot.aggression_availability_rate == 0.5


def test_render_contains_operational_readiness_fields():
    diagnostics = ProfitDeltaSourceDiagnostics()
    flow = OrderFlowState()
    diagnostics.observe(
        integrity=_decision(), aggression_buy=100, aggression_sell=80, order_flow=flow
    )
    text = diagnostics.render()
    assert "[DELTA SOURCE]" in text
    assert "status=" in text
    assert "fresh=" in text
    assert "aggression=" in text
    assert "resets=" in text
