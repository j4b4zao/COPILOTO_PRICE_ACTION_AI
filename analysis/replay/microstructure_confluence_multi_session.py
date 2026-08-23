"""Comparador passivo de múltiplas sessões da confluência de microestrutura."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class MicrostructureConfluenceMultiSessionReport:
    sessions: int = 0
    samples: int = 0
    weighted_high_quality_rate: float = 0.0
    weighted_three_source_rate: float = 0.0
    weighted_conflict_rate: float = 0.0
    weighted_correlation_rate: float = 0.0
    weighted_average_confidence: float = 0.0
    min_high_quality_rate: float = 0.0
    max_high_quality_rate: float = 0.0
    high_quality_spread: float = 0.0
    strong_sessions: int = 0
    promising_sessions: int = 0
    weak_sessions: int = 0
    degraded_sessions: int = 0
    no_data_sessions: int = 0
    stability: str = "INSUFFICIENT_DATA"
    recommendation: str = "COLLECT_MORE_DATA"
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class MicrostructureConfluenceMultiSessionComparator:
    VERSION = "RC1-MICROSTRUCTURE-CONFLUENCE-MULTI-SESSION"
    MIN_SESSIONS = 3
    MIN_SAMPLES = 300
    MAX_HIGH_RATE_SPREAD = 0.25
    MAX_WEIGHTED_CONFLICT_RATE = 0.20

    def compare(self, reports) -> MicrostructureConfluenceMultiSessionReport:
        reports = list(reports)
        self._validate(reports)

        sessions = len(reports)
        samples = sum(int(r.samples) for r in reports)
        usable = [r for r in reports if int(r.samples) > 0]

        weighted_high = self._weighted(usable, "high_quality_rate", samples)
        weighted_three = self._weighted(usable, "three_source_rate", samples)
        weighted_conflict = self._weighted(usable, "conflict_rate", samples)
        weighted_correlation = self._weighted(usable, "correlation_rate", samples)
        weighted_confidence = self._weighted(usable, "average_confidence", samples)

        high_rates = [float(r.high_quality_rate) for r in usable]
        min_high = min(high_rates) if high_rates else 0.0
        max_high = max(high_rates) if high_rates else 0.0
        spread = max_high - min_high if high_rates else 0.0

        qualities = [str(r.session_quality).upper() for r in reports]
        stability = self._stability(
            sessions=sessions,
            samples=samples,
            qualities=qualities,
            high_spread=spread,
            weighted_conflict=weighted_conflict,
        )
        recommendation = self._recommendation(
            sessions=sessions,
            samples=samples,
            stability=stability,
            weighted_conflict=weighted_conflict,
        )

        return MicrostructureConfluenceMultiSessionReport(
            sessions=sessions,
            samples=samples,
            weighted_high_quality_rate=round(weighted_high, 4),
            weighted_three_source_rate=round(weighted_three, 4),
            weighted_conflict_rate=round(weighted_conflict, 4),
            weighted_correlation_rate=round(weighted_correlation, 4),
            weighted_average_confidence=round(weighted_confidence, 4),
            min_high_quality_rate=round(min_high, 4),
            max_high_quality_rate=round(max_high, 4),
            high_quality_spread=round(spread, 4),
            strong_sessions=qualities.count("STRONG_INDEPENDENT_CONFLUENCE"),
            promising_sessions=qualities.count("PROMISING"),
            weak_sessions=qualities.count("WEAK"),
            degraded_sessions=qualities.count("DEGRADED_BY_CONFLICT"),
            no_data_sessions=qualities.count("NO_DATA"),
            stability=stability,
            recommendation=recommendation,
            passive_only=True,
        )

    @staticmethod
    def _weighted(reports, field: str, total_samples: int) -> float:
        if total_samples <= 0:
            return 0.0
        return sum(float(getattr(r, field)) * int(r.samples) for r in reports) / total_samples

    def _stability(self, *, sessions, samples, qualities, high_spread, weighted_conflict):
        if sessions < self.MIN_SESSIONS or samples < self.MIN_SAMPLES:
            return "INSUFFICIENT_DATA"
        if weighted_conflict >= self.MAX_WEIGHTED_CONFLICT_RATE:
            return "DEGRADED_BY_CONFLICT"
        if high_spread > self.MAX_HIGH_RATE_SPREAD:
            return "INCONSISTENT"

        meaningful = [q for q in qualities if q != "NO_DATA"]
        if not meaningful:
            return "INSUFFICIENT_DATA"
        if all(q == "STRONG_INDEPENDENT_CONFLUENCE" for q in meaningful):
            return "STABLE_STRONG"
        if all(q in {"STRONG_INDEPENDENT_CONFLUENCE", "PROMISING"} for q in meaningful):
            return "STABLE_PROMISING"
        if all(q == "WEAK" for q in meaningful):
            return "STABLE_WEAK"
        return "INCONSISTENT"

    def _recommendation(self, *, sessions, samples, stability, weighted_conflict):
        if sessions < self.MIN_SESSIONS or samples < self.MIN_SAMPLES:
            return "COLLECT_MORE_DATA"
        if weighted_conflict >= self.MAX_WEIGHTED_CONFLICT_RATE:
            return "REVIEW_CONFLICTS"
        if stability == "INCONSISTENT":
            return "REVIEW_STABILITY"
        return "KEEP_OBSERVING"

    @staticmethod
    def _validate(reports):
        required = (
            "samples",
            "high_quality_rate",
            "three_source_rate",
            "conflict_rate",
            "correlation_rate",
            "average_confidence",
            "session_quality",
        )
        for report in reports:
            if not all(hasattr(report, field) for field in required):
                raise TypeError("Relatório de sessão de microestrutura inválido.")
