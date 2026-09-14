"""Tests for offline Brooks management reprocessor."""

from __future__ import annotations

import json

from tools.profit_rtd_brooks_management_reprocessor import (
    reprocess_file,
    reprocess_payload,
)


def _evidence(candle_id, o, h, l, c):
    return {
        "status": "CANDLE_EVIDENCE_READY",
        "candle_id": candle_id,
        "open": float(o),
        "high": float(h),
        "low": float(l),
        "close": float(c),
        "volume": 1000.0,
    }


def test_reprocess_payload_does_not_mutate_source(monkeypatch):
    source = {
        "samples": [
            {
                "price_action": {},
                "candle_evidence": _evidence(
                    "WINV26|M1|2026-09-11T10:00:00",
                    100, 105, 95, 102,
                ),
            }
        ]
    }

    def fake_enrich(payload):
        payload["samples"][0]["price_action"]["marker"] = True
        payload[
            "brooks_management_postprocessed_after_candle_evidence"
        ] = True
        return payload

    monkeypatch.setattr(
        "tools.profit_rtd_brooks_management_reprocessor."
        "_enrich_management_after_candle_evidence",
        fake_enrich,
    )

    out = reprocess_payload(source)

    assert "marker" not in source["samples"][0]["price_action"]
    assert out["samples"][0]["price_action"]["marker"] is True
    assert out["brooks_management_reprocessed_offline"] is True
    assert out["brooks_management_risk_influence_allowed"] is False
    assert out["brooks_management_order_execution_allowed"] is False


def test_reprocess_file_preserves_source_and_writes_copy(
    monkeypatch,
    tmp_path,
):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()

    source_path = source_dir / "session.json"
    original = {
        "status": "COMPLETED",
        "samples": [
            {
                "price_action": {},
                "candle_evidence": _evidence(
                    "WINV26|M1|2026-09-11T10:00:00",
                    100, 105, 95, 102,
                ),
            }
        ],
    }
    source_path.write_text(
        json.dumps(original),
        encoding="utf-8",
    )

    def fake_enrich(payload):
        payload["samples"][0]["price_action"]["marker"] = "ENRICHED"
        payload[
            "brooks_management_postprocessed_after_candle_evidence"
        ] = True
        return payload

    monkeypatch.setattr(
        "tools.profit_rtd_brooks_management_reprocessor."
        "_enrich_management_after_candle_evidence",
        fake_enrich,
    )

    report = reprocess_file(source_path, output_dir)

    source_after = json.loads(
        source_path.read_text(encoding="utf-8")
    )
    output_path = output_dir / "session.json"
    output = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert source_after == original
    assert output["samples"][0]["price_action"]["marker"] == "ENRICHED"
    assert report["management_postprocessed"] is True
    assert report["brooks_management_research_only"] is True
    assert report["brooks_management_order_execution_allowed"] is False
