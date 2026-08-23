"""Comparador observacional multi-pregao para sessoes de BookDepth real."""

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class BookDepthMultiSessionReport:
    status: str = "INSUFFICIENT_DATA"
    recommendation: str = "COLLECT_MORE_DATA"
    sessions: int = 0
    samples: int = 0
    weighted_valid_rate: float = 0.0
    weighted_degraded_rate: float = 0.0
    weighted_shallow_rate: float = 0.0
    weighted_bid_levels: float = 0.0
    weighted_ask_levels: float = 0.0
    weighted_duplicate_rate: float = 0.0
    weighted_availability_rate: float = 0.0
    valid_rate_spread: float = 0.0
    duplicate_rate_spread: float = 0.0
    availability_rate_spread: float = 0.0
    total_anomalies: int = 0
    passive_only: bool = True

    def to_dict(self): return asdict(self)


class BookDepthMultiSessionComparator:
    VERSION = "RC1-BOOK-DEPTH-MULTISESSION"
    MIN_SESSIONS = 3
    MIN_SAMPLES = 300
    MAX_VALID_SPREAD = 0.25
    MAX_DUPLICATE_SPREAD = 0.35
    MAX_AVAILABILITY_SPREAD = 0.20

    def compare(self, reports):
        reports = [r for r in reports if int(getattr(r, "samples", 0) or 0) > 0]
        sessions = len(reports)
        samples = sum(int(r.samples) for r in reports)
        if sessions < self.MIN_SESSIONS or samples < self.MIN_SAMPLES:
            return BookDepthMultiSessionReport(sessions=sessions, samples=samples)

        weighted = lambda field: sum(float(getattr(r, field, 0.0)) * int(r.samples) for r in reports) / samples
        valid = weighted("valid_rate"); degraded = weighted("degraded_rate"); shallow = weighted("shallow_rate")
        bid_levels = weighted("average_bid_levels"); ask_levels = weighted("average_ask_levels")
        duplicate = weighted("average_duplicate_rate"); availability = weighted("average_availability_rate")
        valid_spread = self._spread(reports, "valid_rate")
        duplicate_spread = self._spread(reports, "average_duplicate_rate")
        availability_spread = self._spread(reports, "average_availability_rate")
        anomalies = sum(int(getattr(r, "total_anomalies", 0) or 0) for r in reports)
        bad_session = any(str(getattr(r, "status", "")) in {"DEGRADED_SESSION", "UNSTABLE_SOURCE"} for r in reports)

        if bad_session:
            status, recommendation = "SOURCE_REVIEW_REQUIRED", "REVIEW_SOURCE"
        elif degraded >= 0.20 or availability < 0.80:
            status, recommendation = "DEGRADED_MULTI_SESSION", "REVIEW_SOURCE"
        elif valid_spread > self.MAX_VALID_SPREAD or duplicate_spread > self.MAX_DUPLICATE_SPREAD or availability_spread > self.MAX_AVAILABILITY_SPREAD:
            status, recommendation = "INCONSISTENT", "KEEP_OBSERVING"
        elif valid >= 0.80 and degraded <= 0.05 and shallow <= 0.10 and duplicate < 0.50 and availability >= 0.90:
            status, recommendation = "STABLE_STRONG", "KEEP_OBSERVING"
        elif valid >= 0.60 and degraded <= 0.15 and availability >= 0.80:
            status, recommendation = "STABLE_PROMISING", "KEEP_OBSERVING"
        else:
            status, recommendation = "STABLE_WEAK", "KEEP_OBSERVING"

        return BookDepthMultiSessionReport(
            status=status, recommendation=recommendation, sessions=sessions, samples=samples,
            weighted_valid_rate=round(valid, 4), weighted_degraded_rate=round(degraded, 4),
            weighted_shallow_rate=round(shallow, 4), weighted_bid_levels=round(bid_levels, 4),
            weighted_ask_levels=round(ask_levels, 4), weighted_duplicate_rate=round(duplicate, 4),
            weighted_availability_rate=round(availability, 4), valid_rate_spread=round(valid_spread, 4),
            duplicate_rate_spread=round(duplicate_spread, 4), availability_rate_spread=round(availability_spread, 4),
            total_anomalies=anomalies, passive_only=True)

    @staticmethod
    def _spread(reports, field):
        values = [float(getattr(r, field, 0.0) or 0.0) for r in reports]
        return max(values) - min(values) if values else 0.0
