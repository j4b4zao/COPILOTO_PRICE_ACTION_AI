from dataclasses import dataclass

from analysis.replay.book_diagnostics_outcome_labeler import (
    BookDiagnosticsOutcomeLabeler,
)
from analysis.replay.book_diagnostics_replay_recorder import (
    BookDiagnosticsReplaySample,
)


@dataclass
class C:
    high: float
    low: float
    close: float


def test_buy_book_direction_calculates_mfe_mae_and_1r_target():
    sample = BookDiagnosticsReplaySample(
        symbol="WIN",
        last_price=100.0,
        book_direction="BUY",
    )
    candles = [C(101, 99.5, 100.5), C(102.2, 100.2, 102.0)]

    outcome = BookDiagnosticsOutcomeLabeler().label(
        sample,
        candles,
        horizon_bars=2,
        risk_unit=2.0,
    )

    assert outcome.mfe_points == 2.2
    assert outcome.mae_points == 0.5
    assert outcome.mfe_r == 1.1
    assert outcome.book_target_1r_hit is True
    assert outcome.book_stop_1r_hit is False
    assert outcome.book_first_touch == "TARGET"


def test_sell_book_direction_calculates_directional_excursions():
    sample = BookDiagnosticsReplaySample(last_price=100.0, book_direction="SELL")
    candles = [C(100.5, 98.5, 99.0), C(99.2, 97.0, 97.5)]

    outcome = BookDiagnosticsOutcomeLabeler().label(
        sample,
        candles,
        risk_unit=2.0,
    )

    assert outcome.mfe_points == 3.0
    assert outcome.mae_points == 0.5
    assert outcome.book_target_1r_hit is True
    assert outcome.book_first_touch == "TARGET"


def test_official_trade_levels_are_labeled_independently():
    sample = BookDiagnosticsReplaySample(
        last_price=100.0,
        book_direction="SELL",
        official_action="BUY",
        official_direction="BUY",
        official_entry=100.0,
        official_stop=98.0,
        official_target=104.0,
    )
    candles = [C(102.0, 99.0, 101.0), C(104.5, 100.5, 104.0)]

    outcome = BookDiagnosticsOutcomeLabeler().label(sample, candles)

    assert outcome.official_trade_comparable is True
    assert outcome.official_target_hit is True
    assert outcome.official_stop_hit is False
    assert outcome.official_first_touch == "TARGET"


def test_same_bar_target_and_stop_is_marked_ambiguous():
    sample = BookDiagnosticsReplaySample(last_price=100.0, book_direction="BUY")
    candles = [C(102.5, 97.5, 100.0)]

    outcome = BookDiagnosticsOutcomeLabeler().label(
        sample,
        candles,
        risk_unit=2.0,
    )

    assert outcome.book_target_1r_hit is True
    assert outcome.book_stop_1r_hit is True
    assert outcome.book_first_touch == "AMBIGUOUS_SAME_BAR"


def test_no_future_candles_returns_unlabeled_neutral_outcome():
    sample = BookDiagnosticsReplaySample(
        symbol="WIN",
        timestamp="2026-08-22T10:00:00",
        last_price=100.0,
        book_direction="BUY",
    )

    outcome = BookDiagnosticsOutcomeLabeler().label(sample, [])

    assert outcome.horizon_bars == 0
    assert outcome.mfe_points == 0.0
    assert outcome.mae_points == 0.0
    assert outcome.book_first_touch == "NONE"


def test_recorder_sample_roundtrip_preserves_official_levels():
    sample = BookDiagnosticsReplaySample(
        official_entry=100.0,
        official_stop=98.0,
        official_target=104.0,
    )

    restored = BookDiagnosticsReplaySample.from_dict(sample.to_dict())

    assert restored.official_entry == 100.0
    assert restored.official_stop == 98.0
    assert restored.official_target == 104.0
