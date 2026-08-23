"""Relatório passivo de sessão da confluência PA x Delta x BookDepth."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class MicrostructureConfluenceSessionReport:
    samples: int = 0
    high_quality_samples: int = 0
    medium_quality_samples: int = 0
    low_quality_samples: int = 0
    conflict_samples: int = 0
    correlated_samples: int = 0
    one_source_samples: int = 0
    two_source_samples: int = 0
    three_source_samples: int = 0
    high_quality_rate: float = 0.0
    three_source_rate: float = 0.0
    conflict_rate: float = 0.0
    correlation_rate: float = 0.0
    average_confidence: float = 0.0
    session_quality: str = "NO_DATA"
    recommendation: str = "COLLECT_MORE_DATA"
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class MicrostructureConfluenceSessionReporter:
    VERSION = "RC1-MICROSTRUCTURE-CONFLUENCE-SESSION-REPORT"
    MIN_SAMPLES = 100

    def build(self, recorder) -> MicrostructureConfluenceSessionReport:
        samples = list(recorder.samples)
        total = len(samples)
        if not total:
            return MicrostructureConfluenceSessionReport()

        high = sum(s.confluence_quality == "HIGH" for s in samples)
        medium = sum(s.confluence_quality == "MEDIUM" for s in samples)
        low = sum(s.confluence_quality == "LOW" for s in samples)
        conflicts = sum(s.conflict_count > 0 or s.state == "CONFLICT" for s in samples)
        correlated = sum(s.correlated_evidence_count > 0 for s in samples)
        one = sum(s.independent_evidence_count == 1 for s in samples)
        two = sum(s.independent_evidence_count == 2 for s in samples)
        three = sum(s.independent_evidence_count >= 3 for s in samples)
        avg_conf = sum(float(s.confidence) for s in samples) / total

        high_rate = high / total
        three_rate = three / total
        conflict_rate = conflicts / total
        correlation_rate = correlated / total

        if conflict_rate >= 0.25:
            quality = "DEGRADED_BY_CONFLICT"
        elif high_rate >= 0.30 and three_rate >= 0.20 and conflict_rate <= 0.10:
            quality = "STRONG_INDEPENDENT_CONFLUENCE"
        elif high_rate >= 0.15 or three_rate >= 0.10:
            quality = "PROMISING"
        else:
            quality = "WEAK"

        recommendation = "COLLECT_MORE_DATA" if total < self.MIN_SAMPLES else "KEEP_OBSERVING"
        if total >= self.MIN_SAMPLES and conflict_rate >= 0.25:
            recommendation = "REVIEW_CONFLICTS"

        return MicrostructureConfluenceSessionReport(
            samples=total,
            high_quality_samples=high,
            medium_quality_samples=medium,
            low_quality_samples=low,
            conflict_samples=conflicts,
            correlated_samples=correlated,
            one_source_samples=one,
            two_source_samples=two,
            three_source_samples=three,
            high_quality_rate=round(high_rate, 4),
            three_source_rate=round(three_rate, 4),
            conflict_rate=round(conflict_rate, 4),
            correlation_rate=round(correlation_rate, 4),
            average_confidence=round(avg_conf, 4),
            session_quality=quality,
            recommendation=recommendation,
            passive_only=True,
        )
