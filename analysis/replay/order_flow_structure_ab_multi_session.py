"""Comparador passivo multi-sessão do A/B estrutural de Order Flow."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class OrderFlowStructureABMultiSessionReport:
    sessions: int = 0
    samples: int = 0
    weighted_average_delta: float = 0.0
    weighted_average_confidence: float = 0.0
    min_session_delta: float = 0.0
    max_session_delta: float = 0.0
    delta_spread: float = 0.0
    positive_sessions: int = 0
    negative_sessions: int = 0
    neutral_sessions: int = 0
    mixed_sessions: int = 0
    no_data_sessions: int = 0
    sessions_with_grade_changes: int = 0
    sessions_with_validity_changes: int = 0
    stability: str = "INSUFFICIENT_DATA"
    recommendation: str = "COLLECT_MORE_DATA"
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class OrderFlowStructureABMultiSessionComparator:
    VERSION = "RC1-ORDER-FLOW-STRUCTURE-AB-MULTI-SESSION"
    MIN_SESSIONS = 3
    MIN_SAMPLES = 300
    MAX_STABLE_SPREAD = 0.75

    def compare(self, reports) -> OrderFlowStructureABMultiSessionReport:
        reports = list(reports)
        self._validate(reports)

        sessions = len(reports)
        samples = sum(int(r.samples) for r in reports)
        deltas = [float(r.average_delta) for r in reports if int(r.samples) > 0]

        weighted_delta = (
            sum(float(r.average_delta) * int(r.samples) for r in reports) / samples
            if samples else 0.0
        )
        weighted_confidence = (
            sum(float(r.average_confidence) * int(r.samples) for r in reports) / samples
            if samples else 0.0
        )

        min_delta = min(deltas) if deltas else 0.0
        max_delta = max(deltas) if deltas else 0.0
        spread = max_delta - min_delta if deltas else 0.0

        effects = [str(r.dominant_effect).upper() for r in reports]
        grade_sessions = sum(int(r.grade_changes) > 0 for r in reports)
        validity_sessions = sum(int(r.validity_changes) > 0 for r in reports)

        stability = self._stability(
            sessions=sessions,
            samples=samples,
            effects=effects,
            spread=spread,
            validity_sessions=validity_sessions,
        )
        recommendation = self._recommendation(
            sessions=sessions,
            samples=samples,
            grade_sessions=grade_sessions,
            validity_sessions=validity_sessions,
            stability=stability,
        )

        return OrderFlowStructureABMultiSessionReport(
            sessions=sessions,
            samples=samples,
            weighted_average_delta=round(weighted_delta, 4),
            weighted_average_confidence=round(weighted_confidence, 4),
            min_session_delta=round(min_delta, 4),
            max_session_delta=round(max_delta, 4),
            delta_spread=round(spread, 4),
            positive_sessions=effects.count("POSITIVE"),
            negative_sessions=effects.count("NEGATIVE"),
            neutral_sessions=effects.count("NEUTRAL"),
            mixed_sessions=effects.count("MIXED"),
            no_data_sessions=effects.count("NO_DATA"),
            sessions_with_grade_changes=grade_sessions,
            sessions_with_validity_changes=validity_sessions,
            stability=stability,
            recommendation=recommendation,
            passive_only=True,
        )

    def _stability(self, *, sessions, samples, effects, spread, validity_sessions):
        if sessions < self.MIN_SESSIONS or samples < self.MIN_SAMPLES:
            return "INSUFFICIENT_DATA"
        if validity_sessions or spread > self.MAX_STABLE_SPREAD:
            return "INCONSISTENT"

        meaningful = [effect for effect in effects if effect != "NO_DATA"]
        if not meaningful:
            return "INSUFFICIENT_DATA"

        unique = set(meaningful)
        if unique == {"POSITIVE"}:
            return "STABLE_POSITIVE"
        if unique == {"NEGATIVE"}:
            return "STABLE_NEGATIVE"
        if unique == {"NEUTRAL"}:
            return "STABLE_NEUTRAL"
        return "INCONSISTENT"

    def _recommendation(self, *, sessions, samples, grade_sessions, validity_sessions, stability):
        if sessions < self.MIN_SESSIONS or samples < self.MIN_SAMPLES:
            return "COLLECT_MORE_DATA"
        if grade_sessions or validity_sessions or stability == "INCONSISTENT":
            return "REVIEW_BEFORE_ENABLE"
        return "KEEP_OBSERVING"

    @staticmethod
    def _validate(reports):
        required = (
            "samples",
            "average_delta",
            "average_confidence",
            "dominant_effect",
            "grade_changes",
            "validity_changes",
        )
        for report in reports:
            if not all(hasattr(report, field) for field in required):
                raise TypeError(
                    "Relatório de sessão A/B estrutural de Order Flow inválido."
                )
