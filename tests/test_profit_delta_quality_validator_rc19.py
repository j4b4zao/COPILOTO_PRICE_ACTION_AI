from types import SimpleNamespace

from core.order_flow_state import OrderFlowState
from market_data.profit_delta_quality_validator import ProfitDeltaQualityValidator


def _source(status="READY"):
    return SimpleNamespace(status=status)


def _state(values, totals=None):
    state = OrderFlowState()
    state.history.extend(values)
    state.aggression_history.extend(totals if totals is not None else [abs(v) + 10 for v in values])
    state.ready = bool(values)
    return state


def test_no_data():
    report = ProfitDeltaQualityValidator().evaluate(OrderFlowState(), _source())
    assert report.status == "NO_DATA"


def test_initializing_with_few_samples():
    report = ProfitDeltaQualityValidator().evaluate(_state([10, 20, -5]), _source())
    assert report.status == "INITIALIZING"


def test_valid_after_minimum_samples():
    report = ProfitDeltaQualityValidator().evaluate(_state([10, 12, 8, 15, 11, 9]), _source())
    assert report.status == "VALID"


def test_degraded_when_source_degraded():
    report = ProfitDeltaQualityValidator().evaluate(_state([10] * 6), _source("DEGRADED"))
    assert report.status == "DEGRADED"
    assert "SOURCE_DEGRADED" in report.reasons


def test_degraded_when_aggression_unavailable():
    report = ProfitDeltaQualityValidator().evaluate(_state([10] * 6), _source("AGGRESSION_UNAVAILABLE"))
    assert report.status == "DEGRADED"


def test_excessive_zero_delta_is_anomaly():
    report = ProfitDeltaQualityValidator().evaluate(_state([0, 0, 0, 0, 0, 10]), _source())
    assert report.status == "DEGRADED"
    assert "EXCESSIVE_ZERO_DELTA" in report.reasons


def test_single_sample_dominance_is_anomaly():
    report = ProfitDeltaQualityValidator().evaluate(_state([1, 1, 1, 1, 1, 200]), _source())
    assert report.status == "DEGRADED"
    assert "SINGLE_SAMPLE_DOMINANCE" in report.reasons


def test_low_activity_status():
    report = ProfitDeltaQualityValidator().evaluate(_state([0.1] * 6, totals=[0.1] * 6), _source())
    assert report.status == "LOW_ACTIVITY"


def test_metrics_are_exposed():
    state = _state([10, 20, 30, -10, 15, 25])
    report = ProfitDeltaQualityValidator().evaluate(state, _source())
    assert report.sample_count == 6
    assert report.max_abs_delta == 30
    assert 0.0 <= report.dominance <= 1.0
    assert 0.0 <= report.persistence <= 1.0


def test_report_is_passive_only():
    report = ProfitDeltaQualityValidator().evaluate(_state([10] * 6), _source())
    assert report.passive_only is True
