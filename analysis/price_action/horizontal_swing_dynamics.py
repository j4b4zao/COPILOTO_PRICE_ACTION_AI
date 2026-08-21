"""Linhas horizontais de swing inspiradas em Brooks Trends, capítulo 17."""

from statistics import median

from enums.trend import Trend


class HorizontalSwingDynamics:

    LOOKBACK = 30
    TOLERANCE_RATIO = 0.15

    @classmethod
    def analyze(cls, candles, trend):
        closed = list(candles[:-1])
        if len(closed) < 5:
            return cls._empty()

        window = closed[-cls.LOOKBACK:]
        reference = window[:-1]
        current = window[-1]
        levels = cls._levels(reference)
        if not levels:
            return cls._empty()

        tolerance = cls._typical_range(window) * cls.TOLERANCE_RATIO
        levels = cls._merge_levels(levels, tolerance)
        candidates = [
            cls._candidate(level, reference, current, tolerance)
            for level in levels
        ]
        selected = min(
            candidates,
            key=lambda item: (
                -item["priority"],
                item["distance"],
                -item["level_index"],
            ),
        )
        context = cls._context(trend, selected)

        return {
            "brooks_horizontal_state": selected["state"],
            "brooks_horizontal_level_type": selected["level_type"],
            "brooks_horizontal_level": round(selected["level"], 4),
            "brooks_horizontal_distance": round(selected["distance"], 4),
            "brooks_horizontal_tolerance": round(tolerance, 4),
            "brooks_horizontal_test_count": selected["test_count"],
            "brooks_horizontal_break_direction": selected["break_direction"],
            "brooks_horizontal_context": context,
            "brooks_horizontal_tested": selected["tested"],
            "brooks_horizontal_broken": selected["broken"],
            "brooks_horizontal_returned_inside": selected["returned_inside"],
            "brooks_horizontal_breakout_pullback": selected["breakout_pullback"],
            "brooks_horizontal_second_attempt": selected["test_count"] >= 2,
            "brooks_horizontal_countertrend_risk": cls._countertrend_risk(
                trend,
                selected,
            ),
            "brooks_horizontal_valid": True,
        }

    @staticmethod
    def _levels(candles):
        levels = []
        for index in range(1, len(candles) - 1):
            previous = candles[index - 1]
            current = candles[index]
            following = candles[index + 1]
            if current.high >= previous.high and current.high > following.high:
                levels.append(("RESISTANCE", current.high, index))
            if current.low <= previous.low and current.low < following.low:
                levels.append(("SUPPORT", current.low, index))
        return levels

    @staticmethod
    def _merge_levels(levels, tolerance):
        merged = []
        for candidate in levels:
            level_type, level, _ = candidate
            same_zone = any(
                stored_type == level_type
                and abs(stored_level - level) <= tolerance
                for stored_type, stored_level, _ in merged
            )
            if not same_zone:
                merged.append(candidate)
        return merged

    @classmethod
    def _candidate(cls, level_data, reference, current, tolerance):
        level_type, level, level_index = level_data
        previous = reference[-1]
        resistance = level_type == "RESISTANCE"
        beyond_now = (
            current.close > level + tolerance
            if resistance
            else current.close < level - tolerance
        )
        beyond_before = (
            previous.close > level + tolerance
            if resistance
            else previous.close < level - tolerance
        )
        touched = (
            current.high >= level - tolerance
            if resistance
            else current.low <= level + tolerance
        )
        inside_now = current.close <= level if resistance else current.close >= level
        pullback_touch = (
            current.low <= level + tolerance
            if resistance
            else current.high >= level - tolerance
        )
        breakout_pullback = beyond_before and beyond_now and pullback_touch
        returned_inside = beyond_before and inside_now
        broken = beyond_now
        tested = touched and inside_now and not returned_inside
        test_count = cls._test_count(
            reference[level_index + 1:],
            level_type,
            level,
            tolerance,
        ) + (1 if tested or returned_inside else 0)

        if returned_inside:
            state, priority = "FAILED_BREAKOUT", 5
        elif breakout_pullback:
            state, priority = "BREAKOUT_PULLBACK", 4
        elif broken:
            state, priority = "BREAKOUT", 3
        elif tested:
            state, priority = "LEVEL_TEST", 2
        else:
            state, priority = "ACTIVE_LEVEL", 1

        return {
            "state": state,
            "priority": priority,
            "level_type": level_type,
            "level": level,
            "level_index": level_index,
            "distance": abs(current.close - level),
            "test_count": test_count,
            "break_direction": (
                ("UP" if resistance else "DOWN")
                if broken or beyond_before
                else "NONE"
            ),
            "tested": tested,
            "broken": broken,
            "returned_inside": returned_inside,
            "breakout_pullback": breakout_pullback,
        }

    @staticmethod
    def _test_count(candles, level_type, level, tolerance):
        count = 0
        for candle in candles:
            if level_type == "RESISTANCE":
                test = candle.high >= level - tolerance and candle.close <= level
            else:
                test = candle.low <= level + tolerance and candle.close >= level
            if test:
                count += 1
        return count

    @staticmethod
    def _context(trend, selected):
        if trend in (Trend.SIDEWAYS, Trend.UNKNOWN):
            return "RANGE_REVERSAL"
        if selected["breakout_pullback"]:
            return "TREND_PULLBACK"
        return "TREND_REFERENCE"

    @staticmethod
    def _countertrend_risk(trend, selected):
        return (
            trend == Trend.UP
            and selected["level_type"] == "RESISTANCE"
            and selected["state"] in ("LEVEL_TEST", "FAILED_BREAKOUT")
        ) or (
            trend == Trend.DOWN
            and selected["level_type"] == "SUPPORT"
            and selected["state"] in ("LEVEL_TEST", "FAILED_BREAKOUT")
        )

    @staticmethod
    def _typical_range(candles):
        ranges = [candle.range for candle in candles if candle.range > 0.0]
        return median(ranges) if ranges else 0.0

    @staticmethod
    def _empty():
        return {
            "brooks_horizontal_state": "NO_LEVEL",
            "brooks_horizontal_level_type": "NONE",
            "brooks_horizontal_level": 0.0,
            "brooks_horizontal_distance": 0.0,
            "brooks_horizontal_tolerance": 0.0,
            "brooks_horizontal_test_count": 0,
            "brooks_horizontal_break_direction": "NONE",
            "brooks_horizontal_context": "NEUTRAL",
            "brooks_horizontal_tested": False,
            "brooks_horizontal_broken": False,
            "brooks_horizontal_returned_inside": False,
            "brooks_horizontal_breakout_pullback": False,
            "brooks_horizontal_second_attempt": False,
            "brooks_horizontal_countertrend_risk": False,
            "brooks_horizontal_valid": False,
        }
