"""Recorder passivo da elegibilidade de confluência de microestrutura."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from analysis.replay.microstructure_confluence import MicrostructureConfluenceAudit
from analysis.replay.microstructure_eligibility_policy import MicrostructureEligibilityPolicy


@dataclass(slots=True, frozen=True)
class MicrostructureEligibilityReplaySample:
    state: str = "NOT_ELIGIBLE"
    reason: str = "INSUFFICIENT_DATA"
    independent_evidence_count: int = 0
    confluence_quality: str = "INSUFFICIENT_DATA"
    confidence: float = 0.0
    conflict_count: int = 0
    correlated_evidence_count: int = 0
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "MicrostructureEligibilityReplaySample":
        if not isinstance(payload, dict):
            raise TypeError("Amostra de elegibilidade deve ser um dict.")
        allowed = {field.name for field in fields(cls)}
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError("Campos desconhecidos: " + ", ".join(sorted(unknown)))
        return cls(**payload)


class MicrostructureEligibilityReplayRecorder:
    VERSION = "RC2-MICROSTRUCTURE-ELIGIBILITY-REPLAY-PERSISTENCE"

    def __init__(self, max_samples: int = 50000):
        self.max_samples = max(1, int(max_samples))
        self._samples: list[MicrostructureEligibilityReplaySample] = []
        self.audit = MicrostructureConfluenceAudit()
        self.policy = MicrostructureEligibilityPolicy()

    @property
    def samples(self) -> tuple[MicrostructureEligibilityReplaySample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def add_sample(self, sample: MicrostructureEligibilityReplaySample) -> None:
        if not isinstance(sample, MicrostructureEligibilityReplaySample):
            raise TypeError("sample deve ser MicrostructureEligibilityReplaySample.")
        self._append(sample)

    def record(self, context) -> MicrostructureEligibilityReplaySample:
        snapshot = self.audit.analyze(context)
        decision = self.policy.evaluate(snapshot)
        sample = MicrostructureEligibilityReplaySample(
            state=decision.state,
            reason=decision.reason,
            independent_evidence_count=decision.independent_evidence_count,
            confluence_quality=decision.confluence_quality,
            confidence=decision.confidence,
            conflict_count=decision.conflict_count,
            correlated_evidence_count=decision.correlated_evidence_count,
            passive_only=True,
        )
        self._append(sample)
        return sample

    def summary(self) -> dict:
        total = len(self._samples)
        by_state = Counter(sample.state for sample in self._samples)
        by_reason = Counter(sample.reason for sample in self._samples)
        by_quality = Counter(sample.confluence_quality for sample in self._samples)
        by_independent = Counter(sample.independent_evidence_count for sample in self._samples)
        return {
            "version": self.VERSION,
            "samples": total,
            "by_state": dict(sorted(by_state.items())),
            "by_reason": dict(sorted(by_reason.items())),
            "by_quality": dict(sorted(by_quality.items())),
            "by_independent_evidence": dict(sorted(by_independent.items())),
            "not_eligible_samples": by_state.get("NOT_ELIGIBLE", 0),
            "observable_samples": by_state.get("OBSERVABLE", 0),
            "promising_samples": by_state.get("PROMISING", 0),
            "strong_candidate_samples": by_state.get("STRONG_CANDIDATE", 0),
            "conflict_samples": sum(sample.conflict_count > 0 for sample in self._samples),
            "correlated_samples": sum(sample.correlated_evidence_count > 0 for sample in self._samples),
            "average_confidence": round(sum(sample.confidence for sample in self._samples) / total, 4) if total else 0.0,
            "passive_only": True,
        }

    def rates(self) -> dict:
        total = len(self._samples)
        if not total:
            return {key: 0.0 for key in (
                "not_eligible_rate", "observable_rate", "promising_rate",
                "strong_candidate_rate", "conflict_rate", "correlation_rate"
            )}
        states = Counter(sample.state for sample in self._samples)
        return {
            "not_eligible_rate": round(states.get("NOT_ELIGIBLE", 0) / total, 4),
            "observable_rate": round(states.get("OBSERVABLE", 0) / total, 4),
            "promising_rate": round(states.get("PROMISING", 0) / total, 4),
            "strong_candidate_rate": round(states.get("STRONG_CANDIDATE", 0) / total, 4),
            "conflict_rate": round(sum(s.conflict_count > 0 for s in self._samples) / total, 4),
            "correlation_rate": round(sum(s.correlated_evidence_count > 0 for s in self._samples) / total, 4),
        }

    def export_jsonl(self, path) -> Path:
        destination = self._prepare_path(path, ".jsonl")
        with destination.open("w", encoding="utf-8") as handle:
            for sample in self._samples:
                handle.write(json.dumps(sample.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return destination

    def export_csv(self, path) -> Path:
        destination = self._prepare_path(path, ".csv")
        names = [field.name for field in fields(MicrostructureEligibilityReplaySample)]
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=names)
            writer.writeheader()
            for sample in self._samples:
                writer.writerow(sample.to_dict())
        return destination

    def export_metrics_json(self, path) -> Path:
        destination = self._prepare_path(path, ".json")
        with destination.open("w", encoding="utf-8") as handle:
            json.dump({"summary": self.summary(), "rates": self.rates()}, handle, ensure_ascii=False, indent=2, sort_keys=True)
        return destination

    def load_jsonl(self, path, *, clear: bool = False) -> int:
        source = Path(path)
        if source.suffix.lower() != ".jsonl":
            raise ValueError("Arquivo de elegibilidade deve usar .jsonl.")
        if not source.exists():
            raise FileNotFoundError(source)
        loaded = []
        with source.open("r", encoding="utf-8") as handle:
            for line_number, raw in enumerate(handle, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    loaded.append(MicrostructureEligibilityReplaySample.from_dict(json.loads(line)))
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise ValueError(f"JSONL de elegibilidade inválido na linha {line_number}.") from exc
        if clear:
            self.clear()
        for sample in loaded:
            self._append(sample)
        return len(loaded)

    def _append(self, sample: MicrostructureEligibilityReplaySample) -> None:
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]

    @staticmethod
    def _prepare_path(path, suffix: str) -> Path:
        destination = Path(path)
        if destination.suffix.lower() != suffix:
            raise ValueError(f"Arquivo deve usar extensão {suffix}.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination
