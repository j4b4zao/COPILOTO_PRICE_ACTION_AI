"""Tests for observational Brooks trailing-stop capture."""

from dataclasses import dataclass
from types import SimpleNamespace

from tools.profit_rtd_brooks_trailing_stop_capture import (
    enrich_price_action_snapshot,
)


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return Candle(o, h, l, cl)


def buy_sequence():
    closed = [
        c(100, 104, 99, 103),
        c(103, 106, 101, 105),
        c(105, 110, 104, 108),
        c(108, 107, 102, 104),
        c(104, 106, 100, 105),
        c(105, 108, 102, 107),
        c(107, 111, 105, 110),
        c(110, 115, 108, 113),
        c(113, 112, 106, 109),
        c(109, 111, 105, 108),
    ]
    return closed + [c(108, 120, 107, 119)]


def _context(candles):
    return SimpleNamespace(
        market=SimpleNamespace(candles=candles)
    )


def _base_item(**overrides):
    pa = {
        "brooks_signal_direction": "UP",
        "brooks_entry_triggered": True,
        "brooks_stop_target_direction": "BUY",
        "brooks_stop_target_entry_triggered": True,
        "brooks_stop_target_entry_price": 105.0,
        "brooks_stop_target_initial_stop": 95.0,
        "brooks_stop_target_stop_geometry_valid": True,
    }
    pa.update(overrides)
    return {
        "price_action": pa,
        "candle_evidence": {
            "status": "CANDLE_EVIDENCE_READY",
            "candle_id": "WINV26|M1|2026-09-12T10:00:00",
        },
    }


def test_capture_records_proposed_trailing_stop_without_mutating_initial_stop():
    item = _base_item()

    out = enrich_price_action_snapshot(item, _context(buy_sequence()))
    pa = out["price_action"]

    assert pa["brooks_management_capture_status"] == "CAPTURED"
    assert pa["brooks_management_state"] == "TRAILING_STOP_ADVANCE"
    assert pa["brooks_management_current_stop"] == 95.0
    assert pa["brooks_management_proposed_stop"] == 99.0
    assert pa["brooks_management_initial_stop"] == 95.0
    assert pa["brooks_management_stop_improved"] is True
    assert pa["brooks_management_structural_advance_confirmed"] is True


def test_capture_is_explicitly_research_only_and_non_operational():
    out = enrich_price_action_snapshot(
        _base_item(),
        _context(buy_sequence()),
    )
    pa = out["price_action"]

    assert pa["brooks_management_research_only"] is True
    assert pa["brooks_management_observational_only"] is True
    assert pa["brooks_management_predictive_claim_allowed"] is False
    assert pa["brooks_management_score_influence_allowed"] is False
    assert pa["brooks_management_risk_influence_allowed"] is False
    assert pa["brooks_management_decision_influence_allowed"] is False
    assert pa["brooks_management_alert_influence_allowed"] is False
    assert pa["brooks_management_order_execution_allowed"] is False


def test_invalid_initial_stop_is_not_eligible():
    item = _base_item(
        brooks_stop_target_stop_geometry_valid=False,
        brooks_stop_target_initial_stop=105.0,
    )

    out = enrich_price_action_snapshot(item, _context(buy_sequence()))
    pa = out["price_action"]

    assert pa["brooks_management_capture_status"] == "NOT_ELIGIBLE"
    assert "INITIAL_STOP_GEOMETRY_NOT_VALIDATED" in pa[
        "brooks_management_reasons"
    ]


def test_not_triggered_entry_is_not_eligible():
    item = _base_item(
        brooks_entry_triggered=False,
        brooks_stop_target_entry_triggered=False,
    )

    out = enrich_price_action_snapshot(item, _context(buy_sequence()))
    pa = out["price_action"]

    assert pa["brooks_management_capture_status"] == "NOT_ELIGIBLE"
    assert "ENTRY_NOT_TRIGGERED" in pa["brooks_management_reasons"]


def test_insufficient_history_is_not_eligible():
    short_history = [c(100, 101, 99, 100)] * 5

    out = enrich_price_action_snapshot(
        _base_item(),
        _context(short_history),
    )
    pa = out["price_action"]

    assert pa["brooks_management_capture_status"] == "NOT_ELIGIBLE"
    assert "INSUFFICIENT_HISTORY" in pa["brooks_management_reasons"]


def test_capture_does_not_create_partial_or_outcome_fields():
    out = enrich_price_action_snapshot(
        _base_item(),
        _context(buy_sequence()),
    )
    pa = out["price_action"]

    assert "brooks_management_partial_exit" not in pa
    assert "brooks_management_outcome" not in pa
