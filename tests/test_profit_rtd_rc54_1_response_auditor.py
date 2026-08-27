import json
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.profit_rtd_rc54_1_response_auditor import audit


def main():
    with TemporaryDirectory() as td:
        p = Path(td) / "s.json"
        payload = {
            "status": "COMPLETED",
            "symbol": "WINV26",
            "price_capture": True,
            "collection_errors": 0,
            "missing_price_count": 0,
            "samples": [
                {"alignment": "BEARISH_ALIGNED", "last_price": 100.0},
                {"alignment": "BEARISH_ALIGNED", "last_price": 95.0},
                {"alignment": "DIVERGENT", "last_price": 97.0},
                {"alignment": "NEUTRAL", "last_price": 96.0},
                {"alignment": "NEUTRAL", "last_price": 94.0},
                {"alignment": "NEUTRAL", "last_price": 93.0},
                {"alignment": "NEUTRAL", "last_price": 92.0},
                {"alignment": "NEUTRAL", "last_price": 91.0},
                {"alignment": "NEUTRAL", "last_price": 90.0},
                {"alignment": "NEUTRAL", "last_price": 89.0},
                {"alignment": "NEUTRAL", "last_price": 88.0},
            ],
        }
        p.write_text(json.dumps(payload), encoding="utf-8")
        r = audit(p)
        assert r["status"] == "RC54_1_RESPONSE_AUDIT_COMPLETED"
        assert r["groups"]["BEARISH_ALIGNED"]["occurrences"] == 2
        assert r["groups"]["BULLISH_ALIGNED"]["occurrences"] == 0
        assert r["groups"]["BEARISH_ALIGNED"]["horizons"]["1"]["mean_delta"] == -1.5
        assert r["observational_only"] is True
        assert r["score_influence_allowed"] is False
    print("PROFIT_RTD_RC54_1_RESPONSE_AUDITOR=OK")


if __name__ == "__main__":
    main()
