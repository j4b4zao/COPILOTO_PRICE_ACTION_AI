"""
analysis/replay/book_diagnostics_shadow_outcome_tracker.py

BookDiagnostics RC19 - Shadow Outcome Tracker.

Avalia o que teria acontecido apos cada observacao aprovada em Shadow Mode.
A camada mede caminho futuro, MFE/MAE, toque de alvo/stop hipotetico de 1R,
direcao futura e edge observacional.

Regras de seguranca:
- somente observacoes geradas por BookDiagnosticsShadowMode;
- somente BUY/SELL sao avaliados como trades shadow;
- nao altera Candidate Registry;
- nao altera AnalysisContext, Strategy, Score, Risk, Decision ou Alert;
- toque simultaneo de alvo e stop na mesma barra e AMBIGUOUS_SAME_BAR.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from analysis.replay.book_diagnostics_shadow_mode import ShadowObservation


@dataclass(slots=True, frozen=True)
class ShadowOutcome:
    timestamp: str
    book_state: str
    shadow_action: str
    reference_price: float
    horizon_bars: int

    future_close: float = 0.0
    future_change_points: float = 0.0
    future_direction: str = "NONE"

    risk_unit: float = 0.0
    mfe_points: float = 0.0
    mae_points: float = 0.0
    mfe_r: float = 0.0
    mae_r: float = 0.0
    edge_r: float = 0.0

    target_1r_hit: bool = False
    stop_1r_hit: bool = False
    first_touch: str = "NONE"
    direction_correct: bool = False

    official_action: str = "NONE"
    shadow_official_agreement: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsShadowOutcomeTracker:
    VERSION = "RC19-SHADOW-OUTCOME-TRACKER"

    def __init__(self):
        self._outcomes: list[ShadowOutcome] = []

    def track(
        self,
        observation: ShadowObservation,
        future_candles,
        *,
        horizon_bars: int = 10,
        risk_unit: float | None = None,
    ) -> ShadowOutcome:
        if not isinstance(observation, ShadowObservation):
            raise TypeError("observation must be ShadowObservation")

        action = str(observation.shadow_action or "NONE").upper()
        if action not in {"BUY", "SELL"}:
            raise ValueError("shadow observation must be directional")
        if observation.market_price is None or float(observation.market_price) <= 0.0:
            raise ValueError("shadow observation requires positive market_price")

        candles = list(future_candles or [])[: max(0, int(horizon_bars))]
        reference = float(observation.market_price)

        if not candles:
            outcome = ShadowOutcome(
                timestamp=observation.timestamp,
                book_state=observation.book_state,
                shadow_action=action,
                reference_price=reference,
                horizon_bars=0,
                official_action=observation.official_action,
                shadow_official_agreement=observation.agreement,
            )
            self._outcomes.append(outcome)
            return outcome

        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]
        closes = [float(c.close) for c in candles]
        future_close = closes[-1]
        change = future_close - reference

        if change > 0:
            future_direction = "BUY"
        elif change < 0:
            future_direction = "SELL"
        else:
            future_direction = "NONE"

        if action == "BUY":
            mfe = max(max(highs) - reference, 0.0)
            mae = max(reference - min(lows), 0.0)
        else:
            mfe = max(reference - min(lows), 0.0)
            mae = max(max(highs) - reference, 0.0)

        unit = self._resolve_risk_unit(candles, risk_unit)
        mfe_r = (mfe / unit) if unit > 0.0 else 0.0
        mae_r = (mae / unit) if unit > 0.0 else 0.0
        target_hit, stop_hit, first_touch = self._path_1r(
            action,
            reference,
            unit,
            candles,
        )

        outcome = ShadowOutcome(
            timestamp=observation.timestamp,
            book_state=observation.book_state,
            shadow_action=action,
            reference_price=reference,
            horizon_bars=len(candles),
            future_close=round(future_close, 6),
            future_change_points=round(change, 6),
            future_direction=future_direction,
            risk_unit=round(unit, 6),
            mfe_points=round(mfe, 6),
            mae_points=round(mae, 6),
            mfe_r=round(mfe_r, 4),
            mae_r=round(mae_r, 4),
            edge_r=round(mfe_r - mae_r, 4),
            target_1r_hit=target_hit,
            stop_1r_hit=stop_hit,
            first_touch=first_touch,
            direction_correct=(future_direction == action),
            official_action=observation.official_action,
            shadow_official_agreement=observation.agreement,
        )
        self._outcomes.append(outcome)
        return outcome

    def all(self) -> list[dict]:
        return [item.to_dict() for item in self._outcomes]

    def by_state(self, book_state: str) -> list[dict]:
        state = str(book_state or "").upper().strip()
        if not state:
            raise ValueError("book_state is required")
        return [row for row in self.all() if row["book_state"] == state]

    def metrics(self, book_state: str | None = None) -> dict:
        rows = self.all() if book_state is None else self.by_state(book_state)
        completed = [row for row in rows if row["horizon_bars"] > 0]
        target_first = [row for row in completed if row["first_touch"] == "TARGET"]
        stop_first = [row for row in completed if row["first_touch"] == "STOP"]
        ambiguous = [
            row for row in completed
            if row["first_touch"] == "AMBIGUOUS_SAME_BAR"
        ]
        direction_correct = [row for row in completed if row["direction_correct"]]

        def avg(field):
            return (
                sum(float(row[field]) for row in completed) / len(completed)
                if completed else 0.0
            )

        return {
            "version": self.VERSION,
            "book_state": (
                None
                if book_state is None
                else str(book_state or "").upper().strip()
            ),
            "outcomes": len(rows),
            "completed": len(completed),
            "target_first": len(target_first),
            "stop_first": len(stop_first),
            "ambiguous_same_bar": len(ambiguous),
            "target_first_rate": (
                len(target_first) / len(completed) if completed else 0.0
            ),
            "stop_first_rate": (
                len(stop_first) / len(completed) if completed else 0.0
            ),
            "direction_correct_rate": (
                len(direction_correct) / len(completed) if completed else 0.0
            ),
            "avg_mfe_r": round(avg("mfe_r"), 4),
            "avg_mae_r": round(avg("mae_r"), 4),
            "avg_edge_r": round(avg("edge_r"), 4),
        }

    def snapshot(self) -> dict:
        return {
            "version": self.VERSION,
            "outcomes": self.all(),
            "metrics": self.metrics(),
        }

    def save_json(self, path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.snapshot(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return target

    @classmethod
    def load_json(cls, path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        tracker = cls()
        for item in payload.get("outcomes", []):
            tracker._outcomes.append(ShadowOutcome(**item))
        return tracker

    @staticmethod
    def _resolve_risk_unit(candles, explicit) -> float:
        if explicit is not None:
            value = float(explicit)
            if value <= 0.0:
                raise ValueError("risk_unit must be positive")
            return value

        avg_range = sum(
            max(float(c.high) - float(c.low), 0.0)
            for c in candles
        ) / len(candles)
        return max(avg_range, 0.0)

    @staticmethod
    def _path_1r(action, reference, unit, candles):
        if unit <= 0.0:
            return False, False, "NONE"

        if action == "BUY":
            target = reference + unit
            stop = reference - unit
            hit_target = lambda c: float(c.high) >= target
            hit_stop = lambda c: float(c.low) <= stop
        else:
            target = reference - unit
            stop = reference + unit
            hit_target = lambda c: float(c.low) <= target
            hit_stop = lambda c: float(c.high) >= stop

        target_hit = False
        stop_hit = False
        first_touch = "NONE"
        for candle in candles:
            target_now = hit_target(candle)
            stop_now = hit_stop(candle)
            target_hit = target_hit or target_now
            stop_hit = stop_hit or stop_now
            if first_touch == "NONE":
                if target_now and stop_now:
                    first_touch = "AMBIGUOUS_SAME_BAR"
                elif target_now:
                    first_touch = "TARGET"
                elif stop_now:
                    first_touch = "STOP"
        return target_hit, stop_hit, first_touch
