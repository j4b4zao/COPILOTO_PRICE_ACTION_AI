from types import SimpleNamespace

from tools.profit_rtd_brooks_delta_rtd_telemetry import (
    snapshot_delta_rtd_telemetry,
)


def receipt(
    *,
    continuity="CONTIGUOUS",
    new_trade_count=3,
    state_updated=True,
    baseline_reset=False,
    source_units=3,
):
    return SimpleNamespace(
        symbol="WINV26",
        timestamp="2026-09-16T12:42:12.456",
        continuity=continuity,
        new_trade_count=new_trade_count,
        state_updated=state_updated,
        baseline_reset=baseline_reset,
        source_units=source_units,
    )


def test_snapshot_captures_contiguous_receipt():
    result = snapshot_delta_rtd_telemetry(
        receipt()
    )

    assert result == {
        "available": True,
        "symbol": "WINV26",
        "timestamp": "2026-09-16T12:42:12.456",
        "continuity": "CONTIGUOUS",
        "new_trade_count": 3,
        "state_updated": True,
        "baseline_reset": False,
        "source_units": 3,
        "research_only": True,
        "observational_only": True,
        "source_session_validity_changed": False,
        "selection_eligibility_changed": False,
        "oos_eligibility_changed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
    }


def test_snapshot_exposes_overlap_lost_rebase():
    result = snapshot_delta_rtd_telemetry(
        receipt(
            continuity="OVERLAP_LOST_REBASE",
            new_trade_count=0,
            state_updated=False,
            baseline_reset=True,
            source_units=0,
        )
    )

    assert result["available"] is True
    assert result["continuity"] == "OVERLAP_LOST_REBASE"
    assert result["baseline_reset"] is True
    assert result["new_trade_count"] == 0
    assert result["state_updated"] is False
    assert result["source_units"] == 0


def test_snapshot_exposes_symbol_reset():
    result = snapshot_delta_rtd_telemetry(
        receipt(
            continuity="SYMBOL_RESET",
            new_trade_count=0,
            state_updated=False,
            baseline_reset=True,
            source_units=0,
        )
    )

    assert result["continuity"] == "SYMBOL_RESET"
    assert result["baseline_reset"] is True


def test_snapshot_exposes_baseline_established():
    result = snapshot_delta_rtd_telemetry(
        receipt(
            continuity="BASELINE_ESTABLISHED",
            new_trade_count=0,
            state_updated=False,
            baseline_reset=True,
            source_units=0,
        )
    )

    assert result["continuity"] == "BASELINE_ESTABLISHED"
    assert result["baseline_reset"] is True


def test_missing_receipt_is_observationally_unavailable():
    result = snapshot_delta_rtd_telemetry(None)

    assert result["available"] is False
    assert result["continuity"] is None
    assert result["baseline_reset"] is None
    assert result["new_trade_count"] is None
    assert result["source_units"] is None
    assert result["research_only"] is True
    assert result["source_session_validity_changed"] is False
    assert result["selection_eligibility_changed"] is False
    assert result["oos_eligibility_changed"] is False
    assert result["order_execution_allowed"] is False
