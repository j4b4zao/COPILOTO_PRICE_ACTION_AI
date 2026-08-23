"""Recorder passivo da elegibilidade de confluência de microestrutura."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

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


class MicrostructureEligibilityReplayRecorder:
    VERSION = "RC1-MICROSTRUCTURE-ELIGIBILITY-REPLAY"

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
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]
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
            "correlated_samples": sum(
                sample.correlated_evidence_count > 0 for sample in self._samples
            ),
            "average_confidence": (
                round(sum(sample.confidence for sample in self._samples) / total, 4)
                if total else 0.0
            ),
            "passive_only": True,
        }

    def rates(self) -> dict:
        total = len(self._samples)
        if not total:
            return {
                "not_eligible_rate": 0.0,
                "observable_rate": 0.0,
                "promising_rate": 0.0,
                "strong_candidate_rate": 0.0,
                "conflict_rate": 0.0,
                "correlation_rate": 0.0,
            }

        states = Counter(sample.state for sample in self._samples)
        return {
            "not_eligible_rate": round(states.get("NOT_ELIGIBLE", 0) / total, 4),
            "observable_rate": round(states.get("OBSERVABLE", 0) / total, 4),
            "promising_rate": round(states.get("PROMISING", 0) / total, 4),
            "strong_candidate_rate": round(states.get("STRONG_CANDIDATE", 0) / total, 4),
            "conflict_rate": round(
                sum(sample.conflict_count > 0 for sample in self._samples) / total, 4
            ),
            "correlation_rate": round(
                sum(sample.correlated_evidence_count > 0 for sample in self._samples) / total,
                4,
            ),
        }
