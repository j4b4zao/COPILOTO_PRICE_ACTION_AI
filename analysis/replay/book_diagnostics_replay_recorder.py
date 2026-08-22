"""
analysis/replay/book_diagnostics_replay_recorder.py

BookDiagnostics RC8 - Replay/A-B recorder.

Captura, ao final de cada ciclo da pipeline, uma fotografia comparativa entre:
- decisão oficial do núcleo;
- síntese observacional do BookDiagnostics RC7.

O recorder é estritamente passivo: não escreve em AnalysisContext e não altera
Strategy, Score, Risk, Decision ou execução.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class BookDiagnosticsReplaySample:
    symbol: str = ""
    timeframe: str = ""
    timestamp: str = ""
    candle_count: int = 0
    last_price: float = 0.0

    official_action: str = "WAIT"
    official_direction: str = "NONE"
    official_score: float = 0.0
    official_risk_reward: float = 0.0
    official_setup: str = ""

    book_state: str = "NEUTRAL"
    book_direction: str = "NONE"
    book_score: float = 0.0
    book_caution_count: int = 0

    trend_control_state: str = "NEUTRAL"
    reversal_pressure_state: str = "NONE"
    market_environment_state: str = "NORMAL_OR_OTHER"

    direction_agreement: str = "NOT_COMPARABLE"
    book_passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsReplayRecorder:
    """In-memory A/B recorder for passive validation and replay analysis."""

    VERSION = "RC8-REPLAY-AB"

    def __init__(self, max_samples: int = 50000):
        self.max_samples = max(1, int(max_samples))
        self._samples: list[BookDiagnosticsReplaySample] = []

    @property
    def samples(self) -> tuple[BookDiagnosticsReplaySample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def record(self, context) -> BookDiagnosticsReplaySample:
        market = context.market
        decision = context.decision
        book = context.book_diagnostics

        official_action = str(getattr(decision, "action", "WAIT") or "WAIT").upper()
        official_direction = str(
            getattr(decision, "direction", "NONE") or "NONE"
        ).upper()
        if official_direction not in {"BUY", "SELL"} and official_action in {"BUY", "SELL"}:
            official_direction = official_action

        book_direction = str(
            getattr(book, "synthesis_direction", "NONE") or "NONE"
        ).upper()

        agreement = self._direction_agreement(
            official_action=official_action,
            official_direction=official_direction,
            book_direction=book_direction,
        )

        timestamp = getattr(market, "timestamp", None)
        timestamp_text = timestamp.isoformat() if timestamp is not None else ""

        sample = BookDiagnosticsReplaySample(
            symbol=str(getattr(market, "symbol", "") or ""),
            timeframe=str(getattr(market, "timeframe", "") or ""),
            timestamp=timestamp_text,
            candle_count=int(getattr(market, "candle_count", 0) or 0),
            last_price=float(getattr(market, "last_price", 0.0) or 0.0),
            official_action=official_action,
            official_direction=official_direction,
            official_score=float(getattr(decision, "score", 0.0) or 0.0),
            official_risk_reward=float(getattr(decision, "risk_reward", 0.0) or 0.0),
            official_setup=str(getattr(decision, "setup", "") or ""),
            book_state=str(getattr(book, "synthesis_state", "NEUTRAL") or "NEUTRAL"),
            book_direction=book_direction,
            book_score=float(getattr(book, "synthesis_score", 0.0) or 0.0),
            book_caution_count=int(getattr(book, "caution_count", 0) or 0),
            trend_control_state=str(
                getattr(book, "trend_control_state", "NEUTRAL") or "NEUTRAL"
            ),
            reversal_pressure_state=str(
                getattr(book, "reversal_pressure_state", "NONE") or "NONE"
            ),
            market_environment_state=str(
                getattr(book, "market_environment_state", "NORMAL_OR_OTHER")
                or "NORMAL_OR_OTHER"
            ),
            direction_agreement=agreement,
            book_passive_only=bool(getattr(book, "passive_only", True)),
        )

        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]

        return sample

    def summary(self) -> dict:
        total = len(self._samples)
        comparable = [s for s in self._samples if s.direction_agreement != "NOT_COMPARABLE"]
        agreements = sum(s.direction_agreement == "AGREE" for s in comparable)
        conflicts = sum(s.direction_agreement == "CONFLICT" for s in comparable)

        return {
            "version": self.VERSION,
            "samples": total,
            "comparable": len(comparable),
            "agreements": agreements,
            "conflicts": conflicts,
            "agreement_rate": round(agreements / len(comparable), 4) if comparable else 0.0,
            "conflict_rate": round(conflicts / len(comparable), 4) if comparable else 0.0,
        }

    @staticmethod
    def _direction_agreement(
        official_action: str,
        official_direction: str,
        book_direction: str,
    ) -> str:
        if official_action not in {"BUY", "SELL"}:
            return "NOT_COMPARABLE"
        if official_direction not in {"BUY", "SELL"}:
            return "NOT_COMPARABLE"
        if book_direction not in {"BUY", "SELL"}:
            return "NOT_COMPARABLE"
        return "AGREE" if official_direction == book_direction else "CONFLICT"
