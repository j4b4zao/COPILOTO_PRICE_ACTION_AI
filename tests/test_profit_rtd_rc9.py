from types import SimpleNamespace

import pytest

from market_data.profit_rtd_validation_recorder import ProfitRTDValidationRecorder


def _receipt(**overrides):
    data = dict(
        symbol="WINV26",
        continuity="CONTIGUOUS",
        new_trade_count=3,
        state_updated=True,
        baseline_reset=False,
        source_units=3,
        observational_only=True,
        score_influence_allowed=False,
        decision_influence_allowed=False,
        order_execution_allowed=False,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_rc9_records_validation_metrics_without_operational_capabilities():
    recorder = ProfitRTDValidationRecorder()

    recorder.record(
        _receipt(
            continuity="BASELINE_ESTABLISHED",
            new_trade_count=0,
            state_updated=False,
            baseline_reset=True,
            source_units=0,
        )
    )
    recorder.record(_receipt())
    recorder.record(
        _receipt(
            new_trade_count=0,
            state_updated=False,
            source_units=0,
        )
    )

    snapshot = recorder.snapshot
    assert snapshot.total_cycles == 3
    assert snapshot.state_updates == 1
    assert snapshot.baseline_resets == 1
    assert snapshot.total_new_trades == 3
    assert snapshot.total_source_units == 3
    assert snapshot.contiguous_cycles == 2
    assert snapshot.no_new_trade_cycles == 1
    assert snapshot.continuity_rate == pytest.approx(0.6667)
    assert snapshot.observational_only is True
    assert snapshot.score_influence_allowed is False
    assert snapshot.decision_influence_allowed is False
    assert snapshot.order_execution_allowed is False


def test_rc9_tracks_continuity_loss_and_symbol_reset():
    recorder = ProfitRTDValidationRecorder()
    recorder.record(
        _receipt(
            continuity="OVERLAP_LOST_REBASE",
            new_trade_count=0,
            state_updated=False,
            baseline_reset=True,
            source_units=0,
        )
    )
    recorder.record(
        _receipt(
            symbol="WDOU26",
            continuity="SYMBOL_RESET",
            new_trade_count=0,
            state_updated=False,
            baseline_reset=True,
            source_units=0,
        )
    )

    snapshot = recorder.snapshot
    assert snapshot.continuity_loss_cycles == 1
    assert snapshot.symbol_reset_cycles == 1
    assert snapshot.baseline_resets == 2
    assert snapshot.last_symbol == "WDOU26"
    assert snapshot.last_continuity == "SYMBOL_RESET"


def test_rc9_rejects_receipt_with_operational_capability():
    recorder = ProfitRTDValidationRecorder()

    with pytest.raises(ValueError):
        recorder.record(_receipt(score_influence_allowed=True))

    with pytest.raises(ValueError):
        recorder.record(_receipt(decision_influence_allowed=True))

    with pytest.raises(ValueError):
        recorder.record(_receipt(order_execution_allowed=True))


def test_rc9_clear_resets_all_validation_metrics():
    recorder = ProfitRTDValidationRecorder()
    recorder.record(_receipt())
    recorder.clear()

    snapshot = recorder.snapshot
    assert snapshot.total_cycles == 0
    assert snapshot.state_updates == 0
    assert snapshot.total_new_trades == 0
    assert snapshot.last_symbol == ""
    assert snapshot.last_continuity == ""
