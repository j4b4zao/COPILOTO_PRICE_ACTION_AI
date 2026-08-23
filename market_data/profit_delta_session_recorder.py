"""Recorder observacional de sessão para a fonte real de Delta Profit/Excel."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass


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


class ProfitDeltaSessionRecorder:
    """Armazena snapshots de saúde/qualidade do Delta durante o pregão."""

    VERSION = "RC1-REAL-DELTA-SESSION-RECORDER"

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
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]
        return sample

    def summary(self) -> dict:
        total = self.size
        quality = Counter(sample.quality_status for sample in self._samples)
        source = Counter(sample.source_status for sample in self._samples)
        return {
            "version": self.VERSION,
            "samples": total,
            "quality_distribution": dict(quality),
            "source_distribution": dict(source),
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

    def _average(self, field: str) -> float:
        if not self._samples:
            return 0.0
        return round(sum(float(getattr(sample, field)) for sample in self._samples) / self.size, 4)

    @staticmethod
    def _rate(value: int, total: int) -> float:
        return round(value / total, 4) if total else 0.0
