"""Offline gate do Profit RTD RC11: export explícito pelo Collector."""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from market_data.collector import Collector
from market_data.profit_rtd_validation_recorder import ProfitRTDValidationRecorder


def _receipt(**overrides):
    data = dict(
        symbol="WINV26",
        continuity="CONTIGUOUS",
        new_trade_count=4,
        state_updated=True,
        baseline_reset=False,
        source_units=4,
        observational_only=True,
        score_influence_allowed=False,
        decision_influence_allowed=False,
        order_execution_allowed=False,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _collector_with_validation():
    collector = Collector.__new__(Collector)
    collector.profit_rtd_validation_recorder = ProfitRTDValidationRecorder()
    collector.profit_rtd_validation_recorder.record(
        _receipt(
            continuity="BASELINE_ESTABLISHED",
            new_trade_count=0,
            state_updated=False,
            baseline_reset=True,
            source_units=0,
        )
    )
    collector.profit_rtd_validation_recorder.record(_receipt())
    return collector


def test_collector_exports_current_validation_snapshot_explicitly():
    collector = _collector_with_validation()
    before = collector.profit_rtd_validation_recorder.snapshot

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp).resolve() / "profit_rtd_session.json"
        receipt = collector.export_profit_rtd_validation_session(target)
        payload = json.loads(target.read_text(encoding="utf-8"))

        assert receipt.path == str(target)
        assert receipt.total_cycles == 2
        assert receipt.schema == "PROFIT_RTD_VALIDATION_SESSION_V1"
        assert len(receipt.sha256) == 64
        assert receipt.byte_size == target.stat().st_size
        assert payload["validation"]["total_cycles"] == 2
        assert payload["validation"]["total_new_trades"] == 4
        assert payload["capabilities"]["observational_only"] is True
        assert payload["capabilities"]["score_influence_allowed"] is False
        assert payload["capabilities"]["decision_influence_allowed"] is False
        assert payload["capabilities"]["order_execution_allowed"] is False

    after = collector.profit_rtd_validation_recorder.snapshot
    assert after == before


def test_collector_export_keeps_overwrite_blocked_by_default():
    collector = _collector_with_validation()

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp).resolve() / "profit_rtd_session.json"
        collector.export_profit_rtd_validation_session(target)

        blocked = False
        try:
            collector.export_profit_rtd_validation_session(target)
        except FileExistsError:
            blocked = True
        assert blocked is True

        receipt = collector.export_profit_rtd_validation_session(target, overwrite=True)
        assert receipt.total_cycles == 2


def test_collector_export_is_not_automatic_and_does_not_require_rtd_flag():
    collector = _collector_with_validation()
    collector.enable_profit_rtd_order_flow = False

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp).resolve() / "manual_session.json"
        assert target.exists() is False
        receipt = collector.export_profit_rtd_validation_session(target)
        assert target.exists() is True
        assert receipt.observational_only is True
        assert receipt.score_influence_allowed is False
        assert receipt.decision_influence_allowed is False
        assert receipt.order_execution_allowed is False


def main():
    test_collector_exports_current_validation_snapshot_explicitly()
    print("✅ test_collector_exports_current_validation_snapshot_explicitly")
    test_collector_export_keeps_overwrite_blocked_by_default()
    print("✅ test_collector_export_keeps_overwrite_blocked_by_default")
    test_collector_export_is_not_automatic_and_does_not_require_rtd_flag()
    print("✅ test_collector_export_is_not_automatic_and_does_not_require_rtd_flag")
    print("🏆 PROFIT RTD RC11 APROVADO")


if __name__ == "__main__":
    main()
