from tools.profit_rtd_brooks_trailing_stop_diagnostics import (
    diagnose_many,
)


def _sample(cid, state, structural=False):
    return {
        "candle_evidence": {"candle_id": cid},
        "price_action": {
            "brooks_management_capture_status": "CAPTURED",
            "brooks_management_state": state,
            "brooks_management_reason": state,
            "brooks_management_structural_advance_confirmed": structural,
            "brooks_management_trailing_active": (
                state == "TRAILING_STOP_ADVANCE"
            ),
            "brooks_management_stop_improved": (
                state == "TRAILING_STOP_ADVANCE"
            ),
            "brooks_management_latest_swing_price": 100.0,
        },
    }


def test_detects_intrabar_advance_disappearing_on_last_revision(
    monkeypatch,
):
    payload = {
        "samples": [
            _sample(
                "WIN|M1|10:00",
                "TRAILING_STOP_ADVANCE",
                True,
            ),
            _sample(
                "WIN|M1|10:00",
                "PROTECTIVE_STOP_HOLD",
                False,
            ),
        ]
    }

    monkeypatch.setattr(
        "tools.profit_rtd_brooks_trailing_stop_diagnostics._load",
        lambda path: payload,
    )

    report = diagnose_many(["x.json"])

    assert report["raw_totals"]["advances"] == 1
    assert report["exact_totals"]["advances"] == 0
    assert report["diagnosis"] == (
        "INTRABAR_ADVANCES_DISAPPEAR_ON_LAST_REVISION"
    )


def test_detects_no_advance_anywhere(monkeypatch):
    payload = {
        "samples": [
            _sample("WIN|M1|10:00", "PROTECTIVE_STOP_HOLD"),
            _sample("WIN|M1|10:01", "TRAILING_STOP_HOLD"),
        ]
    }

    monkeypatch.setattr(
        "tools.profit_rtd_brooks_trailing_stop_diagnostics._load",
        lambda path: payload,
    )

    report = diagnose_many(["x.json"])

    assert report["raw_totals"]["advances"] == 0
    assert report["exact_totals"]["advances"] == 0
    assert report["diagnosis"] == "NO_ADVANCE_IN_RAW_OR_EXACT_CAPTURE"
