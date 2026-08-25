from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace

from analysis.replay.book_diagnostics_shadow_mode import ShadowObservation
from analysis.replay.book_diagnostics_shadow_outcome_tracker import (
    BookDiagnosticsShadowOutcomeTracker,
)


def _obs(action="BUY", price=100.0, official="WAIT"):
    return ShadowObservation(
        timestamp="2026-08-22T10:00:00+00:00",
        book_state="CLEAN_DIRECTIONAL_CONTEXT",
        shadow_action=action,
        official_action=official,
        agreement=(action == official),
        market_price=price,
        metadata={},
    )


def _candle(high, low, close):
    return SimpleNamespace(high=high, low=low, close=close)


def test_buy_shadow_tracks_target_first_and_positive_edge():
    tracker = BookDiagnosticsShadowOutcomeTracker()
    candles = [
        _candle(101.2, 99.7, 101.0),
        _candle(102.0, 100.5, 101.8),
    ]
    outcome = tracker.track(_obs("BUY"), candles, risk_unit=1.0)

    assert outcome.first_touch == "TARGET"
    assert outcome.target_1r_hit is True
    assert outcome.stop_1r_hit is False
    assert outcome.direction_correct is True
    assert outcome.mfe_r >= 1.0
    assert outcome.edge_r > 0.0


def test_sell_shadow_tracks_target_first():
    tracker = BookDiagnosticsShadowOutcomeTracker()
    candles = [
        _candle(100.3, 98.8, 99.0),
        _candle(99.2, 98.0, 98.2),
    ]
    outcome = tracker.track(_obs("SELL"), candles, risk_unit=1.0)

    assert outcome.first_touch == "TARGET"
    assert outcome.direction_correct is True
    assert outcome.future_direction == "SELL"


def test_same_bar_target_and_stop_is_ambiguous():
    tracker = BookDiagnosticsShadowOutcomeTracker()
    outcome = tracker.track(
        _obs("BUY"),
        [_candle(101.2, 98.8, 100.2)],
        risk_unit=1.0,
    )
    assert outcome.first_touch == "AMBIGUOUS_SAME_BAR"
    assert outcome.target_1r_hit is True
    assert outcome.stop_1r_hit is True


def test_wait_shadow_is_not_treated_as_trade():
    tracker = BookDiagnosticsShadowOutcomeTracker()
    try:
        tracker.track(_obs("WAIT"), [_candle(101.0, 99.0, 100.5)])
    except ValueError as exc:
        assert "directional" in str(exc)
    else:
        raise AssertionError("WAIT shadow observation should be rejected")


def test_missing_market_price_is_rejected():
    tracker = BookDiagnosticsShadowOutcomeTracker()
    try:
        tracker.track(_obs("BUY", price=None), [_candle(101.0, 99.0, 100.5)])
    except ValueError as exc:
        assert "market_price" in str(exc)
    else:
        raise AssertionError("missing market price should be rejected")


def test_metrics_aggregate_shadow_quality():
    tracker = BookDiagnosticsShadowOutcomeTracker()
    tracker.track(
        _obs("BUY"),
        [_candle(101.2, 99.8, 101.0)],
        risk_unit=1.0,
    )
    tracker.track(
        _obs("BUY"),
        [_candle(100.2, 98.8, 99.0)],
        risk_unit=1.0,
    )

    metrics = tracker.metrics("CLEAN_DIRECTIONAL_CONTEXT")
    assert metrics["completed"] == 2
    assert metrics["target_first"] == 1
    assert metrics["stop_first"] == 1
    assert metrics["target_first_rate"] == 0.5
    assert metrics["stop_first_rate"] == 0.5


def test_json_round_trip_preserves_outcomes():
    tracker = BookDiagnosticsShadowOutcomeTracker()
    tracker.track(
        _obs("BUY"),
        [_candle(101.2, 99.8, 101.0)],
        risk_unit=1.0,
    )

    with TemporaryDirectory() as tmp:
        path = tracker.save_json(Path(tmp) / "shadow_outcomes.json")
        loaded = BookDiagnosticsShadowOutcomeTracker.load_json(path)

    assert loaded.metrics()["outcomes"] == 1
    assert loaded.all()[0]["first_touch"] == "TARGET"


def test_tracker_does_not_modify_observation():
    tracker = BookDiagnosticsShadowOutcomeTracker()
    observation = _obs("BUY", official="SELL")
    before = observation.to_dict()
    tracker.track(observation, [_candle(101.1, 99.8, 100.9)], risk_unit=1.0)
    assert observation.to_dict() == before
