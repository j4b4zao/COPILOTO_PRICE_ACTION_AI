"""Replay recorder observacional da confluência PA x Delta x BookDepth."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from analysis.replay.microstructure_confluence import MicrostructureConfluenceAudit


@dataclass(slots=True, frozen=True)
class MicrostructureConfluenceReplaySample:
    state: str = "INSUFFICIENT_DATA"
    direction: str = "NONE"
    confluence_quality: str = "INSUFFICIENT_DATA"
    confidence: float = 0.0
    independent_evidence_count: int = 0
    correlated_evidence_count: int = 0
    conflict_count: int = 0
    price_action_bias: str = "NONE"
    flow_direction: str = "NONE"
    book_direction: str = "NONE"
    book_available: bool = False
    book_correlated_with_delta: bool = False
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "MicrostructureConfluenceReplaySample":
        if not isinstance(payload, dict):
            raise TypeError("Amostra de replay de microestrutura deve ser um dict.")
        allowed = {field.name for field in fields(cls)}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(
                "Campos desconhecidos na amostra de microestrutura: "
                + ", ".join(sorted(unknown))
            )
        return cls(**payload)


class MicrostructureConfluenceReplayRecorder:
    VERSION = "RC2-MICROSTRUCTURE-CONFLUENCE-REPLAY-PERSISTENCE"

    def __init__(self, max_samples: int = 50000):
        self.max_samples = max(1, int(max_samples))
        self._samples: list[MicrostructureConfluenceReplaySample] = []
        self.audit = MicrostructureConfluenceAudit()

    @property
    def samples(self) -> tuple[MicrostructureConfluenceReplaySample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def add_sample(self, sample: MicrostructureConfluenceReplaySample) -> None:
        if not isinstance(sample, MicrostructureConfluenceReplaySample):
            raise TypeError("sample deve ser MicrostructureConfluenceReplaySample.")
        self._append(sample)

    def record(self, context) -> MicrostructureConfluenceReplaySample:
        snapshot = self.audit.analyze(context)
        sample = MicrostructureConfluenceReplaySample(
            state=snapshot.state,
            direction=snapshot.direction,
            confluence_quality=snapshot.confluence_quality,
            confidence=snapshot.confidence,
            independent_evidence_count=snapshot.independent_evidence_count,
            correlated_evidence_count=snapshot.correlated_evidence_count,
            conflict_count=snapshot.conflict_count,
            price_action_bias=snapshot.price_action_bias,
            flow_direction=snapshot.flow_direction,
            book_direction=snapshot.book_direction,
            book_available=snapshot.book_available,
            book_correlated_with_delta=snapshot.book_correlated_with_delta,
            passive_only=True,
        )
        self._append(sample)
        return sample

    def summary(self) -> dict:
        total = len(self._samples)
        by_independent = Counter(s.independent_evidence_count for s in self._samples)
        by_quality = Counter(s.confluence_quality for s in self._samples)
        by_state = Counter(s.state for s in self._samples)
        return {
            "version": self.VERSION,
            "samples": total,
            "by_independent_evidence": dict(sorted(by_independent.items())),
            "by_quality": dict(sorted(by_quality.items())),
            "by_state": dict(sorted(by_state.items())),
            "correlated_samples": sum(s.correlated_evidence_count > 0 for s in self._samples),
            "conflict_samples": sum(s.conflict_count > 0 for s in self._samples),
            "book_available_samples": sum(s.book_available for s in self._samples),
            "average_confidence": (
                round(sum(s.confidence for s in self._samples) / total, 4)
                if total else 0.0
            ),
            "passive_only": True,
        }

    def distribution(self) -> dict:
        return {
            "one_source": sum(s.independent_evidence_count == 1 for s in self._samples),
            "two_sources": sum(s.independent_evidence_count == 2 for s in self._samples),
            "three_sources": sum(s.independent_evidence_count >= 3 for s in self._samples),
            "with_correlation": sum(s.correlated_evidence_count > 0 for s in self._samples),
            "with_conflict": sum(s.conflict_count > 0 for s in self._samples),
        }

    def scenario_summary(self) -> dict:
        return {
            "version": self.VERSION,
            "samples": len(self._samples),
            "by_quality": self._group_by("confluence_quality"),
            "by_state": self._group_by("state"),
            "by_direction": self._group_by("direction"),
            "by_independent_evidence": self._group_by("independent_evidence_count"),
            "by_correlation": self._group_by_bool(
                lambda sample: sample.correlated_evidence_count > 0,
                true_label="CORRELATED",
                false_label="INDEPENDENT",
            ),
            "by_conflict": self._group_by_bool(
                lambda sample: sample.conflict_count > 0,
                true_label="WITH_CONFLICT",
                false_label="NO_CONFLICT",
            ),
        }

    def scenario(self, *, quality=None, state=None, direction=None, independent=None, correlation=None, conflict=None) -> dict:
        selected = list(self._samples)
        filters = {}

        if quality is not None:
            value = str(quality).upper()
            filters["confluence_quality"] = value
            selected = [s for s in selected if s.confluence_quality == value]
        if state is not None:
            value = str(state).upper()
            filters["state"] = value
            selected = [s for s in selected if s.state == value]
        if direction is not None:
            value = str(direction).upper()
            filters["direction"] = value
            selected = [s for s in selected if s.direction == value]
        if independent is not None:
            value = int(independent)
            filters["independent_evidence_count"] = value
            selected = [s for s in selected if s.independent_evidence_count == value]
        if correlation is not None:
            value = str(correlation).upper()
            filters["correlation"] = value
            correlated = value == "CORRELATED"
            selected = [s for s in selected if (s.correlated_evidence_count > 0) == correlated]
        if conflict is not None:
            value = str(conflict).upper()
            filters["conflict"] = value
            with_conflict = value in {"WITH_CONFLICT", "CONFLICT", "TRUE", "1"}
            selected = [s for s in selected if (s.conflict_count > 0) == with_conflict]

        return {
            "version": self.VERSION,
            "filters": filters,
            **self._metrics(selected),
        }

    def export_jsonl(self, path) -> Path:
        destination = self._prepare_path(path, ".jsonl")
        with destination.open("w", encoding="utf-8") as handle:
            for sample in self._samples:
                handle.write(json.dumps(sample.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return destination

    def export_csv(self, path) -> Path:
        destination = self._prepare_path(path, ".csv")
        fieldnames = [field.name for field in fields(MicrostructureConfluenceReplaySample)]
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for sample in self._samples:
                writer.writerow(sample.to_dict())
        return destination

    def export_metrics_json(self, path) -> Path:
        destination = self._prepare_path(path, ".json")
        payload = {
            "summary": self.summary(),
            "distribution": self.distribution(),
            "scenarios": self.scenario_summary(),
        }
        with destination.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        return destination

    def load_jsonl(self, path, *, clear: bool = False) -> int:
        source = Path(path)
        if source.suffix.lower() != ".jsonl":
            raise ValueError("Arquivo de replay de microestrutura deve usar .jsonl.")
        if not source.exists():
            raise FileNotFoundError(source)

        loaded = []
        with source.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    sample = MicrostructureConfluenceReplaySample.from_dict(json.loads(line))
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"JSONL de microestrutura inválido na linha {line_number}."
                    ) from exc
                loaded.append(sample)

        if clear:
            self.clear()
        for sample in loaded:
            self._append(sample)
        return len(loaded)

    def _append(self, sample: MicrostructureConfluenceReplaySample) -> None:
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]

    def _group_by(self, field: str) -> dict:
        grouped = defaultdict(list)
        for sample in self._samples:
            grouped[str(getattr(sample, field))].append(sample)
        return {key: self._metrics(values) for key, values in sorted(grouped.items())}

    def _group_by_bool(self, predicate, *, true_label: str, false_label: str) -> dict:
        grouped = {true_label: [], false_label: []}
        for sample in self._samples:
            grouped[true_label if predicate(sample) else false_label].append(sample)
        return {key: self._metrics(values) for key, values in grouped.items() if values}

    @staticmethod
    def _metrics(samples) -> dict:
        samples = list(samples)
        total = len(samples)
        return {
            "samples": total,
            "average_confidence": (
                round(sum(s.confidence for s in samples) / total, 4) if total else 0.0
            ),
            "average_independent_evidence": (
                round(sum(s.independent_evidence_count for s in samples) / total, 4)
                if total else 0.0
            ),
            "average_correlated_evidence": (
                round(sum(s.correlated_evidence_count for s in samples) / total, 4)
                if total else 0.0
            ),
            "average_conflict_count": (
                round(sum(s.conflict_count for s in samples) / total, 4)
                if total else 0.0
            ),
            "book_available_samples": sum(s.book_available for s in samples),
            "correlated_samples": sum(s.correlated_evidence_count > 0 for s in samples),
            "conflict_samples": sum(s.conflict_count > 0 for s in samples),
        }

    @staticmethod
    def _prepare_path(path, expected_suffix: str) -> Path:
        destination = Path(path)
        if destination.suffix.lower() != expected_suffix:
            raise ValueError(f"Arquivo deve usar extensão {expected_suffix}.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination
