"""Métricas offline do experimento Order Flow -> Score RC4.8."""

import math

from ai.score_engine import ScoreEngine


class OrderFlowExperimentMetrics:

    VERSION = "RC4.8"

    def __init__(self, score_threshold=None):
        threshold = (
            ScoreEngine.MIN_SCORE
            if score_threshold is None
            else score_threshold
        )

        try:
            self.score_threshold = float(threshold)
        except (TypeError, ValueError):
            raise ValueError(
                "Limite de score deve ser numérico."
            ) from None

        if (
            not math.isfinite(self.score_threshold)
            or not 0.0 <= self.score_threshold <= ScoreEngine.MAX_SCORE
        ):
            raise ValueError(
                "Limite de score deve ficar entre 0 e 100."
            )

        self.clear()

    def clear(self):
        self.observations = 0
        self.patterns_confirmed = 0
        self.contributions_applied = 0
        self.score_promotions = 0
        self.total_contribution = 0.0
        self.max_contribution = 0.0
        self.by_direction = {
            "BUY": 0,
            "SELL": 0,
            "OTHER": 0,
        }
        self.by_sampling_mode = {
            "TICK": 0,
            "RENKO_CLOSE": 0,
            "OTHER": 0,
        }

    def register(self, context):
        self.observations += 1

        order_flow = context.order_flow
        score = context.score

        if order_flow.pattern_confirmed:
            self.patterns_confirmed += 1

        if not score.order_flow_applied:
            return

        contribution = self._contribution(
            score.order_flow_contribution
        )

        if contribution <= 0.0:
            return

        self.contributions_applied += 1
        self.total_contribution += contribution
        self.max_contribution = max(
            self.max_contribution,
            contribution,
        )

        direction = str(
            score.order_flow_direction
        ).upper()
        direction_key = (
            direction
            if direction in ("BUY", "SELL")
            else "OTHER"
        )
        self.by_direction[direction_key] += 1

        sampling_mode = str(
            order_flow.sampling_mode
        ).upper()
        sampling_key = (
            sampling_mode
            if sampling_mode in ("TICK", "RENKO_CLOSE")
            else "OTHER"
        )
        self.by_sampling_mode[sampling_key] += 1

        baseline_total = max(
            0.0,
            float(score.total) - contribution,
        )

        if (
            baseline_total < self.score_threshold
            <= float(score.total)
        ):
            self.score_promotions += 1

    def snapshot(self):
        average = 0.0

        if self.contributions_applied:
            average = (
                self.total_contribution
                / self.contributions_applied
            )

        return {
            "score_threshold": self.score_threshold,
            "observations": self.observations,
            "patterns_confirmed": self.patterns_confirmed,
            "contributions_applied": self.contributions_applied,
            "application_rate": self._rate(
                self.contributions_applied,
                self.observations,
            ),
            "score_promotions": self.score_promotions,
            "promotion_rate": self._rate(
                self.score_promotions,
                self.contributions_applied,
            ),
            "total_contribution": round(
                self.total_contribution,
                2,
            ),
            "average_contribution": round(average, 2),
            "max_contribution": round(
                self.max_contribution,
                2,
            ),
            "by_direction": dict(self.by_direction),
            "by_sampling_mode": dict(self.by_sampling_mode),
        }

    @staticmethod
    def _contribution(value):
        try:
            contribution = float(value)
        except (TypeError, ValueError):
            return 0.0

        if not math.isfinite(contribution):
            return 0.0

        return max(0.0, contribution)

    @staticmethod
    def _rate(numerator, denominator):
        if not denominator:
            return 0.0

        return round(
            (numerator / denominator) * 100.0,
            2,
        )
