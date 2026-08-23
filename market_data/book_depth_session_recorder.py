"""Recorder observacional de sessão para BookDepth real, com persistência."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass(slots=True, frozen=True)
class BookDepthSessionSample:
    source_status: str
    quality_status: str
    bid_levels: int
    ask_levels: int
    spread: float
    spread_ratio: float
    imbalance: float
    top_bid_concentration: float
    top_ask_concentration: float
    concentration_edge: float
    duplicate_rate: float
    availability_rate: float
    anomaly_count: int
    symbol: str = ""
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class BookDepthSessionRecorder:
    VERSION = "RC2-BOOK-DEPTH-SESSION-PERSISTENCE"

    def __init__(self, max_samples: int = 50000):
        self.max_samples = max(1, int(max_samples))
        self._samples: list[BookDepthSessionSample] = []

    @property
    def samples(self): return tuple(self._samples)
    @property
    def size(self): return len(self._samples)
    def clear(self): self._samples.clear()

    def record(self, source_report, quality_report) -> BookDepthSessionSample:
        sample = BookDepthSessionSample(
            source_status=str(getattr(source_report, "status", "NO_DATA") or "NO_DATA"),
            quality_status=str(getattr(quality_report, "status", "NO_DATA") or "NO_DATA"),
            bid_levels=int(getattr(quality_report, "levels_bid", 0) or 0),
            ask_levels=int(getattr(quality_report, "levels_ask", 0) or 0),
            spread=float(getattr(quality_report, "spread", 0.0) or 0.0),
            spread_ratio=float(getattr(quality_report, "spread_ratio", 0.0) or 0.0),
            imbalance=float(getattr(quality_report, "imbalance", 0.0) or 0.0),
            top_bid_concentration=float(getattr(quality_report, "top_bid_concentration", 0.0) or 0.0),
            top_ask_concentration=float(getattr(quality_report, "top_ask_concentration", 0.0) or 0.0),
            concentration_edge=float(getattr(quality_report, "concentration_edge", 0.0) or 0.0),
            duplicate_rate=float(getattr(source_report, "duplicate_rate", 0.0) or 0.0),
            availability_rate=float(getattr(source_report, "availability_rate", 0.0) or 0.0),
            anomaly_count=int(getattr(quality_report, "anomaly_count", 0) or 0),
            symbol=str(getattr(source_report, "symbol", "") or ""), passive_only=True)
        self._append(sample)
        return sample

    def _append(self, sample):
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0: del self._samples[:overflow]

    def save_jsonl(self, path) -> Path:
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for sample in self._samples: f.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")
        return path

    def load_jsonl(self, path, *, clear=True) -> int:
        path = Path(path)
        if clear: self.clear()
        if not path.exists(): return 0
        loaded = 0
        allowed = {f.name for f in fields(BookDepthSessionSample)}
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                raw = json.loads(line)
                self._append(BookDepthSessionSample(**{k: v for k, v in raw.items() if k in allowed}))
                loaded += 1
        return loaded

    def export_csv(self, path) -> Path:
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        names = [f.name for f in fields(BookDepthSessionSample)]
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=names); writer.writeheader()
            for sample in self._samples: writer.writerow(sample.to_dict())
        return path

    def export_summary_json(self, path) -> Path:
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.summary(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def summary(self) -> dict:
        total = self.size; quality = Counter(s.quality_status for s in self._samples); source = Counter(s.source_status for s in self._samples)
        return {"version": self.VERSION, "samples": total, "quality_distribution": dict(quality),
                "source_distribution": dict(source), "valid_rate": self._rate(quality.get("VALID", 0), total),
                "degraded_rate": self._rate(quality.get("DEGRADED", 0), total),
                "shallow_rate": self._rate(quality.get("SHALLOW", 0), total),
                "average_bid_levels": self._average("bid_levels"), "average_ask_levels": self._average("ask_levels"),
                "average_spread": self._average("spread"), "average_spread_ratio": self._average("spread_ratio"),
                "average_abs_imbalance": self._average_abs("imbalance"),
                "average_concentration_edge": self._average("concentration_edge"),
                "average_duplicate_rate": self._average("duplicate_rate"),
                "average_availability_rate": self._average("availability_rate"),
                "total_anomalies": sum(s.anomaly_count for s in self._samples), "passive_only": True}

    def _average(self, field): return round(sum(float(getattr(s, field)) for s in self._samples) / self.size, 6) if self._samples else 0.0
    def _average_abs(self, field): return round(sum(abs(float(getattr(s, field))) for s in self._samples) / self.size, 6) if self._samples else 0.0
    @staticmethod
    def _rate(value, total): return round(value / total, 4) if total else 0.0
