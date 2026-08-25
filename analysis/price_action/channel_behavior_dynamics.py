"""Comportamento de canais inspirado em Brooks Trends, capítulo 15."""

from statistics import median


class ChannelBehaviorDynamics:

    TIGHT_WIDTH_RATIO = 2.50
    WIDE_WIDTH_RATIO = 4.00
    HIGH_OVERLAP = 0.65
    OUTER_ZONE = 0.80

    @classmethod
    def analyze(cls, candles, result):
        closed = list(candles[:-1])
        if not result.brooks_channel_line_valid or len(closed) < 5:
            return cls._empty()

        typical_range = cls._typical_range(closed)
        width_ratio = (
            result.brooks_channel_line_width / typical_range
            if typical_range > 0.0
            else 0.0
        )
        slope_strength = (
            abs(result.brooks_channel_line_slope) / typical_range
            if typical_range > 0.0
            else 0.0
        )
        overlap = cls._overlap(closed[-10:])
        classification = cls._classification(
            width_ratio,
            overlap,
            slope_strength,
        )
        behavior = cls._behavior(classification)
        location = cls._location(
            result.brooks_channel_line_position
        )
        pushes = cls._pushes(
            closed[-12:],
            result.brooks_channel_line_direction,
        )
        outer_zone = cls._outer_zone(
            result.brooks_channel_line_position,
            result.brooks_channel_line_direction,
        )
        third_push_risk = pushes >= 3 and outer_zone
        measured_target = cls._measured_target(result)

        return {
            "brooks_channel_state": cls._state(result),
            "brooks_channel_classification": classification,
            "brooks_channel_behavior": behavior,
            "brooks_channel_direction": result.brooks_channel_line_direction,
            "brooks_channel_location": location,
            "brooks_channel_width_ratio": round(width_ratio, 4),
            "brooks_channel_slope_strength": round(slope_strength, 4),
            "brooks_channel_overlap": round(overlap, 4),
            "brooks_channel_pushes": pushes,
            "brooks_channel_outer_zone": outer_zone,
            "brooks_channel_third_push_risk": third_push_risk,
            "brooks_channel_two_sided": behavior == "SLOPED_RANGE",
            "brooks_channel_countertrend_risk": behavior == "TREND_LIKE",
            "brooks_channel_measured_target": round(measured_target, 4),
            "brooks_channel_valid": True,
        }

    @staticmethod
    def _typical_range(candles):
        ranges = [candle.range for candle in candles if candle.range > 0.0]
        return median(ranges) if ranges else 0.0

    @staticmethod
    def _overlap(candles):
        ratios = []
        for previous, current in zip(candles, candles[1:]):
            shared = max(
                0.0,
                min(previous.high, current.high)
                - max(previous.low, current.low),
            )
            scale = min(previous.range, current.range)
            ratios.append(shared / scale if scale > 0.0 else 0.0)
        return sum(ratios) / len(ratios) if ratios else 0.0

    @classmethod
    def _classification(cls, width_ratio, overlap, slope_strength):
        if (
            width_ratio <= cls.TIGHT_WIDTH_RATIO
            and overlap < cls.HIGH_OVERLAP
        ) or (
            slope_strength >= 0.20
            and overlap < 0.50
        ):
            return "TIGHT"
        if width_ratio >= cls.WIDE_WIDTH_RATIO or overlap >= cls.HIGH_OVERLAP:
            return "WIDE"
        return "STANDARD"

    @staticmethod
    def _behavior(classification):
        if classification == "TIGHT":
            return "TREND_LIKE"
        if classification == "WIDE":
            return "SLOPED_RANGE"
        return "MIXED"

    @staticmethod
    def _location(position):
        if position <= 1.0 / 3.0:
            return "LOWER_THIRD"
        if position >= 2.0 / 3.0:
            return "UPPER_THIRD"
        return "MIDDLE"

    @staticmethod
    def _pushes(candles, direction):
        count = 0
        for index in range(1, len(candles) - 1):
            previous = candles[index - 1]
            current = candles[index]
            following = candles[index + 1]
            if direction == "UP":
                pivot = (
                    current.high >= previous.high
                    and current.high >= following.high
                )
            else:
                pivot = (
                    current.low <= previous.low
                    and current.low <= following.low
                )
            if pivot:
                count += 1
        return count

    @classmethod
    def _outer_zone(cls, position, direction):
        if direction == "UP":
            return position >= cls.OUTER_ZONE
        return position <= 1.0 - cls.OUTER_ZONE

    @staticmethod
    def _measured_target(result):
        if result.brooks_channel_line_accelerating:
            if result.brooks_channel_line_direction == "UP":
                return (
                    result.brooks_channel_line_level
                    + result.brooks_channel_line_width
                )
            return (
                result.brooks_channel_line_level
                - result.brooks_channel_line_width
            )
        if result.brooks_channel_line_returned_inside:
            return result.brooks_channel_line_trend_level
        return 0.0

    @staticmethod
    def _state(result):
        if result.brooks_channel_line_returned_inside:
            return "FAILED_BREAKOUT_RETURN"
        if result.brooks_channel_line_accelerating:
            return "BREAKOUT_MEASURED_MOVE"
        if result.brooks_channel_line_tested:
            return "OUTER_LINE_TEST"
        return "CHANNEL_ACTIVE"

    @staticmethod
    def _empty():
        return {
            "brooks_channel_state": "NO_CHANNEL",
            "brooks_channel_classification": "NONE",
            "brooks_channel_behavior": "NONE",
            "brooks_channel_direction": "NONE",
            "brooks_channel_location": "MIDDLE",
            "brooks_channel_width_ratio": 0.0,
            "brooks_channel_slope_strength": 0.0,
            "brooks_channel_overlap": 0.0,
            "brooks_channel_pushes": 0,
            "brooks_channel_outer_zone": False,
            "brooks_channel_third_push_risk": False,
            "brooks_channel_two_sided": False,
            "brooks_channel_countertrend_risk": False,
            "brooks_channel_measured_target": 0.0,
            "brooks_channel_valid": False,
        }
