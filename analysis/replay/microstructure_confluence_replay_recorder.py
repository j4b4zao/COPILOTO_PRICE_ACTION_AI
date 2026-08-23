"""Replay recorder observacional da confluência PA x Delta x BookDepth."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

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


class MicrostructureConfluenceReplayRecorder:
    VERSION = "RC1-MICROSTRUCTURE-CONFLUENCE-REPLAY"

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
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]
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
