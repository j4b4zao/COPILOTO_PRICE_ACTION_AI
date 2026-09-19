from __future__ import annotations

import json

from tools.profit_rtd_order_flow_historical_shadow_reprocessor import (
    DIRECTION_LOGIC_VERSION,
    _eligible_sample,
    _reprocess_session,
    _safe_payload,
)


def _safe_source():
    return {
        "observational_only": True,
        "score_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
    }


def _sample(
    *,
    recent_delta,
    dominance,
    imbalance,
    alignment="NEUTRAL",
    cycle=1,
):
    return {
        "cycle": cycle,
        "timestamp": f"2026-09-19T10:00:{cycle:02d}",
        "data_ready": True,
        "context_ready": True,
        "delta_status": "VALID",
        "book_status": "VALID",
        "recent_delta": recent_delta,
        "dominance": dominance,
        "imbalance": imbalance,
        "alignment": alignment,
    }


def test_historical_reprocessor_source_safety_is_fail_closed():
    assert _safe_payload(_safe_source()) is True

    unsafe = _safe_source()
    unsafe["score_influence_allowed"] = True

    assert _safe_payload(unsafe) is False


def test_historical_reprocessor_requires_ready_valid_sample():
    sample = _sample(
        recent_delta=500,
        dominance=0.60,
        imbalance=0.20,
    )

    assert _eligible_sample(sample) is True

    sample["delta_status"] = "NO_DATA"

    assert _eligible_sample(sample) is False


def test_historical_reprocessor_uses_recent_delta_for_direction(tmp_path):
    source_path = tmp_path / "source.json"

    samples = [
        _sample(
            recent_delta=-500,
            dominance=0.80,
            imbalance=-0.20,
            alignment="NEUTRAL",
            cycle=1,
        ),
        _sample(
            recent_delta=500,
            dominance=0.80,
            imbalance=0.20,
            alignment="NEUTRAL",
            cycle=2,
        ),
        _sample(
            recent_delta=500,
            dominance=0.80,
            imbalance=-0.20,
            alignment="NEUTRAL",
            cycle=3,
        ),
    ]

    report = _reprocess_session(
        source_path,
        {"symbol": "WINV26"},
        samples,
        delta_threshold=0.35,
        book_threshold=0.10,
    )

    assert report["completed_cycles"] == 3

    assert report["samples"][0]["shadow_alignment"] == "BEARISH_ALIGNED"
    assert report["samples"][1]["shadow_alignment"] == "BULLISH_ALIGNED"
    assert report["samples"][2]["shadow_alignment"] == "DIVERGENT"

    assert report["samples"][0]["dominance"] == 0.80
    assert report["samples"][0]["recent_delta"] == -500.0

    assert report["direction_logic_version"] == DIRECTION_LOGIC_VERSION


def test_historical_reprocessor_is_strictly_observational(tmp_path):
    report = _reprocess_session(
        tmp_path / "source.json",
        {"symbol": "WINV26"},
        [
            _sample(
                recent_delta=500,
                dominance=0.80,
                imbalance=0.20,
            )
        ],
        delta_threshold=0.35,
        book_threshold=0.10,
    )

    assert report["observational_only"] is True
    assert report["score_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["order_execution_allowed"] is False

    for sample in report["samples"]:
        assert sample["observational_only"] is True
        assert sample["score_influence_allowed"] is False
        assert sample["decision_influence_allowed"] is False
        assert sample["order_execution_allowed"] is False


def test_serialized_report_preserves_safety_contract(tmp_path):
    report = _reprocess_session(
        tmp_path / "source.json",
        {"symbol": "WINV26"},
        [
            _sample(
                recent_delta=-250,
                dominance=0.70,
                imbalance=-0.15,
            )
        ],
        delta_threshold=0.35,
        book_threshold=0.10,
    )

    encoded = json.dumps(report)
    decoded = json.loads(encoded)

    assert decoded["historical_reprocessing"] is True
    assert decoded["oos_included"] is False
    assert decoded["brooks_included"] is False
    assert decoded["score_influence_allowed"] is False
    assert decoded["decision_influence_allowed"] is False
    assert decoded["order_execution_allowed"] is False
