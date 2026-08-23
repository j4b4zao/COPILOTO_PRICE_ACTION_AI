"""Recorder observacional de sessão para a fonte real de Delta Profit/Excel."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass(slots=True, frozen=True)
class ProfitDeltaSessionSample:
    source_status: str
    quality_status: str
    sample_count: int
    recent_delta: float
    dominance: float
    persistence: float
    acceleration: float
    impulse_ratio: float
    average_abs_delta: float
    max_abs_delta: float
    zero_delta_rate: float
    anomaly_count: int
    duplicate_rate: float
    aggression_availability_rate: float
    symbol: str = ""
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ProfitDeltaSessionSample":
        if not isinstance(data, dict):
            raise TypeError("Amostra de sessão Delta deve ser um dict.")
        names = {field.name for field in fields(cls)}
        return cls(**{name: data[name] for name in names if name in data})


class ProfitDeltaSessionRecorder:
    """Armazena snapshots de saúde/qualidade do Delta durante o pregão."""

    VERSION = "RC2-REAL-DELTA-SESSION-PERSISTENCE"

    def __init__(self, max_samples: int = 50000):
        self.max_samples = max(1, int(max_samples))
        self._samples: list[ProfitDeltaSessionSample] = []

    @property
    def samples(self) -> tuple[ProfitDeltaSessionSample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def add_sample(self, sample: ProfitDeltaSessionSample) -> None:
        if not isinstance(sample, ProfitDeltaSessionSample):
            raise TypeError("sample deve ser ProfitDeltaSessionSample.")
        self._append(sample)

    def record(self, source_snapshot, quality_report) -> ProfitDeltaSessionSample:
        sample = ProfitDeltaSessionSample(
            source_status=str(getattr(source_snapshot, "status", "NO_DATA") or "NO_DATA"),
            quality_status=str(getattr(quality_report, "status", "NO_DATA") or "NO_DATA"),
            sample_count=int(getattr(quality_report, "sample_count", 0) or 0),
            recent_delta=float(getattr(quality_report, "recent_delta", 0.0) or 0.0),
            dominance=float(getattr(quality_report, "dominance", 0.0) or 0.0),
            persistence=float(getattr(quality_report, "persistence", 0.0) or 0.0),
            acceleration=float(getattr(quality_report, "acceleration", 0.0) or 0.0),
            impulse_ratio=float(getattr(quality_report, "impulse_ratio", 0.0) or 0.0),
            average_abs_delta=float(getattr(quality_report, "average_abs_delta", 0.0) or 0.0),
            max_abs_delta=float(getattr(quality_report, "max_abs_delta", 0.0) or 0.0),
            zero_delta_rate=float(getattr(quality_report, "zero_delta_rate", 0.0) or 0.0),
            anomaly_count=int(getattr(quality_report, "anomaly_count", 0) or 0),
            duplicate_rate=float(getattr(source_snapshot, "duplicate_rate", 0.0) or 0.0),
            aggression_availability_rate=float(getattr(source_snapshot, "aggression_availability_rate", 0.0) or 0.0),
            symbol=str(getattr(source_snapshot, "symbol", "") or ""),
            passive_only=True,
        )
        self._append(sample)
        return sample

    def summary(self) -> dict:
        total = self.size
        quality = Counter(sample.quality_status for sample in self._samples)
        source = Counter(sample.source_status for sample in self._samples)
        symbols = Counter(sample.symbol for sample in self._samples if sample.symbol)
        return {
            "version": self.VERSION,
            "samples": total,
            "quality_distribution": dict(quality),
            "source_distribution": dict(source),
            "symbol_distribution": dict(symbols),
            "valid_rate": self._rate(quality.get("VALID", 0), total),
            "degraded_rate": self._rate(quality.get("DEGRADED", 0), total),
            "low_activity_rate": self._rate(quality.get("LOW_ACTIVITY", 0), total),
            "average_dominance": self._average("dominance"),
            "average_persistence": self._average("persistence"),
            "average_abs_delta": self._average("average_abs_delta"),
            "average_zero_delta_rate": self._average("zero_delta_rate"),
            "average_duplicate_rate": self._average("duplicate_rate"),
            "average_aggression_availability_rate": self._average("aggression_availability_rate"),
            "total_anomalies": sum(sample.anomaly_count for sample in self._samples),
            "max_abs_delta": max((sample.max_abs_delta for sample in self._samples), default=0.0),
            "passive_only": True,
        }

    def save_jsonl(self, path) -> Path:
        target = self._path(path, ".jsonl")
        with target.open("w", encoding="utf-8") as handle:
            for sample in self._samples:
                handle.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")
        return target

    def load_jsonl(self, path, *, clear: bool = True) -> int:
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(source)
        loaded = []
        with source.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    loaded.append(ProfitDeltaSessionSample.from_dict(json.loads(text)))
                except Exception as exc:
                    raise ValueError(f"JSONL inválido na linha {line_number}: {exc}") from exc
        if clear:
            self.clear()
        for sample in loaded:
            self.add_sample(sample)
        return len(loaded)

    def export_csv(self, path) -> Path:
        target = self._path(path, ".csv")
        fieldnames = [field.name for field in fields(ProfitDeltaSessionSample)]
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for sample in self._samples:
                writer.writerow(sample.to_dict())
        return target

    def export_summary_json(self, path) -> Path:
        target = self._path(path, ".json")
        with target.open("w", encoding="utf-8") as handle:
            json.dump(self.summary(), handle, ensure_ascii=False, indent=2)
        return target

    def _append(self, sample: ProfitDeltaSessionSample) -> None:
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]

    def _average(self, field: str) -> float:
        if not self._samples:
            return 0.0
        return round(sum(float(getattr(sample, field)) for sample in self._samples) / self.size, 4)

    @staticmethod
    def _rate(value: int, total: int) -> float:
        return round(value / total, 4) if total else 0.0

    @staticmethod
    def _path(path, suffix: str) -> Path:
        target = Path(path)
        if target.suffix.lower() != suffix:
            target = target.with_suffix(suffix)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target
