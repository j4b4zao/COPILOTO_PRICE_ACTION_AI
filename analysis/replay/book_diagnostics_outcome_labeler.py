"""
analysis/replay/book_diagnostics_outcome_labeler.py

BookDiagnostics RC10 - Outcome Labeling.

Rotula resultados futuros para amostras do replay sem alterar qualquer decisão
operacional. Mede MFE/MAE na direção experimental, direção futura, níveis 1R
hipotéticos e, quando disponíveis, stop/target oficiais.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_replay_recorder import (
    BookDiagnosticsReplaySample,
)


@dataclass(slots=True, frozen=True)
class BookDiagnosticsOutcome:
    symbol: str = ""
    timestamp: str = ""
    horizon_bars: int = 0
    reference_price: float = 0.0
    book_direction: str = "NONE"

    future_close: float = 0.0
    future_change_points: float = 0.0
    future_direction: str = "NONE"

    mfe_points: float = 0.0
    mae_points: float = 0.0
    mfe_r: float = 0.0
    mae_r: float = 0.0

    risk_unit: float = 0.0
    book_target_1r_hit: bool = False
    book_stop_1r_hit: bool = False
    book_first_touch: str = "NONE"

    official_trade_comparable: bool = False
    official_target_hit: bool = False
    official_stop_hit: bool = False
    official_first_touch: str = "NONE"

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsOutcomeLabeler:
    """Future-path labeler for passive BookDiagnostics replay validation."""

    VERSION = "RC10-OUTCOME-LABELING"

    def label(
        self,
        sample: BookDiagnosticsReplaySample,
        future_candles,
        horizon_bars: int = 10,
        risk_unit: float | None = None,
    ) -> BookDiagnosticsOutcome:
        if not isinstance(sample, BookDiagnosticsReplaySample):
            raise TypeError("sample must be BookDiagnosticsReplaySample")

        candles = list(future_candles or [])[: max(0, int(horizon_bars))]
        if not candles:
            return BookDiagnosticsOutcome(
                symbol=sample.symbol,
                timestamp=sample.timestamp,
                horizon_bars=0,
                reference_price=float(sample.last_price),
                book_direction=str(sample.book_direction).upper(),
            )

        reference = float(sample.last_price)
        direction = str(sample.book_direction or "NONE").upper()
        closes = [float(c.close) for c in candles]
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]
        future_close = closes[-1]
        raw_change = future_close - reference

        if raw_change > 0:
            future_direction = "BUY"
        elif raw_change < 0:
            future_direction = "SELL"
        else:
            future_direction = "NONE"

        if direction == "BUY":
            mfe = max(max(highs) - reference, 0.0)
            mae = max(reference - min(lows), 0.0)
        elif direction == "SELL":
            mfe = max(reference - min(lows), 0.0)
            mae = max(max(highs) - reference, 0.0)
        else:
            mfe = 0.0
            mae = 0.0

        unit = self._resolve_risk_unit(sample, candles, risk_unit)
        mfe_r = mfe / unit if unit > 0 else 0.0
        mae_r = mae / unit if unit > 0 else 0.0

        target_hit, stop_hit, first_touch = self._hypothetical_1r_path(
            direction,
            reference,
            unit,
            candles,
        )

        official_comparable, official_target_hit, official_stop_hit, official_first = (
            self._official_path(sample, candles)
        )

        return BookDiagnosticsOutcome(
            symbol=sample.symbol,
            timestamp=sample.timestamp,
            horizon_bars=len(candles),
            reference_price=reference,
            book_direction=direction,
            future_close=round(future_close, 6),
            future_change_points=round(raw_change, 6),
            future_direction=future_direction,
            mfe_points=round(mfe, 6),
            mae_points=round(mae, 6),
            mfe_r=round(mfe_r, 4),
            mae_r=round(mae_r, 4),
            risk_unit=round(unit, 6),
            book_target_1r_hit=target_hit,
            book_stop_1r_hit=stop_hit,
            book_first_touch=first_touch,
            official_trade_comparable=official_comparable,
            official_target_hit=official_target_hit,
            official_stop_hit=official_stop_hit,
            official_first_touch=official_first,
        )

    @staticmethod
    def _resolve_risk_unit(sample, candles, explicit) -> float:
        if explicit is not None and float(explicit) > 0:
            return float(explicit)

        entry = float(sample.official_entry or 0.0)
        stop = float(sample.official_stop or 0.0)
        if entry > 0 and stop > 0 and entry != stop:
            return abs(entry - stop)

        avg_range = sum(
            max(float(c.high) - float(c.low), 0.0)
            for c in candles
        ) / len(candles)
        return max(avg_range, 0.0)

    @staticmethod
    def _hypothetical_1r_path(direction, reference, unit, candles):
        if direction not in {"BUY", "SELL"} or unit <= 0:
            return False, False, "NONE"

        if direction == "BUY":
            target = reference + unit
            stop = reference - unit
            target_test = lambda c: float(c.high) >= target
            stop_test = lambda c: float(c.low) <= stop
        else:
            target = reference - unit
            stop = reference + unit
            target_test = lambda c: float(c.low) <= target
            stop_test = lambda c: float(c.high) >= stop

        target_hit = False
        stop_hit = False
        first_touch = "NONE"
        for candle in candles:
            hit_target = target_test(candle)
            hit_stop = stop_test(candle)
            target_hit = target_hit or hit_target
            stop_hit = stop_hit or hit_stop
            if first_touch == "NONE":
                if hit_target and hit_stop:
                    first_touch = "AMBIGUOUS_SAME_BAR"
                elif hit_target:
                    first_touch = "TARGET"
                elif hit_stop:
                    first_touch = "STOP"
        return target_hit, stop_hit, first_touch

    @staticmethod
    def _official_path(sample, candles):
        direction = str(sample.official_direction or "NONE").upper()
        entry = float(sample.official_entry or 0.0)
        stop = float(sample.official_stop or 0.0)
        target = float(sample.official_target or 0.0)

        comparable = bool(
            direction in {"BUY", "SELL"}
            and entry > 0
            and stop > 0
            and target > 0
            and stop != target
        )
        if not comparable:
            return False, False, False, "NONE"

        if direction == "BUY":
            target_test = lambda c: float(c.high) >= target
            stop_test = lambda c: float(c.low) <= stop
        else:
            target_test = lambda c: float(c.low) <= target
            stop_test = lambda c: float(c.high) >= stop

        target_hit = False
        stop_hit = False
        first_touch = "NONE"
        for candle in candles:
            hit_target = target_test(candle)
            hit_stop = stop_test(candle)
            target_hit = target_hit or hit_target
            stop_hit = stop_hit or hit_stop
            if first_touch == "NONE":
                if hit_target and hit_stop:
                    first_touch = "AMBIGUOUS_SAME_BAR"
                elif hit_target:
                    first_touch = "TARGET"
                elif hit_stop:
                    first_touch = "STOP"
        return True, target_hit, stop_hit, first_touch
