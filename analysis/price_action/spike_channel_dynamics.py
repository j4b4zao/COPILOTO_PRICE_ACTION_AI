"""Dinâmica Spike and Channel inspirada em Brooks Trends, capítulo 21.

Esta camada é diagnóstica. Ela identifica a transição de um spike direcional
para um canal de tendência, estima a qualidade da continuação e projeta alvos
simples de movimento medido. Não autoriza operações por conta própria.
"""

from statistics import median

from enums.trend import Trend


class SpikeChannelDynamics:

    LOOKBACK = 30
    MIN_SPIKE_BARS = 1
    MAX_SPIKE_BARS = 8
    MIN_CHANNEL_BARS = 3
    LARGE_BODY_RATIO = 0.60
    STRONG_CLOSE = 0.70
    MAX_SPIKE_OVERLAP = 0.35
    MIN_SPIKE_EFFICIENCY = 0.65

    @classmethod
    def analyze(cls, candles, trend):
        closed = list(candles[:-1])
        if len(closed) < 6 or trend not in (Trend.UP, Trend.DOWN):
            return cls._empty()

        window = closed[-cls.LOOKBACK:]
        direction = "UP" if trend == Trend.UP else "DOWN"
        spike = cls._find_spike(window, direction)
        if spike is None:
            return cls._empty(direction=direction)

        pullback = cls._find_pullback(window, spike, direction)
        channel = cls._find_channel(window, spike, pullback, direction)
        phase = cls._phase(spike, pullback, channel)

        spike_size = abs(spike["end_price"] - spike["start_price"])
        channel_size = cls._channel_size(channel)
        measured_target = cls._measured_target(spike, direction)
        leg_equality_target = cls._leg_equality_target(spike, channel, direction)

        return {
            "brooks_spike_channel_state": phase,
            "brooks_spike_channel_direction": direction,
            "brooks_spike_start_index": spike["start_index"],
            "brooks_spike_end_index": spike["end_index"],
            "brooks_spike_bar_count": spike["bar_count"],
            "brooks_spike_size": round(spike_size, 4),
            "brooks_spike_efficiency": round(spike["efficiency"], 4),
            "brooks_spike_overlap": round(spike["overlap"], 4),
            "brooks_spike_strength": spike["strength"],
            "brooks_spike_urgency": spike["urgency"],
            "brooks_spike_pullback_detected": pullback is not None,
            "brooks_spike_pullback_bars": pullback["bar_count"] if pullback else 0,
            "brooks_spike_pullback_depth": round(pullback["depth"], 4) if pullback else 0.0,
            "brooks_channel_detected": channel is not None,
            "brooks_channel_bar_count_ch21": channel["bar_count"] if channel else 0,
            "brooks_channel_progress": round(channel["progress"], 4) if channel else 0.0,
            "brooks_channel_overlap_ch21": round(channel["overlap"], 4) if channel else 0.0,
            "brooks_channel_two_sided": bool(channel and channel["two_sided"]),
            "brooks_spike_channel_continuation": bool(channel and channel["progress"] > 0),
            "brooks_spike_channel_measured_target": round(measured_target, 4),
            "brooks_spike_channel_leg_equality_target": round(leg_equality_target, 4),
            "brooks_spike_channel_target_reached": cls._target_reached(window, measured_target, direction),
            "brooks_spike_channel_second_spike_risk": cls._second_spike_risk(window, spike, channel, direction),
            "brooks_spike_channel_reversal_watch": cls._reversal_watch(window, channel, direction),
            "brooks_spike_channel_valid": True,
        }

    @classmethod
    def _find_spike(cls, candles, direction):
        best = None
        typical_range = cls._typical_range(candles)
        if typical_range <= 0:
            return None

        for end in range(len(candles) - 2, 0, -1):
            for length in range(cls.MAX_SPIKE_BARS, cls.MIN_SPIKE_BARS - 1, -1):
                start = end - length + 1
                if start < 0:
                    continue
                segment = candles[start:end + 1]
                metrics = cls._spike_metrics(segment, direction, typical_range)
                if metrics is None:
                    continue
                candidate = {
                    **metrics,
                    "start_index": start,
                    "end_index": end,
                    "start_price": segment[0].open,
                    "end_price": segment[-1].close,
                    "bar_count": length,
                }
                if best is None or candidate["score"] > best["score"]:
                    best = candidate
            if best is not None:
                break
        return best

    @classmethod
    def _spike_metrics(cls, segment, direction, typical_range):
        start = segment[0].open
        end = segment[-1].close
        net = end - start
        if direction == "DOWN":
            net = -net
        if net <= 0:
            return None

        path = sum(abs(c.close - c.open) for c in segment)
        efficiency = net / path if path > 0 else 0.0
        overlap = cls._average_overlap(segment)
        aligned = sum(1 for c in segment if cls._aligned(c, direction)) / len(segment)
        large = sum(
            1 for c in segment
            if c.range > 0 and (c.body / c.range) >= cls.LARGE_BODY_RATIO
        ) / len(segment)
        near_extreme = sum(
            1 for c in segment
            if cls._close_near_extreme(c, direction)
        ) / len(segment)
        range_multiple = net / typical_range

        if (
            efficiency < cls.MIN_SPIKE_EFFICIENCY
            or overlap > cls.MAX_SPIKE_OVERLAP
            or aligned < 0.70
            or range_multiple < 1.2
        ):
            return None

        score = (
            efficiency * 35
            + (1.0 - overlap) * 20
            + aligned * 20
            + large * 10
            + near_extreme * 10
            + min(range_multiple / 4.0, 1.0) * 5
        )
        strength = "VERY_STRONG" if score >= 85 else "STRONG" if score >= 70 else "MODERATE"
        urgency = bool(aligned >= 0.80 and overlap <= 0.20 and efficiency >= 0.75)
        return {
            "efficiency": efficiency,
            "overlap": overlap,
            "aligned_ratio": aligned,
            "score": score,
            "strength": strength,
            "urgency": urgency,
        }

    @classmethod
    def _find_pullback(cls, candles, spike, direction):
        start = spike["end_index"] + 1
        if start >= len(candles):
            return None

        spike_size = abs(spike["end_price"] - spike["start_price"])
        bars = 0
        extreme = spike["end_price"]
        deepest = extreme
        for index in range(start, min(start + 10, len(candles))):
            candle = candles[index]
            against = not cls._aligned(candle, direction)
            if bars == 0 and not against:
                continue
            if bars > 0 and cls._aligned(candle, direction):
                break
            bars += 1
            deepest = min(deepest, candle.low) if direction == "UP" else max(deepest, candle.high)

        if bars == 0:
            return None

        depth_points = (spike["end_price"] - deepest) if direction == "UP" else (deepest - spike["end_price"])
        depth = depth_points / spike_size if spike_size > 0 else 0.0
        return {
            "start_index": start,
            "end_index": start + bars - 1,
            "bar_count": bars,
            "depth": max(depth, 0.0),
        }

    @classmethod
    def _find_channel(cls, candles, spike, pullback, direction):
        if pullback is None:
            return None
        start = pullback["end_index"] + 1
        if len(candles) - start < cls.MIN_CHANNEL_BARS:
            return None
        segment = candles[start:]
        aligned = sum(1 for c in segment if cls._aligned(c, direction))
        opposite = len(segment) - aligned
        first = segment[0].close
        last = segment[-1].close
        progress = (last - first) if direction == "UP" else (first - last)
        if progress <= 0 or aligned < max(2, len(segment) // 2):
            return None
        return {
            "start_index": start,
            "end_index": len(candles) - 1,
            "bar_count": len(segment),
            "progress": progress,
            "overlap": cls._average_overlap(segment),
            "two_sided": opposite > 0,
            "start_price": segment[0].open,
            "end_price": segment[-1].close,
        }

    @staticmethod
    def _phase(spike, pullback, channel):
        if channel is not None:
            return "CHANNEL"
        if pullback is not None:
            return "PULLBACK_AFTER_SPIKE"
        if spike is not None:
            return "SPIKE"
        return "NONE"

    @staticmethod
    def _channel_size(channel):
        if channel is None:
            return 0.0
        return abs(channel["end_price"] - channel["start_price"])

    @staticmethod
    def _measured_target(spike, direction):
        size = abs(spike["end_price"] - spike["start_price"])
        return spike["end_price"] + size if direction == "UP" else spike["end_price"] - size

    @staticmethod
    def _leg_equality_target(spike, channel, direction):
        size = abs(spike["end_price"] - spike["start_price"])
        base = channel["start_price"] if channel else spike["end_price"]
        return base + size if direction == "UP" else base - size

    @staticmethod
    def _target_reached(candles, target, direction):
        if direction == "UP":
            return any(c.high >= target for c in candles)
        return any(c.low <= target for c in candles)

    @classmethod
    def _second_spike_risk(cls, candles, spike, channel, direction):
        if channel is None or channel["bar_count"] < 2:
            return False
        recent = candles[-2:]
        if not all(cls._aligned(c, direction) for c in recent):
            return False
        return all(c.range > 0 and (c.body / c.range) >= cls.LARGE_BODY_RATIO for c in recent)

    @classmethod
    def _reversal_watch(cls, candles, channel, direction):
        if channel is None or channel["bar_count"] < 3:
            return False
        recent = candles[-3:]
        opposite = [not cls._aligned(c, direction) for c in recent]
        return sum(opposite) >= 2

    @staticmethod
    def _aligned(candle, direction):
        return candle.close > candle.open if direction == "UP" else candle.close < candle.open

    @classmethod
    def _close_near_extreme(cls, candle, direction):
        if candle.range <= 0:
            return False
        if direction == "UP":
            position = (candle.close - candle.low) / candle.range
        else:
            position = (candle.high - candle.close) / candle.range
        return position >= cls.STRONG_CLOSE

    @staticmethod
    def _average_overlap(candles):
        if len(candles) < 2:
            return 0.0
        ratios = []
        for previous, current in zip(candles, candles[1:]):
            low = max(previous.low, current.low)
            high = min(previous.high, current.high)
            overlap = max(0.0, high - low)
            base = min(previous.range, current.range)
            ratios.append(overlap / base if base > 0 else 0.0)
        return sum(ratios) / len(ratios)

    @staticmethod
    def _typical_range(candles):
        ranges = [c.range for c in candles if c.range > 0]
        return median(ranges) if ranges else 0.0

    @staticmethod
    def _empty(direction="NONE"):
        return {
            "brooks_spike_channel_state": "NONE",
            "brooks_spike_channel_direction": direction,
            "brooks_spike_start_index": -1,
            "brooks_spike_end_index": -1,
            "brooks_spike_bar_count": 0,
            "brooks_spike_size": 0.0,
            "brooks_spike_efficiency": 0.0,
            "brooks_spike_overlap": 0.0,
            "brooks_spike_strength": "NONE",
            "brooks_spike_urgency": False,
            "brooks_spike_pullback_detected": False,
            "brooks_spike_pullback_bars": 0,
            "brooks_spike_pullback_depth": 0.0,
            "brooks_channel_detected": False,
            "brooks_channel_bar_count_ch21": 0,
            "brooks_channel_progress": 0.0,
            "brooks_channel_overlap_ch21": 0.0,
            "brooks_channel_two_sided": False,
            "brooks_spike_channel_continuation": False,
            "brooks_spike_channel_measured_target": 0.0,
            "brooks_spike_channel_leg_equality_target": 0.0,
            "brooks_spike_channel_target_reached": False,
            "brooks_spike_channel_second_spike_risk": False,
            "brooks_spike_channel_reversal_watch": False,
            "brooks_spike_channel_valid": False,
        }
