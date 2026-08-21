"""Força de tendência inspirada em Brooks Trends, capítulo 19.

A camada transforma características recorrentes de tendências fortes em
métricas objetivas. Ela usa somente candles fechados e não autoriza ordens.
"""

from enums.trend import Trend


class TrendStrengthDynamics:

    LOOKBACK = 12
    MIN_BARS = 6

    @classmethod
    def analyze(cls, candles, trend, result=None):
        closed = list(candles[:-1])

        if trend not in (Trend.UP, Trend.DOWN):
            return cls._empty("NO_TREND")

        if len(closed) < cls.MIN_BARS:
            return cls._empty("INSUFFICIENT_DATA")

        window = closed[-cls.LOOKBACK:]
        bullish = trend == Trend.UP
        direction = "BUY" if bullish else "SELL"

        aligned_bars = [
            candle for candle in window
            if (candle.close > candle.open) == bullish
            and candle.close != candle.open
        ]
        aligned_ratio = len(aligned_bars) / len(window)

        trend_bars = [
            candle for candle in aligned_bars
            if cls._body_ratio(candle) >= 0.55
        ]
        trend_bar_ratio = len(trend_bars) / len(window)

        overlap_ratio = cls._body_overlap_ratio(window)
        counter_streak = cls._longest_counter_streak(window, bullish)
        pullback_ratio = cls._counter_bar_ratio(window, bullish)
        close_extreme_ratio = cls._close_extreme_ratio(window, bullish)
        efficiency = cls._directional_efficiency(window, bullish)
        micro_gap_count = cls._micro_gap_count(window, bullish)
        no_pullback_streak = cls._latest_aligned_streak(window, bullish)
        counter_follow_through = counter_streak >= 2
        climax_risk = bool(
            getattr(result, "climax_active", False)
            if result is not None else False
        )

        urgency = bool(
            no_pullback_streak >= 5
            or (
                aligned_ratio >= 0.70
                and counter_streak <= 1
                and overlap_ratio <= 0.45
            )
        )

        score = cls._score(
            aligned_ratio=aligned_ratio,
            trend_bar_ratio=trend_bar_ratio,
            overlap_ratio=overlap_ratio,
            pullback_ratio=pullback_ratio,
            counter_streak=counter_streak,
            close_extreme_ratio=close_extreme_ratio,
            efficiency=efficiency,
            micro_gap_count=micro_gap_count,
            urgency=urgency,
            counter_follow_through=counter_follow_through,
            climax_risk=climax_risk,
        )
        classification = cls._classification(score)

        return {
            "brooks_trend_strength_state": classification,
            "brooks_trend_strength_direction": direction,
            "brooks_trend_strength_score": round(score, 2),
            "brooks_trend_strength_aligned_ratio": round(aligned_ratio, 4),
            "brooks_trend_strength_trend_bar_ratio": round(trend_bar_ratio, 4),
            "brooks_trend_strength_overlap_ratio": round(overlap_ratio, 4),
            "brooks_trend_strength_pullback_ratio": round(pullback_ratio, 4),
            "brooks_trend_strength_counter_streak": counter_streak,
            "brooks_trend_strength_close_extreme_ratio": round(close_extreme_ratio, 4),
            "brooks_trend_strength_efficiency": round(efficiency, 4),
            "brooks_trend_strength_micro_gap_count": micro_gap_count,
            "brooks_trend_strength_no_pullback_streak": no_pullback_streak,
            "brooks_trend_strength_urgency": urgency,
            "brooks_trend_strength_counter_follow_through": counter_follow_through,
            "brooks_trend_strength_climax_risk": climax_risk,
            "brooks_trend_strength_with_trend_only": classification in (
                "STRONG",
                "VERY_STRONG",
            ),
            "brooks_trend_strength_valid": True,
        }

    @staticmethod
    def _body_ratio(candle):
        if candle.range <= 0.0:
            return 0.0
        return candle.body / candle.range

    @staticmethod
    def _body_overlap_ratio(candles):
        if len(candles) < 2:
            return 0.0

        overlaps = 0
        pairs = 0

        for previous, current in zip(candles, candles[1:]):
            previous_low = min(previous.open, previous.close)
            previous_high = max(previous.open, previous.close)
            current_low = min(current.open, current.close)
            current_high = max(current.open, current.close)

            intersection = min(previous_high, current_high) - max(
                previous_low,
                current_low,
            )
            if intersection > 0.0:
                overlaps += 1
            pairs += 1

        return overlaps / pairs if pairs else 0.0

    @staticmethod
    def _counter_bar_ratio(candles, bullish):
        counter = 0
        for candle in candles:
            if candle.close == candle.open:
                continue
            aligned = (candle.close > candle.open) == bullish
            if not aligned:
                counter += 1
        return counter / len(candles)

    @staticmethod
    def _longest_counter_streak(candles, bullish):
        longest = 0
        current = 0

        for candle in candles:
            if candle.close == candle.open:
                current = 0
                continue

            aligned = (candle.close > candle.open) == bullish
            if aligned:
                current = 0
            else:
                current += 1
                longest = max(longest, current)

        return longest

    @staticmethod
    def _latest_aligned_streak(candles, bullish):
        streak = 0
        for candle in reversed(candles):
            if candle.close == candle.open:
                break
            aligned = (candle.close > candle.open) == bullish
            if not aligned:
                break
            streak += 1
        return streak

    @staticmethod
    def _close_extreme_ratio(candles, bullish):
        aligned = []
        for candle in candles:
            if candle.range <= 0.0:
                continue
            same_direction = (candle.close > candle.open) == bullish
            if not same_direction or candle.close == candle.open:
                continue
            position = (candle.close - candle.low) / candle.range
            near_extreme = position >= 0.75 if bullish else position <= 0.25
            aligned.append(near_extreme)

        if not aligned:
            return 0.0
        return sum(aligned) / len(aligned)

    @staticmethod
    def _directional_efficiency(candles, bullish):
        if len(candles) < 2:
            return 0.0

        net = candles[-1].close - candles[0].open
        if not bullish:
            net = -net

        travelled = sum(abs(candle.close - candle.open) for candle in candles)
        if travelled <= 0.0:
            return 0.0

        return max(0.0, min(1.0, net / travelled))

    @staticmethod
    def _micro_gap_count(candles, bullish):
        count = 0
        for index in range(1, len(candles) - 1):
            before = candles[index - 1]
            after = candles[index + 1]
            if bullish:
                if after.low >= before.high:
                    count += 1
            else:
                if after.high <= before.low:
                    count += 1
        return count

    @staticmethod
    def _score(
        aligned_ratio,
        trend_bar_ratio,
        overlap_ratio,
        pullback_ratio,
        counter_streak,
        close_extreme_ratio,
        efficiency,
        micro_gap_count,
        urgency,
        counter_follow_through,
        climax_risk,
    ):
        score = 0.0
        score += aligned_ratio * 25.0
        score += min(1.0, trend_bar_ratio / 0.60) * 20.0
        score += (1.0 - overlap_ratio) * 15.0
        score += (1.0 - min(1.0, pullback_ratio / 0.45)) * 10.0
        score += max(0.0, 1.0 - (counter_streak / 3.0)) * 5.0
        score += close_extreme_ratio * 10.0
        score += efficiency * 10.0
        score += min(1.0, micro_gap_count / 2.0) * 3.0
        score += 2.0 if urgency else 0.0

        if counter_follow_through:
            score -= 10.0
        if climax_risk:
            score -= 8.0

        return max(0.0, min(100.0, score))

    @staticmethod
    def _classification(score):
        if score >= 85.0:
            return "VERY_STRONG"
        if score >= 70.0:
            return "STRONG"
        if score >= 50.0:
            return "MODERATE"
        return "WEAK"

    @staticmethod
    def _empty(state):
        return {
            "brooks_trend_strength_state": state,
            "brooks_trend_strength_direction": "NONE",
            "brooks_trend_strength_score": 0.0,
            "brooks_trend_strength_aligned_ratio": 0.0,
            "brooks_trend_strength_trend_bar_ratio": 0.0,
            "brooks_trend_strength_overlap_ratio": 0.0,
            "brooks_trend_strength_pullback_ratio": 0.0,
            "brooks_trend_strength_counter_streak": 0,
            "brooks_trend_strength_close_extreme_ratio": 0.0,
            "brooks_trend_strength_efficiency": 0.0,
            "brooks_trend_strength_micro_gap_count": 0,
            "brooks_trend_strength_no_pullback_streak": 0,
            "brooks_trend_strength_urgency": False,
            "brooks_trend_strength_counter_follow_through": False,
            "brooks_trend_strength_climax_risk": False,
            "brooks_trend_strength_with_trend_only": False,
            "brooks_trend_strength_valid": False,
        }
