from types import SimpleNamespace

from analysis.replay.book_diagnostics_walk_forward import BookDiagnosticsWalkForward


def _record(ts, edge_sign=1.0, state="CLEAN_DIRECTIONAL_CONTEXT"):
    sample = SimpleNamespace(
        timestamp=ts,
        book_state=state,
        book_direction="BUY",
        market_environment_state="NORMAL_OR_OTHER",
        reversal_pressure_state="NONE",
        trend_control_state="CONTROL",
        direction_agreement="AGREE",
    )
    outcome = SimpleNamespace(
        book_direction="BUY",
        book_first_touch="TARGET" if edge_sign > 0 else "STOP",
        future_direction="BUY" if edge_sign > 0 else "SELL",
        official_trade_comparable=False,
        official_first_touch="NONE",
        mfe_r=1.2 if edge_sign > 0 else 0.2,
        mae_r=0.2 if edge_sign > 0 else 1.2,
    )
    return sample, outcome


def test_walk_forward_creates_chronological_folds():
    records = [_record(f"2026-08-{day:02d}T10:00:00") for day in range(1, 9)]
    wf = BookDiagnosticsWalkForward(train_size=4, validation_size=2, step_size=2)
    result = wf.evaluate(records)
    assert result["total_folds"] == 2
    assert result["folds"][0]["train_start"].startswith("2026-08-01")
    assert result["folds"][0]["validation_start"].startswith("2026-08-05")


def test_positive_validation_passes():
    records = [_record(f"2026-08-{day:02d}T10:00:00") for day in range(1, 9)]
    result = BookDiagnosticsWalkForward(train_size=4, validation_size=2, step_size=2).evaluate(records)
    assert result["passed_folds"] == result["total_folds"]
    assert result["walk_forward_stable"] is True


def test_negative_validation_fails():
    records = []
    for day in range(1, 5):
        records.append(_record(f"2026-08-{day:02d}T10:00:00", 1.0))
    for day in range(5, 7):
        records.append(_record(f"2026-08-{day:02d}T10:00:00", -1.0))
    wf = BookDiagnosticsWalkForward(train_size=4, validation_size=2)
    result = wf.evaluate(records)
    assert result["total_folds"] == 1
    assert result["failed_folds"] == 1
    assert result["walk_forward_stable"] is False


def test_state_filter_isolated():
    records = [
        _record("2026-08-01T10:00:00", state="A"),
        _record("2026-08-02T10:00:00", state="B"),
        _record("2026-08-03T10:00:00", state="A"),
        _record("2026-08-04T10:00:00", state="A"),
    ]
    wf = BookDiagnosticsWalkForward(train_size=2, validation_size=1)
    result = wf.evaluate_state(records, "A")
    assert result["book_state"] == "A"
    assert result["filtered_samples"] == 3
    assert result["total_folds"] == 1


def test_insufficient_data_returns_no_folds():
    result = BookDiagnosticsWalkForward(train_size=5, validation_size=2).evaluate([
        _record("2026-08-01T10:00:00")
    ])
    assert result["total_folds"] == 0
    assert result["walk_forward_stable"] is False
