"""Trend-from-open e small-pullback trends inspirados em Brooks Trends, cap. 23.

Camada puramente diagnóstica. O candle atual e sempre excluido da confirmacao.
Nao altera Score, Risk, Decision nem autoriza ordens.
"""

from statistics import median

from enums.trend import Trend


class TrendFromOpenDynamics:

    LOOKBACK = 24
    OPENING_BARS = 8
    MIN_BARS = 6
    SMALL_PULLBACK_RANGE_RATIO = 1.25
    MAX_COUNTER_SEQUENCE = 2

    @classmethod
    def analyze(cls, candles, trend):
        closed = list(candles[:-1])
        if len(closed) < cls.MIN_BARS:
            return cls._empty()

        if trend not in (Trend.UP, Trend.DOWN):
            return cls._empty(state="NO_DIRECTIONAL_TREND")

        window = closed[-cls.LOOKBACK:]
        direction = "BUY" if trend == Trend.UP else "SELL"
        opening = window[: min(cls.OPENING_BARS, len(window))]

        open_price = float(window[0].open)
        last_close = float(window[-1].close)
        typical_range = cls._typical_range(window)
        total_move = cls._directional_move(open_price, last_close, trend)
        total_range = max(c.high for c in window) - min(c.low for c in window)
        efficiency = total_move / total_range if total_range > 0 else 0.0

        aligned_ratio = cls._aligned_ratio(window, trend)
        opening_aligned_ratio = cls._aligned_ratio(opening, trend)
        close_progress = cls._close_progress(window, trend)
        overlap = cls._average_overlap(window)
        counter_sequence = cls._max_counter_sequence(window, trend)
        pullbacks = cls._pullbacks(window, trend)
        max_pullback = max((item["depth"] for item in pullbacks), default=0.0)
        max_pullback_bars = max((item["bars"] for item in pullbacks), default=0)
        pullback_ratio = max_pullback / typical_range if typical_range > 0 else 0.0

        opening_displacement = cls._opening_displacement(opening, trend)
        opening_displacement_ratio = (
            opening_displacement / typical_range if typical_range > 0 else 0.0
        )

        holds_open = cls._holds_open(window, open_price, trend)
        no_deep_pullback = bool(
            pullback_ratio <= cls.SMALL_PULLBACK_RANGE_RATIO
            and counter_sequence <= cls.MAX_COUNTER_SEQUENCE
        )
        persistent = bool(
            aligned_ratio >= 0.62
            and close_progress >= 0.60
            and efficiency >= 0.45
        )

        trend_from_open = bool(
            opening_aligned_ratio >= 0.625
            and opening_displacement_ratio >= 1.5
            and holds_open
            and persistent
        )

        small_pullback_trend = bool(
            persistent
            and no_deep_pullback
            and overlap <= 0.65
            and len(pullbacks) <= max(4, len(window) // 3)
        )

        if trend_from_open and small_pullback_trend:
            state = "TREND_FROM_OPEN_SMALL_PULLBACK"
        elif trend_from_open:
            state = "TREND_FROM_OPEN"
        elif small_pullback_trend:
            state = "SMALL_PULLBACK_TREND"
        else:
            state = "NORMAL_TREND"

        strength = cls._strength_score(
            opening_aligned_ratio=opening_aligned_ratio,
            aligned_ratio=aligned_ratio,
            close_progress=close_progress,
            efficiency=efficiency,
            overlap=overlap,
            pullback_ratio=pullback_ratio,
            counter_sequence=counter_sequence,
            opening_displacement_ratio=opening_displacement_ratio,
            holds_open=holds_open,
        )

        wait_for_deep_pullback_risk = bool(
            small_pullback_trend
            and strength >= 70
            and max_pullback_bars <= 2
        )

        if strength >= 85:
            quality = "VERY_STRONG"
        elif strength >= 70:
            quality = "STRONG"
        elif strength >= 50:
            quality = "MODERATE"
        else:
            quality = "WEAK"

        return {
            "brooks_open_trend_state": state,
            "brooks_open_trend_direction": direction,
            "brooks_open_trend_quality": quality,
            "brooks_open_trend_score": strength,
            "brooks_open_trend_open_price": round(open_price, 4),
            "brooks_open_trend_last_close": round(last_close, 4),
            "brooks_open_trend_total_move": round(total_move, 4),
            "brooks_open_trend_efficiency": round(efficiency, 4),
            "brooks_open_trend_aligned_ratio": round(aligned_ratio, 4),
            "brooks_open_trend_opening_aligned_ratio": round(opening_aligned_ratio, 4),
            "brooks_open_trend_close_progress": round(close_progress, 4),
            "brooks_open_trend_overlap": round(overlap, 4),
            "brooks_open_trend_opening_displacement": round(opening_displacement, 4),
            "brooks_open_trend_opening_displacement_ratio": round(opening_displacement_ratio, 4),
            "brooks_open_trend_pullback_count": len(pullbacks),
            "brooks_open_trend_max_pullback": round(max_pullback, 4),
            "brooks_open_trend_max_pullback_ratio": round(pullback_ratio, 4),
            "brooks_open_trend_max_pullback_bars": max_pullback_bars,
            "brooks_open_trend_counter_sequence": counter_sequence,
            "brooks_open_trend_holds_open": holds_open,
            "brooks_open_trend_persistent": persistent,
            "brooks_open_trend_from_open": trend_from_open,
            "brooks_open_trend_small_pullback": small_pullback_trend,
            "brooks_open_trend_wait_deep_pullback_risk": wait_for_deep_pullback_risk,
            "brooks_open_trend_with_trend_only": strength >= 70,
            "brooks_open_trend_valid": True,
        }

    @staticmethod
    def _directional_move(open_price, close_price, trend):
        if trend == Trend.UP:
            return max(0.0, close_price - open_price)
        return max(0.0, open_price - close_price)

    @staticmethod
    def _aligned(candle, trend):
        if trend == Trend.UP:
            return candle.close > candle.open
        return candle.close < candle.open

    @classmethod
    def _aligned_ratio(cls, candles, trend):
        if not candles:
            return 0.0
        aligned = sum(1 for candle in candles if cls._aligned(candle, trend))
        return aligned / len(candles)

    @staticmethod
    def _close_progress(candles, trend):
        if len(candles) < 2:
            return 0.0
        progress = 0
        for previous, current in zip(candles, candles[1:]):
            if trend == Trend.UP and current.close >= previous.close:
                progress += 1
            elif trend == Trend.DOWN and current.close <= previous.close:
                progress += 1
        return progress / (len(candles) - 1)

    @staticmethod
    def _bar_overlap(left, right):
        overlap = min(left.high, right.high) - max(left.low, right.low)
        if overlap <= 0:
            return 0.0
        base = min(left.range, right.range)
        return overlap / base if base > 0 else 0.0

    @classmethod
    def _average_overlap(cls, candles):
        if len(candles) < 2:
            return 0.0
        values = [
            cls._bar_overlap(left, right)
            for left, right in zip(candles, candles[1:])
        ]
        return sum(values) / len(values)

    @classmethod
    def _max_counter_sequence(cls, candles, trend):
        current = 0
        maximum = 0
        for candle in candles:
            counter = (
                candle.close < candle.open
                if trend == Trend.UP
                else candle.close > candle.open
            )
            if counter:
                current += 1
                maximum = max(maximum, current)
            else:
                current = 0
        return maximum

    @staticmethod
    def _opening_displacement(candles, trend):
        if not candles:
            return 0.0
        first_open = candles[0].open
        last_close = candles[-1].close
        if trend == Trend.UP:
            return max(0.0, last_close - first_open)
        return max(0.0, first_open - last_close)

    @staticmethod
    def _holds_open(candles, open_price, trend):
        if trend == Trend.UP:
            violations = sum(1 for candle in candles[1:] if candle.close < open_price)
        else:
            violations = sum(1 for candle in candles[1:] if candle.close > open_price)
        return violations <= 1

    @classmethod
    def _pullbacks(cls, candles, trend):
        items = []
        anchor = candles[0].high if trend == Trend.UP else candles[0].low
        active_start = None
        extreme = None

        for index, candle in enumerate(candles[1:], start=1):
            if trend == Trend.UP:
                if candle.high > anchor:
                    anchor = candle.high
                    active_start = None
                    extreme = None
                elif candle.low < anchor:
                    if active_start is None:
                        active_start = index
                        extreme = candle.low
                    else:
                        extreme = min(extreme, candle.low)
                    if candle.close >= anchor:
                        items.append({
                            "bars": index - active_start + 1,
                            "depth": max(0.0, anchor - extreme),
                        })
                        active_start = None
                        extreme = None
            else:
                if candle.low < anchor:
                    anchor = candle.low
                    active_start = None
                    extreme = None
                elif candle.high > anchor:
                    if active_start is None:
                        active_start = index
                        extreme = candle.high
                    else:
                        extreme = max(extreme, candle.high)
                    if candle.close <= anchor:
                        items.append({
                            "bars": index - active_start + 1,
                            "depth": max(0.0, extreme - anchor),
                        })
                        active_start = None
                        extreme = None

        if active_start is not None and extreme is not None:
            items.append({
                "bars": len(candles) - active_start,
                "depth": max(0.0, anchor - extreme) if trend == Trend.UP else max(0.0, extreme - anchor),
            })
        return items

    @staticmethod
    def _typical_range(candles):
        values = [candle.range for candle in candles if candle.range > 0]
        return median(values) if values else 0.0

    @staticmethod
    def _strength_score(
        opening_aligned_ratio,
        aligned_ratio,
        close_progress,
        efficiency,
        overlap,
        pullback_ratio,
        counter_sequence,
        opening_displacement_ratio,
        holds_open,
    ):
        score = 0.0
        score += min(20.0, opening_aligned_ratio * 20.0)
        score += min(15.0, aligned_ratio * 15.0)
        score += min(15.0, close_progress * 15.0)
        score += min(15.0, efficiency * 20.0)
        score += min(15.0, opening_displacement_ratio * 5.0)
        score += max(0.0, 10.0 * (1.0 - min(1.0, overlap)))
        score += max(0.0, 10.0 * (1.0 - min(1.0, pullback_ratio / 2.0)))
        if holds_open:
            score += 5.0
        score -= min(15.0, counter_sequence * 5.0)
        return round(max(0.0, min(100.0, score)), 2)

    @staticmethod
    def _empty(state="NO_TREND"):
        return {
            "brooks_open_trend_state": state,
            "brooks_open_trend_direction": "NONE",
            "brooks_open_trend_quality": "NONE",
            "brooks_open_trend_score": 0.0,
            "brooks_open_trend_open_price": 0.0,
            "brooks_open_trend_last_close": 0.0,
            "brooks_open_trend_total_move": 0.0,
            "brooks_open_trend_efficiency": 0.0,
            "brooks_open_trend_aligned_ratio": 0.0,
            "brooks_open_trend_opening_aligned_ratio": 0.0,
            "brooks_open_trend_close_progress": 0.0,
            "brooks_open_trend_overlap": 0.0,
            "brooks_open_trend_opening_displacement": 0.0,
            "brooks_open_trend_opening_displacement_ratio": 0.0,
            "brooks_open_trend_pullback_count": 0,
            "brooks_open_trend_max_pullback": 0.0,
            "brooks_open_trend_max_pullback_ratio": 0.0,
            "brooks_open_trend_max_pullback_bars": 0,
            "brooks_open_trend_counter_sequence": 0,
            "brooks_open_trend_holds_open": False,
            "brooks_open_trend_persistent": False,
            "brooks_open_trend_from_open": False,
            "brooks_open_trend_small_pullback": False,
            "brooks_open_trend_wait_deep_pullback_risk": False,
            "brooks_open_trend_with_trend_only": False,
            "brooks_open_trend_valid": False,
        }
