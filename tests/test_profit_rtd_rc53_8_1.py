from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tools.profit_rtd_book_extended_session_adapter import analyze


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        samples = root / "samples.jsonl"
        summary = root / "summary.json"
        rows = [
            {"quality_status": "VALID", "imbalance": -0.1, "symbol": "WINV26"},
            {"quality_status": "VALID", "imbalance": 0.1, "symbol": "WINV26"},
        ]
        samples.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        summary.write_text(json.dumps({"requested_cycles": 2, "completed_cycles": 2, "collection_errors": 0}), encoding="utf-8")
        result = analyze(samples, summary)
        assert result["status"] == "EXTENDED_SESSION_INCOMPATIBLE"
        assert result["synchronized_price_samples"] == 0
        assert result["missing_price_count"] == 2
        assert "SYNCHRONIZED_LAST_PRICE_MISSING" in result["reasons"]
        assert result["rc53_6_compatible"] is False
        assert result["rc53_7_compatible"] is False
        assert result["score_influence_allowed"] is False
        assert result["decision_influence_allowed"] is False
        assert result["order_execution_allowed"] is False

    print("PROFIT_RTD_RC53_8_1=OK")


if __name__ == "__main__":
    main()
