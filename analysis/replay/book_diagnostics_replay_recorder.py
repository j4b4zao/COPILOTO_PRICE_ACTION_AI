"""
analysis/replay/book_diagnostics_replay_recorder.py

BookDiagnostics RC9 - Replay/A-B recorder + persistence.

Captura, ao final de cada ciclo da pipeline, uma fotografia comparativa entre:
- decisão oficial do núcleo;
- síntese observacional do BookDiagnostics.

RC9 adiciona exportação explícita para JSONL e CSV para replay/auditoria.
O recorder continua estritamente passivo: não escreve em AnalysisContext e não
altera Strategy, Score, Risk, Decision ou execução.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


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

    @classmethod
    def from_dict(cls, payload: dict) -> "BookDiagnosticsReplaySample":
        allowed = cls.__dataclass_fields__.keys()
        clean = {key: payload[key] for key in allowed if key in payload}
        return cls(**clean)


class BookDiagnosticsReplayRecorder:
    """In-memory A/B recorder for passive validation and replay analysis."""

    VERSION = "RC9-REPLAY-PERSISTENCE"

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

        self._append(sample)
        return sample

    def add_sample(self, sample: BookDiagnosticsReplaySample) -> None:
        if not isinstance(sample, BookDiagnosticsReplaySample):
            raise TypeError("sample must be BookDiagnosticsReplaySample")
        self._append(sample)

    def _append(self, sample: BookDiagnosticsReplaySample) -> None:
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]

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

    def export_jsonl(self, path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8", newline="") as handle:
            for sample in self._samples:
                handle.write(
                    json.dumps(sample.to_dict(), ensure_ascii=False, sort_keys=True)
                    + "\n"
                )
        return destination

    def export_csv(self, path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fields = list(BookDiagnosticsReplaySample.__dataclass_fields__.keys())
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for sample in self._samples:
                writer.writerow(sample.to_dict())
        return destination

    @classmethod
    def load_jsonl(
        cls,
        path,
        max_samples: int = 50000,
    ) -> "BookDiagnosticsReplayRecorder":
        recorder = cls(max_samples=max_samples)
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(source)

        with source.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL at line {line_number}: {exc.msg}"
                    ) from exc
                if not isinstance(payload, dict):
                    raise ValueError(
                        f"Invalid JSONL at line {line_number}: object expected"
                    )
                recorder.add_sample(BookDiagnosticsReplaySample.from_dict(payload))
        return recorder

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
