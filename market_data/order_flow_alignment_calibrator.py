"""Calibração observacional de thresholds do Order Flow consolidado (RC31)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math


@dataclass(slots=True, frozen=True)
class OrderFlowCalibrationReport:
    sample_count: int
    dominance_p50: float
    dominance_p75: float
    dominance_p90: float
    imbalance_p50: float
    imbalance_p75: float
    imbalance_p90: float
    suggested_delta_threshold: float
    suggested_book_threshold: float
    candidate_aligned_count: int
    candidate_divergent_count: int
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class OrderFlowAlignmentCalibrator:
    """Resume a distribuição real sem alterar thresholds operacionais."""

    VERSION = "RC31-ORDER-FLOW-ALIGNMENT-CALIBRATION"
    MIN_SAMPLES = 30

    @staticmethod
    def _percentile(values: list[float], q: float) -> float:
        if not values:
            return 0.0
        values = sorted(values)
        pos = (len(values) - 1) * q
        lo = math.floor(pos)
        hi = math.ceil(pos)
        if lo == hi:
            return values[lo]
        return values[lo] * (hi - pos) + values[hi] * (pos - lo)

    def evaluate(self, samples) -> OrderFlowCalibrationReport:
        dominance = []
        imbalance = []
        signed = []
        for sample in samples or ():
            d = float(sample.get("dominance", 0.0) or 0.0)
            b = float(sample.get("imbalance", 0.0) or 0.0)
            if math.isfinite(d) and math.isfinite(b):
                dominance.append(abs(d))
                imbalance.append(abs(b))
                signed.append((d, b))

        n = len(signed)
        if n < self.MIN_SAMPLES:
            raise ValueError(f"São necessárias ao menos {self.MIN_SAMPLES} amostras válidas.")

        d50 = self._percentile(dominance, 0.50)
        d75 = self._percentile(dominance, 0.75)
        d90 = self._percentile(dominance, 0.90)
        b50 = self._percentile(imbalance, 0.50)
        b75 = self._percentile(imbalance, 0.75)
        b90 = self._percentile(imbalance, 0.90)

        delta_threshold = max(0.05, min(0.35, d75))
        book_threshold = max(0.02, min(0.10, b75))

        aligned = 0
        divergent = 0
        for d, b in signed:
            ds = 1 if d >= delta_threshold else (-1 if d <= -delta_threshold else 0)
            bs = 1 if b >= book_threshold else (-1 if b <= -book_threshold else 0)
            if ds and bs:
                if ds == bs:
                    aligned += 1
                else:
                    divergent += 1

        return OrderFlowCalibrationReport(
            sample_count=n,
            dominance_p50=round(d50, 4),
            dominance_p75=round(d75, 4),
            dominance_p90=round(d90, 4),
            imbalance_p50=round(b50, 6),
            imbalance_p75=round(b75, 6),
            imbalance_p90=round(b90, 6),
            suggested_delta_threshold=round(delta_threshold, 4),
            suggested_book_threshold=round(book_threshold, 6),
            candidate_aligned_count=aligned,
            candidate_divergent_count=divergent,
        )
