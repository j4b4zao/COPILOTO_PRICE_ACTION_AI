"""Qualidade informativa de barras de reversão - Brooks Trends, capítulo 5."""

from statistics import median

from enums.trend import Trend


class ReversalBarDynamics:

    DOJI_BODY_RATIO = 0.10
    PROMINENT_TAIL_RATIO = 0.25
    EXCESSIVE_TAIL_RATIO = 0.55
    SMALL_OPPOSITE_TAIL_RATIO = 0.20
    EXCESSIVE_OVERLAP_RATIO = 0.75
    LOOKBACK = 5

    @classmethod
    def analyze(cls, candles, trend=Trend.UNKNOWN):
        closed = list(candles[:-1])

        if len(closed) < 2:
            return {}

        current = closed[-1]
        previous = closed[-2]
        reference = closed[-(cls.LOOKBACK + 1):-1]

        body_ratio = cls._body_ratio(current)
        lower_tail_ratio = cls._tail_ratio(
            current.lower_wick,
            current.range,
        )
        upper_tail_ratio = cls._tail_ratio(
            current.upper_wick,
            current.range,
        )
        overlap_ratio = cls._overlap_ratio(current, previous)
        relative_range = cls._relative_range(current, reference)
        large_doji_risk = (
            body_ratio <= cls.DOJI_BODY_RATIO
            and relative_range >= 1.0
        )

        bull_score = cls._direction_score(
            direction="BULL",
            current=current,
            previous=previous,
            reference=reference,
            body_ratio=body_ratio,
            rejection_tail_ratio=lower_tail_ratio,
            opposite_tail_ratio=upper_tail_ratio,
        )
        bear_score = cls._direction_score(
            direction="BEAR",
            current=current,
            previous=previous,
            reference=reference,
            body_ratio=body_ratio,
            rejection_tail_ratio=upper_tail_ratio,
            opposite_tail_ratio=lower_tail_ratio,
        )
        direction = cls._select_direction(bull_score, bear_score)
        candidate = direction != "NONE"

        reversed_closes = cls._reversed_closes(
            current,
            reference,
            direction,
        )
        reversed_extremes = cls._reversed_extremes(
            current,
            reference,
            direction,
        )
        excessive_overlap = (
            overlap_ratio >= cls.EXCESSIVE_OVERLAP_RATIO
        )
        quality = cls._quality(
            candidate=candidate,
            direction=direction,
            current=current,
            body_ratio=body_ratio,
            rejection_tail_ratio=(
                lower_tail_ratio
                if direction == "BULL"
                else upper_tail_ratio
            ),
            opposite_tail_ratio=(
                upper_tail_ratio
                if direction == "BULL"
                else lower_tail_ratio
            ),
            reversed_closes=reversed_closes,
            excessive_overlap=excessive_overlap,
            large_doji_risk=large_doji_risk,
        )

        return {
            "brooks_reversal_candidate": candidate,
            "brooks_reversal_direction": direction,
            "brooks_reversal_quality": quality,
            "brooks_reversal_context": cls._context(
                direction,
                trend,
            ),
            "brooks_reversal_body_ratio": round(body_ratio, 4),
            "brooks_reversal_tail_ratio": round(
                lower_tail_ratio
                if direction == "BULL"
                else upper_tail_ratio,
                4,
            ),
            "brooks_reversal_opposite_tail_ratio": round(
                upper_tail_ratio
                if direction == "BULL"
                else lower_tail_ratio,
                4,
            ),
            "brooks_reversal_overlap_ratio": round(
                overlap_ratio,
                4,
            ),
            "brooks_reversal_relative_range": round(
                relative_range,
                4,
            ),
            "brooks_reversal_reversed_closes": reversed_closes,
            "brooks_reversal_reversed_extremes": reversed_extremes,
            "brooks_reversal_excessive_overlap": excessive_overlap,
            "brooks_reversal_large_doji_risk": large_doji_risk,
        }

    @classmethod
    def _direction_score(
        cls,
        *,
        direction,
        current,
        previous,
        reference,
        body_ratio,
        rejection_tail_ratio,
        opposite_tail_ratio,
    ):
        if current.range <= 0.0:
            return 0

        bullish = direction == "BULL"
        closes_past_midpoint = (
            current.close > current.midpoint
            if bullish
            else current.close < current.midpoint
        )
        body_aligned = (
            current.close > current.open
            if bullish
            else current.close < current.open
        )
        previous_opposite = (
            previous.close < previous.open
            if bullish
            else previous.close > previous.open
        )
        sweeps_extreme = cls._sweeps_extreme(
            current,
            reference,
            direction,
        )
        rejection_tail = (
            rejection_tail_ratio >= cls.PROMINENT_TAIL_RATIO
        )

        minimum_close = body_aligned or closes_past_midpoint
        reversal_evidence = (
            previous_opposite
            or sweeps_extreme
            or rejection_tail
        )

        if not minimum_close or not reversal_evidence:
            return 0

        score = 1
        score += int(body_aligned)
        score += int(closes_past_midpoint)
        score += int(previous_opposite)
        score += int(sweeps_extreme)
        score += int(rejection_tail)
        score += int(opposite_tail_ratio <= cls.SMALL_OPPOSITE_TAIL_RATIO)
        score += int(body_ratio > cls.DOJI_BODY_RATIO)
        return score

    @staticmethod
    def _select_direction(bull_score, bear_score):
        if bull_score == bear_score:
            return "NONE"
        if bull_score > bear_score:
            return "BULL"
        return "BEAR"

    @classmethod
    def _quality(
        cls,
        *,
        candidate,
        direction,
        current,
        body_ratio,
        rejection_tail_ratio,
        opposite_tail_ratio,
        reversed_closes,
        excessive_overlap,
        large_doji_risk,
    ):
        if not candidate:
            return "NONE"
        if large_doji_risk:
            return "REJECTED"

        aligned_body = (
            direction == "BULL"
            and current.close > current.open
        ) or (
            direction == "BEAR"
            and current.close < current.open
        )
        balanced_tail = (
            cls.PROMINENT_TAIL_RATIO
            <= rejection_tail_ratio
            <= cls.EXCESSIVE_TAIL_RATIO
        )
        clean_opposite_tail = (
            opposite_tail_ratio <= cls.SMALL_OPPOSITE_TAIL_RATIO
        )

        strength = sum((
            aligned_body,
            body_ratio > cls.DOJI_BODY_RATIO,
            balanced_tail,
            clean_opposite_tail,
            reversed_closes >= 2,
            not excessive_overlap,
        ))

        if strength >= 5:
            return "STRONG"
        if strength >= 3:
            return "MODERATE"
        return "WEAK"

    @staticmethod
    def _context(direction, trend):
        if direction == "NONE":
            return "NEUTRAL"
        if trend == Trend.UP:
            return (
                "WITH_TREND"
                if direction == "BULL"
                else "COUNTER_TREND"
            )
        if trend == Trend.DOWN:
            return (
                "WITH_TREND"
                if direction == "BEAR"
                else "COUNTER_TREND"
            )
        return "NEUTRAL"

    @staticmethod
    def _body_ratio(candle):
        if candle.range <= 0.0:
            return 0.0
        return candle.body / candle.range

    @staticmethod
    def _tail_ratio(tail, candle_range):
        if candle_range <= 0.0:
            return 0.0
        return max(0.0, tail) / candle_range

    @staticmethod
    def _overlap_ratio(current, previous):
        if current.range <= 0.0:
            return 0.0
        overlap = max(
            0.0,
            min(current.high, previous.high)
            - max(current.low, previous.low),
        )
        return overlap / current.range

    @staticmethod
    def _relative_range(current, reference):
        ranges = [candle.range for candle in reference if candle.range > 0.0]
        reference_range = median(ranges) if ranges else 0.0
        if reference_range <= 0.0:
            return 0.0
        return current.range / reference_range

    @staticmethod
    def _sweeps_extreme(current, reference, direction):
        if not reference:
            return False
        if direction == "BULL":
            return current.low < min(candle.low for candle in reference)
        return current.high > max(candle.high for candle in reference)

    @staticmethod
    def _reversed_closes(current, reference, direction):
        if direction == "BULL":
            return sum(current.close > candle.close for candle in reference)
        if direction == "BEAR":
            return sum(current.close < candle.close for candle in reference)
        return 0

    @staticmethod
    def _reversed_extremes(current, reference, direction):
        if direction == "BULL":
            return sum(current.high > candle.high for candle in reference)
        if direction == "BEAR":
            return sum(current.low < candle.low for candle in reference)
        return 0
