"""Relatório final observacional de uma sessão de BookDepth real."""

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class BookDepthSessionReport:
    status: str = "NO_DATA"
    action: str = "KEEP_OBSERVING"
    samples: int = 0
    valid_rate: float = 0.0
    degraded_rate: float = 0.0
    shallow_rate: float = 0.0
    average_bid_levels: float = 0.0
    average_ask_levels: float = 0.0
    average_duplicate_rate: float = 0.0
    average_availability_rate: float = 0.0
    total_anomalies: int = 0
    mature: bool = False
    passive_only: bool = True

    def to_dict(self): return asdict(self)


class BookDepthSessionReporter:
    VERSION = "RC1-BOOK-DEPTH-SESSION-REPORT"
    MIN_SAMPLES = 100

    def build(self, recorder) -> BookDepthSessionReport:
        s = recorder.summary(); n = int(s.get("samples", 0))
        if n == 0: return BookDepthSessionReport()
        valid = float(s.get("valid_rate", 0.0)); degraded = float(s.get("degraded_rate", 0.0)); shallow = float(s.get("shallow_rate", 0.0))
        duplicate = float(s.get("average_duplicate_rate", 0.0)); availability = float(s.get("average_availability_rate", 0.0)); anomalies = int(s.get("total_anomalies", 0))
        mature = n >= self.MIN_SAMPLES
        if not mature:
            status, action = "INSUFFICIENT_DATA", "KEEP_OBSERVING"
        elif degraded >= 0.20 or availability < 0.80:
            status, action = "DEGRADED_SESSION", "REVIEW_SOURCE"
        elif duplicate >= 0.80:
            status, action = "UNSTABLE_SOURCE", "REVIEW_SOURCE"
        elif valid >= 0.80 and degraded <= 0.05 and shallow <= 0.10:
            status, action = "STRONG_VALID_SESSION", "KEEP_OBSERVING"
        elif valid >= 0.60 and degraded <= 0.15:
            status, action = "PROMISING_VALID_SESSION", "KEEP_OBSERVING"
        else:
            status, action = "WEAK_VALID_SESSION", "KEEP_OBSERVING"
        return BookDepthSessionReport(status=status, action=action, samples=n, valid_rate=valid,
            degraded_rate=degraded, shallow_rate=shallow,
            average_bid_levels=float(s.get("average_bid_levels", 0.0)), average_ask_levels=float(s.get("average_ask_levels", 0.0)),
            average_duplicate_rate=duplicate, average_availability_rate=availability,
            total_anomalies=anomalies, mature=mature, passive_only=True)
